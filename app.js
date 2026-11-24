(() => {
  "use strict";

  // Same origin by default (Flask serves this page). Set window.API_BASE to point elsewhere.
  const API = window.API_BASE || "";
  const $ = (id) => document.getElementById(id);

  const SAMPLES = {
    spam: {
      subject: "URGENT: your account has been suspended",
      body: "Dear customer,\n\nWe detected unusual activity and your bank account has been blocked. " +
            "Verify your password immediately at http://account-check.xyz/login or you will lose access.\n\n" +
            "You have also been selected to receive a $5000 cash prize. Act now!!!",
    },
    ham: {
      subject: "Meeting tomorrow",
      body: "Hi Priya,\n\nAre we still meeting tomorrow at 3:30 PM to go over the project report? " +
            "I've attached the latest draft. Let me know if you need to reschedule.\n\nThanks,\nAlex",
    },
  };

  const BATCH_SAMPLE = [
    "You WON!!!\nCongratulations! Claim your $10000 gift card at http://bit.ly/x9Fq2 before it expires!!!",
    "Project update\nHi team, the sprint retrospective has moved to Thursday. Please add your feedback to the shared document.",
    "Cheap meds online\nGet pills without a prescription. Cheap prices, worldwide shipping, order today!",
    "Invoice attached\nAttached is the invoice for last month's consulting work. Let me know if anything looks incorrect.",
  ].join("\n\n---\n\n");

  /* ---------- helpers ---------- */
  function el(tag, props = {}, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(props)) {
      if (k === "class") node.className = v;
      else if (k === "text") node.textContent = v;
      else node.setAttribute(k, v);
    }
    children.forEach((c) => node.append(c));
    return node; // text always goes through textContent/append, never innerHTML
  }

  async function api(path, options) {
    let res;
    try {
      res = await fetch(API + path, options);
    } catch {
      throw new Error("Cannot reach the server. Start it with: python app.py");
    }
    let data = {};
    try { data = await res.json(); } catch { /* non-JSON error page */ }
    if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
    return data;
  }

  const post = (path, payload) =>
    api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });

  const pct = (p) => `${Math.round(p * 100)}%`;
  const showError = (node, msg) => { node.textContent = msg; node.hidden = !msg; };

  /* ---------- tabs ---------- */
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => {
        const active = t === tab;
        t.classList.toggle("is-active", active);
        t.setAttribute("aria-selected", String(active));
      });
      document.querySelectorAll(".panel").forEach((p) => { p.hidden = p.id !== `panel-${tab.dataset.tab}`; });
      if (tab.dataset.tab === "model") loadModelInfo();
    });
  });

  /* ---------- single email ---------- */
  const history = [];

  function renderResult(r) {
    $("result-empty").hidden = true;
    $("result-body").hidden = false;

    const spam = r.label === "spam";
    const stamp = $("stamp");
    stamp.className = "stamp " + (spam ? "is-spam" : "is-ham");
    void stamp.offsetWidth; // restart the stamp animation
    stamp.classList.add("land");
    $("stamp-text").textContent = spam ? "SPAM" : "SAFE";

    $("verdict-line").textContent = spam
      ? "This looks like spam"
      : "This looks like a normal email";
    $("verdict-sub").textContent = spam
      ? `${pct(r.spam_probability)} chance of spam. Do not click links or reply.`
      : `Only a ${pct(r.spam_probability)} chance of spam.`;

    const fill = $("meter-fill");
    fill.classList.toggle("is-spam", spam);
    fill.style.width = `${Math.max(3, Math.round(r.spam_probability * 100))}%`;

    const signals = $("signals");
    signals.replaceChildren();
    if (!r.signals.length) {
      signals.append(el("li", { class: "none" }, el("div", {}, el("strong", { text: "No warning signs found" }),
        el("span", { text: "No suspicious links, pressure phrases or account requests." }))));
    }
    r.signals.forEach((s) => {
      signals.append(el("li", { class: s.level }, el("div", {}, el("strong", { text: s.name }), el("span", { text: s.detail }))));
    });

    const words = $("words");
    words.replaceChildren();
    if (!r.top_words.length) words.append(el("li", { class: "ham", text: "No known words found" }));
    r.top_words.forEach((w) => words.append(el("li", { class: w.direction, text: w.word })));
  }

  function addHistory(subject, r) {
    history.unshift({ subject: subject || "(no subject)", label: r.label, p: r.spam_probability });
    history.splice(8);
    const list = $("history");
    list.replaceChildren();
    history.forEach((h) => {
      list.append(el("li", {},
        el("span", { class: `tag ${h.label}`, text: h.label === "spam" ? "Spam" : "Safe" }),
        el("span", { class: "subj", text: h.subject }),
        el("span", { class: "pct", text: pct(h.p) })));
    });
    $("history-wrap").hidden = false;
  }

  $("email-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const subject = $("subject").value;
    const body = $("body").value;
    const err = $("form-error");
    showError(err, "");
    if (!subject.trim() && !body.trim()) {
      showError(err, "Enter a subject or message to check.");
      return;
    }
    const btn = $("check-btn");
    btn.disabled = true; btn.textContent = "Checking…";
    try {
      const r = await post("/api/predict", { subject, body });
      renderResult(r);
      addHistory(subject, r);
    } catch (ex) {
      showError(err, ex.message);
    } finally {
      btn.disabled = false; btn.textContent = "Check email";
    }
  });

  const loadSample = (key) => () => {
    $("subject").value = SAMPLES[key].subject;
    $("body").value = SAMPLES[key].body;
    showError($("form-error"), "");
  };
  $("sample-spam").addEventListener("click", loadSample("spam"));
  $("sample-ham").addEventListener("click", loadSample("ham"));
  $("clear-btn").addEventListener("click", () => {
    $("subject").value = ""; $("body").value = "";
    $("result-body").hidden = true; $("result-empty").hidden = false;
    showError($("form-error"), "");
  });

  /* ---------- batch ---------- */
  function parseBatch(text) {
    return text.split(/^\s*---\s*$/m)
      .map((block) => block.trim())
      .filter(Boolean)
      .map((block) => {
        const lines = block.split("\n");
        return { subject: lines[0].trim(), body: lines.slice(1).join("\n").trim() };
      });
  }

  $("batch-sample").addEventListener("click", () => { $("batch-input").value = BATCH_SAMPLE; });

  $("batch-btn").addEventListener("click", async () => {
    const err = $("batch-error");
    showError(err, "");
    const emails = parseBatch($("batch-input").value);
    if (!emails.length) { showError(err, "Paste at least one email to check."); return; }
    if (emails.length > 100) { showError(err, "Check up to 100 emails at a time."); return; }

    const btn = $("batch-btn");
    btn.disabled = true; btn.textContent = "Checking…";
    try {
      const data = await post("/api/predict/batch", { emails });
      $("batch-empty").hidden = true;
      $("batch-body").hidden = false;
      const { total, spam } = data.summary;
      $("batch-summary").textContent = `${spam} of ${total} flagged as spam`;
      const list = $("batch-list");
      list.replaceChildren();
      data.results.forEach((r) => {
        list.append(el("li", {},
          el("span", { class: `tag ${r.label}`, text: r.label === "spam" ? "Spam" : "Safe" }),
          el("span", { class: "subj", text: r.subject || "(no subject)" }),
          el("span", { class: "pct", text: pct(r.spam_probability) })));
      });
    } catch (ex) {
      showError(err, ex.message);
    } finally {
      btn.disabled = false; btn.textContent = "Check all";
    }
  });

  /* ---------- model info ---------- */
  let modelLoaded = false;
  async function loadModelInfo() {
    if (modelLoaded) return;
    try {
      const m = await api("/api/model-info");
      const stats = $("model-stats");
      stats.replaceChildren();
      [["Accuracy", m.accuracy], ["Precision", m.precision], ["Recall", m.recall], ["F1 score", m.f1]]
        .forEach(([k, v]) => stats.append(el("div", {}, el("dt", { text: k }), el("dd", { text: pct(v) }))));
      const cm = m.confusion_matrix;
      $("m-tn").textContent = cm.true_negative; $("m-fp").textContent = cm.false_positive;
      $("m-fn").textContent = cm.false_negative; $("m-tp").textContent = cm.true_positive;
      $("model-meta").textContent =
        `${m.algorithm}. Trained on ${m.samples} emails from ${m.dataset} (${m.spam_samples} spam, ${m.ham_samples} safe); ` +
        `scores below come from ${m.test_samples} emails held back for testing.`;
      $("model-note").textContent = m.dataset === "emails.csv"
        ? "This model was trained on a small generated demo dataset, so near-perfect scores are expected and will not hold on real mail. Retrain on a real dataset for realistic results."
        : "";
      $("model-note").hidden = !$("model-note").textContent;
      modelLoaded = true;
    } catch (ex) {
      $("model-meta").textContent = ex.message;
    }
  }
})();
