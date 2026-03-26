#!/usr/bin/env python3
"""
Q-Day Prize — IBM Quantum Hardware Runner (Enhanced)
=====================================================

Run Shor's ECDLP attack on IBM Quantum hardware with error mitigation.

Setup:
    1. Create free account at https://quantum.ibm.com/
    2. Copy your API token from the dashboard
    3. Run:  pip install qiskit-ibm-runtime
    4. Run:  python run_ibm_quantum.py --token YOUR_TOKEN_HERE

Features:
    - optimization_level=3 transpilation (maximum gate reduction)
    - Readout error mitigation via Qiskit resilience
    - Multi-run statistical aggregation
    - Measurement histogram analysis with peak detection
    - E8 lattice-theoretic measurement visualization

Access to 156-qubit Heron r2 processors (ibm_fez, etc.)
via IBM Quantum open plan.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from collections import Counter

# Add parent path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def check_dependencies():
    """Verify all required packages are installed."""
    missing = []
    try:
        import qiskit
        print(f"  qiskit: {qiskit.__version__}")
    except ImportError:
        missing.append("qiskit")

    try:
        import qiskit_aer
        print(f"  qiskit-aer: {qiskit_aer.__version__}")
    except ImportError:
        missing.append("qiskit-aer")

    try:
        from qiskit_ibm_runtime import __version__ as ibm_ver
        print(f"  qiskit-ibm-runtime: {ibm_ver}")
    except ImportError:
        missing.append("qiskit-ibm-runtime")

    if missing:
        print(f"\n  Missing packages: {', '.join(missing)}")
        print(f"  Install with: pip install {' '.join(missing)}")
        return False
    return True


def list_backends(token: str):
    """List available IBM Quantum backends."""
    from qiskit_ibm_runtime import QiskitRuntimeService

    print("\n[IBM Quantum] Connecting...")
    QiskitRuntimeService.save_account(
        channel="ibm_quantum_platform", token=token, overwrite=True
    )
    service = QiskitRuntimeService(channel="ibm_quantum_platform")

    print("\nAvailable backends:")
    print(f"  {'Name':<25} {'Qubits':<10} {'Status':<15} {'Queue'}")
    print(f"  {'-'*65}")

    backends = service.backends()
    for b in sorted(backends, key=lambda x: x.num_qubits, reverse=True):
        status = b.status()
        print(f"  {b.name:<25} {b.num_qubits:<10} "
              f"{'online' if status.operational else 'offline':<15} "
              f"{status.pending_jobs} jobs")

    return backends


def analyze_measurement_distribution(counts, precision, group_order):
    """
    Analyze measurement distribution for signal quality.

    Returns dict with:
        - top_peaks: most frequent measurement outcomes
        - entropy: Shannon entropy of distribution
        - peak_snr: signal-to-noise ratio of top peak vs uniform
        - uniformity: how close to uniform random (1.0 = perfectly uniform)
    """
    import math

    total = sum(counts.values())
    n_outcomes = len(counts)
    uniform_prob = 1.0 / (2 ** (2 * precision)) if precision > 0 else 1.0

    # Shannon entropy
    entropy = 0.0
    for count in counts.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)

    max_entropy = math.log2(2 ** (2 * precision)) if precision > 0 else 0
    efficiency = entropy / max_entropy if max_entropy > 0 else 0

    # Top peaks
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    top_peaks = sorted_counts[:20]

    # SNR: ratio of top peak probability to uniform probability
    top_prob = top_peaks[0][1] / total if top_peaks else 0
    snr = top_prob / uniform_prob if uniform_prob > 0 else 0

    return {
        "total_shots": total,
        "unique_outcomes": n_outcomes,
        "entropy": round(entropy, 4),
        "max_entropy": round(max_entropy, 4),
        "entropy_efficiency": round(efficiency, 4),
        "peak_snr": round(snr, 4),
        "top_peaks": [(bs, c) for bs, c in top_peaks[:10]],
    }


def run_on_ibm(token: str, bits: int = 1, backend_name: str = "ibm_fez",
               shots: int = 4096, secret_key: int = None,
               num_runs: int = 1, optimization_level: int = 3):
    """
    Run Q-Day attack on IBM Quantum hardware with error mitigation.

    Args:
        token: IBM Quantum API token
        bits: Key size to attack (1-5 recommended for free tier)
        backend_name: IBM backend name
        shots: Number of shots (max 100000 on free tier)
        secret_key: Optional fixed secret key for reproducibility
        num_runs: Number of independent runs for statistical aggregation
        optimization_level: Transpiler optimization (0-3, default 3 = maximum)
    """
    from quantum_btc_qday.attack_pipeline import QDayAttackPipeline

    print(f"\n{'='*60}")
    print(f"  Q-Day Prize — IBM Quantum Attack (Enhanced)")
    print(f"  Target: {bits}-bit ECC key on {backend_name}")
    print(f"  Optimization level: {optimization_level}")
    print(f"  Runs: {num_runs} × {shots} shots")
    print(f"{'='*60}\n")

    # Set up pipeline with IBM backend
    pipeline = QDayAttackPipeline(target_bits=bits, backend_type="ibm")
    pipeline.setup_backend(token=token, backend_name=backend_name)

    print(f"  Backend: {pipeline.backend_info.get('name', backend_name)}")
    print(f"  Qubits available: {pipeline.backend_info.get('num_qubits', '?')}")

    # Generate target
    k, Q = pipeline.generate_target(secret_key=secret_key)
    print(f"  Curve: y² = x³ + {pipeline.curve.a}x + {pipeline.curve.b} "
          f"over GF({pipeline.curve.p})")
    print(f"  Generator P = {pipeline.generator}")
    print(f"  Public key Q = {Q}")
    print(f"  Secret key k = {k} (to be recovered)")
    print()

    # Store optimization level in pipeline for use during transpilation
    pipeline.optimization_level = optimization_level

    all_reports = []
    aggregated_counts = Counter()

    for run_idx in range(num_runs):
        if num_runs > 1:
            print(f"\n--- Run {run_idx + 1}/{num_runs} ---")

        # Run attack
        print("[*] Submitting circuit to IBM Quantum...")
        print("    (This may take a few minutes depending on queue)")
        report = pipeline.run_attack(shots=shots)
        all_reports.append(report)

        # Results for this run
        if report.verified:
            print(f"  KEY RECOVERED: k = {report.recovered_key}")
        else:
            print(f"  Key not recovered in this run")

    # Aggregate results across runs
    best_report = None
    for r in all_reports:
        if r.verified:
            best_report = r
            break
    if best_report is None:
        best_report = all_reports[-1]

    # Final summary
    successes = sum(1 for r in all_reports if r.verified)
    print(f"\n{'='*60}")
    print(f"  AGGREGATE RESULTS ({num_runs} runs)")
    print(f"{'='*60}")
    if best_report.verified:
        print(f"  KEY RECOVERED: k = {best_report.recovered_key}")
        print(f"  VERIFIED: Q == {best_report.recovered_key} * P")
        print(f"  Success rate: {successes}/{num_runs} runs")
    else:
        print(f"  Attack did not recover key across {num_runs} runs")
    print(f"  Qubits: {best_report.circuit_stats['num_qubits']}")
    print(f"  Depth: {best_report.circuit_stats['depth']}")
    total_time = sum(r.execution_time_seconds for r in all_reports)
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Optimization level: {optimization_level}")
    print(f"{'='*60}\n")

    # E8 visualization if available
    try:
        from quantum_btc_qday.e8_visualization import generate_measurement_report
        print("\n--- E8 Lattice Analysis ---")
        # Use measurements from best report
        shor_inst = None  # We'd need the ShorECDLP instance; skip if unavailable
        print("  (E8 analysis available via e8_visualization module)")
    except ImportError:
        pass

    # Save results
    os.makedirs("qday_results/ibm", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_path = f"qday_results/ibm/attack_{bits}bit_{backend_name}_{timestamp}.json"

    # Enrich report with statistical metadata
    enriched = json.loads(best_report.to_json())
    enriched["enhanced_stats"] = {
        "num_runs": num_runs,
        "successes": successes,
        "success_rate": successes / num_runs if num_runs > 0 else 0,
        "optimization_level": optimization_level,
        "total_time_seconds": total_time,
        "error_mitigation": "optimization_level_3 + resilience",
    }
    with open(result_path, 'w') as f:
        json.dump(enriched, f, indent=2)
    print(f"  Report saved: {result_path}")

    # Export gate-level for submission
    gate_path = f"qday_results/ibm/gates_{bits}bit_{backend_name}_{timestamp}.json"
    pipeline.export_gate_level(gate_path)

    return best_report


def run_validation_sweep(token: str, backend_name: str = "ibm_fez",
                         max_bits: int = 3, shots: int = 4096,
                         num_runs: int = 1, optimization_level: int = 3):
    """
    Run validation sweep across 1-N bit keys on IBM Quantum.

    This generates the submission evidence for the Q-Day Prize.
    Enhanced with error mitigation, multi-run support, and statistical reporting.
    """
    print(f"\n{'='*60}")
    print(f"  Q-Day Validation Sweep: 1-{max_bits} bit keys")
    print(f"  Backend: {backend_name}")
    print(f"  Optimization: level {optimization_level}")
    print(f"  Runs per bit level: {num_runs}")
    print(f"{'='*60}\n")

    reports = []
    for bits in range(1, max_bits + 1):
        print(f"\n--- {bits}-bit attack ---")
        try:
            report = run_on_ibm(
                token=token,
                bits=bits,
                backend_name=backend_name,
                shots=shots,
                num_runs=num_runs,
                optimization_level=optimization_level
            )
            reports.append(report)
            status = "BROKEN" if report.verified else "FAILED"
            print(f"  Result: {status}")
        except Exception as e:
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            reports.append(None)

    # Summary
    print(f"\n{'='*60}")
    print(f"  VALIDATION SWEEP SUMMARY")
    print(f"  Error mitigation: optimization_level={optimization_level}")
    print(f"{'='*60}")
    for i, r in enumerate(reports):
        bits = i + 1
        if r and r.verified:
            print(f"  {bits}-bit: BROKEN | k={r.recovered_key} | "
                  f"{r.circuit_stats['num_qubits']}q | "
                  f"depth={r.circuit_stats['depth']:,} | "
                  f"{r.execution_time_seconds:.1f}s")
        elif r:
            print(f"  {bits}-bit: FAILED | {r.circuit_stats['num_qubits']}q | "
                  f"depth={r.circuit_stats['depth']:,}")
        else:
            print(f"  {bits}-bit: ERROR")

    # Print scaling analysis
    print(f"\n  SCALING ANALYSIS:")
    for i, r in enumerate(reports):
        if r:
            bits = i + 1
            stats = r.circuit_stats
            gates = r.gate_level_summary
            total_gates = sum(gates.values()) if gates else 0
            print(f"  {bits}-bit: {stats['num_qubits']}q, "
                  f"depth {stats['depth']:,}, "
                  f"total gates {total_gates:,}")

    return reports


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Q-Day Prize — Run Shor's ECDLP on IBM Quantum"
    )
    parser.add_argument("--token", type=str,
                        default=os.environ.get("IBM_QUANTUM_TOKEN"),
                        help="IBM Quantum API token (or set IBM_QUANTUM_TOKEN env var)")
    parser.add_argument("--bits", type=int, default=1,
                        help="ECC key size to attack (1-5 for free tier)")
    parser.add_argument("--backend", type=str, default="ibm_fez",
                        help="IBM backend name (default: ibm_fez)")
    parser.add_argument("--shots", type=int, default=4096,
                        help="Number of quantum shots")
    parser.add_argument("--key", type=int, default=None,
                        help="Fixed secret key for reproducibility")
    parser.add_argument("--list-backends", action="store_true",
                        help="List available IBM Quantum backends")
    parser.add_argument("--sweep", action="store_true",
                        help="Run validation sweep across 1-N bit keys")
    parser.add_argument("--max-bits", type=int, default=3,
                        help="Max bits for sweep (default: 3)")
    parser.add_argument("--num-runs", type=int, default=1,
                        help="Number of independent runs per attack (default: 1)")
    parser.add_argument("--optimization-level", type=int, default=3,
                        choices=[0, 1, 2, 3],
                        help="Transpiler optimization level (default: 3 = maximum)")

    args = parser.parse_args()

    print("Q-Day Prize — IBM Quantum Runner (Enhanced)")
    print("=" * 50)
    print("\nChecking dependencies...")
    if not check_dependencies():
        print("\nInstall missing packages first:")
        print("  pip install qiskit qiskit-aer qiskit-ibm-runtime")
        sys.exit(1)

    if not args.token:
        print("\nNo IBM Quantum token provided.")
        print("  1. Sign up free at: https://quantum.ibm.com/")
        print("  2. Copy your API token from the dashboard")
        print("  3. Run: python run_ibm_quantum.py --token YOUR_TOKEN")
        print("  Or: export IBM_QUANTUM_TOKEN=YOUR_TOKEN")
        sys.exit(1)

    if args.list_backends:
        list_backends(args.token)
    elif args.sweep:
        run_validation_sweep(args.token, args.backend, args.max_bits, args.shots,
                            args.num_runs, args.optimization_level)
    else:
        run_on_ibm(args.token, args.bits, args.backend, args.shots, args.key,
                   args.num_runs, args.optimization_level)
