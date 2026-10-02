# NutriRoute AI — AWS Services Map

## All 20 AWS Services — Purpose, Config, Why It Wins

---

## Intelligence Layer (8 Services)

### 1. Amazon Bedrock — Multi-Agent Orchestration
- **Model:** Claude 3.5 Sonnet (best reasoning for complex queries)
- **Agents:** Supervisor + FoodFinder + MealPlanner + RouteOptimizer
- **Knowledge Base:** USDA nutrition data, SNAP guidelines, dietary rules
- **Guardrails:** Block medical advice, protect PII, safe content only
- **Why it wins:** Multi-agent architecture is the most advanced Bedrock pattern in 2026. Most submissions use one chatbot. You use four coordinated agents.

### 2. Amazon Rekognition — FoodLens Computer Vision
- **Use:** DetectLabels on fridge/pantry photos
- **Confidence threshold:** 75% minimum for food items
- **Fallback:** Manual ingredient entry if confidence < 75%
- **Why it wins:** The jaw-drop demo moment. Judges will test this themselves.

### 3. Amazon Transcribe — Voice Input
- **Languages:** en-US, es-US (English + Spanish)
- **Mode:** Streaming transcription for real-time response
- **Use:** Convert voice queries to text before sending to Bedrock
- **Why it wins:** Serves elderly and low-literacy users — the most vulnerable population

### 4. Amazon Polly — Voice Output
- **Voices:** Joanna (EN), Lupe (ES)
- **Format:** MP3 streaming
- **Use:** Convert Bedrock text responses to spoken audio
- **Why it wins:** Completes the voice loop — fully hands-free experience

### 5. Amazon Translate — Multilingual Support
- **Languages:** EN, ES, FR, ZH, AR, PT, VI, KO, TL, HT (10 languages)
- **Use:** Translate queries in → English for Bedrock, translate responses out → user language
- **Why it wins:** 40% of food desert residents are non-English speakers. No other submission covers this.

### 6. Amazon Rekognition (Trust Verification)
- **Use:** Verify community-submitted pantry stock photos
- **Logic:** Detect food items in photo, compare with reported inventory
- **Why it wins:** Solves the #1 reason people don't trust food bank apps

---

## Data Layer (4 Services)

### 7. Amazon DynamoDB — Primary Database
- **Tables:** users, food-sources, inventory, trust-scores, nutri-scores
- **Capacity:** On-demand (auto-scales for demo traffic spikes)
- **TTL:** Inventory items expire after 6 hours (keeps data fresh)
- **GSIs:** byType-index, byTrust-index for fast queries
- **Why it wins:** Serverless, scales to zero cost when not in use, instant at demo time

### 8. Amazon S3 — Object Storage
- **Buckets:** food-images, meal-plans, usda-docs, user-uploads, pantry-photos
- **Access:** Private + presigned URLs for user uploads
- **Lifecycle:** User uploads expire after 24 hours (privacy)
- **Why it wins:** Stores Bedrock Knowledge Base source documents (USDA PDFs)

### 9. Amazon OpenSearch Serverless — Food Search
- **Collection:** nutriroute-food-search
- **Use:** Full-text search across food sources, fuzzy matching on food items
- **Bedrock KB:** Vector store for semantic nutrition search
- **Why it wins:** Enables "find me something like quinoa but cheaper" semantic queries

### 10. Amazon ElastiCache (Redis) — Real-Time Caching
- **Use:** Cache food source stock levels, API responses from 211.org
- **TTL:** 6 hours for stock data, 24 hours for food source metadata
- **Why it wins:** Keeps response time under 8 seconds even under load

---

## Routing & Location (1 Service)

### 11. Amazon Location Service — Maps + Routing
- **Map:** VectorEsriNavigation style
- **Route Calculator:** Esri provider, walking + transit modes
- **Place Index:** Esri, Storage intent (index all food sources)
- **Geofencing:** 2-mile radius alerts around user location
- **Why it wins:** Underused AWS service that visually impresses judges. Real routes, real transit times.

---

## Delivery Layer (5 Services)

### 12. AWS Lambda — All Business Logic
- **Functions:** food-finder, meal-planner, route-optimizer, inventory-updater, voice-handler, foodlens, alert-engine
- **Runtime:** Python 3.12
- **Architecture:** arm64 (Graviton2 — 20% cheaper, faster cold starts)
- **Why it wins:** Fully serverless, zero infrastructure to manage

### 13. Amazon API Gateway — API Layer
- **Type:** REST API + WebSocket API
- **Auth:** Cognito JWT authorizer
- **Rate limiting:** 1000 req/min per user
- **WebSocket:** Real-time agent streaming responses
- **Why it wins:** WebSocket enables streaming Bedrock responses (users see text appear in real-time)

### 14. Amazon CloudFront — Global CDN
- **Origins:** Amplify (frontend), API Gateway (backend)
- **Cache:** Static assets cached at edge
- **WAF:** Attached for DDoS + injection protection
- **Why it wins:** Sub-100ms frontend load time globally

### 15. AWS Amplify — Frontend Hosting
- **Apps:** Mobile (React Native), Web (Next.js admin)
- **CI/CD:** Auto-deploy from GitHub on push
- **Offline:** Service workers for PWA offline mode
- **Why it wins:** Live URL ready in minutes, judges can access immediately

### 16. Amazon Cognito — Authentication
- **User Pools:** Email + phone sign-up
- **Identity Pools:** AWS credentials for S3 uploads
- **MFA:** Optional SMS MFA
- **Why it wins:** Secure, production-ready auth in hours not days

---

## Alerts & Events (2 Services)

### 17. Amazon EventBridge — Event Orchestration
- **Rules:** Pantry stock check every 30 minutes
- **Rules:** SNAP balance reminder 3 days before renewal
- **Rules:** Weekly NutriScore calculation every Sunday
- **Why it wins:** Makes the app proactive, not just reactive

### 18. Amazon SNS + SES — Notifications
- **SNS:** Push notifications to mobile (pantry restocked, new food source)
- **SES:** Email alerts (weekly meal plan, NutriScore report)
- **Why it wins:** Judges receive a live notification during the demo

---

## Monitoring (2 Services)

### 19. Amazon CloudWatch — Observability
- **Logs:** All Lambda functions, API Gateway access logs
- **Metrics:** Agent response time, query volume, error rates
- **Alarms:** Alert if response time > 8 seconds
- **Dashboard:** Real-time system health visible during demo
- **Why it wins:** Shows production-readiness, not just a prototype

### 20. AWS X-Ray — Distributed Tracing
- **Tracing:** End-to-end trace from API Gateway → Lambda → Bedrock → DynamoDB
- **Service Map:** Visual map of all service dependencies
- **Why it wins:** AWS judges love seeing X-Ray service maps — shows architectural maturity

---

## Service Cost Estimate (Hackathon Period)

| Service | Monthly Estimate | Notes |
|---------|-----------------|-------|
| Bedrock (Claude 3.5 Sonnet) | ~$15-30 | ~1000 queries during dev + demo |
| Lambda | ~$0 | Free tier covers hackathon usage |
| DynamoDB | ~$0 | On-demand, free tier |
| S3 | ~$1 | Storage + requests |
| Location Service | ~$5 | Map tiles + routing |
| Rekognition | ~$2 | ~200 image analyses |
| Transcribe | ~$2 | ~100 voice queries |
| Polly | ~$1 | ~100 voice responses |
| ElastiCache | ~$15 | t3.micro instance |
| OpenSearch Serverless | ~$10 | Minimum OCU |
| CloudFront | ~$0 | Free tier |
| Amplify | ~$0 | Free tier |
| Cognito | ~$0 | Free tier |
| EventBridge | ~$0 | Free tier |
| SNS/SES | ~$1 | Low volume |
| **Total** | **~$52/month** | Well within hackathon budget |

---

## AWS Console Setup Order

```
Day 1:  IAM → Roles + Policies
Day 1:  DynamoDB → 5 tables
Day 2:  S3 → 5 buckets
Day 2:  Cognito → User Pool + Identity Pool
Day 3:  Bedrock → Enable Claude 3.5 Sonnet access
Day 3:  Bedrock → Knowledge Base + OpenSearch Serverless
Day 4:  Location Service → Map + Route Calculator + Place Index
Day 5:  Lambda → 7 functions
Day 5:  API Gateway → REST + WebSocket APIs
Day 6:  Bedrock → 4 Agents (FoodFinder, MealPlanner, RouteOpt, Supervisor)
Day 7:  ElastiCache → Redis cluster
Day 8:  Rekognition → No setup needed (API-based)
Day 8:  Transcribe + Polly + Translate → No setup needed (API-based)
Day 9:  EventBridge → 3 scheduled rules
Day 9:  SNS → Topics + subscriptions
Day 10: CloudFront → Distribution
Day 10: Amplify → Connect GitHub repo
Day 11: CloudWatch → Dashboards + Alarms
Day 11: X-Ray → Enable on all Lambdas
Day 12: WAF → Attach to CloudFront
```
