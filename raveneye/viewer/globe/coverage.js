/* RavenEye globe — coverage rendering during scheduled access windows.
 *
 * For every SCHEDULED allocation we add two Cesium entities:
 *   1. a target swath polygon (ground ellipse) at the bid's target,
 *      sized by the satellite's swath_width_km, visible only during
 *      the window's [start, end] interval and faded in/out at the edges.
 *   2. a thin polyline from the satellite's current position to the
 *      target during the same window, so you can see which sat is
 *      "taking the shot."
 *
 * Visibility is driven by Cesium CallbackProperty so it tracks the
 * playback clock without rebuilding geometry. DROPPED allocations get
 * no entities — they're already represented in the side panel.
 */
(function (global) {
  "use strict";

  const STATUS_COLOR = {
    SCHEDULED:        "#4cc4d8",
    COLLECTED:        "#5fb87a",
    DEADLINE_MISSED:  "#e55a3c",
  };

  function _withinWindow(viewer, t0_iso, start_iso, end_iso) {
    const Cesium = global.Cesium;
    const t0 = Cesium.JulianDate.fromIso8601(t0_iso);
    const start = Cesium.JulianDate.fromIso8601(start_iso);
    const end = Cesium.JulianDate.fromIso8601(end_iso);
    const t = viewer.clock.currentTime;
    if (Cesium.JulianDate.lessThan(t, start)) return 0.0;
    if (Cesium.JulianDate.greaterThan(t, end)) return 0.0;
    const total_s = Cesium.JulianDate.secondsDifference(end, start);
    const dt_s = Cesium.JulianDate.secondsDifference(t, start);
    if (total_s <= 0) return 1.0;
    // Trapezoid: linear ramp at start and end, flat at center
    const ramp_s = Math.min(15.0, total_s * 0.15);
    if (dt_s < ramp_s) return dt_s / ramp_s;
    if (dt_s > total_s - ramp_s) return (total_s - dt_s) / ramp_s;
    return 1.0;
  }

  /**
   * Build the coverage layer.
   *
   *   scenario  — full scenario JSON
   *   viewer    — Cesium.Viewer instance
   *   satLayer  — return value of RavenEyeOrbits.addSatellites
   *
   * Returns:
   *   {
   *     entitiesByWindowId: Map,
   *     allocationByWindowId: Map,
   *     allocationByBidId: Map,
   *     refresh()  // call when satellite filter visibility changes
   *   }
   */
  function addCoverage(scenario, viewer, satLayer) {
    const Cesium = global.Cesium;
    const t0_iso = scenario.meta.t0_iso;
    const allocations = scenario.allocations || [];
    const windowsById = new Map();
    for (const w of (scenario.access_windows || [])) {
      windowsById.set(w.window_id, w);
    }
    const allocationByWindowId = new Map();
    const allocationByBidId = new Map();
    for (const a of allocations) {
      if (a.window_id) allocationByWindowId.set(a.window_id, a);
      allocationByBidId.set(a.bid_id, a);
    }

    const satsById = new Map();
    for (const s of (scenario.satellites || [])) satsById.set(s.sat_id, s);

    const entitiesByWindowId = new Map();

    for (const a of allocations) {
      if (a.status !== "SCHEDULED" && a.status !== "COLLECTED") continue;
      const w = windowsById.get(a.window_id);
      if (!w) continue;
      const sat = satsById.get(w.sat_id);
      if (!sat) continue;
      const sw_km = Math.max(2.0, sat.swath_width_km || 5.0);
      const swath_radius_m = (sw_km / 2.0) * 1000.0;
      const baseColor = STATUS_COLOR[a.status] || "#a3b0bf";

      const targetPos = Cesium.Cartesian3.fromDegrees(w.target_lon, w.target_lat);

      const fillColorProp = new Cesium.CallbackProperty((time, result) => {
        const v = _withinWindow(viewer, t0_iso, w.start_iso, w.end_iso);
        return Cesium.Color.fromCssColorString(baseColor)
          .withAlpha(0.15 * v).clone(result);
      }, false);
      const outlineColorProp = new Cesium.CallbackProperty((time, result) => {
        const v = _withinWindow(viewer, t0_iso, w.start_iso, w.end_iso);
        return Cesium.Color.fromCssColorString(baseColor)
          .withAlpha(0.85 * v).clone(result);
      }, false);
      const showProp = new Cesium.CallbackProperty(() => {
        return _withinWindow(viewer, t0_iso, w.start_iso, w.end_iso) > 0.0;
      }, false);

      const swath = viewer.entities.add({
        id: "cov-swath:" + w.window_id,
        position: targetPos,
        ellipse: {
          semiMajorAxis: swath_radius_m,
          semiMinorAxis: swath_radius_m,
          material: new Cesium.ColorMaterialProperty(fillColorProp),
          outline: true,
          outlineColor: outlineColorProp,
          outlineWidth: 2.0,
          height: 0.0,
          show: showProp,
        },
        properties: new Cesium.PropertyBag({
          kind: "coverage",
          window_id: w.window_id,
          allocation_id: a.allocation_id,
        }),
      });

      // Tether: thin polyline from sat current position to target during
      // the active window. Polyline positions themselves are a CallbackProperty
      // that re-resolves the sat position every tick.
      const linePositionsProp = new Cesium.CallbackProperty(() => {
        const visible = _withinWindow(viewer, t0_iso, w.start_iso, w.end_iso) > 0.0;
        if (!visible) return [targetPos, targetPos];
        const satPos = satLayer.positionAt(w.sat_id, viewer.clock.currentTime);
        if (!satPos) return [targetPos, targetPos];
        return [satPos, targetPos];
      }, false);

      const lineMaterial = new Cesium.PolylineDashMaterialProperty({
        color: new Cesium.CallbackProperty((time, result) => {
          const v = _withinWindow(viewer, t0_iso, w.start_iso, w.end_iso);
          return Cesium.Color.fromCssColorString(baseColor)
            .withAlpha(0.65 * v).clone(result);
        }, false),
        dashLength: 12.0,
      });

      const tether = viewer.entities.add({
        id: "cov-tether:" + w.window_id,
        polyline: {
          positions: linePositionsProp,
          width: 1.5,
          material: lineMaterial,
          arcType: Cesium.ArcType.NONE,
          show: showProp,
        },
        properties: new Cesium.PropertyBag({
          kind: "coverage_tether",
          window_id: w.window_id,
          allocation_id: a.allocation_id,
        }),
      });

      entitiesByWindowId.set(w.window_id, { swath, tether });
    }

    function refresh() { /* placeholder for filter integration */ }

    return {
      entitiesByWindowId,
      allocationByWindowId,
      allocationByBidId,
      refresh,
    };
  }

  global.RavenEyeCoverage = {
    addCoverage,
    STATUS_COLOR,
  };
})(window);
