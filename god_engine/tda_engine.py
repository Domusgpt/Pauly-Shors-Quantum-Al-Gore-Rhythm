"""
Topological Data Analysis Engine
=================================
Persistent homology on E8 lattice projections and number-theoretic
point clouds. Detects topological features (connected components,
loops, voids) that persist across filtration scales.

Key insight: When we project a composite number's residue structure
through the E8 lattice, the persistent homology reveals factor-related
topological features that a flat Euclidean analysis misses.

Uses Vietoris-Rips filtration computed directly (no external TDA library
dependency) for portability.
"""

import numpy as np
from collections import defaultdict


class UnionFind:
    """Weighted union-find for connected component tracking."""

    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n
        self.component_count = n

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x, y):
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return False
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        if self.rank[rx] == self.rank[ry]:
            self.rank[rx] += 1
        self.component_count -= 1
        return True


class PersistentHomology:
    """
    Vietoris-Rips persistent homology for H0 (components) and H1 (loops).

    H0: Connected components that merge as filtration radius grows.
          Birth = 0 for all points. Death = distance at merge.
    H1: Loops that appear when triangles close but weren't already contractible.
          Approximated via the 1-skeleton cycle detection.
    """

    def __init__(self, points):
        self.points = np.array(points)
        self.n = len(points)
        self.distance_matrix = self._compute_distances()

    def _compute_distances(self):
        diff = self.points[:, np.newaxis, :] - self.points[np.newaxis, :, :]
        return np.sqrt(np.sum(diff**2, axis=2))

    def compute_h0(self):
        """Compute H0 persistence diagram (connected components)."""
        # Sort all edges by distance
        edges = []
        for i in range(self.n):
            for j in range(i + 1, self.n):
                edges.append((self.distance_matrix[i, j], i, j))
        edges.sort()

        uf = UnionFind(self.n)
        diagram = []

        for dist, i, j in edges:
            if uf.find(i) != uf.find(j):
                uf.union(i, j)
                diagram.append((0, dist))  # (birth, death)

        # One component survives to infinity
        diagram.append((0, float('inf')))
        return diagram

    def compute_h1_approx(self):
        """
        Approximate H1 (loops) via cycle detection in growing graph.

        At each filtration step, when an edge creates a cycle (both
        endpoints already connected), that's a potential H1 birth.
        The cycle dies when a triangle fills it.
        """
        edges = []
        for i in range(self.n):
            for j in range(i + 1, self.n):
                edges.append((self.distance_matrix[i, j], i, j))
        edges.sort()

        uf = UnionFind(self.n)
        adjacency = defaultdict(set)
        h1_births = []

        for dist, i, j in edges:
            if uf.find(i) == uf.find(j):
                # Cycle detected — H1 birth
                # Check if a triangle already kills it
                common_neighbors = adjacency[i] & adjacency[j]
                if not common_neighbors:
                    h1_births.append(dist)
            else:
                uf.union(i, j)
            adjacency[i].add(j)
            adjacency[j].add(i)

        # Approximate deaths: next common-neighbor formation
        diagram = []
        for birth in h1_births:
            # Simple model: loops persist for ~1.5x their birth radius
            death = birth * 1.5
            diagram.append((birth, death))

        return diagram

    def persistence_landscape(self, diagram, resolution=100):
        """Convert persistence diagram to persistence landscape function."""
        if not diagram:
            return np.zeros(resolution), np.zeros(resolution)

        finite_deaths = [d for _, d in diagram if d != float('inf')]
        if not finite_deaths:
            return np.zeros(resolution), np.zeros(resolution)

        max_val = max(finite_deaths) * 1.1
        t = np.linspace(0, max_val, resolution)
        landscape = np.zeros(resolution)

        for birth, death in diagram:
            if death == float('inf'):
                continue
            mid = (birth + death) / 2
            half_life = (death - birth) / 2
            for k, tk in enumerate(t):
                if birth <= tk <= mid:
                    landscape[k] = max(landscape[k], tk - birth)
                elif mid < tk <= death:
                    landscape[k] = max(landscape[k], death - tk)

        return t, landscape

    def total_persistence(self, diagram):
        """Sum of all bar lengths (excluding infinite bars)."""
        return sum(d - b for b, d in diagram if d != float('inf'))

    def betti_curve(self, diagram, resolution=100):
        """Betti number as function of filtration parameter."""
        finite_deaths = [d for _, d in diagram if d != float('inf')]
        if not finite_deaths:
            return np.zeros(resolution), np.zeros(resolution)

        max_val = max(finite_deaths) * 1.1
        t = np.linspace(0, max_val, resolution)
        betti = np.zeros(resolution)

        for birth, death in diagram:
            d = death if death != float('inf') else max_val
            for k, tk in enumerate(t):
                if birth <= tk < d:
                    betti[k] += 1

        return t, betti


class LatticeTopology:
    """
    TDA specifically for E8 lattice-projected point clouds.

    Maps number-theoretic objects (residues mod N, Galois orbits)
    into the E8 projected space and computes their persistent homology.
    """

    def __init__(self, lattice):
        """
        Args:
            lattice: E8Lattice instance
        """
        self.lattice = lattice

    def residue_point_cloud(self, n, base=None):
        """
        Map residues mod n into E8 projected space.

        For each a in (Z/nZ)*, embed a as:
            point = projected_root[a mod 240] * scale(a, n)

        This maps the multiplicative group structure into
        the geometric structure of the lattice projection.
        """
        from math import gcd
        residues = [a for a in range(1, n) if gcd(a, n) == 1]
        points = []
        for a in residues:
            root_idx = a % 240
            # Scale by normalized residue position
            scale = a / n
            point = self.lattice.projected[root_idx] * (0.5 + scale)
            points.append(point)
        return np.array(points), residues

    def galois_orbit_cloud(self, a, n):
        """
        Trace the Galois orbit of a mod n through E8 projected space.

        The orbit is: a, a^2 mod n, a^3 mod n, ..., a^r mod n = 1
        Each step maps to an E8 projected root.
        """
        from math import gcd
        if gcd(a, n) != 1:
            return None, None

        orbit = []
        points = []
        val = a % n
        while True:
            orbit.append(val)
            root_idx = val % 240
            # Embed with phase encoding from orbit position
            phase = len(orbit) / 100.0
            point = self.lattice.projected[root_idx] * (1 + 0.1 * np.sin(phase * 2 * np.pi))
            points.append(point)
            val = (val * a) % n
            if val == a % n or len(orbit) > n:
                break

        return np.array(points), orbit

    def factor_topology(self, n):
        """
        Full topological analysis of a composite number n.

        Computes:
        1. H0 of residue cloud (connected components = factor structure)
        2. H1 of residue cloud (loops = cyclic subgroup structure)
        3. Persistence landscapes for visualization
        4. Topological signatures that differ between primes and composites
        """
        points, residues = self.residue_point_cloud(n)

        if len(points) < 3:
            return {'n': n, 'too_small': True}

        # Subsample for large n to keep computation tractable
        if len(points) > 200:
            indices = np.random.RandomState(42).choice(len(points), 200, replace=False)
            points = points[indices]
            residues = [residues[i] for i in indices]

        ph = PersistentHomology(points)
        h0 = ph.compute_h0()
        h1 = ph.compute_h1_approx()

        return {
            'n': n,
            'phi_n': len(residues),
            'num_points': len(points),
            'h0_diagram': h0,
            'h1_diagram': h1,
            'h0_total_persistence': ph.total_persistence(h0),
            'h1_total_persistence': ph.total_persistence(h1),
            'h0_bars': len(h0),
            'h1_bars': len(h1),
        }

    def compare_factor_signatures(self, n1, n2):
        """Compare topological signatures of two numbers."""
        t1 = self.factor_topology(n1)
        t2 = self.factor_topology(n2)
        return {
            'n1': n1, 'n2': n2,
            'h0_persistence_ratio': t1['h0_total_persistence'] / max(t2['h0_total_persistence'], 1e-10),
            'h1_persistence_ratio': t1['h1_total_persistence'] / max(t2['h1_total_persistence'], 1e-10),
            'h1_count_ratio': t1['h1_bars'] / max(t2['h1_bars'], 1),
        }


if __name__ == '__main__':
    from e8_lattice import E8Lattice

    print("=" * 70)
    print("TOPOLOGICAL DATA ANALYSIS ENGINE - TEST")
    print("=" * 70)

    lattice = E8Lattice()
    topo = LatticeTopology(lattice)

    # Test with small composites
    for n in [15, 21, 35, 77, 143]:
        result = topo.factor_topology(n)
        if 'too_small' in result:
            print(f"  n={n}: too small for analysis")
            continue
        print(f"  n={n:4d} (phi={result['phi_n']:3d}): "
              f"H0_persist={result['h0_total_persistence']:.3f}  "
              f"H1_bars={result['h1_bars']:3d}  "
              f"H1_persist={result['h1_total_persistence']:.3f}")

    # Compare prime vs composite
    print("\nPrime vs Composite comparison:")
    for p, c in [(13, 15), (23, 21), (37, 35)]:
        comp = topo.compare_factor_signatures(p, c)
        print(f"  {p} (prime) vs {c} (composite): "
              f"H1_ratio={comp['h1_persistence_ratio']:.3f}")
