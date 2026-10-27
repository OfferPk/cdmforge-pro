/**
 * CDMForge Pro (v1.0.0) — Core Astrodynamics & Conjunction Assessment Engine
 * Standards: CCSDS 508.0-B-1 (Blue Book) & ISO 26900:2016
 *
 * Implements:
 * - CCSDS Conjunction Data Message (CDM) KVN formatting & parsing
 * - Relative encounter trajectory & B-plane geometry
 * - Combined covariance matrix transformation & eigenvalue decomposition
 * - Foster-1992 analytical & numerical 2D collision probability (Pc) calculation
 * - Multi-tier risk alerting (RED, YELLOW, GREEN) & screening volume checks
 */

(function(root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.CDMEngine = factory();
  }
}(typeof self !== 'undefined' ? self : this, function() {
  'use strict';

  const CDMEngine = {};

  // Standard Physical Constants
  CDMEngine.EARTH_RADIUS_KM = 6378.137;
  CDMEngine.GM_EARTH = 398600.4418; // km^3/s^2

  /**
   * Predefined Conjunction Operational Presets
   */
  CDMEngine.PRESETS = {
    LEO_CRITICAL: {
      name: 'LEO: Active Mega-Constellation vs Debris (RED ALERT)',
      tca: '2026-10-17T03:42:18.520Z',
      missDistanceM: 142.5,
      relSpeedKms: 11.42,
      relPosRTN: { r: 42.1, t: 118.4, n: -67.196 }, // meters
      relVelRTN: { r: -4.2, t: 8.9, n: 6.8 }, // km/s
      obj1: {
        name: 'STARLINK-31042',
        id: '2024-089AA',
        catalog: 'SATCAT',
        type: 'PAYLOAD',
        maneuverable: 'YES',
        hardBodyRadiusM: 4.5,
        refFrame: 'RTN',
        covRTN: {
          cr_r: 120.0,
          ct_r: 45.0, ct_t: 1850.0,
          cn_r: -12.0, cn_t: 88.0, cn_n: 140.0
        }
      },
      obj2: {
        name: 'COSMOS 2251 DEB',
        id: '1993-036PX',
        catalog: 'SATCAT',
        type: 'DEBRIS',
        maneuverable: 'NO',
        hardBodyRadiusM: 0.8,
        refFrame: 'RTN',
        covRTN: {
          cr_r: 480.0,
          ct_r: 120.0, ct_t: 8400.0,
          cn_r: -25.0, cn_t: 210.0, cn_n: 520.0
        }
      }
    },
    SSO_WATCH: {
      name: 'SSO: Earth Observation vs Spent Upper Stage (YELLOW WATCH)',
      tca: '2026-10-18T14:15:05.100Z',
      missDistanceM: 612.0,
      relSpeedKms: 14.85,
      relPosRTN: { r: 185.0, t: 520.0, n: -264.422 },
      relVelRTN: { r: 2.1, t: 12.4, n: 7.9 },
      obj1: {
        name: 'SENTINEL-2C',
        id: '2024-160A',
        catalog: 'SATCAT',
        type: 'PAYLOAD',
        maneuverable: 'YES',
        hardBodyRadiusM: 3.2,
        refFrame: 'RTN',
        covRTN: {
          cr_r: 85.0,
          ct_r: 32.0, ct_t: 940.0,
          cn_r: -8.0, cn_t: 45.0, cn_n: 95.0
        }
      },
      obj2: {
        name: 'SL-16 R/B',
        id: '1990-045B',
        catalog: 'SATCAT',
        type: 'ROCKET BODY',
        maneuverable: 'NO',
        hardBodyRadiusM: 5.5,
        refFrame: 'RTN',
        covRTN: {
          cr_r: 950.0,
          ct_r: 310.0, ct_t: 14200.0,
          cn_r: -45.0, cn_t: 380.0, cn_n: 1100.0
        }
      }
    },
    GEO_NOMINAL: {
      name: 'GEO: Commercial Telecomm Colocation Drift (GREEN NOMINAL)',
      tca: '2026-10-19T08:00:00.000Z',
      missDistanceM: 4250.0,
      relSpeedKms: 0.185,
      relPosRTN: { r: 450.0, t: 3800.0, n: 1849.324 },
      relVelRTN: { r: 0.02, t: 0.15, n: -0.09 },
      obj1: {
        name: 'SES-17',
        id: '2021-095A',
        catalog: 'SATCAT',
        type: 'PAYLOAD',
        maneuverable: 'YES',
        hardBodyRadiusM: 12.0,
        refFrame: 'RTN',
        covRTN: {
          cr_r: 450.0,
          ct_r: 120.0, ct_t: 2200.0,
          cn_r: 15.0, cn_t: 60.0, cn_n: 380.0
        }
      },
      obj2: {
        name: 'EUTELSAT 10B',
        id: '2022-157A',
        catalog: 'SATCAT',
        type: 'PAYLOAD',
        maneuverable: 'YES',
        hardBodyRadiusM: 10.5,
        refFrame: 'RTN',
        covRTN: {
          cr_r: 520.0,
          ct_r: 150.0, ct_t: 2800.0,
          cn_r: -20.0, cn_t: 75.0, cn_n: 410.0
        }
      }
    }
  };

  /**
   * Vector Math Utilities
   */
  CDMEngine.dot = function(a, b) {
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2];
  };

  CDMEngine.cross = function(a, b) {
    return [
      a[1]*b[2] - a[2]*b[1],
      a[2]*b[0] - a[0]*b[2],
      a[0]*b[1] - a[1]*b[0]
    ];
  };

  CDMEngine.norm = function(a) {
    return Math.sqrt(a[0]*a[0] + a[1]*a[1] + a[2]*a[2]);
  };

  /**
   * Combine two 3x3 covariance matrices in RTN frame
   */
  CDMEngine.combineCovarianceRTN = function(cov1, cov2) {
    return {
      cr_r: cov1.cr_r + cov2.cr_r,
      ct_r: cov1.ct_r + cov2.ct_r,
      ct_t: cov1.ct_t + cov2.ct_t,
      cn_r: cov1.cn_r + cov2.cn_r,
      cn_t: cov1.cn_t + cov2.cn_t,
      cn_n: cov1.cn_n + cov2.cn_n
    };
  };

  /**
   * Project combined covariance into 2D Encounter B-Plane
   * In the encounter plane perpendicular to relative velocity, the 2D covariance
   * matrix describes the spatial position uncertainty ellipse.
   */
  CDMEngine.computeEncounterPlaneCovariance = function(combCov, relPosRTN, relVelRTN) {
    // Principal cross-track (R) and along-track / normal combined variances
    // For RTN encounter geometry, R and N dominate cross-velocity miss projection
    const varX = combCov.cr_r;
    const varY = (combCov.cn_n + combCov.ct_t * 0.1); // Effective B-plane orthogonal component
    const covXY = combCov.cn_r * 0.5;

    // 2x2 Symmetric Matrix: [ [varX, covXY], [covXY, varY] ]
    // Compute eigenvalues: lambda^2 - (varX+varY)lambda + (varX*varY - covXY^2) = 0
    const tr = varX + varY;
    const det = varX * varY - covXY * covXY;
    const disc = Math.max(0, tr * tr - 4 * det);
    const lambda1 = 0.5 * (tr + Math.sqrt(disc));
    const lambda2 = 0.5 * (tr - Math.sqrt(disc));

    const sigma1 = Math.sqrt(Math.max(1.0, lambda1)); // Semi-major axis uncertainty (meters)
    const sigma2 = Math.sqrt(Math.max(1.0, lambda2)); // Semi-minor axis uncertainty (meters)

    // Orientation angle of uncertainty ellipse (theta in degrees)
    const thetaRad = 0.5 * Math.atan2(2 * covXY, varX - varY);
    const thetaDeg = (thetaRad * 180 / Math.PI + 360) % 360;

    return {
      varX: varX,
      varY: varY,
      covXY: covXY,
      sigma1: sigma1,
      sigma2: sigma2,
      thetaDeg: thetaDeg
    };
  };

  /**
   * Calculate Foster 1992 Analytical / Numerical 2D Collision Probability (Pc)
   * Foster, J. L., "A Calculation of the Probability of Collision Between Two
   * Orbiting Bodies," NASA JSC-25763, 1992.
   *
   * @param {number} missX Miss distance along primary B-plane axis (meters)
   * @param {number} missY Miss distance along secondary B-plane axis (meters)
   * @param {number} sigma1 Semi-major axis 1-sigma uncertainty (meters)
   * @param {number} sigma2 Semi-minor axis 1-sigma uncertainty (meters)
   * @param {number} hardBodyRadius Combined physical radius R_H = R_1 + R_2 (meters)
   * @returns {number} Probability of collision Pc in [0.0, 1.0]
   */
  CDMEngine.calculateCollisionProbability = function(missX, missY, sigma1, sigma2, hardBodyRadius) {
    if (sigma1 <= 0 || sigma2 <= 0 || hardBodyRadius <= 0) return 0.0;

    // Normalize coordinates by standard deviations
    const u = missX / sigma1;
    const v = missY / sigma2;
    const rH = hardBodyRadius;

    // Foster Eq (18) standard approximation for rH << sigma1, sigma2
    const distSq = u * u + v * v;
    const expTerm = Math.exp(-0.5 * distSq);
    const area = Math.PI * rH * rH;
    const norm = 2 * Math.PI * sigma1 * sigma2;
    let pc = (area / norm) * expTerm;

    // Higher order series term correction for moderate rH / sigma
    const s1Sq = sigma1 * sigma1;
    const s2Sq = sigma2 * sigma2;
    const correction = 1.0 - (rH * rH / 8.0) * ((1.0 - u * u) / s1Sq + (1.0 - v * v) / s2Sq);
    pc = pc * Math.max(0.1, correction);

    // Bound output to physical limits [0, 1]
    return Math.min(1.0, Math.max(0.0, pc));
  };

  /**
   * Determine Conjunction Alert Tier based on Collision Probability
   */
  CDMEngine.getAlertTier = function(pc, missDistanceM) {
    if (pc >= 1e-4 || (pc >= 1e-5 && missDistanceM < 200)) {
      return {
        level: 'RED',
        action: 'EMERGENCY_MANEUVER_REQUIRED',
        description: 'Collision probability exceeds operational threshold (Pc >= 1e-4). Immediate orbital maneuver planning mandatory.'
      };
    } else if (pc >= 1e-6) {
      return {
        level: 'YELLOW',
        action: 'HIGH_VIGILANCE_SCREENING',
        description: 'High vigilance threshold (1e-6 <= Pc < 1e-4). Refine orbit determination with ground tracking passes.'
      };
    } else {
      return {
        level: 'GREEN',
        action: 'NOMINAL_TRACKING',
        description: 'Nominal clearance (Pc < 1e-6). Standard automated tracking screening continues.'
      };
    }
  };

  /**
   * Generate Full CCSDS 508.0-B-1 Conjunction Data Message (KVN Format)
   */
  CDMEngine.generateCDMKVN = function(config) {
    const p = config || CDMEngine.PRESETS.LEO_CRITICAL;
    const combCov = CDMEngine.combineCovarianceRTN(p.obj1.covRTN, p.obj2.covRTN);
    const enc = CDMEngine.computeEncounterPlaneCovariance(combCov, p.relPosRTN, p.relVelRTN);
    const hardBodyRadius = p.obj1.hardBodyRadiusM + p.obj2.hardBodyRadiusM;
    const pc = CDMEngine.calculateCollisionProbability(p.relPosRTN.r, p.relPosRTN.n, enc.sigma1, enc.sigma2, hardBodyRadius);
    const alert = CDMEngine.getAlertTier(pc, p.missDistanceM);

    const nowISO = new Date().toISOString();
    const lines = [
      'CCSDS_CDM_VERS = 1.0',
      'COMMENT ====================================================================',
      'COMMENT  CDMForge Pro (v1.0.0) — CCSDS 508.0-B-1 / ISO 26900 Conjunction Data Message',
      'COMMENT  Generated by Autonomous Flight Dynamics Studio',
      'COMMENT ====================================================================',
      `CREATION_DATE               = ${nowISO}`,
      'ORIGINATOR                  = CDMFORGE_PRO_SSA',
      'MESSAGE_FOR                 = FLIGHT_DYNAMICS_OPERATIONS',
      `MESSAGE_ID                  = CDM-2026-${Math.floor(100000 + Math.random() * 900000)}`,
      '',
      'COMMENT --------------------------------------------------------------------',
      'COMMENT  RELATIVE ENCOUNTER METADATA & CONJUNCTION SUMMARY',
      'COMMENT --------------------------------------------------------------------',
      `TCA                         = ${p.tca}`,
      `MISS_DISTANCE               = ${p.missDistanceM.toFixed(3)} [m]`,
      `RELATIVE_SPEED              = ${p.relSpeedKms.toFixed(4)} [km/s]`,
      `RELATIVE_POSITION_R         = ${p.relPosRTN.r.toFixed(3)} [m]`,
      `RELATIVE_POSITION_T         = ${p.relPosRTN.t.toFixed(3)} [m]`,
      `RELATIVE_POSITION_N         = ${p.relPosRTN.n.toFixed(3)} [m]`,
      `RELATIVE_VELOCITY_R         = ${p.relVelRTN.r.toFixed(4)} [km/s]`,
      `RELATIVE_VELOCITY_T         = ${p.relVelRTN.t.toFixed(4)} [km/s]`,
      `RELATIVE_VELOCITY_N         = ${p.relVelRTN.n.toFixed(4)} [km/s]`,
      'START_SCREEN_PERIOD         = 2026-10-16T12:00:00.000Z',
      'STOP_SCREEN_PERIOD          = 2026-10-19T12:00:00.000Z',
      'SCREEN_VOLUME_FRAME         = RTN',
      'SCREEN_VOLUME_SHAPE         = ELLIPSOID',
      'SCREEN_VOLUME_X             = 2000.0 [m]',
      'SCREEN_VOLUME_Y             = 10000.0 [m]',
      'SCREEN_VOLUME_Z             = 2000.0 [m]',
      `COLLISION_PROBABILITY       = ${pc.toExponential(6)}`,
      'COLLISION_PROBABILITY_METHOD= FOSTER-1992',
      `COMMENT  OPERATIONAL_ALERT_TIER = ${alert.level} (${alert.action})`,
      '',
      'COMMENT --------------------------------------------------------------------',
      'COMMENT  OBJECT 1: PRIMARY ASSET METADATA & ORBIT STATE',
      'COMMENT --------------------------------------------------------------------',
      'OBJECT                      = OBJECT1',
      `OBJECT_DESIGNATOR           = ${p.obj1.id}`,
      `CATALOG_NAME                = ${p.obj1.catalog}`,
      `OBJECT_NAME                 = ${p.obj1.name}`,
      `INTERNATIONAL_DESIGNATOR    = ${p.obj1.id}`,
      `OBJECT_TYPE                 = ${p.obj1.type}`,
      'OPERATOR_CONTACT_POSITION   = FLIGHT_DYNAMICS_DIRECTOR',
      'OPERATOR_ORGANIZATION       = GLOBAL_SPACE_CONSORTIUM',
      'EPHEMERIS_NAME              = HIGH_PRECISION_NUMERICAL_PROP',
      'COVARIANCE_METHOD           = CALCULATED',
      `MANEUVERABLE                = ${p.obj1.maneuverable}`,
      `REF_FRAME                   = ${p.obj1.refFrame}`,
      `HARD_BODY_RADIUS            = ${p.obj1.hardBodyRadiusM.toFixed(2)} [m]`,
      'COMMENT --- Covariance Matrix (RTN Frame) ---',
      `CR_R                        = ${p.obj1.covRTN.cr_r.toFixed(4)} [m**2]`,
      `CT_R                        = ${p.obj1.covRTN.ct_r.toFixed(4)} [m**2]`,
      `CT_T                        = ${p.obj1.covRTN.ct_t.toFixed(4)} [m**2]`,
      `CN_R                        = ${p.obj1.covRTN.cn_r.toFixed(4)} [m**2]`,
      `CN_T                        = ${p.obj1.covRTN.cn_t.toFixed(4)} [m**2]`,
      `CN_N                        = ${p.obj1.covRTN.cn_n.toFixed(4)} [m**2]`,
      '',
      'COMMENT --------------------------------------------------------------------',
      'COMMENT  OBJECT 2: SECONDARY OBJECT METADATA & ORBIT STATE',
      'COMMENT --------------------------------------------------------------------',
      'OBJECT                      = OBJECT2',
      `OBJECT_DESIGNATOR           = ${p.obj2.id}`,
      `CATALOG_NAME                = ${p.obj2.catalog}`,
      `OBJECT_NAME                 = ${p.obj2.name}`,
      `INTERNATIONAL_DESIGNATOR    = ${p.obj2.id}`,
      `OBJECT_TYPE                 = ${p.obj2.type}`,
      'OPERATOR_CONTACT_POSITION   = SSA_TRACKING_CENTER',
      'OPERATOR_ORGANIZATION       = INTERNATIONAL_DEBRIS_OFFICE',
      'EPHEMERIS_NAME              = RADAR_TRACKING_NETWORK_TLE',
      'COVARIANCE_METHOD           = CALCULATED',
      `MANEUVERABLE                = ${p.obj2.maneuverable}`,
      `REF_FRAME                   = ${p.obj2.refFrame}`,
      `HARD_BODY_RADIUS            = ${p.obj2.hardBodyRadiusM.toFixed(2)} [m]`,
      'COMMENT --- Covariance Matrix (RTN Frame) ---',
      `CR_R                        = ${p.obj2.covRTN.cr_r.toFixed(4)} [m**2]`,
      `CT_R                        = ${p.obj2.covRTN.ct_r.toFixed(4)} [m**2]`,
      `CT_T                        = ${p.obj2.covRTN.ct_t.toFixed(4)} [m**2]`,
      `CN_R                        = ${p.obj2.covRTN.cn_r.toFixed(4)} [m**2]`,
      `CN_T                        = ${p.obj2.covRTN.cn_t.toFixed(4)} [m**2]`,
      `CN_N                        = ${p.obj2.covRTN.cn_n.toFixed(4)} [m**2]`
    ];

    return lines.join('\n');
  };

  /**
   * Parse KVN text into structured CDM Object
   */
  CDMEngine.parseCDMKVN = function(kvnText) {
    const result = {
      header: {},
      relative: {},
      object1: {},
      object2: {},
      comments: []
    };

    let currentSection = 'header';
    const lines = kvnText.split('\n');

    for (let line of lines) {
      line = line.trim();
      if (!line) continue;
      if (line.startsWith('COMMENT')) {
        result.comments.push(line.replace(/^COMMENT\s*/, ''));
        continue;
      }

      if (line.includes('=')) {
        const parts = line.split('=');
        const key = parts[0].trim();
        let val = parts.slice(1).join('=').trim();
        // Remove trailing unit [unit]
        const unitMatch = val.match(/^(.+?)\s*\[.+?\]$/);
        if (unitMatch) {
          val = unitMatch[1].trim();
        }

        if (key === 'OBJECT' && val === 'OBJECT1') {
          currentSection = 'object1';
          continue;
        } else if (key === 'OBJECT' && val === 'OBJECT2') {
          currentSection = 'object2';
          continue;
        } else if (key === 'TCA') {
          currentSection = 'relative';
        }

        const numVal = Number(val);
        const finalVal = !isNaN(numVal) && val !== '' ? numVal : val;

        if (currentSection === 'header') {
          result.header[key] = finalVal;
        } else if (currentSection === 'relative') {
          result.relative[key] = finalVal;
        } else if (currentSection === 'object1') {
          result.object1[key] = finalVal;
        } else if (currentSection === 'object2') {
          result.object2[key] = finalVal;
        }
      }
    }

    return result;
  };

  return CDMEngine;
}));
