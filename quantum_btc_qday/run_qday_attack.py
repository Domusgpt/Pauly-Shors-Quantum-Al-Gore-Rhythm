#!/usr/bin/env python3
"""
Q-Day Prize Attack Runner

Usage:
    # Run on simulator (default, 1-5 bit keys):
    python -m quantum_btc_qday.run_qday_attack

    # Attack specific bit level:
    python -m quantum_btc_qday.run_qday_attack --bits 3

    # Run on IBM Quantum hardware:
    python -m quantum_btc_qday.run_qday_attack --bits 1 --backend ibm --token YOUR_TOKEN

    # Run full campaign (1-5 bits):
    python -m quantum_btc_qday.run_qday_attack --campaign --max-bits 5

    # Export circuit for submission:
    python -m quantum_btc_qday.run_qday_attack --bits 3 --export-qasm circuit.qasm
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quantum_btc_qday.attack_pipeline import QDayAttackPipeline, run_qday_campaign
from quantum_btc_qday.shor_ecdlp import attack_ecc_key
from quantum_btc_qday.ecc_curves import get_curve


def main():
    parser = argparse.ArgumentParser(
        description="Q-Day Prize: Shor's Algorithm Attack on ECC Keys",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --bits 1                    # Attack 1-bit key on simulator
  %(prog)s --bits 3 --shots 4096       # Attack 3-bit key with more shots
  %(prog)s --campaign --max-bits 5     # Run attacks from 1 to 5 bits
  %(prog)s --bits 2 --backend ibm      # Run on IBM Quantum
  %(prog)s --bits 3 --export-qasm out  # Export circuit as QASM
        """
    )

    parser.add_argument('--bits', type=int, default=1,
                       help='ECC key size in bits (1-25, default: 1)')
    parser.add_argument('--shots', type=int, default=2048,
                       help='Number of quantum shots (default: 2048)')
    parser.add_argument('--backend', choices=['simulator', 'ibm', 'aws'],
                       default='simulator', help='Quantum backend')
    parser.add_argument('--token', type=str, help='IBM Quantum API token')
    parser.add_argument('--device', type=str, help='Specific device name/ARN')
    parser.add_argument('--secret-key', type=int,
                       help='Use specific secret key (for testing)')
    parser.add_argument('--campaign', action='store_true',
                       help='Run attack campaign across multiple bit levels')
    parser.add_argument('--max-bits', type=int, default=5,
                       help='Maximum bits for campaign (default: 5)')
    parser.add_argument('--export-qasm', type=str,
                       help='Export circuit as OpenQASM file')
    parser.add_argument('--export-gates', type=str,
                       help='Export gate-level description as JSON')
    parser.add_argument('--output-dir', type=str, default='qday_results',
                       help='Output directory for results')
    parser.add_argument('--curve-info', action='store_true',
                       help='Print curve information and exit')

    args = parser.parse_args()

    print("=" * 60)
    print("  Project Eleven Q-Day Prize")
    print("  Shor's Algorithm for ECDLP")
    print("  https://www.qdayprize.com/")
    print("=" * 60)
    print()

    if args.curve_info:
        print_curve_info(args.bits)
        return

    if args.campaign:
        reports = run_qday_campaign(
            max_bits=args.max_bits,
            shots=args.shots,
            output_dir=args.output_dir
        )
        successes = sum(1 for r in reports if r.verified)
        print(f"\nCampaign complete: {successes}/{len(reports)} keys broken")
        return

    # Single attack
    pipeline = QDayAttackPipeline(
        target_bits=args.bits,
        backend_type=args.backend
    )

    # Setup backend
    backend_kwargs = {}
    if args.token:
        backend_kwargs['token'] = args.token
    if args.device:
        backend_kwargs['backend_name' if args.backend == 'ibm' else 'device_arn'] = args.device
    pipeline.setup_backend(**backend_kwargs)

    # Generate target
    pipeline.generate_target(secret_key=args.secret_key)

    print(f"Target: {args.bits}-bit ECC key")
    print(f"Curve: y^2 = x^3 + {pipeline.curve.a}x + {pipeline.curve.b} over GF({pipeline.curve.p})")
    print(f"Generator P = {pipeline.generator}")
    print(f"Public Key Q = {pipeline.public_key}")
    print(f"Group Order = {pipeline.group_order}")
    print(f"Backend: {args.backend}")
    print()

    # Export if requested
    if args.export_qasm:
        pipeline.export_qasm(args.export_qasm)
        if not args.export_gates:
            return

    if args.export_gates:
        pipeline.export_gate_level(args.export_gates)
        return

    # Run attack
    report = pipeline.run_attack(shots=args.shots)

    # Print results
    print()
    print("=" * 60)
    print("  RESULTS")
    print("=" * 60)
    if report.verified:
        print(f"  STATUS: KEY RECOVERED")
        print(f"  Secret key k = {report.recovered_key}")
    else:
        print(f"  STATUS: KEY NOT RECOVERED")

    print(f"  Qubits used: {report.circuit_stats['num_qubits']}")
    print(f"  Circuit depth: {report.circuit_stats['depth']}")
    print(f"  Measurements: {report.num_measurements}")
    print(f"  Time: {report.execution_time_seconds:.2f}s")
    print(f"  Gates: {report.gate_level_summary}")
    print()

    # Save report
    os.makedirs(args.output_dir, exist_ok=True)
    report_path = os.path.join(args.output_dir, f"attack_{args.bits}bit.json")
    report.save(report_path)
    print(f"Report saved to {report_path}")


def print_curve_info(bits: int):
    """Print detailed curve information."""
    curve = get_curve(bits)
    G = curve.find_generator()
    n = curve.point_order(G)
    points = curve.enumerate_points()

    print(f"Curve for {bits}-bit security:")
    print(f"  E: y^2 = x^3 + {curve.a}x + {curve.b} over GF({curve.p})")
    print(f"  #E(GF({curve.p})) = {len(points)}")
    print(f"  Generator P = {G}")
    print(f"  ord(P) = {n}")
    print(f"  Security bits: {curve.security_bits()}")
    print(f"  All points ({len(points)}):")
    for p in points:
        print(f"    {p}")


if __name__ == '__main__':
    main()
