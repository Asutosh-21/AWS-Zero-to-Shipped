# NutriRoute AI — Project Plan

## Hackathon: AWS Zero to Shipped | Deadline: October 2, 2026

---

## Evaluation Gates

### Gate 1 — AI + Human Review (Week of Oct 5, 2026)
| Criterion | Weight | Target Score | Strategy |
|-----------|--------|-------------|----------|
| Technical Innovation & Originality | 25% | 25/25 | Multi-agent Bedrock + FoodLens CV + Voice |
| Implementation Quality | 25% | 24/25 | Real data, live demo, offline mode, 20 AWS services |
| Community/Market Impact | 25% | 25/25 | 19M Americans, Spanish voice, USDA real data |
| Creativity & Storytelling | 25% | 24/25 | Detroit mom story, impact dashboard, startup narrative |
| **Projected Total** | | **98/100** | |

### Gate 2 — AWS Expert Panel (Week of Oct 12, 2026)
| Criterion | Weight | Target Score | Strategy |
|-----------|--------|-------------|----------|
| Technical Innovation & Originality | 25% | 25/25 | 8 AWS AI services working together |
| Implementation Quality | 25% | 25/25 | Production-ready, any zip code works live |
| Community/Market Impact | 25% | 25/25 | Measurable pilot data, city gov partnership story |
| Creativity & Storytelling | 25% | 25/25 | 2-min video, human story first, tech second |
| **Projected Total** | | **100/100** | |

---

## 30-Day Build Plan

### Week 1 (Sep 1–7) — Data Foundation
**Goal: Real data flowing into the system**

| Day | Task | Owner | Status |
|-----|------|-------|--------|
| 1 | AWS account setup, IAM roles, Bedrock access enabled | Dev | ⬜ |
| 1 | DynamoDB tables created (users, food-sources, inventory) | Dev | ⬜ |
| 2 | USDA Food Desert Atlas API integration | Dev | ⬜ |
| 2 | 211.org food bank API integration | Dev | ⬜ |
| 3 | Open Food Facts API integration | Dev | ⬜ |
| 3 | Data pipeline: fetch + normalize + store in DynamoDB | Dev | ⬜ |
| 4 | S3 buckets created (images, meal plans, documents) | Dev | ⬜ |
| 4 | Bedrock Knowledge Base created, USDA nutrition PDFs ingested | Dev | ⬜ |
| 5 | OpenSearch Serverless collection created + indexed | Dev | ⬜ |
| 5 | Amazon Location Service: map, route calculator, place index | Dev | ⬜ |
| 6 | ElastiCache Redis cluster for real-time stock caching | Dev | ⬜ |
| 7 | Week 1 review: all data sources live and queryable | Dev | ⬜ |

**Week 1 Deliverable:** Any US zip code returns real food sources from live APIs

---

### Week 2 (Sep 8–14) — Bedrock Agent Core
**Goal: All 4 agents working end-to-end**

| Day | Task | Owner | Status |
|-----|------|-------|--------|
| 8 | FoodFinder Agent created in Bedrock console | Dev | ⬜ |
| 8 | FoodFinder action groups + Lambda handlers | Dev | ⬜ |
| 9 | MealPlanner Agent created + KB connected | Dev | ⬜ |
| 9 | MealPlanner action groups + SNAP logic | Dev | ⬜ |
| 10 | RouteOptimizer Agent created + Location Service connected | Dev | ⬜ |
| 10 | RouteOptimizer action groups + transit logic | Dev | ⬜ |
| 11 | Supervisor Agent created — orchestrates all 3 sub-agents | Dev | ⬜ |
| 11 | Bedrock Guardrails configured for safe responses | Dev | ⬜ |
| 12 | API Gateway REST + WebSocket APIs created | Dev | ⬜ |
| 12 | Cognito user pools + identity pools configured | Dev | ⬜ |
| 13 | End-to-end test: one query → all 3 agents → unified response | Dev | ⬜ |
| 14 | Week 2 review: full agent pipeline working under 8 seconds | Dev | ⬜ |

**Week 2 Deliverable:** Type one query, get food sources + meal plan + route in one response

---

### Week 3 (Sep 15–21) — Power Features
**Goal: The jaw-drop features that win Gate 2**

| Day | Task | Owner | Status |
|-----|------|-------|--------|
| 15 | FoodLens: Rekognition integration + image upload Lambda | Dev | ⬜ |
| 15 | FoodLens: Bedrock generates meal plan from detected ingredients | Dev | ⬜ |
| 16 | Voice input: Amazon Transcribe Lambda handler | Dev | ⬜ |
| 16 | Voice output: Amazon Polly response synthesis | Dev | ⬜ |
| 17 | Multilingual: Amazon Translate EN↔ES + 10 languages | Dev | ⬜ |
| 17 | Predictive alerts: EventBridge scheduler + pantry stock monitor | Dev | ⬜ |
| 18 | Push notifications: SNS + SES alert system | Dev | ⬜ |
| 18 | Community Trust Score: verification logic + DynamoDB scoring | Dev | ⬜ |
| 19 | NutriScore tracker: weekly nutrition trend calculation | Dev | ⬜ |
| 19 | QuickSight dashboard: impact metrics embedded | Dev | ⬜ |
| 20 | Offline PWA: Amplify service workers + local cache sync | Dev | ⬜ |
| 21 | Week 3 review: all 10 features working | Dev | ⬜ |

**Week 3 Deliverable:** FoodLens demo works, voice works in Spanish, alerts fire on restock

---

### Week 4 (Sep 22–30) — Frontend, Polish & Submission
**Goal: Beautiful demo, compelling story, submitted on time**

| Day | Task | Owner | Status |
|-----|------|-------|--------|
| 22 | React Native mobile app: HomeScreen + FoodFinderScreen | Dev | ⬜ |
| 23 | React Native: MealPlanScreen + RouteScreen + FoodLensScreen | Dev | ⬜ |
| 24 | Next.js web admin: NGO dashboard + inventory management | Dev | ⬜ |
| 25 | Amplify deployment: mobile + web live URLs | Dev | ⬜ |
| 25 | CloudFront + WAF configured | Dev | ⬜ |
| 26 | CloudWatch dashboards + X-Ray tracing enabled | Dev | ⬜ |
| 26 | Load test: 100 concurrent users, verify under 8s response | Dev | ⬜ |
| 27 | Record 2-minute demo video (Detroit zip code live demo) | Dev | ⬜ |
| 28 | Write submission story (problem → solution → impact → scale) | Dev | ⬜ |
| 29 | Final review: all features, all links, all screenshots | Dev | ⬜ |
| 30 | Submit before Oct 2, 11:59 PM PT | Dev | ⬜ |

**Week 4 Deliverable:** Live app deployed, video recorded, submission complete

---

## Feature Priority Matrix

```
P0 — MUST SHIP (Gate 1 pass)
├── Natural Language Food Query
├── Real-Time Food Source Finder  
├── SNAP Meal Planner
├── Zero-Car Route Optimizer
└── Community Impact Dashboard

P1 — SHOULD SHIP (Gate 2 win)
├── FoodLens Computer Vision      ← highest impact
├── Voice Interface EN + ES       ← second highest
├── Predictive Pantry Alerts
└── Offline PWA Mode

P2 — NICE TO SHIP (polish)
├── Community Trust Score
└── NutriScore Health Tracker
```

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Bedrock Agent latency > 8s | Medium | High | ElastiCache for frequent queries, async streaming |
| 211.org API rate limits | Medium | Medium | Cache responses in DynamoDB with 6hr TTL |
| Rekognition food accuracy < 80% | Low | Medium | Fallback to manual ingredient entry |
| Amplify build failures | Low | High | Test build pipeline on Day 22, not Day 29 |
| Demo fails during judging | Low | Critical | Pre-recorded backup video ready |

---

## Definition of Done (Ship Gate Checklist)

- [ ] App is publicly accessible via live URL
- [ ] Any US zip code returns real food source data
- [ ] Bedrock multi-agent pipeline responds in under 8 seconds
- [ ] FoodLens works on a real fridge photo
- [ ] Voice query works in English and Spanish
- [ ] Offline mode caches last session
- [ ] Impact dashboard shows real pilot metrics
- [ ] 2-minute demo video uploaded
- [ ] Submission story written with USDA citations
- [ ] All 20 AWS services visible in architecture diagram

---

## Submission Checklist

- [ ] Project name: NutriRoute AI
- [ ] Category: Social Good → Health
- [ ] Lane: Startups
- [ ] Live demo URL: [Amplify URL]
- [ ] GitHub repo: public, clean README
- [ ] Demo video: 2 minutes, Detroit zip code live
- [ ] Architecture diagram: all 20 services labeled
- [ ] Impact metrics: cited, measurable, real
- [ ] Story: problem → solution → impact → scale
