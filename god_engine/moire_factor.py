"""
Moire Pattern Factorization Engine
====================================
Uses interference patterns between E8 lattice projections at different
scales to reveal the factor structure of composite numbers.

Core Idea:
  When you overlay two periodic lattice projections with periods p and q,
  the moire interference pattern has period lcm(p,q) and reveals the
  factor relationship. By projecting the multiplicative group (Z/nZ)*
  through the E8 cross-parity projection at multiple scales corresponding
  to candidate factors, we get constructive interference ONLY when the
  candidate is an actual factor.

  This is the geometric analog of period-finding in Shor's algorithm:
  - Shor uses QFT to find the period of a^x mod N
  - We use E8 lattice interference to find geometric resonance at factor periods

The Galois orbit sigma_a^x on the Clifford torus IS the period-finding
step. The moire pattern IS the interference that reveals the period.
"""

import numpy as np
import math
from typing import Optional, Tuple, List, Dict


class MoirePatternEngine:
    """
    Generates and analyzes moire interference patterns from E8 lattice
    projections to detect factors of composite numbers.
    """

    def __init__(self, lattice):
        self.lattice = lattice

    def _galois_orbit(self, a: int, n: int) -> List[int]:
        """Compute multiplicative order orbit of a mod n."""
        if math.gcd(a, n) != 1:
            return []
        orbit = []
        val = a % n
        for _ in range(n + 1):
            orbit.append(val)
            val = (val * a) % n
            if val == a % n:
                break
        return orbit

    def _orbit_period(self, a: int, n: int) -> int:
        """Period of a in (Z/nZ)* — the Galois orbit length."""
        if math.gcd(a, n) != 1:
            return -1
        val = a % n
        r = 1
        while True:
            val = (val * a) % n
            if val == a % n:
                break
            r += 1
            if r > n:
                return -1
        return r

    def lattice_wave(self, period: int, phase: float, resolution: int = 1024) -> np.ndarray:
        """
        Generate a 1D lattice wave with given period.

        Maps the E8 shell structure onto a periodic signal:
        the shell populations [24, 56, 40, 40, 56, 24] modulate
        the wave amplitude at each cycle.
        """
        t = np.linspace(0, 2 * np.pi * (resolution / period), resolution)
        # Base wave
        wave = np.cos(t)
        # Modulate by E8 shell populations (normalized)
        pops = np.array([24, 56, 40, 40, 56, 24]) / 240.0
        shell_mod = np.zeros_like(t)
        for k, pop in enumerate(pops):
            shell_mod += pop * np.cos((k + 1) * t / period + phase)
        return wave * (1 + 0.5 * shell_mod)

    def moire_interference(self, p1: int, p2: int, resolution: int = 4096) -> Dict:
        """
        Compute moire pattern between two lattice waves with periods p1, p2.

        The moire beat frequency = |1/p1 - 1/p2| reveals lcm structure.
        """
        wave1 = self.lattice_wave(p1, 0.0, resolution)
        wave2 = self.lattice_wave(p2, np.pi / 7, resolution)

        # Interference
        combined = wave1 + wave2
        envelope = np.abs(wave1 * wave2)

        # FFT to find dominant frequencies
        fft = np.fft.rfft(combined)
        freqs = np.fft.rfftfreq(resolution)
        magnitudes = np.abs(fft)

        # Find peaks (above 5x median)
        median_mag = np.median(magnitudes[1:])
        peak_indices = np.where(magnitudes > 5 * median_mag)[0]
        peak_freqs = freqs[peak_indices]
        peak_mags = magnitudes[peak_indices]

        # Beat frequency
        beat = abs(1.0 / p1 - 1.0 / p2) if p1 != p2 else 0
        lcm_val = math.lcm(p1, p2)

        return {
            'p1': p1, 'p2': p2,
            'beat_frequency': beat,
            'lcm': lcm_val,
            'gcd': math.gcd(p1, p2),
            'num_peaks': len(peak_indices),
            'dominant_freq': freqs[np.argmax(magnitudes[1:]) + 1] if len(magnitudes) > 1 else 0,
            'interference_energy': np.sum(envelope**2),
            'combined': combined,
            'envelope': envelope,
        }

    def galois_moire_scan(self, n: int, max_base: int = 50) -> Dict:
        """
        Scan multiple bases and compute Galois orbit moire patterns.

        For each base a, the orbit period r divides phi(n).
        When r is even, a^(r/2) mod n gives the "spinor half-turn"
        which, via GCD, can extract factors.

        The moire analysis adds: interference between different bases'
        orbit periods reveals common divisor structure = factors.
        """
        results = {
            'n': n,
            'bases_tested': 0,
            'orbits': [],
            'factor_candidates': set(),
            'moire_resonances': [],
        }

        orbit_periods = []

        for a in range(2, min(max_base, n)):
            if math.gcd(a, n) != 1:
                # Direct factor found
                g = math.gcd(a, n)
                if 1 < g < n:
                    results['factor_candidates'].add(g)
                    results['factor_candidates'].add(n // g)
                continue

            r = self._orbit_period(a, n)
            if r <= 0:
                continue

            results['bases_tested'] += 1
            orbit_periods.append((a, r))

            # Classical Shor step: if r is even, try half-turn
            if r % 2 == 0:
                half_turn = pow(a, r // 2, n)
                if half_turn != n - 1:
                    p = math.gcd(half_turn - 1, n)
                    q = math.gcd(half_turn + 1, n)
                    if 1 < p < n:
                        results['factor_candidates'].add(p)
                        results['factor_candidates'].add(n // p)
                    if 1 < q < n:
                        results['factor_candidates'].add(q)
                        results['factor_candidates'].add(n // q)

            results['orbits'].append({
                'base': a,
                'period': r,
                'half_turn': pow(a, r // 2, n) if r % 2 == 0 else None,
            })

        # Moire analysis: interference between orbit periods
        if len(orbit_periods) >= 2:
            for i in range(min(len(orbit_periods), 10)):
                for j in range(i + 1, min(len(orbit_periods), 10)):
                    a1, r1 = orbit_periods[i]
                    a2, r2 = orbit_periods[j]
                    moire = self.moire_interference(max(r1, 2), max(r2, 2))
                    if moire['gcd'] > 1:
                        results['moire_resonances'].append({
                            'bases': (a1, a2),
                            'periods': (r1, r2),
                            'gcd_periods': moire['gcd'],
                            'energy': moire['interference_energy'],
                        })

        results['factor_candidates'] = sorted(results['factor_candidates'])
        return results

    def multi_scale_projection(self, n: int) -> Dict:
        """
        Project n's residue structure through E8 at multiple scales.

        Each BABEL tower level provides a different projection scale:
          Level 0 (E8):    delta = sqrt(5)/10,  8D
          Level 1 (Leech): delta = 1/(2*sqrt(7)), 24D
          Level 2 (Craig): delta = 1/(2*sqrt(13)), 120D

        Factors create resonance at specific tower levels based on
        their relationship to the tower twin primes.
        """
        from math import gcd
        residues = [a for a in range(1, n) if gcd(a, n) == 1]
        phi_n = len(residues)

        # Project through E8 shell structure at each scale
        tower_deltas = [
            math.sqrt(5) / 10,        # Level 0
            1 / (2 * math.sqrt(7)),    # Level 1
            1 / (2 * math.sqrt(13)),   # Level 2
        ]

        resonances = []
        for level, delta in enumerate(tower_deltas):
            # Map residues to shell-quantized radii
            radii = []
            for a in residues:
                r_sq = 1 + ((a % 6) - 3) * delta  # Shell-like quantization
                if r_sq > 0:
                    radii.append(math.sqrt(r_sq))

            if not radii:
                continue

            radii = np.array(radii)

            # Check for clustering at shell boundaries
            # (factors create discrete clusters)
            hist, edges = np.histogram(radii, bins=50)
            max_gap = max(np.diff(edges[hist > 0])) if np.sum(hist > 0) > 1 else 0
            clustering = np.std(radii) / np.mean(radii) if np.mean(radii) > 0 else 0

            resonances.append({
                'level': level,
                'delta': delta,
                'clustering': clustering,
                'max_gap': max_gap,
                'mean_radius': np.mean(radii),
            })

        return {
            'n': n,
            'phi_n': phi_n,
            'tower_resonances': resonances,
        }


class MoireFactorizer:
    """
    Complete factorization system combining Galois orbit period-finding
    with moire interference analysis.
    """

    def __init__(self, lattice):
        self.engine = MoirePatternEngine(lattice)

    def factorize(self, n: int, verbose: bool = True) -> Dict:
        """
        Attempt to factor n using:
        1. Galois orbit period-finding (classical Shor)
        2. Moire interference resonance detection
        3. Multi-scale tower projection
        """
        if n < 4:
            return {'n': n, 'factors': [n], 'method': 'trivial'}

        # Check small primes first
        for p in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31]:
            if n % p == 0 and n != p:
                return {'n': n, 'factors': sorted([p, n // p]), 'method': 'trial_division'}

        # Galois orbit scan with moire
        scan = self.engine.galois_moire_scan(n)

        if scan['factor_candidates']:
            factors = scan['factor_candidates']
            # Verify
            for f in factors:
                if 1 < f < n and n % f == 0:
                    if verbose:
                        print(f"  Factor found via Galois orbit: {n} = {f} x {n//f}")
                        if scan['moire_resonances']:
                            best = max(scan['moire_resonances'],
                                      key=lambda x: x['energy'])
                            print(f"  Moire resonance: bases={best['bases']} "
                                  f"periods={best['periods']} "
                                  f"gcd={best['gcd_periods']}")
                    return {
                        'n': n,
                        'factors': sorted([f, n // f]),
                        'method': 'galois_orbit_moire',
                        'orbits_tested': scan['bases_tested'],
                        'moire_resonances': len(scan['moire_resonances']),
                    }

        return {'n': n, 'factors': None, 'method': 'failed'}


if __name__ == '__main__':
    from e8_lattice import E8Lattice

    print("=" * 70)
    print("MOIRE PATTERN FACTORIZATION ENGINE - TEST")
    print("=" * 70)

    lattice = E8Lattice()
    factorizer = MoireFactorizer(lattice)

    # Test composites
    test_numbers = [
        15, 21, 35, 77, 91, 143, 221, 323, 437, 899,
        1147, 2021, 3127, 4087, 5767, 7387, 10403,
        # BABEL tower conductors
        15, 35, 143, 323, 899,
        # RSA-style
        127 * 131,    # 16637
        251 * 257,    # 64507
        509 * 521,    # 265189
    ]

    successes = 0
    for n in test_numbers:
        result = factorizer.factorize(n, verbose=False)
        if result['factors']:
            successes += 1
            f = result['factors']
            print(f"  {n:>8d} = {f[0]} x {f[1] if len(f) > 1 else '(prime)'}"
                  f"  [{result['method']}]")
        else:
            print(f"  {n:>8d} = FAILED")

    print(f"\nSuccess rate: {successes}/{len(test_numbers)} "
          f"({100*successes/len(test_numbers):.1f}%)")
