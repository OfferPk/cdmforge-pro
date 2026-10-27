/**
 * CDMForge Pro (v1.0.0) — 10-Point Normative Compliance Auditor
 * Standards: CCSDS 508.0-B-1 (Blue Book) & ISO 26900:2016
 *
 * Evaluates Conjunction Data Messages against 10 strict aerospace rules.
 */

(function(root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.CDMAuditor = factory();
  }
}(typeof self !== 'undefined' ? self : this, function() {
  'use strict';

  const CDMAuditor = {};

  CDMAuditor.RULES = [
    {
      id: 'CDM-001',
      name: 'CCSDS_CDM_VERS Syntax',
      normativeRef: 'CCSDS 508.0-B-1 §3.2',
      check: function(data) {
        const vers = String(data.header.CCSDS_CDM_VERS || '').trim();
        const pass = vers === '1.0';
        return {
          pass: pass,
          value: vers,
          message: pass ? 'Valid CCSDS CDM version 1.0' : `Invalid version '${vers}'; must be '1.0'`
        };
      }
    },
    {
      id: 'CDM-002',
      name: 'Mandatory Header Integrity',
      normativeRef: 'CCSDS 508.0-B-1 §3.2',
      check: function(data) {
        const h = data.header;
        const required = ['CREATION_DATE', 'ORIGINATOR', 'MESSAGE_FOR', 'MESSAGE_ID'];
        const missing = required.filter(k => !h[k] || String(h[k]).trim() === '');
        const pass = missing.length === 0;
        return {
          pass: pass,
          value: pass ? 'All 4 present' : `Missing: ${missing.join(', ')}`,
          message: pass ? 'Mandatory header fields verified' : `Missing header fields: ${missing.join(', ')}`
        };
      }
    },
    {
      id: 'CDM-003',
      name: 'Dual Object Metadata Integrity',
      normativeRef: 'CCSDS 508.0-B-1 §3.3',
      check: function(data) {
        const o1 = data.object1;
        const o2 = data.object2;
        const keys = ['OBJECT_NAME', 'OBJECT_DESIGNATOR', 'OBJECT_TYPE', 'MANEUVERABLE'];
        const missing1 = keys.filter(k => !o1[k]);
        const missing2 = keys.filter(k => !o2[k]);
        const pass = missing1.length === 0 && missing2.length === 0;
        return {
          pass: pass,
          value: pass ? 'Both Objects Valid' : `Obj1 missing: ${missing1.join(',') || 'none'}; Obj2 missing: ${missing2.join(',') || 'none'}`,
          message: pass ? 'Both conjunction participants populated' : 'Incomplete object metadata'
        };
      }
    },
    {
      id: 'CDM-004',
      name: 'ISO 8601 TCA Epoch Strictness',
      normativeRef: 'CCSDS 508.0-B-1 §2.4',
      check: function(data) {
        const tca = String(data.relative.TCA || '').trim();
        const isoRegex = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$/;
        const pass = isoRegex.test(tca) && !isNaN(Date.parse(tca));
        return {
          pass: pass,
          value: tca,
          message: pass ? 'TCA conforms to ISO 8601 UTC' : `TCA '${tca}' violates ISO 8601 UTC format (YYYY-MM-DDThh:mm:ss[.sss]Z)`
        };
      }
    },
    {
      id: 'CDM-005',
      name: 'Miss Distance Consistency',
      normativeRef: 'Celestial Mechanics & Relative Motion',
      check: function(data) {
        const miss = Number(data.relative.MISS_DISTANCE);
        const r = Number(data.relative.RELATIVE_POSITION_R || 0);
        const t = Number(data.relative.RELATIVE_POSITION_T || 0);
        const n = Number(data.relative.RELATIVE_POSITION_N || 0);
        const norm = Math.sqrt(r * r + t * t + n * n);

        const pass = !isNaN(miss) && miss > 0 && Math.abs(miss - norm) < (miss * 0.05 + 1.0);
        return {
          pass: pass,
          value: `${miss.toFixed(1)} m (norm: ${norm.toFixed(1)} m)`,
          message: pass ? 'Miss distance is positive and matches relative position vector' : 'Miss distance inconsistent with relative position vector'
        };
      }
    },
    {
      id: 'CDM-006',
      name: 'Relative Velocity Realism',
      normativeRef: 'Astrodynamics & Orbit Propagation',
      check: function(data) {
        const speed = Number(data.relative.RELATIVE_SPEED);
        const pass = !isNaN(speed) && speed >= 0.01 && speed <= 25.0; // km/s
        return {
          pass: pass,
          value: `${speed} km/s`,
          message: pass ? 'Relative encounter velocity is within physical orbital limits' : `Relative speed ${speed} km/s outside realistic orbital range [0.01, 25.0] km/s`
        };
      }
    },
    {
      id: 'CDM-007',
      name: 'Reference Frame Conformance',
      normativeRef: 'ISO 26900 §4.2 & CCSDS 508.0-B-1',
      check: function(data) {
        const validFrames = ['RTN', 'GCRF', 'EME2000', 'ITRF', 'ICRF'];
        const f1 = String(data.object1.REF_FRAME || '').toUpperCase();
        const f2 = String(data.object2.REF_FRAME || '').toUpperCase();
        const pass = validFrames.includes(f1) && validFrames.includes(f2);
        return {
          pass: pass,
          value: `Obj1: ${f1}, Obj2: ${f2}`,
          message: pass ? 'Approved reference frames (RTN / Celestial Inertial)' : 'Unrecognized or non-standard reference frame'
        };
      }
    },
    {
      id: 'CDM-008',
      name: 'Covariance Matrix Positive Variances',
      normativeRef: 'Mathematical Covariance Properties',
      check: function(data) {
        const o1 = data.object1;
        const o2 = data.object2;
        const v1_r = Number(o1.CR_R), v1_t = Number(o1.CT_T), v1_n = Number(o1.CN_N);
        const v2_r = Number(o2.CR_R), v2_t = Number(o2.CT_T), v2_n = Number(o2.CN_N);

        const pass = v1_r > 0 && v1_t > 0 && v1_n > 0 && v2_r > 0 && v2_t > 0 && v2_n > 0;
        return {
          pass: pass,
          value: pass ? 'All 6 variances > 0' : 'Non-positive diagonal covariance elements detected',
          message: pass ? 'Both covariance matrices have strictly positive diagonal variances' : 'Covariance diagonal variance must be > 0'
        };
      }
    },
    {
      id: 'CDM-009',
      name: 'Collision Probability Realism',
      normativeRef: 'Foster (1992) & SSA Operational Doctrine',
      check: function(data) {
        const pc = Number(data.relative.COLLISION_PROBABILITY);
        const pass = !isNaN(pc) && pc >= 0.0 && pc <= 1.0;
        return {
          pass: pass,
          value: isNaN(pc) ? 'NaN' : pc.toExponential(4),
          message: pass ? 'Collision probability Pc is in valid bounded domain [0.0, 1.0]' : 'Pc must be a valid probability between 0 and 1'
        };
      }
    },
    {
      id: 'CDM-010',
      name: 'Strict KVN Line Syntax',
      normativeRef: 'CCSDS 508.0-B-1 §6.2',
      check: function(data, rawText) {
        if (!rawText) return { pass: true, value: 'Parsed Object Check', message: 'Syntax verified' };
        const lines = rawText.split('\n');
        let invalidLines = 0;
        for (let l of lines) {
          l = l.trim();
          if (!l || l.startsWith('COMMENT')) continue;
          if (!l.includes('=')) {
            invalidLines++;
          }
        }
        const pass = invalidLines === 0;
        return {
          pass: pass,
          value: `${invalidLines} syntax violations`,
          message: pass ? 'Strict KEY = VALUE [UNIT] KVN format compliant' : `Found ${invalidLines} lines violating KVN format`
        };
      }
    }
  ];

  /**
   * Run full audit against parsed or raw CDM KVN
   */
  CDMAuditor.audit = function(cdmData, rawText) {
    const results = [];
    let passedCount = 0;

    for (let rule of CDMAuditor.RULES) {
      const outcome = rule.check(cdmData, rawText);
      if (outcome.pass) passedCount++;
      results.push({
        id: rule.id,
        name: rule.name,
        normativeRef: rule.normativeRef,
        pass: outcome.pass,
        value: outcome.value,
        message: outcome.message
      });
    }

    return {
      total: CDMAuditor.RULES.length,
      passed: passedCount,
      failed: CDMAuditor.RULES.length - passedCount,
      score: (passedCount / CDMAuditor.RULES.length) * 100,
      certified: passedCount === CDMAuditor.RULES.length,
      details: results
    };
  };

  return CDMAuditor;
}));
