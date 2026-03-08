# CLAUDE.md — Q-Day Prize Submission Repo

## What This Is

Public-facing submission repo for the **Project Eleven Q-Day Prize** (1 BTC, deadline April 5, 2026).

**GitHub**: `Domusgpt/Pauly-Shors-Quantum-Al-Gore-Rhythm`
**Owner**: Paul J. Phillips, Clear Seas Solutions LLC

---

## Current State

The repo currently contains the **G.O.D. Engine** (classical factoring via E8 lattice).

**IMPORTANT**: The Q-Day Prize requires Shor's algorithm on quantum hardware. The G.O.D. Engine is classical. The submission strategy is still being decided:

- **Option A**: Submit G.O.D. Engine as-is, accept low "Quantum Hardware Dependency" score, refuse to share code details (use it as a public timestamp / flex)
- **Option B**: Replace with `quantum_btc_qday/` Shor's ECDLP circuits from the main repo, run on IBM Quantum hardware, submit proper quantum results
- **Option C**: Don't submit to Q-Day at all, protect IP for patent

**All submissions are published publicly by the judges.**

---

## Repo Contents

```
god_engine/          # G.O.D. Engine modules (classical factoring)
README.md            # Project description
SUBMISSION.md        # Q-Day submission writeup
requirements.txt     # numpy only
```

## Source of Truth

The main research repo is at `/home/user/Patent-HexagalPairty-/`. This submission repo is a derivative. See that repo's CLAUDE.md for full documentation.

Key source directories in main repo:
- `/home/user/Patent-HexagalPairty-/god_engine/` — G.O.D. Engine (classical)
- `/home/user/Patent-HexagalPairty-/quantum_btc_qday/` — Shor's ECDLP (quantum)
- `/home/user/Patent-HexagalPairty-/qday_results/` — Existing simulator results

## Commands

```bash
pip install numpy
python god_engine/run_all.py                # Full test
python god_engine/run_all.py --factor 143   # Factor a number
```
