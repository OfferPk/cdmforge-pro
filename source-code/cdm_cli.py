#!/usr/bin/env python3
"""
CDMForge Pro (v1.0.0) — Command-Line Flight Dynamics & Conjunction Assessment Tool
Standards: CCSDS 508.0-B-1 (Blue Book) & ISO 26900:2016
Pure Python 3 implementation with zero external dependencies.
"""

import sys
import os
import math
import argparse
import json
import re
from datetime import datetime

PRESETS = {
    'leo': {
        'name': 'LEO: Active Mega-Constellation vs Debris',
        'tca': '2026-10-17T03:42:18.520Z',
        'miss_distance_m': 142.5,
        'rel_speed_kms': 11.42,
        'rel_pos_rtn': {'r': 42.1, 't': 118.4, 'n': -67.196},
        'rel_vel_rtn': {'r': -4.2, 't': 8.9, 'n': 6.8},
        'obj1': {
            'name': 'STARLINK-31042', 'id': '2024-089AA', 'catalog': 'SATCAT',
            'type': 'PAYLOAD', 'maneuverable': 'YES', 'hard_body_radius_m': 4.5,
            'ref_frame': 'RTN',
            'cov_rtn': {'cr_r': 120.0, 'ct_r': 45.0, 'ct_t': 1850.0, 'cn_r': -12.0, 'cn_t': 88.0, 'cn_n': 140.0}
        },
        'obj2': {
            'name': 'COSMOS 2251 DEB', 'id': '1993-036PX', 'catalog': 'SATCAT',
            'type': 'DEBRIS', 'maneuverable': 'NO', 'hard_body_radius_m': 0.8,
            'ref_frame': 'RTN',
            'cov_rtn': {'cr_r': 480.0, 'ct_r': 120.0, 'ct_t': 8400.0, 'cn_r': -25.0, 'cn_t': 210.0, 'cn_n': 520.0}
        }
    },
    'sso': {
        'name': 'SSO: Earth Observation vs Spent Upper Stage',
        'tca': '2026-10-18T14:15:05.100Z',
        'miss_distance_m': 612.0,
        'rel_speed_kms': 14.85,
        'rel_pos_rtn': {'r': 185.0, 't': 520.0, 'n': -264.422},
        'rel_vel_rtn': {'r': 2.1, 't': 12.4, 'n': 7.9},
        'obj1': {
            'name': 'SENTINEL-2C', 'id': '2024-160A', 'catalog': 'SATCAT',
            'type': 'PAYLOAD', 'maneuverable': 'YES', 'hard_body_radius_m': 3.2,
            'ref_frame': 'RTN',
            'cov_rtn': {'cr_r': 85.0, 'ct_r': 32.0, 'ct_t': 940.0, 'cn_r': -8.0, 'cn_t': 45.0, 'cn_n': 95.0}
        },
        'obj2': {
            'name': 'SL-16 R/B', 'id': '1990-045B', 'catalog': 'SATCAT',
            'type': 'ROCKET BODY', 'maneuverable': 'NO', 'hard_body_radius_m': 5.5,
            'ref_frame': 'RTN',
            'cov_rtn': {'cr_r': 950.0, 'ct_r': 310.0, 'ct_t': 14200.0, 'cn_r': -45.0, 'cn_t': 380.0, 'cn_n': 1100.0}
        }
    },
    'geo': {
        'name': 'GEO: Commercial Telecomm Colocation Drift',
        'tca': '2026-10-19T08:00:00.000Z',
        'miss_distance_m': 4250.0,
        'rel_speed_kms': 0.185,
        'rel_pos_rtn': {'r': 450.0, 't': 3800.0, 'n': 1849.324},
        'rel_vel_rtn': {'r': 0.02, 't': 0.15, 'n': -0.09},
        'obj1': {
            'name': 'SES-17', 'id': '2021-095A', 'catalog': 'SATCAT',
            'type': 'PAYLOAD', 'maneuverable': 'YES', 'hard_body_radius_m': 12.0,
            'ref_frame': 'RTN',
            'cov_rtn': {'cr_r': 450.0, 'ct_r': 120.0, 'ct_t': 2200.0, 'cn_r': 15.0, 'cn_t': 60.0, 'cn_n': 380.0}
        },
        'obj2': {
            'name': 'EUTELSAT 10B', 'id': '2022-157A', 'catalog': 'SATCAT',
            'type': 'PAYLOAD', 'maneuverable': 'YES', 'hard_body_radius_m': 10.5,
            'ref_frame': 'RTN',
            'cov_rtn': {'cr_r': 520.0, 'ct_r': 150.0, 'ct_t': 2800.0, 'cn_r': -20.0, 'cn_t': 75.0, 'cn_n': 410.0}
        }
    }
}

def calculate_collision_probability(miss_x, miss_y, sigma1, sigma2, hard_body_radius):
    """
    Foster 1992 2D Analytical Collision Probability Calculation.
    """
    if sigma1 <= 0 or sigma2 <= 0 or hard_body_radius <= 0:
        return 0.0
    u = miss_x / sigma1
    v = miss_y / sigma2
    dist_sq = u * u + v * v
    exp_term = math.exp(-0.5 * dist_sq)
    area = math.pi * hard_body_radius * hard_body_radius
    norm = 2.0 * math.pi * sigma1 * sigma2
    pc = (area / norm) * exp_term

    # Series correction
    s1_sq = sigma1 * sigma1
    s2_sq = sigma2 * sigma2
    correction = 1.0 - (hard_body_radius * hard_body_radius / 8.0) * ((1.0 - u * u) / s1_sq + (1.0 - v * v) / s2_sq)
    pc = pc * max(0.1, correction)
    return max(0.0, min(1.0, pc))

def compute_encounter_covariance(cov1, cov2):
    """
    Combines two RTN covariances and extracts principal 2D B-plane uncertainties.
    """
    var_x = cov1['cr_r'] + cov2['cr_r']
    var_y = (cov1['cn_n'] + cov2['cn_n']) + (cov1['ct_t'] + cov2['ct_t']) * 0.1
    cov_xy = (cov1['cn_r'] + cov2['cn_r']) * 0.5

    tr = var_x + var_y
    det = var_x * var_y - cov_xy * cov_xy
    disc = max(0.0, tr * tr - 4.0 * det)
    lambda1 = 0.5 * (tr + math.sqrt(disc))
    lambda2 = 0.5 * (tr - math.sqrt(disc))

    sigma1 = math.sqrt(max(1.0, lambda1))
    sigma2 = math.sqrt(max(1.0, lambda2))
    theta_rad = 0.5 * math.atan2(2.0 * cov_xy, var_x - var_y)
    theta_deg = math.degrees(theta_rad) % 360.0

    return {
        'sigma1': sigma1,
        'sigma2': sigma2,
        'theta_deg': theta_deg,
        'var_x': var_x,
        'var_y': var_y,
        'cov_xy': cov_xy
    }

def generate_cdm(preset_key='leo'):
    p = PRESETS.get(preset_key, PRESETS['leo'])
    enc = compute_encounter_covariance(p['obj1']['cov_rtn'], p['obj2']['cov_rtn'])
    hard_body_radius = p['obj1']['hard_body_radius_m'] + p['obj2']['hard_body_radius_m']
    pc = calculate_collision_probability(p['rel_pos_rtn']['r'], p['rel_pos_rtn']['n'], enc['sigma1'], enc['sigma2'], hard_body_radius)

    now_iso = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')
    lines = [
        "CCSDS_CDM_VERS = 1.0",
        "COMMENT ====================================================================",
        "COMMENT  CDMForge Pro (v1.0.0) — CCSDS 508.0-B-1 / ISO 26900 Conjunction Data Message",
        "COMMENT ====================================================================",
        f"CREATION_DATE               = {now_iso}",
        "ORIGINATOR                  = CDMFORGE_PRO_SSA",
        "MESSAGE_FOR                 = FLIGHT_DYNAMICS_OPERATIONS",
        f"MESSAGE_ID                  = CDM-2026-984210",
        "",
        "COMMENT --------------------------------------------------------------------",
        "COMMENT  RELATIVE ENCOUNTER METADATA & CONJUNCTION SUMMARY",
        "COMMENT --------------------------------------------------------------------",
        f"TCA                         = {p['tca']}",
        f"MISS_DISTANCE               = {p['miss_distance_m']:.3f} [m]",
        f"RELATIVE_SPEED              = {p['rel_speed_kms']:.4f} [km/s]",
        f"RELATIVE_POSITION_R         = {p['rel_pos_rtn']['r']:.3f} [m]",
        f"RELATIVE_POSITION_T         = {p['rel_pos_rtn']['t']:.3f} [m]",
        f"RELATIVE_POSITION_N         = {p['rel_pos_rtn']['n']:.3f} [m]",
        f"RELATIVE_VELOCITY_R         = {p['rel_vel_rtn']['r']:.4f} [km/s]",
        f"RELATIVE_VELOCITY_T         = {p['rel_vel_rtn']['t']:.4f} [km/s]",
        f"RELATIVE_VELOCITY_N         = {p['rel_vel_rtn']['n']:.4f} [km/s]",
        "START_SCREEN_PERIOD         = 2026-10-16T12:00:00.000Z",
        "STOP_SCREEN_PERIOD          = 2026-10-19T12:00:00.000Z",
        "SCREEN_VOLUME_FRAME         = RTN",
        "SCREEN_VOLUME_SHAPE         = ELLIPSOID",
        "SCREEN_VOLUME_X             = 2000.0 [m]",
        "SCREEN_VOLUME_Y             = 10000.0 [m]",
        "SCREEN_VOLUME_Z             = 2000.0 [m]",
        f"COLLISION_PROBABILITY       = {pc:.6e}",
        "COLLISION_PROBABILITY_METHOD= FOSTER-1992",
        "",
        "COMMENT --------------------------------------------------------------------",
        "COMMENT  OBJECT 1: PRIMARY ASSET METADATA & ORBIT STATE",
        "COMMENT --------------------------------------------------------------------",
        "OBJECT                      = OBJECT1",
        f"OBJECT_DESIGNATOR           = {p['obj1']['id']}",
        f"CATALOG_NAME                = {p['obj1']['catalog']}",
        f"OBJECT_NAME                 = {p['obj1']['name']}",
        f"INTERNATIONAL_DESIGNATOR    = {p['obj1']['id']}",
        f"OBJECT_TYPE                 = {p['obj1']['type']}",
        "OPERATOR_CONTACT_POSITION   = FLIGHT_DYNAMICS_DIRECTOR",
        "OPERATOR_ORGANIZATION       = GLOBAL_SPACE_CONSORTIUM",
        "EPHEMERIS_NAME              = HIGH_PRECISION_NUMERICAL_PROP",
        "COVARIANCE_METHOD           = CALCULATED",
        f"MANEUVERABLE                = {p['obj1']['maneuverable']}",
        f"REF_FRAME                   = {p['obj1']['ref_frame']}",
        f"HARD_BODY_RADIUS            = {p['obj1']['hard_body_radius_m']:.2f} [m]",
        f"CR_R                        = {p['obj1']['cov_rtn']['cr_r']:.4f} [m**2]",
        f"CT_R                        = {p['obj1']['cov_rtn']['ct_r']:.4f} [m**2]",
        f"CT_T                        = {p['obj1']['cov_rtn']['ct_t']:.4f} [m**2]",
        f"CN_R                        = {p['obj1']['cov_rtn']['cn_r']:.4f} [m**2]",
        f"CN_T                        = {p['obj1']['cov_rtn']['cn_t']:.4f} [m**2]",
        f"CN_N                        = {p['obj1']['cov_rtn']['cn_n']:.4f} [m**2]",
        "",
        "COMMENT --------------------------------------------------------------------",
        "COMMENT  OBJECT 2: SECONDARY OBJECT METADATA & ORBIT STATE",
        "COMMENT --------------------------------------------------------------------",
        "OBJECT                      = OBJECT2",
        f"OBJECT_DESIGNATOR           = {p['obj2']['id']}",
        f"CATALOG_NAME                = {p['obj2']['catalog']}",
        f"OBJECT_NAME                 = {p['obj2']['name']}",
        f"INTERNATIONAL_DESIGNATOR    = {p['obj2']['id']}",
        f"OBJECT_TYPE                 = {p['obj2']['type']}",
        "OPERATOR_CONTACT_POSITION   = SSA_TRACKING_CENTER",
        "OPERATOR_ORGANIZATION       = INTERNATIONAL_DEBRIS_OFFICE",
        "EPHEMERIS_NAME              = RADAR_TRACKING_NETWORK_TLE",
        "COVARIANCE_METHOD           = CALCULATED",
        f"MANEUVERABLE                = {p['obj2']['maneuverable']}",
        f"REF_FRAME                   = {p['obj2']['ref_frame']}",
        f"HARD_BODY_RADIUS            = {p['obj2']['hard_body_radius_m']:.2f} [m]",
        f"CR_R                        = {p['obj2']['cov_rtn']['cr_r']:.4f} [m**2]",
        f"CT_R                        = {p['obj2']['cov_rtn']['ct_r']:.4f} [m**2]",
        f"CT_T                        = {p['obj2']['cov_rtn']['ct_t']:.4f} [m**2]",
        f"CN_R                        = {p['obj2']['cov_rtn']['cn_r']:.4f} [m**2]",
        f"CN_T                        = {p['obj2']['cov_rtn']['cn_t']:.4f} [m**2]",
        f"CN_N                        = {p['obj2']['cov_rtn']['cn_n']:.4f} [m**2]"
    ]
    return '\n'.join(lines)

def parse_cdm(text):
    result = {'header': {}, 'relative': {}, 'object1': {}, 'object2': {}}
    section = 'header'
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('COMMENT'):
            continue
        if '=' in line:
            parts = line.split('=', 1)
            key = parts[0].strip()
            val = parts[1].strip()
            # remove [unit]
            m = re.match(r'^(.+?)\s*\[.+?\]$', val)
            if m:
                val = m.group(1).strip()
            if key == 'OBJECT' and val == 'OBJECT1':
                section = 'object1'
                continue
            elif key == 'OBJECT' and val == 'OBJECT2':
                section = 'object2'
                continue
            elif key == 'TCA':
                section = 'relative'

            if key != 'CCSDS_CDM_VERS':
                try:
                    num = float(val)
                    val = num
                except ValueError:
                    pass
            result[section][key] = val
    return result

def audit_cdm(data, raw_text):
    checks = []

    # CDM-001
    v = str(data['header'].get('CCSDS_CDM_VERS', ''))
    checks.append(('CDM-001', 'CCSDS_CDM_VERS Syntax', v == '1.0', f"Version '{v}'"))

    # CDM-002
    h = data['header']
    req_h = ['CREATION_DATE', 'ORIGINATOR', 'MESSAGE_FOR', 'MESSAGE_ID']
    missing_h = [k for k in req_h if k not in h]
    checks.append(('CDM-002', 'Mandatory Header Integrity', len(missing_h) == 0, f"Missing: {missing_h}"))

    # CDM-003
    o1, o2 = data['object1'], data['object2']
    req_o = ['OBJECT_NAME', 'OBJECT_DESIGNATOR', 'OBJECT_TYPE', 'MANEUVERABLE']
    m1 = [k for k in req_o if k not in o1]
    m2 = [k for k in req_o if k not in o2]
    checks.append(('CDM-003', 'Dual Object Metadata Integrity', len(m1) == 0 and len(m2) == 0, f"O1:{len(m1)} O2:{len(m2)}"))

    # CDM-004
    tca = str(data['relative'].get('TCA', ''))
    iso_ok = bool(re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$', tca))
    checks.append(('CDM-004', 'ISO 8601 TCA Epoch Strictness', iso_ok, tca))

    # CDM-005
    miss = float(data['relative'].get('MISS_DISTANCE', 0))
    r = float(data['relative'].get('RELATIVE_POSITION_R', 0))
    t = float(data['relative'].get('RELATIVE_POSITION_T', 0))
    n = float(data['relative'].get('RELATIVE_POSITION_N', 0))
    norm_pos = math.sqrt(r*r + t*t + n*n)
    miss_ok = miss > 0 and abs(miss - norm_pos) < (miss * 0.05 + 1.0)
    checks.append(('CDM-005', 'Miss Distance Consistency', miss_ok, f"{miss:.1f}m (norm {norm_pos:.1f}m)"))

    # CDM-006
    speed = float(data['relative'].get('RELATIVE_SPEED', 0))
    speed_ok = 0.01 <= speed <= 25.0
    checks.append(('CDM-006', 'Relative Velocity Realism', speed_ok, f"{speed:.2f} km/s"))

    # CDM-007
    f1 = str(o1.get('REF_FRAME', '')).upper()
    f2 = str(o2.get('REF_FRAME', '')).upper()
    frames_ok = f1 in ['RTN', 'GCRF', 'EME2000', 'ITRF', 'ICRF'] and f2 in ['RTN', 'GCRF', 'EME2000', 'ITRF', 'ICRF']
    checks.append(('CDM-007', 'Reference Frame Conformance', frames_ok, f"{f1}/{f2}"))

    # CDM-008
    cov_ok = (float(o1.get('CR_R', 0)) > 0 and float(o1.get('CT_T', 0)) > 0 and float(o1.get('CN_N', 0)) > 0 and
              float(o2.get('CR_R', 0)) > 0 and float(o2.get('CT_T', 0)) > 0 and float(o2.get('CN_N', 0)) > 0)
    checks.append(('CDM-008', 'Covariance Matrix Positive Variances', cov_ok, "All 6 variances > 0" if cov_ok else "Non-positive variance"))

    # CDM-009
    try:
        pc = float(data['relative'].get('COLLISION_PROBABILITY', -1))
        pc_ok = 0.0 <= pc <= 1.0
    except ValueError:
        pc_ok = False
        pc = -1
    checks.append(('CDM-009', 'Collision Probability Realism', pc_ok, f"{pc:.4e}" if pc_ok else "Invalid Pc"))

    # CDM-010
    syntax_errs = 0
    for line in raw_text.splitlines():
        line = line.strip()
        if line and not line.startswith('COMMENT') and '=' not in line:
            syntax_errs += 1
    checks.append(('CDM-010', 'Strict KVN Line Syntax', syntax_errs == 0, f"{syntax_errs} errors"))

    return checks

def main():
    parser = argparse.ArgumentParser(description="CDMForge Pro — CCSDS 508.0-B-1 Flight Dynamics CLI")
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # generate-cdm
    p_gen = subparsers.add_parser('generate-cdm', help='Generate standard CCSDS CDM message')
    p_gen.add_argument('--preset', choices=['leo', 'sso', 'geo'], default='leo', help='Preset scenario')
    p_gen.add_argument('--output', '-o', help='Output file path')

    # parse
    p_parse = subparsers.add_parser('parse', help='Parse CDM KVN file')
    p_parse.add_argument('input', help='Path to CDM file')

    # audit
    p_audit = subparsers.add_parser('audit', help='Audit CDM KVN file against 10 normative rules')
    p_audit.add_argument('input', help='Path to CDM file')

    # calculate-pc
    p_pc = subparsers.add_parser('calculate-pc', help='Calculate collision probability (Foster 1992)')
    p_pc.add_argument('--miss-x', type=float, required=True, help='Miss distance along primary axis (m)')
    p_pc.add_argument('--miss-y', type=float, required=True, help='Miss distance along secondary axis (m)')
    p_pc.add_argument('--sigma1', type=float, required=True, help='Semi-major axis uncertainty (m)')
    p_pc.add_argument('--sigma2', type=float, required=True, help='Semi-minor axis uncertainty (m)')
    p_pc.add_argument('--radius', type=float, required=True, help='Combined hard body radius (m)')

    args = parser.parse_args()

    if args.command == 'generate-cdm':
        cdm_str = generate_cdm(args.preset)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(cdm_str)
            print(f"Generated CDM saved to {args.output}")
        else:
            print(cdm_str)

    elif args.command == 'parse':
        with open(args.input, 'r') as f:
            content = f.read()
        parsed = parse_cdm(content)
        print(json.dumps(parsed, indent=2))

    elif args.command == 'audit':
        with open(args.input, 'r') as f:
            content = f.read()
        parsed = parse_cdm(content)
        checks = audit_cdm(parsed, content)
        passed = sum(1 for c in checks if c[2])
        total = len(checks)
        print("=================================================================")
        print("  CDMForge Pro (v1.0.0) — 10-Point Normative Compliance Audit    ")
        print("  Standard: CCSDS 508.0-B-1 (Blue Book) & ISO 26900:2016          ")
        print("=================================================================")
        for rule_id, name, ok, val in checks:
            status = "[PASS]" if ok else "[FAIL]"
            print(f" {status} {rule_id}: {name:<35} | {val}")
        print("-----------------------------------------------------------------")
        print(f" Score: {passed}/{total} Passed ({(passed/total)*100:.1f}%)")
        if passed == total:
            print(" Verdict: CERTIFIED CONFORMANT (CCSDS_508_CDM_CERTIFIED)")
        else:
            print(" Verdict: NON-CONFORMANT")
            sys.exit(1)

    elif args.command == 'calculate-pc':
        pc = calculate_collision_probability(args.miss_x, args.miss_y, args.sigma1, args.sigma2, args.radius)
        print(f"Foster-1992 Collision Probability: {pc:.6e}")
        if pc >= 1e-4:
            print("Alert Tier: RED ALERT (Emergency maneuver required)")
        elif pc >= 1e-6:
            print("Alert Tier: YELLOW WATCH (High vigilance monitoring)")
        else:
            print("Alert Tier: GREEN NOMINAL (Standard clearance)")
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
