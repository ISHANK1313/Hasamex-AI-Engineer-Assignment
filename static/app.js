/* Single-page UI: Guide answers, Themes and disagreements, Ask.
   No build step and no framework. Every value from the API is inserted with textContent, never
   innerHTML, because transcript text is data and the app must not execute it. */

"use strict";

const state = { guide: [], themes: [], disagreements: [], transcripts: [] };

// --- small helpers ------------------------------------------------------------------------------

async function api(path, options) {
  const res = await fetch(path, options);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((body.error && body.error.message) || "Request failed (" + res.status + ")");
  return body;
}

function el(tag, props, children) {
  const node = document.createElement(tag);
  for (const key of Object.keys(props || {})) {
    const value = props[key];
    if (value === null || value === undefined) continue;
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key === "hidden") node.hidden = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value);
  }
  for (const child of [].concat(children || [])) if (child) node.append(child);
  return node;
}

const p = (cls, value) => el("p", { class: cls, text: value });

function banner(message, kind) {
  const node = document.querySelector("#banner");
  node.textContent = message || "";
  node.className = "banner " + (kind || "info");
  node.hidden = !message;
}

function status(message) {
  document.querySelector("#status").textContent = message;
}

async function copy(text, button) {
  const label = button.textContent;
  try {
    await navigator.clipboard.writeText(text);
    button.textContent = "Copied";
  } catch (err) {
    button.textContent = "Copy failed";
  }
  setTimeout(() => { button.textContent = label; }, 1200);
}

// Reveal the full source turn behind a quote, so a claim can be checked against the transcript.
async function toggleSource(segmentId, host, button) {
  if (!host.hidden) {
    host.hidden = true;
    button.textContent = "Source turn";
    return;
  }
  if (!host.textContent) {
    try {
      const seg = await api("/api/segments/" + encodeURIComponent(segmentId));
      host.textContent = seg.timestamp + "  " + seg.speaker + " (" + seg.market + ")\n\n" + seg.text;
    } catch (err) {
      host.textContent = err.message;
    }
  }
  host.hidden = false;
  button.textContent = "Hide source";
}

// One quoted span: verbatim text, its timestamp, its speaker, plus source and copy actions.
function quoteFigure(q) {
  const source = el("pre", { class: "source", hidden: true });
  const sourceBtn = el("button", { class: "link", type: "button", text: "Source turn" });
  sourceBtn.addEventListener("click", () => toggleSource(q.segment_id, source, sourceBtn));
  const copyBtn = el("button", { class: "link", type: "button", text: "Copy quote" });
  copyBtn.addEventListener("click", () => copy(q.text || q.quote, copyBtn));
  return el("figure", { class: "quote" }, [
    el("blockquote", { text: q.text || q.quote }),
    el("figcaption", { class: "row meta" }, [
      el("span", { class: "chip", text: q.timestamp }),
      el("span", { class: "chip soft", text: q.speaker }),
      el("span", { class: "chip soft", text: q.expert || q.market }),
      sourceBtn,
      copyBtn,
    ]),
    source,
  ]);
}

// --- guide answers ------------------------------------------------------------------------------

function answerCard(a) {
  const card = el("article", { class: "expert" + (a.not_covered ? " muted" : "") });
  card.append(el("h4", { text: a.expert + " - " + a.expert_name }));
  card.append(p("role", a.role + (a.question_timestamp ? " | asked at " + a.question_timestamp : "")));
  if (a.not_covered) {
    card.append(p("empty", "Not covered in this call."));
    return card;
  }
  card.append(el("div", { class: "figures" }, a.quotes.map(quoteFigure)));
  return card;
}

function questionCard(q) {
  const provider = q.summary_provider && q.summary_provider !== "lexical"
    ? el("span", { class: "chip model", text: "summarised by " + q.summary_provider })
    : el("span", { class: "chip soft", text: "summary built from the quotes only" });
  return el("section", { class: "card" }, [
    el("header", {}, [
      el("h3", { text: "Q" + q.id + " - " + q.name }),
      p("q", q.question),
      el("div", { class: "row" }, [provider]),
      p("summary", q.summary || "No summary available."),
    ]),
    el("div", { class: "grid" }, q.answers.map(answerCard)),
  ]);
}

function renderGuide() {
  const host = document.querySelector("#guide");
  const needle = document.querySelector("#filter").value.trim().toLowerCase();
  host.replaceChildren();
  const questions = state.guide.filter(
    (q) => !needle || (q.name + " " + q.question + " " + q.topic).toLowerCase().includes(needle)
  );
  if (!questions.length) {
    host.append(p("empty", "No guide question matches that filter."));
    return;
  }
  host.append(el("div", {}, questions.map(questionCard)));
}

// --- themes and disagreements --------------------------------------------------------------------

function viewCard(v) {
  return el("article", { class: "expert" }, [
    el("h4", { text: v.expert + " - " + v.speaker }),
    quoteFigure({
      text: v.quote,
      timestamp: v.timestamp,
      speaker: v.speaker,
      expert: v.expert,
      segment_id: v.segment_id,
    }),
    v.quantifier ? p("role", "quantified as: " + v.quantifier) : null,
  ]);
}

function renderThemes() {
  const host = document.querySelector("#themes");
  host.replaceChildren();
  host.append(el("h2", { text: "Common themes" }));
  if (!state.themes.length) {
    host.append(p("empty", "No theme is shared by two or more experts in the loaded transcripts."));
  }
  for (const t of state.themes) {
    host.append(el("section", { class: "card" }, [
      el("header", {}, [
        el("h3", { text: t.name }),
        p("q", t.question),
        p("role", t.expert_count + " of " + t.total_experts + " experts raised this: " + t.experts.join(", ")),
      ]),
      el("div", { class: "grid" }, t.views.map(viewCard)),
    ]));
  }

  host.append(el("h2", { text: "Where the experts disagree" }));
  if (!state.disagreements.length) {
    host.append(p("empty", "No contrasting stances found on any topic."));
  }
  for (const d of state.disagreements) {
    host.append(el("section", { class: "card dis" }, [
      el("header", {}, [el("h3", { text: d.name }), p("q", d.question), p("reason", d.reason)]),
      el("div", { class: "grid" }, d.sides.map(viewCard)),
    ]));
  }
}

// --- ask ----------------------------------------------------------------------------------------

function renderAnswer(body) {
  const host = document.querySelector("#answer");
  host.replaceChildren();
  const citations = body.citations || [];
  const card = el("section", { class: "card" }, [
    el("header", {}, [
      el("h3", { text: body.question }),
      el("div", { class: "row" }, [
        el("span", { class: "chip", text: citations.length + " cited source" + (citations.length === 1 ? "" : "s") }),
        body.topic ? el("span", { class: "chip soft", text: "topic: " + body.topic }) : null,
        el("span", {
          class: "chip " + (body.provider === "lexical" ? "soft" : "model"),
          text: body.provider === "lexical" ? "verbatim evidence" : "written by " + body.provider,
        }),
      ]),
    ]),
    p("answer", body.answer || ""),
  ]);
  if (body.note) card.append(p("note", body.note));
  if (!citations.length) {
    card.append(p("empty", "No turn in the loaded transcripts covers that question, so nothing was invented."));
  }
  host.append(card);
  if (citations.length) {
    host.append(el("section", { class: "card" }, [
      el("h3", { text: "Sources" }),
      el("div", { class: "grid" }, citations.map(quoteFigure)),
    ]));
  }
}

// --- corpus panel and wiring ----------------------------------------------------------------------

function renderCorpus(health, transcripts) {
  const host = document.querySelector("#corpus");
  host.replaceChildren();
  host.append(el("span", { class: "chip", text: transcripts.length + " transcripts" }));
  host.append(el("span", { class: "chip", text: health.segments + " turns" }));
  host.append(el("span", {
    class: "chip " + (health.llm_available ? "model" : "soft"),
    text: health.llm_available ? "model: " + health.llm : "no key: verbatim mode",
  }));
  for (const t of transcripts) {
    host.append(el("span", { class: "chip soft", text: t.expert + " | " + t.market + " | " + t.turns + " turns" }));
  }
}

function loadTab(name) {
  for (const tab of document.querySelectorAll("[role=tab]")) {
    const on = tab.id === "tab-" + name;
    tab.setAttribute("aria-selected", String(on));
    tab.tabIndex = on ? 0 : -1;
  }
  for (const panel of document.querySelectorAll("[role=tabpanel]")) {
    panel.hidden = panel.id !== "panel-" + name;
  }
}

async function loadAll() {
  banner("");
  status("loading transcripts");
  try {
    const health = await api("/api/health");
    const listing = await api("/api/transcripts");
    state.transcripts = listing.transcripts;
    renderCorpus(health, state.transcripts);
    state.guide = (await api("/api/guide-answers")).questions;
    const themes = await api("/api/themes");
    state.themes = themes.themes;
    state.disagreements = themes.disagreements;
    renderGuide();
    renderThemes();
    status("ready: " + state.guide.length + " guide questions across " + state.transcripts.length + " experts.");
  } catch (err) {
    banner(err.message, "error");
    status("failed to load");
  }
}

function wire() {
  for (const tab of document.querySelectorAll("[role=tab]")) {
    tab.addEventListener("click", () => loadTab(tab.id.replace("tab-", "")));
    tab.addEventListener("keydown", (event) => {
      if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
      const tabs = [...document.querySelectorAll("[role=tab]")];
      const step = event.key === "ArrowRight" ? 1 : -1;
      const next = tabs[(tabs.indexOf(tab) + step + tabs.length) % tabs.length];
      next.focus();
      loadTab(next.id.replace("tab-", ""));
    });
  }

  document.querySelector("#filter").addEventListener("input", renderGuide);

  document.querySelector("#ask-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const question = document.querySelector("#question").value.trim();
    if (!question) return;
    const button = event.target.querySelector("button");
    button.disabled = true;
    banner("");
    try {
      renderAnswer(await api("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      }));
    } catch (err) {
      banner(err.message, "error");
    } finally {
      button.disabled = false;
    }
  });

  document.querySelector("#add").addEventListener("click", async () => {
    const input = document.querySelector("#file");
    if (!input.files.length) {
      banner("Choose a .txt transcript first.", "warn");
      return;
    }
    const body = new FormData();
    body.append("file", input.files[0]);
    try {
      const out = await api("/api/transcripts/ingest", { method: "POST", body });
      input.value = "";
      await loadAll();
      banner("Added " + out.expert + " (" + out.segments + " turns).", "ok");
    } catch (err) {
      banner(err.message, "error");
    }
  });

  document.querySelector("#reload").addEventListener("click", async () => {
    try {
      await api("/api/transcripts/ingest", { method: "POST" });
      await loadAll();
      banner("Reloaded the three bundled samples.", "ok");
    } catch (err) {
      banner(err.message, "error");
    }
  });
}

wire();
loadAll();
