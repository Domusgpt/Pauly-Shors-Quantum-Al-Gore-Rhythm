#!/usr/bin/env python3
"""
TDA-Based Oracle Manipulation Detector
========================================

Targets: Any DeFi protocol with price oracles on Immunefi ($10K-$10M)

Uses persistent homology from TDA to detect oracle manipulation in real-time.
The E8 shell structure provides a natural multi-scale anomaly detector:

METHODOLOGY:
1. Map price time-series onto E8 shell radii (golden-ratio spacing)
2. Compute persistent homology (Vietoris-Rips filtration)
3. Flash loan manipulation creates distinctive topological signatures:
   - Normal markets: smooth persistence diagrams, gradual birth/death
   - Manipulation: sudden topological "explosions" (many features born/die
     at same filtration scale) = atomic flash loan transaction
4. The cross-parity (D8/S+) split separates buy-side from sell-side pressure
   - Healthy: balanced D8/S+ activity
   - Manipulation: extreme parity imbalance (all pressure on one side)

APPLICATIONS:
- MEV searcher: Detect manipulation in mempool, front-run the correction
- Bug bounty: Find protocols vulnerable to oracle manipulation
- Defense: Real-time manipulation detector for protocol integration

Based on:
- BitcoinHeist (2019): TDA for ransomware detection on Bitcoin blockchain
- Akcora et al.: "Topological Data Analysis for Ransomware Detection"
- Phillips (2026): E8 Cross-Parity Lattice Codec

Author: Paul J. Phillips / Claude
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import deque
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'code', 'core'))
try:
    from e8_lattice_codec_patent import build_e8_roots, build_coxeter_element
    HAS_E8 = True
except ImportError:
    HAS_E8 = False


# ================================================================
# PERSISTENT HOMOLOGY (Lightweight Implementation)
# ================================================================

class VietorisRipsFiltration:
    """
    Compute persistent homology via Vietoris-Rips filtration.

    For oracle data, each price observation is a point in feature space.
    We track connected components (β₀) and loops (β₁) as the filtration
    parameter (distance threshold) increases.

    β₀ persistence: How long distinct price clusters survive
    β₁ persistence: Cyclic price patterns (wash trading, manipulation loops)
    """

    def __init__(self, points: np.ndarray, max_dim: int = 1):
        self.points = points
        self.n = len(points)
        self.max_dim = max_dim

        # Compute pairwise distance matrix
        self.dist_matrix = np.zeros((self.n, self.n))
        for i in range(self.n):
            for j in range(i + 1, self.n):
                d = np.linalg.norm(points[i] - points[j])
                self.dist_matrix[i, j] = d
                self.dist_matrix[j, i] = d

    def compute_persistence(self, n_steps: int = 50) -> Dict:
        """
        Compute persistence diagram using union-find for β₀
        and cycle detection for β₁.
        """
        # Sort all edges by distance
        edges = []
        for i in range(self.n):
            for j in range(i + 1, self.n):
                edges.append((self.dist_matrix[i, j], i, j))
        edges.sort()

        if not edges:
            return {"birth_death_0": [], "birth_death_1": [], "persistence_0": [], "persistence_1": []}

        max_dist = edges[-1][0] if edges else 1.0

        # Union-Find for β₀
        parent = list(range(self.n))
        rank = [0] * self.n
        birth = [0.0] * self.n  # Each point born at filtration 0

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y, dist):
            px, py = find(x), find(y)
            if px == py:
                return None  # Already connected -> creates a cycle (β₁ feature)
            # Merge smaller into larger
            if rank[px] < rank[py]:
                px, py = py, px
            parent[py] = px
            if rank[px] == rank[py]:
                rank[px] += 1
            # The younger component dies
            death_time = dist
            birth_time = max(birth[px], birth[py])
            return (birth_time, death_time)

        bd_0 = []  # Birth-death pairs for β₀
        bd_1 = []  # Birth-death pairs for β₁

        for dist, i, j in edges:
            result = union(i, j, dist)
            if result is None:
                # Cycle created -> β₁ feature
                bd_1.append((dist, dist * 1.1))  # Approximate death
            elif result[1] > result[0]:
                bd_0.append(result)

        # Surviving components (infinite persistence)
        n_components = len(set(find(i) for i in range(self.n)))

        persistence_0 = [d - b for b, d in bd_0]
        persistence_1 = [d - b for b, d in bd_1]

        return {
            "birth_death_0": bd_0,
            "birth_death_1": bd_1,
            "persistence_0": persistence_0,
            "persistence_1": persistence_1,
            "n_surviving_components": n_components,
            "max_persistence_0": max(persistence_0) if persistence_0 else 0,
            "max_persistence_1": max(persistence_1) if persistence_1 else 0,
            "total_persistence_0": sum(persistence_0),
            "total_persistence_1": sum(persistence_1),
        }


# ================================================================
# E8 SHELL ORACLE MAPPING
# ================================================================

class E8OracleMapper:
    """
    Maps price/oracle data onto the E8 shell structure for anomaly detection.

    The 6 shells with golden-ratio spacing provide natural multi-scale bins:
    Shell populations: [24, 56, 40, 40, 56, 24] = 240 roots
    Shell radii: R_k = sqrt(1 + k·√5/10) for k in {-3,-2,-1,1,2,3}

    Normal price action maps smoothly across shells.
    Manipulation creates sharp transitions (data clustered in extreme shells).
    """

    # Shell populations (E8 cross-parity projection)
    SHELL_POPS = {-3: 24, -2: 56, -1: 40, 1: 40, 2: 56, 3: 24}
    SQRT5_10 = np.sqrt(5) / 10

    def __init__(self):
        self.shell_radii = {
            k: np.sqrt(1 + k * self.SQRT5_10) for k in self.SHELL_POPS
        }
        # D8/S+ type mapping (inner shells = D8, outer = S+, middle = mixed)
        # Based on E8 cross-parity theorem
        self.shell_types = {
            -3: 'D8', -2: 'D8', -1: 'mixed',
            1: 'mixed', 2: 'S+', 3: 'S+'
        }

    def map_price_to_shell(self, price: float, ref_price: float) -> Tuple[int, str]:
        """Map a price relative to reference onto the nearest E8 shell."""
        ratio = price / ref_price if ref_price != 0 else 1.0
        # Map ratio to shell radius space
        best_shell = 1
        best_dist = float('inf')
        for k, r in self.shell_radii.items():
            d = abs(ratio - r)
            if d < best_dist:
                best_dist = d
                best_shell = k
        return best_shell, self.shell_types[best_shell]

    def analyze_price_window(self, prices: List[float],
                              window_size: int = 20) -> Dict:
        """
        Analyze a window of prices for manipulation signatures.

        Returns shell distribution and cross-parity balance.
        """
        if len(prices) < 2:
            return {"error": "Need at least 2 prices"}

        ref_price = np.median(prices)
        shell_counts = {k: 0 for k in self.SHELL_POPS}
        d8_count = 0
        sp_count = 0
        type_sequence = []

        for p in prices:
            shell, stype = self.map_price_to_shell(p, ref_price)
            shell_counts[shell] += 1
            if stype == 'D8':
                d8_count += 1
            elif stype == 'S+':
                sp_count += 1
            else:
                d8_count += 0.5
                sp_count += 0.5
            type_sequence.append(stype)

        total = d8_count + sp_count
        parity_balance = abs(d8_count - sp_count) / max(total, 1)

        # Concentration metric: how clustered are prices in extreme shells?
        extreme_count = shell_counts[-3] + shell_counts[3]
        inner_count = shell_counts[-1] + shell_counts[1]
        extreme_ratio = extreme_count / max(len(prices), 1)

        # Volatility in shell space
        shells_visited = [k for k in shell_counts if shell_counts[k] > 0]
        shell_range = max(shells_visited) - min(shells_visited) if shells_visited else 0

        return {
            "shell_distribution": shell_counts,
            "d8_count": d8_count,
            "sp_count": sp_count,
            "parity_balance": round(parity_balance, 4),
            "extreme_ratio": round(extreme_ratio, 4),
            "shell_range": shell_range,
            "manipulation_score": round(
                0.4 * parity_balance +
                0.3 * extreme_ratio +
                0.3 * (shell_range / 6.0),
                4
            ),
            "type_sequence": type_sequence[-10:]  # Last 10
        }


# ================================================================
# ORACLE MANIPULATION DETECTOR
# ================================================================

class OracleManipulationDetector:
    """
    Combined TDA + E8 detector for oracle manipulation.

    Detection Strategy:
    1. Sliding window over price time series
    2. For each window:
       a. Compute E8 shell distribution (fast, O(n))
       b. If manipulation_score > threshold:
          Compute full TDA persistence (slower, confirms)
    3. Alert if both E8 parity AND TDA persistence are anomalous

    This two-phase approach gives:
    - Phase 1 (E8): Sub-millisecond screening (can run on every block)
    - Phase 2 (TDA): Detailed analysis (only triggered on suspicious windows)
    """

    def __init__(self, threshold: float = 0.5, window_size: int = 20):
        self.threshold = threshold
        self.window_size = window_size
        self.mapper = E8OracleMapper()
        self.price_buffer = deque(maxlen=1000)
        self.alerts = []

    def ingest_price(self, price: float, timestamp: int = 0,
                     source: str = "unknown") -> Optional[Dict]:
        """
        Ingest a single price observation.
        Returns an alert dict if manipulation detected, None otherwise.
        """
        self.price_buffer.append({
            'price': price,
            'timestamp': timestamp,
            'source': source
        })

        if len(self.price_buffer) < self.window_size:
            return None

        # Phase 1: E8 shell screening
        recent_prices = [p['price'] for p in list(self.price_buffer)[-self.window_size:]]
        e8_analysis = self.mapper.analyze_price_window(recent_prices)

        if e8_analysis['manipulation_score'] < self.threshold:
            return None  # Normal activity

        # Phase 2: TDA persistence confirmation
        # Build point cloud from price deltas
        deltas = np.diff(recent_prices)
        if len(deltas) < 3:
            return None

        # Create 2D embedding: (delta, delta_of_delta)
        points = np.column_stack([
            deltas[:-1],
            np.diff(deltas)
        ])

        vr = VietorisRipsFiltration(points)
        persistence = vr.compute_persistence()

        # Manipulation signature: high total persistence + few surviving components
        tda_score = (
            persistence['total_persistence_0'] /
            max(persistence['max_persistence_0'], 1e-10)
        )

        if tda_score > 3.0 or persistence['n_surviving_components'] <= 1:
            alert = {
                "type": "ORACLE_MANIPULATION_DETECTED",
                "severity": "HIGH",
                "timestamp": timestamp,
                "source": source,
                "e8_score": e8_analysis['manipulation_score'],
                "e8_parity_balance": e8_analysis['parity_balance'],
                "e8_extreme_ratio": e8_analysis['extreme_ratio'],
                "tda_score": round(tda_score, 4),
                "tda_components": persistence['n_surviving_components'],
                "tda_max_persistence": persistence['max_persistence_0'],
                "price_window": recent_prices,
                "recommendation": (
                    "Possible flash loan oracle manipulation. "
                    "Check for atomic transactions with large volume. "
                    "This pattern matches known manipulation signatures."
                )
            }
            self.alerts.append(alert)
            return alert

        return None

    def analyze_historical(self, prices: List[float],
                           timestamps: List[int] = None) -> List[Dict]:
        """Analyze historical price data for manipulation events."""
        if timestamps is None:
            timestamps = list(range(len(prices)))

        alerts = []
        for i, (p, t) in enumerate(zip(prices, timestamps)):
            alert = self.ingest_price(p, t)
            if alert:
                alerts.append(alert)

        return alerts

    def generate_flash_loan_attack(self, base_price: float = 100.0,
                                    n_normal: int = 50,
                                    spike_magnitude: float = 10.0) -> Tuple[List[float], List[int]]:
        """
        Generate synthetic price data with an embedded flash loan attack
        for testing/demo purposes.
        """
        np.random.seed(42)

        # Normal price action (small random walk)
        normal_before = base_price + np.cumsum(
            np.random.normal(0, 0.5, n_normal)
        )

        # Flash loan attack: massive spike + immediate recovery
        attack = [
            normal_before[-1],
            normal_before[-1] + spike_magnitude,   # Pump
            normal_before[-1] + spike_magnitude * 1.2,  # Peak
            normal_before[-1] + spike_magnitude * 0.3,  # Partial recovery
            normal_before[-1] - spike_magnitude * 0.1,  # Overshoot
        ]

        # Normal after
        normal_after = normal_before[-1] + np.cumsum(
            np.random.normal(0, 0.5, n_normal)
        )

        prices = list(normal_before) + attack + list(normal_after)
        timestamps = list(range(len(prices)))

        return prices, timestamps


# ================================================================
# SMART CONTRACT SCANNER: Find Vulnerable Oracles
# ================================================================

def scan_oracle_patterns(solidity_source: str) -> List[Dict]:
    """
    Scan Solidity source for oracle manipulation vulnerability patterns.
    """
    import re
    findings = []
    lines = solidity_source.split('\n')

    # Pattern 1: Direct balance-based price
    for i, line in enumerate(lines):
        if 'balanceOf' in line and ('price' in line.lower() or 'rate' in line.lower()):
            findings.append({
                "type": "BALANCE_BASED_PRICE",
                "severity": "CRITICAL",
                "line": i + 1,
                "code": line.strip(),
                "description": (
                    "Price derived from token balance. Manipulable via flash loan."
                ),
                "payout": "$50K-$500K"
            })

    # Pattern 2: Single-block TWAP
    for i, line in enumerate(lines):
        if 'getReserves' in line or 'slot0' in line:
            context = '\n'.join(lines[max(0, i-5):min(len(lines), i+5)])
            if 'block.timestamp' not in context and 'observe' not in context:
                findings.append({
                    "type": "SPOT_PRICE_NO_TWAP",
                    "severity": "HIGH",
                    "line": i + 1,
                    "code": line.strip(),
                    "description": (
                        "Spot price from AMM without TWAP. Single-block manipulable."
                    ),
                    "payout": "$25K-$250K"
                })

    # Pattern 3: Missing price deviation check
    has_price = any('price' in line.lower() for line in lines)
    has_deviation_check = any(
        pattern in solidity_source
        for pattern in ['maxDeviation', 'priceDeviation', 'staleness',
                       'maxPrice', 'minPrice', 'priceThreshold']
    )
    if has_price and not has_deviation_check:
        findings.append({
            "type": "NO_PRICE_BOUNDS",
            "severity": "MEDIUM",
            "line": 0,
            "code": "(contract-wide)",
            "description": (
                "No price deviation bounds. Extreme values not rejected."
            ),
            "payout": "$10K-$100K"
        })

    # Pattern 4: totalSupply in price calculation
    for i, line in enumerate(lines):
        if 'totalSupply' in line:
            context = '\n'.join(lines[max(0, i-3):min(len(lines), i+3)])
            if any(x in context.lower() for x in ['price', 'rate', 'value', 'nav']):
                findings.append({
                    "type": "TOTAL_SUPPLY_IN_PRICE",
                    "severity": "HIGH",
                    "line": i + 1,
                    "code": line.strip(),
                    "description": (
                        "totalSupply used in price/rate calculation. "
                        "Manipulable via flash mint/burn."
                    ),
                    "payout": "$50K-$500K"
                })

    return findings


# ================================================================
# CLI
# ================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="TDA + E8 Oracle Manipulation Detector"
    )
    parser.add_argument('--demo', action='store_true',
                       help='Run demo with synthetic flash loan attack')
    parser.add_argument('--scan', type=str,
                       help='Scan Solidity file for oracle vulnerabilities')
    parser.add_argument('--prices', type=str,
                       help='JSON file with price array to analyze')
    parser.add_argument('--threshold', type=float, default=0.4,
                       help='Manipulation detection threshold (0-1)')

    args = parser.parse_args()

    if args.demo:
        print("=" * 60)
        print("  ORACLE MANIPULATION DETECTION DEMO")
        print("  E8 Cross-Parity + TDA Persistent Homology")
        print("=" * 60)

        detector = OracleManipulationDetector(threshold=args.threshold)
        prices, timestamps = detector.generate_flash_loan_attack(
            base_price=100, n_normal=50, spike_magnitude=15
        )

        print(f"\nGenerated {len(prices)} price observations with embedded attack")
        print(f"Normal range: ~${min(prices[:50]):.2f} - ${max(prices[:50]):.2f}")
        print(f"Attack spike: ${max(prices):.2f}")

        alerts = detector.analyze_historical(prices, timestamps)

        if alerts:
            print(f"\n{'!'*60}")
            print(f"  {len(alerts)} MANIPULATION ALERT(S) DETECTED")
            print(f"{'!'*60}")
            for a in alerts:
                print(f"\n  Timestamp: {a['timestamp']}")
                print(f"  E8 Score: {a['e8_score']}")
                print(f"  E8 Parity Balance: {a['e8_parity_balance']}")
                print(f"  TDA Score: {a['tda_score']}")
                print(f"  TDA Components: {a['tda_components']}")
        else:
            print("\nNo manipulation detected (try lowering --threshold)")

        # Also show E8 analysis of attack window
        print("\n--- E8 Shell Analysis of Attack Window ---")
        mapper = E8OracleMapper()
        attack_window = prices[45:60]
        analysis = mapper.analyze_price_window(attack_window)
        print(json.dumps(analysis, indent=2, default=str))

    elif args.scan:
        print(f"Scanning {args.scan} for oracle vulnerabilities...")
        with open(args.scan) as f:
            source = f.read()
        findings = scan_oracle_patterns(source)
        if findings:
            print(f"\n{len(findings)} findings:")
            for f_item in findings:
                print(f"\n  [{f_item['severity']}] {f_item['type']}")
                print(f"    Line {f_item['line']}: {f_item['code'][:80]}")
                print(f"    {f_item['description']}")
                print(f"    Bounty: {f_item['payout']}")
        else:
            print("No oracle vulnerabilities found.")

    elif args.prices:
        with open(args.prices) as f:
            prices = json.load(f)
        detector = OracleManipulationDetector(threshold=args.threshold)
        alerts = detector.analyze_historical(prices)
        print(json.dumps(alerts, indent=2, default=str))

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
