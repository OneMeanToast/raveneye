/* RavenEye globe — RTB / architecture explainer drawer.
 *
 * A slide-in side drawer that walks a prospective audience through the
 * four-layer architecture (Demand → Supply → Mechanism → Delivery) with
 * live numbers from the loaded scenario rendered against each layer.
 *
 * Toggle from the ABOUT button in the header, or by pressing `?`. Press
 * Esc or click outside the drawer to dismiss.
 */
(function (global) {
  "use strict";

  function _pct(x) {
    return (x != null) ? (x * 100).toFixed(1) + "%" : "—";
  }

  function _fmt(x) {
    return (x == null) ? "—" : String(x);
  }

  function _section(title, lead, rows) {
    const root = document.createElement("section");
    root.className = "explainer-section";
    if (title) {
      const h = document.createElement("h3");
      h.textContent = title;
      root.appendChild(h);
    }
    if (lead) {
      const p = document.createElement("p");
      p.innerHTML = lead;
      root.appendChild(p);
    }
    if (rows && rows.length) {
      const dl = document.createElement("dl");
      for (const [k, v, hint] of rows) {
        const dt = document.createElement("dt");
        dt.textContent = k;
        const dd = document.createElement("dd");
        const span = document.createElement("span");
        span.className = "stat";
        span.textContent = _fmt(v);
        dd.appendChild(span);
        if (hint) {
          const small = document.createElement("small");
          small.textContent = "  " + hint;
          dd.appendChild(small);
        }
        dl.appendChild(dt); dl.appendChild(dd);
      }
      root.appendChild(dl);
    }
    return root;
  }

  function _renderContent(scenario) {
    const m = scenario.meta || {};
    const root = document.createElement("div");
    root.className = "explainer-body";

    // Hero block
    const hero = document.createElement("div");
    hero.className = "explainer-hero";
    hero.innerHTML = `
      <div class="explainer-eyebrow">RAVENEYE</div>
      <h2>Real-time bidding for orbital collection.</h2>
      <p>
        Modern intelligence collection isn't a single-mission problem. CENTCOM,
        NRO, allied maritime HQs, and commercial war-risk insurers all want
        imagery of the same chokepoint — but they value events through
        different utility functions. RavenEye applies the architecture that
        scaled programmatic advertising to multi-constellation EO tasking,
        and lets you A/B different auction mechanisms on a deterministic
        scenario before any of them touch a real spacecraft.
      </p>
    `;
    root.appendChild(hero);

    root.appendChild(_section(
      "Why RTB?",
      `Three properties make a real-time auction the right shape for this:`,
      null,
    ));

    const why = document.createElement("ul");
    why.className = "explainer-list";
    why.innerHTML = `
      <li><strong>Multi-stakeholder utility.</strong>
        Each bidder values events through their own weights table. The same
        <code>KINETIC_STRIKE</code> at Siri Island produces a sev-5/0.95 bid
        from CENTCOM J2 (force protection) and a sev-5/1.6 bid from a
        commercial war-risk insurer (premium repricing) — same event,
        different priorities, no information lost.</li>
      <li><strong>Mechanism-pluggable.</strong>
        Greedy first-come-first-served → sequential single-item auctions →
        CBBA / VCG combinatorial mechanisms. Same demand stream, swappable
        allocator. Welfare metrics let you A/B them.</li>
      <li><strong>Deterministic and auditable.</strong>
        Every allocation has a rationale, a welfare contribution, a
        delivery timeline. Same seed → byte-identical scenario JSON. No
        black box.</li>
    `;
    root.appendChild(why);

    root.appendChild(_section(
      "The four-layer architecture",
      `Each layer is independently swappable. Layers communicate through plain JSON, so a third party can drop in their own mechanism without touching demand or supply.`,
      null,
    ));

    // Layer diagram
    const layers = document.createElement("div");
    layers.className = "explainer-layers";
    layers.innerHTML = `
      <div class="layer demand">
        <div class="layer-name">DEMAND</div>
        <div class="layer-rule">events × stakeholders → bids</div>
        <div class="layer-stat">${_fmt(m.n_events)} events · ${_fmt(m.n_bids)} bids</div>
      </div>
      <div class="layer-arrow">↓</div>
      <div class="layer supply">
        <div class="layer-name">SUPPLY</div>
        <div class="layer-rule">TLEs × targets → access windows</div>
        <div class="layer-stat">${_fmt(m.n_satellites)} sats · ${_fmt(m.n_constellations)} vendors · ${_fmt(m.n_access_windows)} windows</div>
      </div>
      <div class="layer-arrow">↓</div>
      <div class="layer mechanism">
        <div class="layer-name">MECHANISM</div>
        <div class="layer-rule">bids + windows → allocations</div>
        <div class="layer-stat">${_fmt(m.mechanism)} · ${_fmt(m.n_scheduled)} scheduled · welfare ${_fmt(m.total_welfare)}</div>
      </div>
      <div class="layer-arrow">↓</div>
      <div class="layer delivery">
        <div class="layer-name">DELIVERY</div>
        <div class="layer-rule">collection → processing → handoff</div>
        <div class="layer-stat">${_fmt(m.n_delivered)} delivered · ${_pct(m.delivery_rate)} rate</div>
      </div>
    `;
    root.appendChild(layers);

    // Layer-by-layer detail sections
    root.appendChild(_section(
      "Demand — events ≠ bids",
      `An <strong>event</strong> is a world-state change. A <strong>bid</strong> is what a stakeholder produces when they observe the event through their own utility weights. Don't collapse them — that's the multi-utility surface that makes the sim worth running.`,
      [
        ["events fired",       m.n_events],
        ["stakeholder bids",   m.n_bids,
            "≈ 4× events; one bid per stakeholder per event"],
        ["scenario tempo",     `${_fmt(m.duration_hours)}h across ${(m.phases||[]).length} phases`],
      ],
    ));

    root.appendChild(_section(
      "Supply — real orbits, not stand-ins",
      `Skyfield/SGP4 propagation against committed TLEs. Per-window quality scoring blends elevation, sun angle, and off-nadir geometry. SAR rigs ignore the sun term. Tests pin a seed-42 invariant so a refactor that breaks the math gets caught.`,
      [
        ["satellites",         m.n_satellites],
        ["constellations",     m.n_constellations],
        ["access windows",     m.n_access_windows],
        ["min elevation",      m.min_elevation_deg + "°"],
      ],
    ));

    root.appendChild(_section(
      "Mechanism — where the auction lives",
      `<code>greedy_priority</code> matches the highest-priority bid to the earliest available window. <code>ssi</code> (sequential single-item auction) hands every bid the welfare-maximizing window across all candidates. SSI must beat greedy on welfare or the complexity isn't earning its keep.`,
      [
        ["mechanism",          m.mechanism],
        ["scheduled",          m.n_scheduled,  "matched to a window"],
        ["dropped",            m.n_dropped,    "no feasible match (target / deadline / band)"],
        ["drop rate",          _pct(m.drop_rate)],
        ["total welfare",      m.total_welfare,
            "Σ priority × quality across SCHEDULED rows"],
      ],
    ));

    root.appendChild(_section(
      "Delivery — what happens after the shot",
      `Per-vendor processing latency + delivery latency. The success roll for processing is modulated by window quality (cloud cover, sensor calibration, frame quality). LTIOV deadlines are enforced — a delivered image past its deadline counts as <code>DEADLINE_MISSED</code>, not <code>DELIVERED</code>.`,
      [
        ["delivered",          m.n_delivered],
        ["processing failed",  m.n_processing_failed],
        ["deadline missed",    m.n_deadline_missed],
        ["delivery rate",      _pct(m.delivery_rate)],
        ["proc. success rate", _pct(m.processing_success_rate)],
      ],
    ));

    root.appendChild(_section(
      "What this unblocks",
      `RTB is the architecture that lets you stop arguing about which mechanism is "best" in the abstract and start measuring on a realistic scenario instead.`,
      null,
    ));

    const closing = document.createElement("ul");
    closing.className = "explainer-list";
    closing.innerHTML = `
      <li><strong>Multi-vendor absorbs demand spikes.</strong>
        Drop rate scales inversely with supply diversity — the same scenario
        runs against 5 sats vs 36 sats in our fixtures and the dropped-bid
        count falls dramatically.</li>
      <li><strong>Mechanism A/B is one CLI flag.</strong>
        <code>--mechanism greedy</code> vs <code>--mechanism ssi</code> on
        the same seed produces directly comparable welfare and delivery
        numbers.</li>
      <li><strong>Pluggable for v0.3+ research.</strong>
        CBBA, VCG, ILP combinatorial mechanisms slot in behind the same
        <code>Mechanism</code> protocol. Runtime / streaming variants
        already have a <code>now</code> hook in the protocol.</li>
    `;
    root.appendChild(closing);

    const footer = document.createElement("div");
    footer.className = "explainer-footer";
    footer.innerHTML = `
      <div>seed <strong>${_fmt(m.seed)}</strong> · scenario <strong>${_fmt(m.scenario)}</strong></div>
      <div class="muted">Source: <code>github.com/OneMeanToast/raveneye</code> · MIT</div>
    `;
    root.appendChild(footer);

    return root;
  }

  function init(scenario) {
    const panel = document.getElementById("explainer-panel");
    const body  = document.getElementById("explainer-content");
    const open  = document.getElementById("btn-explainer");
    const close = document.getElementById("btn-explainer-close");
    const scrim = document.getElementById("explainer-scrim");
    if (!panel || !body || !open) return;

    body.innerHTML = "";
    body.appendChild(_renderContent(scenario));

    function show() {
      panel.classList.add("open");
      if (scrim) scrim.classList.add("open");
    }
    function hide() {
      panel.classList.remove("open");
      if (scrim) scrim.classList.remove("open");
    }
    function toggle() {
      panel.classList.toggle("open");
      if (scrim) scrim.classList.toggle("open");
    }

    open.addEventListener("click", toggle);
    if (close) close.addEventListener("click", hide);
    if (scrim) scrim.addEventListener("click", hide);

    window.addEventListener("keydown", (e) => {
      if (e.target && (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA")) return;
      if (e.key === "Escape" && panel.classList.contains("open")) {
        e.preventDefault();
        hide();
      } else if (e.key === "?" || (e.shiftKey && e.code === "Slash")) {
        e.preventDefault();
        toggle();
      }
    });
  }

  global.RavenEyeExplainer = { init };
})(window);
