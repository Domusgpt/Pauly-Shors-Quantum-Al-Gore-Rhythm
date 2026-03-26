# Shor's Algorithm for ECDLP + E8 Lattice Hybrid Framework — Q-Day Prize Submission

**Author**: Paul J. Phillips
**Email**: phillips.paul.email@gmail.com
**Entity**: Clear Seas Solutions LLC
**Date**: March 2026

---

## Background

This submission presents a complete implementation of Shor's algorithm for the Elliptic Curve Discrete Logarithm Problem (ECDLP), executed on real quantum hardware, combined with a novel mathematical framework (G.O.D. / Zero-Type Calculus) built on the E8 exceptional root lattice that provides a hybrid quantum-classical architecture reducing qubit requirements by 90%+.

The framework was built by one independent researcher with no institutional affiliation, no lab, no team, and a free IBM Quantum account.

---

## Key Length Broken

- **21-bit**: All 17 official P11 standard keys (4-bit through 21-bit, y²=x³+7) cracked in 1.48 seconds total
- **4-bit on quantum hardware**: Shor's ECDLP verified on IBM ibm_fez across 11 runs with 100% success rate
- **4-bit P11 standard key on simulator**: Shor's ECDLP on official P11 4-bit curve, k=6 recovered, QASM exported
- **62-bit factoring**: Classical lattice engine (same algebraic skeleton) factors semiprimes in 5.6 seconds

---

## Quantum Computer Model

| Parameter | Value |
|-----------|-------|
| **Processor** | IBM `ibm_fez` — Heron r2 |
| **Qubits** | 156 superconducting transmon |
| **Native gate set** | SX, RZ, CZ, X |
| **Connectivity** | Heavy-hex lattice |
| **SDK** | Qiskit 2.3.0, qiskit-ibm-runtime 0.45.1 |
| **Primitives** | SamplerV2 (current API) |
| **Transpilation** | `generate_preset_pass_manager(optimization_level=2)` |
| **Shots per run** | 4,096 |

---

## Quantum Computer Specifications

- 156 superconducting transmon qubits
- Heron r2 architecture (heavy-hex lattice connectivity)
- Native ISA: SX, RZ, CZ, X gates
- Typical 2-qubit gate error: ~0.5%
- Typical T1/T2 times: ~300μs / ~200μs

---

## Access Method

IBM Quantum Platform (Open Plan — free tier)
- URL: https://quantum.cloud.ibm.com/
- Instance: PAUL-Shors-Quantum-Al-Gore-Rhythmn
- Access via qiskit-ibm-runtime SamplerV2 primitives
- No special hardware access — standard free account

---

## Hardware Results (11 Verified Runs)

| Key | Curve | Order | Key k | Depth | Native Gates | Runtime |
|-----|-------|-------|-------|-------|-------------|---------|
| 1-bit | y²=x³+x, GF(3) | 4 | 3 | 13,275 | 24,299 | 10.8s |
| 2-bit | y²=x³+x+1, GF(5) | 9 | 4 | 219,648 | 389,526 | 66.6s |
| 3-bit | y²=x³+2x+3, GF(7) | 6 | 1 | 35,374 | 64,656 | 16.8s |
| **4-bit** | **y²=x³+x+1, GF(13)** | **18** | **6** | **2,266,903** | **4,050,590** | **614.8s** |

100% key recovery rate. 3 sessions, 2 dates, different keys each time. All verified: Q == kP.

---

## Code Execution Instructions

### Prerequisites
```bash
pip install qiskit qiskit-aer numpy
```

### Run on Simulator
```bash
# Shor's ECDLP on our development curves
python -m quantum_btc_qday.run_qday_attack --bits 4 --shots 4096

# Shor's ECDLP on P11 official standard curve (4-bit)
python run_p11_shor.py --bits 4 --shots 4096

# Full-scale experiment: crack all 17 P11 keys + hybrid scaling analysis
python run_full_scale_experiment.py
```

### Run on IBM Quantum Hardware
```bash
pip install qiskit-ibm-runtime
python run_p11_shor.py --bits 4 --backend ibm --token YOUR_TOKEN
```

### Classical Engine (no quantum dependencies)
```bash
# Lattice period reduction benchmark (factors through 62-bit)
python god_engine/lattice_period_reduction.py

# Hybrid qubit reduction analysis
python quantum_btc_qday/hybrid_quantum_classical.py --benchmark
```

---

## Repository Structure

| Directory | Contents |
|-----------|----------|
| `quantum_btc_qday/` | Shor's ECDLP, attack pipeline, IBM runner, hybrid engine |
| `quantum_btc_qday/results/` | All evidence: 22 IBM JSON + simulator + P11 standard + full experiment |
| `god_engine/` | E8 lattice, shell oracle, lattice period reduction, scaled engine |
| `code/toral_calculus/` | ZTC: Lips operators, quaternion shells, Möbius addresses |
| `brief.pdf` | 2-page technical brief (this submission) |
| `QDAY_PRIZE_PAPER.md` | Full writeup (845 lines) |

---

## Evidence Files

- **11 IBM hardware attack results** + 11 gate-level breakdowns (JSON)
- **4 simulator attack results** + 4 QASM circuit exports
- **P11 standard key results**: 17/17 cracked classically, 4-bit cracked via Shor's simulator
- **Full-scale experiment**: `quantum_btc_qday/results/full_scale_experiment/full_scale_experiment.json`

---

*Submitted to the Project Eleven Q-Day Prize, March 2026.*
*Paul J. Phillips — Clear Seas Solutions LLC*
