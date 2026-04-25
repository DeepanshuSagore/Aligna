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
- Next.js
- TypeScript
- Tailwind CSS

## Backend
- FastAPI

## AI Layer
- Gemini API

## Data Layer
1. JSON mock dataset initially
2. Later upgrade to MongoDB or Supabase if needed

## Deployment
- Vercel (frontend)
- Render / Railway (backend)

---

# Product Vision

Paste a JD -> understand needs -> find candidates -> assess interest -> ranked shortlist.

---

# Current Progress Status

## Completed
### Phase 0
- Premium frontend UI
- Frontend/backend shell connected

### Phase 1
- Gemini API configured
- FastAPI backend created
- /parse-jd endpoint built
- JD parser functional

## Current Next Phase
PHASE 6 — UX Polish & Export

---

# Full Development Roadmap

## Phase 0 — Foundation (DONE)
Frontend shell + backend connection.

## Phase 1 — JD Parser (DONE)

## Phase 2 — Candidate Dataset + Matching Engine (DONE)
Create 100–500 realistic candidates.
Compare JD with candidates.
Return top 10.

## Phase 3 — Explainability Layer (DONE)
Show why each candidate was selected.

## Phase 4 — Interest Scoring Agent (DONE)
Simulated outreach chat + interest score.

## Phase 5 — Final Ranking Engine (DONE)
Final Score = 0.7 Match + 0.3 Interest

## Phase 6 — UX Polish
Loading states, charts, export CSV, polish.

## Phase 7 — Judge Wow Features
Voice JD, PDF upload, persona fit, salary prediction.

---

# Backend API Plan

POST /parse-jd
POST /match-candidates
POST /simulate-interest
POST /rank-shortlist

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

1. Paste JD
2. Analyze
3. Show parsed JD
4. Show top candidates
5. Show interest score
6. Export shortlist

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
Continue from current phase.

Current phase:
PHASE 6 — UX Polish & Export

---

# Builder Mindset

Ship fast.
Iterate.
Polish later.
Reliability beats complexity.
