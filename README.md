# 🚀 ALIGNA — AI-Powered Talent Scouting & Engagement

ALIGNA is a premium, AI-driven candidate scouting platform designed to help recruiters find the perfect match with speed and precision. By combining **JD Parsing**, **Weighted Candidate Matching**, and **AI-Simulated Engagement**, ALIGNA transforms the hiring pipeline into a data-backed, automated workflow.

---

## 🏗️ Architecture & How It's Made

ALIGNA is built with a modern, high-performance tech stack designed for scalability and seamless AI integration.

### **Frontend: Next.js 15+ & Tailwind CSS v4**
- **UI/UX**: A state-of-the-art "Cyber-Minimalism" dashboard with glassmorphism, smooth animations (Framer Motion), and responsive layouts.
- **Dynamic Backgrounds**: Uses `AuroraBackground` and `LightRays` for a premium, alive feel.
- **Client-Side Simulation**: Interactive engagement modals that display real-time AI-generated chat logs.

### **Backend: FastAPI on Vercel Serverless**
- **Orchestration**: A Python-based FastAPI server acting as the intelligent middleware.
- **AI Layer**: 
  - **Google Gemini 2.0 Flash**: Handles complex reasoning tasks like structured JD parsing from text/PDF and candidate match explainability.
  - **Groq (Llama 3 / Gemma)**: Provides lightning-fast, high-volume chat simulations to predict candidate interest.
- **Data Layer**: MongoDB Atlas for primary storage, with a deterministic JSON fallback for seamless demos.

---

## 🔄 How It Works (The Pipeline)

1.  **Requirement Extraction**: The user provides a Job Description (Paste or PDF). ALIGNA's parsing engine (via Gemini) extracts structured requirements: roles, skills, seniority, and work preferences.
2.  **Multidimensional Matching**: The **Scoring Engine** runs a weighted algorithm comparing the JD against the candidate pool, evaluating skills, experience, location, and work-mode alignment.
3.  **Explainable AI**: Every top match includes a concise, AI-generated justification for *why* that candidate was selected.
4.  **Simulated Interest**: For the top candidates, the user can trigger an **Engagement Simulation**. Groq generates a realistic recruiter-candidate conversation based on the candidate's profile to predict their likely responsiveness and "Hot Lead" status.
5.  **Ranked Shortlist**: Final candidates are ranked into a professional shortlist, ready for CSV export or direct action.

---

## 🛠️ Local Setup & Development

Follow these steps to get ALIGNA running on your local machine.

### **1. Prerequisites**
- **Node.js** (v18+)
- **Python** (3.10+)
- **API Keys**: Google Gemini, Groq, and optionally MongoDB Atlas.

### **2. Environment Configuration**
Copy the example environment file and fill in your keys:
```bash
cp .env.example .env.local
```
Provide your `GEMINI_API_KEY`, `GROQ_API_KEY`, and `MONGODB_URI`.

### **3. Install Dependencies**
```bash
# Frontend
npm install

# Backend (Virtual Environment)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### **4. Run the Application**
You need **two terminals** running:

**Terminal 1 — Backend (FastAPI):**
```bash
source .venv/bin/activate
uvicorn api.index:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — Frontend (Next.js):**
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to see the app in action.

---

## 🚀 Deployment
ALIGNA is optimized for **Vercel**. Both the frontend and the Python backend are deployed as serverless functions.
- **Frontend Build**: `@vercel/next`
- **Backend Build**: `@vercel/python` (from `api/index.py`)
- **API Rewrite**: All `/api/*` requests are routed to the Python function via `vercel.json`.

---

## 📁 Repository Structure
- `/api`: FastAPI backend entry point.
- `/src`: Next.js frontend source (app router, components, styles).
- `/backend`: Legacy scripts and data generation utilities.
- `mock_candidates.json`: Pre-generated dataset for immediate testing.
- `vercel.json`: Configuration for serverless deployment.

---
Built for the **Catalyst** hackathon by **Deccan AI**.
