#!/usr/bin/env python3
"""
Run Shor's ECDLP against Project Eleven OFFICIAL standard curves.

Uses the EXACT same attack pipeline that produced 11 verified IBM
hardware runs — just pointed at P11's standard curves (y²=x³+7)
instead of our development curves.

Usage:
    # Single attack on 4-bit P11 standard key (simulator)
    python run_p11_shor.py --bits 4 --shots 4096

    # Campaign: attack all feasible P11 standard keys
    python run_p11_shor.py --campaign --max-bits 8

    # Export QASM circuit for 4-bit P11 key
    python run_p11_shor.py --bits 4 --export-qasm p11_circuit_4bit.qasm

    # IBM Quantum hardware
    python run_p11_shor.py --bits 4 --backend ibm --token YOUR_TOKEN
"""

import sys
import os

# Patch QDAY_CURVES to use P11 official curves BEFORE importing the pipeline
from quantum_btc_qday.ecc_curves import (
    P11_CURVES, P11_STANDARD_KEYS, ECPoint,
    QDAY_CURVES,
)

# Replace development curves with P11 official curves
for bits, curve in P11_CURVES.items():
    QDAY_CURVES[bits] = curve

# Now import the attack pipeline — it will use P11 curves via get_curve()
from quantum_btc_qday.attack_pipeline import QDayAttackPipeline, AttackReport
from quantum_btc_qday.shor_ecdlp import ShorECDLP

import argparse
import json
import time
from datetime import datetime


def run_p11_attack(bits, shots=4096, backend_type="simulator",
                   token=None, export_qasm=None, export_gates=None,
                   output_dir="quantum_btc_qday/results/p11_standard"):
    """Run Shor's ECDLP on a P11 standard key using the proven pipeline."""

    if bits not in P11_STANDARD_KEYS:
        print(f"No P11 standard key for {bits}-bit. Available: {sorted(P11_STANDARD_KEYS.keys())}")
        return None

    kd = P11_STANDARD_KEYS[bits]
    curve = P11_CURVES[bits]
    d_expected = kd["d"]

    print(f"\n{'='*60}")
    print(f"  P11 STANDARD {bits}-BIT KEY ATTACK (Shor's ECDLP)")
    print(f"  Curve: y²=x³+7 over GF({curve.p}) [same form as secp256k1]")
    print(f"  Group order: {kd['n']}")
    print(f"  Target public key: Q = {kd['Q']}")
    print(f"  Backend: {backend_type}")
    print(f"{'='*60}\n")

    # Use the exact same pipeline that did our IBM runs
    pipeline = QDayAttackPipeline(
        target_bits=bits,
        backend_type=backend_type,
    )

    # Setup backend
    if backend_type == "ibm" and token:
        pipeline.setup_backend(token=token)
    elif backend_type == "simulator":
        pipeline.setup_backend()

    # Set the P11 standard key (known secret for verification)
    pipeline.generate_target(secret_key=d_expected)

    # Override generator and public key with P11 official values
    pipeline.generator = ECPoint(kd["G"][0], kd["G"][1])
    pipeline.public_key = ECPoint(kd["Q"][0], kd["Q"][1])
    pipeline.secret_key = d_expected
    pipeline.group_order = kd["n"]

    # Export if requested
    if export_qasm:
        print(f"Exporting QASM to {export_qasm}...")
        pipeline.export_qasm(export_qasm)
        print(f"QASM exported.")
        if not export_gates:
            return None

    if export_gates:
        print(f"Exporting gate-level to {export_gates}...")
        pipeline.export_gate_level(export_gates)
        print(f"Gates exported.")
        return None

    # Run the attack
    report = pipeline.run_attack(shots=shots)

    # Enhanced output with P11 metadata
    print(f"\n{'='*60}")
    print(f"  RESULT: {bits}-BIT P11 STANDARD KEY")
    print(f"{'='*60}")
    if report.verified:
        print(f"  STATUS: KEY RECOVERED")
        print(f"  Recovered key:  k = {report.recovered_key}")
        print(f"  Expected key:   d = {d_expected}")
        print(f"  Match: {'YES' if report.recovered_key == d_expected else 'NO'}")
    else:
        print(f"  STATUS: KEY NOT RECOVERED")
    print(f"  Qubits: {report.circuit_stats['num_qubits']}")
    print(f"  Depth:  {report.circuit_stats['depth']}")
    print(f"  Time:   {report.execution_time_seconds:.2f}s")
    print(f"  Gates:  {report.gate_level_summary}")

    # Save
    os.makedirs(output_dir, exist_ok=True)
    fname = os.path.join(output_dir,
        f"p11_shor_{bits}bit_{backend_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json")
    report.save(fname)
    print(f"  Saved:  {fname}")

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Shor's ECDLP on Project Eleven Q-Day Prize standard curves",
    )
    parser.add_argument("--bits", type=int, default=4,
                        help="Bit level (4,6,7,8,9,10,11,12)")
    parser.add_argument("--shots", type=int, default=4096)
    parser.add_argument("--backend", choices=["simulator", "ibm"], default="simulator")
    parser.add_argument("--token", type=str, help="IBM Quantum token")
    parser.add_argument("--campaign", action="store_true",
                        help="Attack all feasible standard keys")
    parser.add_argument("--max-bits", type=int, default=8)
    parser.add_argument("--export-qasm", type=str)
    parser.add_argument("--export-gates", type=str)
    parser.add_argument("--output-dir", type=str,
                        default="quantum_btc_qday/results/p11_standard")
    args = parser.parse_args()

    print("=" * 60)
    print("  PROJECT ELEVEN Q-DAY PRIZE SUBMISSION")
    print("  Shor's Algorithm for ECDLP")
    print("  Official standard curves: y² = x³ + 7")
    print("  https://www.qdayprize.com/")
    print("=" * 60)

    if args.campaign:
        available = sorted(P11_STANDARD_KEYS.keys())
        targets = [b for b in available if b <= args.max_bits]
        print(f"\nCampaign: attacking {len(targets)} standard keys: {targets}")

        results = []
        for bits in targets:
            r = run_p11_attack(
                bits, args.shots, args.backend, args.token,
                output_dir=args.output_dir
            )
            results.append((bits, r))

        print(f"\n{'='*60}")
        print(f"  CAMPAIGN SUMMARY")
        print(f"{'='*60}")
        for bits, r in results:
            if r and r.verified:
                print(f"  {bits}-bit: CRACKED (k={r.recovered_key}, "
                      f"depth={r.circuit_stats['depth']}, "
                      f"time={r.execution_time_seconds:.1f}s)")
            else:
                print(f"  {bits}-bit: FAILED")
    else:
        run_p11_attack(
            args.bits, args.shots, args.backend, args.token,
            args.export_qasm, args.export_gates, args.output_dir
        )


if __name__ == "__main__":
    main()
