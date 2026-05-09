/* RavenEye globe — static location markers + animated event pulses.
 *
 * Locations: a billboard per LOCATIONS entry, drawn at WGS84 surface, with
 * a hover label and click-through to a side-panel description.
 *
 * Events: a pulsing ground ring at the event lat/lon, sized by severity
 * and visible only inside its [t-0.5h, t + min(6h, ltiov_hours)] active
 * window plus a 4-hour fade. Driven by a Cesium CallbackProperty on the
 * ring radius/alpha so it follows the playback clock without per-frame
 * scene-graph thrash.
 */
(function (global) {
  "use strict";

  const SEV_COLOR = {
    1: "#4cc4d8",
    2: "#5fb87a",
    3: "#f0a020",
    4: "#e07b3c",
    5: "#e55a3c",
  };

  function visibility(ev, t_hours) {
    const start = ev.t_hours - 0.5;
    const endActive = ev.t_hours + Math.min(6.0, ev.ltiov_hours);
    const endFade = endActive + 4.0;
    if (t_hours < start || t_hours >= endFade) return 0.0;
    if (t_hours < endActive) return 1.0;
    return Math.max(0.0, (endFade - t_hours) / 4.0);
  }

  function tHoursFromClock(viewer, t0_iso) {
    const Cesium = global.Cesium;
    const t0 = Cesium.JulianDate.fromIso8601(t0_iso);
    const dt = Cesium.JulianDate.secondsDifference(viewer.clock.currentTime, t0);
    return dt / 3600.0;
  }

  function addLocations(scenario, viewer) {
    const Cesium = global.Cesium;
    const locs = scenario.locations || {};
    const entitiesById = new Map();
    for (const [loc_id, L] of Object.entries(locs)) {
      const ent = viewer.entities.add({
        id: "loc:" + loc_id,
        name: L.name,
        position: Cesium.Cartesian3.fromDegrees(L.lon, L.lat),
        point: {
          pixelSize: 5,
          color: Cesium.Color.fromCssColorString("#3a4856"),
          outlineColor: Cesium.Color.fromCssColorString("#7a8896"),
          outlineWidth: 1,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
        },
        label: {
          text: L.name,
          font: "11px JetBrains Mono, ui-monospace, monospace",
          fillColor: Cesium.Color.fromCssColorString("#5a6675"),
          showBackground: false,
          horizontalOrigin: Cesium.HorizontalOrigin.LEFT,
          verticalOrigin: Cesium.VerticalOrigin.CENTER,
          pixelOffset: new Cesium.Cartesian2(8, 0),
          distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 4_000_000),
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
        },
        properties: new Cesium.PropertyBag({
          kind: "location",
          location_id: loc_id,
          loc: L,
        }),
      });
      entitiesById.set(loc_id, ent);
    }
    return entitiesById;
  }

  /**
   * Add an event pulse for each event in scenario.events.
   *
   * Implementation: one Cesium ellipse entity per event, with semi-major-
   * axis and material driven by CallbackProperty so visibility tracks
   * playback without re-creating geometry. Severity sets the base radius.
   */
  function addEventPulses(scenario, viewer, opts = {}) {
    const Cesium = global.Cesium;
    const t0_iso = scenario.meta.t0_iso;
    const events = scenario.events || [];
    const onSelect = opts.onSelect;
    const baseRadius = 12_000;       // metres at sev 1
    const radiusPerSev = 14_000;     // metres
    const entitiesByEventId = new Map();

    for (const ev of events) {
      const sevColor = SEV_COLOR[ev.severity] || "#a3b0bf";
      const baseColor = Cesium.Color.fromCssColorString(sevColor);
      const evRadius = baseRadius + radiusPerSev * (ev.severity - 1);

      // Outer pulse: radius grows over the active window
      const radiusProp = new Cesium.CallbackProperty(() => {
        const t_h = tHoursFromClock(viewer, t0_iso);
        const v = visibility(ev, t_h);
        if (v <= 0) return 1.0;
        // Pulse factor: gently expand from 1.0 to 1.4 across the active window
        const start = ev.t_hours - 0.5;
        const endActive = ev.t_hours + Math.min(6.0, ev.ltiov_hours);
        const span = Math.max(0.001, endActive - start);
        const phase = Math.min(1, Math.max(0, (t_h - start) / span));
        return evRadius * (1.0 + 0.4 * phase);
      }, false);

      const fillColorProp = new Cesium.CallbackProperty((time, result) => {
        const t_h = tHoursFromClock(viewer, t0_iso);
        const alpha = 0.18 * visibility(ev, t_h);
        return Cesium.Color.fromCssColorString(sevColor).withAlpha(alpha).clone(result);
      }, false);

      const outlineColorProp = new Cesium.CallbackProperty((time, result) => {
        const t_h = tHoursFromClock(viewer, t0_iso);
        const alpha = 0.85 * visibility(ev, t_h);
        return Cesium.Color.fromCssColorString(sevColor).withAlpha(alpha).clone(result);
      }, false);

      const showProp = new Cesium.CallbackProperty(() => {
        return visibility(ev, tHoursFromClock(viewer, t0_iso)) > 0.0;
      }, false);

      const ent = viewer.entities.add({
        id: "ev:" + ev.event_id,
        name: ev.event_id + " " + ev.event_type,
        position: Cesium.Cartesian3.fromDegrees(ev.lon, ev.lat),
        ellipse: {
          semiMajorAxis: radiusProp,
          semiMinorAxis: radiusProp,
          material: new Cesium.ColorMaterialProperty(fillColorProp),
          outline: true,
          outlineColor: outlineColorProp,
          outlineWidth: 2.0,
          height: 0,
          show: showProp,
        },
        properties: new Cesium.PropertyBag({
          kind: "event",
          event_id: ev.event_id,
          ev: ev,
        }),
      });
      entitiesByEventId.set(ev.event_id, ent);
    }
    return entitiesByEventId;
  }

  global.RavenEyeGround = {
    addLocations,
    addEventPulses,
    visibility,
    SEV_COLOR,
  };
})(window);
