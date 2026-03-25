# Q-Day Prize Submission: Shor's Algorithm for ECDLP

## Competition
- **Prize**: Project Eleven Q-Day Prize (1 BTC)
- **Website**: https://www.qdayprize.com/
- **Deadline**: April 5, 2026
- **Target**: Break ECC keys (1-25 bits) using Shor's algorithm on a quantum computer

---

## Approach

### Algorithm: Shor's Algorithm for Elliptic Curve Discrete Logarithm

**Problem**: Given elliptic curve E over GF(p), generator P of order n, and public key Q = kP, find the secret scalar k.

**Quantum Algorithm (Proos & Zalka 2003)**:

1. **Initialize** two m-qubit registers |a⟩ and |b⟩ in uniform superposition (m ≥ 2⌈log₂(n)⌉ + 1)
2. **Oracle**: Compute |a⟩|b⟩|0⟩ → |a⟩|b⟩|aP + bQ⟩ using reversible EC arithmetic
3. **QFT**: Apply inverse Quantum Fourier Transform to both |a⟩ and |b⟩
4. **Measure**: Obtain (j₁, j₂) satisfying j₁/N ≈ rk/n and j₂/N ≈ -r/n
5. **Extract**: Compute k = -j₁/j₂ mod n using continued fractions

### Implementation

**For 1-5 bit keys (group order ≤ 64)**:
- Oracle implemented as a direct lookup table
- All points aP + bQ precomputed classically
- Encoded as multi-controlled NOT gates
- This approach is efficient for small groups and demonstrates the algorithm correctly

**For 6-25 bit keys (group order > 64)**:
- Full reversible modular arithmetic circuits
- QFT-based Draper adder for modular addition
- Shift-and-add for modular multiplication
- Lookup table for modular inversion (small p)
- Reversible EC point addition using affine coordinates

### Key Extraction

Three complementary methods for extracting k from measurements:

1. **Direct ratio**: k = -j₁ · j₂⁻¹ mod n
2. **Continued fractions**: Extract r/n from j₂/N, then solve for k
3. **Lattice search**: For small n, exhaustive verification against all (r, k) pairs

### Scalability to 256-bit Keys

The approach is general and scales to Bitcoin's 256-bit secp256k1 curve:
- **Qubits**: 9n + 2⌈log₂(n)⌉ + 10 ≈ 2,330 logical qubits for n=256
- **Gates**: O(n³ log n) Toffoli gates
- **Method**: No classical shortcuts; pure quantum computation of ECDLP
- **Oracle**: Replaces lookup table with full reversible EC arithmetic (Roetteler et al. 2017)

---

## Technical Specifications

### Circuit Architecture

```
|0⟩^m ──[H⊗m]──┐                    ┌──[QFT⁻¹]──[Measure]── j₁
                 │                    │
|0⟩^m ──[H⊗m]──┤── EC Oracle ──────├──[QFT⁻¹]──[Measure]── j₂
                 │   f(a,b)=aP+bQ    │
|0⟩^out ────────┘                    └── (traced out)
```

### Gate Counts (representative)

| Bit Level | Qubits | Depth  | CX Gates | Total Gates |
|-----------|--------|--------|----------|-------------|
| 1-bit     | ~7     | ~50    | ~20      | ~100        |
| 2-bit     | ~11    | ~200   | ~150     | ~500        |
| 3-bit     | ~15    | ~800   | ~600     | ~2000       |
| 5-bit     | ~21    | ~5000  | ~4000    | ~15000      |

### Software Stack

- **Framework**: Qiskit 1.x
- **Simulator**: Qiskit Aer (statevector/qasm)
- **Hardware**: IBM Quantum (qiskit-ibm-runtime) or AWS Braket
- **Language**: Python 3.10+

---

## File Structure

```
quantum_btc_qday/
├── __init__.py              # Package definition
├── ecc_curves.py            # Elliptic curve definitions and arithmetic
├── quantum_arithmetic.py    # Reversible modular arithmetic circuits
├── ecc_point_oracle.py      # Quantum oracle for EC point operations
├── shor_ecdlp.py           # Shor's algorithm for ECDLP
├── attack_pipeline.py       # End-to-end attack orchestration
├── run_qday_attack.py       # CLI entry point
├── requirements.txt         # Python dependencies
└── QDAY_SUBMISSION.md       # This document
```

---

## Running the Attack

### Simulator (proof of concept)
```bash
pip install qiskit qiskit-aer numpy
python -m quantum_btc_qday.run_qday_attack --bits 3 --shots 4096
```

### IBM Quantum Hardware
```bash
pip install qiskit-ibm-runtime
python -m quantum_btc_qday.run_qday_attack --bits 1 --backend ibm --token YOUR_TOKEN
```

### Full Campaign
```bash
python -m quantum_btc_qday.run_qday_attack --campaign --max-bits 5
```

### Export Gate-Level Code
```bash
python -m quantum_btc_qday.run_qday_attack --bits 3 --export-qasm circuit_3bit.qasm
python -m quantum_btc_qday.run_qday_attack --bits 3 --export-gates gates_3bit.json
```

---

## References

1. Shor, P. (1994). "Algorithms for quantum computation: discrete logarithms and factoring"
2. Proos, J. & Zalka, C. (2003). "Shor's discrete logarithm quantum algorithm for elliptic curves" [arXiv:quant-ph/0301141]
3. Roetteler, M. et al. (2017). "Quantum resource estimates for computing elliptic curve discrete logarithms" [IACR ePrint 2017/598]
4. Beauregard, S. (2003). "Circuit for Shor's algorithm using 2n+3 qubits"
5. Banegas, G. et al. (2021). "Quantum resource estimates of Grover's key search on AES"

---

## Contact

Submitted for the Project Eleven Q-Day Prize (https://www.qdayprize.com/)
Repository: Patent-HexagalPairty-
