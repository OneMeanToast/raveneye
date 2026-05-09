/* RavenEye globe — satellite propagation + orbit ribbons (Phase L4).
 *
 * For each satellite in the scenario, build a Cesium SampledPositionProperty
 * by sampling the SGP4 orbit (via satellite.js) every SAMPLE_S seconds over
 * the scenario duration. Cesium handles the smooth interpolation between
 * samples at viewer.clock-driven playback rates.
 *
 * Trailing orbit ribbons are rendered as polylines showing the previous
 * RIBBON_MIN minutes of the satellite's path. Full ground tracks are NOT
 * drawn — at 100+ sats they become visual noise.
 */
(function (global) {
  "use strict";

  const SAMPLE_S    = 30;     // SGP4 propagation step (seconds)
  const RIBBON_MIN  = 20;     // trailing orbit length (minutes)
  const POINT_PIXELS = 6;

  const VENDOR_COLOR = {
    "BlackSky":              "#4cc4d8",
    "Planet":                "#5fb87a",
    "Capella Space":         "#f0a020",
    "ICEYE":                 "#e07b3c",
    "Vantor (Maxar)":        "#9d7cd8",
  };
  const FALLBACK_COLOR = "#a3b0bf";

  function vendorColor(vendor) {
    return VENDOR_COLOR[vendor] || FALLBACK_COLOR;
  }

  function buildSatrec(sat) {
    if (!global.satellite || !global.satellite.twoline2satrec) {
      throw new Error("satellite.js missing — check the CDN <script> tag");
    }
    return global.satellite.twoline2satrec(sat.tle_line1, sat.tle_line2);
  }

  /**
   * Propagate a satellite from t_start through t_end at SAMPLE_S spacing
   * and write each (time, ECEF position) sample into a Cesium
   * SampledPositionProperty. Returns the property.
   *
   * Uses ECF (Earth-fixed) coordinates so the resulting Cesium entity
   * tracks the rotating-Earth frame the camera and ground markers live in.
   */
  function buildPositionProperty(sat, t_start_jd, t_end_jd) {
    const Cesium = global.Cesium;
    const sat_lib = global.satellite;
    const satrec = buildSatrec(sat);
    const prop = new Cesium.SampledPositionProperty(Cesium.ReferenceFrame.FIXED);
    prop.forwardExtrapolationType = Cesium.ExtrapolationType.HOLD;
    prop.backwardExtrapolationType = Cesium.ExtrapolationType.HOLD;

    const samples = [];
    const step_jd = SAMPLE_S / 86400.0;
    let t = t_start_jd;
    while (t <= t_end_jd + 1e-9) {
      const date = Cesium.JulianDate.toDate(Cesium.JulianDate.fromIso8601(
        Cesium.JulianDate.toIso8601(Cesium.JulianDate.fromIso8601(julianToIso(t)))
      ));
      // Simpler: work directly in JS Date for satellite.js
      const ms = (t - 2440587.5) * 86400.0 * 1000.0;
      const d = new Date(ms);
      const pv = sat_lib.propagate(satrec, d);
      if (!pv || !pv.position || isNaN(pv.position.x)) {
        t += step_jd;
        continue;
      }
      // satellite.js .propagate() returns ECI in km. Convert to ECF.
      const gmst = sat_lib.gstime(d);
      const ecf = sat_lib.eciToEcf(pv.position, gmst);
      const sample_time = Cesium.JulianDate.fromDate(d);
      const cart = new Cesium.Cartesian3(ecf.x * 1000.0, ecf.y * 1000.0, ecf.z * 1000.0);
      samples.push({ time: sample_time, position: cart });
      t += step_jd;
    }
    // Bulk-add for performance (one allocation, one re-sort).
    for (const s of samples) prop.addSample(s.time, s.position);
    return prop;
  }

  function julianToIso(jd) {
    const ms = (jd - 2440587.5) * 86400.0 * 1000.0;
    return new Date(ms).toISOString();
  }

  /**
   * Add satellite entities to the viewer.
   *
   *   scenario  — full scenario JSON (uses scenario.satellites)
   *   viewer    — Cesium.Viewer instance
   *   onSelect  — optional callback(sat_dict) when a sat is clicked
   *
   * Returns:
   *   {
   *     entitiesBySatId: Map<sat_id, Cesium.Entity>,
   *     constellations: Array<{constellation_id, vendor, color, count}>,
   *     setVisible(constellation_id, bool),
   *     positionAt(sat_id, julianDate) -> Cesium.Cartesian3 | null,
   *     follow(sat_id),
   *   }
   */
  function addSatellites(scenario, viewer, onSelect) {
    const Cesium = global.Cesium;
    const sats = scenario.satellites || [];
    const start_iso = scenario.meta.t0_iso;
    const dur_h = scenario.meta.duration_hours;
    const t_start = Cesium.JulianDate.fromIso8601(start_iso);
    const t_end = Cesium.JulianDate.addSeconds(
      t_start, dur_h * 3600.0, new Cesium.JulianDate()
    );
    const t_start_jd = Cesium.JulianDate.toIso8601 ? jdNumber(t_start) : null;
    const t_end_jd = jdNumber(t_end);

    // Wire viewer clock to scenario span.
    viewer.clock.startTime  = t_start.clone();
    viewer.clock.stopTime   = t_end.clone();
    viewer.clock.currentTime = t_start.clone();
    viewer.clock.clockRange = Cesium.ClockRange.LOOP_STOP;
    viewer.clock.multiplier = 1800;
    viewer.clock.shouldAnimate = false;

    const entitiesBySatId = new Map();
    const propertiesBySatId = new Map();
    const conIndex = new Map();   // constellation_id → {vendor, color, count, ids}

    for (const sat of sats) {
      const color = vendorColor(sat.vendor);
      const prop = buildPositionProperty(sat, jdNumber(t_start), t_end_jd);
      propertiesBySatId.set(sat.sat_id, prop);

      const cesiumColor = Cesium.Color.fromCssColorString(color);
      const entity = viewer.entities.add({
        id: "sat:" + sat.sat_id,
        name: sat.name || sat.sat_id,
        position: prop,
        point: {
          pixelSize: POINT_PIXELS,
          color: cesiumColor,
          outlineColor: Cesium.Color.BLACK,
          outlineWidth: 1.0,
        },
        path: {
          show: true,
          leadTime: 0,
          trailTime: RIBBON_MIN * 60,
          width: 1.5,
          material: cesiumColor.withAlpha(0.55),
          resolution: 60,
        },
        // Properties bag for the click handler / tooltip lookup
        properties: new Cesium.PropertyBag({
          kind: "satellite",
          sat_id: sat.sat_id,
          name: sat.name,
          norad_id: sat.norad_id,
          constellation_id: sat.constellation_id,
          vendor: sat.vendor,
          sensor_class: sat.sensor_class,
          spectral_bands: sat.spectral_bands,
        }),
      });
      entitiesBySatId.set(sat.sat_id, entity);

      const c = conIndex.get(sat.constellation_id) || {
        constellation_id: sat.constellation_id,
        vendor: sat.vendor,
        color: color,
        count: 0,
        ids: [],
        visible: true,
      };
      c.count += 1;
      c.ids.push(sat.sat_id);
      conIndex.set(sat.constellation_id, c);
    }

    function setVisible(constellation_id, on) {
      const c = conIndex.get(constellation_id);
      if (!c) return;
      c.visible = !!on;
      for (const sid of c.ids) {
        const e = entitiesBySatId.get(sid);
        if (e) e.show = !!on;
      }
    }

    function positionAt(sat_id, julianDate) {
      const prop = propertiesBySatId.get(sat_id);
      if (!prop) return null;
      return prop.getValue(julianDate, new Cesium.Cartesian3());
    }

    function follow(sat_id) {
      const e = entitiesBySatId.get(sat_id);
      if (e) viewer.trackedEntity = e;
    }

    return {
      entitiesBySatId,
      constellations: Array.from(conIndex.values()),
      setVisible,
      positionAt,
      follow,
    };
  }

  function jdNumber(julianDate) {
    const Cesium = global.Cesium;
    return Cesium.JulianDate.toIso8601 ? toJDNumber(julianDate) : 0;
  }

  function toJDNumber(julianDate) {
    // Cesium's JulianDate is dayNumber + secondsOfDay; convert to a single number.
    return julianDate.dayNumber + julianDate.secondsOfDay / 86400.0;
  }

  global.RavenEyeOrbits = {
    addSatellites,
    vendorColor,
  };
})(window);
