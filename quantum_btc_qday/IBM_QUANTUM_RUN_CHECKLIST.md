# IBM Quantum Hardware Run Checklist — Q-Day Prize Submission

**Date:** 2026-03-24
**Goal:** Get real hardware results for 1-3 bit ECDLP keys on IBM Quantum free tier

---

## Prerequisites

- [ ] **IBM Quantum Account**: Register at https://quantum.ibm.com/
- [ ] **API Token**: Copy from dashboard → Set `IBM_QUANTUM_TOKEN` env var
- [ ] **Dependencies installed**:
  ```bash
  pip install qiskit qiskit-aer qiskit-ibm-runtime numpy
  ```
- [ ] **Verify simulator works first**:
  ```bash
  python -m quantum_btc_qday.run_qday_attack --bits 1 --shots 2048
  python -m quantum_btc_qday.run_qday_attack --bits 2 --shots 2048
  python -m quantum_btc_qday.run_qday_attack --bits 3 --shots 2048
  ```

## Hardware Access

| Backend | Qubits | Type | Status |
|---------|--------|------|--------|
| ibm_fez | 156 | Heron r2 | Primary target |
| ibm_brisbane | 127 | Eagle | Fallback |
| ibm_osaka | 127 | Eagle | Fallback |

**Free tier allocation**: 10 minutes/month on public queues
**Max shots per run**: 100,000

## Run Plan (Budget: 10 min/month)

### Month 1: 1-bit key

```bash
# List available backends first
python quantum_btc_qday/run_ibm_quantum.py --token $IBM_QUANTUM_TOKEN --list-backends

# 1-bit ECDLP (smallest circuit, most likely to succeed)
python quantum_btc_qday/run_ibm_quantum.py \
  --token $IBM_QUANTUM_TOKEN \
  --bits 1 \
  --backend ibm_fez \
  --shots 4096 \
  --optimization-level 3
```

**Expected**: 17 qubits, should complete in <2 minutes
**Save output**: Redirect to `results/hardware_1bit_$(date +%Y%m%d).json`

### Month 2: 2-bit key

```bash
python quantum_btc_qday/run_ibm_quantum.py \
  --token $IBM_QUANTUM_TOKEN \
  --bits 2 \
  --backend ibm_fez \
  --shots 4096 \
  --optimization-level 3
```

**Expected**: 22 qubits, should complete in <5 minutes

### Month 3: 3-bit key (stretch goal)

```bash
python quantum_btc_qday/run_ibm_quantum.py \
  --token $IBM_QUANTUM_TOKEN \
  --bits 3 \
  --backend ibm_fez \
  --shots 8192 \
  --optimization-level 3
```

**Expected**: 17 qubits, may need more shots for signal
**Risk**: Gate depth may exceed decoherence time

## Export Artifacts for Submission

```bash
# Export QASM circuits (required for Q-Day submission)
python -m quantum_btc_qday.run_qday_attack --bits 1 --export-qasm results/hw_circuit_1bit.qasm
python -m quantum_btc_qday.run_qday_attack --bits 2 --export-qasm results/hw_circuit_2bit.qasm
python -m quantum_btc_qday.run_qday_attack --bits 3 --export-qasm results/hw_circuit_3bit.qasm

# Export gate-level JSON
python -m quantum_btc_qday.run_qday_attack --bits 1 --export-gates results/hw_gates_1bit.json
```

## Q-Day Submission Rubric Alignment

| Category | Evidence Needed | Status |
|----------|----------------|--------|
| Writeup Clarity | Summary document explaining Shor's ECDLP approach | TODO |
| Technical Coherence | Circuit diagrams, mathematical proof of correctness | Circuits exist |
| Quantum Hardware Dependency | Real hardware execution logs with timestamps | NEED HW RUNS |
| Implementation Impact | Key bits cracked, scalability analysis | 1-4 bit simulator done |
| Resource Complexity | Gate count, qubit count, depth analysis | Exported in gates_*.json |

## Important Notes

1. **DO NOT submit G.O.D. Engine code** — it's worth more as a patent
2. Submit ONLY the quantum_btc_qday Shor's ECDLP circuits
3. Hardware results must include IBM Quantum job IDs for verification
4. Deadline: April 5, 2026 (12 days from now!)
5. Prize: 1 BTC (~$80K+ at current prices)
6. All submissions are published publicly

## Post-Run Actions

- [ ] Save raw hardware measurement distributions
- [ ] Analyze peak SNR (signal-to-noise ratio)
- [ ] Compare hardware vs simulator results
- [ ] Write submission document referencing hardware job IDs
- [ ] Export all circuits as QASM for submission
- [ ] Upload to Q-Day Prize portal: https://www.qdayprize.com/
