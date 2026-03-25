"""
Q-Day Prize: Shor's Algorithm for Elliptic Curve Discrete Logarithm Problem (ECDLP)

A complete quantum cryptanalysis framework targeting ECC keys (1-25 bits)
using Shor's algorithm implemented in Qiskit for the Project Eleven Q-Day Prize.

Architecture:
    - ecc_curves: Small elliptic curve definitions over GF(p)
    - quantum_arithmetic: Reversible modular arithmetic quantum circuits
    - ecc_point_oracle: Quantum oracle for elliptic curve point multiplication
    - shor_ecdlp: Core Shor's algorithm for ECDLP
    - attack_pipeline: End-to-end attack orchestration
"""

__version__ = "1.0.0"
__author__ = "Phillips / Patent-HexagalPairty"
__competition__ = "Project Eleven Q-Day Prize (April 2025 - April 2026)"
