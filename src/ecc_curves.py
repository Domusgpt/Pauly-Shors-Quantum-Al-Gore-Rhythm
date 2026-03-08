"""
Small Elliptic Curve Definitions for Q-Day Prize

Defines elliptic curves E: y^2 = x^3 + ax + b over GF(p) for small primes p,
suitable for 1-25 bit security levels. Each curve includes precomputed group
structure (generator, order, all points) for verification.

References:
    - Proos & Zalka (2003): "Shor's discrete logarithm quantum algorithm for elliptic curves"
    - Project Eleven Q-Day Prize: ECC keys from 1 to 25 bits
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import math


@dataclass(frozen=True)
class ECPoint:
    """Point on an elliptic curve, or the point at infinity (x=None, y=None)."""
    x: Optional[int]
    y: Optional[int]

    @property
    def is_infinity(self) -> bool:
        return self.x is None and self.y is None

    def __repr__(self):
        if self.is_infinity:
            return "O (infinity)"
        return f"({self.x}, {self.y})"


INFINITY = ECPoint(None, None)


@dataclass
class EllipticCurve:
    """Elliptic curve y^2 = x^3 + ax + b over GF(p)."""
    a: int
    b: int
    p: int
    name: str = ""
    generator: Optional[ECPoint] = None
    order: Optional[int] = None
    _points: Optional[List[ECPoint]] = field(default=None, repr=False)

    def __post_init__(self):
        disc = (4 * self.a**3 + 27 * self.b**2) % self.p
        if disc == 0:
            raise ValueError(f"Singular curve: discriminant is 0 (mod {self.p})")

    def contains(self, P: ECPoint) -> bool:
        if P.is_infinity:
            return True
        lhs = (P.y * P.y) % self.p
        rhs = (P.x**3 + self.a * P.x + self.b) % self.p
        return lhs == rhs

    def add(self, P: ECPoint, Q: ECPoint) -> ECPoint:
        if P.is_infinity:
            return Q
        if Q.is_infinity:
            return P
        if P.x == Q.x and (P.y + Q.y) % self.p == 0:
            return INFINITY

        if P.x == Q.x and P.y == Q.y:
            # Point doubling
            num = (3 * P.x * P.x + self.a) % self.p
            den = (2 * P.y) % self.p
        else:
            num = (Q.y - P.y) % self.p
            den = (Q.x - P.x) % self.p

        den_inv = pow(den, self.p - 2, self.p)
        lam = (num * den_inv) % self.p

        x_r = (lam * lam - P.x - Q.x) % self.p
        y_r = (lam * (P.x - x_r) - P.y) % self.p
        return ECPoint(x_r, y_r)

    def negate(self, P: ECPoint) -> ECPoint:
        if P.is_infinity:
            return INFINITY
        return ECPoint(P.x, (-P.y) % self.p)

    def scalar_mult(self, k: int, P: ECPoint) -> ECPoint:
        if k == 0 or P.is_infinity:
            return INFINITY
        if k < 0:
            return self.scalar_mult(-k, self.negate(P))

        result = INFINITY
        addend = P
        while k > 0:
            if k & 1:
                result = self.add(result, addend)
            addend = self.add(addend, addend)
            k >>= 1
        return result

    def enumerate_points(self) -> List[ECPoint]:
        """Enumerate all points on the curve (including infinity)."""
        if self._points is not None:
            return self._points

        points = [INFINITY]
        for x in range(self.p):
            rhs = (x**3 + self.a * x + self.b) % self.p
            # Check if rhs is a quadratic residue
            for y in range(self.p):
                if (y * y) % self.p == rhs:
                    points.append(ECPoint(x, y))
        self._points = points
        return points

    def group_order(self) -> int:
        """Compute #E(GF(p)) by enumeration."""
        if self.order is not None:
            return self.order
        self.order = len(self.enumerate_points())
        return self.order

    def find_generator(self) -> ECPoint:
        """Find a generator of the curve group (point of maximum order)."""
        if self.generator is not None:
            return self.generator

        n = self.group_order()
        points = self.enumerate_points()

        for P in points:
            if P.is_infinity:
                continue
            # Check if P generates the full group
            order = 1
            Q = P
            while not Q.is_infinity:
                Q = self.add(Q, P)
                order += 1
                if order > n:
                    break
            if order == n:
                self.generator = P
                return P

        # If no generator of full order, find max order point
        best_point = points[1]
        best_order = 1
        for P in points[1:]:
            order = self.point_order(P)
            if order > best_order:
                best_order = order
                best_point = P
        self.generator = best_point
        return best_point

    def point_order(self, P: ECPoint) -> int:
        """Compute the order of point P."""
        if P.is_infinity:
            return 1
        Q = P
        order = 1
        while not Q.is_infinity:
            Q = self.add(Q, P)
            order += 1
            if order > self.p + 1 + 2 * int(math.isqrt(self.p)) + 1:
                raise ValueError("Order computation exceeded Hasse bound")
        return order

    def security_bits(self) -> int:
        """Approximate security level in bits."""
        n = self.group_order()
        return max(1, int(math.log2(n))) if n > 1 else 1


def _mod_sqrt(a: int, p: int) -> Optional[int]:
    """Tonelli-Shanks for modular square root."""
    a = a % p
    if a == 0:
        return 0
    if pow(a, (p - 1) // 2, p) != 1:
        return None
    if p % 4 == 3:
        return pow(a, (p + 1) // 4, p)
    # Tonelli-Shanks
    q = p - 1
    s = 0
    while q % 2 == 0:
        q //= 2
        s += 1
    z = 2
    while pow(z, (p - 1) // 2, p) != p - 1:
        z += 1
    m = s
    c = pow(z, q, p)
    t = pow(a, q, p)
    r = pow(a, (q + 1) // 2, p)
    while True:
        if t == 1:
            return r
        i = 1
        tmp = (t * t) % p
        while tmp != 1:
            tmp = (tmp * tmp) % p
            i += 1
        b = pow(c, 1 << (m - i - 1), p)
        m = i
        c = (b * b) % p
        t = (t * c) % p
        r = (r * b) % p


# ─── Pre-defined curves for Q-Day Prize bit levels ───────────────────────────

def generate_curve_for_bits(target_bits: int) -> EllipticCurve:
    """
    Generate an elliptic curve with approximately target_bits of security.
    The group order n should satisfy: 2^(target_bits-1) < n <= 2^target_bits.
    """
    # For small bit sizes, we search for suitable curves
    # Security bits ~ log2(group_order)
    target_min = 2 ** max(0, target_bits - 1)
    target_max = 2 ** (target_bits + 1)

    # Search primes from small to large
    primes = _primes_up_to(max(100, target_max * 4))

    for p in primes:
        if p < 3:
            continue
        for a in range(p):
            for b in range(p):
                if (4 * a**3 + 27 * b**2) % p == 0:
                    continue
                curve = EllipticCurve(a=a, b=b, p=p, name=f"QDay-{target_bits}bit")
                n = curve.group_order()
                if target_min < n <= target_max:
                    curve.find_generator()
                    return curve

    raise ValueError(f"Could not find curve for {target_bits}-bit security")


def _primes_up_to(n: int) -> List[int]:
    if n < 2:
        return []
    sieve = [True] * (n + 1)
    sieve[0] = sieve[1] = False
    for i in range(2, int(n**0.5) + 1):
        if sieve[i]:
            for j in range(i*i, n + 1, i):
                sieve[j] = False
    return [i for i, v in enumerate(sieve) if v]


# ─── Standard small test curves ─────────────────────────────────────────────

# 1-bit: Trivial curve, group order 2-3
CURVE_1BIT = EllipticCurve(a=1, b=0, p=3, name="QDay-1bit")

# 2-bit: Group order ~4
CURVE_2BIT = EllipticCurve(a=1, b=1, p=5, name="QDay-2bit")

# 3-bit: Group order ~8
CURVE_3BIT = EllipticCurve(a=2, b=3, p=7, name="QDay-3bit")

# 4-bit: Group order ~16
CURVE_4BIT = EllipticCurve(a=1, b=1, p=13, name="QDay-4bit")

# 5-bit: Group order ~32
CURVE_5BIT = EllipticCurve(a=1, b=1, p=29, name="QDay-5bit")


# Pre-built catalogue
QDAY_CURVES = {
    1: CURVE_1BIT,
    2: CURVE_2BIT,
    3: CURVE_3BIT,
    4: CURVE_4BIT,
    5: CURVE_5BIT,
}


def get_curve(bits: int) -> EllipticCurve:
    """Get or generate a curve for the given bit security level."""
    if bits in QDAY_CURVES:
        return QDAY_CURVES[bits]
    curve = generate_curve_for_bits(bits)
    QDAY_CURVES[bits] = curve
    return curve


def generate_keypair(curve: EllipticCurve) -> Tuple[int, ECPoint]:
    """
    Generate an ECDLP instance: private key k, public key Q = kG.
    Returns (k, Q) where G is the curve generator.
    """
    import random
    G = curve.find_generator()
    n = curve.point_order(G)
    k = random.randint(1, n - 1)
    Q = curve.scalar_mult(k, G)
    return k, Q
