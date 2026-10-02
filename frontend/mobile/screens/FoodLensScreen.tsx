import React, { useState, useRef } from "react";
import {
  View, Text, TouchableOpacity, Image,
  ScrollView, StyleSheet, ActivityIndicator, Alert,
} from "react-native";
import { Camera, CameraType } from "expo-camera";

const API_URL = process.env.EXPO_PUBLIC_API_URL || "";

const RESTRICTIONS = ["none", "lactose-free", "gluten-free", "vegan", "halal"];

interface DetectedFood { name: string; confidence: number; }

export default function FoodLensScreen() {
  const [permission, requestPermission] = Camera.useCameraPermissions();
  const [cameraActive, setCameraActive]       = useState(false);
  const [preview, setPreview]                 = useState<string | null>(null);
  const [loading, setLoading]                 = useState(false);
  const [detectedFoods, setDetectedFoods]     = useState<DetectedFood[]>([]);
  const [mealSuggestions, setMealSuggestions] = useState("");
  const [restriction, setRestriction]         = useState("none");
  const cameraRef = useRef<Camera>(null);

  async function takePicture() {
    if (!cameraRef.current) return;
    const photo = await cameraRef.current.takePictureAsync({ quality: 0.7, base64: true });
    setPreview(photo.uri);
    setCameraActive(false);
    await analyzeImage(photo.base64 || "");
  }

  async function analyzeImage(base64: string) {
    if (!base64) return;
    setLoading(true);
    setDetectedFoods([]);
    setMealSuggestions("");
    try {
      const res = await fetch(`${API_URL}/foodlens`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          image: base64,
          dietaryRestrictions: restriction,
          sessionId: Math.random().toString(36),
        }),
      });
      const data = await res.json();
      setDetectedFoods(data.detectedFoods || []);
      setMealSuggestions(data.mealSuggestions || data.message || "");
    } catch {
      Alert.alert("Error", "Could not analyze image. Check your connection.");
    } finally {
      setLoading(false);
    }
  }

  async function openCamera() {
    if (!permission?.granted) {
      const { granted } = await requestPermission();
      if (!granted) { Alert.alert("Camera permission required"); return; }
    }
    setCameraActive(true);
  }

  if (cameraActive) {
    return (
      <View style={styles.cameraContainer}>
        <Camera ref={cameraRef} style={styles.camera} type={CameraType.back}>
          <View style={styles.cameraOverlay}>
            <Text style={styles.cameraHint}>Point at your fridge or pantry shelf</Text>
            <TouchableOpacity style={styles.captureBtn} onPress={takePicture}>
              <Text style={styles.captureBtnText}>📸</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={() => setCameraActive(false)}>
              <Text style={styles.cancelText}>Cancel</Text>
            </TouchableOpacity>
          </View>
        </Camera>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <Text style={styles.title}>📷 FoodLens</Text>
        <Text style={styles.subtitle}>Point at your fridge — get instant meal ideas</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.label}>Dietary restrictions</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chips}>
          {RESTRICTIONS.map((r) => (
            <TouchableOpacity
              key={r}
              onPress={() => setRestriction(r)}
              style={[styles.chip, restriction === r && styles.chipActive]}
            >
              <Text style={[styles.chipText, restriction === r && styles.chipTextActive]}>{r}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
        <TouchableOpacity style={styles.button} onPress={openCamera}>
          <Text style={styles.buttonText}>📷 Open Camera</Text>
        </TouchableOpacity>
      </View>

      {preview && (
        <Image source={{ uri: preview }} style={styles.preview} resizeMode="cover" />
      )}

      {loading && (
        <View style={styles.loadingCard}>
          <ActivityIndicator color="#16A34A" size="large" />
          <Text style={styles.loadingText}>Analyzing with Amazon Rekognition...</Text>
        </View>
      )}

      {detectedFoods.length > 0 && (
        <View style={styles.resultCard}>
          <Text style={styles.resultTitle}>Found {detectedFoods.length} ingredients</Text>
          <View style={styles.foodChips}>
            {detectedFoods.map((f, i) => (
              <View key={i} style={styles.foodChip}>
                <Text style={styles.foodChipText}>{f.name} ({f.confidence}%)</Text>
              </View>
            ))}
          </View>
          {mealSuggestions ? (
            <>
              <Text style={styles.mealsTitle}>🍳 Meals you can make right now</Text>
              <Text style={styles.mealsText}>{mealSuggestions}</Text>
            </>
          ) : null}
        </View>
      )}

      {!loading && detectedFoods.length === 0 && mealSuggestions ? (
        <View style={styles.resultCard}>
          <Text style={styles.mealsText}>{mealSuggestions}</Text>
        </View>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container:      { flex: 1, backgroundColor: "#F0FDF4" },
  content:        { padding: 20, paddingBottom: 40 },
  header:         { alignItems: "center", marginBottom: 20 },
  title:          { fontSize: 28, fontWeight: "bold", color: "#166534" },
  subtitle:       { fontSize: 14, color: "#6B7280", marginTop: 4, textAlign: "center" },
  card:           { backgroundColor: "#fff", borderRadius: 16, padding: 16, marginBottom: 16, shadowColor: "#000", shadowOpacity: 0.08, shadowRadius: 8, elevation: 3 },
  label:          { fontSize: 13, color: "#6B7280", marginBottom: 8 },
  chips:          { flexDirection: "row", marginBottom: 12 },
  chip:           { borderWidth: 1, borderColor: "#D1D5DB", borderRadius: 20, paddingHorizontal: 12, paddingVertical: 6, marginRight: 8 },
  chipActive:     { backgroundColor: "#16A34A", borderColor: "#16A34A" },
  chipText:       { fontSize: 12, color: "#6B7280" },
  chipTextActive: { color: "#fff" },
  button:         { backgroundColor: "#16A34A", borderRadius: 12, padding: 16, alignItems: "center" },
  buttonText:     { color: "#fff", fontWeight: "700", fontSize: 16 },
  preview:        { width: "100%", height: 220, borderRadius: 16, marginBottom: 16 },
  loadingCard:    { backgroundColor: "#fff", borderRadius: 16, padding: 24, alignItems: "center", gap: 12, marginBottom: 16 },
  loadingText:    { fontSize: 13, color: "#6B7280", textAlign: "center" },
  resultCard:     { backgroundColor: "#fff", borderRadius: 16, padding: 16, shadowColor: "#000", shadowOpacity: 0.08, shadowRadius: 8, elevation: 3 },
  resultTitle:    { fontSize: 16, fontWeight: "bold", color: "#166534", marginBottom: 10 },
  foodChips:      { flexDirection: "row", flexWrap: "wrap", gap: 6, marginBottom: 14 },
  foodChip:       { backgroundColor: "#DCFCE7", borderRadius: 12, paddingHorizontal: 10, paddingVertical: 4 },
  foodChipText:   { fontSize: 12, color: "#166534" },
  mealsTitle:     { fontSize: 14, fontWeight: "600", color: "#1F2937", marginBottom: 8 },
  mealsText:      { fontSize: 13, color: "#374151", lineHeight: 20 },
  cameraContainer:{ flex: 1 },
  camera:         { flex: 1 },
  cameraOverlay:  { flex: 1, justifyContent: "flex-end", alignItems: "center", paddingBottom: 40, gap: 16 },
  cameraHint:     { color: "#fff", fontSize: 14, backgroundColor: "rgba(0,0,0,0.5)", paddingHorizontal: 16, paddingVertical: 8, borderRadius: 20 },
  captureBtn:     { width: 72, height: 72, borderRadius: 36, backgroundColor: "#fff", justifyContent: "center", alignItems: "center" },
  captureBtnText: { fontSize: 32 },
  cancelText:     { color: "#fff", fontSize: 16 },
});
