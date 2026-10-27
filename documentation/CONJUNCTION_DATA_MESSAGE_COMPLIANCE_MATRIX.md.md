# Conjunction Data Message (CDM) 10-Point Normative Compliance Matrix

| Rule ID | Check Item | Normative Reference | Verification Method | Pass Criteria |
| :---- | :---- | :---- | :---- | :---- |
| **CDM-001** | CCSDS\_CDM\_VERS Syntax | CCSDS 508.0-B-1 §3.2 | Exact String Match | Must equal '1.0' |
| **CDM-002** | Mandatory Header Completeness | CCSDS 508.0-B-1 §3.2 | Field Presence Check | CREATION\_DATE, ORIGINATOR, MESSAGE\_FOR, MESSAGE\_ID all present and non-empty |
| **CDM-003** | Dual Object Metadata Integrity | CCSDS 508.0-B-1 §3.3 | Entity Validation | OBJECT\_NAME, OBJECT\_DESIGNATOR, OBJECT\_TYPE, MANEUVERABLE populated for both Object 1 & Object 2 |
| **CDM-004** | ISO 8601 TCA Epoch Strictness | CCSDS 508.0-B-1 §2.4 | Strict ISO Regex & Datetime Parse | Conforms to YYYY-MM-DDThh:mm:ss\[.sss\]Z |
| **CDM-005** | Miss Distance Consistency | Astrodynamics / Relative State | Geometric Vector Norm Check | MISS\_DISTANCE \> 0 and consistent with \$\\sqrt{R^2 \+ T^2 \+ N^2}\$ within 5% or 1m tolerance |
| **CDM-006** | Relative Velocity Realism | Celestial Mechanics | Physical Range Boundary Check | 0.01 km/s \<= RELATIVE\_SPEED \<= 25.0 km/s |
| **CDM-007** | Reference Frame Conformance | ISO 26900 §4.2 | Enumeration Check | REF\_FRAME in {RTN, GCRF, EME2000, ITRF, ICRF} |
| **CDM-008** | Covariance Matrix Positive Variances | Matrix Algebra / Covariance Theory | Positivity Check | Diagonal position variances \$CR\_R \> 0, CT\_T \> 0, CN\_N \> 0\$ for both objects |
| **CDM-009** | Collision Probability Realism | Foster (1992) Formulation | Mathematical Bounds Check | \$0.0 \\le P\_c \\le 1.0\$ and declared calculation method |
| **CDM-010** | Strict KVN Line Syntax | CCSDS 508.0-B-1 §6.2 | Lexical Syntax Parser | Strict KEY \= VALUE \[UNIT\] structure without unkeyed drift |

