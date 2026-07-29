# 🧭 Career Compass — AI Job Finder Agent

An agentic career advisor built on **LangGraph** + **Groq**. You give it a degree
and a few interests; it routes you through a small state graph — `intake → router →
category specialist → job lookup` — and hands back real jobs, skills, companies,
and a 3-step roadmap for your field.

This repo has three parts, all built from the *same* underlying agent logic:

```
career-compass/
├── notebook/    ← the original Colab notebook, upgraded (still 100% notebook-native)
├── backend/     ← FastAPI wrapper around the LangGraph agent → deploy to Render
└── frontend/    ← dependency-free HTML/CSS/JS UI with a course dropdown → deploy to Vercel
```

The graph shape is untouched from the original: `intake`, `router`,
`engineering_tech`, `business_management`, `medical_health`, `arts_humanities`,
and `job_lookup` are still the seven nodes, wired the same way. What's new is
around the edges: a course **dropdown** (a real `<select>` on the web, a numbered
menu in the notebook), fuzzy matching for near-miss spellings, a 3-step roadmap,
and a "vibe" tag per degree — plus a compass needle on the frontend that
physically rotates to point at your matched category.

---

## 1. Run it locally

**Backend**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate      # optional but recommended
pip install -r requirements.txt
cp .env.example .env                                     # then paste your Groq key into .env
export $(cat .env | xargs)                                # or use python-dotenv / your OS's env vars
uvicorn main:app --reload --port 8000
```
Visit `http://localhost:8000/health` — you should see `{"status":"ok"}`.
Get a free Groq key at https://console.groq.com/keys (the app still works without
one — it just falls back to keyword-only routing for ambiguous degrees).

**Frontend**
```bash
cd frontend
python3 -m http.server 5500
```
Open `http://localhost:5500`. `app.js` auto-detects `localhost` and points at
`http://localhost:8000` — no config needed for local dev.

---

## 2. Deploy the backend to Render

1. Push this repo to GitHub.
2. In Render: **New → Web Service**, connect the repo, and either:
   - let Render auto-detect `backend/render.yaml`, or
   - set manually: **Root Directory** = `backend`, **Build Command** =
     `pip install -r requirements.txt`, **Start Command** =
     `uvicorn main:app --host 0.0.0.0 --port $PORT`.
3. Add an environment variable `GROQ_API_KEY` with your key (mark it as a secret).
4. Deploy. Render gives you a URL like `https://career-compass-api.onrender.com`.
5. Hit `https://<your-render-url>/health` to confirm it's live.

> Free-tier Render services spin down when idle — the first request after a
> quiet period can take ~30s to wake up. That's expected, not a bug.

---

## 3. Deploy the frontend to Vercel

1. Before deploying, open `frontend/app.js` and update the fallback URL in
   `API_BASE` to your actual Render URL:
   ```js
   return "https://career-compass-api.onrender.com"; // ← your real backend URL
   ```
2. In Vercel: **New Project → Import** this repo, set **Root Directory** to
   `frontend`, framework preset **Other** (it's static, no build step).
3. Deploy. Vercel gives you a URL like `https://career-compass.vercel.app`.
4. Back in Render, set `ALLOWED_ORIGINS` to your Vercel URL (instead of `*`)
   to lock down CORS once you know the final domain.

---

## 4. The notebook

`notebook/job_finder_agent_v2.ipynb` is the original Colab flow, upgraded:
- a numbered, category-grouped course menu stands in for a dropdown (Colab's
  `input()` can't render a real `<select>`, so this is the closest notebook-native
  equivalent — the web frontend has an actual dropdown);
- fuzzy matching on the degree lookup;
- a 3-step roadmap and a "vibe" tag in the final printed report.

Upload `notebook/degree_to_jobs_dataset.csv` when the notebook asks for a file.

---

## Dataset

`degree_to_jobs_dataset.csv` (shared by the notebook and the backend) covers 28
degrees across four categories — Engineering & Tech, Business & Management,
Medical & Health, and Arts & Humanities — each with suitable jobs, key skills,
companies to target, a vibe tag, and a 3-step roadmap. Add a row any time you
want to expand the dropdown; no code changes needed.
