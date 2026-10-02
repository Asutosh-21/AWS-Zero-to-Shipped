import React, { useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity,
  ScrollView, StyleSheet, ActivityIndicator, Alert,
} from "react-native";

const API_URL = process.env.EXPO_PUBLIC_API_URL || "";

const EXAMPLE_QUERIES = [
  "Family of 4 in Detroit 48201, $180 SNAP, no car, daughter is lactose intolerant",
  "Single mom in Chicago 60629, $120 SNAP, 2 kids, halal food only",
  "Familia de 3 en Los Angeles 90011, $150 SNAP, sin carro",
];

export default function HomeScreen() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleQuery(queryText: string) {
    if (!queryText.trim()) return;
    setLoading(true);
    setResponse("");
    try {
      const res = await fetch(`${API_URL}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: queryText, sessionId: Math.random().toString(36) }),
      });
      const data = await res.json();
      setResponse(data.response || "No response received");
    } catch {
      Alert.alert("Error", "Could not connect. Check your internet connection.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <Text style={styles.title}>🥦 NutriRoute AI</Text>
        <Text style={styles.subtitle}>Find food, plan meals, get there</Text>
      </View>

      <View style={styles.card}>
        <TextInput
          style={styles.input}
          multiline
          numberOfLines={3}
          placeholder="Tell me your location, family size, SNAP balance, and dietary needs..."
          placeholderTextColor="#9CA3AF"
          value={query}
          onChangeText={setQuery}
        />
        <TouchableOpacity
          style={[styles.button, (!query.trim() || loading) && styles.buttonDisabled]}
          onPress={() => handleQuery(query)}
          disabled={!query.trim() || loading}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>Find Food & Plan Meals</Text>
          )}
        </TouchableOpacity>
      </View>

      <View style={styles.examples}>
        <Text style={styles.examplesTitle}>Try an example:</Text>
        {EXAMPLE_QUERIES.map((q, i) => (
          <TouchableOpacity key={i} onPress={() => { setQuery(q); handleQuery(q); }}>
            <Text style={styles.exampleText}>→ {q}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {loading && (
        <View style={styles.loadingCard}>
          <Text style={styles.loadingText}>🔍 Finding food sources...</Text>
          <Text style={styles.loadingText}>🥗 Planning your meals...</Text>
          <Text style={styles.loadingText}>🗺 Optimizing your route...</Text>
        </View>
      )}

      {response ? (
        <View style={styles.responseCard}>
          <Text style={styles.responseText}>{response}</Text>
        </View>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F0FDF4" },
  content: { padding: 20, paddingBottom: 40 },
  header: { alignItems: "center", marginBottom: 24 },
  title: { fontSize: 32, fontWeight: "bold", color: "#166534" },
  subtitle: { fontSize: 16, color: "#6B7280", marginTop: 4 },
  card: { backgroundColor: "#fff", borderRadius: 16, padding: 16, marginBottom: 16, shadowColor: "#000", shadowOpacity: 0.08, shadowRadius: 8, elevation: 3 },
  input: { borderWidth: 1, borderColor: "#E5E7EB", borderRadius: 12, padding: 12, fontSize: 15, color: "#1F2937", minHeight: 80, textAlignVertical: "top", marginBottom: 12 },
  button: { backgroundColor: "#16A34A", borderRadius: 12, padding: 16, alignItems: "center" },
  buttonDisabled: { backgroundColor: "#D1D5DB" },
  buttonText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  examples: { marginBottom: 16 },
  examplesTitle: { fontSize: 12, color: "#9CA3AF", marginBottom: 8 },
  exampleText: { fontSize: 13, color: "#15803D", marginBottom: 6, lineHeight: 18 },
  loadingCard: { backgroundColor: "#fff", borderRadius: 16, padding: 20, marginBottom: 16, alignItems: "center", gap: 8 },
  loadingText: { fontSize: 14, color: "#6B7280" },
  responseCard: { backgroundColor: "#fff", borderRadius: 16, padding: 16, shadowColor: "#000", shadowOpacity: 0.08, shadowRadius: 8, elevation: 3 },
  responseText: { fontSize: 14, color: "#1F2937", lineHeight: 22 },
});
