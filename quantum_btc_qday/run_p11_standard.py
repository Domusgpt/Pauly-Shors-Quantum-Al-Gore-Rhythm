#!/usr/bin/env python3
"""
Run Shor's ECDLP against the Project Eleven OFFICIAL standard curves.

These are the REQUIRED curves for Q-Day Prize qualification.
All curves use y² = x³ + 7 (a=0, b=7), same as Bitcoin secp256k1.
Keys from https://www.qdayprize.com/curves.json (seed=536).

Usage:
    # Simulator (no token needed)
    python quantum_btc_qday/run_p11_standard.py --bits 4

    # All standard curves on simulator
    python quantum_btc_qday/run_p11_standard.py --sweep --max-bits 8

    # IBM Quantum hardware
    python quantum_btc_qday/run_p11_standard.py --bits 4 --ibm --token YOUR_TOKEN
"""

import sys
import os
import json
import time
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ecc_curves import (
    EllipticCurve, ECPoint,
    P11_CURVES, P11_STANDARD_KEYS,
)


def verify_standard_key(bits: int) -> bool:
    """Verify that a P11 standard key is correctly defined."""
    if bits not in P11_CURVES or bits not in P11_STANDARD_KEYS:
        print(f"  No standard curve/key for {bits}-bit")
        return False

    curve = P11_CURVES[bits]
    key_data = P11_STANDARD_KEYS[bits]
    G = ECPoint(key_data["G"][0], key_data["G"][1])
    d = key_data["d"]
    Q_expected = ECPoint(key_data["Q"][0], key_data["Q"][1])

    # Verify G is on the curve: y² = x³ + ax + b mod p
    lhs = (G.y * G.y) % curve.p
    rhs = (G.x * G.x * G.x + curve.a * G.x + curve.b) % curve.p
    if lhs != rhs:
        print(f"  ERROR: Generator G={G} is NOT on curve for {bits}-bit")
        return False

    # Verify Q = d*G
    Q_computed = curve.scalar_mult(d, G)
    if Q_computed != Q_expected:
        print(f"  ERROR: d*G = {Q_computed} != Q = {Q_expected}")
        return False

    print(f"  {bits}-bit: G={G} on curve, Q=d*G verified (d={d})")
    return True


def attack_standard_key_classical(bits: int) -> dict:
    """Classically brute-force the standard key (for verification)."""
    curve = P11_CURVES[bits]
    key_data = P11_STANDARD_KEYS[bits]
    G = ECPoint(key_data["G"][0], key_data["G"][1])
    Q = ECPoint(key_data["Q"][0], key_data["Q"][1])
    n = key_data["n"]
    d_expected = key_data["d"]

    t0 = time.time()
    # Brute force: try all k from 1 to n-1
    for k in range(1, n):
        kG = curve.scalar_mult(k, G)
        if kG == Q:
            elapsed = time.time() - t0
            verified = (k == d_expected)
            return {
                "bits": bits,
                "recovered_key": k,
                "expected_key": d_expected,
                "verified": verified,
                "method": "classical_brute_force",
                "time": elapsed,
                "curve": f"y²=x³+7 over GF({curve.p})",
                "group_order": n,
            }

    return {"bits": bits, "recovered_key": None, "verified": False}


def attack_standard_key_shor_simulator(bits: int, shots: int = 4096) -> dict:
    """Run Shor's ECDLP on the standard key using Qiskit simulator."""
    try:
        from shor_ecdlp import ShorECDLP
        from attack_pipeline import ECDLPAttackPipeline
    except ImportError:
        try:
            from quantum_btc_qday.shor_ecdlp import ShorECDLP
            from quantum_btc_qday.attack_pipeline import ECDLPAttackPipeline
        except ImportError:
            print("  Qiskit not available. Use --classical for brute-force verification.")
            return {"bits": bits, "error": "qiskit not installed"}

    curve = P11_CURVES[bits]
    key_data = P11_STANDARD_KEYS[bits]
    G = ECPoint(key_data["G"][0], key_data["G"][1])
    Q = ECPoint(key_data["Q"][0], key_data["Q"][1])
    n = key_data["n"]
    d_expected = key_data["d"]

    print(f"  Building Shor's ECDLP circuit for P11 {bits}-bit standard key...")
    print(f"  Curve: y²=x³+7 over GF({curve.p}), order={n}")
    print(f"  Target: recover d={d_expected} from Q={Q}")

    pipeline = ECDLPAttackPipeline(
        curve=curve,
        target_bits=bits,
        backend_type="simulator",
        shots=shots,
    )

    t0 = time.time()
    result = pipeline.run_attack(generator=G, public_key=Q)
    elapsed = time.time() - t0

    out = {
        "timestamp": datetime.utcnow().isoformat(),
        "competition": "Project Eleven Q-Day Prize",
        "standard_curve": True,
        "bits": bits,
        "curve": f"y²=x³+7 over GF({curve.p})",
        "curve_params": {"a": 0, "b": 7, "p": curve.p},
        "group_order": n,
        "generator": str(G),
        "public_key": str(Q),
        "expected_key": d_expected,
        "recovered_key": result.get("recovered_key"),
        "verified": result.get("verified", False),
        "method": "shor_ecdlp_simulator",
        "shots": shots,
        "execution_time": elapsed,
    }

    if result.get("circuit_stats"):
        out["circuit_stats"] = result["circuit_stats"]

    return out


def main():
    parser = argparse.ArgumentParser(
        description="Run Shor's ECDLP against Project Eleven standard curves"
    )
    parser.add_argument("--bits", type=int, default=4,
                        help="Bit level to attack (4,6,7,8,9,10,11,12)")
    parser.add_argument("--sweep", action="store_true",
                        help="Attack all standard curves up to --max-bits")
    parser.add_argument("--max-bits", type=int, default=8,
                        help="Maximum bit level for sweep")
    parser.add_argument("--classical", action="store_true",
                        help="Use classical brute-force (no Qiskit needed)")
    parser.add_argument("--verify-only", action="store_true",
                        help="Only verify keys are correct, don't attack")
    parser.add_argument("--shots", type=int, default=4096)
    parser.add_argument("--ibm", action="store_true",
                        help="Run on IBM Quantum hardware")
    parser.add_argument("--token", type=str, default=None,
                        help="IBM Quantum token")
    parser.add_argument("--output-dir", type=str,
                        default="quantum_btc_qday/results/p11_standard",
                        help="Output directory for results")
    args = parser.parse_args()

    print("=" * 70)
    print("PROJECT ELEVEN Q-DAY PRIZE — STANDARD CURVE ATTACK")
    print("All curves: y² = x³ + 7 (same as Bitcoin secp256k1)")
    print("=" * 70)

    # First verify all keys
    print("\nVerifying standard keys...")
    available_bits = sorted(P11_STANDARD_KEYS.keys())
    for b in available_bits:
        verify_standard_key(b)

    if args.verify_only:
        print("\nAll standard keys verified.")
        return

    # Determine which bits to attack
    if args.sweep:
        target_bits = [b for b in available_bits if b <= args.max_bits]
    else:
        target_bits = [args.bits]

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Run attacks
    results = []
    for bits in target_bits:
        print(f"\n{'='*50}")
        print(f"ATTACKING {bits}-BIT STANDARD KEY")
        print(f"{'='*50}")

        if args.classical:
            result = attack_standard_key_classical(bits)
        else:
            result = attack_standard_key_shor_simulator(bits, args.shots)

        results.append(result)

        # Save result
        out_file = os.path.join(
            args.output_dir,
            f"p11_attack_{bits}bit_{'classical' if args.classical else 'shor'}.json"
        )
        with open(out_file, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"  Result saved to {out_file}")

        if result.get("verified"):
            print(f"  KEY RECOVERED: d = {result['recovered_key']}")
        else:
            print(f"  Attack result: {result.get('recovered_key', 'FAILED')}")

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    for r in results:
        status = "VERIFIED" if r.get("verified") else "FAILED"
        print(f"  {r['bits']}-bit: {status} "
              f"(key={r.get('recovered_key', '?')}, "
              f"method={r.get('method', '?')})")


if __name__ == "__main__":
    main()
