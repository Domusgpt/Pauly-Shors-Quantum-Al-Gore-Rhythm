#!/usr/bin/env python3
"""
Q-Day Prize — IBM Quantum Free Tier Runner
============================================

Run Shor's ECDLP attack on IBM Quantum hardware (free tier).

Setup:
    1. Create free account at https://quantum.ibm.com/
    2. Copy your API token from the dashboard
    3. Run:  pip install qiskit-ibm-runtime
    4. Run:  python run_ibm_quantum.py --token YOUR_TOKEN_HERE

Free tier gives you access to 127-qubit Eagle processors (ibm_brisbane, etc.)
with up to 10 minutes of quantum compute per month.

For the Q-Day Prize competition, we need to demonstrate Shor's ECDLP
on real quantum hardware. Even small bit sizes (1-5 bit keys) on real
hardware are meaningful for the submission.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

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


def run_on_ibm(token: str, bits: int = 1, backend_name: str = "ibm_brisbane",
               shots: int = 4096, secret_key: int = None):
    """
    Run Q-Day attack on IBM Quantum hardware.

    Args:
        token: IBM Quantum API token
        bits: Key size to attack (1-5 recommended for free tier)
        backend_name: IBM backend name
        shots: Number of shots (max 100000 on free tier)
        secret_key: Optional fixed secret key for reproducibility
    """
    from quantum_btc_qday.attack_pipeline import QDayAttackPipeline

    print(f"\n{'='*60}")
    print(f"  Q-Day Prize — IBM Quantum Attack")
    print(f"  Target: {bits}-bit ECC key on {backend_name}")
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

    # Run attack
    print("[*] Submitting circuit to IBM Quantum...")
    print("    (This may take a few minutes depending on queue)")
    report = pipeline.run_attack(shots=shots)

    # Results
    print(f"\n{'='*60}")
    if report.verified:
        print(f"  KEY RECOVERED: k = {report.recovered_key}")
        print(f"  VERIFIED: Q == {report.recovered_key} * P")
    else:
        print(f"  Attack did not recover key (may need more shots or iterations)")
    print(f"  Qubits: {report.circuit_stats['num_qubits']}")
    print(f"  Depth: {report.circuit_stats['depth']}")
    print(f"  Time: {report.execution_time_seconds:.2f}s")
    print(f"{'='*60}\n")

    # Save results
    os.makedirs("qday_results/ibm", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_path = f"qday_results/ibm/attack_{bits}bit_{backend_name}_{timestamp}.json"
    report.save(result_path)
    print(f"  Report saved: {result_path}")

    # Export gate-level for submission
    gate_path = f"qday_results/ibm/gates_{bits}bit_{backend_name}_{timestamp}.json"
    pipeline.export_gate_level(gate_path)

    return report


def run_validation_sweep(token: str, backend_name: str = "ibm_brisbane",
                         max_bits: int = 3, shots: int = 4096):
    """
    Run validation sweep across 1-N bit keys on IBM Quantum.

    This generates the submission evidence for the Q-Day Prize.
    """
    print(f"\n{'='*60}")
    print(f"  Q-Day Validation Sweep: 1-{max_bits} bit keys")
    print(f"  Backend: {backend_name}")
    print(f"{'='*60}\n")

    reports = []
    for bits in range(1, max_bits + 1):
        print(f"\n--- {bits}-bit attack ---")
        try:
            report = run_on_ibm(
                token=token,
                bits=bits,
                backend_name=backend_name,
                shots=shots
            )
            reports.append(report)
            status = "BROKEN" if report.verified else "FAILED"
            print(f"  Result: {status}")
        except Exception as e:
            print(f"  Error: {e}")
            reports.append(None)

    # Summary
    print(f"\n{'='*60}")
    print(f"  VALIDATION SWEEP SUMMARY")
    print(f"{'='*60}")
    for i, r in enumerate(reports):
        bits = i + 1
        if r and r.verified:
            print(f"  {bits}-bit: BROKEN | k={r.recovered_key} | "
                  f"{r.circuit_stats['num_qubits']}q | "
                  f"{r.execution_time_seconds:.1f}s")
        elif r:
            print(f"  {bits}-bit: FAILED | {r.circuit_stats['num_qubits']}q")
        else:
            print(f"  {bits}-bit: ERROR")

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
    parser.add_argument("--backend", type=str, default="ibm_brisbane",
                        help="IBM backend name (default: ibm_brisbane)")
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

    args = parser.parse_args()

    print("Q-Day Prize — IBM Quantum Runner")
    print("=" * 40)
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
        run_validation_sweep(args.token, args.backend, args.max_bits, args.shots)
    else:
        run_on_ibm(args.token, args.bits, args.backend, args.shots, args.key)
