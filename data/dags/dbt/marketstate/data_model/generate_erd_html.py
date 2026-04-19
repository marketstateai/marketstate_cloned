# generate_erd_html.py
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ERD (single file)</title>
  <style>
    :root{{
      --bg:#f6f7fb; --card:#ffffff; --border:#e5e7eb; --text:#111827; --muted:#6b7280;
      --header:#f3f4f6;
      --dimHead:#eaf2ff; --dimBorder:#bfdbfe;
      --factHead:#ecfdf5; --factBorder:#a7f3d0;
      --pk:#059669; --fk:#7c3aed; --unique:#2563eb; --nn:#dc2626; --line:#374151;
    }}
    *{{box-sizing:border-box}}
    body{{margin:0;font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;background:var(--bg);color:var(--text);}}
    /* Leave room for the fixed top control bar */
    .wrap{{position:relative;height:100vh;padding:28px;padding-top:104px;overflow:auto;cursor:grab;}}
    .wrap.panning{{cursor:grabbing;}}
    .canvas{{position:relative;min-height:700px;min-width:1000px;}}
    .viewport{{position:absolute;inset:0;transform-origin:0 0;}}
    .hint{{position:fixed;top:18px;left:28px;right:28px;z-index:50;display:flex;align-items:center;justify-content:space-between;gap:12px;
      padding:10px 12px;background:rgba(246,247,251,.85);backdrop-filter:blur(6px);border:1px solid var(--border);
      border-radius:12px;box-shadow:0 6px 18px rgba(0,0,0,.05);font-size:13px;color:var(--muted);}}
    .hint b{{color:var(--text)}}
    .controls{{display:flex;align-items:center;gap:10px;}}
    .btn{{border:1px solid var(--border);background:#fff;color:var(--text);border-radius:10px;padding:6px 10px;font-weight:700;cursor:pointer;}}
    .btn:active{{transform:translateY(1px);}}
    .table-card{{position:absolute;width:520px;background:var(--card);border:1px solid var(--border);border-radius:14px;
      box-shadow:0 6px 18px rgba(0,0,0,.06);overflow:hidden;user-select:none;}}
    .table-card.dim{{border-color:var(--dimBorder);}}
    .table-card.fact{{border-color:var(--factBorder);}}
    .table-card.report{{border-color:rgba(251,191,36,.75);}}
    .table-title{{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 12px;font-weight:800;
      background:var(--header);border-bottom:1px solid var(--border);cursor:grab;}}
    .table-card.dim .table-title{{background:var(--dimHead);border-bottom-color:rgba(191,219,254,.7);}}
    .table-card.fact .table-title{{background:var(--factHead);border-bottom-color:rgba(167,243,208,.7);}}
    .table-card.report .table-title{{background:rgba(255,247,237,.95);border-bottom-color:rgba(251,191,36,.35);}}
    .table-title:active{{cursor:grabbing}}
    .title-left{{display:flex;align-items:center;gap:8px;min-width:0}}
    .toggle{{border:0;background:transparent;color:var(--muted);cursor:pointer;padding:2px 4px;border-radius:8px;line-height:1;}}
    .toggle:hover{{background:rgba(0,0,0,.04);color:var(--text);}}
    .toggle svg{{display:block}}
    .chip{{font-weight:600;font-size:11px;padding:2px 8px;border-radius:999px;border:1px solid var(--border);color:var(--muted);background:#fff;}}
    .cols{{padding:10px 12px}}
    .col{{display:flex;align-items:baseline;justify-content:space-between;gap:12px;padding:8px 0;border-bottom:1px dashed #eef0f3;font-size:14px;}}
    .col:last-child{{border-bottom:0}}
    .left{{display:flex;align-items:baseline;gap:10px;min-width:0}}
    .keys{{display:inline-flex;gap:6px;align-items:center;flex:0 0 auto}}
    .keydot{{width:12px;height:12px;border-radius:999px;border:2px solid var(--border);background:#fff;display:inline-block;}}
    .keydot.pk{{border-color:rgba(5,150,105,.55);background:rgba(5,150,105,.10)}}
    .keydot.fk{{border-color:rgba(124,58,237,.55);background:rgba(124,58,237,.10)}}
    .name{{font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    .type{{color:var(--muted);font-size:12px;white-space:nowrap}}
    .badges{{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}}
    .badge{{font-size:11px;padding:2px 8px;border-radius:999px;border:1px solid var(--border);background:#fff;white-space:nowrap;}}
    .pk{{border-color:rgba(5,150,105,.25);color:var(--pk);background:rgba(5,150,105,.06)}}
    .fk{{border-color:rgba(124,58,237,.25);color:var(--fk);background:rgba(124,58,237,.06)}}
    .unique{{border-color:rgba(37,99,235,.25);color:var(--unique);background:rgba(37,99,235,.06)}}
    .nn{{border-color:rgba(220,38,38,.25);color:var(--nn);background:rgba(220,38,38,.06)}}
    details.optional{{margin-top:6px;border-top:1px dashed #eef0f3;padding-top:8px;}}
    summary.optional-summary{{list-style:none;cursor:pointer;user-select:none;display:flex;align-items:center;justify-content:space-between;
      gap:12px;color:var(--muted);font-size:12px;font-weight:750;padding:6px 8px;border-radius:10px;}}
    summary.optional-summary::-webkit-details-marker{{display:none;}}
    summary.optional-summary:hover{{background:rgba(0,0,0,.04);color:var(--text);}}
    .optional-caret{{display:inline-block;transform:rotate(-90deg);transition:transform .12s ease;}}
    details[open] .optional-caret{{transform:rotate(0deg);}}
    .optional-cols{{margin-top:6px;}}
    .hover-tip{{position:fixed;z-index:9999;max-width:520px;padding:8px 10px;border-radius:12px;
      background:rgba(17,24,39,.96);color:#fff;border:1px solid rgba(255,255,255,.16);
      box-shadow:0 14px 34px rgba(0,0,0,.24);font-size:12px;line-height:1.25;
      opacity:0;transform:translateY(2px);transition:opacity .12s ease,transform .12s ease;pointer-events:none;
      white-space:pre-wrap;}}
    .hover-tip.show{{opacity:1;transform:translateY(0);}}
    .table-card.selected{{opacity:1!important;filter:none!important;border-color:rgba(37,99,235,.75)!important;box-shadow:0 18px 44px rgba(37,99,235,.18),0 0 0 1px rgba(37,99,235,.25);}}
    .table-card.related{{border-color:rgba(96,165,250,.65);box-shadow:0 10px 26px rgba(37,99,235,.10);}}
    .table-card.dimmed{{opacity:.12;filter:saturate(.6);}}
    .table-card.focused{{opacity:1!important;filter:none!important;z-index:60;}}
    .col.selected-col{{background:rgba(37,99,235,.08);border-radius:10px;padding-left:8px;padding-right:8px;}}
    svg{{position:absolute;inset:0;pointer-events:none;overflow:visible;}}
    .edge{{stroke:var(--line);stroke-width:2.2;fill:none;opacity:.42;}}
    .edge.active{{stroke:#2563eb;stroke-width:3.4;opacity:1;filter:drop-shadow(0 0 6px rgba(37,99,235,.55)) drop-shadow(0 0 14px rgba(37,99,235,.28));}}
    .edge.dimmed{{opacity:.06;}}
    .label{{font-size:12px;fill:var(--muted);}}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hover-tip" id="hoverTip" aria-hidden="true"></div>
    <div class="hint">
      <div><b>Single-file ERD.</b> Generated from <b>{db_name}</b>. Drag a table by its header.</div>
      <div class="controls">
        <button class="btn" id="zoomOut" title="Zoom out">−</button>
        <div class="chip" id="zoomLabel">100%</div>
        <button class="btn" id="zoomIn" title="Zoom in">+</button>
        <button class="btn" id="zoomFit" title="Fit diagram">Fit</button>
        <button class="btn" id="resetFormat" title="Reset layout + collapse all">Reset</button>
        <div class="chip">{out_name}</div>
      </div>
    </div>
    <div class="canvas" id="canvas">
      <div class="viewport" id="viewport">
        <svg id="wires">
          <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--line)"></path>
            </marker>
          </defs>
        </svg>
      </div>
    </div>
  </div>

<script>
const MODEL = {model_json};

/* Rendering + dragging (auto) */
const wrap = document.querySelector(".wrap");
const canvas = document.getElementById("canvas");
const viewport = document.getElementById("viewport");
const wires = document.getElementById("wires");
const zoomLabel = document.getElementById("zoomLabel");
const zoomInBtn = document.getElementById("zoomIn");
const zoomOutBtn = document.getElementById("zoomOut");
const zoomFitBtn = document.getElementById("zoomFit");
const resetFormatBtn = document.getElementById("resetFormat");
const hoverTip = document.getElementById("hoverTip");

let zoom = 1.0;
const minZoom = 0.35;
const maxZoom = 2.25;
let contentW = 1400;
let contentH = 900;
let bounds = {{ minX: 0, minY: 0, maxX: 1400, maxY: 900 }};
let rafPending = false;
let selectedTable = null;

function scheduleRedraw() {{
  if (rafPending) return;
  rafPending = true;
  requestAnimationFrame(() => {{
    rafPending = false;
    drawEdges();
  }});
}}

function layoutTablesAuto() {{
  // Tiered left-to-right layout:
  // - Core dims (no FK deps) on the far left, vertically aligned.
  // - Facts on the far right, vertically aligned.
  // - Middle tiers are dependency levels (dims with FK deps), vertically aligned.
  const nodes = MODEL.tables.map((t) => {{
    const el = document.getElementById(`tbl_${{t.name}}`);
    return {{
      t,
      el,
      w: el ? el.offsetWidth : 320,
      h: el ? el.offsetHeight : 220,
      x: t.x || 80,
      y: t.y || 120,
      vx: 0,
      vy: 0,
    }};
  }});

  const nodeByName = new Map(nodes.map(n => [n.t.name, n]));
  const rels = (MODEL.relationships || [])
    .map((r) => ({{ a: nodeByName.get(r.from), b: nodeByName.get(r.to) }}))
    .filter((e) => e.a && e.b);

  if (nodes.length <= 1) return;

  const facts = nodes.filter(n => (n.t.kind || "") === "fact");
  const reports = nodes.filter(n => (n.t.kind || "") === "report");
  const dims = nodes.filter(n => (n.t.kind || "") === "dim");
  const others = nodes.filter(n => !(n.t.kind === "fact" || n.t.kind === "dim" || n.t.kind === "report"));

  // If we don't have facts, fall back to a simple grid with generous spacing.
  if (facts.length === 0) {{
    const cols = Math.max(2, Math.ceil(Math.sqrt(nodes.length)));
    nodes.forEach((n, i) => {{
      const col = i % cols;
      const row = Math.floor(i / cols);
      n.x = 80 + col * 520;
      n.y = 120 + row * 340;
    }});
  }} else {{
    // Build dependency parent map from FK relationships (parent -> child).
    const parents = new Map();
    const children = new Map();
    for (const n of nodes) {{
      parents.set(n.t.name, new Set());
      children.set(n.t.name, new Set());
    }}
    for (const r of (MODEL.relationships || [])) {{
      if (!parents.has(r.to) || !children.has(r.from)) continue;
      parents.get(r.to).add(r.from);
      children.get(r.from).add(r.to);
    }}

    const factSet = new Set(facts.map(f => f.t.name));
    const reportSet = new Set(reports.map(r => r.t.name));
    const nonFacts = nodes.filter(n => !factSet.has(n.t.name) && !reportSet.has(n.t.name));

    // Compute dependency "tier" for non-facts (0 = no FK deps).
    const tier = new Map();
    const core = nonFacts.filter(n => (parents.get(n.t.name)?.size || 0) === 0);
    core.sort((a, b) => a.t.name.localeCompare(b.t.name));
    for (const n of core) tier.set(n.t.name, 0);
    for (const n of nonFacts) if (!tier.has(n.t.name)) tier.set(n.t.name, 1);

    // Relax tiers based on parents.
    for (let it = 0; it < nodes.length; it++) {{
      let changed = false;
      for (const n of nonFacts) {{
        const ps = [...(parents.get(n.t.name) || [])];
        if (ps.length === 0) continue;
        let maxP = 0;
        for (const p of ps) maxP = Math.max(maxP, tier.get(p) ?? 0);
        const next = maxP + 1;
        if (next !== tier.get(n.t.name)) {{
          tier.set(n.t.name, next);
          changed = true;
        }}
      }}
      if (!changed) break;
    }}

    const maxDimTier = Math.max(0, ...nonFacts.map(n => tier.get(n.t.name) ?? 0));
    const factTier = maxDimTier + 2; // leave a visual gap before facts
    for (const f of facts) tier.set(f.t.name, factTier);
    const reportTier = factTier + 1;
    for (const r of reports) tier.set(r.t.name, reportTier);

    // Group into columns by tier.
    const tiers = new Map();
    for (const n of nodes) {{
      const t = tier.get(n.t.name) ?? 0;
      if (!tiers.has(t)) tiers.set(t, []);
      tiers.get(t).push(n);
    }}

    const sortedTiers = [...tiers.keys()].sort((a, b) => a - b);
    const tierIndex = new Map(sortedTiers.map((t, i) => [t, i]));
    const x0 = 80;
    const gapX = 620;
    const topY = 120;
    const gapY = 52;

    const sortTierNodes = (arr) => {{
      return arr.sort((a, b) => {{
        const kindRank = (k) => (k === "dim" ? 0 : (k === "fact" ? 2 : (k === "report" ? 3 : 1)));
        const ak = kindRank(a.t.kind || "");
        const bk = kindRank(b.t.kind || "");
        if (ak !== bk) return ak - bk;
        const ap = (parents.get(a.t.name)?.size || 0);
        const bp = (parents.get(b.t.name)?.size || 0);
        if (ap !== bp) return bp - ap; // multi-input dims first
        const ac = (children.get(a.t.name)?.size || 0);
        const bc = (children.get(b.t.name)?.size || 0);
        if (ac !== bc) return bc - ac; // fan-out next
        return a.t.name.localeCompare(b.t.name);
      }});
    }};

    for (const t of sortedTiers) {{
      const col = tierIndex.get(t) || 0;
      const x = x0 + col * gapX;
      const arr = sortTierNodes(tiers.get(t));

      let y = topY;
      for (const n of arr) {{
        n.x = Math.round(x);
        n.y = Math.round(y);
        y += n.h + gapY;
      }}
    }}
  }}

  // Commit back to model + DOM
  for (const n of nodes) {{
    n.t.x = Math.round(n.x);
    n.t.y = Math.round(n.y);
    if (n.el) {{
      n.el.style.left = n.t.x + "px";
      n.el.style.top = n.t.y + "px";
    }}
  }}
}}

function computeContentBounds() {{
  // Measure from the rendered table cards (unscaled logical coords).
  let minLeft = Infinity;
  let minTop = Infinity;
  let maxRight = 0;
  let maxBottom = 0;
  for (const card of viewport.querySelectorAll(".table-card")) {{
    const x = card.offsetLeft;
    const y = card.offsetTop;
    const w = card.offsetWidth;
    const h = card.offsetHeight;
    minLeft = Math.min(minLeft, x);
    minTop = Math.min(minTop, y);
    maxRight = Math.max(maxRight, x + w);
    maxBottom = Math.max(maxBottom, y + h);
  }}

  // If layout produced negative coordinates, normalize all tables so everything is scrollable
  // (scroll containers can't scroll into negative space).
  if (minLeft !== Infinity) {{
    const targetPad = 20;
    const dx = Math.max(0, targetPad - minLeft);
    const dy = Math.max(0, targetPad - minTop);
    if (dx || dy) {{
      for (const t of MODEL.tables) {{
        t.x = Math.round((t.x || 0) + dx);
        t.y = Math.round((t.y || 0) + dy);
        const el = document.getElementById(`tbl_${{t.name}}`);
        if (el) {{
          el.style.left = t.x + "px";
          el.style.top = t.y + "px";
        }}
      }}
      // Recompute after normalization.
      minLeft += dx;
      minTop += dy;
      maxRight += dx;
      maxBottom += dy;
    }}
  }}

  // Extra margin so clusters breathe and panning doesn't feel cramped.
  const pad = 320;
  const safeMinX = (minLeft === Infinity) ? 0 : minLeft;
  const safeMinY = (minTop === Infinity) ? 0 : minTop;
  bounds = {{ minX: safeMinX, minY: safeMinY, maxX: maxRight, maxY: maxBottom }};
  contentW = Math.max(1000, (maxRight - safeMinX) + pad);
  contentH = Math.max(700, (maxBottom - safeMinY) + pad);
  viewport.style.width = contentW + "px";
  viewport.style.height = contentH + "px";
}}

function applyZoom() {{
  zoom = clamp(zoom, minZoom, maxZoom);
  viewport.style.transform = `scale(${{zoom}})`;
  zoomLabel.textContent = `${{Math.round(zoom * 100)}}%`;
  canvas.style.width = (contentW * zoom) + "px";
  canvas.style.height = (contentH * zoom) + "px";
  scheduleRedraw();
}}

const badgeClass = (b) => ({{
  "PK":"pk","FK":"fk","UNIQUE":"unique","NOT NULL":"nn"
}}[b] || "");

function el(tag, attrs={{}}, children=[]) {{
  const node = document.createElement(tag);
  for (const [k,v] of Object.entries(attrs)) {{
    if (k === "class") node.className = v;
    else if (k === "style") node.setAttribute("style", v);
    else node.setAttribute(k, v);
  }}
  for (const ch of children) node.appendChild(ch);
  return node;
}}

function renderTables() {{
  [...viewport.querySelectorAll(".table-card")].forEach(n => n.remove());

  const isCritical = (c) => {{
    const b = c.badges || [];
    return b.includes("PK") || b.includes("FK") || b.includes("UNIQUE") || b.includes("NOT NULL");
  }};

  const renderCol = (tableName, c) => {{
    const colTitle = [
      c.name || "",
      c.type ? `(${{c.type}})` : "",
      (c.badges && c.badges.length) ? `- ${{c.badges.join(", ")}}` : "",
    ].filter(Boolean).join(" ");

    const keys = el("div", {{ class: "keys" }});
    if ((c.badges || []).includes("PK")) keys.appendChild(el("span", {{ class: "keydot pk", "data-tip": "Primary key" }}));
    if ((c.badges || []).includes("FK")) keys.appendChild(el("span", {{ class: "keydot fk", "data-tip": "Foreign key" }}));

    const left = el("div", {{ class: "left" }}, [
      keys,
      el("div", {{ class: "name", "data-tip": c.name || "" }}, [document.createTextNode(c.name)]),
      el("div", {{ class: "type" }}, [document.createTextNode(c.type || "")]),
    ]);

    const badges = el("div", {{ class: "badges" }});
    (c.badges || []).forEach(b => {{
      badges.appendChild(el("span", {{ class: `badge ${{badgeClass(b)}}`, "data-tip": b }}, [document.createTextNode(b)]));
    }});

    return el("div", {{
      class: "col",
      id: `col_${{tableName}}_${{c.name}}`,
      "data-tip": colTitle,
    }}, [left, badges]);
  }};

  for (const t of MODEL.tables) {{
    const card = el("div", {{
      class: `table-card ${{(t.kind || "")}}`.trim(),
      id: `tbl_${{t.name}}`,
      style: `left:${{t.x}}px; top:${{t.y}}px;`
    }});

    const toggle = el("button", {{
      class: "toggle",
      title: "Collapse/expand columns",
      "aria-label": "Collapse/expand columns",
      type: "button",
    }});
    toggle.innerHTML = `<svg width="14" height="14" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M6 8l4 4 4-4" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`;

    const title = el("div", {{ class: "table-title" }}, [
      el("div", {{ class: "title-left" }}, [
        toggle,
        el("div", {{}}, [document.createTextNode(t.name)]),
      ]),
      el("div", {{ class: "chip" }}, [document.createTextNode(`${{t.columns.length}} cols`)]),
    ]);

    const cols = el("div", {{ class: "cols" }});

    const criticalCols = (t.columns || []).filter(isCritical);
    const optionalCols = (t.columns || []).filter(c => !isCritical(c));

    for (const c of criticalCols) {{
      cols.appendChild(renderCol(t.name, c));
    }}

    if (optionalCols.length) {{
      if (t.show_optional == null) t.show_optional = false;

      const details = el("details", {{ class: "optional" }});
      if (t.show_optional) details.setAttribute("open", "");

      const summary = el("summary", {{
        class: "optional-summary",
        "data-tip": `Optional columns (${{optionalCols.length}})`,
      }}, [
        el("span", {{}}, [document.createTextNode(`Optional columns (${{optionalCols.length}})`) ]),
        el("span", {{ class: "optional-caret", "aria-hidden": "true" }}, [document.createTextNode("▾")]),
      ]);

      const optionalWrap = el("div", {{ class: "optional-cols" }});
      for (const c of optionalCols) {{
        optionalWrap.appendChild(renderCol(t.name, c));
      }}

      details.appendChild(summary);
      details.appendChild(optionalWrap);
      details.addEventListener("toggle", () => {{
        t.show_optional = details.open;
        if (details.open) card.classList.add("focused");
        else card.classList.remove("focused");
        reflowColumns();
        computeContentBounds();
        applyZoom();
        scheduleRedraw();
      }});

      cols.appendChild(details);
    }}

    card.appendChild(title);
    card.appendChild(cols);
    viewport.appendChild(card);

    makeDraggable(card, title, t);
    card.addEventListener("click", (e) => {{
      // Avoid toggling selection when the user was dragging.
      if (card.dataset.dragged === "1") return;
      e.stopPropagation();
      selectTable(t.name);
    }});

    const setCollapsed = (collapsed) => {{
      cols.style.display = collapsed ? "none" : "";
      toggle.style.transform = collapsed ? "rotate(-90deg)" : "";
      toggle.setAttribute("aria-expanded", (!collapsed).toString());
      if (collapsed) card.classList.remove("focused");
    }};

    if (t.collapsed == null) t.collapsed = false; // expand by default
    setCollapsed(!!t.collapsed);
    // Prevent table dragging / background panning from stealing the toggle interaction.
    ["pointerdown","pointerup","pointercancel"].forEach((evt) => {{
      toggle.addEventListener(evt, (e) => {{
        e.stopPropagation();
      }});
    }});
    toggle.addEventListener("click", (e) => {{
      e.stopPropagation();
      t.collapsed = !t.collapsed;
      setCollapsed(!!t.collapsed);
      reflowColumns();
      computeContentBounds();
      applyZoom();
      scheduleRedraw();
    }});
  }}
}}

function getViewportRect() {{
  return viewport.getBoundingClientRect();
}}

function centerRight(cardEl) {{
  const r = cardEl.getBoundingClientRect();
  const c = getViewportRect();
  return {{ x: (r.right - c.left) / zoom, y: ((r.top - c.top) + r.height/2) / zoom }};
}}

function centerLeft(cardEl) {{
  const r = cardEl.getBoundingClientRect();
  const c = getViewportRect();
  return {{ x: (r.left - c.left) / zoom, y: ((r.top - c.top) + r.height/2) / zoom }};
}}

function clamp(n, lo, hi) {{
  return Math.max(lo, Math.min(hi, n));
}}

function reflowColumns() {{
  // Prevent overlaps when a table changes height (collapse/expand, optional columns).
  // Keeps X positions fixed (tier columns) and repacks Y positions within each column.
  const cards = [...viewport.querySelectorAll(".table-card")];
  if (!cards.length) return;

  const modelByName = new Map((MODEL.tables || []).map(t => [t.name, t]));
  const items = cards.map((card) => {{
    const name = (card.id || "").replace(/^tbl_/, "");
    const t = modelByName.get(name);
    return t ? {{
      card,
      t,
      name,
      x: t.x || 0,
      y: t.y || 0,
      h: card.offsetHeight || 220,
    }} : null;
  }}).filter(Boolean);

  // Group by approximate X (snap to nearest column within 60px).
  const groups = [];
  const getGroup = (x) => {{
    for (const g of groups) {{
      if (Math.abs(g.x - x) <= 60) return g;
    }}
    const ng = {{ x, items: [] }};
    groups.push(ng);
    return ng;
  }};

  for (const it of items) getGroup(it.x).items.push(it);
  groups.sort((a, b) => a.x - b.x);

  const topY = 120;
  const gapY = 52;
  for (const g of groups) {{
    g.items.sort((a, b) => (a.y - b.y) || a.name.localeCompare(b.name));
    let y = topY;
    for (const it of g.items) {{
      it.t.x = Math.round(g.x);
      it.t.y = Math.round(y);
      it.card.style.left = it.t.x + "px";
      it.card.style.top = it.t.y + "px";
      y += it.h + gapY;
    }}
  }}
}}

/* Hover tooltips (1s delay; avoids native title timing differences) */
let tipTimer = null;
let tipTarget = null;
let tipText = "";
let lastX = 0;
let lastY = 0;

function hideTip() {{
  if (tipTimer) {{
    clearTimeout(tipTimer);
    tipTimer = null;
  }}
  tipTarget = null;
  hoverTip.classList.remove("show");
  hoverTip.setAttribute("aria-hidden", "true");
}}

function placeTip(x, y) {{
  const pad = 14;
  const gap = 12;

  // Start near cursor.
  let left = x + gap;
  let top = y + gap;

  // Measure after setting text; keep on screen.
  const r = hoverTip.getBoundingClientRect();
  const maxLeft = window.innerWidth - r.width - pad;
  const maxTop = window.innerHeight - r.height - pad;

  left = clamp(left, pad, Math.max(pad, maxLeft));
  top = clamp(top, pad, Math.max(pad, maxTop));

  hoverTip.style.left = left + "px";
  hoverTip.style.top = top + "px";
}}

function showTip(text) {{
  if (!text) return;
  tipText = text;
  hoverTip.textContent = text;
  hoverTip.setAttribute("aria-hidden", "false");
  // Allow DOM to measure before clamping.
  hoverTip.classList.add("show");
  placeTip(lastX, lastY);
}}

function closestTipEl(node) {{
  if (!node || !node.closest) return null;
  return node.closest("[data-tip]");
}}

viewport.addEventListener("pointermove", (e) => {{
  lastX = e.clientX;
  lastY = e.clientY;
  if (hoverTip.classList.contains("show")) placeTip(lastX, lastY);
}}, {{ passive: true }});

viewport.addEventListener("pointerover", (e) => {{
  const el = closestTipEl(e.target);
  if (!el) return;

  const text = el.getAttribute("data-tip") || "";
  if (!text) return;

  // If we moved within the same element, keep current timer/tooltip.
  if (el === tipTarget) return;

  hideTip();
  tipTarget = el;
  tipTimer = setTimeout(() => {{
    if (tipTarget !== el) return;
    showTip(text);
  }}, 500);
}}, true);

viewport.addEventListener("pointerout", (e) => {{
  if (!tipTarget) return;
  const next = closestTipEl(e.relatedTarget);
  if (next && (next === tipTarget || tipTarget.contains(next))) return;
  hideTip();
}}, true);

wrap.addEventListener("scroll", hideTip, {{ passive: true }});
window.addEventListener("blur", hideTip);

/* Click-to-highlight direct connections */
function clearSelection() {{
  selectedTable = null;
  applySelection();
}}

function selectTable(name) {{
  selectedTable = name;
  applySelection();
}}

function applySelection() {{
  hideTip();

  // Clear previous styling.
  for (const card of viewport.querySelectorAll(".table-card")) {{
    card.classList.remove("selected", "related", "dimmed");
  }}
  for (const row of viewport.querySelectorAll(".col.selected-col")) {{
    row.classList.remove("selected-col");
  }}

  if (!selectedTable) {{
    scheduleRedraw();
    return;
  }}

  const related = new Set([selectedTable]);
  const colHits = [];
  for (const r of (MODEL.relationships || [])) {{
    if (r.from === selectedTable) {{
      related.add(r.to);
      colHits.push({{ table: r.from, col: r.from_col }});
      colHits.push({{ table: r.to, col: r.to_col }});
    }} else if (r.to === selectedTable) {{
      related.add(r.from);
      colHits.push({{ table: r.from, col: r.from_col }});
      colHits.push({{ table: r.to, col: r.to_col }});
    }}
  }}

  for (const card of viewport.querySelectorAll(".table-card")) {{
    const name = (card.id || "").replace(/^tbl_/, "");
    if (name === selectedTable) card.classList.add("selected");
    else if (related.has(name)) card.classList.add("related");
    else card.classList.add("dimmed");
  }}

  for (const hit of colHits) {{
    const el = document.getElementById(`col_${{hit.table}}_${{hit.col}}`);
    if (el) el.classList.add("selected-col");
  }}

  scheduleRedraw();
}}

// Clear selection when clicking the background (not a table).
wrap.addEventListener("click", (e) => {{
  if (e.target && e.target.closest && e.target.closest(".table-card")) return;
  if (e.target && e.target.closest && e.target.closest(".hint")) return;
  clearSelection();
}});

function anchorFromColumn(table, col, kind) {{
  const colEl = document.getElementById(`col_${{table}}_${{col}}`);
  const cardEl = document.getElementById(`tbl_${{table}}`);
  if (!colEl || !cardEl) return null;

  // Always anchor to the table's left/right edge (never bottom/top), but pick Y from the column row.
  const c = getViewportRect();
  const cardR = cardEl.getBoundingClientRect();
  const rowR = colEl.getBoundingClientRect();

  const edgePad = 2;
  const xPx = (kind === "pk")
    ? (cardR.right - c.left - edgePad)
    : (cardR.left - c.left + edgePad);

  const yPxRaw = (rowR.top - c.top) + rowR.height / 2;
  const yMin = (cardR.top - c.top) + 18;
  const yMax = (cardR.bottom - c.top) - 18;
  const yPx = clamp(yPxRaw, yMin, yMax);

  return {{ x: xPx / zoom, y: yPx / zoom }};
}}

function orthogonalRoundedPath(a, b) {{
  // Route with horizontal then vertical then horizontal, with rounded corners.
  const minOut = 60;
  const xOut = (b.x >= a.x + minOut)
    ? (a.x + b.x) / 2
    : (a.x + minOut);

  const p0 = a;
  const p1 = {{ x: xOut, y: a.y }};
  const p2 = {{ x: xOut, y: b.y }};
  const p3 = b;

  const r1 = clamp(Math.min(16, Math.abs(p1.x - p0.x) / 2, Math.abs(p2.y - p1.y) / 2), 0, 16);
  const r2 = clamp(Math.min(16, Math.abs(p3.x - p2.x) / 2, Math.abs(p2.y - p1.y) / 2), 0, 16);

  // Build path with quadratic corners at p1 and p2.
  const sx1 = (p1.x > p0.x) ? 1 : -1;
  const sy1 = (p2.y > p1.y) ? 1 : -1;
  const sx2 = (p3.x > p2.x) ? 1 : -1;

  const p0a = {{ x: p1.x - sx1 * r1, y: p0.y }};
  const p1b = {{ x: p1.x, y: p1.y + sy1 * r1 }};

  const p2a = {{ x: p2.x, y: p2.y - sy1 * r2 }};
  const p2b = {{ x: p2.x + sx2 * r2, y: p2.y }};

  return [
    `M ${{p0.x}} ${{p0.y}}`,
    `L ${{p0a.x}} ${{p0a.y}}`,
    `Q ${{p1.x}} ${{p1.y}} ${{p1b.x}} ${{p1b.y}}`,
    `L ${{p2a.x}} ${{p2a.y}}`,
    `Q ${{p2.x}} ${{p2.y}} ${{p2b.x}} ${{p2b.y}}`,
    `L ${{p3.x}} ${{p3.y}}`,
  ].join(" ");
}}

function drawEdges() {{
  // SVG uses the unscaled logical coordinate system (pre-zoom).
  wires.setAttribute("width", contentW);
  wires.setAttribute("height", contentH);
  // Preserve <defs> so arrow marker stays available.
  const defs = wires.querySelector("defs");
  wires.innerHTML = "";
  if (defs) wires.appendChild(defs);

  for (const rel of MODEL.relationships) {{
    const fromEl = document.getElementById(`tbl_${{rel.from}}`);
    const toEl = document.getElementById(`tbl_${{rel.to}}`);
    if (!fromEl || !toEl) continue;

    const a = anchorFromColumn(rel.from, rel.from_col, "pk") || centerRight(fromEl);
    const b = anchorFromColumn(rel.to, rel.to_col, "fk") || centerLeft(toEl);
    const d = orthogonalRoundedPath(a, b);
    const midX = (a.x + b.x) / 2;

    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", d);
    const isActive = !!selectedTable && (rel.from === selectedTable || rel.to === selectedTable);
    path.setAttribute("class", isActive ? "edge active" : (selectedTable ? "edge dimmed" : "edge"));
    path.setAttribute("marker-end", "url(#arrow)");
    path.dataset.from = rel.from;
    path.dataset.to = rel.to;
    path.dataset.fromCol = rel.from_col;
    path.dataset.toCol = rel.to_col;
    wires.appendChild(path);
  }}
}}

function makeDraggable(card, handle, modelRef) {{
  let dragging = false;
  let startX = 0, startY = 0;
  let origX = 0, origY = 0;
  let moved = false;

  const onDown = (e) => {{
    dragging = true;
    moved = false;
    card.dataset.dragged = "0";
    // Allow interactive controls inside the header (e.g., collapse button) to work.
    if (e.target && e.target.closest && e.target.closest("button")) {{
      dragging = false;
      return;
    }}
    handle.setPointerCapture(e.pointerId);
    startX = e.clientX;
    startY = e.clientY;
    origX = modelRef.x;
    origY = modelRef.y;
  }};

  const onMove = (e) => {{
    if (!dragging) return;
    const dx = (e.clientX - startX) / zoom;
    const dy = (e.clientY - startY) / zoom;
    if (!moved && (Math.abs(dx) + Math.abs(dy)) > 2) {{
      moved = true;
      card.dataset.dragged = "1";
    }}
    modelRef.x = Math.round(origX + dx);
    modelRef.y = Math.round(origY + dy);
    card.style.left = modelRef.x + "px";
    card.style.top = modelRef.y + "px";
    drawEdges();
  }};

  const onUp = (e) => {{
    dragging = false;
    try {{ handle.releasePointerCapture(e.pointerId); }} catch {{}}
    // Clear "dragged" shortly after so a subsequent click works.
    setTimeout(() => {{ card.dataset.dragged = "0"; }}, 0);
  }};

  handle.addEventListener("pointerdown", onDown);
  handle.addEventListener("pointermove", onMove);
  handle.addEventListener("pointerup", onUp);
  handle.addEventListener("pointercancel", onUp);
}}

renderTables();
layoutTablesAuto();
computeContentBounds();
applyZoom();
drawEdges();
window.addEventListener("resize", drawEdges);
wrap.addEventListener("scroll", scheduleRedraw, {{ passive: true }});

// Pan the whole diagram by dragging on the background.
let panning = false;
let panStartX = 0, panStartY = 0, panScrollL = 0, panScrollT = 0;
wrap.addEventListener("pointerdown", (e) => {{
  if (e.button !== 0) return;
  if (e.target && e.target.closest && e.target.closest(".hint")) return;
  if (e.target && e.target.closest && e.target.closest(".table-card")) return;
  panning = true;
  wrap.classList.add("panning");
  wrap.setPointerCapture(e.pointerId);
  panStartX = e.clientX;
  panStartY = e.clientY;
  panScrollL = wrap.scrollLeft;
  panScrollT = wrap.scrollTop;
}});
wrap.addEventListener("pointermove", (e) => {{
  if (!panning) return;
  const dx = e.clientX - panStartX;
  const dy = e.clientY - panStartY;
  wrap.scrollLeft = panScrollL - dx;
  wrap.scrollTop = panScrollT - dy;
}});
function endPan(e) {{
  if (!panning) return;
  panning = false;
  wrap.classList.remove("panning");
  try {{ wrap.releasePointerCapture(e.pointerId); }} catch {{}}
}}
wrap.addEventListener("pointerup", endPan);
wrap.addEventListener("pointercancel", endPan);

zoomInBtn.addEventListener("click", () => {{
  zoom *= 1.12;
  applyZoom();
}});
zoomOutBtn.addEventListener("click", () => {{
  zoom /= 1.12;
  applyZoom();
}});

zoomFitBtn.addEventListener("click", () => {{
  hideTip();
  computeContentBounds();

  // Fit the full diagram bounds into the visible area.
  // Account for wrap padding + hint bar; keep a bit of margin.
  const margin = 48;
  const availW = Math.max(320, wrap.clientWidth - margin);
  const availH = Math.max(260, wrap.clientHeight - 140);

  const z = Math.min(availW / contentW, availH / contentH);
  zoom = clamp(z, minZoom, maxZoom);
  applyZoom();

  // Center the diagram in the scroll viewport.
  const canvasW = contentW * zoom;
  const canvasH = contentH * zoom;
  wrap.scrollLeft = Math.max(0, (canvasW - wrap.clientWidth) / 2);
  wrap.scrollTop = Math.max(0, (canvasH - wrap.clientHeight) / 2);
  scheduleRedraw();
}});

function resetFormatting() {{
  clearSelection();
  for (const t of MODEL.tables) {{
    // Reset user-changed layout.
    t.x = 80;
    t.y = 120;
    // Reset UI state.
    t.collapsed = true;
    t.show_optional = false;
  }}
  renderTables();
  layoutTablesAuto();
  computeContentBounds();
  // Auto-fit after reset so everything is visible.
  zoomFitBtn.click();
}}

resetFormatBtn.addEventListener("click", resetFormatting);

wrap.addEventListener("wheel", (e) => {{
  // Zoom the whole diagram on scroll.
  e.preventDefault();
  const before = zoom;
  const factor = Math.exp(-e.deltaY * 0.0014);
  zoom = before * factor;

  // Keep the point under the cursor stable while zooming.
  const canvasRect = canvas.getBoundingClientRect();
  const cx = e.clientX - canvasRect.left;
  const cy = e.clientY - canvasRect.top;
  const logicalX = (wrap.scrollLeft + cx) / before;
  const logicalY = (wrap.scrollTop + cy) / before;

  applyZoom();
  wrap.scrollLeft = logicalX * zoom - cx;
  wrap.scrollTop = logicalY * zoom - cy;
  scheduleRedraw();
}}, {{ passive: false }});
</script>
</body>
</html>
"""


def list_tables(con: sqlite3.Connection) -> List[str]:
    rows = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def table_columns(con: sqlite3.Connection, table: str) -> List[Dict]:
    cols = con.execute(f"PRAGMA table_info('{table}')").fetchall()
    # cols: cid, name, type, notnull, dflt_value, pk
    uniques = unique_columns(con, table)
    fks = fk_columns(con, table)

    out = []
    for _, name, coltype, notnull, _, pk in cols:
        badges = []
        if pk:
            badges.append("PK")
        if name in fks:
            badges.append("FK")
        if name in uniques:
            badges.append("UNIQUE")
        if notnull:
            badges.append("NOT NULL")

        out.append(
            {
                "name": name,
                "type": (coltype or "").lower(),
                "badges": badges,
            }
        )
    return out


def unique_columns(con: sqlite3.Connection, table: str) -> set:
    # PRAGMA index_list gives indexes; PRAGMA index_info gives columns for each index
    uniques = set()
    for idx_name, unique in [
        (r[1], r[2]) for r in con.execute(f"PRAGMA index_list('{table}')").fetchall()
    ]:
        if unique != 1:
            continue
        for colrow in con.execute(f"PRAGMA index_info('{idx_name}')").fetchall():
            # seqno, cid, name
            uniques.add(colrow[2])
    return uniques


def fk_columns(con: sqlite3.Connection, table: str) -> set:
    # PRAGMA foreign_key_list: id, seq, table, from, to, on_update, on_delete, match
    fks = con.execute(f"PRAGMA foreign_key_list('{table}')").fetchall()
    return {r[3] for r in fks}


def relationships(con: sqlite3.Connection, tables: List[str]) -> List[Dict]:
    rels = []
    for table in tables:
        fks = con.execute(f"PRAGMA foreign_key_list('{table}')").fetchall()
        for r in fks:
            # r: id, seq, table, from, to, on_update, on_delete, match
            ref_table = r[2]
            from_col = r[4]  # referenced column on parent
            to_col = r[3]  # fk column on child
            if ref_table in tables:
                rels.append(
                    {
                        "from": ref_table,
                        "from_col": from_col,
                        "to": table,
                        "to_col": to_col,
                        "label": "1 — *",
                    }
                )
    # de-dupe
    seen = set()
    deduped = []
    for r in rels:
        key = (r["from"], r["from_col"], r["to"], r["to_col"], r["label"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    return deduped


def layout_tables(tables: List[str]) -> Dict[str, Tuple[int, int]]:
    # simple layout: two columns flowing down
    x_left, x_right = 80, 520
    y = 120
    positions = {}
    for i, t in enumerate(tables):
        x = x_left if i % 2 == 0 else x_right
        positions[t] = (x, y if i % 2 == 0 else y + 20)
        if i % 2 == 1:
            y += 220
    return positions


def main(db_path: str = "mini.db", out_html: str = "erd.html") -> None:
    script_dir = Path(__file__).resolve().parent
    db_file = Path(db_path)
    if not db_file.is_absolute():
        # Prefer resolving relative paths from this script's directory so running from other
        # working directories still works.
        db_file = (script_dir / db_file).resolve()

    if not db_file.exists():
        raise SystemExit(
            f"Database not found: {db_file}\n"
            f"Create it by running models.py, or pass an explicit path: "
            f"python generate_erd_html.py /path/to/mini.db"
        )

    con = sqlite3.connect(str(db_file))
    try:
        tables = list_tables(con)
        if not tables:
            raise SystemExit(f"No tables found in {db_file}. Did you run python models.py?")

        pos = layout_tables(tables)

        def table_kind(name: str) -> str:
            n = name.lower()
            if n.startswith("fact_"):
                return "fact"
            if n.startswith("dim_"):
                return "dim"
            if n.startswith("bridge_"):
                return "dim"
            if n.startswith("rpt_"):
                return "report"
            return ""

        model = {
            "tables": [
                {
                    "name": t,
                    "kind": table_kind(t),
                    "x": pos[t][0],
                    "y": pos[t][1],
                    "columns": table_columns(con, t),
                }
                for t in tables
            ],
            "relationships": relationships(con, tables),
        }

        out_path = Path(out_html)
        if out_path.parent == Path("."):
            out_path = Path(__file__).resolve().parent / out_path.name

        html = HTML_TEMPLATE.format(
            model_json=json.dumps(model, indent=2),
            db_name=db_file.name,
            out_name=out_path.name,
        )
        out_path.write_text(html, encoding="utf-8")
        print(f"Wrote {out_path} from {db_path}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
