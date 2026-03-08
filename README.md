# Q-Day Prize: Shor's ECDLP Attack

Shor's algorithm for the Elliptic Curve Discrete Logarithm Problem. Breaks ECC keys from 1-5 bits on quantum hardware/simulator.

**Submission for [Project Eleven Q-Day Prize](https://qprize.org)** — Deadline: April 5, 2026

## Quick Start

```bash
pip install qiskit qiskit-aer numpy
python -m src.run_qday_attack --bits 4 --shots 2048
```

## IBM Quantum Hardware

```bash
pip install qiskit-ibm-runtime
python src/run_ibm_quantum.py --token YOUR_TOKEN --bits 1
```

## Export Gate-Level Code

```bash
python -m src.run_qday_attack --bits 4 --export-qasm circuit.qasm
python -m src.run_qday_attack --bits 4 --export-gates gates.json
```

## Results

4-bit key recovered: k=14, verified, 27 qubits, depth 960, 2048 shots.

See [SUBMISSION.md](SUBMISSION.md) for full technical writeup.

## Author

Paul J. Phillips — Clear Seas Solutions LLC
