"""
Career Compass API — FastAPI backend for the Job Finder Agent.

Endpoints:
    GET  /health        -> uptime check (used by Render)
    GET  /api/courses   -> list of degrees for the frontend dropdown
    POST /api/analyze   -> runs the LangGraph agent and returns a career report
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent_graph import run_agent, list_courses

app = FastAPI(
    title="Career Compass API",
    description="An AI-powered job finder agent (LangGraph + Groq) that maps a degree to careers.",
    version="1.0.0",
)

# Wide-open CORS so the Vercel-hosted frontend (any subdomain/preview URL)
# can reach this API. Tighten `allow_origins` to your real frontend domain
# once you know it, if you'd like.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    name: str = Field(default="Explorer", max_length=80)
    degree: str = Field(..., min_length=1, max_length=120)
    interests: str = Field(default="", max_length=300)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/courses")
def get_courses():
    """Powers the dropdown on the frontend — grouped by category."""
    courses = list_courses()
    grouped: dict = {}
    for c in courses:
        grouped.setdefault(c["Category"], []).append({"degree": c["Degree"], "vibe": c["Vibe"]})
    return {"categories": grouped}


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    if not req.degree.strip():
        raise HTTPException(status_code=400, detail="Please select or enter a degree/course.")
    try:
        result = run_agent(req.name, req.degree, req.interests)
    except Exception as exc:  # keep the API resilient for a demo/portfolio project
        raise HTTPException(status_code=500, detail=f"Agent failed: {exc}") from exc
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
