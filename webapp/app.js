// Helios Underwriting Workbench
// Communicates with the four backend services to provide a complete UI.

const SUBMISSION_URL = "http://localhost:8001";
const RISK_URL = "http://localhost:8002";
const PRICING_URL = "http://localhost:8003";
const POLICY_URL = "http://localhost:8004";
const RAG_URL = "http://localhost:8005";

// === STATE ===
let state = {
  submissions: [],
  selectedId: null,
  selectedSubmission: null,
  underwriting: null, // { triage, assessment, pricing }
  similarPolicies: [],
  pollTimer: null,
  currentTaskId: null,
  existingQuote: null,
  existingPolicy: null,
};

// === HELPERS ===
const fmt = {
  currency: (amount, currency = "GBP") => {
    const num = typeof amount === "string" ? parseFloat(amount) : amount;
    return new Intl.NumberFormat("en-GB", {
      style: "currency",
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(num);
  },
  number: (n) => new Intl.NumberFormat("en-GB").format(n),
  status: (s) => s.replace(/_/g, " "),
};

function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "className") node.className = value;
    else if (key === "html") node.innerHTML = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2).toLowerCase(), value);
    else node.setAttribute(key, value);
  }
  for (const child of children) {
    if (child == null) continue;
    if (typeof child === "string") node.appendChild(document.createTextNode(child));
    else node.appendChild(child);
  }
  return node;
}

function toast(message, type = "success") {
  const t = el("div", { className: `toast ${type}` }, message);
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

async function api(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text || res.statusText}`);
  }
  return res.json();
}

// Convert a persisted assessment + triage into the same shape as the async-task result
// so the same renderer can be used.
function buildUnderwritingFromPersisted(triage, assessment) {
  if (!triage) return null;
  const u = {
    triage: {
      decision: triage.decision,
      confidence: triage.confidence,
      reasoning: triage.reasoning,
      appetite_matches: triage.appetite_matches,
      appetite_concerns: triage.appetite_concerns,
    },
  };
  if (assessment) {
    u.assessment = {
      risk_band: assessment.risk_band,
      risk_score: assessment.risk_score,
      factors: assessment.factors,
      summary: assessment.summary,
    };
  }
  return u;
}

// === SERVICE STATUS ===
async function checkServices() {
  const services = [
    { name: "submission", url: `${SUBMISSION_URL}/health` },
    { name: "risk", url: `${RISK_URL}/health` },
    { name: "pricing", url: `${PRICING_URL}/health` },
    { name: "policy", url: `${POLICY_URL}/health` },
    { name: "rag", url: `${RAG_URL}/health` },
  ];
  const container = document.getElementById("serviceStatus");
  container.innerHTML = "";
  for (const svc of services) {
    let ok = false;
    try {
      const res = await fetch(svc.url);
      ok = res.ok;
    } catch (e) {}
    const pill = el(
      "span",
      { className: "service-pill" },
      el("span", { className: `dot ${ok ? "ok" : "error"}` }),
      svc.name,
    );
    container.appendChild(pill);
  }
}

// === SUBMISSIONS LIST ===
async function loadSubmissions() {
  try {
    const data = await api(`${SUBMISSION_URL}/v1/submissions?limit=100`);
    state.submissions = data.items;
    renderSubmissionList();
  } catch (e) {
    toast(`Failed to load submissions: ${e.message}`, "error");
  }
}

function renderSubmissionList() {
  document.getElementById("submissionCount").textContent = state.submissions.length;
  const list = document.getElementById("submissionList");
  list.innerHTML = "";

  for (const s of state.submissions) {
    const item = el(
      "div",
      {
        className: `submission-item ${state.selectedId === s.id ? "selected" : ""}`,
        onclick: () => selectSubmission(s.id),
      },
      el("div", { className: "ref" }, s.reference),
      el("div", { className: "name" }, s.insured_name),
      el(
        "div",
        { className: "meta" },
        el("span", {}, `${s.fleet_size} vehicles`),
        el("span", {}, fmt.currency(s.total_fleet_value, s.currency)),
      ),
      el("span", { className: `status-badge status-${s.status}` }, fmt.status(s.status)),
    );
    list.appendChild(item);
  }
}

// === SUBMISSION DETAIL ===
async function selectSubmission(id) {
  state.selectedId = id;
  state.underwriting = null;
  state.similarPolicies = [];
  state.currentTaskId = null;
  state.existingQuote = null;
  state.existingPolicy = null;
  if (state.pollTimer) {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
  renderSubmissionList();

  try {
    const submission = await api(`${SUBMISSION_URL}/v1/submissions/${id}`);
    state.selectedSubmission = submission;

    // Hydrate persisted underwriting state in parallel
    const [triage, assessment, quotes] = await Promise.all([
      api(`${RISK_URL}/v1/risk/${id}/triage`).catch(() => null),
      api(`${RISK_URL}/v1/risk/${id}/assessment`).catch(() => null),
      api(`${PRICING_URL}/v1/quotes/by-submission/${id}`).catch(() => []),
    ]);

    state.underwriting = buildUnderwritingFromPersisted(triage, assessment);

    // If there are quotes, take the most recent (first in the list)
    if (quotes && quotes.length > 0) {
      state.existingQuote = quotes[0];

      // We don't store pricing rationale on the quote in same shape; reconstruct enough
      // to display the pricing card from the persisted data
      if (!state.underwriting) state.underwriting = {};
      state.underwriting.pricing = {
        premium_amount: state.existingQuote.premium.amount.toString(),
        premium_currency: state.existingQuote.premium.currency,
        base_premium_amount: state.existingQuote.premium.amount.toString(),
        risk_loading_pct: 0,
        rationale: state.existingQuote.rationale,
      };

      // Check if a policy was bound from this quote
      const policy = await api(`${POLICY_URL}/v1/policies/by-quote/${state.existingQuote.id}`).catch(
        () => null,
      );
      if (policy) state.existingPolicy = policy;
    }

    renderMain();
    loadSimilarPolicies(id);
  } catch (e) {
    toast(`Failed to load submission: ${e.message}`, "error");
  }
}

function renderMain() {
  const main = document.getElementById("main");
  main.innerHTML = "";
  const s = state.selectedSubmission;
  if (!s) return;

  // Header
  const header = el(
    "div",
    { className: "detail-header" },
    el("div", { className: "ref" }, s.reference),
    el("h1", {}, s.insured_name),
    el("div", { style: "color: var(--text-muted); font-size: 13px;" }, s.business_description),
    renderActionButtons(s),
  );
  main.appendChild(header);

  // Submission overview card
  main.appendChild(renderOverviewSection(s));

  // Workflow section
  main.appendChild(renderWorkflowSection(s));

  // Fleet detail
  main.appendChild(renderFleetSection(s));
}

function renderActionButtons(s) {
  const actions = el("div", { className: "actions" });

  const hasUnderwriting = state.underwriting && state.underwriting.triage;
  const declined = hasUnderwriting && state.underwriting.triage.decision === "decline";
  const hasQuote = !!state.existingQuote;
  const hasPolicy = !!state.existingPolicy;

  // "Run AI underwriting" button
  // - Always show, but label changes if we already have results
  const runLabel = hasUnderwriting ? "↻ Re-run AI underwriting" : "▶ Run AI underwriting";
  const runBtn = el(
    "button",
    {
      className: hasUnderwriting ? "btn secondary" : "btn",
      onclick: () => runUnderwriting(s.id),
      id: "runBtn",
    },
    runLabel,
  );
  actions.appendChild(runBtn);

  // Quote / PDF / Bind buttons depending on state
  if (state.underwriting && state.underwriting.pricing && !hasQuote && !declined) {
    actions.appendChild(
      el(
        "button",
        {
          className: "btn secondary",
          onclick: () => createQuote(s.id),
        },
        "Create quote",
      ),
    );
  }

  if (hasQuote) {
    actions.appendChild(
      el(
        "button",
        {
          className: "btn secondary",
          onclick: () => window.open(`${PRICING_URL}/v1/quotes/${state.existingQuote.id}/pdf`, "_blank"),
        },
        `📄 Download ${state.existingQuote.quote_reference}.pdf`,
      ),
    );

    if (!hasPolicy) {
      actions.appendChild(
        el(
          "button",
          {
            className: "btn success",
            onclick: () => bindPolicy(state.existingQuote.id),
          },
          "Bind policy",
        ),
      );
    }
  }

  if (hasPolicy) {
    actions.appendChild(
      el(
        "div",
        {
          style:
            "padding: 10px 16px; background: rgba(63, 185, 80, 0.15); color: var(--green); border-radius: var(--radius); font-size: 13px; font-weight: 500;",
        },
        `✓ Bound: ${state.existingPolicy.policy_number}`,
      ),
    );
  }

  return actions;
}

function renderOverviewSection(s) {
  const totalDrivers = s.drivers.length;
  const avgExp = totalDrivers
    ? (s.drivers.reduce((a, d) => a + d.years_licensed, 0) / totalDrivers).toFixed(1)
    : 0;

  return el(
    "div",
    { className: "section" },
    el("div", { className: "section-title" }, "Risk overview"),
    el(
      "div",
      { className: "card" },
      el(
        "div",
        { className: "kv-grid" },
        kv("Annual revenue", fmt.currency(s.annual_revenue.amount, s.annual_revenue.currency), true),
        kv("Fleet size", `${s.fleet_size} vehicles`, true),
        kv("Total fleet value", fmt.currency(s.total_fleet_value, s.annual_revenue.currency)),
        kv("Drivers", `${totalDrivers} (avg ${avgExp}y experience)`),
        kv("Coverage", s.requested_coverage.coverage_type.replace(/_/g, " ")),
        kv("Period", `${s.requested_coverage.period.start} → ${s.requested_coverage.period.end}`),
        kv("Claims (5y)", `${s.claims_count_5y} totalling ${fmt.currency(s.claims_value_5y.amount, s.claims_value_5y.currency)}`),
        kv("Operations", s.operates_internationally ? "International" : "UK only"),
      ),
    ),
  );
}

function kv(label, value, large = false) {
  return el(
    "div",
    {},
    el("div", { className: "kv-label" }, label),
    el("div", { className: `kv-value ${large ? "large" : ""}` }, value),
  );
}

function renderWorkflowSection(s) {
  const section = el(
    "div",
    { className: "section" },
    el("div", { className: "section-title" }, "Underwriting workflow"),
  );

  const u = state.underwriting;

  // Triage step
  section.appendChild(renderTriageStep(u));

  // Assessment step (skip if declined)
  if (!u || u.triage?.decision !== "decline") {
    section.appendChild(renderAssessmentStep(u));
  }

  // Pricing step (skip if declined)
  if (!u || u.triage?.decision !== "decline") {
    section.appendChild(renderPricingStep(u));
  }

  return section;
}

function renderTriageStep(u) {
  const triage = u?.triage;
  const stepClass = triage
    ? triage.decision === "decline"
      ? "declined"
      : "complete"
    : state.currentTaskId
    ? "active"
    : "";

  const card = el("div", { className: `agent-step ${stepClass}` });
  card.appendChild(el("div", { className: `agent-icon ${stepClass}` }, "1"));

  const body = el(
    "div",
    { className: "agent-body" },
    el("div", { className: "agent-name" }, "Triage agent"),
    el(
      "div",
      { className: "agent-status" },
      triage
        ? `Decision made • confidence ${(triage.confidence * 100).toFixed(0)}%`
        : state.currentTaskId
        ? "Running…"
        : "Awaiting underwriting run",
    ),
  );

  if (triage) {
    const decisionMap = {
      accept: "decision-accept",
      refer: "decision-refer",
      decline: "decision-decline",
    };
    const result = el("div", { className: "agent-result" });
    result.appendChild(
      el(
        "div",
        {},
        el("span", { className: `decision ${decisionMap[triage.decision]}` }, triage.decision),
        el("span", { className: "confidence" }, `${(triage.confidence * 100).toFixed(0)}% confidence`),
      ),
    );
    result.appendChild(el("div", { className: "reasoning" }, triage.reasoning));

    if ((triage.appetite_matches?.length || 0) > 0 || (triage.appetite_concerns?.length || 0) > 0) {
      const appetite = el("div", { className: "appetite-list" });
      for (const m of triage.appetite_matches || []) {
        appetite.appendChild(el("div", { className: "item match" }, el("span", {}, m)));
      }
      for (const c of triage.appetite_concerns || []) {
        appetite.appendChild(el("div", { className: "item concern" }, el("span", {}, c)));
      }
      result.appendChild(appetite);
    }
    body.appendChild(result);
  }
  card.appendChild(body);
  return card;
}

function renderAssessmentStep(u) {
  const a = u?.assessment;
  const stepClass = a
    ? "complete"
    : u?.triage && state.currentTaskId
    ? "active"
    : "";

  const card = el("div", { className: `agent-step ${stepClass}` });
  card.appendChild(el("div", { className: `agent-icon ${stepClass}` }, "2"));

  const body = el(
    "div",
    { className: "agent-body" },
    el("div", { className: "agent-name" }, "Risk assessor"),
    el(
      "div",
      { className: "agent-status" },
      a ? `${a.risk_band.toUpperCase()} risk band • score ${a.risk_score.toFixed(1)}/100` : "Awaiting triage",
    ),
  );

  if (a) {
    const result = el("div", { className: "agent-result" });
    result.appendChild(renderRiskBands(a));
    result.appendChild(el("div", { className: "reasoning" }, a.summary));
    result.appendChild(renderFactors(a.factors));
    body.appendChild(result);
  }
  card.appendChild(body);
  return card;
}

function renderRiskBands(a) {
  const bands = ["low", "medium", "high", "extreme"];
  const ranges = ["0–25", "25–50", "50–70", "70+"];
  const grid = el("div", { className: "risk-bands" });
  for (let i = 0; i < bands.length; i++) {
    const isActive = a.risk_band === bands[i];
    const band = el(
      "div",
      { className: `risk-band ${isActive ? "active" : ""} ${bands[i]}` },
      el("div", { className: "risk-band-label" }, bands[i]),
      el("div", { className: "risk-band-score" }, ranges[i]),
    );
    grid.appendChild(band);
  }
  return grid;
}

function renderFactors(factors) {
  const wrap = el("div", { className: "factors" });
  const labels = {
    fleet_size_factor: "Fleet size",
    driver_experience_factor: "Driver experience",
    driver_points_factor: "Driver points",
    claims_history_factor: "Claims history",
    international_operations_factor: "International ops",
    high_risk_vehicle_factor: "High-risk vehicles",
    young_driver_factor: "Young drivers",
  };
  for (const [key, label] of Object.entries(labels)) {
    const value = factors[key] || 0;
    const fillClass =
      value >= 70 ? "extreme" : value >= 50 ? "high" : value >= 25 ? "medium" : "low";
    const row = el(
      "div",
      { className: "factor-row" },
      el("div", { className: "factor-name" }, label),
      el(
        "div",
        { className: "factor-bar" },
        el("div", { className: `factor-fill ${fillClass}`, style: `width: ${value}%` }),
      ),
      el("div", { className: "factor-value" }, value.toFixed(0)),
    );
    wrap.appendChild(row);
  }
  return wrap;
}

function renderPricingStep(u) {
  const p = u?.pricing;
  const stepClass = p ? "complete" : u?.assessment && state.currentTaskId ? "active" : "";

  const card = el("div", { className: `agent-step ${stepClass}` });
  card.appendChild(el("div", { className: `agent-icon ${stepClass}` }, "3"));

  const body = el(
    "div",
    { className: "agent-body" },
    el("div", { className: "agent-name" }, "Pricing agent"),
    el(
      "div",
      { className: "agent-status" },
      p ? `${fmt.currency(p.premium_amount, p.premium_currency)} annual premium` : "Awaiting assessment",
    ),
  );

  if (p) {
    const pricingCard = el("div", { className: "pricing-card" });
    const grid = el(
      "div",
      { className: "pricing-grid" },
      el(
        "div",
        { className: "pricing-col" },
        el("div", { className: "label" }, "Base premium"),
        el("div", { className: "value" }, fmt.currency(p.base_premium_amount, p.premium_currency)),
      ),
      el(
        "div",
        { className: "pricing-col" },
        el("div", { className: "label" }, "Risk loading"),
        el("div", { className: "value" }, `${(p.risk_loading_pct * 100).toFixed(0)}%`),
      ),
      el(
        "div",
        { className: "pricing-col final" },
        el("div", { className: "label" }, "Final premium"),
        el("div", { className: "value" }, fmt.currency(p.premium_amount, p.premium_currency)),
      ),
    );
    pricingCard.appendChild(grid);
    pricingCard.appendChild(el("div", { className: "reasoning" }, p.rationale));
    body.appendChild(pricingCard);
  }
  card.appendChild(body);
  return card;
}

function renderFleetSection(s) {
  const section = el(
    "div",
    { className: "section" },
    el("div", { className: "section-title" }, `Fleet (${s.fleet_size} vehicles)`),
  );
  const card = el("div", { className: "card" });
  const summary = {};
  for (const v of s.vehicles) {
    summary[v.vehicle_type] = (summary[v.vehicle_type] || 0) + 1;
  }
  const lines = Object.entries(summary)
    .map(([type, count]) => `${count}× ${type.replace(/_/g, " ")}`)
    .join(" • ");
  card.appendChild(el("div", { style: "color: var(--text-muted); font-size: 13px;" }, lines));
  card.appendChild(
    el(
      "div",
      { style: "margin-top: 12px; font-size: 12px; color: var(--text-subtle);" },
      `${s.drivers.length} drivers, average experience ${(s.drivers.reduce((a, d) => a + d.years_licensed, 0) / s.drivers.length).toFixed(1)} years`,
    ),
  );
  section.appendChild(card);
  return section;
}

// === ASYNC UNDERWRITING ===
async function runUnderwriting(submissionId) {
  const btn = document.getElementById("runBtn");
  if (!btn) return;
  btn.disabled = true;
  btn.innerHTML = '<span class="loading"></span> Starting…';

  try {
    const result = await api(`${RISK_URL}/v1/risk/${submissionId}/process-async`, {
      method: "POST",
    });
    state.currentTaskId = result.task_id;
    state.underwriting = {};
    state.existingQuote = null; // Will need a fresh quote after re-run
    state.existingPolicy = null;
    renderMain();
    pollTask(result.task_id, submissionId);
    toast("Underwriting started", "success");
  } catch (e) {
    btn.disabled = false;
    btn.innerHTML = "▶ Run AI underwriting";
    toast(`Failed to start: ${e.message}`, "error");
  }
}

function pollTask(taskId, submissionId) {
  if (state.pollTimer) clearInterval(state.pollTimer);
  state.pollTimer = setInterval(async () => {
    try {
      const status = await api(`${RISK_URL}/v1/risk/jobs/${taskId}`);

      if (status.status === "SUCCESS") {
        clearInterval(state.pollTimer);
        state.pollTimer = null;
        state.currentTaskId = null;
        state.underwriting = status.result;
        renderMain();
        loadSubmissions();
        toast("Underwriting complete", "success");
      } else if (status.status === "FAILURE") {
        clearInterval(state.pollTimer);
        state.pollTimer = null;
        state.currentTaskId = null;
        toast(`Underwriting failed: ${status.error}`, "error");
        renderMain();
      }
    } catch (e) {
      console.error("Poll error", e);
    }
  }, 1500);
}

// === SIMILAR POLICIES (RAG) ===
async function loadSimilarPolicies(submissionId) {
  const list = document.getElementById("similarList");
  list.innerHTML = '<div style="padding: 24px; text-align: center;"><span class="loading"></span></div>';

  try {
    const data = await api(`${RAG_URL}/v1/rag/similar/${submissionId}?top_n=5`);
    state.similarPolicies = data.matches;
    renderSimilarPolicies();
  } catch (e) {
    list.innerHTML = `<div style="padding: 24px; color: var(--text-subtle); font-size: 12px;">Failed to load similar policies: ${e.message}</div>`;
  }
}

function renderSimilarPolicies() {
  const list = document.getElementById("similarList");
  list.innerHTML = "";
  for (const match of state.similarPolicies) {
    const p = match.policy;
    const lossRatioClass = p.loss_ratio > 0.7 ? "bad" : p.loss_ratio < 0.4 ? "good" : "";
    const card = el(
      "div",
      { className: "similar-policy" },
      el(
        "div",
        { className: "similarity" },
        `${(match.similarity * 100).toFixed(0)}% match`,
        el("div", { className: "similarity-bar" }, el("div", { className: "similarity-fill", style: `width: ${match.similarity * 100}%` })),
      ),
      el("div", { className: "insured" }, p.insured_name),
      el("div", { className: "desc" }, p.business_description),
      el(
        "div",
        { className: "stats" },
        statRow("Fleet", `${p.fleet_size} ${p.primary_vehicle_type}s`),
        statRow("Risk band", p.risk_band.toUpperCase()),
        statRow("Premium", fmt.currency(p.final_premium)),
        statRow("Loss ratio", `${(p.loss_ratio * 100).toFixed(0)}%`, lossRatioClass),
      ),
      el("div", { className: "notes" }, p.underwriter_notes),
    );
    list.appendChild(card);
  }
  if (state.similarPolicies.length === 0) {
    list.innerHTML = '<div style="padding: 24px; color: var(--text-subtle); font-size: 12px;">No similar policies found.</div>';
  }
}

function statRow(label, value, valueClass = "") {
  return el(
    "div",
    { className: "stat" },
    el("span", { className: "stat-label" }, label),
    el("span", { className: `stat-value ${valueClass}` }, value),
  );
}

// === QUOTE & POLICY ACTIONS ===
async function createQuote(submissionId) {
  const u = state.underwriting;
  if (!u || !u.pricing) return;
  const s = state.selectedSubmission;

  try {
    const quote = await api(`${PRICING_URL}/v1/quotes`, {
      method: "POST",
      body: JSON.stringify({
        submission_id: submissionId,
        premium: { amount: u.pricing.premium_amount, currency: u.pricing.premium_currency },
        excess: { amount: "500.00", currency: "GBP" },
        coverage: s.requested_coverage,
        valid_until: new Date(Date.now() + 30 * 86400000).toISOString().split("T")[0],
        rationale: u.pricing.rationale,
      }),
    });
    state.existingQuote = quote;
    toast(`Quote created: ${quote.quote_reference}`, "success");
    renderMain();
  } catch (e) {
    toast(`Failed to create quote: ${e.message}`, "error");
  }
}

async function bindPolicy(quoteId) {
  try {
    const policy = await api(`${POLICY_URL}/v1/policies/bind`, {
      method: "POST",
      body: JSON.stringify({
        quote_id: quoteId,
        bound_by: "underwriter_alice",
      }),
    });
    state.existingPolicy = policy;
    toast(`Policy bound: ${policy.policy_number}`, "success");
    loadSubmissions();
    renderMain();
  } catch (e) {
    toast(`Failed to bind: ${e.message}`, "error");
  }
}

// === STARTUP ===
async function init() {
  await checkServices();
  await loadSubmissions();
  setInterval(checkServices, 30000); // refresh every 30s
}

init();
