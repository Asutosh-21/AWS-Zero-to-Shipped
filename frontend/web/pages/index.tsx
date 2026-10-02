"use client";
import { useState, useRef } from "react";
import { Amplify } from "aws-amplify";
import { fetchAuthSession } from "aws-amplify/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

interface QueryResult {
  response: string;
  sessionId: string;
  agentSteps: string[];
}

export default function HomePage() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<QueryResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const exampleQueries = [
    "Family of 4 in Detroit 48201, $180 SNAP, no car, daughter is lactose intolerant",
    "Single mom in Chicago 60629, $120 SNAP, 2 kids, need halal food options",
    "Familia de 3 en Los Angeles 90011, $150 SNAP, sin carro",
  ];

  async function handleQuery(queryText: string) {
    if (!queryText.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString() || "";

      const response = await fetch(`${API_URL}/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ query: queryText, sessionId: crypto.randomUUID() }),
      });

      if (!response.ok) throw new Error(`API error: ${response.status}`);
      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  async function startVoiceRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mediaRecorder = new MediaRecorder(stream);
    mediaRecorderRef.current = mediaRecorder;
    audioChunksRef.current = [];

    mediaRecorder.ondataavailable = (e) => audioChunksRef.current.push(e.data);
    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunksRef.current, { type: "audio/mpeg" });
      const reader = new FileReader();
      reader.onloadend = async () => {
        const base64 = (reader.result as string).split(",")[1];
        const session = await fetchAuthSession();
        const token = session.tokens?.idToken?.toString() || "";
        const response = await fetch(`${API_URL}/voice`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({ audio: base64, language: "en", sessionId: crypto.randomUUID() }),
        });
        const data = await response.json();
        setQuery(data.transcribedText || "");
        setResult({ response: data.responseText, sessionId: "", agentSteps: [] });
        if (data.audioResponse) {
          const audio = new Audio(`data:audio/mpeg;base64,${data.audioResponse}`);
          audio.play();
        }
      };
      reader.readAsDataURL(audioBlob);
      stream.getTracks().forEach((t) => t.stop());
    };

    mediaRecorder.start();
    setIsRecording(true);
  }

  function stopVoiceRecording() {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-green-50 to-white">
      <div className="max-w-3xl mx-auto px-4 py-12">
        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold text-green-800 mb-2">🥦 NutriRoute AI</h1>
          <p className="text-gray-600 text-lg">
            Find food, plan meals, and get there — one question at a time
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-lg p-6 mb-6">
          <textarea
            className="w-full border border-gray-200 rounded-xl p-4 text-gray-800 resize-none focus:outline-none focus:ring-2 focus:ring-green-400"
            rows={3}
            placeholder="Tell me about your family, location, SNAP balance, and any dietary needs..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />

          <div className="flex gap-3 mt-3">
            <button
              onClick={() => handleQuery(query)}
              disabled={loading || !query.trim()}
              className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-300 text-white font-semibold py-3 rounded-xl transition-colors"
            >
              {loading ? "Finding food..." : "Find Food & Plan Meals"}
            </button>
            <button
              onClick={isRecording ? stopVoiceRecording : startVoiceRecording}
              className={`px-4 py-3 rounded-xl font-semibold transition-colors ${
                isRecording ? "bg-red-500 text-white animate-pulse" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {isRecording ? "⏹ Stop" : "🎤 Voice"}
            </button>
          </div>

          <div className="mt-4">
            <p className="text-xs text-gray-400 mb-2">Try an example:</p>
            <div className="flex flex-col gap-2">
              {exampleQueries.map((q, i) => (
                <button
                  key={i}
                  onClick={() => { setQuery(q); handleQuery(q); }}
                  className="text-left text-sm text-green-700 hover:text-green-900 hover:underline truncate"
                >
                  → {q}
                </button>
              ))}
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 text-red-700">
            {error}
          </div>
        )}

        {loading && (
          <div className="bg-white rounded-2xl shadow-lg p-8 text-center">
            <div className="flex justify-center gap-4 mb-4">
              {["🔍 Finding food sources...", "🥗 Planning meals...", "🗺 Optimizing route..."].map((step, i) => (
                <div key={i} className="text-sm text-gray-500 animate-pulse" style={{ animationDelay: `${i * 0.3}s` }}>
                  {step}
                </div>
              ))}
            </div>
            <p className="text-gray-400 text-sm">3 AI agents working for you...</p>
          </div>
        )}

        {result && (
          <div className="bg-white rounded-2xl shadow-lg p-6">
            <div className="prose prose-green max-w-none">
              <pre className="whitespace-pre-wrap text-gray-800 font-sans text-sm leading-relaxed">
                {result.response}
              </pre>
            </div>
            {result.agentSteps.length > 0 && (
              <details className="mt-4">
                <summary className="text-xs text-gray-400 cursor-pointer">Agent reasoning steps</summary>
                <div className="mt-2 space-y-1">
                  {result.agentSteps.map((step, i) => (
                    <p key={i} className="text-xs text-gray-500">• {step}</p>
                  ))}
                </div>
              </details>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
