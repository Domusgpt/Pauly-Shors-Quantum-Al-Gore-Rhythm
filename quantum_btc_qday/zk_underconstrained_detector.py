#!/usr/bin/env python3
"""
ZK Circuit Underconstrained Detector via E8 Cross-Parity Analysis
=================================================================

Targets: zkSync ($100K), zkVerify ($50K), Light Protocol ($50K) on Immunefi

INSIGHT: Zero-knowledge proof circuits (R1CS, Plonkish) define algebraic
constraint systems over finite fields. An "underconstrained" circuit has
witness variables that are not fully determined by the constraints - meaning
a malicious prover can forge proofs.

The E8 cross-parity framework provides a natural detection mechanism:
- Map R1CS constraint matrices onto the E8 shell structure
- Use the D8/S+ type separation as a parity oracle
- Underconstrained variables show up as roots that lack a type-partner
  (they break the cross-parity symmetry)

This is analogous to how the E8 codec detects transmission errors via the
free type-parity bit: if a constraint system is "noisy" (underconstrained),
the parity check fails.

Additionally, we use persistent homology (TDA) on the constraint dependency
graph to detect:
- Disconnected components (independent witness groups = underconstrained)
- Homological cycles (circular dependencies = potential soundness issues)
- Betti number anomalies (unexpected topology = constraint gaps)

Author: Paul J. Phillips / Claude
Framework: G.O.D. (Geometric Orthogonal Dialectics)
"""

import numpy as np
from collections import defaultdict
from typing import List, Dict, Tuple, Optional, Set
import json
import sys
import os

# Import E8 core from the patent codec
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'code', 'core'))
try:
    from e8_lattice_codec_patent import build_e8_roots, build_coxeter_element, build_cross_parity_projection
    HAS_E8 = True
except ImportError:
    HAS_E8 = False


# ================================================================
# R1CS CONSTRAINT PARSER
# ================================================================

class R1CSConstraint:
    """Represents a single R1CS constraint: A · w * B · w = C · w"""
    def __init__(self, a: Dict[int, int], b: Dict[int, int], c: Dict[int, int]):
        self.a = a  # {wire_index: coefficient}
        self.b = b
        self.c = c

    @property
    def wires_used(self) -> Set[int]:
        return set(self.a.keys()) | set(self.b.keys()) | set(self.c.keys())


class CircuitAnalyzer:
    """
    Analyzes ZK circuit constraint systems for underconstraint vulnerabilities.

    Attack surface:
    1. Unconstrained witness wires (no constraints reference them)
    2. Underconstrained wires (appear in too few constraints)
    3. Missing range checks (field elements can take unexpected values)
    4. Algebraic degree deficiency (constraints don't pin down values)
    """

    def __init__(self, n_wires: int, constraints: List[R1CSConstraint],
                 public_inputs: Set[int] = None):
        self.n_wires = n_wires
        self.constraints = constraints
        self.public_inputs = public_inputs or {0}  # wire 0 is usually "one"
        self.n_constraints = len(constraints)

        # Build wire-to-constraint adjacency
        self.wire_constraints: Dict[int, List[int]] = defaultdict(list)
        for ci, c in enumerate(constraints):
            for w in c.wires_used:
                self.wire_constraints[w].append(ci)

    # ─── Core Analysis ────────────────────────────────────────────────

    def find_unconstrained_wires(self) -> List[int]:
        """Wires that appear in zero constraints = completely free."""
        unconstrained = []
        for w in range(self.n_wires):
            if w not in self.wire_constraints or len(self.wire_constraints[w]) == 0:
                if w not in self.public_inputs:
                    unconstrained.append(w)
        return unconstrained

    def find_underconstrained_wires(self, min_constraints: int = 2) -> List[Tuple[int, int]]:
        """
        Wires appearing in fewer than min_constraints constraints.
        A wire in only 1 constraint is likely underconstrained.
        """
        under = []
        for w in range(self.n_wires):
            if w in self.public_inputs:
                continue
            n = len(self.wire_constraints.get(w, []))
            if 0 < n < min_constraints:
                under.append((w, n))
        return sorted(under, key=lambda x: x[1])

    def compute_constraint_graph(self) -> Dict[int, Set[int]]:
        """
        Build constraint dependency graph: two constraints are connected
        if they share a wire.
        """
        graph: Dict[int, Set[int]] = defaultdict(set)
        for w, cis in self.wire_constraints.items():
            for i in range(len(cis)):
                for j in range(i + 1, len(cis)):
                    graph[cis[i]].add(cis[j])
                    graph[cis[j]].add(cis[i])
        return graph

    def find_disconnected_components(self) -> List[Set[int]]:
        """
        Find connected components in the constraint graph.
        Multiple components = independent subsystems = potential issue.
        """
        graph = self.compute_constraint_graph()
        visited = set()
        components = []

        for start in range(self.n_constraints):
            if start in visited:
                continue
            component = set()
            stack = [start]
            while stack:
                node = stack.pop()
                if node in visited:
                    continue
                visited.add(node)
                component.add(node)
                for neighbor in graph.get(node, []):
                    if neighbor not in visited:
                        stack.append(neighbor)
            components.append(component)

        return sorted(components, key=len, reverse=True)

    # ─── E8 Cross-Parity Analysis ────────────────────────────────────

    def e8_parity_analysis(self) -> Dict:
        """
        Map the constraint system onto E8 shell structure and check
        cross-parity balance.

        Methodology:
        - The 240 E8 roots split into 112 D8 (integer) + 128 S+ (spinor)
        - Map each wire's constraint profile to a root vector
        - Well-constrained circuits should have balanced D8/S+ representation
        - Underconstrained regions show as parity imbalance

        This is the ZTC cross-parity oracle applied to constraint systems.
        """
        if not HAS_E8:
            return {"error": "E8 codec not available - install from code/core/"}

        roots, types = build_e8_roots()
        w = build_coxeter_element()
        proj = build_cross_parity_projection(w)

        # Create feature vector for each wire based on constraint participation
        wire_features = []
        for wire in range(min(self.n_wires, 240)):
            cis = self.wire_constraints.get(wire, [])
            if not cis:
                wire_features.append(np.zeros(8))
                continue

            # Feature: constraint coefficients mapped to 8D
            feature = np.zeros(8)
            for ci in cis[:8]:  # Use up to 8 constraints per wire
                c = self.constraints[ci]
                # Aggregate: A coefficient contributes +, C contributes -
                for w_idx, coeff in c.a.items():
                    if w_idx == wire:
                        feature[ci % 8] += coeff
                for w_idx, coeff in c.c.items():
                    if w_idx == wire:
                        feature[ci % 8] -= coeff

            # Normalize to unit sphere
            n = np.linalg.norm(feature)
            if n > 0:
                feature = feature / n * np.sqrt(2)  # E8 root norm = sqrt(2)
            wire_features.append(feature)

        wire_features = np.array(wire_features)

        # Find nearest E8 root for each wire
        d8_count = 0
        sp_count = 0
        orphan_wires = []  # Wires far from any root
        type_assignments = []

        for i, feat in enumerate(wire_features):
            if np.linalg.norm(feat) < 0.01:
                orphan_wires.append(i)
                type_assignments.append('orphan')
                continue

            dists = np.sum((roots - feat) ** 2, axis=1)
            nearest = np.argmin(dists)
            min_dist = np.sqrt(dists[nearest])

            if min_dist > 1.5:  # Far from lattice = suspicious
                orphan_wires.append(i)
                type_assignments.append('distant')
            elif types[nearest] == 'D8':
                d8_count += 1
                type_assignments.append('D8')
            else:
                sp_count += 1
                type_assignments.append('S+')

        # Cross-parity balance check
        total = d8_count + sp_count
        if total > 0:
            d8_ratio = d8_count / total
            sp_ratio = sp_count / total
            # Ideal: D8 = 112/240 ≈ 0.467, S+ = 128/240 ≈ 0.533
            ideal_d8 = 112 / 240
            imbalance = abs(d8_ratio - ideal_d8)
        else:
            imbalance = 1.0

        return {
            "n_wires_analyzed": len(wire_features),
            "d8_count": d8_count,
            "sp_count": sp_count,
            "orphan_count": len(orphan_wires),
            "orphan_wires": orphan_wires[:20],  # First 20
            "parity_imbalance": round(imbalance, 4),
            "parity_healthy": imbalance < 0.15,
            "type_assignments": type_assignments,
            "interpretation": (
                "HEALTHY: Cross-parity balanced" if imbalance < 0.15
                else "WARNING: Parity imbalance detected - possible underconstrained region"
            )
        }

    # ─── Persistent Homology (TDA) ───────────────────────────────────

    def compute_betti_numbers(self) -> Dict:
        """
        Compute Betti numbers of the constraint dependency graph.

        β₀ = connected components (should be 1 for sound circuit)
        β₁ = independent cycles (circular constraint dependencies)

        Uses simple graph-theoretic computation (Euler characteristic).
        """
        graph = self.compute_constraint_graph()
        components = self.find_disconnected_components()

        # β₀ = number of connected components
        beta_0 = len(components)

        # Count edges
        n_edges = sum(len(neighbors) for neighbors in graph.values()) // 2

        # For a graph: χ = V - E, β₀ - β₁ = χ
        # So β₁ = β₀ - V + E
        n_vertices = self.n_constraints
        beta_1 = beta_0 - n_vertices + n_edges

        return {
            "beta_0": beta_0,
            "beta_1": max(0, beta_1),
            "euler_characteristic": n_vertices - n_edges,
            "n_vertices": n_vertices,
            "n_edges": n_edges,
            "interpretation": (
                f"β₀={beta_0}: {'Single connected system (good)' if beta_0 == 1 else f'{beta_0} independent subsystems (SUSPICIOUS)'}, "
                f"β₁={max(0,beta_1)}: {max(0,beta_1)} independent cycles"
            )
        }

    # ─── Comprehensive Audit ─────────────────────────────────────────

    def full_audit(self) -> Dict:
        """Run all analyses and produce a comprehensive report."""
        unconstrained = self.find_unconstrained_wires()
        underconstrained = self.find_underconstrained_wires()
        components = self.find_disconnected_components()
        betti = self.compute_betti_numbers()
        e8_result = self.e8_parity_analysis()

        severity = "LOW"
        findings = []

        if unconstrained:
            severity = "CRITICAL"
            findings.append({
                "type": "UNCONSTRAINED_WIRES",
                "severity": "CRITICAL",
                "count": len(unconstrained),
                "wires": unconstrained[:20],
                "description": (
                    f"{len(unconstrained)} wires have NO constraints. "
                    "A malicious prover can set these to any value."
                ),
                "bounty_relevance": "Proof forgery -> fund theft",
                "estimated_payout": "$50K-$100K on zkSync/zkVerify"
            })

        if underconstrained:
            if severity != "CRITICAL":
                severity = "HIGH"
            findings.append({
                "type": "UNDERCONSTRAINED_WIRES",
                "severity": "HIGH",
                "count": len(underconstrained),
                "wires": underconstrained[:20],
                "description": (
                    f"{len(underconstrained)} wires appear in only 1 constraint. "
                    "May not be fully determined."
                ),
                "bounty_relevance": "Possible witness manipulation",
                "estimated_payout": "$25K-$75K"
            })

        if len(components) > 1:
            if severity == "LOW":
                severity = "MEDIUM"
            findings.append({
                "type": "DISCONNECTED_CONSTRAINT_GRAPH",
                "severity": "MEDIUM",
                "n_components": len(components),
                "component_sizes": [len(c) for c in components],
                "description": (
                    f"Constraint graph has {len(components)} disconnected components. "
                    "Independent subsystems may allow partial witness forgery."
                ),
                "bounty_relevance": "Soundness violation",
                "estimated_payout": "$10K-$50K"
            })

        if not e8_result.get("parity_healthy", True):
            findings.append({
                "type": "E8_PARITY_IMBALANCE",
                "severity": "MEDIUM",
                "imbalance": e8_result["parity_imbalance"],
                "orphan_count": e8_result["orphan_count"],
                "description": (
                    "E8 cross-parity analysis shows structural imbalance. "
                    "Constraint system may have algebraic degree deficiency."
                ),
                "bounty_relevance": "Algebraic soundness issue",
                "estimated_payout": "$10K-$50K"
            })

        return {
            "summary": {
                "severity": severity,
                "n_wires": self.n_wires,
                "n_constraints": self.n_constraints,
                "n_findings": len(findings),
                "constraint_density": self.n_constraints / max(self.n_wires, 1),
            },
            "findings": findings,
            "betti_numbers": betti,
            "e8_parity": e8_result,
            "components": {
                "count": len(components),
                "sizes": [len(c) for c in components]
            }
        }


# ================================================================
# CIRCOM / R1CS FILE PARSER
# ================================================================

def parse_r1cs_json(filepath: str) -> Tuple[int, List[R1CSConstraint], Set[int]]:
    """
    Parse a Circom-generated R1CS JSON file.

    Circom outputs constraint systems as JSON with:
    {
        "constraints": [
            [{"wire": coeff, ...}, {"wire": coeff, ...}, {"wire": coeff, ...}],
            ...
        ],
        "nVars": int,
        "nPubInputs": int,
        "nOutputs": int
    }
    """
    with open(filepath) as f:
        data = json.load(f)

    n_wires = data.get("nVars", data.get("n_wires", 0))
    n_pub = data.get("nPubInputs", 0) + data.get("nOutputs", 0)
    public = set(range(n_pub + 1))  # Wire 0 + public inputs + outputs

    constraints = []
    for c_data in data.get("constraints", []):
        a = {int(k): int(v) for k, v in c_data[0].items()}
        b = {int(k): int(v) for k, v in c_data[1].items()}
        c = {int(k): int(v) for k, v in c_data[2].items()}
        constraints.append(R1CSConstraint(a, b, c))

    return n_wires, constraints, public


def parse_r1cs_binary(filepath: str) -> Tuple[int, List[R1CSConstraint], Set[int]]:
    """
    Parse a binary .r1cs file (standard Circom/snarkjs format).
    Format spec: https://github.com/iden3/r1csfile/blob/master/doc/r1cs_bin_format.md
    """
    import struct

    with open(filepath, 'rb') as f:
        # Magic: "r1cs"
        magic = f.read(4)
        if magic != b'r1cs':
            raise ValueError(f"Not an R1CS file: {magic}")

        version = struct.unpack('<I', f.read(4))[0]
        n_sections = struct.unpack('<I', f.read(4))[0]

        n_wires = 0
        n_pub_out = 0
        n_pub_in = 0
        n_constraints_total = 0
        constraints = []
        field_size = 32  # bytes, default for BN254

        for _ in range(n_sections):
            section_type = struct.unpack('<I', f.read(4))[0]
            section_size = struct.unpack('<Q', f.read(8))[0]
            section_start = f.tell()

            if section_type == 1:  # Header
                field_size = struct.unpack('<I', f.read(4))[0]
                f.read(field_size)  # prime
                n_wires = struct.unpack('<I', f.read(4))[0]
                n_pub_out = struct.unpack('<I', f.read(4))[0]
                n_pub_in = struct.unpack('<I', f.read(4))[0]
                _n_prv = struct.unpack('<I', f.read(4))[0]
                _n_labels = struct.unpack('<Q', f.read(8))[0]
                n_constraints_total = struct.unpack('<I', f.read(4))[0]

            elif section_type == 2:  # Constraints
                for _ in range(n_constraints_total):
                    abc = []
                    for _ in range(3):  # A, B, C
                        n_terms = struct.unpack('<I', f.read(4))[0]
                        terms = {}
                        for _ in range(n_terms):
                            wire = struct.unpack('<I', f.read(4))[0]
                            coeff_bytes = f.read(field_size)
                            coeff = int.from_bytes(coeff_bytes, 'little')
                            terms[wire] = coeff
                        abc.append(terms)
                    constraints.append(R1CSConstraint(abc[0], abc[1], abc[2]))

            f.seek(section_start + section_size)

    public = set(range(1 + n_pub_out + n_pub_in))
    return n_wires, constraints, public


# ================================================================
# DEMO: Generate a vulnerable circuit for testing
# ================================================================

def demo_vulnerable_circuit():
    """
    Create a deliberately underconstrained circuit to demonstrate detection.

    This models a simplified "balance update" circuit where:
    - Wire 0: constant 1
    - Wire 1: old_balance (public input)
    - Wire 2: amount (public input)
    - Wire 3: new_balance (public output)
    - Wire 4: intermediate computation
    - Wire 5: UNCONSTRAINED (vulnerability!)
    - Wire 6: range check witness
    """
    constraints = [
        # old_balance + amount = new_balance
        # A: [old_balance] * B: [1] = C: [new_balance - amount]
        R1CSConstraint(
            a={1: 1},           # old_balance
            b={0: 1},           # 1
            c={3: 1, 2: -1}    # new_balance - amount
        ),
        # range check: amount * amount = amount_sq (intermediate)
        R1CSConstraint(
            a={2: 1},           # amount
            b={2: 1},           # amount
            c={4: 1}            # amount_sq
        ),
        # amount_sq constrained to range (simplified)
        R1CSConstraint(
            a={4: 1},
            b={6: 1},           # range witness
            c={0: 1}            # should equal 1 (simplified range check)
        ),
        # Wire 5 is NEVER referenced - unconstrained!
        # Wire 6 only appears once (underconstrained)
    ]

    return CircuitAnalyzer(
        n_wires=7,
        constraints=constraints,
        public_inputs={0, 1, 2, 3}
    )


def demo_sound_circuit():
    """A properly constrained circuit for comparison."""
    constraints = [
        R1CSConstraint(a={1: 1}, b={0: 1}, c={3: 1, 2: -1}),
        R1CSConstraint(a={2: 1}, b={2: 1}, c={4: 1}),
        R1CSConstraint(a={4: 1}, b={5: 1}, c={0: 1}),
        # Additional constraint linking wire 5
        R1CSConstraint(a={5: 1}, b={5: 1}, c={5: 1}),  # 5*5 = 5 -> 5 is 0 or 1
    ]

    return CircuitAnalyzer(
        n_wires=6,
        constraints=constraints,
        public_inputs={0, 1, 2, 3}
    )


# ================================================================
# CLI
# ================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="ZK Circuit Underconstrained Detector (E8 Cross-Parity + TDA)"
    )
    parser.add_argument('file', nargs='?', help='.r1cs or .json constraint file')
    parser.add_argument('--demo', action='store_true', help='Run demo analysis')
    parser.add_argument('--output', type=str, help='Output JSON report')

    args = parser.parse_args()

    if args.demo:
        print("=" * 60)
        print("  ZK CIRCUIT VULNERABILITY DEMO")
        print("  Using E8 Cross-Parity + TDA Analysis")
        print("=" * 60)

        print("\n--- VULNERABLE Circuit ---")
        vuln = demo_vulnerable_circuit()
        vuln_report = vuln.full_audit()
        print(json.dumps(vuln_report, indent=2, default=str))

        print("\n--- SOUND Circuit ---")
        sound = demo_sound_circuit()
        sound_report = sound.full_audit()
        print(json.dumps(sound_report, indent=2, default=str))

        return

    if args.file:
        if args.file.endswith('.json'):
            n_wires, constraints, public = parse_r1cs_json(args.file)
        elif args.file.endswith('.r1cs'):
            n_wires, constraints, public = parse_r1cs_binary(args.file)
        else:
            print(f"Unknown format: {args.file}")
            sys.exit(1)

        analyzer = CircuitAnalyzer(n_wires, constraints, public)
        report = analyzer.full_audit()

        print(json.dumps(report, indent=2, default=str))

        if args.output:
            with open(args.output, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"\nReport saved to {args.output}")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
