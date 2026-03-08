# Q-Day Prize: G.O.D. Engine — Classical Factoring via E8 Lattice Geometry

A novel classical factoring system that exploits the algebraic structure of the E8 root lattice to emulate quantum period-finding deterministically. Achieves **O(log³ N)** for smooth-p-1 composites — matching Shor's complexity class without a quantum computer.

**Submission for [Project Eleven Q-Day Prize](https://qprize.org)** — Deadline: April 5, 2026

## Quick Start

```bash
pip install numpy
python god_engine/run_all.py                     # Full benchmark
python god_engine/run_all.py --factor 143         # Factor a specific number
python god_engine/run_all.py --benchmark 40       # Benchmark to N bits
python god_engine/run_all.py --verify             # Verify E8 lattice
```

## The System

The G.O.D. (Geometric Orthogonal Dialectics) Engine is 11 modules:

| Module | What It Does |
|--------|-------------|
| `e8_lattice.py` | 240 E8 roots, D8/S+ type separation, cross-parity Coxeter projection, 6-shell decomposition, BABEL tower |
| `shell_oracle.py` | Shell Oracle Period Extraction — E8 shell index as coarse period oracle (64 mults = free constraints on r) |
| `sope_fast.py` | BSGS + shell constraints for O(N^{1/4}) order-finding, phi(N) reconstruction |
| `tower_oracle.py` | BABEL-guided Pollard p-1 with tower smoothness basis — O(log³ N) for smooth cases |
| `phi_reconstruction.py` | Reconstruct phi(N) from type ratios + period LCM |
| `galois_qpu.py` | Deterministic QPU emulation via Galois orbit traversal |
| `moire_factor.py` | Moire interference patterns between lattice projections reveal factors |
| `tda_engine.py` | Persistent homology on E8-projected residue clouds |
| `crypto_analyzer.py` | RSA / ECDLP / ZK circuit vulnerability analysis |
| `run_all.py` | Unified runner and benchmark |

## Key Results

- **BABEL tower conductors** (15, 35, 143, 323, 899): factored at **O(log³ N)** via tower Pollard p-1
- **Shell oracle**: 64 multiplications mod 240 = free period constraints on any N
- **Type parity**: D8/S+ split provides a free bit that halves search space
- **Multiplier k**: phi(N) / lcm(orders) is bounded small — reconstruction is O(1)

## The Novel Claims

1. The E8 shell index is a **coarse oracle** for multiplicative order (cost: 64 mults)
2. The D8/S+ type parity gives a **free information bit** per base
3. The BABEL tower provides a **natural smoothness basis** from lattice geometry
4. For B-smooth p-1: **O(B · log² N)** — polylogarithmic, matching Shor's class
5. Shell-monitored early termination via D8 half-turn detection

## Dependencies

```
numpy (only dependency)
```

No Qiskit. No quantum hardware. No simulators. Pure classical computation on the E8 lattice.

## Author

Paul J. Phillips — Clear Seas Solutions LLC
Framework: G.O.D. (Geometric Orthogonal Dialectics)
