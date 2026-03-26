# Quantum Shor's ECDLP — Q-Day Prize Submission Code

> **PUBLIC-FACING CODE. This is the quantum attack code submitted to the Q-Day Prize. Safe to share.**

This directory implements Shor's algorithm for the Elliptic Curve Discrete Logarithm Problem (ECDLP), targeting the [Project Eleven Q-Day Prize](https://www.qdayprize.com/) (1 BTC, deadline April 5, 2026). It also includes a suite of security bounty hunting tools for ECDSA vulnerabilities, ZK circuit analysis, oracle manipulation detection, and VRF bias testing.

**Dependencies**: `qiskit`, `qiskit-aer`, `qiskit-ibm-runtime`, `numpy`

---

## How Shor's ECDLP Works (The Algorithm)

Given an elliptic curve E over GF(p) with generator G and public key Q = kG, find the secret scalar k.

1. **Prepare two quantum registers** in uniform superposition: |a⟩|b⟩ over all values 0..n-1 (where n = order of G)
2. **Apply the EC point oracle**: |a⟩|b⟩|0⟩ → |a⟩|b⟩|aG + bQ⟩ — this entangles the registers with the elliptic curve computation
3. **Apply inverse QFT** to both registers — this converts period information into measurement outcomes
4. **Measure** → get (j₁, j₂) where j₁/N ≈ r·k/n and j₂/N ≈ -r/n
5. **Extract k** via continued fractions on the ratio j₁/j₂
6. **Verify** by checking Q == kG

Reference: Proos & Zalka 2003.

---

## Architecture

```
QUANTUM CORE (Q-Day Prize submission)
├── shor_ecdlp.py ..................... Main Shor's algorithm implementation
├── ecc_curves.py ..................... Elliptic curve math + precomputed curves
├── quantum_arithmetic.py ............. Reversible modular arithmetic circuits
├── ecc_point_oracle.py ............... Quantum oracle: |a⟩|b⟩ → |aG+bQ⟩
└── attack_pipeline.py ................ End-to-end orchestration + reporting

EXECUTION & CLI
├── run_qday_attack.py ................ Simulator CLI (primary entry point)
├── run_ibm_quantum.py ................ IBM Quantum hardware runner
└── bounty_hunter.py .................. Multi-domain bounty aggregator

AUXILIARY ATTACK ENGINES
└── babel_factorization_engine.py ..... ZTC-Shor hybrid RSA factoring

CIRCUIT SOLVERS
└── peaked_circuit_solver.py .......... BlueQubit Quantum Advantage Challenge

SECURITY SCANNERS (Bounty hunting tools)
├── ecdsa_vuln_scanner.py ............. Solidity ECDSA vulnerability scanner
├── zk_underconstrained_detector.py ... ZK circuit underconstraint detector
├── vrf_bias_detector.py .............. VRF/randomness bias detector
└── tda_oracle_detector.py ............ DeFi oracle manipulation detector
```

---

## Every File Explained

### Quantum Core

#### `shor_ecdlp.py` — The Main Attack
Core implementation of Shor's algorithm for ECDLP. This is the heart of the Q-Day submission.

**Key classes**:
- `ShorResult`: Dataclass wrapping attack outcome — recovered secret key, number of shots, iterations, measurements, candidate keys, success flag, circuit depth, qubit count, gate counts.
- `ShorECDLP`: Main attack class.
  - `__init__(curve, generator, public_key, precision_bits)`: Initialize with curve parameters
  - `build_circuit(use_simplified_oracle, known_key)`: Construct the full quantum circuit (superposition → oracle → inverse QFT → measurement)
  - `extract_key_from_measurements(measurements)`: Convert measurement outcomes to candidate keys using 3 extraction methods (continued fractions, direct ratio, modular inverse)
  - `verify_key(k)`: Check if candidate k satisfies Q == kG
  - `run_attack(backend, shots, max_iterations)`: Full orchestration loop — build, run, extract, verify, repeat
- `BruteForceQuantumSearch`: Grover-enhanced brute force for small keys (for comparison, not eligible for prize)

**Key function**: `attack_ecc_key(bits, secret_key, shots, backend)` — high-level entry point.

#### `ecc_curves.py` — Elliptic Curve Definitions
Small elliptic curves for 1-25 bit security levels, used as test targets.

**Key classes**:
- `ECPoint`: Immutable point (x, y) on the curve. `is_infinity` property for the identity element.
- `EllipticCurve`: Full curve implementation over GF(p) with `add()`, `negate()`, `scalar_mult()` (binary double-and-add), `enumerate_points()`, `find_generator()`, `point_order()`, `security_bits()`.

**Pre-defined curves**: `CURVE_1BIT` (p=3), `CURVE_2BIT` (p=5), `CURVE_3BIT` (p=7), `CURVE_4BIT` (p=13), `CURVE_5BIT` (p=29). Lookup via `QDAY_CURVES` dictionary.

**Key functions**: `generate_curve_for_bits(target_bits)` dynamically creates curves; `generate_keypair(curve)` creates random (k, Q=kG) pairs.

#### `quantum_arithmetic.py` — Reversible Modular Arithmetic Circuits
Builds the quantum circuits for modular addition, multiplication, and inversion that the oracle needs.

**Key classes**:
- `ModularAdder`: QFT-based Draper adder. `build_adder()` implements |a⟩|b⟩ → |a⟩|(a+b) mod p⟩. Also has `build_constant_adder()` and `build_controlled_adder()`.
- `LookupTableOracle`: For small primes (p < 32), encodes all operations as multi-controlled gates from a precomputed lookup table. More gate-efficient than arithmetic circuits for small p. Methods: `build_constant_mult_mod()`, `build_addition_table()`, `build_inversion_table()`.
- `ModularMultiplier`: Controlled modular multiplication using either lookup tables or shift-and-add.

**Key function**: `num_qubits_for_mod(p)` — calculates how many qubits are needed to represent values mod p.

#### `ecc_point_oracle.py` — The Quantum Oracle
Implements the quantum oracle that computes |a⟩|b⟩|0⟩ → |a⟩|b⟩|aP + bQ⟩ on the elliptic curve.

**Key classes**:
- `ECPointOracle`: Main oracle for full point arithmetic. For small curves (order ≤ 64), uses a precomputed lookup table of all (a,b) → aP+bQ mappings encoded as multi-controlled gates. For larger curves (order > 64), would use arithmetic circuits (currently raises NotImplementedError).
- `SimplifiedECOracle`: A "cheating" oracle that directly computes f(a,b) = (a + k·b) mod n — requires knowing k, so it's only for testing, not real attacks.

**Key method**: `_point_to_int(P)` maps an EC point to a unique integer for circuit encoding.

#### `attack_pipeline.py` — End-to-End Orchestration
Connects everything into a complete attack pipeline.

**Key classes**:
- `AttackReport`: JSON-serializable result summary with target_bits, curve_params, recovered_key, verified flag, circuit_stats, backend_info, timing, gate_counts. Methods: `to_json()`, `save(filepath)`.
- `QDayAttackPipeline`: Main orchestrator.
  - `setup_backend(backend_type)`: Configure Aer simulator, IBM hardware, or AWS Braket
  - `generate_target(secret_key)`: Create random ECDLP instance
  - `run_attack(shots, max_iterations)`: Execute full attack → AttackReport
  - `export_qasm(filepath)`: Save circuit in OpenQASM format
  - `export_gate_level(filepath)`: Save transpiled gate counts to JSON

**Key function**: `run_qday_campaign(max_bits, shots, output_dir)` — batch attacks across 1..max_bits.

---

### Execution & CLI

#### `run_qday_attack.py` — Simulator CLI (Primary Entry Point)
Command-line interface for running attacks on the Aer simulator.

```bash
# Basic attack
python -m quantum_btc_qday.run_qday_attack --bits 3 --shots 2048

# Full campaign across bit sizes
python -m quantum_btc_qday.run_qday_attack --campaign --max-bits 5

# Export circuit
python -m quantum_btc_qday.run_qday_attack --bits 2 --export-qasm circuit.qasm

# Fixed key for reproducibility
python -m quantum_btc_qday.run_qday_attack --bits 3 --secret-key 5

# Show curve info
python -m quantum_btc_qday.run_qday_attack --bits 4 --curve-info
```

#### `run_ibm_quantum.py` — IBM Quantum Hardware Runner
Runs attacks on real IBM quantum hardware (ibm_fez 156-qubit Heron r2).

```bash
# Single attack on hardware
python quantum_btc_qday/run_ibm_quantum.py --token $IBM_QUANTUM_TOKEN --bits 1

# Sweep across bit sizes
python quantum_btc_qday/run_ibm_quantum.py --token $IBM_QUANTUM_TOKEN --sweep --max-bits 3

# List available backends
python quantum_btc_qday/run_ibm_quantum.py --token $IBM_QUANTUM_TOKEN --list-backends
```

**Supported backends**: ibm_fez (156-qubit Heron r2), ibm_brisbane, ibm_osaka.
Results saved to `results/ibm/{timestamp}.json`.

#### `bounty_hunter.py` — Multi-Domain Bounty CLI
Unified interface for all security scanning tools.

```bash
python quantum_btc_qday/bounty_hunter.py ecdsa path/to/contracts/  # ECDSA vuln scan
python quantum_btc_qday/bounty_hunter.py zk --demo                 # ZK circuit analysis
python quantum_btc_qday/bounty_hunter.py oracle --demo             # Oracle manipulation
python quantum_btc_qday/bounty_hunter.py vrf --demo                # VRF bias detection
python quantum_btc_qday/bounty_hunter.py factor --demo             # BABEL factoring
python quantum_btc_qday/bounty_hunter.py scan path/to/project/     # Full audit
python quantum_btc_qday/bounty_hunter.py targets                   # Show active bounties
```

**Active bounty targets**: Q-Day Prize (1 BTC), BlueQubit (0.25 BTC), zkSync ($100K), Sky/MakerDAO ($10M), Wormhole ($2M), Axelar ($500K).

---

### Auxiliary Attack Engines

#### `babel_factorization_engine.py` — ZTC-Shor Hybrid Factoring
Factors integers using BABEL tower twin-prime conductors. Implements both classical Shor's (Galois orbit period-finding → spinor half-turn → GCD) and quantum Shor's (QFT circuit → continued fractions → candidate periods).

**Key classes**: `BABELTower` (twin-prime conductor levels), `ZTCShorFactorizer` (classical + quantum factoring), `QDayAttack` (submission package generator).

```bash
python quantum_btc_qday/babel_factorization_engine.py --demo       # Factor all BABEL levels
python quantum_btc_qday/babel_factorization_engine.py --factor 143  # Factor specific number
python quantum_btc_qday/babel_factorization_engine.py --qday        # Generate submission package
```

#### `peaked_circuit_solver.py` — BlueQubit Quantum Advantage Challenge
Solver for the BlueQubit challenge (0.25 BTC): find the "peaked" bitstring in a quantum circuit where one output has anomalously high probability.

**5-strategy cascade**: Simplify circuit → exact statevector (≤28 qubits) → sampling (100K shots) → marginal estimation → light-cone reduction.

---

### Security Scanners

#### `ecdsa_vuln_scanner.py` — ECDSA Vulnerability Scanner
Scans Solidity smart contracts for 9 classes of ECDSA signature vulnerabilities:
1. Raw ecrecover without OpenZeppelin wrapper
2. Missing address(0) validation after ecrecover
3. Signature malleability (unrestricted s-value)
4. Missing nonce (no replay protection)
5. Missing chainId (no cross-chain separation)
6. Missing deadline (no timestamp bounds)
7. Signature reuse (no invalidation)
8. EIP-2612 permit issues
9. EIP-712 domain separator mismatches

**Bounty relevance**: Immunefi Top 10 vulnerability class. Payouts $10K-$2M+.

#### `zk_underconstrained_detector.py` — ZK Circuit Underconstraint Detector
Detects underconstrained ZK circuits using R1CS constraint analysis + E8 cross-parity check. Finds unconstrained wires, underconstrained wires (< 2 constraints), disconnected constraint components, and E8 parity imbalances.

**E8 analysis**: Maps constraint wires onto E8 shells. Well-constrained circuits have balanced D8/S+ representation; underconstrained regions show parity imbalance.

**Targets**: zkSync OS ($100K), zkVerify ($50K), Light Protocol ($50K).

#### `vrf_bias_detector.py` — VRF/Randomness Bias Detector
Tests randomness quality using E8 shell distribution:
1. **Shell chi-squared test**: Random data should fill E8 shells proportionally to [24, 56, 40, 40, 56, 24]
2. **Cross-parity balance test**: D8:S+ ratio should be 7:8 (Z-test)
3. **Galois periodicity test**: No hidden period structure (indicates determinism)

**Targets**: Chainlink VRF integrations, drand protocol, on-chain randomness.

#### `tda_oracle_detector.py` — TDA-Based Oracle Manipulation Detector
Uses persistent homology to detect oracle price manipulation. Normal price feeds have smooth persistence diagrams; flash-loan attacks create topological "explosions" (many features born/dying at the same filtration scale).

**Targets**: Sky/MakerDAO ($10M), any DeFi oracle user ($10K-$500K).

---

## Existing Results

Results from previous attacks are stored in `results/`:

| File | Key Cracked | Field | Qubits | Verified |
|------|-------------|-------|--------|----------|
| `attack_1bit.json` | k=3 | GF(3) | 17 | Yes |
| `attack_2bit.json` | k=2 | GF(5) | 22 | Yes |
| `attack_3bit.json` | k=3 | GF(7) | 17 | Yes |
| `attack_4bit.json` | k=14 | GF(13) | 27 | Yes |

QASM circuits: `circuit_1bit.qasm` through `circuit_3bit.qasm`
Gate-level JSON: `gates_1bit.json` through `gates_4bit.json`

---

## Relationship to Other Directories

- `god_engine/` — The PRIVATE classical factoring engine. DO NOT confuse with this public code.
- `results/` — Attack results (simulator + IBM hardware)
- `submission/` — Complete Q-Day prize submission package
- `source_of_truth/3_systems/quantum_shor/` — Reference copy
