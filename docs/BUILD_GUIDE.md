# NutriRoute AI — Build Guide

## Prerequisites
- AWS Account with Bedrock Claude 3.5 Sonnet access enabled
- Node.js 20+, Python 3.12+, AWS CLI v2 configured
- React Native CLI, Expo CLI
- GitHub account (for Amplify CI/CD)

---

## Phase 1 — AWS Infrastructure Setup

### Step 1: IAM Roles

Create these roles in AWS Console → IAM → Roles:

**nutriroute-lambda-role**
```
Policies to attach:
- AmazonDynamoDBFullAccess
- AmazonS3FullAccess
- AmazonBedrockFullAccess
- AmazonLocationFullAccess
- AmazonRekognitionFullAccess
- AmazonTranscribeFullAccess
- AmazonPollyFullAccess
- AmazonTranslateFullAccess
- AmazonElastiCacheFullAccess
- AmazonSNSFullAccess
- AmazonSESFullAccess
- CloudWatchLogsFullAccess
- AWSXRayDaemonWriteAccess
```

**nutriroute-bedrock-agent-role**
```
Policies to attach:
- AmazonBedrockFullAccess
- AmazonDynamoDBFullAccess
- AWSLambdaRole
```

---

### Step 2: DynamoDB Tables

AWS Console → DynamoDB → Create Table (repeat for each):

```
Table: nutriroute-users
  Partition key: userId (String)
  Sort key: profileType (String)
  Capacity: On-demand
  
Table: nutriroute-food-sources
  Partition key: zipCode (String)
  Sort key: sourceId (String)
  GSI 1: byType-index (PK: sourceType, SK: zipCode)
  GSI 2: byTrust-index (PK: zipCode, SK: trustScore)
  Capacity: On-demand

Table: nutriroute-inventory
  Partition key: sourceId (String)
  Sort key: itemCategory (String)
  TTL attribute: expiresAt
  Capacity: On-demand

Table: nutriroute-trust-scores
  Partition key: sourceId (String)
  Sort key: date (String)
  Capacity: On-demand

Table: nutriroute-nutri-scores
  Partition key: userId (String)
  Sort key: weekOf (String)
  Capacity: On-demand
```

---

### Step 3: S3 Buckets

AWS Console → S3 → Create Bucket (all in us-east-1):

```
nutriroute-food-images        — public-read for verified pantry photos
nutriroute-meal-plans         — private, per-user access
nutriroute-usda-docs          — private, Bedrock KB source
nutriroute-user-uploads       — private, presigned URL access, 24hr lifecycle
nutriroute-pantry-photos      — private, Rekognition input
```

---

### Step 4: Bedrock Knowledge Base

AWS Console → Amazon Bedrock → Knowledge Bases → Create:

```
Name: NutriRouteKnowledgeBase
Embeddings model: Amazon Titan Embeddings V2
Vector store: Create new OpenSearch Serverless collection
  Collection name: nutriroute-food-search

Data source: S3
  Bucket: nutriroute-usda-docs
  
Upload these documents to nutriroute-usda-docs:
  - USDA Dietary Guidelines 2025 (PDF)
  - SNAP Eligible Food Items list (PDF)
  - USDA Food Desert Atlas data (CSV)
  - Open Food Facts nutrition database (JSON)
  
Sync the knowledge base after upload.
```

---

### Step 5: Amazon Location Service

AWS Console → Amazon Location Service:

```
Maps → Create Map:
  Name: nutriroute-map
  Map style: VectorEsriNavigation

Route Calculators → Create:
  Name: nutriroute-router
  Data provider: Esri

Place Indexes → Create:
  Name: nutriroute-places
  Data provider: Esri
  Intent: Storage

Geofence Collections → Create:
  Name: nutriroute-geofences
```

---

### Step 6: Bedrock Agents

AWS Console → Amazon Bedrock → Agents → Create Agent (repeat 4 times):

**Agent 1: NutriRoute-FoodFinder**
```
Model: Claude 3.5 Sonnet
Instructions: (paste from backend/agents/food_finder_agent.py AGENT_INSTRUCTIONS)
Action Groups:
  - Name: FoodSourceActions
    Lambda: food-finder-handler
    Schema: (paste OpenAPI schema from backend/agents/schemas/food_finder_schema.json)
```

**Agent 2: NutriRoute-MealPlanner**
```
Model: Claude 3.5 Sonnet
Instructions: (paste from backend/agents/meal_planner_agent.py AGENT_INSTRUCTIONS)
Knowledge Base: NutriRouteKnowledgeBase
Action Groups:
  - Name: MealPlanActions
    Lambda: meal-planner-handler
    Schema: (paste from backend/agents/schemas/meal_planner_schema.json)
```

**Agent 3: NutriRoute-RouteOptimizer**
```
Model: Claude 3.5 Sonnet
Instructions: (paste from backend/agents/route_optimizer_agent.py AGENT_INSTRUCTIONS)
Action Groups:
  - Name: RouteActions
    Lambda: route-optimizer-handler
    Schema: (paste from backend/agents/schemas/route_optimizer_schema.json)
```

**Agent 4: NutriRoute-Supervisor**
```
Model: Claude 3.5 Sonnet
Instructions: (paste from backend/agents/supervisor_agent.py AGENT_INSTRUCTIONS)
Sub-agents:
  - NutriRoute-FoodFinder (alias: LIVE)
  - NutriRoute-MealPlanner (alias: LIVE)
  - NutriRoute-RouteOptimizer (alias: LIVE)
Guardrails: Create guardrail
  - Block: medical advice, PII, harmful content
  - Allow: food, nutrition, directions, budgeting
```

---

### Step 7: Lambda Functions

AWS Console → Lambda → Create Function (Python 3.12, arm64, nutriroute-lambda-role):

```
food-finder-handler       512MB  30s timeout
meal-planner-handler     1024MB  60s timeout
route-optimizer-handler   512MB  30s timeout
inventory-updater-handler 256MB  60s timeout
voice-handler             512MB  30s timeout
foodlens-handler          512MB  30s timeout
alert-engine-handler      256MB  60s timeout
```

Environment variables for each Lambda:
```
DYNAMODB_TABLE_USERS=nutriroute-users
DYNAMODB_TABLE_SOURCES=nutriroute-food-sources
DYNAMODB_TABLE_INVENTORY=nutriroute-inventory
BEDROCK_AGENT_SUPERVISOR_ID=[from console after agent creation]
BEDROCK_AGENT_SUPERVISOR_ALIAS=LIVE
BEDROCK_KB_ID=[from console after KB creation]
LOCATION_MAP_NAME=nutriroute-map
LOCATION_ROUTER_NAME=nutriroute-router
LOCATION_PLACE_INDEX=nutriroute-places
S3_BUCKET_IMAGES=nutriroute-food-images
S3_BUCKET_UPLOADS=nutriroute-user-uploads
ELASTICACHE_ENDPOINT=[from ElastiCache console]
SNS_TOPIC_ARN=[from SNS console]
```

---

### Step 8: API Gateway

AWS Console → API Gateway → Create API:

**REST API: nutriroute-api**
```
Resources + Methods:
POST /query          → food-finder-handler Lambda
POST /foodlens       → foodlens-handler Lambda
POST /voice          → voice-handler Lambda
GET  /sources/{zip}  → food-finder-handler Lambda
GET  /route          → route-optimizer-handler Lambda
GET  /mealplan       → meal-planner-handler Lambda
POST /inventory      → inventory-updater-handler Lambda
GET  /impact/{zip}   → food-finder-handler Lambda

Authorizer: Cognito JWT (attach to all endpoints)
CORS: Enable for Amplify domain
Deploy to stage: prod
```

**WebSocket API: nutriroute-ws**
```
Routes:
$connect    → auth Lambda
$disconnect → cleanup Lambda
query       → food-finder-handler Lambda (streaming)
```

---

### Step 9: Cognito

AWS Console → Cognito → Create User Pool:
```
Name: nutriroute-users
Sign-in: Email + Phone
Password: 8+ chars, number required
MFA: Optional SMS
App client: nutriroute-mobile (no secret)
App client: nutriroute-web (no secret)
```

Create Identity Pool:
```
Name: nutriroute-identity
User Pool: link to above
Authenticated role: nutriroute-cognito-auth-role
  (allow S3 presigned URL generation for user's own prefix)
```

---

### Step 10: EventBridge Rules

AWS Console → EventBridge → Rules → Create:

```
Rule 1: nutriroute-pantry-check
  Schedule: rate(30 minutes)
  Target: inventory-updater-handler Lambda

Rule 2: nutriroute-snap-reminder
  Schedule: cron(0 9 * * ? *)  [9am daily]
  Target: alert-engine-handler Lambda

Rule 3: nutriroute-nutriscore-weekly
  Schedule: cron(0 8 ? * SUN *)  [8am every Sunday]
  Target: alert-engine-handler Lambda
```

---

### Step 11: SNS Topics

AWS Console → SNS → Create Topic:
```
Name: nutriroute-alerts
Type: Standard
Display name: NutriRoute

Create subscription:
  Protocol: Application (for mobile push)
  Protocol: Email (for weekly reports)
```

---

### Step 12: ElastiCache

AWS Console → ElastiCache → Create:
```
Engine: Redis 7.x
Node type: cache.t3.micro
Replicas: 0 (single node for hackathon)
Subnet group: default VPC
Security group: allow Lambda access on port 6379
```

---

### Step 13: Amplify

AWS Console → Amplify → Create App:
```
Source: GitHub
Repo: your-username/nutriroute-ai
Branch: main
Build settings: auto-detected (Next.js)

Environment variables:
  NEXT_PUBLIC_API_URL=[API Gateway URL]
  NEXT_PUBLIC_WS_URL=[WebSocket API URL]
  NEXT_PUBLIC_COGNITO_USER_POOL_ID=[from Cognito]
  NEXT_PUBLIC_COGNITO_CLIENT_ID=[from Cognito]
  NEXT_PUBLIC_LOCATION_MAP_NAME=nutriroute-map
  NEXT_PUBLIC_LOCATION_API_KEY=[from Location Service]
```

---

### Step 14: CloudFront + WAF

AWS Console → CloudFront → Create Distribution:
```
Origin: Amplify app URL
Cache policy: CachingOptimized for static assets
WAF: Create web ACL
  Rules:
    - AWSManagedRulesCommonRuleSet
    - AWSManagedRulesKnownBadInputsRuleSet
    - Rate limit: 2000 req/5min per IP
```

---

### Step 15: CloudWatch + X-Ray

AWS Console → CloudWatch → Dashboards → Create:
```
Dashboard: NutriRoute-Operations
Widgets:
  - Lambda invocations + errors (all 7 functions)
  - API Gateway request count + latency
  - Bedrock agent response time
  - DynamoDB read/write capacity

Alarms:
  - Agent response time > 8000ms → SNS alert
  - Lambda error rate > 5% → SNS alert
```

AWS Console → X-Ray → Enable on all Lambda functions:
```
Lambda → Configuration → Monitoring → Enable X-Ray tracing
(repeat for all 7 Lambda functions)
```

---

## Phase 2 — Backend Code Deployment

Deploy Lambda code in this order:
```
1. food-finder-handler     (backend/lambdas/food_finder/)
2. meal-planner-handler    (backend/lambdas/meal_planner/)
3. route-optimizer-handler (backend/lambdas/route_optimizer/)
4. inventory-updater-handler (backend/lambdas/inventory_updater/)
5. voice-handler           (backend/lambdas/voice_handler/)
6. foodlens-handler        (backend/lambdas/foodlens/)
7. alert-engine-handler    (backend/lambdas/alert_engine/)
```

Run data pipeline to seed initial data:
```
python backend/data_pipeline/fetch_food_banks.py
python backend/data_pipeline/fetch_usda_data.py
python backend/data_pipeline/sync_inventory.py
```

---

## Phase 3 — Frontend Deployment

```
cd frontend/web
npm install
npm run build
# Push to GitHub → Amplify auto-deploys

cd frontend/mobile
npm install
npx expo build:android
npx expo build:ios
```

---

## Phase 4 — Demo Preparation

1. Test with zip code 48201 (Detroit) — primary demo zip
2. Test with zip code 90011 (Los Angeles) — Spanish demo
3. Test with zip code 60629 (Chicago) — backup demo
4. Record 2-minute video (see demo/DEMO_SCRIPT.md)
5. Take screenshots of all 10 features
6. Export impact metrics from QuickSight dashboard
