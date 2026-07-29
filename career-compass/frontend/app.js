// ---------------------------------------------------------------------
// Config — point this at your Render backend once deployed.
// While developing locally, the FastAPI server default (uvicorn) is used.
// ---------------------------------------------------------------------
const API_BASE = (() => {
  const isLocal = ["localhost", "127.0.0.1"].includes(window.location.hostname);
  if (isLocal) return "http://localhost:8000";
  // 👉 Replace this with your deployed Render URL after `render deploy`,
  //    e.g. "https://career-compass-api.onrender.com"
  return "https://career-compass-api.onrender.com";
})();

// Compass needle angle (degrees) per routed category — N/E/S/W.
const CATEGORY_ANGLE = {
  engineering_tech: 0,
  business_management: 90,
  medical_health: 180,
  arts_humanities: 270,
};

const form = document.getElementById("career-form");
const degreeSelect = document.getElementById("degree-select");
const degreeCustom = document.getElementById("degree-custom");
const errorBox = document.getElementById("error-box");
const submitBtn = document.getElementById("submit-btn");
const btnText = document.getElementById("btn-text");
const formCard = document.getElementById("form-card");
const resultCard = document.getElementById("result-card");
const needle = document.getElementById("needle");

// Sprinkle a few faint ambient stars
(function scatterStars() {
  const field = document.getElementById("stars");
  const count = 60;
  for (let i = 0; i < count; i++) {
    const s = document.createElement("span");
    s.style.left = Math.random() * 100 + "%";
    s.style.top = Math.random() * 100 + "%";
    s.style.opacity = (Math.random() * 0.4 + 0.05).toFixed(2);
    field.appendChild(s);
  }
})();

// ---------------------------------------------------------------------
// Load the dropdown from the backend's /api/courses endpoint
// ---------------------------------------------------------------------
async function loadCourses() {
  try {
    const res = await fetch(`${API_BASE}/api/courses`);
    if (!res.ok) throw new Error("bad response");
    const data = await res.json();

    const categoryLabels = {
      engineering_tech: "Engineering & Tech",
      business_management: "Business & Management",
      medical_health: "Medical & Health",
      arts_humanities: "Arts & Humanities",
    };

    Object.entries(data.categories).forEach(([cat, courses]) => {
      const group = document.createElement("optgroup");
      group.label = categoryLabels[cat] || cat;
      courses.forEach((c) => {
        const opt = document.createElement("option");
        opt.value = c.degree;
        opt.textContent = `${c.vibe.split(" ")[0] || ""} ${c.degree}`.trim();
        group.appendChild(opt);
      });
      degreeSelect.appendChild(group);
    });
  } catch (err) {
    // Backend not reachable yet (e.g. first local run before starting it) —
    // fail quietly, the free-text field still works.
    console.warn("Could not load course list from API:", err);
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "(Could not load courses — type one below instead)";
    opt.disabled = true;
    degreeSelect.appendChild(opt);
  }
}
loadCourses();

// Selecting from the dropdown clears the custom field, and vice versa,
// so it's always unambiguous which one the user means.
degreeSelect.addEventListener("change", () => {
  if (degreeSelect.value) degreeCustom.value = "";
});
degreeCustom.addEventListener("input", () => {
  if (degreeCustom.value) degreeSelect.value = "";
});

function showError(msg) {
  errorBox.textContent = msg;
  errorBox.hidden = false;
}
function clearError() {
  errorBox.hidden = true;
  errorBox.textContent = "";
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  clearError();

  const name = document.getElementById("name").value.trim();
  const degree = (degreeSelect.value || degreeCustom.value).trim();
  const interests = document.getElementById("interests").value.trim();

  if (!degree) {
    showError("Pick a course from the dropdown or type your own to continue.");
    return;
  }

  submitBtn.disabled = true;
  btnText.textContent = "🧭 Routing to a specialist...";

  try {
    const res = await fetch(`${API_BASE}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name || "Explorer", degree, interests }),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || "The agent couldn't process that — try again.");
    }

    const result = await res.json();
    renderResult(result);
  } catch (err) {
    showError(err.message || "Something went wrong reaching the Career Compass API.");
  } finally {
    submitBtn.disabled = false;
    btnText.textContent = "✨ Chart My Path";
  }
});

function pillify(container, rawText) {
  container.innerHTML = "";
  rawText
    .split(";")
    .map((s) => s.trim())
    .filter(Boolean)
    .forEach((item) => {
      const span = document.createElement("span");
      span.className = "pill";
      span.textContent = item;
      container.appendChild(span);
    });
}

function renderResult(result) {
  document.getElementById("vibe-badge").textContent = result.vibe;
  document.getElementById("result-title").textContent =
    `${result.name}'s route: ${result.category_label}`;
  document.getElementById("result-reasoning").textContent = result.reasoning;

  pillify(document.getElementById("jobs-list"), result.recommendations.jobs);
  pillify(document.getElementById("skills-list"), result.recommendations.skills);
  pillify(document.getElementById("companies-list"), result.recommendations.companies);

  const roadmapList = document.getElementById("roadmap-list");
  roadmapList.innerHTML = "";
  (result.recommendations.roadmap || []).forEach((step) => {
    const li = document.createElement("li");
    li.textContent = step;
    roadmapList.appendChild(li);
  });

  // Point the compass needle at the matched category — the signature moment.
  const angle = CATEGORY_ANGLE[result.category] ?? 0;
  needle.style.transform = `rotate(${angle}deg)`;

  formCard.hidden = true;
  resultCard.hidden = false;
  resultCard.scrollIntoView({ behavior: "smooth", block: "start" });
}

document.getElementById("reset-btn").addEventListener("click", () => {
  resultCard.hidden = true;
  formCard.hidden = false;
  needle.style.transform = "rotate(0deg)";
  form.reset();
  clearError();
});
