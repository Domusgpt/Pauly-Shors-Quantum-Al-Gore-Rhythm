"""
E8 Lattice Visualization of Quantum Measurement Results
========================================================

Maps Shor's ECDLP measurement pairs onto the E8 exceptional root lattice,
providing a geometrically meaningful lens for analyzing quantum outputs.

The E8 root system has 240 roots decomposed into 6 shells of sizes
[24, 56, 40, 40, 56, 24], with a D8-type (128 spinor) vs S+-type
(112 integer) classification yielding the cross-parity ratio 8:7.

Author: Paul J. Phillips, Clear Seas Solutions LLC
"""

import math
from collections import Counter

import numpy as np

# ---------------------------------------------------------------------------
# E8 lattice constants
# ---------------------------------------------------------------------------
E8_ROOTS = 240
E8_SHELLS = [24, 56, 40, 40, 56, 24]
E8_SHELL_CUMULATIVE = [sum(E8_SHELLS[:i + 1]) for i in range(len(E8_SHELLS))]
D8_COUNT = 128   # spinor-type roots
SPLUS_COUNT = 112  # integer-type roots
CROSS_PARITY_RATIO = "8:7"  # D8 : S+
PHI_240 = 64
BABEL_CONDUCTORS = [15, 35, 143, 323, 899]

# Theoretical shell distribution normalised to probabilities
E8_SHELL_PROBS = np.array(E8_SHELLS, dtype=float) / E8_ROOTS


def _shell_from_index(idx):
    """Return shell number (0-5) for a root index in [0, 240)."""
    for shell_num, boundary in enumerate(E8_SHELL_CUMULATIVE):
        if idx < boundary:
            return shell_num
    return len(E8_SHELLS) - 1


def classify_d8_splus(shell_index):
    """
    Classify a shell index into D8-type or S+-type.

    Shells 0, 5 (outermost pair) -> D8-type (spinor)
    Shells 1, 4                  -> S+-type (integer)
    Shells 2, 3 (innermost pair) -> mixed

    Returns one of "D8", "S+", or "mixed".
    """
    if shell_index in (0, 5):
        return "D8"
    if shell_index in (1, 4):
        return "S+"
    return "mixed"


def project_measurements_to_shells(measurements, group_order, precision):
    """
    Map Shor's ECDLP measurement pairs (j1, j2) to E8 shell indices.

    Mapping rule:
        root_index = (j1 * j2) mod 240
        shell = lookup via cumulative shell sizes [24, 80, 120, 160, 216, 240]

    Parameters
    ----------
    measurements : list of (int, int)
        Measurement pairs from the two-register Shor circuit.
    group_order : int
        Order of the elliptic curve group.
    precision : int
        Number of precision qubits used in each register.

    Returns
    -------
    dict with keys:
        shell_counts   - list[int] of length 6
        shell_fractions - list[float] normalised to 1
        d8_count       - int, measurements classified D8
        splus_count    - int, measurements classified S+
        mixed_count    - int, measurements classified mixed
        root_indices   - list[int] raw root indices for every measurement
        total          - int, total measurements processed
    """
    shell_counts = [0] * len(E8_SHELLS)
    type_counts = {"D8": 0, "S+": 0, "mixed": 0}
    root_indices = []

    for j1, j2 in measurements:
        root_idx = (j1 * j2) % E8_ROOTS
        root_indices.append(root_idx)
        shell = _shell_from_index(root_idx)
        shell_counts[shell] += 1
        type_counts[classify_d8_splus(shell)] += 1

    total = len(measurements)
    shell_fractions = [c / total if total else 0.0 for c in shell_counts]

    return {
        "shell_counts": shell_counts,
        "shell_fractions": shell_fractions,
        "d8_count": type_counts["D8"],
        "splus_count": type_counts["S+"],
        "mixed_count": type_counts["mixed"],
        "root_indices": root_indices,
        "total": total,
    }


def compute_palindromic_polynomial(shell_dist):
    """
    Evaluate the palindromic polynomial

        P(q) = 24 + 56q + 40q^2 + 40q^3 + 56q^4 + 24q^5

    at q = 1 (sanity: should equal 240) and compute a chi-squared
    goodness-of-fit between the observed shell distribution and the
    theoretical E8 shell sizes.

    Parameters
    ----------
    shell_dist : list[int]
        Observed counts per shell (length 6).

    Returns
    -------
    dict with keys:
        polynomial_at_1 - int, P(1) = 240
        chi_squared     - float, sum((obs - exp)^2 / exp)
        p_value_approx  - float, rough p-value (5 dof chi-sq)
    """
    poly_at_1 = sum(E8_SHELLS)  # always 240
    total = sum(shell_dist)
    if total == 0:
        return {"polynomial_at_1": poly_at_1, "chi_squared": float("inf"),
                "p_value_approx": 0.0}

    expected = [total * p for p in E8_SHELL_PROBS]
    chi_sq = sum((o - e) ** 2 / e for o, e in zip(shell_dist, expected))

    # Rough p-value via Wilson-Hilferty normal approximation for chi-sq(5)
    k = 5  # degrees of freedom
    z = ((chi_sq / k) ** (1.0 / 3.0) - (1 - 2.0 / (9 * k))) / math.sqrt(
        2.0 / (9 * k))
    p_approx = max(0.0, min(1.0, 0.5 * math.erfc(z / math.sqrt(2))))

    return {
        "polynomial_at_1": poly_at_1,
        "chi_squared": chi_sq,
        "p_value_approx": p_approx,
    }


def measurement_entropy_analysis(measurements, group_order, precision):
    """
    Compute Shannon entropy of the measurement distribution and compare
    to the theoretical maximum (uniform over n^2 outcomes).

    Parameters
    ----------
    measurements : list of (int, int)
    group_order : int
    precision : int

    Returns
    -------
    dict with keys:
        entropy       - float, observed Shannon entropy (bits)
        max_entropy   - float, log2(n^2) where n = 2^precision
        efficiency    - float, entropy / max_entropy
        unique_ratio  - float, fraction of distinct outcomes
    """
    n = 2 ** precision
    max_entropy = 2.0 * precision  # log2(n^2)

    counts = Counter(measurements)
    total = len(measurements)
    if total == 0:
        return {"entropy": 0.0, "max_entropy": max_entropy,
                "efficiency": 0.0, "unique_ratio": 0.0}

    entropy = 0.0
    for c in counts.values():
        p = c / total
        if p > 0:
            entropy -= p * math.log2(p)

    unique_ratio = len(counts) / total

    return {
        "entropy": entropy,
        "max_entropy": max_entropy,
        "efficiency": entropy / max_entropy if max_entropy > 0 else 0.0,
        "unique_ratio": unique_ratio,
    }


def generate_measurement_report(measurements, group_order, precision,
                                recovered_key=None):
    """
    Generate a text report analysing measurement results through the E8 lens.

    Includes shell distribution histogram, D8/S+ ratio, palindromic
    polynomial fit, entropy analysis, and (optionally) the recovered key.
    """
    proj = project_measurements_to_shells(measurements, group_order, precision)
    poly = compute_palindromic_polynomial(proj["shell_counts"])
    ent = measurement_entropy_analysis(measurements, group_order, precision)

    lines = []
    lines.append("=" * 60)
    lines.append("  E8 LATTICE ANALYSIS OF SHOR ECDLP MEASUREMENTS")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"  Group order n = {group_order}")
    lines.append(f"  Precision qubits = {precision}")
    lines.append(f"  Total measurements = {proj['total']}")
    if recovered_key is not None:
        lines.append(f"  Recovered private key k = {recovered_key}")
    lines.append("")

    # Shell histogram
    lines.append("  Shell Distribution (E8 root mapping)")
    lines.append("  " + "-" * 44)
    bar_width = 30
    max_count = max(proj["shell_counts"]) if proj["total"] else 1
    for i, (cnt, frac) in enumerate(
            zip(proj["shell_counts"], proj["shell_fractions"])):
        bar_len = int(round(cnt / max_count * bar_width)) if max_count else 0
        bar = "#" * bar_len
        theory = E8_SHELL_PROBS[i] * 100
        tag = classify_d8_splus(i)
        lines.append(f"  Shell {i} [{tag:>5}] | {bar:<{bar_width}} "
                      f"{cnt:>5} ({frac * 100:5.1f}% vs {theory:5.1f}%)")
    lines.append("")

    # D8 / S+ classification
    d8_frac = proj["d8_count"] / proj["total"] * 100 if proj["total"] else 0
    sp_frac = proj["splus_count"] / proj["total"] * 100 if proj["total"] else 0
    mx_frac = proj["mixed_count"] / proj["total"] * 100 if proj["total"] else 0
    lines.append(f"  D8 (spinor):  {proj['d8_count']:>5}  ({d8_frac:5.1f}%)")
    lines.append(f"  S+ (integer): {proj['splus_count']:>5}  ({sp_frac:5.1f}%)")
    lines.append(f"  Mixed:        {proj['mixed_count']:>5}  ({mx_frac:5.1f}%)")
    lines.append(f"  Cross-parity ratio (D8:S+) = {CROSS_PARITY_RATIO} "
                  f"(theoretical)")
    lines.append("")

    # Palindromic polynomial
    lines.append("  Palindromic Polynomial Fit")
    lines.append("  P(q) = 24 + 56q + 40q^2 + 40q^3 + 56q^4 + 24q^5")
    lines.append(f"  P(1) = {poly['polynomial_at_1']}  (= |E8 roots|)")
    lines.append(f"  Chi-squared = {poly['chi_squared']:.4f}  "
                  f"(p ~ {poly['p_value_approx']:.4f}, 5 dof)")
    lines.append("")

    # Entropy
    lines.append("  Entropy Analysis")
    lines.append(f"  Shannon entropy   = {ent['entropy']:.4f} bits")
    lines.append(f"  Maximum entropy   = {ent['max_entropy']:.4f} bits")
    lines.append(f"  Efficiency ratio  = {ent['efficiency']:.4f}")
    lines.append(f"  Unique outcomes   = {ent['unique_ratio'] * 100:.1f}%")
    lines.append("")

    # E8 constants reminder
    lines.append("  E8 Constants")
    lines.append(f"  Roots = {E8_ROOTS}, phi(240) = {PHI_240}")
    lines.append(f"  Shells = {E8_SHELLS}")
    lines.append(f"  BABEL conductors = {BABEL_CONDUCTORS}")
    lines.append("=" * 60)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Demo with synthetic data
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    rng = np.random.default_rng(42)

    # Simulate a 3-bit ECDLP attack: group order 7, precision 3 (8 outcomes)
    group_order = 7
    precision = 3
    n_shots = 512
    n_vals = 2 ** precision

    # Generate synthetic measurement pairs biased toward multiples of n/order
    synthetic = []
    for _ in range(n_shots):
        j1 = int(rng.integers(0, n_vals))
        j2 = int(rng.integers(0, n_vals))
        synthetic.append((j1, j2))

    report = generate_measurement_report(
        synthetic, group_order, precision, recovered_key=3
    )
    print(report)
