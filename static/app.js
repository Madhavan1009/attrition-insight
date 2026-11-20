(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const esc = (t) => String(t).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const NUMS = ["age", "job_level", "monthly_income", "years_at_company", "years_since_promotion", "distance_km", "num_companies_worked"];
  let samples = {};

  async function api(path, options) {
    const res = await fetch(path, options);
    let body = null;
    try { body = await res.json(); } catch (e) { body = null; }
    if (!res.ok) {
      let msg = body && body.detail ? body.detail : "Request failed (" + res.status + ")";
      if (Array.isArray(msg)) msg = msg.map((d) => (d.loc ? d.loc[d.loc.length - 1] + ": " : "") + d.msg).join(" · ");
      const err = new Error(msg); err.status = res.status; throw err;
    }
    return body;
  }

  /* ---------- tabs ---------- */
  $$(".tab").forEach((t) => t.addEventListener("click", () => {
    $$(".tab").forEach((x) => x.classList.toggle("on", x === t));
    $$(".panel").forEach((p) => p.classList.toggle("on", p.id === "tab-" + t.dataset.tab));
  }));

  /* ---------- segmented controls ---------- */
  $$(".seg").forEach((seg) => seg.addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    $$("button", seg).forEach((x) => x.classList.toggle("on", x === b));
  }));
  const segValue = (name) => { const b = $('.seg[data-name="' + name + '"] button.on'); return b ? b.dataset.v : null; };
  const setSeg = (name, v) => $$('.seg[data-name="' + name + '"] button').forEach((b) => b.classList.toggle("on", b.dataset.v === String(v)));

  function readForm() {
    const f = $("#form"), data = {}; let bad = [];
    $$("input", f).forEach((i) => i.classList.remove("bad"));
    NUMS.forEach((n) => {
      const el = f.elements[n], v = Number(el.value);
      if (el.value === "" || !Number.isFinite(v) || v < Number(el.min) || v > Number(el.max)) { bad.push(el); el.classList && el.classList.add("bad"); }
      data[n] = Math.round(v);
    });
    data.department = f.elements.department.value;
    data.overtime = segValue("overtime");
    data.job_satisfaction = Number(segValue("job_satisfaction"));
    data.work_life_balance = Number(segValue("work_life_balance"));
    return { data, bad };
  }

  function fill(emp) {
    const f = $("#form");
    ["department", ...NUMS].forEach((n) => { f.elements[n].value = emp[n]; });
    setSeg("overtime", emp.overtime); setSeg("job_satisfaction", emp.job_satisfaction); setSeg("work_life_balance", emp.work_life_balance);
  }

  /* ---------- result ---------- */
  function renderPrediction(p) {
    $("#empty").hidden = true; $("#res").hidden = false;
    const fg = $("#g-fg"), len = 267.04;
    const color = p.band === "High" ? "var(--red)" : p.band === "Medium" ? "var(--amber)" : "var(--green)";
    fg.style.stroke = color;
    requestAnimationFrame(() => { fg.style.strokeDashoffset = String(len * (1 - Math.min(p.probability, 1))); });
    $("#pct").textContent = (p.risk_percent < 1 ? "<1" : p.risk_percent) + "%";
    const band = $("#band"); band.textContent = p.band + " risk"; band.className = "band " + p.band;
    const top = p.drivers.slice(0, 5), max = Math.max(...top.map((d) => Math.abs(d.impact)), 0.01);
    $("#drivers").innerHTML = top.map((d) => {
      const w = Math.max(4, (Math.abs(d.impact) / max) * 50).toFixed(1);
      const cls = d.impact > 0 ? "up" : "down";
      return '<li><div><div class="d-t">' + esc(d.label) + '</div><div class="d-v">' + esc(d.value) + " &middot; " + esc(d.effect) +
        '</div></div><div><div class="d-bar"><i class="' + cls + '" style="width:' + w + '%"></i></div></div></li>';
    }).join("") + '<li class="d-key"><span></span><div class="d-k"><span>lowers</span><span>raises</span></div></li>';
  }

  function renderAI(state, payload) {
    const body = $("#ai-body"); $("#ai-model").textContent = "";
    if (state === "loading") { body.innerHTML = '<div class="skel"></div><div class="skel"></div><div class="skel s"></div>'; return; }
    if (state === "off" || state === "error") { body.innerHTML = '<p class="note">' + esc(payload) + "</p>"; return; }
    $("#ai-model").textContent = payload.model;
    body.innerHTML = "<p>" + esc(payload.summary) + "</p><ol>" + payload.actions.map((a) => "<li>" + esc(a) + "</li>").join("") + "</ol>";
  }

  $("#form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const { data, bad } = readForm(), err = $("#form-err"), btn = $("#btn-predict");
    if (bad.length) { err.textContent = "Please check the highlighted fields."; err.hidden = false; return; }
    err.hidden = true; btn.disabled = true; btn.classList.add("busy");
    try {
      const p = await api("/api/predict", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
      renderPrediction(p);
      renderAI("loading");
      try {
        const x = await api("/api/explain", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ employee: data, prediction: p }) });
        renderAI("ok", x);
      } catch (ex) { renderAI(ex.status === 503 ? "off" : "error", ex.message); }
    } catch (ex) {
      err.textContent = ex.message; err.hidden = false;
    } finally { btn.disabled = false; btn.classList.remove("busy"); }
  });

  $$("[data-sample]").forEach((b) => b.addEventListener("click", () => {
    if (samples[b.dataset.sample]) { fill(samples[b.dataset.sample]); $("#form").requestSubmit(); }
  }));

  /* ---------- team CSV ---------- */
  const drop = $("#drop"), file = $("#file");
  async function scoreFile(f) {
    const err = $("#team-err"), out = $("#team-out");
    err.hidden = true; out.hidden = true;
    if (!f) return;
    const fd = new FormData(); fd.append("file", f);
    drop.querySelector("b").textContent = "Scoring " + f.name + "…";
    try {
      const r = await api("/api/predict-batch", { method: "POST", body: fd });
      $("#team-sum").innerHTML = '<span class="n">' + r.rows + " employees</span>" +
        ["High", "Medium", "Low"].map((b) => '<span class="b-' + b + '">' + r.summary[b] + " " + b.toLowerCase() + "</span>").join("");
      $("#team-rows").innerHTML = r.results.map((x) => "<tr><td>" + esc(x.employee_id) + "</td><td>" + esc(x.department) + "</td><td><b>" + (x.risk_percent < 1 ? "<1" : x.risk_percent) +
        '%</b></td><td><span class="pill b-' + x.band + '">' + x.band + "</span></td><td>" + esc(x.top_driver) + "</td></tr>").join("");
      $("#team-note").textContent = r.errors.length ? r.errors.length + " row(s) skipped: " + r.errors.map((e) => "row " + e.row + " (" + e.message + ")").join("; ") : "Sorted by risk, highest first.";
      out.hidden = false;
      showSaved(r.storage);
      loadStorage();
    } catch (ex) { err.textContent = ex.message; err.hidden = false; }
    finally { drop.querySelector("b").textContent = "Choose a CSV file"; file.value = ""; }
  }
  file.addEventListener("change", () => scoreFile(file.files[0]));
  ["dragenter", "dragover"].forEach((t) => drop.addEventListener(t, (e) => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach((t) => drop.addEventListener(t, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
  drop.addEventListener("drop", (e) => scoreFile(e.dataTransfer.files[0]));

  /* ---------- Cloud Storage (mounted bucket) ---------- */
  const FILE_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/></svg>';
  function showSaved(st) {
    const el = $("#team-store");
    if (!st) { el.hidden = true; return; }
    el.className = "store-msg " + (st.saved ? "ok" : "off");
    el.innerHTML = st.saved ? "<b>Saved to Cloud Storage:</b> " + st.files.map((f) => "<code>" + esc(f) + "</code>").join(" and ") : esc(st.message);
    el.hidden = false;
  }
  async function loadStorage() {
    const chip = $("#chip-store");
    try {
      const st = await api("/api/storage");
      chip.classList.remove("ok", "off"); chip.classList.add(st.enabled ? "ok" : "off");
      chip.innerHTML = "<i></i>Storage " + (st.enabled ? "on" : "off");
      $("#team-store-txt").textContent = st.enabled
        ? "Each upload and its scores are saved privately to your Cloud Storage bucket."
        : "Nothing is stored \u2014 the file is scored and forgotten.";
      $("#saved").hidden = !st.enabled;
      $("#saved-list").innerHTML = st.files.length
        ? st.files.map((f) => '<li class="' + (f.name.endsWith("_scored.csv") ? "sc" : "or") + '">' + FILE_ICON + "<span>" + esc(f.name) + "</span><small>" + f.kb + " KB</small></li>").join("")
        : '<li class="none">No files yet &mdash; upload a CSV above.</li>';
    } catch (ex) {
      chip.classList.add("off"); chip.innerHTML = "<i></i>Storage off";
    }
  }

  /* ---------- start-up ---------- */
  loadStorage();
  (async function init() {
    try {
      const [h, card, s] = await Promise.all([api("/api/health"), api("/api/model-card"), api("/api/samples")]);
      samples = s;
      const cm = $("#chip-model"); cm.classList.add("ok"); cm.innerHTML = "<i></i>Model v" + esc(card.version) + " ready";
      const ca = $("#chip-ai"); ca.classList.add(h.ai_enabled ? "ok" : "off"); ca.innerHTML = "<i></i>AI summary " + (h.ai_enabled ? "on" : "off");
      const m = card.metrics;
      $("#hero-stats").innerHTML = [["" + m.roc_auc, "ROC AUC (test)"], [card.rows.train.toLocaleString("en-IN"), "training rows"], [Math.round(card.attrition_rate * 100) + "%", "leave rate in data"]]
        .map((x) => '<div class="stat"><b>' + esc(x[0]) + "</b><span>" + esc(x[1]) + "</span></div>").join("");
      $("#mc-ver").textContent = "Version " + card.version + " · trained " + card.trained_on;
      $("#mc-tiles").innerHTML = [["ROC AUC", m.roc_auc], ["Accuracy", Math.round(m.accuracy * 100) + "%"], ["High-risk precision", Math.round(m.high_risk_precision * 100) + "%"], ["High-risk recall", Math.round(m.high_risk_recall * 100) + "%"]]
        .map((x) => '<div class="tile"><b>' + esc(x[1]) + "</b><span>" + esc(x[0]) + "</span></div>").join("");
      const rows = [["Algorithm", card.algorithm], ["Data", card.data], ["Rows", card.rows.train + " train · " + card.rows.test + " test"],
        ["Risk bands", "Low " + card.bands.low + " · Medium " + card.bands.medium + " · High " + card.bands.high],
        ["Features", card.features.join(", ")], ["Intended use", card.intended_use], ["scikit-learn", card.sklearn_version]];
      $("#mc-list").innerHTML = rows.map((r) => "<dt>" + esc(r[0]) + "</dt><dd>" + esc(r[1]) + "</dd>").join("");
    } catch (ex) {
      const cm = $("#chip-model"); cm.classList.add("off"); cm.innerHTML = "<i></i>Model unavailable";
    }
  })();
})();
