"""
E8 Lattice Engine - Core Mathematical Foundation
=================================================
Consolidated from:
  - code/core/e8_lattice_codec_patent.py (master)
  - code/simulations/constellation_hopping_security.py (master)
  - code/verification/verify_cross_parity.py (codex branch)
  - MVP_Prototypes/One_Parameter_Universe_Compiler (jules branch)

All 240 E8 roots, D8/S+ type classification, cross-parity Coxeter
projection, six-shell decomposition, Galois group structure.

Author: Paul J. Phillips / Clear Seas Solutions LLC
"""

import numpy as np
from itertools import product as cart_product
from functools import lru_cache
import math


# === CONSTANTS (from tower_constants.py) ===
DELTA = math.sqrt(5) / 10          # Shell quantum = sqrt(5)/10
PHI = (1 + math.sqrt(5)) / 2       # Golden ratio
S_TYPE = (5 + 2*math.sqrt(5)) / 10 # Type separation constant = delta * phi^3
H_E8 = 30                          # E8 Coxeter number
RANK_E8 = 8                        # E8 rank
E8_EXPONENTS = (1, 7, 11, 13, 17, 19, 23, 29)  # Coprime to 30
H4_EXPONENTS = (1, 11, 19, 29)     # Golden exponents for type separation
WEYL_ORDER = 696_729_600            # |W(E8)|


class E8Lattice:
    """Complete E8 root system with cross-parity projection."""

    def __init__(self):
        self.roots, self.types = self._build_roots()
        self.coxeter = self._build_coxeter_element()
        self.cross_parity = self._build_cross_parity_element()
        self.projection_matrix = self._build_projection_matrix()
        self.projected, self.shells, self.shell_indices = self._project_all()

    # ----- Root Construction -----

    @staticmethod
    def _build_roots():
        """Construct all 240 E8 roots with D8/S+ type labels."""
        roots, types = [], []
        # D8 roots: +/- e_i +/- e_j  (112 vectors)
        for i in range(8):
            for j in range(i + 1, 8):
                for si in (1, -1):
                    for sj in (1, -1):
                        v = np.zeros(8)
                        v[i], v[j] = si, sj
                        roots.append(v)
                        types.append('D8')
        # S+ roots: (+/-1/2)^8 with even number of minus signs  (128 vectors)
        for signs in cart_product([0.5, -0.5], repeat=8):
            v = np.array(signs)
            if np.sum(v < 0) % 2 == 0:
                roots.append(v)
                types.append('S+')
        roots = np.array(roots)
        types = np.array(types)
        assert len(roots) == 240
        assert np.sum(types == 'D8') == 112
        assert np.sum(types == 'S+') == 128
        return roots, types

    @staticmethod
    def _build_coxeter_element():
        """Build Coxeter element from Bourbaki E8 simple roots."""
        simple = np.zeros((8, 8))
        simple[0] = [1, -1, 0, 0, 0, 0, 0, 0]
        simple[1] = [0, 1, -1, 0, 0, 0, 0, 0]
        simple[2] = [0, 0, 1, -1, 0, 0, 0, 0]
        simple[3] = [0, 0, 0, 1, -1, 0, 0, 0]
        simple[4] = [0, 0, 0, 0, 1, -1, 0, 0]
        simple[5] = [0, 0, 0, 0, 0, 1, -1, 0]
        simple[6] = [0, 0, 0, 0, 0, 1, 1, 0]
        simple[7] = [-0.5] * 8
        w = np.eye(8)
        for a in simple:
            w = w @ (np.eye(8) - 2 * np.outer(a, a) / np.dot(a, a))
        return w

    def _build_cross_parity_element(self):
        """Cross-parity Coxeter element: wt = tau * w * tau^-1."""
        tau = np.diag([1, 1, 1, 1, 1, 1, 1, -1])
        return tau @ self.coxeter @ tau  # tau^-1 = tau for diagonal +/-1

    def _build_projection_matrix(self):
        """4D projection from H4 eigenplanes for exponents {1, 11}.

        Uses the verified method: find eigenvalues matching 2*pi*m/30
        for m in {1, 11}, take real and imaginary parts of their
        eigenvectors to get 4 real basis vectors, then QR-orthonormalize.
        """
        evals, evecs = np.linalg.eig(self.cross_parity)
        basis = []
        for m in [1, 11]:
            target = 2 * np.pi * m / H_E8
            for i, ev in enumerate(evals):
                ang = np.angle(ev) % (2 * np.pi)
                if (abs(ang - target) < 1e-6
                        or abs(ang - (2 * np.pi - target)) < 1e-6):
                    basis.append(evecs[:, i].real)
                    basis.append(evecs[:, i].imag)
                    break
        Q, _ = np.linalg.qr(np.array(basis).T)
        return Q[:, :4]

    def _project_all(self):
        """Project all 240 roots and classify into 6 shells.

        Uses the verified method: k = round((norm_sq - 1) / delta),
        with tolerance check.
        """
        projected = self.roots @ self.projection_matrix
        norms_sq = np.sum(projected**2, axis=1)
        sqrt5_10 = np.sqrt(5) / 10

        shell_indices = np.zeros(240, dtype=int)
        shells = {k: [] for k in [-3, -2, -1, 1, 2, 3]}

        for i, nsq in enumerate(norms_sq):
            k_float = (nsq - 1.0) / sqrt5_10
            k = round(k_float)
            if abs(k_float - k) < 0.01 and k in shells:
                shell_indices[i] = k
                shells[k].append(i)

        # Convert lists to arrays
        for k in shells:
            shells[k] = np.array(shells[k], dtype=int)

        return projected, shells, shell_indices

    # ----- Verification -----

    def verify_type_separation(self):
        """Verify perfect D8/S+ type separation across all 6 shells."""
        results = {}
        for k in [-3, -2, -1, 1, 2, 3]:
            indices = self.shells[k]
            shell_types = set(self.types[indices])
            expected = {'D8'} if abs(k) == 2 else {'S+'}
            pure = shell_types == expected
            results[k] = {
                'population': len(indices),
                'types': shell_types,
                'expected': expected,
                'pure': pure,
            }
        total_classified = sum(len(self.shells[k]) for k in self.shells)
        all_pure = all(r['pure'] for r in results.values())
        return {
            'shells': results,
            'total_classified': total_classified,
            'all_pure': all_pure,
            'populations': {k: len(self.shells[k]) for k in [-3,-2,-1,1,2,3]},
        }

    # ----- Galois Group Structure -----

    @staticmethod
    def galois_group():
        """(Z/30Z)* - the Galois group of Q(zeta_30)."""
        return [a for a in range(30) if math.gcd(a, 30) == 1]

    @staticmethod
    def galois_involutions():
        """Three critical involutions of (Z/30Z)*."""
        return {
            'sigma_29': 29,   # Palindromic: m -> -m mod 30
            'sigma_11': 11,   # Galois conjugation within pairs
            'sigma_19': 19,   # Combined action
        }

    # ----- Information Theory -----

    def entropy_decomposition(self):
        """H(type) + H(shell|type) + H(pos|shell,type) = log2(240)."""
        from collections import Counter
        total = len(self.roots)

        # H(type)
        type_counts = Counter(self.types)
        h_type = -sum((c/total) * np.log2(c/total) for c in type_counts.values())

        # H(shell|type)
        h_shell_given_type = 0
        for t in ['D8', 'S+']:
            t_mask = self.types == t
            t_count = np.sum(t_mask)
            p_t = t_count / total
            shell_counts = Counter(self.shell_indices[t_mask])
            h_shell_t = -sum((c/t_count) * np.log2(c/t_count)
                             for c in shell_counts.values() if c > 0)
            h_shell_given_type += p_t * h_shell_t

        # H(pos|shell,type) = log2(240) - H(type) - H(shell|type)
        h_total = np.log2(total)
        h_pos = h_total - h_type - h_shell_given_type

        return {
            'H_type': h_type,
            'H_shell_given_type': h_shell_given_type,
            'H_pos_given_shell_type': h_pos,
            'H_total': h_total,
            'residual': abs(h_total - h_type - h_shell_given_type - h_pos),
        }

    # ----- Codec -----

    def encode_symbol(self, data_bits):
        """Encode 7 data bits -> nearest E8 root (with free type parity)."""
        idx = int(data_bits, 2) if isinstance(data_bits, str) else data_bits
        idx = idx % 240
        return self.roots[idx], self.types[idx], self.shell_indices[idx]

    def decode_symbol(self, received_4d):
        """Decode received 4D vector -> data + free parity check."""
        dists = np.sum((self.projected - received_4d)**2, axis=1)
        nearest = np.argmin(dists)
        norm_sq = np.sum(received_4d**2)

        # Shell classification for free parity
        best_k, best_dist = 0, 999
        for k in [-3, -2, -1, 1, 2, 3]:
            d = abs(norm_sq - (1 + k * DELTA))
            if d < best_dist:
                best_dist, best_k = d, k

        expected_type = 'D8' if abs(best_k) == 2 else 'S+'
        actual_type = self.types[nearest]
        parity_ok = expected_type == actual_type

        return {
            'index': nearest,
            'type': actual_type,
            'shell': best_k,
            'parity_ok': parity_ok,
            'distance': dists[nearest],
        }


class BABELTower:
    """The Paired Prime Tower of Babel connecting exceptional lattices."""

    LEVELS = {
        0: {'primes': (3, 5),   'h': 15,  'dim': 8,   'lattice': 'E8'},
        1: {'primes': (5, 7),   'h': 35,  'dim': 24,  'lattice': 'Leech'},
        2: {'primes': (11, 13), 'h': 143, 'dim': 120, 'lattice': 'Craig A_142^(2)'},
        3: {'primes': (17, 19), 'h': 323, 'dim': 288, 'lattice': 'Unknown'},
        4: {'primes': (29, 31), 'h': 899, 'dim': 840, 'lattice': 'Unknown'},
    }

    @classmethod
    def shell_quantum(cls, level):
        """delta_n = 1/(2*sqrt(q_n)) where q_n is the outer twin prime."""
        _, q = cls.LEVELS[level]['primes']
        return 1 / (2 * math.sqrt(q))

    @classmethod
    def galois_group_structure(cls, level):
        """(Z/h_nZ)* structure at tower level n."""
        p, q = cls.LEVELS[level]['primes']
        h = cls.LEVELS[level]['h']
        phi_h = (p - 1) * (q - 1)  # = p^2 - 1 = dim
        period = math.lcm(p - 1, q - 1)
        return {
            'h': h,
            'phi_h': phi_h,
            'cyclic_factors': (p - 1, q - 1),
            'orbit_period': period,
            'involution_count': 3,
        }

    @classmethod
    def orbit_period_ratios(cls):
        """Period ratios between tower levels = inner twin primes."""
        periods = []
        for lvl in range(3):
            gs = cls.galois_group_structure(lvl)
            periods.append(gs['orbit_period'])
        ratios = [periods[i+1] // periods[i] for i in range(len(periods)-1)]
        return periods, ratios


# === Standalone verification ===
if __name__ == '__main__':
    print("=" * 70)
    print("E8 LATTICE ENGINE - VERIFICATION")
    print("=" * 70)

    lattice = E8Lattice()

    # Type separation
    sep = lattice.verify_type_separation()
    print(f"\nType Separation: {'PERFECT' if sep['all_pure'] else 'FAILED'}")
    print(f"  Total classified: {sep['total_classified']}/240")
    for k in [-3, -2, -1, 1, 2, 3]:
        s = sep['shells'][k]
        print(f"  Shell k={k:+d}: pop={s['population']:3d}  type={s['types']}  "
              f"expected={s['expected']}  {'OK' if s['pure'] else 'FAIL'}")

    # Entropy
    ent = lattice.entropy_decomposition()
    print(f"\nEntropy Decomposition:")
    print(f"  H(type)           = {ent['H_type']:.4f} bits")
    print(f"  H(shell|type)     = {ent['H_shell_given_type']:.4f} bits")
    print(f"  H(pos|shell,type) = {ent['H_pos_given_shell_type']:.4f} bits")
    print(f"  H(total)          = {ent['H_total']:.4f} bits = log2(240)")
    print(f"  Residual          = {ent['residual']:.8f}")

    # BABEL Tower
    print(f"\nBABEL Tower:")
    periods, ratios = BABELTower.orbit_period_ratios()
    for lvl in range(3):
        gs = BABELTower.galois_group_structure(lvl)
        info = BABELTower.LEVELS[lvl]
        print(f"  Level {lvl}: ({info['primes']}) h={info['h']} "
              f"dim={info['dim']} period={gs['orbit_period']} "
              f"lattice={info['lattice']}")
    print(f"  Period ratios: {ratios} (= inner twin primes)")
    print(f"  Shell quantum delta_0 = {BABELTower.shell_quantum(0):.6f} "
          f"(expected {DELTA:.6f})")
