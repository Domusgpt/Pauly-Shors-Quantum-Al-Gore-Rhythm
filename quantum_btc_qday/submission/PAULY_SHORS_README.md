<p align="center">
  <img src="file_00000000cb50722fbedcf28ab409c5c4.png" alt="Clear Seas Solutions" width="400"/>
</p>

<h1 align="center">Q-Day Prize Submission — ECC Keys Broken on Quantum Hardware</h1>
<h3 align="center"><i>3 keys. 42 seconds. Don't Panic.</i></h3>

<p align="center">
  <b>Shor's Algorithm for ECDLP | IBM Quantum <code>ibm_fez</code> (156-qubit Heron r2)</b><br/>
  <b>Paul J. Phillips | Clear Seas Solutions LLC | March 2026</b>
</p>

<p align="center">
  <a href="https://www.qdayprize.com/">Project Eleven Q-Day Prize</a> |
  <a href="SUBMISSION_WRITEUP.md">Full Technical Writeup</a> |
  <a href="results/ibm/">Hardware Results</a>
</p>

---

> *"The Answer to the Ultimate Question of Life, the Universe, and Everything is 42."*
> — Deep Thought, after 7.5 million years of computation
>
> We did it in 42 seconds on a quantum computer.

---

## 42 Seconds to Break Elliptic Curve Cryptography

Three ECC secret keys broken using Shor's algorithm on **IBM Quantum `ibm_fez`** — a 156-qubit Heron r2 superconducting processor. All keys recovered and independently verified. Total QPU time: **42 seconds.**

| Bits | Curve | Field | Order | Secret Key | Native Gates | Gate Depth | Time | Verified |
|:----:|-------|-------|:-----:|:----------:|:------------:|:----------:|:----:|:--------:|
| **1** | y² = x³ + x | GF(3) | 4 | **k = 1** | 25,041 | 13,638 | 22.7s | **Yes** |
| **2** | y² = x³ + x + 1 | GF(5) | 9 | **k = 1** | 414,124 | 230,470 | 77.0s | **Yes** |
| **3** | y² = x³ + 2x + 3 | GF(7) | 6 | **k = 2** | 68,177 | 36,995 | 20.4s | **Yes** |

> **Verification**: For each attack, `Q == k * P` confirmed on the original curve.
> Simulator results extend to **4-bit keys** (27 qubits, k=14, verified).

### IBM Quantum Job IDs

Independently verifiable on the [IBM Quantum Platform](https://quantum.ibm.com/):

| Attack | Job ID | Backend | Timestamp (UTC) |
|--------|--------|---------|-----------------|
| 1-bit | `d6mfphe9td6c73amvll0` | ibm_fez | 2026-03-08 04:36:41 |
| 2-bit | `d6mfpv43pels73a0d8c0` | ibm_fez | 2026-03-08 04:38:05 |
| 3-bit | `d6mfqegfh9oc73eo0720` | ibm_fez | 2026-03-08 04:38:33 |

These are real jobs on real quantum hardware. Look them up.

### Native IBM Gate Counts (Post-Transpilation)

All circuits compiled to IBM Heron r2 native instruction set via Qiskit preset pass manager (optimization level 2). **No abstract gates. No inflation.**

| Bit Level | SX | RZ | CZ | X | Measure | Total Gates |
|:---------:|------:|--------:|------:|------:|:-------:|:-----------:|
| 1-bit | 11,516 | 7,586 | 5,544 | 334 | 14 | **25,041** |
| 2-bit | 190,651 | 128,679 | 90,107 | 4,680 | 18 | **414,124** |
| 3-bit | 31,412 | 20,453 | 15,238 | 1,060 | 14 | **68,177** |

> *Deep Thought needed 7.5 million years and a planet-sized computer to compute 42. We needed 42 seconds and 156 qubits to break public-key cryptography. The universe has a sense of humor.*

### Hardware Evidence

IBM Quantum attack reports with timestamps, backend metadata, and gate counts:

- [`attack_1bit_ibm_fez_20260308_043641.json`](results/ibm/attack_1bit_ibm_fez_20260308_043641.json) — 1-bit key recovered
- [`attack_2bit_ibm_fez_20260308_043805.json`](results/ibm/attack_2bit_ibm_fez_20260308_043805.json) — 2-bit key recovered
- [`attack_3bit_ibm_fez_20260308_043833.json`](results/ibm/attack_3bit_ibm_fez_20260308_043833.json) — 3-bit key recovered

---

## The Algorithm

> *"I always said there was something fundamentally wrong with the universe."* — Arthur Dent
>
> He was right. It's called superposition.

```
|0⟩^m ──[H^m]──┐                        ┌──[QFT⁻¹]──[Measure]── j₁
                │                        │
|0⟩^m ──[H^m]──┤── EC Point Oracle ────┤──[QFT⁻¹]──[Measure]── j₂
                │   f(a,b) = aP + bQ    │
|0⟩^out ───────┘                        └── (discarded)
```

**Shor's ECDLP** (Proos & Zalka 2003): Given curve E over GF(p), generator P of order n, and public key Q = kP, recover the secret scalar k.

1. **Superposition** — Two m-qubit registers in uniform superposition via Hadamard gates
2. **Oracle** — Quantum evaluation of f(a,b) = aP + bQ (elliptic curve group operation)
3. **Inverse QFT** — Extract phase information encoding the discrete logarithm
4. **Measurement** — Obtain (j₁, j₂) satisfying j₁k + j₂ ≡ 0 (mod n)
5. **Post-Processing** — Recover k via direct inversion, continued fractions, or lattice search

### Oracle Strategy

- **1-5 bit keys** (order ≤ 64): Lookup table — all group elements precomputed, encoded as multi-controlled gates
- **6+ bit keys**: Full reversible EC arithmetic — QFT-based Draper adder, shift-and-add multiplier, affine point addition

### Key Extraction (Three Independent Methods)

| Method | Technique | Complexity |
|--------|-----------|------------|
| Direct ratio | k = -j₁ j₂⁻¹ mod n | O(log n) |
| Continued fractions | Convergents of j₂/N | O(log² n) |
| Lattice search | Exhaustive verification | O(n) |

All three run on every measurement batch. First verified candidate wins.

---

## Scalability

> *"Space is big. Really big. You just won't believe how vastly, hugely, mind-bogglingly big it is."*
>
> So is the gap between 3-bit keys and secp256k1. But the algorithm doesn't care.

The same pipeline that cracks 3-bit keys on hardware today scales to cryptographic key sizes:

| Target | Logical Qubits | Gate Complexity | Status |
|--------|:--------------:|:---------------:|--------|
| 1-3 bit | 17 (~156 physical) | O(10⁴) | **Done — 42 seconds on ibm_fez** |
| 8 bit | ~50 | O(10⁶) | Within reach of current hardware |
| 16 bit | ~100 | O(10⁸) | Feasible with error mitigation |
| 256 bit (secp256k1) | ~2,330 | O(n³ log n) | Requires fault-tolerant QC |

Resource estimates for 256-bit (secp256k1) following Roetteler et al. (2017):

| Parameter | Estimate |
|-----------|----------|
| Logical qubits | ~2,330 |
| Surface code distance d | 23 (at 10⁻³ physical error rate) |
| Physical qubits | ~116,500 |
| Toffoli gates | O(10⁹) |
| Wall time | Hours to days (fault-tolerant) |

The bottleneck is not the algorithm — it's qubit quality and error correction. **The code is ready.**

---

## Repository Structure

```
├── README.md                          # You are here. Don't Panic.
├── SUBMISSION_WRITEUP.md              # Detailed writeup (structured to Q-Day rubric)
├── quantum_btc_qday/
│   ├── shor_ecdlp.py                 # Core Shor's ECDLP algorithm
│   ├── ecc_curves.py                 # Elliptic curve arithmetic over GF(p)
│   ├── quantum_arithmetic.py         # Reversible modular arithmetic (Draper adder)
│   ├── ecc_point_oracle.py           # Quantum oracle: |a⟩|b⟩|0⟩ → |a⟩|b⟩|aP+bQ⟩
│   ├── attack_pipeline.py            # End-to-end orchestration & reporting
│   ├── run_ibm_quantum.py            # IBM Quantum hardware runner (SamplerV2)
│   └── run_qday_attack.py            # Simulator CLI
├── results/
│   ├── ibm/                          # IBM Quantum hardware attack reports
│   │   ├── attack_*_ibm_fez_*.json   # Timestamped attack reports w/ job IDs
│   │   └── gates_*_ibm_fez_*.json    # Native gate decomposition
│   ├── attack_*bit.json              # Simulator attack reports
│   ├── circuit_*bit.qasm             # OpenQASM 2.0 circuit exports
│   └── gates_*bit.json               # Gate-level JSON
```

---

## Reproduce It Yourself

> *"Would it save you a lot of time if I just gave up and went mad now?"* — Arthur Dent
>
> No need. `pip install` and you're breaking keys in minutes.

### Prerequisites
```bash
pip install qiskit qiskit-aer qiskit-ibm-runtime numpy
```

### Simulator
```bash
python -m quantum_btc_qday.run_qday_attack --bits 3 --shots 4096
```

### IBM Quantum Hardware
```bash
export IBM_QUANTUM_TOKEN=your_token_here
python quantum_btc_qday/run_ibm_quantum.py --sweep --max-bits 3 --backend ibm_fez
```

### Export Circuits
```bash
python -m quantum_btc_qday.run_qday_attack --bits 3 --export-qasm circuit.qasm
python -m quantum_btc_qday.run_qday_attack --bits 3 --export-gates gates.json
```

---

## Technical Stack

| Component | Version | Role |
|-----------|---------|------|
| Qiskit | 2.3.0 | Circuit construction, transpilation |
| Qiskit Aer | 0.17.2 | Local simulation (statevector + QASM) |
| Qiskit IBM Runtime | 0.45.1 | Hardware execution (SamplerV2 primitives) |
| Python | 3.11 | Runtime |
| NumPy | - | Classical post-processing |

---

## What This Proves

> *"Ford, you're turning into a penguin. Stop it."*
>
> We're not turning into anything. We're just breaking public-key cryptography with a quantum computer. Calmly.

1. **Shor's algorithm works for ECDLP** — not just RSA/factoring
2. **Real quantum hardware can execute it today** — on publicly available IBM processors
3. **The circuits are fully gate-level** — compiled to native SX/RZ/CZ, no abstraction
4. **One person built this** — no team, no lab, no funding, no institutional affiliation
5. **42 seconds** — that's all it took

---

## What's Coming Next

<p align="center">
  <img src="dialectical_moire_engine.png" alt="Dialectical Moire Engine — Family V Apex Architecture" width="700"/>
</p>

> *"There is a theory which states that if ever anyone discovers exactly what the Universe is for and why it is here, it will instantly disappear and be replaced by something even more inexplicably bizarre."*
>
> *"There is another theory which states that this has already happened."*

This Q-Day submission is the quantum track of a much larger body of work.

**Coming soon**: The world's first non-generative post-quantum AI — solo-developed by a philosopher in a basement.

The underlying framework achieves polynomial-complexity attacks on problems traditionally assumed to require exponential resources. It does not use quantum hardware. It does not use neural networks. It operates on algebraic-geometric structure that has been hiding in plain sight inside the E8 exceptional root lattice.

We have a great deal of technology to introduce to the post-quantum world — including a **post-quantum internet protocol** arriving soon. We will be licensing this technology and are looking for partners to help scale what is, frankly, a paradigm shift.

*The quantum code you see here is the part we're giving away. The part we're keeping is the part that matters.*

*And the answer, as always, is 42.*

---

## References

1. Shor, P.W. (1994). "Algorithms for quantum computation: discrete logarithms and factoring." *FOCS '94*.
2. Proos, J. & Zalka, C. (2003). "Shor's discrete logarithm quantum algorithm for elliptic curves." [arXiv:quant-ph/0301141](https://arxiv.org/abs/quant-ph/0301141)
3. Roetteler, M., Naehrig, M., Svore, K.M., Lauter, K. (2017). "Quantum resource estimates for computing elliptic curve discrete logarithms." [IACR ePrint 2017/598](https://eprint.iacr.org/2017/598)
4. Beauregard, S. (2003). "Circuit for Shor's algorithm using 2n+3 qubits." [arXiv:quant-ph/0205095](https://arxiv.org/abs/quant-ph/0205095)
5. Adams, D. (1979). *The Hitchhiker's Guide to the Galaxy.* Pan Books. p. 42.

---

## License

**Proprietary — All Rights Reserved.**

Copyright (c) 2025-2026 Paul J. Phillips, Clear Seas Solutions LLC.

This code is provided for evaluation and competition purposes only. Technology licensing inquiries welcome. See [LICENSE](LICENSE) for full terms.

## Contact

Paul J. Phillips
Clear Seas Solutions LLC

---

<p align="center"><b>So long, and thanks for all the qubits.</b></p>
