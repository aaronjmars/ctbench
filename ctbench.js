const $ = (s) => document.querySelector(s);
const NS = "http://www.w3.org/2000/svg";
const X_MARK = '<svg class="xmark" viewBox="0 0 24 24" aria-hidden="true" width="11" height="11"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>';
const SLUGS = ["ansem", "pons", "stonk", "pump", "ai", "cashcat"];
// Preferred spoke order. Crypto-native aspects (narrative, momentum, safety) are
// filled once the contract's new enum is re-labeled; older labels still resolve.
const ASPECT_ORDER = ["price", "narrative", "momentum", "tech", "tokenomics", "community", "safety", "team", "security"];
const ASPECT_LABEL = { price: "Price", narrative: "Narrative", momentum: "Momentum", tech: "Tech", tokenomics: "Tokenomics", community: "Community", safety: "Safety", team: "Team", security: "Security", other: "Other" };
// Radar spokes are data-driven: only aspects with signal in >= 2 tokens (set in init()).
let ASPECTS = ASPECT_ORDER.slice();

const el = (tag, attrs = {}) => {
  const n = document.createElementNS(NS, tag);
  Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, v));
  return n;
};
const addText = (svg, x, y, t, c = "r-label", anchor = "start") => {
  const n = el("text", { x, y, class: c, "text-anchor": anchor });
  n.textContent = t;
  svg.append(n);
  return n;
};
const fmt = (n) => new Intl.NumberFormat("en-US").format(n || 0);
const esc = (s) =>
  String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const netClass = (net) => (net > 5 ? "positive" : net < -5 ? "negative" : "neutral");
const signedPct = (n) => `${n > 0 ? "+" : ""}${Math.round(n)}`;

// signal share of positive for a token/aspect: pos / (pos+neg+mixed)
function aspectShare(ap) {
  if (!ap) return { v: 0, n: 0 };
  const pos = ap.positive || 0, neg = ap.negative || 0, mix = ap.mixed || 0, n = pos + neg + mix;
  return { v: n ? pos / n : 0, n };
}

let STATE = { index: [], sum: {}, ev: {}, allEv: [] };

/* ---------- shared chart tooltip (follows cursor) ---------- */
const TIP = document.createElement("div");
TIP.className = "chart-tip";
TIP.hidden = true;
(document.body || document.documentElement).append(TIP);
function moveTip(x, y) {
  const pad = 14, w = TIP.offsetWidth, vw = window.innerWidth;
  TIP.style.left = Math.min(x + pad, vw - w - 8) + "px";
  TIP.style.top = y + pad + "px";
}
function showTip(html, x, y) { TIP.innerHTML = html; TIP.hidden = false; moveTip(x, y); }
const hideTip = () => { TIP.hidden = true; };
document.addEventListener("mousemove", (e) => { if (!TIP.hidden) moveTip(e.clientX, e.clientY); });
// delegate: any element under `root` matching `sel` with a data-tip shows it
function wireTip(root, sel) {
  const r = typeof root === "string" ? $(root) : root;
  if (!r) return;
  r.addEventListener("mouseover", (e) => { const t = e.target.closest(sel); if (t && t.dataset.tip) showTip(t.dataset.tip, e.clientX, e.clientY); });
  r.addEventListener("mouseout", (e) => { if (e.target.closest(sel)) hideTip(); });
}

/* ---------- evidence cards ---------- */
function card(row) {
  const l = row.label || {}, s = l.sentiment || {}, pol = s.polarity || "none";
  const tags =
    `<span class="tag ${pol === "negative" ? "neg" : pol === "mixed" ? "mix" : ""}">${esc(pol)}</span>` +
    (l.firsthand ? `<span class="tag fh">firsthand</span>` : "") +
    (l.bot_or_shill ? `<span class="tag neg">shill</span>` : "");
  const verdict = `$${esc(row.token)}${s.aspect ? ` <em>&middot;</em> ${esc(s.aspect)}` : ""}`;
  const why = l.reason && l.reason.quote ? `<p class="why">${esc(l.reason.quote)}</p>` : "";
  return `<a class="counted-tweet pol-${esc(pol)}" href="${esc(row.url)}" target="_blank" rel="noreferrer"><header><span><b>${verdict}</b><small>@${esc(row.author)}</small></span></header><p>${esc(row.text)}</p>${why}<footer>${tags}</footer><span class="open" aria-hidden="true">${X_MARK}<i>&#8599;</i></span></a>`;
}
const renderCards = (root, rows, empty = "No posts here.") => {
  root.innerHTML = rows.length ? rows.map(card).join("") : `<div class="evidence-empty">${empty}</div>`;
};

/* ---------- sentiment rows (the leaderboard) ---------- */
function sentimentRows(root) {
  root.innerHTML = "";
  STATE.index.forEach((e, rank) => {
    const s = STATE.sum[e.slug], p = s.polarity || {};
    const pos = p.positive || 0, mix = p.mixed || 0, neg = p.negative || 0, tot = pos + mix + neg;
    const net = e.sentiment_score;
    const row = document.createElement("div");
    row.className = "sentiment-row";
    row.dataset.slug = e.slug;
    const w = (x) => (tot ? (x / tot) * 100 : 0);
    const seg = (cls, lbl, c) => c ? `<span class="${cls}" style="width:${w(c)}%" data-tip="${lbl} &middot; ${c} &middot; ${Math.round(w(c))}%"></span>` : "";
    row.innerHTML = `<div class="sentiment-name"><strong>#${rank + 1} $${esc(e.token)}</strong><small>${esc(e.name)} &middot; ${esc(e.chain)} &middot; across ${e.signal_n} posts</small></div><div class="sentiment-main"><div class="stack" aria-label="${pos} positive, ${mix} mixed, ${neg} negative">${seg("positive", "Positive", pos)}${seg("mixed", "Mixed", mix)}${seg("negative", "Negative", neg)}</div><div class="metric-tail ${netClass(net)}">${signedPct(net)}</div></div>`;
    row.onclick = () => selectToken(e.slug);
    root.append(row);
  });
}

/* ---------- stance: who is talking (holder/trader/builder/observer) ---------- */
const STANCE_ORDER = ["holder", "trader", "builder", "observer"];
function stanceRows(root) {
  root.innerHTML = "";
  STATE.index.forEach((e) => {
    const s = STATE.sum[e.slug], st = s.stance || {}, ac = s.action || {};
    const tot = STANCE_ORDER.reduce((a, k) => a + (st[k] || 0), 0) || 1;
    const seg = STANCE_ORDER.map((k) => {
      const c = st[k] || 0;
      return c ? `<span class="st-${k}" style="width:${(c / tot) * 100}%" data-tip="${k} &middot; ${c} &middot; ${Math.round((c / tot) * 100)}%"></span>` : "";
    }).join("");
    const buy = (ac.buy || 0) + (ac.entry || 0), sell = (ac.sell || 0) + (ac.exit || 0);
    const net = buy - sell;
    const intent = net > 0 ? `+${net} buy` : net < 0 ? `${net} sell` : "flat";
    root.insertAdjacentHTML("beforeend",
      `<div class="stance-row"><div class="stance-name"><strong>$${esc(e.token)}</strong><small>across ${e.signal_n} posts</small></div>` +
      `<div class="stance-bar" aria-label="stance mix">${seg}</div>` +
      `<div class="stance-intent ${net >= 0 ? "positive" : "negative"}">${intent}</div></div>`);
  });
}

/* ---------- radar: tokens x aspects ----------
   Spokes are the reasons EVERY shown token has signal on, recomputed as you
   toggle. That keeps each shape complete instead of collapsing a token to the
   centre on a reason it simply has no posts about. */
function radar(svg, legend, defaults) {
  const cx = 280, cy = 280, R = 200;
  const aspN = (slug, id) => {
    const v = (STATE.sum[slug].aspect_polarity || {})[id] || {};
    return (v.positive || 0) + (v.negative || 0) + (v.mixed || 0);
  };
  const totN = (slug) => ASPECT_ORDER.concat(["other"]).reduce((a, id) => a + aspN(slug, id), 0) || 1;
  // value = share of the token's firsthand talk about that reason (always > 0
  // where it has posts, so shapes stay full instead of zeroing on a sparse
  // reason). Per-reason sentiment lives in the book below.
  const share = (slug, id) => ({ v: aspN(slug, id) / totN(slug), n: aspN(slug, id) });
  function dimsFor(list) {
    if (!list.length) return ASPECTS.slice();
    let d = ASPECT_ORDER.filter((a) => list.every((s) => share(s, a).n > 0));
    if (d.length < 3) d = ASPECT_ORDER.filter((a) => list.some((s) => share(s, a).n > 0));
    if (d.length < 3) d = ASPECTS.slice();
    return d;
  }
  let sel = defaults.filter((k) => STATE.sum[k]).slice(0, 6), hover = null;

  function draw() {
    const shown = [...sel, ...(hover && !sel.includes(hover) ? [hover] : [])];
    const base = shown.length ? shown : STATE.index.map((e) => e.slug);
    const dims = dimsFor(base), n = dims.length;
    const angle = (i) => -Math.PI / 2 + (i * 2 * Math.PI) / n;
    const rad = (v) => R * Math.max(0, Math.min(1, v));
    const pt = (i, v) => [cx + Math.cos(angle(i)) * rad(v), cy + Math.sin(angle(i)) * rad(v)];
    // normalize each token to its own top reason: shapes compare by profile
    // (what a crowd talks about), not by raw volume.
    const maxBy = {};
    base.forEach((k) => { maxBy[k] = Math.max(0.01, ...dims.map((id) => share(k, id).v)); });
    const norm = (k, id) => share(k, id).v / maxBy[k];
    svg.innerHTML = "";
    [0, 0.25, 0.5, 0.75, 1].forEach((v) => {
      const d = dims.map((_, i) => pt(i, v)).map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ") + "Z";
      svg.append(el("path", { d, class: `r-ring${v === 1 ? " outer" : v === 0 ? " zero" : ""}` }));
    });
    dims.forEach((id, i) => {
      const [x, y] = pt(i, 1);
      svg.append(el("line", { x1: cx, y1: cy, x2: x, y2: y, class: "r-axis" }));
      const [lx, ly] = pt(i, 1.16);
      const anchor = Math.abs(Math.cos(angle(i))) < 0.2 ? "middle" : Math.cos(angle(i)) > 0 ? "start" : "end";
      addText(svg, lx, ly + 4, ASPECT_LABEL[id], "r-label", anchor);
    });
    shown.forEach((k) => {
      const i = sel.indexOf(k);
      const d = dims.map((id, di) => pt(di, norm(k, id))).map(([x, y], di) => `${di ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ") + "Z";
      const p = el("path", { d, class: `r-poly${i >= 0 ? " on p" + i : " hover"}` });
      p.dataset.slug = k;
      p.addEventListener("mouseenter", () => { if (hover !== k) { hover = k; draw(); } });
      p.addEventListener("mouseleave", () => { hover = null; draw(); });
      svg.append(p);
    });
    const marks = el("g"); svg.append(marks);
    shown.forEach((k) => {
      const i = sel.indexOf(k);
      dims.forEach((id, di) => {
        const { v, n: cnt } = share(k, id), [x, y] = pt(di, norm(k, id));
        const c = el("circle", { cx: x, cy: y, r: 3.4, class: `r-pt ${i >= 0 ? "p" + i : "hov"}${cnt < 5 ? " thin" : ""}` });
        c.dataset.tip = `$${STATE.sum[k].token} &middot; ${ASPECT_LABEL[id]} &middot; ${Math.round(v * 100)}% of talk &middot; n${cnt}`;
        marks.append(c);
      });
    });
    legend.querySelectorAll(".legend-chip").forEach((b) => {
      const i = sel.indexOf(b.dataset.slug);
      b.className = `legend-chip${i >= 0 ? " on p" + i : ""}${hover === b.dataset.slug ? " hov" : ""}`;
    });
    const note = legend.querySelector(".legend-note");
    if (note) note.textContent = `${sel.length}/6 shown - spokes are reasons every shown token has`;
  }

  legend.innerHTML =
    STATE.index.map((e) => `<button class="legend-chip" data-slug="${e.slug}"><i></i><b></b><span>$${esc(e.token)}</span><small>${e.signal_n} posts</small></button>`).join("") +
    '<p class="legend-note"></p>';
  legend.addEventListener("click", (ev) => {
    const b = ev.target.closest(".legend-chip"); if (!b) return;
    const k = b.dataset.slug;
    if (sel.includes(k)) sel = sel.filter((x) => x !== k);
    else { if (sel.length >= 6) sel.shift(); sel.push(k); }
    draw();
  });
  legend.addEventListener("mouseover", (ev) => {
    const b = ev.target.closest(".legend-chip"); if (!b || sel.includes(b.dataset.slug) || hover === b.dataset.slug) return;
    hover = b.dataset.slug; draw();
  });
  legend.addEventListener("mouseleave", () => { if (hover) { hover = null; draw(); } });
  draw();
}

/* ---------- aspect book (per token) ---------- */
function buildBook(root) {
  root.innerHTML =
    `<div class="book-picker">${STATE.index.map((e) => `<button class="pick" data-slug="${e.slug}"><span>$${esc(e.token)}</span></button>`).join("")}</div><div class="book-stage"></div>`;
  root.querySelector(".book-picker").onclick = (ev) => {
    const b = ev.target.closest(".pick"); if (b) selectToken(b.dataset.slug);
  };
}
function renderBookPage(slug) {
  const s = STATE.sum[slug], ap = s.aspect_polarity || {};
  const praise = [], complaints = [];
  ASPECT_ORDER.concat(["other"]).forEach((id) => {
    const a = ap[id]; if (!a) return;
    const pos = a.positive || 0, neg = a.negative || 0, mix = a.mixed || 0;
    if (pos) praise.push([id, pos]);
    if (neg || mix) complaints.push([id, neg, mix]);
  });
  praise.sort((a, b) => b[1] - a[1]);
  complaints.sort((a, b) => b[1] + b[2] - (a[1] + a[2]));
  const lname = (id) => ASPECT_LABEL[id] || id;
  const pList = praise.length ? praise.map(([id, c]) => `<li><span>${lname(id)}</span><b>+${c}</b></li>`).join("") : '<li><span>nothing notable</span><b></b></li>';
  const cList = complaints.length ? complaints.map(([id, neg, mix]) => `<li><span>${lname(id)}</span><b>${neg ? "-" + neg : ""}${neg && mix ? " " : ""}${mix ? "~" + mix : ""}</b></li>`).join("") : '<li><span>few complaints</span><b></b></li>';
  const net = s.sentiment_score, p = s.polarity || {};
  const rows = STATE.ev[slug].filter((r) => r.signal);
  const sorted = rows.sort((a, b) => {
    const rank = (x) => (x.label.sentiment?.polarity === "positive" ? 0 : x.label.sentiment?.polarity === "negative" ? 1 : 2);
    return rank(a) - rank(b);
  }).slice(0, 30);
  const stage = document.querySelector(".book-stage");
  stage.innerHTML =
    `<section class="book-page"><header class="book-head"><div class="book-name"><strong>$${esc(s.token)}</strong></div><div class="book-meta"><b class="${netClass(net)}">${signedPct(net)}</b><span>${s.signal_n} firsthand &middot; ${p.positive || 0} / ${p.mixed || 0} / ${p.negative || 0}</span></div></header>` +
    `<div class="drawer"><div class="aspects"><div class="positive"><h4>Praised for</h4><ul>${pList}</ul></div><div class="negative"><h4>Knocked for</h4><ul>${cList}</ul></div></div><div class="evidence-scroll"></div></div></section>`;
  renderCards(stage.querySelector(".evidence-scroll"), sorted, "No firsthand signal posts.");
}

function selectToken(slug) {
  document.querySelectorAll("#book .pick").forEach((b) => b.classList.toggle("on", b.dataset.slug === slug));
  document.querySelectorAll("#sentimentRows .sentiment-row").forEach((r) => r.classList.toggle("open", r.dataset.slug === slug));
  renderBookPage(slug);
}

/* ---------- evidence chapter (all tokens) ---------- */
function renderEvidence(filter) {
  const rows = STATE.allEv.filter((r) => {
    const pol = r.label.sentiment?.polarity;
    if (filter === "all") return true;
    if (filter === "signal") return r.signal;
    if (filter === "shill") return r.label.bot_or_shill;
    return r.signal && pol === filter;
  });
  renderCards($("#evidenceScroll"), rows.slice(0, 120), "No posts match.");
}

/* ---------- hero mural ---------- */
function mural(rows) {
  const root = $("#muralGrid");
  const posts = rows.filter((r) => r.signal && r.text);
  if (!posts.length) { root.innerHTML = '<p class="mural-loading">The conversation is quiet.</p>'; return; }
  for (let i = posts.length - 1; i > 0; i--) { const k = Math.floor(Math.random() * (i + 1)); [posts[i], posts[k]] = [posts[k], posts[i]]; }
  const c = (p) => {
    const pol = p.label.sentiment?.polarity || "none";
    return `<a class="mural-card pol-${esc(pol)}" href="${esc(p.url)}" target="_blank" rel="noreferrer"><header><span><b>@${esc(p.author)}</b><small>$${esc(p.token)} <em class="pol pol-${esc(pol)}">${esc(pol)}</em></small></span></header><p>${esc(p.text)}</p><span class="mural-open" aria-hidden="true">${X_MARK}<i>&#8599;</i></span></a>`;
  };
  root.innerHTML = posts.slice(0, 6).map(c).join("");
}

async function init() {
  try {
    const index = await fetch("data/public/index.json").then((r) => r.json());
    STATE.index = index;
    const sums = await Promise.all(index.map((e) => fetch(`data/public/${e.slug}/summary.json`).then((r) => r.json())));
    const evs = await Promise.all(index.map((e) => fetch(`data/public/${e.slug}/evidence.json`).then((r) => r.json())));
    index.forEach((e, i) => {
      STATE.sum[e.slug] = sums[i];
      STATE.ev[e.slug] = evs[i].map((r) => ({ ...r, slug: e.slug, token: e.token }));
      STATE.allEv.push(...STATE.ev[e.slug]);
    });

    // manifest (sum across tokens)
    const T = index.reduce((a, e) => {
      a.labeled += e.totals.labeled; a.relevant += e.totals.relevant;
      a.firsthand += e.totals.firsthand; a.shill += e.totals.shill; return a;
    }, { labeled: 0, relevant: 0, firsthand: 0, shill: 0 });
    $("#statPosts").textContent = fmt(T.labeled);
    $("#statRelevant").textContent = fmt(T.relevant);
    $("#statFirsthand").textContent = fmt(T.firsthand);
    $("#statShill").textContent = fmt(T.shill);

    $("#trackedTokens").innerHTML = index.map((e) => `<span>$${esc(e.token)}<small style="color:var(--b48)">${esc(e.chain)}</small></span>`).join("");

    sentimentRows($("#sentimentRows"));
    stanceRows($("#stanceRows"));

    // data-driven radar spokes: keep an aspect only if it is broad (>= 2 tokens)
    // AND carries real weight (>= 4% of total aspect volume). Drops thin spokes
    // that would bowtie the chart; auto-admits new aspects once they matter.
    const vol = {}, tokenCount = {};
    index.forEach((e) => {
      const ap = STATE.sum[e.slug].aspect_polarity || {};
      ASPECT_ORDER.forEach((k) => {
        const v = ap[k]; if (!v) return;
        const n = (v.positive || 0) + (v.negative || 0) + (v.mixed || 0);
        if (n > 0) { vol[k] = (vol[k] || 0) + n; tokenCount[k] = (tokenCount[k] || 0) + 1; }
      });
    });
    // show every aspect that carries signal in at least two tokens (drops only
    // spokes that are empty or a single token's quirk); no top-weight cap.
    ASPECTS = ASPECT_ORDER.filter((a) => (tokenCount[a] || 0) >= 2);
    if (ASPECTS.length < 3) ASPECTS = ASPECT_ORDER.filter((a) => vol[a]);
    const byN = [...index].sort((a, b) => b.signal_n - a.signal_n).map((e) => e.slug);
    radar($("#radar"), $("#radarLegend"), byN.slice(0, 6));

    // hover tooltips on every bar segment + radar point
    wireTip("#sentimentRows", ".stack span");
    wireTip("#stanceRows", ".stance-bar span");
    wireTip("#radar", ".r-pt");

    buildBook($("#book"));

    $("#evidenceMode").onclick = (ev) => {
      const b = ev.target.closest("button"); if (!b) return;
      [...ev.currentTarget.children].forEach((x) => x.classList.toggle("on", x === b));
      renderEvidence(b.dataset.f);
    };
    renderEvidence("signal");

    mural(STATE.allEv);
    selectToken(index[0].slug);
  } catch (err) {
    console.error(err);
    document.body.insertAdjacentHTML("beforeend", `<p style="padding:24px;color:var(--b48)">data could not load: ${esc(err.message)}. Run the pipeline first.</p>`);
  }
}
init();

/* info-tap toggle for touch */
document.addEventListener("click", (e) => {
  const i = e.target.closest(".info");
  document.querySelectorAll(".info.open").forEach((x) => x !== i && x.classList.remove("open"));
  if (i) { e.preventDefault(); i.classList.toggle("open"); }
});
