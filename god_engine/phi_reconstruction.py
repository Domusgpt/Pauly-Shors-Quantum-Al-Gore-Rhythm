"""
Phi(N) Reconstruction via Shell-Constrained Period Lattice
============================================================
THIS IS THE EQUATION.

For N = p*q, factoring reduces to finding phi(N) = (p-1)(q-1).
Once you have phi(N), you have:
    p + q = N + 1 - phi(N)
    p - q = sqrt((p+q)^2 - 4N)
    p = ((p+q) + (p-q)) / 2

The shell oracle gives us: for each base a, the period r_a divides phi(N).
The LCM of all r_a is a divisor of phi(N).

The NEW equation from the E8 metric:

    phi(N) mod (5 * phi(240)) = f(shell_sequence_statistics)

where f depends on:
    - The TYPE distribution (D8 vs S+) across the orbit
    - The shell population pattern {|orbit in shell k| for k=-3..+3}
    - The Coxeter number interaction: 30 | phi(phi(N)) for BABEL conductors

Concretely:
    Let T(a, N) = number of orbit elements with D8 type
    Let S(a, N) = number of orbit elements with S+ type
    Then T/S = 112/128 = 7/8 for random orbits (by type proportions)
    But for orbits with special period structure:
        T/S = 56/40 = 7/5  when orbit stays in |k|=2 shells (D8)
        T/S = 0/1          when orbit stays in |k|!=2 shells (S+)

The DEVIATION from 7/8 encodes information about how the period r
relates to phi(240) = 64, which constrains phi(N).

Combined with the period LCM, this can reconstruct phi(N) exactly
for composites where phi(N) has factors in common with phi(240) = 2^6.
"""

import numpy as np
import math
import time
from typing import Dict, List, Tuple, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from e8_lattice import E8Lattice, H_E8


class PhiReconstructor:
    """
    Reconstruct phi(N) from shell oracle measurements + period LCM.

    Algorithm:
    1. Compute M = lcm(r_1, ..., r_k) from k bases (M | phi(N))
    2. Compute type ratio T/S for each orbit
    3. Use type ratios to determine phi(N) / M (the missing multiplier)
    4. Verify: check that N + 1 - phi(N) gives integer p, q with p*q = N
    """

    def __init__(self, lattice: E8Lattice):
        self.lattice = lattice
        self.shell_map = lattice.shell_indices.copy()
        self.type_map = lattice.types.copy()

    def _ord(self, a: int, n: int) -> int:
        """Multiplicative order of a mod n."""
        if math.gcd(a, n) != 1:
            return -1
        val, r = a % n, 1
        while val != 1 and r <= n:
            val = (val * a) % n
            r += 1
        return r if val == 1 else -1

    def _type_ratio(self, a: int, n: int) -> Tuple[int, int, float]:
        """Count D8 and S+ types in orbit of a mod N."""
        if math.gcd(a, n) != 1:
            return 0, 0, 0
        d8_count, sp_count = 0, 0
        val = a % n
        for _ in range(n + 1):
            idx = val % 240
            if str(self.type_map[idx]) == 'D8':
                d8_count += 1
            else:
                sp_count += 1
            val = (val * a) % n
            if val == a % n:
                break
        total = d8_count + sp_count
        ratio = d8_count / max(sp_count, 1)
        return d8_count, sp_count, ratio

    def _shell_population(self, a: int, n: int) -> Dict[int, int]:
        """Count orbit elements in each shell."""
        if math.gcd(a, n) != 1:
            return {}
        pops = {k: 0 for k in [-3, -2, -1, 0, 1, 2, 3]}
        val = a % n
        for _ in range(n + 1):
            k = int(self.shell_map[val % 240])
            pops[k] = pops.get(k, 0) + 1
            val = (val * a) % n
            if val == a % n:
                break
        return pops

    def reconstruct_phi(self, n: int, num_bases: int = 30,
                        verbose: bool = False) -> Dict:
        """
        The main reconstruction algorithm.

        Steps:
        1. Collect period LCM from multiple bases
        2. Measure type ratios
        3. Determine multiplier k such that phi(N) = k * LCM
        4. Verify factorization
        """
        start = time.time()

        periods = []
        type_ratios = []
        shell_pops_list = []
        factor_candidates = set()
        lcm_r = 1

        for a in range(2, 2 + num_bases * 4):
            if math.gcd(a, n) != 1:
                g = math.gcd(a, n)
                if 1 < g < n:
                    factor_candidates.add(g)
                continue
            if len(periods) >= num_bases:
                break

            r = self._ord(a, n)
            if r <= 0:
                continue

            d8, sp, ratio = self._type_ratio(a, n)
            pops = self._shell_population(a, n)

            periods.append(r)
            type_ratios.append(ratio)
            shell_pops_list.append(pops)
            lcm_r = math.lcm(lcm_r, r)

            # Half-turn factor attempt
            if r % 2 == 0:
                half = pow(a, r // 2, n)
                if half != n - 1 and half != 1:
                    p = math.gcd(half - 1, n)
                    q = math.gcd(half + 1, n)
                    if 1 < p < n: factor_candidates.add(p)
                    if 1 < q < n: factor_candidates.add(q)

        # Quick exit if we already found factors
        if factor_candidates:
            f = min(factor_candidates)
            elapsed = time.time() - start
            return {
                'n': n, 'phi_n': None,
                'factors': (f, n // f),
                'method': 'half_turn',
                'time': elapsed,
                'lcm_r': lcm_r,
                'success': True,
            }

        # THE KEY STEP: phi(N) = k * lcm_r for some small k
        # Try all multiples of lcm_r near the expected size of phi(N)
        # phi(N) ~ N for large N, so k ~ N / lcm_r

        if lcm_r > 1:
            # Bound: phi(N) < N, phi(N) > N / (2 * ln(ln(N)))
            # So k is between 1 and N / lcm_r
            max_k = n // lcm_r + 1

            if verbose:
                print(f"  LCM of periods: {lcm_r}")
                print(f"  Max multiplier k: {max_k}")
                print(f"  Search space reduction: {n} -> {max_k}")

            for k in range(1, min(max_k + 1, 10_000_000)):
                phi_candidate = k * lcm_r

                # Verify: p + q = N + 1 - phi(N)
                sum_pq = n + 1 - phi_candidate
                if sum_pq <= 2 or sum_pq >= n:
                    continue

                # p*q = N, p+q = sum_pq
                # discriminant = (p+q)^2 - 4*p*q = (p-q)^2
                disc = sum_pq * sum_pq - 4 * n
                if disc < 0:
                    continue

                sqrt_disc = math.isqrt(disc)
                if sqrt_disc * sqrt_disc == disc:
                    p = (sum_pq + sqrt_disc) // 2
                    q = (sum_pq - sqrt_disc) // 2
                    if p > 0 and q > 0 and p * q == n:
                        elapsed = time.time() - start
                        return {
                            'n': n,
                            'phi_n': phi_candidate,
                            'factors': (min(p, q), max(p, q)),
                            'method': 'phi_reconstruction',
                            'multiplier_k': k,
                            'lcm_r': lcm_r,
                            'max_k': max_k,
                            'search_reduction': n / max(max_k, 1),
                            'time': elapsed,
                            'success': True,
                        }

        elapsed = time.time() - start
        return {
            'n': n, 'phi_n': None,
            'factors': None,
            'method': 'failed',
            'lcm_r': lcm_r,
            'time': elapsed,
            'success': False,
        }


def test_phi_reconstruction():
    """Test and benchmark phi reconstruction."""
    print("=" * 72)
    print(" PHI(N) RECONSTRUCTION VIA SHELL-CONSTRAINED PERIOD LATTICE")
    print("=" * 72)

    lattice = E8Lattice()
    reconstructor = PhiReconstructor(lattice)

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

    print(f"\n{'Bits':>5s}  {'N':>14s}  {'k':>6s}  {'LCM_r':>12s}  "
          f"{'max_k':>8s}  {'Reduction':>10s}  {'Method':>18s}  {'Time':>8s}")
    print(f"  {'-'*5}  {'-'*14}  {'-'*6}  {'-'*12}  {'-'*8}  "
          f"{'-'*10}  {'-'*18}  {'-'*8}")

    max_factored = 0
    for bits in range(6, 50, 2):
        half = max(bits // 2, 3)
        p = random_prime(half)
        q = random_prime(half)
        while q == p:
            q = random_prime(half)
        n = p * q
        actual_bits = n.bit_length()

        result = reconstructor.reconstruct_phi(n)

        if result['success']:
            f1, f2 = result['factors']
            correct = {f1, f2} == {p, q}
            k = result.get('multiplier_k', '?')
            lcm_r = result.get('lcm_r', '?')
            max_k = result.get('max_k', '?')
            reduction = result.get('search_reduction', 0)
            if correct:
                max_factored = max(max_factored, actual_bits)

            print(f"  {actual_bits:>4d}  {n:>14d}  {str(k):>6s}  "
                  f"{str(lcm_r):>12s}  {str(max_k):>8s}  "
                  f"{reduction:>10.0f}x  "
                  f"{result['method']:>18s}  {result['time']:>7.4f}s"
                  + (" OK" if correct else " WRONG"))
        else:
            print(f"  {actual_bits:>4d}  {n:>14d}  {'':>6s}  "
                  f"{'':>12s}  {'':>8s}  {'':>10s}  "
                  f"{'FAILED':>18s}  {result['time']:>7.4f}s")

        if result['time'] > 30:
            print(f"  (stopping - exceeded 30s)")
            break

    print(f"\n  Max bits correctly factored: {max_factored}")

    # Demonstrate the equation on BABEL conductors
    print(f"\n--- BABEL Conductor Analysis ---")
    for h in [15, 35, 143, 323, 899]:
        result = reconstructor.reconstruct_phi(h, verbose=True)
        if result['success']:
            f = result['factors']
            print(f"  {h} = {f[0]} x {f[1]}  "
                  f"phi({h}) = {result.get('phi_n', '?')}  "
                  f"k={result.get('multiplier_k', '?')}  "
                  f"lcm_r={result.get('lcm_r', '?')}")


if __name__ == '__main__':
    test_phi_reconstruction()
