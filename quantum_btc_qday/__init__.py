"""
Q-Day Prize: Shor's Algorithm for Elliptic Curve Discrete Logarithm Problem (ECDLP)

A complete quantum cryptanalysis framework targeting ECC keys (1-25 bits)
using Shor's algorithm implemented in Qiskit for the Project Eleven Q-Day Prize.

Enhanced with:
    - Noise-tolerant post-processing (majority voting, lattice projection)
    - Error mitigation (optimization_level=3, multi-run aggregation)
    - E8 lattice-theoretic measurement visualization
    - Statistical analysis (Shannon entropy, peak SNR, vote counts)

Architecture:
    - ecc_curves: Small elliptic curve definitions over GF(p)
    - quantum_arithmetic: Reversible modular arithmetic quantum circuits
    - ecc_point_oracle: Quantum oracle with Gray code optimization
    - shor_ecdlp: Core Shor's algorithm with enhanced post-processing
    - attack_pipeline: End-to-end orchestration with statistics
    - e8_visualization: E8 lattice measurement analysis
"""

__version__ = "2.0.0"
__author__ = "Phillips / Patent-HexagalPairty"
__competition__ = "Project Eleven Q-Day Prize (April 2025 - April 2026)"
