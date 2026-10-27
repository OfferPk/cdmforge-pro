# CCSDS 508.0-B-1 & ISO 26900 Conjunction Data Message (CDM) Technical Specification

## 1\. Executive Summary & Normative Scope

The Consultative Committee for Space Data Systems (CCSDS) 508.0-B-1 Blue Book and ISO 26900:2016 standard establish standard electronic message formats for the exchange of spacecraft orbital conjunction assessments, close-approach geometry, and collision risk data between Space Situational Awareness (SSA) tracking networks, satellite owner/operators (O/O), launch service providers, and collision avoidance (COLA) flight dynamics centers.

As orbital traffic and space debris multiply, automated machine-to-machine exchange of Conjunction Data Messages (CDMs) is mandatory for timely risk screening, automated alert triage, and emergency collision avoidance maneuver execution.

---

## 2\. Normative Architecture & Conjunction Geometry

### 2.1 Encounter Time of Closest Approach (TCA)

All relative parameters (relative position, relative velocity, and miss distance) are evaluated at the Time of Closest Approach (TCA), formatted strictly per ISO 8601 UTC: `YYYY-MM-DDThh:mm:ss[.sss]Z`

### 2.2 Relative Coordinate Frames

Relative encounter geometry is typically expressed in the Radial, Transverse, and Normal (RTN) coordinate system anchored on the primary asset (Object 1):

- **Radial (\$R\$)**: Aligned along the primary spacecraft position vector pointing outward from the Earth center of mass.  
- **Transverse (\$T\$)**: Oriented in the orbital plane along the velocity vector (for circular orbits, orthogonal to \$R\$).  
- **Normal (\$N\$)**: Orthogonal to the orbital plane, aligned with the orbital angular momentum vector \$\\mathbf{h} \= \\mathbf{r} \\times \\mathbf{v}\$.

### 2.3 Encounter B-Plane & Collision Plane

In high-velocity conjunction encounters (\$\\Delta v \\gg 1\\text{ km/s}\$), relative motion is modeled as rectilinear across the encounter interval. The collision plane (B-plane) is perpendicular to the relative velocity vector \$\\mathbf{v}\_{rel} \= \\mathbf{v}\_2 \- \\mathbf{v}\_1\$. The position uncertainty of Object 1 and Object 2, described by 3x3 covariance matrices \$\\mathbf{C}*1\$ and \$\\mathbf{C}2\$, is summed and projected onto the 2D collision plane: \$\$\\mathbf{C}^\* \= \\mathbf{C}{1,\\text{plane}} \+ \\mathbf{C}*{2,\\text{plane}} \= \\begin{bmatrix} \\sigma\_x^2 & \\rho \\sigma\_x \\sigma\_y \\ \\rho \\sigma\_x \\sigma\_y & \\sigma\_y^2 \\end{bmatrix}\$\$

---

## 3\. Foster 1992 Analytical Collision Probability (\$P\_c\$)

CDMForge Pro implements the NASA standard Foster (1992) analytical formulation (*Foster, J. L., "A Calculation of the Probability of Collision Between Two Orbiting Bodies," NASA JSC-25763*).

Given:

- Miss vector \$(\\tilde{x}\_m, \\tilde{y}\_m)\$ transformed into the principal axes of the combined covariance ellipse.  
- Principal uncertainty standard deviations \$\\sigma\_1, \\sigma\_2\$ (square roots of eigenvalues \$\\lambda\_1, \\lambda\_2\$).  
- Combined hard-body sphere collision radius \$R\_H \= R\_1 \+ R\_2\$.

For \$R\_H \\ll \\sigma\_1, \\sigma\_2\$: \$\$P\_c \\approx \\frac{\\pi R\_H^2}{2\\pi \\sigma\_1 \\sigma\_2} \\exp\\left( \-\\frac{1}{2} \\left\[ \\frac{\\tilde{x}\_m^2}{\\sigma\_1^2} \+ \\frac{\\tilde{y}\_m^2}{\\sigma\_2^2} \\right\] \\right) \\cdot \\left\[ 1 \- \\frac{R\_H^2}{8}\\left( \\frac{1 \- u^2}{\\sigma\_1^2} \+ \\frac{1 \- v^2}{\\sigma\_2^2} \\right) \\right\]\$\$ where \$u \= \\tilde{x}\_m / \\sigma\_1\$ and \$v \= \\tilde{y}\_m / \\sigma\_2\$.

---

## 4\. Operational Risk Classification Tiers

Satellite operations guidelines establish three operational decision thresholds:

| Risk Tier | Collision Probability (\$P\_c\$) | Operational Action Required |
| :---- | :---- | :---- |
| **RED ALERT** | \$P\_c \\ge 10^{-4}\$ | **Mandatory Maneuver**: Emergency thruster burn planning, conjunction waiver, or differential drag adjustment. |
| **YELLOW WATCH** | \$10^{-6} \\le P\_c \< 10^{-4}\$ | **High Vigilance**: Request additional radar/optical tracking passes, re-evaluate with updated orbit determination. |
| **GREEN NOMINAL** | \$P\_c \< 10^{-6}\$ | **Standard Monitoring**: Conjunction clear of maneuver thresholds; automated tracking continues. |

---

## 5\. Normative Keyword-Value Notation (KVN) Format

CCSDS\_CDM\_VERS \= 1.0

CREATION\_DATE               \= 2026-10-16T12:00:00.000Z

ORIGINATOR                  \= CDMFORGE\_PRO\_SSA

MESSAGE\_FOR                 \= FLIGHT\_DYNAMICS\_OPERATIONS

MESSAGE\_ID                  \= CDM-2026-984210

TCA                         \= 2026-10-17T03:42:18.520Z

MISS\_DISTANCE               \= 142.500 \[m\]

RELATIVE\_SPEED              \= 11.4200 \[km/s\]

RELATIVE\_POSITION\_R         \= 42.100 \[m\]

RELATIVE\_POSITION\_T         \= 118.400 \[m\]

RELATIVE\_POSITION\_N         \= \-67.196 \[m\]

RELATIVE\_VELOCITY\_R         \= \-4.2000 \[km/s\]

RELATIVE\_VELOCITY\_T         \= 8.9000 \[km/s\]

RELATIVE\_VELOCITY\_N         \= 6.8000 \[km/s\]

COLLISION\_PROBABILITY       \= 1.987000e-04

COLLISION\_PROBABILITY\_METHOD= FOSTER-1992

OBJECT                      \= OBJECT1

OBJECT\_DESIGNATOR           \= 2024-089AA

OBJECT\_NAME                 \= STARLINK-31042

OBJECT\_TYPE                 \= PAYLOAD

MANEUVERABLE                \= YES

REF\_FRAME                   \= RTN

HARD\_BODY\_RADIUS            \= 4.50 \[m\]

CR\_R                        \= 120.0000 \[m\*\*2\]

CT\_T                        \= 1850.0000 \[m\*\*2\]

CN\_N                        \= 140.0000 \[m\*\*2\]

OBJECT                      \= OBJECT2

OBJECT\_DESIGNATOR           \= 1993-036PX

OBJECT\_NAME                 \= COSMOS 2251 DEB

OBJECT\_TYPE                 \= DEBRIS

MANEUVERABLE                \= NO

REF\_FRAME                   \= RTN

HARD\_BODY\_RADIUS            \= 0.80 \[m\]

CR\_R                        \= 480.0000 \[m\*\*2\]

CT\_T                        \= 8400.0000 \[m\*\*2\]

CN\_N                        \= 520.0000 \[m\*\*2\]