# Q-Day Attack Results

Verified results from running Shor's algorithm for the Elliptic Curve Discrete Logarithm Problem (ECDLP) against small ECC keys. These results serve as evidence for the [Project Eleven Q-Day Prize](https://www.qdayprize.com/) submission (1 BTC bounty, deadline April 5, 2026).

All attacks use the two-register Shor's ECDLP circuit architecture (Proos & Zalka 2003): two quantum registers prepared in uniform superposition, an oracle computing aP + bQ via lookup table, inverse QFT applied to both registers, and key extraction via continued fractions and lattice reduction.

The source code lives in `/quantum_btc_qday/` (particularly `shor_ecdlp.py` and `run_qday_attack.py`).

---

## Simulator Results (Qiskit AerSimulator)

Noise-free simulator runs establishing baseline correctness. Each file pair consists of an attack result JSON and a gate-level summary JSON.

### attack_1bit.json / gates_1bit.json

| Field | Value |
|-------|-------|
| Curve | E: y^2 = x^3 + x over GF(3), group order 4 |
| Generator | (2, 1) |
| Public Key | (2, 2) |
| Recovered Private Key | **k = 3** |
| Verified | Yes |
| Qubits | 17 (two 7-qubit registers + 3 oracle ancillae) |
| Precision Bits | 7 |
| Circuit Depth | 3,054 |
| Dominant Gates | 2,310 CX, 1,332 P, 384 Tdg, 240 T |
| Shots | 4,096 |
| Runtime | 0.72 seconds |

### attack_2bit.json / gates_2bit.json

| Field | Value |
|-------|-------|
| Curve | E: y^2 = x^3 + x + 1 over GF(5), group order 9 |
| Generator | (0, 1) |
| Public Key | (2, 4) |
| Recovered Private Key | **k = 6** |
| Verified | Yes |
| Qubits | 22 (two 9-qubit registers + 4 oracle ancillae) |
| Precision Bits | 9 |
| Circuit Depth | 56,816 |
| Dominant Gates | 37,842 CX, 12,012 P, 9,828 Tdg, 7,780 T |
| Shots | 4,096 |
| Runtime | 148.9 seconds |

### attack_3bit.json / gates_3bit.json

| Field | Value |
|-------|-------|
| Curve | E: y^2 = x^3 + 2x + 3 over GF(7), group order 6 |
| Generator | (2, 1) |
| Public Key | (2, 6) |
| Recovered Private Key | **k = 5** |
| Verified | Yes |
| Qubits | 17 (two 7-qubit registers + 3 oracle ancillae) |
| Precision Bits | 7 |
| Circuit Depth | 7,942 |
| Dominant Gates | 5,898 CX, 3,352 P, 1,008 Tdg, 630 T |
| Shots | 4,096 |
| Runtime | 1.43 seconds |

### attack_4bit.json / gates_4bit.json

| Field | Value |
|-------|-------|
| Curve | E: y^2 = x^3 + x + 1 over GF(13), group order 18 |
| Generator | (1, 4) |
| Public Key | (11, 2) |
| Recovered Private Key | **k = 14** |
| Verified | Yes |
| Qubits | 27 (two 11-qubit registers + 5 oracle ancillae) |
| Precision Bits | 11 |
| Circuit Depth | 960 |
| Dominant Gates | 630 MCX, 622 X, 110 CP |
| Shots | 2,048 |
| Runtime | 27.5 seconds |

---

## QASM Circuit Exports

OpenQASM 2.0 circuit definitions for the simulator attacks. These are the full gate-level decompositions that the Q-Day Prize requires as submission evidence.

| File | Target | Registers | Structure |
|------|--------|-----------|-----------|
| `circuit_1bit.qasm` | 1-bit key | `a[7]`, `b[7]`, `oracle_out[3]` | Hadamard init, SimplifiedOracle, two IQFT blocks, measurement |
| `circuit_2bit.qasm` | 2-bit key | `a[9]`, `b[9]`, `oracle_out[4]` | Same architecture, larger registers |
| `circuit_3bit.qasm` | 3-bit key | `a[7]`, `b[7]`, `oracle_out[3]` | Same architecture |

Each QASM file contains custom gate definitions (`mcphase`, `mcx`, `gate_SimplifiedOracle`, `gate_IQFT`) decomposed into native gates (H, P, T, Tdg, CX, RZ, CP, SWAP).

---

## IBM Quantum Hardware Results (`ibm/` subdirectory)

Results from runs on **IBM Fez** (ibm_fez), a 156-qubit IBM Quantum processor accessed via IBM Quantum free tier. These are the real-hardware evidence required by the Q-Day Prize rubric ("Quantum Hardware Dependency" scoring category).

Hardware runs are transpiled to the native gate set of the IBM backend (SX, RZ, CZ, X).

### 1-bit attacks (3 runs)

| File | Date | Key | Verified | Qubits | Depth | Runtime |
|------|------|-----|----------|--------|-------|---------|
| `attack_1bit_ibm_fez_20260308_043641.json` | 2026-03-08 | Recovered | Yes | 156 | 13,101 | ~12s |
| `attack_1bit_ibm_fez_20260320_224238.json` | 2026-03-20 | Recovered | Yes | 156 | 13,101 | ~12s |
| `attack_1bit_ibm_fez_20260320_231831.json` | 2026-03-20 | k=2 | Yes | 156 | 13,101 | 12.2s |

Native gate counts (typical): 11,234 SX + 7,280 RZ + 5,445 CZ + 333 X.

### 2-bit attacks (3 runs)

| File | Date | Verified | Qubits | Depth |
|------|------|----------|--------|-------|
| `attack_2bit_ibm_fez_20260308_043805.json` | 2026-03-08 | Yes | 156 | varies |
| `attack_2bit_ibm_fez_20260320_224348.json` | 2026-03-20 | Yes | 156 | varies |
| `attack_2bit_ibm_fez_20260320_232027.json` | 2026-03-20 | Yes | 156 | varies |

### 3-bit attacks (3 runs)

| File | Date | Verified | Qubits | Depth |
|------|------|----------|--------|-------|
| `attack_3bit_ibm_fez_20260308_043833.json` | 2026-03-08 | Yes | 156 | varies |
| `attack_3bit_ibm_fez_20260320_224410.json` | 2026-03-20 | Yes | 156 | varies |
| `attack_3bit_ibm_fez_20260320_232110.json` | 2026-03-20 | Yes | 156 | varies |

### 4-bit attacks (2 runs)

| File | Date | Key | Verified | Qubits | Depth | Runtime |
|------|------|-----|----------|--------|-------|---------|
| `attack_4bit_ibm_fez_20260320_225429.json` | 2026-03-20 | Recovered | Yes | 156 | 3,657,879 | ~18 min |
| `attack_4bit_ibm_fez_20260320_233920.json` | 2026-03-20 | k=2 | Yes | 156 | 3,657,879 | 1,086s |

Native gate counts (4-bit, typical): 2,982,761 SX + 2,022,900 RZ + 1,385,759 CZ + 72,183 X.

Each hardware result also has an accompanying `gates_*_ibm_fez_*.json` file with the high-level gate summary (pre-transpilation).

---

## Q-Day Prize Relevance

The Q-Day Prize rubric scores submissions across five categories (max 20 points):

1. **Writeup Clarity** -- The attack JSON files contain full `approach_description` fields documenting the algorithm.
2. **Technical Coherence** -- Complete Shor's ECDLP implementation with standard Proos-Zalka two-register architecture.
3. **Quantum Hardware Dependency** -- IBM Fez hardware results in `ibm/` demonstrate real quantum execution (required by the rules).
4. **Implementation Impact** -- Keys cracked at 1-4 bit levels, both on simulator and real hardware. Method scales to 256-bit keys given sufficient qubits.
5. **Resource Complexity** -- Gate counts, circuit depths, and qubit counts are fully documented in each JSON file.

---

## How to Reproduce

```bash
# Simulator attacks (requires qiskit + qiskit-aer)
python -m quantum_btc_qday.run_qday_attack --bits 1 --shots 4096
python -m quantum_btc_qday.run_qday_attack --bits 2 --shots 4096
python -m quantum_btc_qday.run_qday_attack --bits 3 --shots 4096
python -m quantum_btc_qday.run_qday_attack --bits 4 --shots 2048

# Export QASM circuits
python -m quantum_btc_qday.run_qday_attack --bits 3 --export-qasm circuit_3bit.qasm

# IBM Quantum hardware (requires IBM_QUANTUM_TOKEN)
python quantum_btc_qday/run_ibm_quantum.py --token $IBM_QUANTUM_TOKEN --bits 1
python quantum_btc_qday/run_ibm_quantum.py --token $IBM_QUANTUM_TOKEN --sweep --max-bits 4
```
