import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Text } from "react-native";
import { Amplify } from "aws-amplify";

import HomeScreen    from "./screens/HomeScreen";
import FoodLensScreen from "./screens/FoodLensScreen";

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId:       process.env.EXPO_PUBLIC_COGNITO_USER_POOL_ID  || "",
      userPoolClientId: process.env.EXPO_PUBLIC_COGNITO_CLIENT_ID     || "",
    },
  },
});

const Tab = createBottomTabNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <Tab.Navigator
        screenOptions={{
          tabBarActiveTintColor:   "#16A34A",
          tabBarInactiveTintColor: "#9CA3AF",
          tabBarStyle: { paddingBottom: 4, height: 60 },
          headerStyle:      { backgroundColor: "#166534" },
          headerTintColor:  "#fff",
          headerTitleStyle: { fontWeight: "bold" },
        }}
      >
        <Tab.Screen
          name="Home"
          component={HomeScreen}
          options={{
            title: "NutriRoute AI",
            tabBarLabel: "Find Food",
            tabBarIcon: ({ color }) => <Text style={{ fontSize: 20, color }}>🥦</Text>,
          }}
        />
        <Tab.Screen
          name="FoodLens"
          component={FoodLensScreen}
          options={{
            title: "FoodLens",
            tabBarLabel: "FoodLens",
            tabBarIcon: ({ color }) => <Text style={{ fontSize: 20, color }}>📷</Text>,
          }}
        />
      </Tab.Navigator>
    </NavigationContainer>
  );
}
