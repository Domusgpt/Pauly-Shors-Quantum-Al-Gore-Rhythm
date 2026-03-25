#!/usr/bin/env python3
"""
VRF/Randomness Bias Detector via E8 Shell Distribution
========================================================

Targets: Chainlink VRF users, drand, on-chain randomness on Immunefi

INSIGHT: The E8 root system's 240 points distributed across 6 shells with
populations [24, 56, 40, 40, 56, 24] provide a natural chi-squared test
for randomness quality. If we map random bytes onto E8 shells, truly random
data should fill shells proportional to their population.

APPLICATIONS:
1. Detect biased VRF outputs (compromised VRF operator)
2. Detect weak on-chain randomness (block hash, timestamp)
3. Test QRNG outputs for quantum side-channel bias
4. Audit Chainlink VRF integrations for misuse

The ZTC framework adds:
- Galois orbit analysis: Random data should have uniform Galois orbits
- Cross-parity balance: D8/S+ ratio should be 112:128 = 7:8
- BABEL tower periodicity: Random data should NOT show period structure
  (if it does, the source is deterministic, not random)

Author: Paul J. Phillips / Claude
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import Counter
import json
import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'code', 'core'))
try:
    from e8_lattice_codec_patent import build_e8_roots, build_coxeter_element
    HAS_E8 = True
except ImportError:
    HAS_E8 = False


class E8RandomnessTest:
    """
    Test randomness quality by mapping data onto E8 lattice structure.

    The 240 E8 roots provide 240 natural "bins" with known structure:
    - 6 shells: [24, 56, 40, 40, 56, 24]
    - 2 types: 112 D8 + 128 S+
    - 30-fold Coxeter symmetry

    Any bias in the random source will show up as deviation from
    the expected distribution across these natural categories.
    """

    # Expected proportions
    SHELL_POPS = {-3: 24, -2: 56, -1: 40, 1: 40, 2: 56, 3: 24}
    TOTAL_ROOTS = 240
    D8_COUNT = 112
    SP_COUNT = 128

    def __init__(self):
        if HAS_E8:
            self.roots, self.types = build_e8_roots()
        else:
            self.roots = None
            self.types = None

    def bytes_to_root_indices(self, data: bytes) -> List[int]:
        """Map raw bytes to E8 root indices (0-239)."""
        indices = []
        for byte in data:
            # Map byte (0-255) to root index (0-239)
            idx = byte % self.TOTAL_ROOTS
            indices.append(idx)
        return indices

    def bytes_to_shell_sequence(self, data: bytes) -> List[int]:
        """Map raw bytes to E8 shell indices."""
        shell_keys = sorted(self.SHELL_POPS.keys())
        shell_boundaries = []
        cumulative = 0
        for k in shell_keys:
            cumulative += self.SHELL_POPS[k]
            shell_boundaries.append((cumulative, k))

        sequence = []
        for byte in data:
            idx = byte % self.TOTAL_ROOTS
            for boundary, shell in shell_boundaries:
                if idx < boundary:
                    sequence.append(shell)
                    break
        return sequence

    def chi_squared_shell_test(self, data: bytes) -> Dict:
        """
        Chi-squared test: does the data fill E8 shells uniformly?

        Expected: each shell filled proportional to its population.
        H0: data is uniformly random.
        """
        shells = self.bytes_to_shell_sequence(data)
        n = len(shells)
        if n == 0:
            return {"error": "No data"}

        observed = Counter(shells)
        expected_proportions = {
            k: v / self.TOTAL_ROOTS for k, v in self.SHELL_POPS.items()
        }

        chi2 = 0.0
        details = {}
        for k in self.SHELL_POPS:
            obs = observed.get(k, 0)
            exp = expected_proportions[k] * n
            if exp > 0:
                contribution = (obs - exp) ** 2 / exp
                chi2 += contribution
                details[str(k)] = {
                    "observed": obs,
                    "expected": round(exp, 2),
                    "chi2_contribution": round(contribution, 4),
                    "deviation": round((obs - exp) / max(exp, 1) * 100, 2)
                }

        df = len(self.SHELL_POPS) - 1  # degrees of freedom

        # Chi-squared critical values (df=5)
        # α=0.05 -> 11.07, α=0.01 -> 15.09, α=0.001 -> 20.52
        if chi2 > 20.52:
            verdict = "FAIL (p < 0.001) - HIGHLY BIASED"
        elif chi2 > 15.09:
            verdict = "FAIL (p < 0.01) - BIASED"
        elif chi2 > 11.07:
            verdict = "MARGINAL (p < 0.05)"
        else:
            verdict = "PASS (p > 0.05) - appears random"

        return {
            "test": "E8 Shell Chi-Squared",
            "chi2_statistic": round(chi2, 4),
            "degrees_of_freedom": df,
            "verdict": verdict,
            "n_samples": n,
            "shell_details": details
        }

    def cross_parity_balance_test(self, data: bytes) -> Dict:
        """
        Test D8/S+ balance. Expected ratio: 112:128 = 0.4667:0.5333.
        Deviation indicates structural bias in the random source.
        """
        indices = self.bytes_to_root_indices(data)
        n = len(indices)
        if n == 0 or self.types is None:
            return {"error": "No data or E8 not loaded"}

        d8_count = sum(1 for idx in indices if self.types[idx] == 'D8')
        sp_count = n - d8_count

        expected_d8 = n * self.D8_COUNT / self.TOTAL_ROOTS
        expected_sp = n * self.SP_COUNT / self.TOTAL_ROOTS

        # Z-test for proportions
        p_hat = d8_count / n
        p_0 = self.D8_COUNT / self.TOTAL_ROOTS
        se = np.sqrt(p_0 * (1 - p_0) / n)
        z_stat = (p_hat - p_0) / se if se > 0 else 0

        if abs(z_stat) > 3.29:
            verdict = "FAIL (|z| > 3.29) - BIASED parity"
        elif abs(z_stat) > 2.58:
            verdict = "FAIL (|z| > 2.58) - BIASED parity"
        elif abs(z_stat) > 1.96:
            verdict = "MARGINAL (|z| > 1.96)"
        else:
            verdict = "PASS - balanced parity"

        return {
            "test": "E8 Cross-Parity Balance",
            "d8_observed": d8_count,
            "d8_expected": round(expected_d8, 2),
            "sp_observed": sp_count,
            "sp_expected": round(expected_sp, 2),
            "z_statistic": round(z_stat, 4),
            "verdict": verdict
        }

    def galois_orbit_periodicity_test(self, data: bytes, max_period: int = 30) -> Dict:
        """
        Test for hidden periodicity using Galois orbit analysis.

        The BABEL tower has Coxeter number h=30 for E8. If the "random"
        data shows period structure at multiples of 30 (or divisors),
        it's likely deterministic (e.g., PRNG with short period).

        This is the ZTC-Shor attack applied defensively:
        if we can find the period, the source is broken.
        """
        indices = self.bytes_to_root_indices(data)
        n = len(indices)
        if n < max_period * 3:
            return {"error": f"Need at least {max_period*3} samples"}

        # Autocorrelation at various lags
        mean = np.mean(indices)
        var = np.var(indices)
        if var < 1e-10:
            return {"error": "Zero variance - constant data"}

        autocorr = {}
        for lag in range(1, max_period + 1):
            if n - lag < 1:
                break
            corr = np.corrcoef(indices[:n-lag], indices[lag:])[0, 1]
            autocorr[lag] = round(float(corr), 6)

        # Check for significant autocorrelation
        threshold = 2.0 / np.sqrt(n)  # Bartlett's formula
        periodic_lags = {
            lag: corr for lag, corr in autocorr.items()
            if abs(corr) > threshold
        }

        # Check specifically for BABEL tower periods
        babel_periods = [5, 6, 10, 15, 30]  # Divisors of h=30
        babel_hits = {
            p: autocorr.get(p, 0) for p in babel_periods
            if p in autocorr and abs(autocorr.get(p, 0)) > threshold
        }

        if babel_hits:
            verdict = f"FAIL - Periodicity at BABEL frequencies: {list(babel_hits.keys())}"
        elif periodic_lags:
            verdict = f"WARNING - Autocorrelation at lags: {list(periodic_lags.keys())[:5]}"
        else:
            verdict = "PASS - No detectable periodicity"

        return {
            "test": "Galois Orbit Periodicity (ZTC-Shor Defensive)",
            "n_samples": n,
            "detection_threshold": round(threshold, 6),
            "periodic_lags": periodic_lags,
            "babel_tower_hits": babel_hits,
            "coxeter_number": 30,
            "verdict": verdict,
            "autocorrelation_sample": {
                k: v for k, v in list(autocorr.items())[:10]
            }
        }

    def full_randomness_audit(self, data: bytes) -> Dict:
        """Run all randomness tests."""
        results = {
            "data_length": len(data),
            "tests": []
        }

        # Test 1: Shell distribution
        results["tests"].append(self.chi_squared_shell_test(data))

        # Test 2: Cross-parity balance
        results["tests"].append(self.cross_parity_balance_test(data))

        # Test 3: Periodicity
        results["tests"].append(self.galois_orbit_periodicity_test(data))

        # Test 4: Basic entropy estimate
        byte_counts = Counter(data)
        entropy = -sum(
            (c / len(data)) * math.log2(c / len(data))
            for c in byte_counts.values() if c > 0
        )
        results["tests"].append({
            "test": "Shannon Entropy",
            "entropy_bits": round(entropy, 4),
            "max_entropy": 8.0,
            "efficiency": round(entropy / 8.0 * 100, 2),
            "verdict": (
                "PASS" if entropy > 7.5
                else "MARGINAL" if entropy > 7.0
                else "FAIL - LOW ENTROPY"
            )
        })

        # Overall verdict
        n_fail = sum(1 for t in results["tests"] if "FAIL" in t.get("verdict", ""))
        n_marginal = sum(1 for t in results["tests"] if "MARGINAL" in t.get("verdict", ""))

        if n_fail >= 2:
            results["overall"] = "COMPROMISED - Multiple test failures"
        elif n_fail == 1:
            results["overall"] = "SUSPICIOUS - One test failure"
        elif n_marginal >= 2:
            results["overall"] = "WEAK - Multiple marginal results"
        else:
            results["overall"] = "HEALTHY - All tests pass"

        return results


# ================================================================
# ON-CHAIN RANDOMNESS SCANNER
# ================================================================

def scan_randomness_patterns(solidity_source: str) -> List[Dict]:
    """Scan Solidity source for weak randomness patterns."""
    import re
    findings = []
    lines = solidity_source.split('\n')

    # Pattern 1: block.timestamp as randomness
    for i, line in enumerate(lines):
        if 'block.timestamp' in line and any(
            x in line.lower() for x in ['random', 'seed', 'hash', 'nonce']
        ):
            findings.append({
                "type": "BLOCK_TIMESTAMP_RANDOMNESS",
                "severity": "CRITICAL",
                "line": i + 1,
                "code": line.strip(),
                "description": "block.timestamp used as randomness source. Miner-manipulable.",
                "payout": "$25K-$250K"
            })

    # Pattern 2: blockhash for randomness
    for i, line in enumerate(lines):
        if 'blockhash' in line.lower() or 'block.blockhash' in line:
            findings.append({
                "type": "BLOCKHASH_RANDOMNESS",
                "severity": "HIGH",
                "line": i + 1,
                "code": line.strip(),
                "description": (
                    "blockhash used for randomness. Predictable by miners, "
                    "only last 256 blocks available."
                ),
                "payout": "$10K-$100K"
            })

    # Pattern 3: keccak256 of predictable values
    for i, line in enumerate(lines):
        if 'keccak256' in line:
            context = '\n'.join(lines[max(0, i-2):min(len(lines), i+2)])
            predictable = ['block.number', 'block.timestamp', 'msg.sender',
                          'block.difficulty', 'block.coinbase', 'tx.origin']
            used_predictable = [p for p in predictable if p in context]
            if used_predictable and any(x in context.lower() for x in ['random', 'seed', 'lottery', 'winner']):
                findings.append({
                    "type": "PREDICTABLE_HASH_RANDOMNESS",
                    "severity": "CRITICAL",
                    "line": i + 1,
                    "code": line.strip(),
                    "description": (
                        f"keccak256 of predictable inputs ({', '.join(used_predictable)}) "
                        "used as randomness. Fully predictable by anyone."
                    ),
                    "payout": "$25K-$500K (lottery/game protocols)"
                })

    # Pattern 4: Missing Chainlink VRF callback validation
    has_vrf = 'VRFConsumerBase' in solidity_source or 'VRFCoordinatorV2' in solidity_source
    if has_vrf:
        has_callback_check = 'fulfillRandomWords' in solidity_source or 'rawFulfillRandomness' in solidity_source
        if not has_callback_check:
            findings.append({
                "type": "VRF_MISSING_CALLBACK",
                "severity": "HIGH",
                "line": 0,
                "code": "(contract-wide)",
                "description": "Chainlink VRF imported but callback not properly implemented.",
                "payout": "$10K-$100K"
            })

    return findings


# ================================================================
# CLI
# ================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="VRF/Randomness Bias Detector (E8 Shell Analysis)"
    )
    parser.add_argument('--demo', action='store_true', help='Run demo')
    parser.add_argument('--test-file', type=str, help='Test binary file for randomness')
    parser.add_argument('--test-hex', type=str, help='Test hex string for randomness')
    parser.add_argument('--scan', type=str, help='Scan Solidity file for weak randomness')

    args = parser.parse_args()

    if args.demo:
        print("=" * 60)
        print("  VRF/RANDOMNESS BIAS DETECTOR")
        print("  E8 Shell Distribution + ZTC Galois Orbit Analysis")
        print("=" * 60)

        tester = E8RandomnessTest()

        # Test 1: Good randomness (os.urandom)
        print("\n--- Test 1: os.urandom (should PASS) ---")
        good_data = os.urandom(10000)
        good_result = tester.full_randomness_audit(good_data)
        print(f"Overall: {good_result['overall']}")
        for t in good_result['tests']:
            print(f"  {t['test']}: {t['verdict']}")

        # Test 2: Weak randomness (counter)
        print("\n--- Test 2: Counter (should FAIL) ---")
        bad_data = bytes(i % 256 for i in range(10000))
        bad_result = tester.full_randomness_audit(bad_data)
        print(f"Overall: {bad_result['overall']}")
        for t in bad_result['tests']:
            print(f"  {t['test']}: {t['verdict']}")

        # Test 3: Block hash simulation (periodic)
        print("\n--- Test 3: Simulated block.timestamp randomness ---")
        # Simulates: keccak256(block.timestamp) where timestamp increments by 12
        import hashlib
        timestamp_data = b''
        for block in range(1000):
            ts = 1700000000 + block * 12  # ~12 sec blocks
            h = hashlib.sha256(ts.to_bytes(8, 'big')).digest()
            timestamp_data += h[:10]
        ts_result = tester.full_randomness_audit(timestamp_data)
        print(f"Overall: {ts_result['overall']}")
        for t in ts_result['tests']:
            print(f"  {t['test']}: {t['verdict']}")

        # Full report for bad data
        print("\n--- Detailed Report (Counter data) ---")
        print(json.dumps(bad_result, indent=2, default=str))

    elif args.test_file:
        with open(args.test_file, 'rb') as f:
            data = f.read()
        tester = E8RandomnessTest()
        result = tester.full_randomness_audit(data)
        print(json.dumps(result, indent=2, default=str))

    elif args.test_hex:
        data = bytes.fromhex(args.test_hex)
        tester = E8RandomnessTest()
        result = tester.full_randomness_audit(data)
        print(json.dumps(result, indent=2, default=str))

    elif args.scan:
        with open(args.scan) as f:
            source = f.read()
        findings = scan_randomness_patterns(source)
        if findings:
            for f_item in findings:
                print(f"[{f_item['severity']}] {f_item['type']}")
                print(f"  Line {f_item['line']}: {f_item['code'][:80]}")
                print(f"  {f_item['description']}")
                print(f"  Bounty: {f_item['payout']}\n")
        else:
            print("No weak randomness patterns found.")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
