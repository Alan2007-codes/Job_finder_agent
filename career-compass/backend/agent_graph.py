"""
Career Compass — AI Job Finder Agent
-------------------------------------
This is the same core idea as the original Colab notebook:

    intake -> router -> (engineering_tech | business_management |
                          medical_health | arts_humanities) -> job_lookup -> END

The graph shape, the node names, and the routing logic are untouched.
What changed: intake no longer blocks on input() (the web frontend supplies
name/degree/interests instead), and job_lookup now also returns a short
"roadmap" and a "vibe" tag pulled straight from the dataset so the frontend
has something fun to render.
"""

import os
import re
import difflib
from typing import TypedDict, Literal

import pandas as pd
from langgraph.graph import StateGraph, END

try:
    from langchain_groq import ChatGroq
    from langchain_core.messages import SystemMessage, HumanMessage
    _GROQ_IMPORT_OK = True
except Exception:  # pragma: no cover - optional dependency at runtime
    _GROQ_IMPORT_OK = False


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------
DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "degree_to_jobs_dataset.csv")
degree_df = pd.read_csv(DATA_PATH)


def list_courses():
    """Return the dataset rows the frontend needs to build its course dropdown."""
    return degree_df[["Degree", "Category", "Vibe"]].to_dict(orient="records")


# ---------------------------------------------------------------------------
# Shared memory (state)
# ---------------------------------------------------------------------------
class JobSeekerState(TypedDict, total=False):
    name: str
    degree: str
    interests: str
    category: str          # Routed category (e.g., engineering_tech)
    reasoning: str
    vibe: str
    recommendations: dict


CATEGORIES = ["engineering_tech", "business_management", "medical_health", "arts_humanities"]

ROUTER_SYSTEM_PROMPT = """You are a career path router. Based on the user's degree,
classify them into EXACTLY ONE of these categories:
- engineering_tech
- business_management
- medical_health
- arts_humanities

Respond with ONLY one word from the list above."""


def _get_llm():
    """Lazily build the Groq LLM client. Returns None if no key is configured,
    so the app still works (with keyword-only routing) if GROQ_API_KEY is unset."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or not _GROQ_IMPORT_OK:
        return None
    try:
        return ChatGroq(model="llama-3.3-70b-versatile", temperature=0, groq_api_key=api_key)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------
def intake_node(state: JobSeekerState) -> JobSeekerState:
    """In the notebook this used input(); here the API layer already supplied
    name / degree / interests, so we just normalize and reset the rest."""
    return {
        "name": (state.get("name") or "Explorer").strip() or "Explorer",
        "degree": (state.get("degree") or "").strip(),
        "interests": (state.get("interests") or "").strip(),
        "category": "",
        "reasoning": "",
        "vibe": "",
        "recommendations": {},
    }


def router_node(state: JobSeekerState) -> JobSeekerState:
    degree_lower = state["degree"].lower()

    if any(kw in degree_lower for kw in
           ["software", "computer", "engineer", " it", "tech", "data science",
            "cyber", "electrical", "mechanical", "civil"]):
        category = "engineering_tech"
    elif any(kw in degree_lower for kw in
             ["business", "mba", "management", "finance", "marketing",
              "economic", "account"]):
        category = "business_management"
    elif any(kw in degree_lower for kw in
             ["medic", "mbbs", "nurs", "health", "pharma", "physio", "biomed"]):
        category = "medical_health"
    elif any(kw in degree_lower for kw in
             ["art", "design", "journal", "literat", "psycholog", "politic",
              "history", "sociol"]):
        category = "arts_humanities"
    else:
        # Ask the LLM for anything ambiguous, falling back gracefully if
        # no GROQ_API_KEY is configured.
        llm = _get_llm()
        if llm is not None:
            response = llm.invoke([
                SystemMessage(content=ROUTER_SYSTEM_PROMPT),
                HumanMessage(content=f"Degree: {state['degree']}\nInterests: {state['interests']}")
            ])
            category = response.content.strip().lower()
        else:
            category = "arts_humanities"

    # Normalize whatever came back (keyword match or LLM) to a graph path
    if "engineering" in category or "tech" in category:
        category = "engineering_tech"
    elif "business" in category or "management" in category:
        category = "business_management"
    elif "medical" in category or "health" in category:
        category = "medical_health"
    else:
        category = "arts_humanities"

    return {
        **state,
        "category": category,
        "reasoning": f"Degree '{state['degree']}' matched to {category.replace('_', ' ').title()}",
    }


def engineering_node(state: JobSeekerState) -> JobSeekerState:
    return {**state, "vibe": "🛠️ Processing for Engineering & Tech roles..."}


def business_node(state: JobSeekerState) -> JobSeekerState:
    return {**state, "vibe": "💼 Processing for Management & Corporate roles..."}


def medical_node(state: JobSeekerState) -> JobSeekerState:
    return {**state, "vibe": "🏥 Processing for Healthcare roles..."}


def arts_node(state: JobSeekerState) -> JobSeekerState:
    return {**state, "vibe": "🎨 Processing for Creative & Social Science roles..."}


def _best_row_for_degree(degree: str):
    """Exact/contains match first (original behaviour), then a fuzzy fallback
    so near-miss spellings from the dropdown or free text still resolve."""
    match = degree_df[degree_df["Degree"].str.contains(re.escape(degree), case=False, na=False)]
    if not match.empty:
        return match.iloc[0], "exact"

    close = difflib.get_close_matches(degree, degree_df["Degree"].tolist(), n=1, cutoff=0.5)
    if close:
        return degree_df[degree_df["Degree"] == close[0]].iloc[0], "fuzzy"

    return None, "none"


def job_lookup_node(state: JobSeekerState) -> JobSeekerState:
    row, match_quality = _best_row_for_degree(state["degree"])

    if row is not None:
        recs = {
            "jobs": row["Suitable_Jobs"],
            "skills": row["Key_Skills"],
            "companies": row["Companies_To_Apply"],
            "roadmap": [step.strip() for step in row["Roadmap"].split("|")],
            "match_quality": match_quality,
        }
        vibe = row["Vibe"]
    else:
        recs = {
            "jobs": "No exact match — but here are general options to explore",
            "skills": "Communication; Adaptability; Digital Literacy; Problem Solving",
            "companies": "Various startups; Local businesses; Remote-first companies",
            "roadmap": [
                "Talk to 3 people already working in a field you admire",
                "Pick one transferable skill and build a small project with it",
                "Try a short online course to test the waters",
            ],
            "match_quality": "none",
        }
        vibe = "🧭 The Explorer"

    return {**state, "recommendations": recs, "vibe": vibe}


def route_decision(state: JobSeekerState) -> Literal[
        "engineering_tech", "business_management", "medical_health", "arts_humanities"]:
    return state["category"]


# ---------------------------------------------------------------------------
# Build and compile the graph (same shape as the notebook)
# ---------------------------------------------------------------------------
builder = StateGraph(JobSeekerState)

builder.add_node("intake", intake_node)
builder.add_node("router", router_node)
builder.add_node("engineering_tech", engineering_node)
builder.add_node("business_management", business_node)
builder.add_node("medical_health", medical_node)
builder.add_node("arts_humanities", arts_node)
builder.add_node("job_lookup", job_lookup_node)

builder.set_entry_point("intake")
builder.add_edge("intake", "router")

builder.add_conditional_edges(
    "router",
    route_decision,
    {
        "engineering_tech": "engineering_tech",
        "business_management": "business_management",
        "medical_health": "medical_health",
        "arts_humanities": "arts_humanities",
    },
)

for node in CATEGORIES:
    builder.add_edge(node, "job_lookup")

builder.add_edge("job_lookup", END)
graph = builder.compile()


# ---------------------------------------------------------------------------
# Public entrypoint used by the API layer
# ---------------------------------------------------------------------------
def run_agent(name: str, degree: str, interests: str = "") -> dict:
    final_state = graph.invoke({"name": name, "degree": degree, "interests": interests})
    return {
        "name": final_state["name"],
        "degree": final_state["degree"],
        "category": final_state["category"],
        "category_label": final_state["category"].replace("_", " ").title(),
        "reasoning": final_state["reasoning"],
        "vibe": final_state["vibe"],
        "recommendations": final_state["recommendations"],
    }


if __name__ == "__main__":
    # Quick manual smoke test: python agent_graph.py
    result = run_agent("Alan", "MBA", "Coding")
    import json
    print(json.dumps(result, indent=2))
