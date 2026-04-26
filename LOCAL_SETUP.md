# 🚀 ScoutIQ — Local Setup Guide

> Complete guide to run ScoutIQ on any machine for development & testing.

---

## 📋 Prerequisites

Before you start, make sure you have these installed:

| Tool       | Minimum Version | Check Command        |
|------------|-----------------|----------------------|
| **Node.js**   | v18+            | `node --version`     |
| **npm**       | v9+             | `npm --version`      |
| **Python**    | 3.10+           | `python3 --version`  |
| **Git**       | Any             | `git --version`      |

---

## 📦 Step 1 — Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/scout-iq.git
cd scout-iq
```

---

## 🔑 Step 2 — Set Up Environment Variables

Copy the example file and fill in your API keys:

```bash
cp .env.example .env.local
```

Open `.env.local` and provide:

```env
# Google Gemini API Key — for JD parsing & candidate explainability
# Get yours: https://aistudio.google.com/apikey
GEMINI_API_KEY=your_gemini_api_key

# MongoDB Atlas URI — for the candidate database
# Get yours: https://cloud.mongodb.com
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/?appName=YourApp

# Groq API Key — for fast interest simulation (high rate limits)
# Get yours: https://console.groq.com/keys
GROQ_API_KEY=your_groq_api_key
```

> **Note:** The `.env.local` file is gitignored. Never commit it.

---

## 🌐 Step 3 — Install Frontend Dependencies

```bash
npm install
```

---

## 🐍 Step 4 — Set Up Python Backend

Create a virtual environment and install dependencies:

```bash
# Create virtual environment (from the project root)
python3 -m venv .venv

# Activate it
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate          # Windows

# Install Python dependencies
pip install -r requirements.txt
```

After this, you should see something like:
```
Successfully installed fastapi uvicorn google-generativeai groq motor ...
```

---

## ▶️ Step 5 — Run the Application

You need **two terminals** running simultaneously:

### Terminal 1 — Backend (FastAPI)

```bash
# Make sure virtualenv is activated
source .venv/bin/activate

# Start the backend server
uvicorn api.index:app --host 127.0.0.1 --port 8000 --reload
```

You should see:
```
Groq configured with model: llama-3.3-70b-versatile
Connected to MongoDB Atlas successfully.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Terminal 2 — Frontend (Next.js)

```bash
npm run dev
```

You should see:
```
▲ Next.js 16.x.x
- Local:  http://localhost:3000
```

### ✅ Verify Everything Works

1. Open **http://localhost:3000** in your browser
2. Test the backend: `curl http://127.0.0.1:8000/api/health` → should return `{"status":"healthy"}`
3. Try pasting a sample job description and click "Analyze Candidates"

---

## 🗃️ Candidate Data

The app uses a **fallback hierarchy** for candidate data:

1. **MongoDB Atlas** — if `MONGODB_URI` is set and the `scoutiq.candidates` collection has data
2. **`mock_candidates.json`** — local JSON file with ~150 pre-generated candidates (shipped with repo)

If you don't have MongoDB set up, the app will automatically use the JSON fallback.

### (Optional) Generate New Candidates

```bash
source .venv/bin/activate
cd backend
python generate_candidates.py
```

This uses Gemini to generate 150 realistic candidate profiles into `mock_candidates.json`.

### (Optional) Migrate Candidates to MongoDB

```bash
source .venv/bin/activate
cd backend
pip install pymongo       # sync driver needed for migration script
python migrate_to_mongo.py
```

---

## 🔧 Troubleshooting

### Port 8000 already in use

```bash
# Find what's using port 8000
lsof -i :8000

# Kill it
kill -9 <PID>
```

### `ModuleNotFoundError: No module named 'fastapi'`

You forgot to activate the virtual environment:

```bash
source .venv/bin/activate
```

### `google.generativeai` FutureWarning

This is just a deprecation notice, **not an error**. The library still works. You can ignore it.

### Frontend can't reach backend (API errors)

Make sure:
1. The backend is running on port **8000** (not another port)
2. Both terminals are running simultaneously
3. `next.config.ts` is proxying `/api/*` to `http://127.0.0.1:8000/api/*` in development

### MongoDB connection fails

- Check your `MONGODB_URI` in `.env.local`
- Ensure your IP is whitelisted in MongoDB Atlas (Network Access → Add Current IP)
- The app will fall back to `mock_candidates.json` anyway

---

## 🚀 Deployment (Vercel Serverless)

ScoutIQ is designed for **full-stack deployment on Vercel** — both the Next.js frontend and the Python FastAPI backend run as serverless functions.

### Why Vercel Serverless?

- **Zero cold-start overhead** compared to Render/Railway
- **Single platform** for both frontend and backend
- **Auto-scaling** and global CDN
- **Free tier** sufficient for demos

### Deploy Steps

1. **Push code to GitHub** (make sure `.env.local` is NOT committed)

2. **Import project on Vercel:**
   - Go to [vercel.com/new](https://vercel.com/new)
   - Import your GitHub repo
   - Set root directory to `scout-iq` (if repo root is `Catalyst`)

3. **Add environment variables in Vercel dashboard:**
   - `GEMINI_API_KEY`
   - `MONGODB_URI`
   - `GROQ_API_KEY`

4. **Deploy** — Vercel auto-detects the `vercel.json` config and builds:
   - Frontend → `@vercel/next`
   - Backend → `@vercel/python` (from `api/index.py`)
   - API routes rewrite `/api/*` → Python serverless function

5. **Verify:**
   - Visit your deployment URL
   - Test `https://your-app.vercel.app/api/health`

### `vercel.json` Config (already set up)

```json
{
  "version": 2,
  "builds": [
    { "src": "api/index.py", "use": "@vercel/python" },
    { "src": "package.json", "use": "@vercel/next" }
  ],
  "rewrites": [
    { "source": "/api/:path*", "destination": "/api/index.py" }
  ]
}
```

### Important Notes for Vercel Deployment

- **Python runtime**: Vercel uses Python 3.12 by default. All dependencies from `requirements.txt` are auto-installed.
- **File uploads**: The `/api/upload-jd` endpoint (PDF upload) works in serverless, but has a 4.5MB body limit on Vercel's free tier.
- **CORS**: In production, the frontend and backend are on the same origin — no CORS issues.
- **MongoDB IP Whitelist**: In MongoDB Atlas, add `0.0.0.0/0` to Network Access to allow Vercel's dynamic IPs.

---

## 📁 Project Structure

```
scout-iq/
├── api/
│   └── index.py              # FastAPI backend (Vercel serverless entry)
├── backend/
│   ├── generate_candidates.py # Script to generate mock candidates
│   └── migrate_to_mongo.py    # Script to push candidates to MongoDB
├── src/
│   ├── app/
│   │   ├── layout.tsx         # Root layout with fonts & metadata
│   │   ├── page.tsx           # Main page
│   │   └── globals.css        # Global styles & Tailwind config
│   ├── components/
│   │   ├── Hero.tsx           # Main orchestrator (JD → Match → Engage → Rank)
│   │   ├── JDInputCard.tsx    # JD text/PDF input UI
│   │   ├── JDResults.tsx      # Parsed JD display
│   │   ├── CandidateList.tsx  # Top 10 matched candidates
│   │   ├── EngagementModal.tsx# AI outreach simulation modal
│   │   ├── RankedShortlist.tsx# Final ranked dashboard + CSV export
│   │   ├── PipelineSteps.tsx  # Pipeline progress indicator
│   │   ├── Navbar.tsx         # Navigation bar
│   │   ├── FeatureCards.tsx   # Landing page feature cards
│   │   ├── SkillPills.tsx     # Skill badge component
│   │   └── VideoBackground.tsx# Background video with fade effects
│   └── lib/
│       └── utils.ts           # Utility functions (cn)
├── mock_candidates.json       # Pre-generated candidate dataset
├── requirements.txt           # Python dependencies
├── package.json               # Node.js dependencies & scripts
├── next.config.ts             # Next.js config (API proxy in dev)
├── vercel.json                # Vercel deployment config
├── .env.example               # Template for environment variables
├── .env.local                 # Your actual API keys (gitignored)
├── MASTER_CONTEXT.md          # Project context & roadmap
└── LOCAL_SETUP.md             # ← This file
```

---

## 🧪 API Endpoints

| Method | Endpoint                | Description                                |
|--------|-------------------------|--------------------------------------------|
| GET    | `/api/health`           | Health check                               |
| POST   | `/api/parse-jd`         | Parse job description text via Gemini AI   |
| POST   | `/api/upload-jd`        | Parse PDF job description via Gemini AI    |
| POST   | `/api/match-candidates` | Match & rank candidates against parsed JD  |
| POST   | `/api/simulate-interest`| Simulate AI outreach & score interest      |

---

## 🔄 Quick Start (TL;DR)

```bash
# 1. Clone & enter project
git clone <repo-url> && cd scout-iq

# 2. Set up env
cp .env.example .env.local
# Edit .env.local with your actual API keys

# 3. Install everything
npm install
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# 4. Run (two terminals)
# Terminal 1: source .venv/bin/activate && uvicorn api.index:app --host 127.0.0.1 --port 8000 --reload
# Terminal 2: npm run dev

# 5. Open http://localhost:3000
```
