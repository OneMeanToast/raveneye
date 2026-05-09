/* RavenEye globe — boot + clock + camera + control wiring.
 *
 * Loads scenario.json, creates a Cesium.Viewer with the toolbar/timeline
 * widgets disabled (we drive playback ourselves), populates satellites
 * (orbits.js), ground markers (ground.js), side panels (panels.js), and
 * the playback timeline (timeline.js). Then opens the playback loop.
 */
(function (global) {
  "use strict";

  // ----- Scenario loading -----
  function urlParam(name) {
    return new URLSearchParams(window.location.search).get(name);
  }
  function scenarioUrl() {
    return urlParam("scenario") || global.RAVENEYE_SCENARIO_URL || "scenario.json";
  }
  function showError(detail) {
    const el = document.getElementById("err-detail");
    if (el) el.textContent = detail;
    const box = document.getElementById("error-box");
    if (box) box.classList.remove("hidden");
  }

  // ----- Cesium viewer factory -----
  function makeViewer() {
    const Cesium = global.Cesium;
    // The Cesium ion default token issues 401s on commercial usage; we
    // explicitly opt into OSM imagery + the bundled ellipsoid terrain so
    // the viewer never depends on a paid Cesium account.
    Cesium.Ion.defaultAccessToken = "";

    const viewer = new Cesium.Viewer("cesiumContainer", {
      animation: false,
      timeline: false,
      baseLayerPicker: false,
      fullscreenButton: false,
      vrButton: false,
      geocoder: false,
      homeButton: false,
      sceneModePicker: false,
      navigationHelpButton: false,
      navigationInstructionsInitiallyVisible: false,
      selectionIndicator: false,
      infoBox: false,
      shouldAnimate: false,
      imageryProvider: new Cesium.OpenStreetMapImageryProvider({
        url: "https://tile.openstreetmap.org/",
      }),
      terrainProvider: new Cesium.EllipsoidTerrainProvider(),
      requestRenderMode: false,
    });
    viewer.scene.skyAtmosphere.show = true;
    viewer.scene.globe.enableLighting = true;
    viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString("#0c1219");
    viewer.scene.backgroundColor = Cesium.Color.fromCssColorString("#020409");
    return viewer;
  }

  function flyToGulf(viewer) {
    const Cesium = global.Cesium;
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(53.0, 26.5, 4_500_000),
      orientation: {
        heading: 0.0,
        pitch: Cesium.Math.toRadians(-65.0),
        roll: 0.0,
      },
      duration: 3.0,
    });
  }

  // ----- Header chrome -----
  function fmtSimClock(t0_iso, t_hours_total, viewer) {
    const Cesium = global.Cesium;
    const t0 = Cesium.JulianDate.fromIso8601(t0_iso);
    const dt_s = Cesium.JulianDate.secondsDifference(viewer.clock.currentTime, t0);
    const t_h = dt_s / 3600.0;
    const ms = Date.parse(t0_iso) + dt_s * 1000;
    const d = new Date(ms);
    const pad = (n) => (n < 10 ? "0" + n : "" + n);
    const iso =
      d.getUTCFullYear() + "-" + pad(d.getUTCMonth() + 1) + "-" + pad(d.getUTCDate()) +
      " " + pad(d.getUTCHours()) + ":" + pad(d.getUTCMinutes()) + "Z";
    return { iso, t_h };
  }

  function currentPhase(scenario, t_h) {
    const phases = scenario.meta.phases || [];
    let active = phases[0];
    for (const p of phases) {
      if (t_h >= p.start_hours) active = p;
    }
    return active;
  }

  function updateHeader(scenario, viewer) {
    const m = scenario.meta;
    document.getElementById("scenario-name").textContent =
      (m.scenario || "Scenario") + "  ·  seed " + (m.seed || "—") + "  ·  " + (m.mechanism || "—");
    const { iso, t_h } = fmtSimClock(m.t0_iso, m.duration_hours, viewer);
    const ph = currentPhase(scenario, t_h);
    if (ph) {
      const badge = document.getElementById("phase-badge");
      badge.textContent = ph.name.replace(/_/g, " ");
    }
    document.getElementById("clock").innerHTML =
      iso + '<span class="t-rel">t+' + t_h.toFixed(1) + 'h / ' + m.duration_hours.toFixed(0) + 'h</span>';
  }

  // ----- Footer controls -----
  function wireControls(viewer) {
    const Cesium = global.Cesium;
    const playBtn = document.getElementById("btn-play");
    const resetBtn = document.getElementById("btn-reset");
    const speeds = document.getElementById("speeds");

    function refreshPlayBtn() {
      playBtn.innerHTML = viewer.clock.shouldAnimate ? "&#10074;&#10074; PAUSE" : "&#9658; PLAY";
    }

    playBtn.addEventListener("click", () => {
      viewer.clock.shouldAnimate = !viewer.clock.shouldAnimate;
      refreshPlayBtn();
    });
    resetBtn.addEventListener("click", () => {
      viewer.clock.currentTime = viewer.clock.startTime.clone();
      viewer.clock.shouldAnimate = false;
      refreshPlayBtn();
    });
    Array.prototype.forEach.call(speeds.querySelectorAll("button"), (b) => {
      b.addEventListener("click", () => {
        viewer.clock.multiplier = parseFloat(b.getAttribute("data-speed"));
        Array.prototype.forEach.call(speeds.querySelectorAll("button"), (x) => {
          x.classList.toggle("active", x === b);
        });
      });
    });

    window.addEventListener("keydown", (e) => {
      if (e.target && (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA")) return;
      if (e.code === "Space") {
        e.preventDefault();
        playBtn.click();
      } else if (e.code === "KeyR") {
        resetBtn.click();
      } else if (e.code === "ArrowLeft") {
        e.preventDefault();
        viewer.clock.currentTime = Cesium.JulianDate.addSeconds(
          viewer.clock.currentTime, -3600, new Cesium.JulianDate()
        );
      } else if (e.code === "ArrowRight") {
        e.preventDefault();
        viewer.clock.currentTime = Cesium.JulianDate.addSeconds(
          viewer.clock.currentTime,  3600, new Cesium.JulianDate()
        );
      } else if (e.code === "KeyF") {
        // F toggles tracked-entity follow on the currently-selected sat
        if (window.RavenEyeState && window.RavenEyeState.selectedSatId) {
          window.RavenEyeState.satLayer.follow(window.RavenEyeState.selectedSatId);
        }
      }
    });

    refreshPlayBtn();
  }

  // ----- Click handler — surface satellite/event/location selection -----
  function wireSelection(viewer, scenario, eventEntities, locationEntities, satLayer) {
    const Cesium = global.Cesium;
    const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
    handler.setInputAction((click) => {
      const picked = viewer.scene.pick(click.position);
      if (!picked || !picked.id || !picked.id.properties) return;
      const props = picked.id.properties;
      const kind = props.kind && props.kind.getValue && props.kind.getValue();
      if (kind === "satellite") {
        const sat_id = props.sat_id.getValue();
        const sat = (scenario.satellites || []).find(s => s.sat_id === sat_id);
        if (sat) {
          window.RavenEyeState.selectedSatId = sat_id;
          window.RavenEyePanels.fillSelection({ kind: "satellite", sat: sat, scenario: scenario });
        }
      } else if (kind === "event") {
        const ev_id = props.event_id.getValue();
        const ev = (scenario.events || []).find(e => e.event_id === ev_id);
        if (ev) {
          window.RavenEyePanels.selectEvent(ev, scenario, viewer, eventEntities);
        }
      } else if (kind === "location") {
        const loc = props.loc.getValue();
        window.RavenEyePanels.fillSelection({ kind: "location", loc: loc, scenario: scenario });
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  }

  // ----- Boot -----
  fetch(scenarioUrl())
    .then((r) => {
      if (!r.ok) throw new Error("HTTP " + r.status + " for " + scenarioUrl());
      return r.json();
    })
    .then((scenario) => {
      const viewer = makeViewer();
      flyToGulf(viewer);

      const satLayer = global.RavenEyeOrbits.addSatellites(scenario, viewer);
      const locationEntities = global.RavenEyeGround.addLocations(scenario, viewer);
      const eventEntities = global.RavenEyeGround.addEventPulses(scenario, viewer);
      const coverageLayer = global.RavenEyeCoverage.addCoverage(scenario, viewer, satLayer);

      window.RavenEyeState = {
        viewer: viewer,
        scenario: scenario,
        satLayer: satLayer,
        eventEntities: eventEntities,
        locationEntities: locationEntities,
        coverageLayer: coverageLayer,
        selectedSatId: null,
      };

      global.RavenEyePanels.render(scenario, viewer, satLayer, {
        eventEntities, locationEntities, t0_iso: scenario.meta.t0_iso,
      }, coverageLayer);
      const tl = global.RavenEyeTimeline.render(scenario, viewer, {
        onEventClick: (ev) => global.RavenEyePanels.selectEvent(ev, scenario, viewer, eventEntities),
      });

      wireControls(viewer);
      wireSelection(viewer, scenario, eventEntities, locationEntities, satLayer);

      // Clock-driven UI updates: header clock, timeline playhead.
      viewer.clock.onTick.addEventListener(() => {
        updateHeader(scenario, viewer);
        global.RavenEyeTimeline.updatePlayhead(scenario, viewer);
      });
      updateHeader(scenario, viewer);
      global.RavenEyeTimeline.updatePlayhead(scenario, viewer);
    })
    .catch((err) => showError(String(err)));
})(window);
