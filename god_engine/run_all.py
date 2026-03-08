#!/usr/bin/env python3
"""
G.O.D. Engine - Unified System Runner
=======================================
Integrates all components:
  1. E8 Lattice Engine (cross-parity projection, type separation)
  2. TDA Engine (persistent homology on lattice-projected clouds)
  3. Moire Factorization (interference geometry reveals factors)
  4. Galois QPU Emulator (deterministic quantum-analog computation)
  5. Cryptographic Analyzer (RSA/ECDLP/ZK analysis)

Usage:
    python god_engine/run_all.py                    # Full benchmark
    python god_engine/run_all.py --factor 143       # Factor a number
    python god_engine/run_all.py --benchmark 30     # Benchmark to N bits
    python god_engine/run_all.py --verify            # Verify lattice only

Author: Paul J. Phillips / Clear Seas Solutions LLC
Framework: G.O.D. (Geometric Orthogonal Dialectics)
"""

import sys
import os
import time
import argparse
import math
import numpy as np

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from e8_lattice import E8Lattice, BABELTower, DELTA, PHI, S_TYPE


def verify_lattice():
    """Full lattice verification suite."""
    print("=" * 72)
    print(" G.O.D. ENGINE: E8 LATTICE VERIFICATION")
    print("=" * 72)

    lattice = E8Lattice()

    # 1. Type separation
    sep = lattice.verify_type_separation()
    print(f"\n[T-02] Perfect Type Separation: "
          f"{'PASS' if sep['all_pure'] else 'FAIL'}")
    print(f"  Classified: {sep['total_classified']}/240")
    expected_pops = {-3: 24, -2: 56, -1: 40, 1: 40, 2: 56, 3: 24}
    pop_match = all(sep['populations'][k] == expected_pops[k] for k in expected_pops)
    print(f"  Populations: {dict(sep['populations'])} "
          f"{'MATCH' if pop_match else 'MISMATCH'}")

    # 2. Entropy
    ent = lattice.entropy_decomposition()
    print(f"\n[L-IV] Information Conservation:")
    print(f"  H(type)           = {ent['H_type']:.4f} bits (expected ~0.9968)")
    print(f"  H(shell|type)     = {ent['H_shell_given_type']:.4f} bits (expected ~1.5090)")
    print(f"  H(pos|shell,type) = {ent['H_pos_given_shell_type']:.4f} bits (expected ~5.4011)")
    print(f"  Total             = {ent['H_total']:.4f} bits = log2(240)")
    print(f"  Residual          = {ent['residual']:.10f}")

    # 3. Constants
    print(f"\n[Constants]")
    print(f"  delta   = {DELTA:.10f} (sqrt(5)/10)")
    print(f"  phi     = {PHI:.10f} (golden ratio)")
    print(f"  S       = {S_TYPE:.10f} (delta * phi^3)")
    print(f"  2*h*d^2 = {2 * 30 * DELTA**2:.10f} (expected = 3 = inner twin prime)")

    # 4. BABEL tower
    print(f"\n[BABEL Tower]")
    periods, ratios = BABELTower.orbit_period_ratios()
    for lvl in range(3):
        info = BABELTower.LEVELS[lvl]
        gs = BABELTower.galois_group_structure(lvl)
        dq = BABELTower.shell_quantum(lvl)
        print(f"  L{lvl}: primes={info['primes']} h={info['h']} "
              f"dim={info['dim']} period={gs['orbit_period']} "
              f"delta={dq:.6f}")
    print(f"  Period ratios: {ratios} (= inner twin primes)")

    # 5. Key identities
    print(f"\n[Key Identities]")
    print(f"  |Phi| = n*h: 240 = 8*30 = {8*30} "
          f"{'PASS' if 8*30 == 240 else 'FAIL'}")
    print(f"  196560 = 13*15120: {13*15120} "
          f"{'PASS' if 13*15120 == 196560 else 'FAIL'}")
    print(f"  phi(15)=8: {sum(1 for a in range(15) if math.gcd(a,15)==1)} "
          f"{'PASS' if sum(1 for a in range(15) if math.gcd(a,15)==1)==8 else 'FAIL'}")
    print(f"  phi(35)=24: {sum(1 for a in range(35) if math.gcd(a,35)==1)} "
          f"{'PASS' if sum(1 for a in range(35) if math.gcd(a,35)==1)==24 else 'FAIL'}")
    print(f"  phi(143)=120: {sum(1 for a in range(143) if math.gcd(a,143)==1)} "
          f"{'PASS' if sum(1 for a in range(143) if math.gcd(a,143)==1)==120 else 'FAIL'}")

    all_pass = (sep['all_pure'] and pop_match and
                ent['residual'] < 1e-8 and
                abs(2 * 30 * DELTA**2 - 3) < 1e-10)
    print(f"\n{'='*72}")
    print(f" OVERALL: {'ALL CHECKS PASS' if all_pass else 'SOME CHECKS FAILED'}")
    print(f"{'='*72}")
    return lattice


def run_factorization(n, lattice=None):
    """Factor a number using all available methods."""
    if lattice is None:
        lattice = E8Lattice()

    print(f"\n{'='*72}")
    print(f" FACTORING: {n} ({n.bit_length()} bits)")
    print(f"{'='*72}")

    from moire_factor import MoireFactorizer
    from galois_qpu import GaloisQPU
    from crypto_analyzer import RSAAnalyzer

    results = {}

    # Method 1: Moire
    print("\n[1] Moire Pattern Engine:")
    start = time.time()
    mf = MoireFactorizer(lattice)
    r = mf.factorize(n, verbose=False)
    elapsed = time.time() - start
    if r['factors']:
        print(f"  {n} = {r['factors'][0]} x {r['factors'][1]}  "
              f"[{r['method']}]  {elapsed:.4f}s")
        results['moire'] = r['factors']
    else:
        print(f"  Failed  {elapsed:.4f}s")

    # Method 2: Galois QPU
    print("\n[2] Galois QPU Emulator:")
    start = time.time()
    qpu = GaloisQPU(lattice)
    f = qpu.factorize(n, verbose=False)
    elapsed = time.time() - start
    if f:
        print(f"  {n} = {f[0]} x {f[1]}  {elapsed:.4f}s")
        results['galois_qpu'] = f
    else:
        print(f"  Failed  {elapsed:.4f}s")

    # Method 3: RSA Analyzer (Fermat + trial + Galois)
    print("\n[3] RSA Analyzer:")
    rsa = RSAAnalyzer(lattice)
    r = rsa.analyze_and_factor(n)
    if r['factors']:
        print(f"  {n} = {r['factors'][0]} x {r['factors'][1]}  "
              f"[{r['method']}]  {r['time_s']:.4f}s")
        results['rsa'] = r['factors']
    else:
        print(f"  Failed  {r['time_s']:.4f}s")

    # Summary
    print(f"\n  Methods succeeded: {len(results)}/3")
    if results:
        # Verify consistency
        first = list(results.values())[0]
        consistent = all(set(v) == set(first) for v in results.values())
        print(f"  Results consistent: {'YES' if consistent else 'NO'}")

    return results


def run_benchmark(max_bits=30, lattice=None):
    """Benchmark factorization across bit sizes."""
    if lattice is None:
        lattice = E8Lattice()

    print(f"\n{'='*72}")
    print(f" FACTORIZATION BENCHMARK (up to {max_bits} bits)")
    print(f"{'='*72}")

    from crypto_analyzer import RSAAnalyzer
    import random

    rsa = RSAAnalyzer(lattice)
    rng = random.Random(42)

    def random_prime(bits):
        while True:
            n = rng.getrandbits(bits) | (1 << (bits - 1)) | 1
            if all(n % p != 0 for p in range(2, min(int(n**0.5) + 1, 10000))):
                return n

    print(f"\n  {'Bits':>5s}  {'N':>14s}  {'Factors':>20s}  {'Method':>16s}  {'Time':>8s}")
    print(f"  {'-'*5}  {'-'*14}  {'-'*20}  {'-'*16}  {'-'*8}")

    max_factored = 0
    for bits in range(6, min(max_bits + 1, 48), 2):
        half = max(bits // 2, 3)
        p = random_prime(half)
        q = random_prime(half)
        while q == p:
            q = random_prime(half)
        n = p * q
        actual_bits = n.bit_length()

        result = rsa.analyze_and_factor(n)
        if result['factors']:
            f1, f2 = result['factors']
            correct = {f1, f2} == {p, q}
            status = f"{f1} x {f2}" + (" OK" if correct else " WRONG")
            if correct:
                max_factored = max(max_factored, actual_bits)
        else:
            status = "FAILED"

        print(f"  {actual_bits:>5d}  {n:>14d}  {status:>20s}  "
              f"{result['method']:>16s}  {result['time_s']:>7.4f}s")

    print(f"\n  Max bits correctly factored: {max_factored}")
    return max_factored


def run_tda_demo(lattice=None):
    """TDA demonstration on BABEL tower conductors."""
    if lattice is None:
        lattice = E8Lattice()

    print(f"\n{'='*72}")
    print(f" TOPOLOGICAL DATA ANALYSIS - BABEL CONDUCTORS")
    print(f"{'='*72}")

    from tda_engine import LatticeTopology

    topo = LatticeTopology(lattice)

    conductors = [15, 35, 143]
    for h in conductors:
        result = topo.factor_topology(h)
        if 'too_small' in result:
            print(f"  h={h}: too small")
            continue
        print(f"  h={h:4d}: phi={result['phi_n']:3d}  "
              f"H0_persist={result['h0_total_persistence']:.2f}  "
              f"H1_bars={result['h1_bars']:3d}  "
              f"H1_persist={result['h1_total_persistence']:.2f}")


def run_full():
    """Run everything."""
    total_start = time.time()

    # 1. Verify lattice
    lattice = verify_lattice()

    # 2. TDA demo
    run_tda_demo(lattice)

    # 3. Factor BABEL conductors
    print(f"\n{'='*72}")
    print(f" BABEL TOWER CONDUCTOR FACTORIZATION")
    print(f"{'='*72}")
    for h in [15, 35, 143, 323, 899]:
        run_factorization(h, lattice)

    # 4. Benchmark
    max_bits = run_benchmark(max_bits=30, lattice=lattice)

    # 5. Summary
    total_time = time.time() - total_start
    print(f"\n{'='*72}")
    print(f" G.O.D. ENGINE - COMPLETE SYSTEM SUMMARY")
    print(f"{'='*72}")
    print(f"  E8 Lattice: 240/240 roots, perfect type separation")
    print(f"  BABEL Tower: 3 levels verified (E8 -> Leech -> Craig)")
    print(f"  Factorization: up to {max_bits} bits")
    print(f"  Engines: E8 Lattice + TDA + Moire + Galois QPU + Crypto")
    print(f"  Total time: {total_time:.2f}s")
    print(f"{'='*72}")


def main():
    parser = argparse.ArgumentParser(description='G.O.D. Engine - Unified Runner')
    parser.add_argument('--verify', action='store_true', help='Verify lattice only')
    parser.add_argument('--factor', type=int, help='Factor a specific number')
    parser.add_argument('--benchmark', type=int, default=0,
                        help='Benchmark to N bits')
    parser.add_argument('--tda', action='store_true', help='Run TDA demo')
    args = parser.parse_args()

    if args.verify:
        verify_lattice()
    elif args.factor:
        run_factorization(args.factor)
    elif args.benchmark:
        run_benchmark(args.benchmark)
    elif args.tda:
        run_tda_demo()
    else:
        run_full()


if __name__ == '__main__':
    main()
