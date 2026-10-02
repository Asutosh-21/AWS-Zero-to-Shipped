# NutriRoute AI — Architecture Design

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         NUTRIROUTE AI PLATFORM                          │
│                    AWS Zero to Shipped Hackathon 2026                   │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐   ┌──────────────────┐   ┌──────────────────────────┐
│   Mobile App     │   │    Web App       │   │    NGO Admin Dashboard   │
│  React Native    │   │    Next.js       │   │        Next.js           │
│  + Amplify       │   │  + Amplify       │   │     + QuickSight         │
│                  │   │                  │   │                          │
│ • FoodFinder     │   │ • Food Map       │   │ • Inventory Management   │
│ • MealPlanner    │   │ • Zip Search     │   │ • Impact Analytics       │
│ • RouteMap       │   │ • Impact Stats   │   │ • Stock Updates          │
│ • FoodLens Cam   │   │                  │   │ • Alert Configuration    │
│ • Voice Input    │   │                  │   │                          │
└────────┬─────────┘   └────────┬─────────┘   └────────────┬─────────────┘
         │                      │                           │
         └──────────────────────┴───────────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │      CloudFront       │
                    │       + WAF           │
                    │  (Global CDN + DDoS)  │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │     API Gateway       │
                    │   REST + WebSocket    │
                    │   (Rate limiting,     │
                    │    Auth, Throttling)  │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │       Cognito         │
                    │  User Pools +         │
                    │  Identity Pools       │
                    └───────────┬───────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         │                      │                      │
┌────────▼────────┐  ┌──────────▼──────────┐  ┌───────▼────────┐
│ food-finder     │  │  meal-planner        │  │ route-optimizer│
│ Lambda          │  │  Lambda              │  │ Lambda         │
│ Python 3.12     │  │  Python 3.12         │  │ Python 3.12    │
│ 512MB / 30s     │  │  1024MB / 60s        │  │ 512MB / 30s    │
└────────┬────────┘  └──────────┬──────────┘  └───────┬────────┘
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                │
              ┌─────────────────▼─────────────────┐
              │         BEDROCK AGENT HUB          │
              │                                    │
              │  ┌──────────────────────────────┐  │
              │  │     SUPERVISOR AGENT         │  │
              │  │   Claude 3.5 Sonnet          │  │
              │  │                              │  │
              │  │  Orchestrates all sub-agents │  │
              │  │  Synthesizes unified response│  │
              │  │  Applies Bedrock Guardrails  │  │
              │  └──────────────┬───────────────┘  │
              │                 │                   │
              │    ┌────────────┼────────────┐      │
              │    │            │            │      │
              │  ┌─▼──────┐ ┌──▼─────┐ ┌───▼────┐  │
              │  │ FOOD   │ │ MEAL   │ │ ROUTE  │  │
              │  │ FINDER │ │PLANNER │ │  OPT   │  │
              │  │ AGENT  │ │ AGENT  │ │ AGENT  │  │
              │  │        │ │        │ │        │  │
              │  │Claude  │ │Claude  │ │Claude  │  │
              │  │3.5     │ │3.5     │ │3.5     │  │
              │  │Sonnet  │ │Sonnet  │ │Sonnet  │  │
              │  └────────┘ └────────┘ └────────┘  │
              └────────────────────────────────────┘
                                │
         ┌──────────────────────┼──────────────────────────┐
         │                      │                          │
┌────────▼────────┐  ┌──────────▼──────────┐  ┌───────────▼──────────┐
│   DynamoDB      │  │  Bedrock KB          │  │  Amazon Location     │
│                 │  │  + OpenSearch        │  │  Service             │
│ nutriroute-     │  │  Serverless          │  │                      │
│   users         │  │                      │  │ • Maps               │
│ nutriroute-     │  │ USDA Nutrition Data  │  │ • Route Calculator   │
│   food-sources  │  │ SNAP Guidelines      │  │ • Place Index        │
│ nutriroute-     │  │ Dietary Guidelines   │  │ • Geofencing         │
│   inventory     │  │ Food Safety Rules    │  │                      │
│ nutriroute-     │  │                      │  │                      │
│   trust-scores  │  │                      │  │                      │
│ nutriroute-     │  │                      │  │                      │
│   nutri-scores  │  │                      │  │                      │
└─────────────────┘  └─────────────────────┘  └──────────────────────┘
         │
┌────────▼────────┐  ┌─────────────────────┐  ┌──────────────────────┐
│  ElastiCache    │  │        S3            │  │    Rekognition       │
│  Redis          │  │                      │  │                      │
│                 │  │ • food-images/       │  │ FoodLens CV:         │
│ Real-time stock │  │ • meal-plans/        │  │ Detect ingredients   │
│ caching 6hr TTL │  │ • usda-docs/         │  │ from fridge photos   │
│                 │  │ • user-uploads/      │  │                      │
└─────────────────┘  │ • pantry-photos/     │  │ Trust Verification:  │
                     └─────────────────────┘  │ Verify pantry stock  │
                                               │ photos from users    │
                                               └──────────────────────┘
         │
┌────────▼────────┐  ┌─────────────────────┐  ┌──────────────────────┐
│   Transcribe    │  │       Polly          │  │     Translate        │
│                 │  │                      │  │                      │
│ Voice → Text    │  │ Text → Voice         │  │ EN ↔ ES + 10 langs  │
│ EN + ES input   │  │ EN + ES output       │  │                      │
└─────────────────┘  └─────────────────────┘  └──────────────────────┘
         │
┌────────▼────────┐  ┌─────────────────────┐
│  EventBridge    │  │     SNS + SES        │
│                 │  │                      │
│ Scheduled jobs: │  │ Push notifications:  │
│ • Pantry checks │  │ • Pantry restocked   │
│ • Stock sync    │  │ • SNAP balance low   │
│ • Alert trigger │  │ • New food source    │
│ • Score refresh │  │ • Weekly NutriScore  │
└─────────────────┘  └─────────────────────┘
         │
┌────────▼────────┐  ┌─────────────────────┐
│  CloudWatch     │  │      X-Ray           │
│                 │  │                      │
│ • Logs          │  │ Distributed tracing  │
│ • Metrics       │  │ across all Lambdas   │
│ • Alarms        │  │ and Bedrock agents   │
│ • Dashboards    │  │                      │
└─────────────────┘  └─────────────────────┘
```

---

## Bedrock Agent Architecture (Deep Dive)

```
USER QUERY
"Family of 4, Detroit 48201, $180 SNAP, no car, lactose intolerant daughter"
                              │
                              ▼
                    ┌─────────────────┐
                    │ SUPERVISOR AGENT│
                    │                 │
                    │ 1. Parse intent │
                    │ 2. Extract:     │
                    │    - location   │
                    │    - budget     │
                    │    - family size│
                    │    - dietary    │
                    │    - transport  │
                    │ 3. Route to     │
                    │    sub-agents   │
                    │ 4. Synthesize   │
                    │    response     │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │ (parallel)      │ (parallel)      │ (parallel)
           ▼                 ▼                 ▼
  ┌────────────────┐ ┌───────────────┐ ┌──────────────────┐
  │ FOODFINDER     │ │ MEALPLANNER   │ │ ROUTEOPTIMIZER   │
  │ AGENT          │ │ AGENT         │ │ AGENT            │
  │                │ │               │ │                  │
  │ Action Groups: │ │ Action Groups:│ │ Action Groups:   │
  │ • search_food_ │ │ • generate_   │ │ • calculate_     │
  │   sources      │ │   meal_plan   │ │   route          │
  │ • check_stock  │ │ • optimize_   │ │ • get_transit_   │
  │ • get_hours    │ │   snap_budget │ │   schedule       │
  │ • verify_snap_ │ │ • calculate_  │ │ • multi_stop_    │
  │   acceptance   │ │   nutrition   │ │   optimize       │
  │                │ │ • dietary_    │ │ • estimate_      │
  │ Data Sources:  │ │   filter      │ │   travel_time    │
  │ • 211.org API  │ │               │ │                  │
  │ • USDA Atlas   │ │ Data Sources: │ │ Data Sources:    │
  │ • DynamoDB     │ │ • Bedrock KB  │ │ • Location Svc   │
  │ • ElastiCache  │ │ • Open Food   │ │ • GTFS Transit   │
  │                │ │   Facts API   │ │ • DynamoDB       │
  └────────────────┘ └───────────────┘ └──────────────────┘
           │                 │                 │
           └─────────────────┼─────────────────┘
                             │
                    ┌────────▼────────┐
                    │ SUPERVISOR      │
                    │ SYNTHESIZES     │
                    │                 │
                    │ Unified JSON    │
                    │ response with:  │
                    │ • food_sources[]│
                    │ • meal_plan{}   │
                    │ • route{}       │
                    │ • savings{}     │
                    │ • alerts[]      │
                    └─────────────────┘
                             │
                    ┌────────▼────────┐
                    │ BEDROCK         │
                    │ GUARDRAILS      │
                    │                 │
                    │ • Safe content  │
                    │ • No medical    │
                    │   advice        │
                    │ • No PII leak   │
                    └─────────────────┘
                             │
                    RESPONSE TO USER
                    < 8 seconds total
```

---

## FoodLens Computer Vision Flow

```
USER OPENS CAMERA
        │
        ▼
React Native Camera Component
        │
        ▼
Image captured → Base64 encoded
        │
        ▼
API Gateway → foodlens-lambda
        │
        ▼
S3 PutObject (user-uploads/[userId]/[timestamp].jpg)
        │
        ▼
Rekognition DetectLabels
        │
        ▼
Labels filtered for food items:
["eggs", "rice", "onion", "canned beans", "milk"]
        │
        ▼
Bedrock MealPlanner Agent
"Generate 3 meals using ONLY: eggs, rice, onion, canned beans"
        │
        ▼
Response:
{
  "meals": [
    {"name": "Bean & Egg Fried Rice", "time": "15min", "nutrition": 87},
    {"name": "Onion Egg Scramble", "time": "10min", "nutrition": 72},
    {"name": "Rice & Bean Bowl", "time": "12min", "nutrition": 91}
  ],
  "message": "You already have dinner. Here's how to make it."
}
```

---

## Predictive Alert Flow

```
EventBridge Scheduler (every 30 minutes)
        │
        ▼
inventory-updater Lambda
        │
        ├── Fetch 211.org API for stock updates
        ├── Compare with DynamoDB cached values
        │
        ▼
Stock change detected?
        │
   YES  │  NO
        │   └── Exit (no alert needed)
        ▼
Find users within 2 miles (Location Service Geofencing)
        │
        ▼
Filter: users who have this food source saved
        │
        ▼
SNS Push Notification:
"St. Mary's Pantry just restocked fresh produce —
 only 40 portions available.
 Bus route 14 gets there in 22 minutes.
 Want me to plan your trip?"
        │
        ▼
User taps notification → RouteOptimizer Agent fires
```

---

## Offline PWA Architecture

```
ONLINE MODE                    OFFLINE MODE
     │                              │
     ▼                              ▼
API Gateway                  Service Worker
     │                         (Amplify)
     ▼                              │
Lambda + Bedrock             IndexedDB Cache
     │                              │
     ▼                              ▼
Fresh data                   Last session data:
returned                     • meal_plan
                             • food_sources
                             • route
                             • shopping_list
                                    │
                                    ▼
                             "You're offline.
                              Showing your last
                              saved plan from
                              2 hours ago."
                                    │
                             When online again:
                             Auto-sync + refresh
```

---

## DynamoDB Table Schemas

### nutriroute-users
```
PK: userId (String)          — Cognito sub
SK: profileType (String)     — "profile" | "preferences" | "history"
Attributes:
  zipCode, familySize, snapBalance, snapRenewalDate,
  dietaryRestrictions[], transportMode, language,
  savedFoodSources[], notificationsEnabled
```

### nutriroute-food-sources
```
PK: zipCode (String)         — "48201"
SK: sourceId (String)        — "foodbank#stmarys#detroit"
GSI1: byType-index           — PK: sourceType, SK: zipCode
GSI2: byTrust-index          — PK: zipCode, SK: trustScore
Attributes:
  name, address, lat, lng, phone, hours{},
  sourceType (foodBank|store|pantry|fridge|market),
  snapAccepted, wicAccepted, trustScore, lastVerified
```

### nutriroute-inventory
```
PK: sourceId (String)
SK: itemCategory (String)    — "produce" | "protein" | "dairy" | "grain"
TTL: expiresAt               — auto-expire stale data after 6 hours
Attributes:
  items[], stockLevel (high|medium|low|empty),
  lastUpdated, verifiedBy, photoUrl
```

### nutriroute-trust-scores
```
PK: sourceId (String)
SK: date (String)            — "2026-09-15"
Attributes:
  score (0-100), verificationCount, accuracyRate,
  communityReports[], lastCalculated
```

### nutriroute-nutri-scores
```
PK: userId (String)
SK: weekOf (String)          — "2026-09-08"
Attributes:
  score (0-100), mealsLogged, vegetableServings,
  proteinServings, snapSaved, improvementVsPrevWeek
```

---

## API Endpoints

```
POST /query              — Main supervisor agent query
POST /foodlens           — FoodLens image analysis
POST /voice              — Voice query (audio → response)
GET  /sources/{zipCode}  — Get food sources for zip
GET  /route              — Get optimized route
GET  /mealplan           — Get current meal plan
POST /inventory/update   — NGO updates stock (admin)
GET  /impact/{zipCode}   — Impact metrics for zip
GET  /alerts             — Get user's active alerts
POST /alerts/subscribe   — Subscribe to pantry alerts
```

---

## Security Architecture

```
• Cognito JWT tokens on all API calls
• WAF rules: rate limiting, SQL injection, XSS protection
• Bedrock Guardrails: no medical advice, no PII in responses
• S3 bucket policies: private, presigned URLs only
• DynamoDB: per-user data isolation via partition key
• Lambda: least-privilege IAM roles per function
• Secrets Manager: all API keys (211.org, Open Food Facts)
• VPC: ElastiCache in private subnet
• CloudTrail: all API calls logged for audit
```
