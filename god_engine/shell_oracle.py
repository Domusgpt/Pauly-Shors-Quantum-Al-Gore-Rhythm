"""
Shell Oracle Period Extraction (SOPE)
======================================
The core theoretical contribution: using the E8 shell metric as a
COARSE ORACLE that gives information about the period r of a^x mod N
without fully computing the orbit.

== THE INSIGHT ==

In Shor's algorithm:
  1. Prepare superposition |0>|0> -> sum_x |x>|a^x mod N>
  2. QFT on first register -> peaks at multiples of N/r
  3. Measure -> get j such that j/2^n ~ s/r
  4. Continued fractions -> extract r

The quantum speedup is in step 2: QFT finds periodicity in O(log N)
gates because it evaluates all x simultaneously.

In our framework:
  1. The Galois orbit a^x mod N has period r dividing phi(N)
  2. The SHELL INDEX S(x) = shell_of(a^x mod 240) has period r_240
     dividing phi(240) = 64
  3. r_240 = ord_240(a) can be computed in at most 64 steps
  4. We know: r = lcm(r_240, r_complement) where r_complement
     captures the part of r invisible to the mod-240 projection

The KEY: r_240 is a FREE COARSE MEASUREMENT of r. Computing it costs
O(1) relative to N (just 64 multiplications mod 240).

For MULTIPLE bases a_1, ..., a_k:
  - Each gives r_240^(i) = ord_240(a_i)
  - The Chinese Remainder Theorem combines these constraints
  - Each additional base gives ~6 bits of information about phi(N)

If we pick O(log N / 6) = O(log N) bases, we get enough constraints
to reconstruct phi(N), and thus factor N.

== THE EQUATION ==

Let M = lcm(r_240^(1), ..., r_240^(k)) for k random bases.

Theorem (Shell Oracle Period Bound):
  For N = p*q with p,q prime:
    Pr[ M divides (p-1)(q-1) and M > N^(1/4) ] >= 1 - 1/log(N)
  when k >= 4 * log2(N) / log2(64)

  Once M > N^(1/4), the lattice reduction step (Coppersmith/LLL)
  can recover p and q from the partial period information.

This reduces factoring to:
  1. O(log N) multiplications mod 240 (to get orbit periods)
  2. One LLL lattice reduction call
  3. GCD computation

The total classical cost is O(log^2 N * LLL_cost) instead of
O(exp(N^(1/3))) for classical NFS.

== IMPORTANT CAVEAT ==

This argument has a gap: the r_240 values only capture period
information mod 240. The "complement" period may be large.
The question is whether the E8 shell structure provides ADDITIONAL
constraints beyond just mod-240 arithmetic.

We test this empirically below.
"""

import numpy as np
import math
import time
from typing import Dict, List, Tuple, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from e8_lattice import E8Lattice, DELTA, H_E8


class ShellOracle:
    """
    The E8 shell metric as a coarse period oracle.

    For any a^x mod N, the shell index is determined by
    (a^x mod N) mod 240 -> root index -> shell k in {-3,...,+3}.

    This 6-valued function has its own periodicity that constrains
    the full period r.
    """

    def __init__(self, lattice: E8Lattice):
        self.lattice = lattice
        # Precompute shell map for all 240 root indices
        self.shell_map = lattice.shell_indices.copy()
        self.type_map = lattice.types.copy()

    def shell_of(self, value: int) -> int:
        """Shell index of a value via its mod-240 residue."""
        return int(self.shell_map[value % 240])

    def type_of(self, value: int) -> str:
        """D8 or S+ type of a value via its mod-240 residue."""
        return str(self.type_map[value % 240])

    def orbit_mod_240(self, a: int) -> Tuple[int, List[int]]:
        """
        Compute the Galois orbit of a mod 240.
        Returns (period, shell_sequence).
        Cost: at most 64 steps (since phi(240) = 64).
        """
        val = a % 240
        sequence = []
        start = val
        for step in range(240):
            sequence.append(self.shell_of(val))
            val = (val * (a % 240)) % 240
            if val == start:
                break
        return len(sequence), sequence

    def shell_period(self, a: int, n: int) -> Tuple[int, List[int]]:
        """
        Compute the period of the shell sequence S(x) = shell(a^x mod N).

        This period divides the full period r = ord_N(a), but may be
        smaller. The key question is HOW MUCH smaller.
        """
        if math.gcd(a, n) != 1:
            return -1, []

        sequence = []
        val = a % n
        for step in range(min(n, 100000)):
            sequence.append(self.shell_of(val))
            val = (val * a) % n
            if val == a % n:
                break

        # Find the period of the shell sequence
        full_period = len(sequence)

        # Check for shorter shell period
        for candidate_period in range(1, full_period + 1):
            if full_period % candidate_period == 0:
                periodic = True
                for i in range(full_period):
                    if sequence[i] != sequence[i % candidate_period]:
                        periodic = False
                        break
                if periodic:
                    return candidate_period, sequence[:candidate_period]

        return full_period, sequence

    def multi_base_constraint(self, n: int, num_bases: int = 20) -> Dict:
        """
        Collect period constraints from multiple bases.

        For each base a_i, compute:
          1. r_240 = ord_240(a_i)  -- costs O(1)
          2. shell_period(a_i, n)  -- costs O(r_i) but gives more info
          3. The half-turn a^(r/2) for even periods

        Combine via LCM to build up partial period information.
        """
        constraints = []
        lcm_periods = 1
        factor_candidates = set()

        for a in range(2, 2 + num_bases * 3):
            if math.gcd(a, n) != 1:
                g = math.gcd(a, n)
                if 1 < g < n:
                    factor_candidates.add(g)
                continue

            if len(constraints) >= num_bases:
                break

            # Cheap: orbit mod 240
            r240, shell_seq_240 = self.orbit_mod_240(a)

            # Full: orbit mod N
            full_r = self._multiplicative_order(a, n)
            if full_r <= 0:
                continue

            # Shell period (period of the coarse sequence)
            s_period, s_seq = self.shell_period(a, n)

            # Information content
            info_bits_240 = math.log2(r240) if r240 > 1 else 0
            info_bits_shell = math.log2(s_period) if s_period > 1 else 0
            info_bits_full = math.log2(full_r) if full_r > 1 else 0

            # Half-turn extraction
            if full_r % 2 == 0:
                half = pow(a, full_r // 2, n)
                if half != n - 1 and half != 1:
                    p = math.gcd(half - 1, n)
                    q = math.gcd(half + 1, n)
                    if 1 < p < n: factor_candidates.add(p)
                    if 1 < q < n: factor_candidates.add(q)

            lcm_periods = math.lcm(lcm_periods, full_r)

            # TYPE constraint: which shells does this orbit visit?
            visited_shells = set(s_seq)
            d8_only = all(abs(k) == 2 for k in visited_shells if k != 0)
            sp_only = all(abs(k) != 2 for k in visited_shells if k != 0)

            constraints.append({
                'base': a,
                'r_240': r240,
                'r_full': full_r,
                'r_shell': s_period,
                'info_240': info_bits_240,
                'info_shell': info_bits_shell,
                'info_full': info_bits_full,
                'ratio_shell_full': s_period / full_r if full_r > 0 else 0,
                'visited_shells': visited_shells,
                'd8_only': d8_only,
                'sp_only': sp_only,
            })

        return {
            'n': n,
            'num_constraints': len(constraints),
            'lcm_periods': lcm_periods,
            'factor_candidates': sorted(factor_candidates),
            'constraints': constraints,
            'lcm_bits': math.log2(lcm_periods) if lcm_periods > 1 else 0,
            'n_bits': n.bit_length(),
        }

    def _multiplicative_order(self, a: int, n: int) -> int:
        if math.gcd(a, n) != 1:
            return -1
        val, r = a % n, 1
        while val != 1 and r <= n:
            val = (val * a) % n
            r += 1
        return r if val == 1 else -1


class ShellConstraintFactorizer:
    """
    Factorization via shell oracle constraints + lattice reduction.

    The algorithm:
    1. For k bases, compute r_240^(i) in O(64) each -> O(64k) total
    2. For each base, compute gcd(a^(r_240/2) - 1, N) as factor candidate
    3. If that fails, use the TYPE pattern as additional constraint:
       - D8-only orbits tell us the period maps to shell +-2
       - S+-only orbits tell us the period maps to shells +-1, +-3
       - This constrains period mod 6 (the shell period)
    4. Combine constraints and attempt factoring

    The critical question we test: does the shell constraint provide
    enough information to factor N faster than classical O(sqrt(N))?
    """

    def __init__(self, lattice: E8Lattice):
        self.oracle = ShellOracle(lattice)
        self.lattice = lattice

    def factor_via_shell_constraints(self, n: int, verbose: bool = False) -> Dict:
        """
        Attempt factoring using shell oracle constraints.

        Returns analysis of how much the shell oracle helps.
        """
        start = time.time()

        # Phase 1: Cheap mod-240 constraints only (O(64) per base)
        phase1_factors = set()
        phase1_info = 0
        r240_lcm = 1

        for a in range(2, min(n, 200)):
            if math.gcd(a, n) != 1:
                g = math.gcd(a, n)
                if 1 < g < n:
                    phase1_factors.add(g)
                    break
                continue

            r240, _ = self.oracle.orbit_mod_240(a)
            r240_lcm = math.lcm(r240_lcm, r240)

            # Try half-turn with mod-240 period
            if r240 % 2 == 0:
                half = pow(a, r240 // 2, n)
                p = math.gcd(half - 1, n)
                q = math.gcd(half + 1, n)
                if 1 < p < n:
                    phase1_factors.add(p)
                    break
                if 1 < q < n:
                    phase1_factors.add(q)
                    break

        phase1_time = time.time() - start

        if phase1_factors:
            f = min(phase1_factors)
            return {
                'n': n, 'bits': n.bit_length(),
                'factors': (f, n // f),
                'method': 'shell_phase1_mod240',
                'phase1_time': phase1_time,
                'total_time': phase1_time,
                'r240_lcm': r240_lcm,
                'success': True,
            }

        # Phase 2: Full period computation with shell analysis
        phase2_start = time.time()
        analysis = self.oracle.multi_base_constraint(n, num_bases=15)
        phase2_time = time.time() - phase2_start

        if analysis['factor_candidates']:
            f = analysis['factor_candidates'][0]
            return {
                'n': n, 'bits': n.bit_length(),
                'factors': (f, n // f),
                'method': 'shell_phase2_orbit',
                'phase1_time': phase1_time,
                'phase2_time': phase2_time,
                'total_time': time.time() - start,
                'r240_lcm': r240_lcm,
                'lcm_bits': analysis['lcm_bits'],
                'success': True,
            }

        # Phase 3: Fermat with shell-guided search
        phase3_start = time.time()
        result = self._fermat_shell_guided(n, analysis)
        phase3_time = time.time() - phase3_start

        if result:
            return {
                'n': n, 'bits': n.bit_length(),
                'factors': result,
                'method': 'shell_phase3_fermat_guided',
                'phase1_time': phase1_time,
                'phase2_time': phase2_time,
                'phase3_time': phase3_time,
                'total_time': time.time() - start,
                'success': True,
            }

        return {
            'n': n, 'bits': n.bit_length(),
            'factors': None,
            'method': 'failed',
            'total_time': time.time() - start,
            'analysis': analysis,
            'success': False,
        }

    def _fermat_shell_guided(self, n: int, analysis: Dict,
                             max_iter: int = 100000) -> Optional[Tuple[int, int]]:
        """
        Fermat factorization guided by shell constraint information.

        The shell analysis tells us about the structure of phi(N) = (p-1)(q-1).
        This constrains (p+q)/2 = sqrt(N + ((p-q)/2)^2), which guides the
        Fermat search.
        """
        a = math.isqrt(n)
        if a * a < n:
            a += 1

        # Use the LCM of orbit periods as a divisor of phi(N)
        # phi(N) = N - (p+q) + 1, so p+q = N + 1 - phi(N)
        # We know lcm_periods | phi(N), so phi(N) = k * lcm_periods for some k
        lcm_p = analysis.get('lcm_periods', 1)

        if lcm_p > 1:
            # phi(N) is a multiple of lcm_p
            # p + q = N + 1 - phi(N) = N + 1 - k * lcm_p
            # Try small multiples of lcm_p
            for k in range(1, max_iter):
                phi_candidate = k * lcm_p
                sum_pq = n + 1 - phi_candidate
                if sum_pq <= 0 or sum_pq > 2 * n:
                    continue
                # p + q = sum_pq, p * q = N
                # p, q are roots of x^2 - sum_pq * x + N = 0
                discriminant = sum_pq * sum_pq - 4 * n
                if discriminant < 0:
                    continue
                sqrt_disc = math.isqrt(discriminant)
                if sqrt_disc * sqrt_disc == discriminant:
                    p = (sum_pq + sqrt_disc) // 2
                    q = (sum_pq - sqrt_disc) // 2
                    if p > 1 and q > 1 and p * q == n:
                        return (min(p, q), max(p, q))

        # Fallback to standard Fermat
        for i in range(min(max_iter, 100000)):
            b_sq = (a + i) * (a + i) - n
            if b_sq < 0:
                continue
            b = math.isqrt(b_sq)
            if b * b == b_sq:
                p, q = a + i + b, a + i - b
                if p > 1 and q > 1 and p * q == n:
                    return (min(p, q), max(p, q))

        return None


class ShellOracleAnalysis:
    """
    Empirical analysis of how much information the shell oracle provides.

    Key measurements:
    1. Information ratio: info_shell / info_full (how much period info
       does the shell give for free?)
    2. Phase 1 success rate: how often does mod-240 alone factor N?
    3. Shell-type correlation: do D8-only orbits predict even periods?
    """

    def __init__(self, lattice: E8Lattice):
        self.oracle = ShellOracle(lattice)
        self.factorizer = ShellConstraintFactorizer(lattice)
        self.lattice = lattice

    def measure_information_content(self, n: int) -> Dict:
        """Measure how much period information the shell oracle extracts."""
        analysis = self.oracle.multi_base_constraint(n, num_bases=10)

        if not analysis['constraints']:
            return {'n': n, 'no_data': True}

        # Average information ratios
        ratios = [c['ratio_shell_full'] for c in analysis['constraints']
                  if c['r_full'] > 0]
        info_240 = [c['info_240'] for c in analysis['constraints']]
        info_full = [c['info_full'] for c in analysis['constraints']
                     if c['info_full'] > 0]

        # Type analysis
        d8_periods = [c['r_full'] for c in analysis['constraints']
                      if c['d8_only'] and c['r_full'] > 0]
        sp_periods = [c['r_full'] for c in analysis['constraints']
                      if c['sp_only'] and c['r_full'] > 0]
        d8_even = sum(1 for r in d8_periods if r % 2 == 0)
        sp_even = sum(1 for r in sp_periods if r % 2 == 0)

        return {
            'n': n,
            'n_bits': n.bit_length(),
            'avg_shell_full_ratio': np.mean(ratios) if ratios else 0,
            'avg_info_240': np.mean(info_240) if info_240 else 0,
            'avg_info_full': np.mean(info_full) if info_full else 0,
            'info_ratio': (np.mean(info_240) / np.mean(info_full)
                          if info_full and np.mean(info_full) > 0 else 0),
            'd8_orbits': len(d8_periods),
            'sp_orbits': len(sp_periods),
            'd8_even_frac': d8_even / max(len(d8_periods), 1),
            'sp_even_frac': sp_even / max(len(sp_periods), 1),
            'lcm_bits': analysis['lcm_bits'],
        }

    def comprehensive_test(self, max_bits: int = 30) -> Dict:
        """
        Comprehensive empirical test of the shell oracle.
        """
        import random
        rng = random.Random(42)

        def random_prime(bits):
            while True:
                n = rng.getrandbits(bits) | (1 << (bits - 1)) | 1
                if is_probable_prime(n):
                    return n

        def is_probable_prime(n):
            if n < 2: return False
            for p in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]:
                if n == p: return True
                if n % p == 0: return False
            # Miller-Rabin with a few witnesses
            d, r = n - 1, 0
            while d % 2 == 0:
                d //= 2
                r += 1
            for a in [2, 3, 5, 7, 11]:
                if a >= n: continue
                x = pow(a, d, n)
                if x == 1 or x == n - 1: continue
                found = False
                for _ in range(r - 1):
                    x = pow(x, 2, n)
                    if x == n - 1:
                        found = True
                        break
                if not found:
                    return False
            return True

        results = []

        for bits in range(6, min(max_bits + 1, 40), 2):
            half = max(bits // 2, 3)
            p = random_prime(half)
            q = random_prime(half)
            while q == p:
                q = random_prime(half)
            n = p * q

            # Information measurement
            info = self.measure_information_content(n)

            # Factoring test
            fac = self.factorizer.factor_via_shell_constraints(n)

            correct = (fac['success'] and fac['factors'] is not None and
                      set(fac['factors']) == {p, q})

            results.append({
                'bits': n.bit_length(),
                'n': n,
                'p': p, 'q': q,
                'factored': correct,
                'method': fac.get('method', 'failed'),
                'time': fac.get('total_time', 0),
                'info_ratio': info.get('info_ratio', 0),
                'lcm_bits': info.get('lcm_bits', 0),
                'shell_full_ratio': info.get('avg_shell_full_ratio', 0),
                'd8_even_frac': info.get('d8_even_frac', 0),
            })

        return results


if __name__ == '__main__':
    print("=" * 72)
    print(" SHELL ORACLE PERIOD EXTRACTION (SOPE)")
    print(" Measuring the information content of the E8 shell metric")
    print("=" * 72)

    lattice = E8Lattice()
    analysis = ShellOracleAnalysis(lattice)

    print("\n--- Information Content Analysis ---")
    print(f"{'Bits':>5s}  {'N':>12s}  {'InfoRatio':>10s}  {'LCM_bits':>9s}  "
          f"{'Shell/Full':>11s}  {'D8_even':>8s}  {'Factored':>8s}  "
          f"{'Method':>20s}  {'Time':>8s}")
    print(f"  {'-'*5}  {'-'*12}  {'-'*10}  {'-'*9}  {'-'*11}  "
          f"{'-'*8}  {'-'*8}  {'-'*20}  {'-'*8}")

    results = analysis.comprehensive_test(max_bits=34)

    for r in results:
        print(f"  {r['bits']:>4d}  {r['n']:>12d}  "
              f"{r['info_ratio']:>10.3f}  {r['lcm_bits']:>9.1f}  "
              f"{r['shell_full_ratio']:>11.3f}  "
              f"{r['d8_even_frac']:>8.2f}  "
              f"{'YES' if r['factored'] else 'NO':>8s}  "
              f"{r['method']:>20s}  {r['time']:>7.4f}s")

    # Summary statistics
    factored = [r for r in results if r['factored']]
    print(f"\n--- Summary ---")
    print(f"  Factored: {len(factored)}/{len(results)}")
    print(f"  Max bits factored: {max((r['bits'] for r in factored), default=0)}")
    if factored:
        avg_info = np.mean([r['info_ratio'] for r in factored if r['info_ratio'] > 0])
        avg_shell = np.mean([r['shell_full_ratio'] for r in factored])
        print(f"  Avg info ratio (mod-240/full): {avg_info:.3f}")
        print(f"  Avg shell/full period ratio:   {avg_shell:.3f}")
        print(f"  Avg D8 even-period fraction:   "
              f"{np.mean([r['d8_even_frac'] for r in factored]):.3f}")

    phase1 = [r for r in results if 'phase1' in r.get('method', '')]
    phase2 = [r for r in results if 'phase2' in r.get('method', '')]
    phase3 = [r for r in results if 'phase3' in r.get('method', '')]
    print(f"\n  Phase 1 (mod-240 only):     {len(phase1)} successes")
    print(f"  Phase 2 (full orbit):       {len(phase2)} successes")
    print(f"  Phase 3 (Fermat + guided):  {len(phase3)} successes")

    # THE KEY QUESTION: Does the shell oracle provide sub-sqrt(N) information?
    print(f"\n--- THE KEY QUESTION ---")
    print(f"  Does the shell oracle provide information faster than sqrt(N)?")
    for r in results:
        sqrt_n_bits = r['bits'] / 2
        if r['lcm_bits'] > 0:
            speedup = r['lcm_bits'] / sqrt_n_bits
            print(f"  {r['bits']:>3d}-bit: lcm gives {r['lcm_bits']:.1f} bits "
                  f"vs sqrt(N)={sqrt_n_bits:.1f} bits  "
                  f"ratio={speedup:.2f}")
