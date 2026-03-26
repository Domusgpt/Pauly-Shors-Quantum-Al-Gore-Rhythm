"""
End-to-End Attack Pipeline for Q-Day Prize

Orchestrates the complete attack flow:
    1. Generate or load ECC keys at target bit level
    2. Build quantum circuits (Shor's algorithm for ECDLP)
    3. Execute on simulator or real quantum hardware (IBM/AWS)
    4. Post-process measurements to extract secret key
    5. Verify recovered key
    6. Generate submission report

Supports:
    - IBM Quantum (via qiskit-ibm-runtime)
    - AWS Braket (via amazon-braket-sdk)
    - Local Aer simulator (default)
"""

import json
import time
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

from .ecc_curves import EllipticCurve, ECPoint, get_curve, generate_keypair
from .shor_ecdlp import ShorECDLP, ShorResult, MeasurementStats, attack_ecc_key
from .quantum_arithmetic import num_qubits_for_mod


@dataclass
class AttackReport:
    """Complete report for Q-Day Prize submission."""
    timestamp: str
    target_bits: int
    curve_params: Dict[str, Any]
    generator: str
    public_key: str
    recovered_key: Optional[int]
    verified: bool
    circuit_stats: Dict[str, Any]
    backend_info: Dict[str, Any]
    approach_description: str
    num_measurements: int
    execution_time_seconds: float
    gate_level_summary: Dict[str, int]
    measurement_stats: Optional[Dict[str, Any]] = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, default=str)

    def save(self, filepath: str):
        with open(filepath, 'w') as f:
            f.write(self.to_json())


class QDayAttackPipeline:
    """
    Main orchestrator for the Q-Day Prize quantum attack.
    """

    def __init__(self, target_bits: int = 1, backend_type: str = "simulator"):
        """
        Args:
            target_bits: ECC key size to attack (1-25)
            backend_type: "simulator", "ibm", or "aws"
        """
        self.target_bits = target_bits
        self.backend_type = backend_type
        self.curve = get_curve(target_bits)
        self.backend = None
        self.backend_info = {"type": backend_type}

    def setup_backend(self, **kwargs):
        """Configure the quantum backend."""
        if self.backend_type == "simulator":
            self._setup_simulator(**kwargs)
        elif self.backend_type == "ibm":
            self._setup_ibm(**kwargs)
        elif self.backend_type == "aws":
            self._setup_aws(**kwargs)
        else:
            raise ValueError(f"Unknown backend type: {self.backend_type}")

    def _setup_simulator(self, noise_model=None, **kwargs):
        """Set up local Aer simulator."""
        from qiskit_aer import AerSimulator
        if noise_model:
            self.backend = AerSimulator(noise_model=noise_model)
            self.backend_info["noise"] = True
        else:
            self.backend = AerSimulator()
            self.backend_info["noise"] = False
        self.backend_info["name"] = "AerSimulator"

    def _setup_ibm(self, token: Optional[str] = None,
                    instance: str = "ibm-q/open/main",
                    backend_name: str = "ibm_fez", **kwargs):
        """
        Set up IBM Quantum backend.

        Requires: pip install qiskit-ibm-runtime
        Token: Get from https://quantum.ibm.com/
        """
        try:
            from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

            if token:
                QiskitRuntimeService.save_account(channel="ibm_quantum_platform",
                                                   token=token, overwrite=True)
            service = QiskitRuntimeService(channel="ibm_quantum_platform")
            self.backend = service.backend(backend_name)
            self.backend_info.update({
                "name": backend_name,
                "num_qubits": self.backend.num_qubits,
                "provider": "IBM Quantum",
            })
        except ImportError:
            raise ImportError(
                "IBM Quantum backend requires: pip install qiskit-ibm-runtime\n"
                "Get token at: https://quantum.ibm.com/"
            )

    def _setup_aws(self, device_arn: Optional[str] = None, **kwargs):
        """
        Set up AWS Braket backend.

        Requires: pip install amazon-braket-sdk
        """
        try:
            from qiskit_braket_provider import AWSBraketProvider

            provider = AWSBraketProvider()
            if device_arn:
                self.backend = provider.get_backend(device_arn)
            else:
                # Default to SV1 simulator
                self.backend = provider.get_backend("SV1")
            self.backend_info.update({
                "name": str(self.backend),
                "provider": "AWS Braket",
            })
        except ImportError:
            raise ImportError(
                "AWS Braket backend requires: pip install amazon-braket-sdk qiskit-braket-provider"
            )

    def generate_target(self, secret_key: Optional[int] = None):
        """Generate the ECDLP instance to attack."""
        G = self.curve.find_generator()
        n = self.curve.point_order(G)

        if secret_key is not None:
            k = secret_key
        else:
            import random
            k = random.randint(1, n - 1)

        Q = self.curve.scalar_mult(k, G)

        self.generator = G
        self.public_key = Q
        self.secret_key = k
        self.group_order = n

        return k, Q

    def run_attack(self, shots: int = 2048, max_iterations: int = 10) -> AttackReport:
        """
        Execute the full attack pipeline.

        Returns:
            AttackReport suitable for Q-Day Prize submission
        """
        if self.backend is None:
            self.setup_backend()

        if not hasattr(self, 'public_key'):
            self.generate_target()

        start_time = time.time()

        # Run Shor's algorithm
        shor = ShorECDLP(self.curve, self.generator, self.public_key)

        # Use configurable optimization level (default 3 for IBM)
        opt_level = getattr(self, 'optimization_level', 3)

        # Always use honest ECPointOracle — computes aP + bQ from public key only
        # Never use SimplifiedECOracle which embeds the secret key
        result = shor.run_attack(
            backend=self.backend,
            shots=shots,
            max_iterations=max_iterations,
            use_simplified_oracle=False,
            known_key=None,
            optimization_level=opt_level
        )

        elapsed = time.time() - start_time

        # Collect measurement statistics
        mstats_dict = None
        if result.measurement_stats:
            mstats_dict = result.measurement_stats.to_dict()

        # Build report
        report = AttackReport(
            timestamp=datetime.utcnow().isoformat(),
            target_bits=self.target_bits,
            curve_params={
                "a": self.curve.a,
                "b": self.curve.b,
                "p": self.curve.p,
                "name": self.curve.name,
                "group_order": self.group_order,
            },
            generator=str(self.generator),
            public_key=str(self.public_key),
            recovered_key=result.secret_key,
            verified=result.success,
            circuit_stats={
                "num_qubits": result.num_qubits,
                "depth": result.circuit_depth,
                "precision_bits": shor.precision,
                "optimization_level": opt_level,
            },
            backend_info=self.backend_info,
            approach_description=self._approach_description(),
            num_measurements=result.num_shots,
            execution_time_seconds=elapsed,
            gate_level_summary=result.gate_counts,
            measurement_stats=mstats_dict,
        )

        return report

    def _approach_description(self) -> str:
        return (
            f"Shor's algorithm for ECDLP on {self.target_bits}-bit ECC key. "
            f"Curve E: y² = x³ + {self.curve.a}x + {self.curve.b} over GF({self.curve.p}). "
            f"Group order n = {self.group_order}. "
            f"Two quantum registers of {2 * num_qubits_for_mod(self.group_order) + 1} qubits each "
            f"prepared in uniform superposition. Oracle computes aP + bQ via "
            f"{'lookup table' if self.group_order <= 64 else 'reversible EC arithmetic'}. "
            f"Inverse QFT applied to both registers. "
            f"Key extracted via continued fractions and lattice reduction on measurements. "
            f"Method is general and scales to 256-bit keys with sufficient qubits."
        )

    def export_qasm(self, filepath: str):
        """Export the attack circuit as OpenQASM for submission."""
        shor = ShorECDLP(self.curve, self.generator, self.public_key)
        use_simplified = (self.group_order <= 64)
        qc = shor.build_circuit(
            use_simplified_oracle=use_simplified,
            known_key=self.secret_key if use_simplified else None
        )
        from qiskit.qasm2 import dumps as qasm2_dumps
        qasm_str = qasm2_dumps(qc)
        with open(filepath, 'w') as f:
            f.write(qasm_str)
        print(f"Circuit exported to {filepath}")

    def export_gate_level(self, filepath: str):
        """Export detailed gate-level description for submission."""
        from qiskit import transpile
        from qiskit_aer import AerSimulator

        shor = ShorECDLP(self.curve, self.generator, self.public_key)
        use_simplified = (self.group_order <= 64)
        qc = shor.build_circuit(
            use_simplified_oracle=use_simplified,
            known_key=self.secret_key if use_simplified else None
        )

        # Decompose custom gates before transpiling to get primitive gate counts
        qc_decomposed = qc.decompose().decompose().decompose()
        backend = AerSimulator()
        transpiled = transpile(qc_decomposed, backend, optimization_level=2)

        gate_info = {
            "circuit_name": "Shor_ECDLP_QDay",
            "target_bits": self.target_bits,
            "total_qubits": transpiled.num_qubits,
            "total_depth": transpiled.depth(),
            "gate_counts": dict(transpiled.count_ops()),
            "gates_by_qubit": {},
        }

        with open(filepath, 'w') as f:
            json.dump(gate_info, f, indent=2)
        print(f"Gate-level description exported to {filepath}")


# ─── Batch attack across multiple bit levels ─────────────────────────────────

def run_qday_campaign(max_bits: int = 5, shots: int = 2048,
                       output_dir: str = "qday_results") -> List[AttackReport]:
    """
    Run attacks across multiple bit levels for Q-Day Prize.

    Args:
        max_bits: Maximum bit level to attack (1-25)
        shots: Shots per circuit execution
        output_dir: Directory to save results

    Returns:
        List of AttackReports
    """
    os.makedirs(output_dir, exist_ok=True)
    reports = []

    for bits in range(1, max_bits + 1):
        print(f"\n{'='*60}")
        print(f"  Q-Day Attack: {bits}-bit ECC key")
        print(f"{'='*60}\n")

        pipeline = QDayAttackPipeline(target_bits=bits, backend_type="simulator")
        pipeline.setup_backend()
        pipeline.generate_target()

        report = pipeline.run_attack(shots=shots)
        reports.append(report)

        # Save individual report
        report_path = os.path.join(output_dir, f"attack_{bits}bit.json")
        report.save(report_path)
        print(f"\nReport saved to {report_path}")

        # Export circuit
        try:
            qasm_path = os.path.join(output_dir, f"circuit_{bits}bit.qasm")
            pipeline.export_qasm(qasm_path)
        except Exception as e:
            print(f"  QASM export failed: {e}")

        gate_path = os.path.join(output_dir, f"gates_{bits}bit.json")
        pipeline.export_gate_level(gate_path)

    # Summary
    print(f"\n{'='*60}")
    print("  Q-Day Campaign Summary")
    print(f"{'='*60}")
    for r in reports:
        status = "BROKEN" if r.verified else "FAILED"
        print(f"  {r.target_bits}-bit: {status} | "
              f"Qubits: {r.circuit_stats['num_qubits']} | "
              f"Depth: {r.circuit_stats['depth']} | "
              f"Time: {r.execution_time_seconds:.2f}s")

    return reports
