# MASTER_CONTEXT.md

# ScoutIQ — Hackathon Master Context

## Project Name
ScoutIQ

## Tagline
AI-Powered Talent Scouting & Engagement Agent

## Hackathon / Event
Catalyst by Deccan AI

---

# Core Problem Statement

Recruiters spend hours manually reviewing profiles and chasing candidate interest.

Build an AI agent that:

1. Takes a Job Description (JD) as input  
2. Discovers matching candidates  
3. Engages candidates conversationally (simulated)  
4. Assesses genuine interest  
5. Outputs ranked shortlist with:

- Match Score
- Interest Score
- Final Score

---

# Primary Goal

Create a polished, judge-impressive, end-to-end working AI recruiter product that feels like a real SaaS startup tool.

---

# Judging Criteria Priority

1. Core Agent Quality — 35%
2. End-to-End Working — 20%
3. Output Quality — 20%
4. Technical Implementation — 15%
5. Innovation & Creativity — 10%
6. UX — 5%
7. Clean Code & Documentation — 5%

## Strategy Based on Criteria

Optimize for:

- Reliability
- Strong outputs
- Visible intelligence
- Great UX
- Fast demo wow-factor

---

# Tech Stack

## Frontend
- Next.js 16
- TypeScript
- Tailwind CSS v4

## Backend
- FastAPI (Python)
- Served as Vercel Serverless Functions

## AI Layer
- **Gemini API** (gemini-2.0-flash) — JD parsing & candidate explainability
- **Groq API** (llama-3.3-70b-versatile) — Fast interest simulation (high rate limit)
- Graceful synthetic fallback when both APIs fail

## Data Layer
1. MongoDB Atlas (`scoutiq.candidates` collection)
2. JSON fallback (`mock_candidates.json` — ~150 candidates)

## Deployment
- **Vercel** — Full-stack serverless (both frontend + backend)
- Frontend: `@vercel/next`
- Backend: `@vercel/python` (from `api/index.py`)
- Config: `vercel.json`

---

# Architecture

```
User → Next.js Frontend (Vercel)
         ↓ /api/* requests
       FastAPI Backend (Vercel Serverless Python)
         ↓
       Gemini API / Groq API / MongoDB Atlas
```

## Local Development
- Frontend: `npm run dev` → http://localhost:3000
- Backend: `uvicorn api.index:app --host 127.0.0.1 --port 8000 --reload`
- `next.config.ts` proxies `/api/*` → `http://127.0.0.1:8000/api/*` in dev mode

## Production (Vercel)
- `vercel.json` rewrites `/api/*` → `api/index.py` serverless function
- No CORS issues (same origin)
- Environment variables set in Vercel dashboard

---

# Product Vision

Paste a JD -> understand needs -> find candidates -> assess interest -> ranked shortlist.

---

# Current Progress Status

## Completed
### Phase 0 — Foundation
- Premium frontend UI with glassmorphism design
- Frontend/backend shell connected
- Video background hero section

### Phase 1 — JD Parser
- Gemini API configured
- FastAPI backend created
- `/api/parse-jd` endpoint (text)
- `/api/upload-jd` endpoint (PDF)

### Phase 2 — Candidate Dataset + Matching Engine
- 150 realistic AI-generated candidates
- Scoring engine: skills (60pts) + experience (20pts) + location/role (20pts)
- Returns top 10 matched candidates

### Phase 3 — Explainability Layer
- Gemini generates 1-sentence explanations per candidate
- Shows why each candidate was selected

### Phase 4 — Interest Scoring Agent
- Simulated AI outreach via Groq (primary) / Gemini (fallback)
- 3-message chat simulation
- Interest score (0-100) per candidate
- Graceful synthetic fallback when APIs fail

### Phase 5 — Final Ranking Engine
- Final Score = 0.7 × Match + 0.3 × Interest
- Ranked shortlist dashboard with tier labels (Hot Lead / Warm / Cold)

### Phase 6 — UX Polish & Export
- CSV export for shortlist
- Engage All & Rank flow with progress bar
- Pipeline step indicator
- Loading states and animations

### Phase 7 — Deployment & Documentation
- Vercel serverless configuration (`vercel.json`)
- Local setup documentation (`LOCAL_SETUP.md`)
- Environment variable template (`.env.example`)
- Comprehensive `.gitignore`

## Current Phase
SHIPPED — Ready for demo & deployment

---

# Backend API Endpoints

| Method | Endpoint                | Description                                |
|--------|-------------------------|--------------------------------------------|
| GET    | `/api/health`           | Health check                               |
| POST   | `/api/parse-jd`         | Parse JD text → structured JSON via Gemini |
| POST   | `/api/upload-jd`        | Parse PDF JD → structured JSON via Gemini  |
| POST   | `/api/match-candidates` | Score & rank candidates against parsed JD  |
| POST   | `/api/simulate-interest`| Simulate AI outreach → interest score      |

---

# Candidate Dataset Fields

- name
- role
- skills
- years_experience
- city
- remote_preference
- expected_salary
- education
- last_company
- open_to_work

---

# Demo Strategy

1. Paste JD (or use sample / upload PDF)
2. AI parses and structures JD
3. Show top 10 matched candidates with scores
4. "Engage All & Rank" — AI simulates outreach for all candidates
5. View final ranked shortlist with chat logs
6. Export CSV

---

# Key Files

| File | Purpose |
|------|---------|
| `api/index.py` | FastAPI backend (all endpoints) |
| `src/components/Hero.tsx` | Main orchestrator component |
| `src/components/JDInputCard.tsx` | JD input UI (text + PDF) |
| `src/components/CandidateList.tsx` | Matched candidates display |
| `src/components/EngagementModal.tsx` | Individual engagement modal |
| `src/components/RankedShortlist.tsx` | Final ranked dashboard + CSV |
| `mock_candidates.json` | Fallback candidate dataset |
| `vercel.json` | Vercel deployment config |
| `next.config.ts` | Dev proxy config |
| `.env.example` | Environment variable template |
| `LOCAL_SETUP.md` | Setup instructions |

---

# Environment Variables Required

| Variable | Provider | Purpose |
|----------|----------|---------|
| `GEMINI_API_KEY` | Google AI Studio | JD parsing & explainability |
| `MONGODB_URI` | MongoDB Atlas | Candidate database |
| `GROQ_API_KEY` | Groq Console | Fast interest simulation |

---

# What To Avoid

- Broken flows
- Overengineering
- Slow responses
- Ugly UI
- Too many buggy features

---

# Current Instruction For Any AI Assistant

Read this file first.
The project is SHIPPED and ready for deployment.

Priorities:
1. Keep existing features stable
2. Fix any bugs reported
3. Only add features if explicitly requested

---

# Builder Mindset

Ship fast.
Iterate.
Polish later.
Reliability beats complexity.
