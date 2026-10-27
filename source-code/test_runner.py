#!/usr/bin/env python3
"""
CDMForge Pro (v1.0.0) — Automated Test Suite
Standards: CCSDS 508.0-B-1 (Blue Book) & ISO 26900:2016
Tests core astrodynamics, Foster Pc math, KVN parsing, and the 10-point normative auditor.
"""

import unittest
import math
import sys
import os

# Import CDM CLI modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdm_cli import (
    calculate_collision_probability,
    compute_encounter_covariance,
    generate_cdm,
    parse_cdm,
    audit_cdm,
    PRESETS
)

class TestCDMForgePro(unittest.TestCase):

    def test_01_cdm_generation_leo(self):
        """1. Test standard LEO Conjunction Data Message KVN generation."""
        cdm_str = generate_cdm('leo')
        self.assertIn("CCSDS_CDM_VERS = 1.0", cdm_str)
        self.assertIn("ORIGINATOR                  = CDMFORGE_PRO_SSA", cdm_str)
        self.assertIn("TCA                         = 2026-10-17T03:42:18.520Z", cdm_str)
        self.assertIn("OBJECT_NAME                 = STARLINK-31042", cdm_str)
        self.assertIn("OBJECT_NAME                 = COSMOS 2251 DEB", cdm_str)
        self.assertIn("COLLISION_PROBABILITY_METHOD= FOSTER-1992", cdm_str)

    def test_02_cdm_parsing_kvn(self):
        """2. Test KVN lexical parser and block segmentation."""
        cdm_str = generate_cdm('sso')
        parsed = parse_cdm(cdm_str)
        self.assertEqual(parsed['header']['CCSDS_CDM_VERS'], '1.0')
        self.assertEqual(parsed['object1']['OBJECT_NAME'], 'SENTINEL-2C')
        self.assertEqual(parsed['object2']['OBJECT_NAME'], 'SL-16 R/B')
        self.assertAlmostEqual(float(parsed['relative']['MISS_DISTANCE']), 612.0, places=2)
        self.assertIn('CR_R', parsed['object1'])

    def test_03_relative_geometry_norm(self):
        """3. Test 3D relative position vector norm equals scalar miss distance."""
        for key in ['leo', 'sso', 'geo']:
            p = PRESETS[key]
            r = p['rel_pos_rtn']['r']
            t = p['rel_pos_rtn']['t']
            n = p['rel_pos_rtn']['n']
            norm = math.sqrt(r*r + t*t + n*n)
            self.assertAlmostEqual(norm, p['miss_distance_m'], delta=1.0)

    def test_04_covariance_combination_rtn(self):
        """4. Test RTN covariance combination symmetry and positive variances."""
        p = PRESETS['leo']
        cov1 = p['obj1']['cov_rtn']
        cov2 = p['obj2']['cov_rtn']
        var_r = cov1['cr_r'] + cov2['cr_r']
        var_t = cov1['ct_t'] + cov2['ct_t']
        var_n = cov1['cn_n'] + cov2['cn_n']

        self.assertGreater(var_r, 0.0)
        self.assertGreater(var_t, 0.0)
        self.assertGreater(var_n, 0.0)
        self.assertEqual(var_r, 120.0 + 480.0)

    def test_05_bplane_eigenvalues(self):
        """5. Test B-plane covariance eigenvalue decomposition and sigma bounds."""
        p = PRESETS['leo']
        enc = compute_encounter_covariance(p['obj1']['cov_rtn'], p['obj2']['cov_rtn'])
        self.assertGreater(enc['sigma1'], 0.0)
        self.assertGreater(enc['sigma2'], 0.0)
        self.assertGreaterEqual(enc['sigma1'], enc['sigma2'])
        self.assertGreaterEqual(enc['theta_deg'], 0.0)
        self.assertLess(enc['theta_deg'], 360.0)

    def test_06_foster_pc_calculation(self):
        """6. Test Foster 1992 analytical collision probability behavior."""
        # Case 1: Direct hit (0 miss distance) with tight covariance -> maximum Pc
        pc_direct = calculate_collision_probability(0.0, 0.0, 20.0, 20.0, 5.0)
        self.assertGreater(pc_direct, 0.01)
        self.assertLessEqual(pc_direct, 1.0)

        # Case 2: Distant miss (10,000m miss) -> Pc approaches 0
        pc_far = calculate_collision_probability(5000.0, 5000.0, 50.0, 50.0, 5.0)
        self.assertLess(pc_far, 1e-12)

        # Case 3: Scaling with hard-body radius (Pc proportional to R^2)
        pc_small = calculate_collision_probability(50.0, 50.0, 100.0, 100.0, 2.0)
        pc_large = calculate_collision_probability(50.0, 50.0, 100.0, 100.0, 4.0)
        self.assertAlmostEqual(pc_large / pc_small, 4.0, delta=0.2)

    def test_07_alert_threshold_tiers(self):
        """7. Test operational alert tier classification logic."""
        # Critical LEO
        cdm_leo = generate_cdm('leo')
        parsed_leo = parse_cdm(cdm_leo)
        pc_leo = float(parsed_leo['relative']['COLLISION_PROBABILITY'])
        self.assertGreaterEqual(pc_leo, 1e-4) # Red threshold

        # Nominal GEO
        cdm_geo = generate_cdm('geo')
        parsed_geo = parse_cdm(cdm_geo)
        pc_geo = float(parsed_geo['relative']['COLLISION_PROBABILITY'])
        self.assertLess(pc_geo, 1e-6) # Green threshold

    def test_08_normative_auditor_pass(self):
        """8. Test 10-point normative auditor on compliant LEO Conjunction Data Message."""
        cdm_str = generate_cdm('leo')
        parsed = parse_cdm(cdm_str)
        checks = audit_cdm(parsed, cdm_str)
        self.assertEqual(len(checks), 10)
        passed_count = sum(1 for c in checks if c[2])
        self.assertEqual(passed_count, 10, f"Failed rules: {[c for c in checks if not c[2]]}")

    def test_09_normative_auditor_reject_invalid_vers(self):
        """9. Test auditor catches invalid CCSDS_CDM_VERS syntax."""
        cdm_str = generate_cdm('leo').replace("CCSDS_CDM_VERS = 1.0", "CCSDS_CDM_VERS = 9.9")
        parsed = parse_cdm(cdm_str)
        checks = audit_cdm(parsed, cdm_str)
        rule_001 = next(c for c in checks if c[0] == 'CDM-001')
        self.assertFalse(rule_001[2]) # Must fail

    def test_10_normative_auditor_reject_invalid_tca(self):
        """10. Test auditor catches malformed ISO 8601 TCA epoch."""
        cdm_str = generate_cdm('leo').replace("2026-10-17T03:42:18.520Z", "17-OCT-2026 03:42:18")
        parsed = parse_cdm(cdm_str)
        checks = audit_cdm(parsed, cdm_str)
        rule_004 = next(c for c in checks if c[0] == 'CDM-004')
        self.assertFalse(rule_004[2]) # Must fail

if __name__ == '__main__':
    unittest.main()
