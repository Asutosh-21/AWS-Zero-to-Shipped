"use client";
import { useState, useRef, useCallback } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

interface DetectedFood {
  name: string;
  confidence: number;
}

interface FoodLensResult {
  detectedFoods: DetectedFood[];
  foodCount: number;
  mealSuggestions: string;
  message: string;
  fallbackToManual?: boolean;
}

export default function FoodLensPage() {
  const [result, setResult] = useState<FoodLensResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [dietaryRestrictions, setDietaryRestrictions] = useState("none");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [cameraActive, setCameraActive] = useState(false);

  const analyzeImage = useCallback(async (base64: string) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/foodlens`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: base64, dietaryRestrictions, sessionId: crypto.randomUUID() }),
      });
      const data = await response.json();
      setResult(data);
    } catch {
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, [dietaryRestrictions]);

  function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onloadend = () => {
      const dataUrl = reader.result as string;
      setPreview(dataUrl);
      const base64 = dataUrl.split(",")[1];
      analyzeImage(base64);
    };
    reader.readAsDataURL(file);
  }

  async function startCamera() {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
    if (videoRef.current) {
      videoRef.current.srcObject = stream;
      videoRef.current.play();
    }
    setCameraActive(true);
  }

  function capturePhoto() {
    if (!videoRef.current) return;
    const canvas = document.createElement("canvas");
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    canvas.getContext("2d")?.drawImage(videoRef.current, 0, 0);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.8);
    setPreview(dataUrl);
    const base64 = dataUrl.split(",")[1];
    const stream = videoRef.current.srcObject as MediaStream;
    stream?.getTracks().forEach((t) => t.stop());
    setCameraActive(false);
    analyzeImage(base64);
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-green-50 to-white">
      <div className="max-w-2xl mx-auto px-4 py-12">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-green-800 mb-2">📷 FoodLens</h1>
          <p className="text-gray-600">Point your camera at your fridge or pantry — get instant meal ideas</p>
        </div>

        <div className="bg-white rounded-2xl shadow-lg p-6 mb-6">
          <div className="mb-4">
            <label className="text-sm text-gray-600 mb-1 block">Dietary restrictions</label>
            <select
              value={dietaryRestrictions}
              onChange={(e) => setDietaryRestrictions(e.target.value)}
              className="w-full border border-gray-200 rounded-lg p-2 text-sm"
            >
              <option value="none">None</option>
              <option value="lactose-free">Lactose-free / Dairy-free</option>
              <option value="gluten-free">Gluten-free</option>
              <option value="vegan">Vegan</option>
              <option value="vegetarian">Vegetarian</option>
              <option value="halal">Halal</option>
            </select>
          </div>

          {cameraActive ? (
            <div className="relative">
              <video ref={videoRef} className="w-full rounded-xl" autoPlay playsInline />
              <button
                onClick={capturePhoto}
                className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-white text-green-700 font-bold px-6 py-3 rounded-full shadow-lg"
              >
                📸 Capture
              </button>
            </div>
          ) : (
            <div className="flex gap-3">
              <button
                onClick={startCamera}
                className="flex-1 bg-green-600 hover:bg-green-700 text-white font-semibold py-4 rounded-xl"
              >
                📷 Open Camera
              </button>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold py-4 rounded-xl"
              >
                🖼 Upload Photo
              </button>
              <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleFileUpload} />
            </div>
          )}
        </div>

        {preview && !cameraActive && (
          <div className="bg-white rounded-2xl shadow-lg p-4 mb-6">
            <img src={preview} alt="Food preview" className="w-full rounded-xl object-cover max-h-64" />
          </div>
        )}

        {loading && (
          <div className="bg-white rounded-2xl shadow-lg p-8 text-center">
            <p className="text-green-600 font-semibold animate-pulse">🔍 Analyzing your ingredients...</p>
            <p className="text-gray-400 text-sm mt-2">Amazon Rekognition is scanning your photo</p>
          </div>
        )}

        {result && (
          <div className="bg-white rounded-2xl shadow-lg p-6">
            {result.detectedFoods.length > 0 ? (
              <>
                <h2 className="font-bold text-green-800 mb-3">
                  Found {result.foodCount} ingredients
                </h2>
                <div className="flex flex-wrap gap-2 mb-4">
                  {result.detectedFoods.map((food, i) => (
                    <span key={i} className="bg-green-100 text-green-800 text-sm px-3 py-1 rounded-full">
                      {food.name} ({food.confidence}%)
                    </span>
                  ))}
                </div>
                <div className="border-t pt-4">
                  <h3 className="font-semibold text-gray-800 mb-2">🍳 Meal Ideas</h3>
                  <pre className="whitespace-pre-wrap text-gray-700 text-sm leading-relaxed">
                    {result.mealSuggestions}
                  </pre>
                </div>
              </>
            ) : (
              <div className="text-center py-4">
                <p className="text-gray-600">{result.message}</p>
                <p className="text-sm text-gray-400 mt-2">Try better lighting or a closer photo</p>
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
