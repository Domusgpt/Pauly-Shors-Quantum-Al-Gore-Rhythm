#!/usr/bin/env python3
"""
G.O.D. Bounty Hunter - Unified Security Toolkit
==================================================

Combines all ZTC/E8/TDA-based security tools into a single CLI
for hunting bounties across multiple domains.

TOOLS:
  1. ecdsa     - ECDSA/ecrecover vulnerability scanner (Immunefi)
  2. zk        - ZK circuit underconstrained detector (zkSync, zkVerify)
  3. oracle    - TDA oracle manipulation detector (DeFi protocols)
  4. vrf       - VRF/randomness bias detector (Chainlink, drand)
  5. factor    - BABEL tower factorization engine (Q-Day Prize)
  6. peaked    - Peaked circuit solver (BlueQubit Challenge)
  7. scan      - Full audit of a Solidity codebase

BOUNTY TARGETS:
  Q-Day Prize:     1 BTC     (ECC key break via quantum)
  BlueQubit:       0.25 BTC  (Peaked circuit challenge)
  zkSync:          $100K     (ZK circuit vulnerabilities)
  Wormhole:        $2M       (Cross-chain bridge bugs)
  Axelar:          $500K     (ECDSA/gateway bugs)
  Sky/MakerDAO:    $10M      (Smart contract bugs)

Usage:
  python bounty_hunter.py ecdsa path/to/contracts/
  python bounty_hunter.py zk --demo
  python bounty_hunter.py oracle --demo
  python bounty_hunter.py vrf --demo
  python bounty_hunter.py factor --demo
  python bounty_hunter.py scan path/to/project/
  python bounty_hunter.py targets

Author: Paul J. Phillips / Claude
Framework: G.O.D. (Geometric Orthogonal Dialectics)
"""

import sys
import os
import json
import argparse

# Ensure module imports work
sys.path.insert(0, os.path.dirname(__file__))


BANNER = """
 ╔══════════════════════════════════════════════════════════╗
 ║  G.O.D. BOUNTY HUNTER                                  ║
 ║  Geometric Orthogonal Dialectics Security Toolkit       ║
 ║                                                         ║
 ║  E8 Lattice × TDA × ZTC-Shor × Cross-Parity            ║
 ║  Patent: Phillips (2026) - Clear Seas Solutions LLC     ║
 ╚══════════════════════════════════════════════════════════╝
"""

TARGETS = """
 ┌──────────────────────────────────────────────────────────┐
 │  ACTIVE BOUNTY TARGETS                                  │
 ├──────────────────────────────────────────────────────────┤
 │                                                         │
 │  QUANTUM / CRYPTO CHALLENGES                            │
 │  ─────────────────────────────                          │
 │  Q-Day Prize      1 BTC ($100K)  Break ECC via quantum  │
 │    Tool: factor   Deadline: Apr 5, 2026                 │
 │    https://www.qdayprize.com/                              │
 │                                                         │
 │  BlueQubit        0.25 BTC ($20K) Peaked circuits       │
 │    Tool: peaked   Active now                            │
 │    https://app.bluequbit.io/                            │
 │                                                         │
 │  ZK PROOF SYSTEMS (Immunefi)                            │
 │  ────────────────────────────                           │
 │  zkSync OS        $100K     Airbender proof system      │
 │    Tool: zk       Circuits + smart contracts            │
 │                                                         │
 │  zkVerify          $50K     Proof verification           │
 │    Tool: zk       Modular blockchain                    │
 │                                                         │
 │  Light Protocol    $50K     ZK Compression on Solana    │
 │    Tool: zk       Circuits + smart contracts            │
 │                                                         │
 │  DEFI / SMART CONTRACTS (Immunefi)                      │
 │  ─────────────────────────────────                      │
 │  Sky (MakerDAO)   $10M     Oracle + governance          │
 │    Tool: oracle   Smart contracts                       │
 │                                                         │
 │  Wormhole          $2M     Cross-chain bridge sigs      │
 │    Tool: ecdsa    Signature verification                │
 │                                                         │
 │  Axelar           $500K    ECDSA gateway                │
 │    Tool: ecdsa    Multi-chain signatures                │
 │                                                         │
 │  Threshold Net    $500K    ECDSA contracts              │
 │    Tool: ecdsa    keep-core/solidity/ecdsa              │
 │                                                         │
 │  Injective        $500K    Blockchain/DLT               │
 │    Tool: ecdsa    Smart contracts                       │
 │                                                         │
 │  RANDOMNESS / VRF (Various)                             │
 │  ──────────────────────────                             │
 │  Any VRF user    $10-500K  Weak randomness              │
 │    Tool: vrf      On-chain randomness sources           │
 │                                                         │
 └──────────────────────────────────────────────────────────┘

 HOW TO START:
   1. Pick a target from above
   2. Get the protocol's source code (GitHub / Etherscan)
   3. Run the appropriate tool:
      python bounty_hunter.py ecdsa path/to/contracts/
      python bounty_hunter.py zk circuit.r1cs
      python bounty_hunter.py oracle --scan contract.sol
      python bounty_hunter.py vrf --scan contract.sol

   For quantum challenges:
      python bounty_hunter.py factor --qday
      python bounty_hunter.py peaked --challenge
"""


def cmd_ecdsa(args):
    """Run ECDSA vulnerability scanner."""
    from ecdsa_vuln_scanner import ECDSAVulnScanner, print_targets
    if args.targets:
        print_targets()
        return
    scanner = ECDSAVulnScanner()
    if args.path:
        if os.path.isfile(args.path):
            scanner.scan_file(args.path)
        elif os.path.isdir(args.path):
            scanner.scan_directory(args.path)
        report = scanner.generate_report()
        print(f"\n{len(report.findings)} findings across {report.files_scanned} files")
        for f in report.findings:
            print(f"  [{f.severity.value.upper()}] {f.vulnerability} @ {f.file_path}:{f.line_number}")
        if args.output:
            with open(args.output, 'w') as fout:
                fout.write(report.to_json())


def cmd_zk(args):
    """Run ZK circuit underconstrained detector."""
    from zk_underconstrained_detector import main as zk_main
    sys.argv = ['zk_underconstrained_detector.py']
    if args.demo:
        sys.argv.append('--demo')
    elif args.path:
        sys.argv.append(args.path)
    if args.output:
        sys.argv.extend(['--output', args.output])
    zk_main()


def cmd_oracle(args):
    """Run TDA oracle manipulation detector."""
    from tda_oracle_detector import main as oracle_main
    sys.argv = ['tda_oracle_detector.py']
    if args.demo:
        sys.argv.append('--demo')
    elif args.scan:
        sys.argv.extend(['--scan', args.scan])
    if hasattr(args, 'threshold') and args.threshold:
        sys.argv.extend(['--threshold', str(args.threshold)])
    oracle_main()


def cmd_vrf(args):
    """Run VRF/randomness bias detector."""
    from vrf_bias_detector import main as vrf_main
    sys.argv = ['vrf_bias_detector.py']
    if args.demo:
        sys.argv.append('--demo')
    elif args.scan:
        sys.argv.extend(['--scan', args.scan])
    elif args.test_file:
        sys.argv.extend(['--test-file', args.test_file])
    vrf_main()


def cmd_factor(args):
    """Run BABEL tower factorization engine."""
    from babel_factorization_engine import main as factor_main
    sys.argv = ['babel_factorization_engine.py']
    if args.demo:
        sys.argv.append('--demo')
    elif args.qday:
        sys.argv.append('--qday')
    elif args.number:
        sys.argv.extend(['--factor', str(args.number)])
    if args.output:
        sys.argv.extend(['--output', args.output])
    factor_main()


def cmd_peaked(args):
    """Run peaked circuit solver."""
    from peaked_circuit_solver import main as peaked_main
    sys.argv = ['peaked_circuit_solver.py']
    if args.challenge:
        sys.argv.append('--challenge')
    else:
        sys.argv.append('--demo')
    peaked_main()


def cmd_scan(args):
    """Full audit of a Solidity codebase."""
    if not args.path:
        print("Usage: bounty_hunter.py scan <path>")
        return

    print(BANNER)
    print(f"Full audit of: {args.path}\n")

    results = {"path": args.path, "tools": {}}

    # ECDSA scan
    print("=" * 50)
    print("[1/3] ECDSA Signature Scanner")
    print("=" * 50)
    from ecdsa_vuln_scanner import ECDSAVulnScanner
    scanner = ECDSAVulnScanner()
    if os.path.isdir(args.path):
        scanner.scan_directory(args.path)
    else:
        scanner.scan_file(args.path)
    report = scanner.generate_report()
    print(f"  {len(report.findings)} ECDSA findings")
    results["tools"]["ecdsa"] = len(report.findings)

    # Oracle scan
    print("\n" + "=" * 50)
    print("[2/3] Oracle Manipulation Scanner")
    print("=" * 50)
    from tda_oracle_detector import scan_oracle_patterns
    oracle_findings = []
    if os.path.isdir(args.path):
        for root, dirs, files in os.walk(args.path):
            dirs[:] = [d for d in dirs if d not in ('node_modules', '.git')]
            for fname in files:
                if fname.endswith('.sol'):
                    fpath = os.path.join(root, fname)
                    with open(fpath) as f:
                        oracle_findings.extend(scan_oracle_patterns(f.read()))
    elif os.path.isfile(args.path):
        with open(args.path) as f:
            oracle_findings = scan_oracle_patterns(f.read())
    print(f"  {len(oracle_findings)} oracle findings")
    results["tools"]["oracle"] = len(oracle_findings)

    # Randomness scan
    print("\n" + "=" * 50)
    print("[3/3] Weak Randomness Scanner")
    print("=" * 50)
    from vrf_bias_detector import scan_randomness_patterns
    rand_findings = []
    if os.path.isdir(args.path):
        for root, dirs, files in os.walk(args.path):
            dirs[:] = [d for d in dirs if d not in ('node_modules', '.git')]
            for fname in files:
                if fname.endswith('.sol'):
                    fpath = os.path.join(root, fname)
                    with open(fpath) as f:
                        rand_findings.extend(scan_randomness_patterns(f.read()))
    elif os.path.isfile(args.path):
        with open(args.path) as f:
            rand_findings = scan_randomness_patterns(f.read())
    print(f"  {len(rand_findings)} randomness findings")
    results["tools"]["randomness"] = len(rand_findings)

    # Summary
    total = sum(results["tools"].values())
    print("\n" + "=" * 50)
    print(f"TOTAL: {total} findings across all scanners")
    print("=" * 50)

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="G.O.D. Bounty Hunter - Unified Security Toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Run 'bounty_hunter.py targets' for active bounty targets."
    )
    subparsers = parser.add_subparsers(dest='command')

    # targets
    subparsers.add_parser('targets', help='Show active bounty targets')

    # ecdsa
    p_ecdsa = subparsers.add_parser('ecdsa', help='ECDSA vulnerability scanner')
    p_ecdsa.add_argument('path', nargs='?', help='File or directory to scan')
    p_ecdsa.add_argument('--targets', action='store_true')
    p_ecdsa.add_argument('--output', type=str)

    # zk
    p_zk = subparsers.add_parser('zk', help='ZK circuit underconstrained detector')
    p_zk.add_argument('path', nargs='?', help='.r1cs or .json file')
    p_zk.add_argument('--demo', action='store_true')
    p_zk.add_argument('--output', type=str)

    # oracle
    p_oracle = subparsers.add_parser('oracle', help='TDA oracle manipulation detector')
    p_oracle.add_argument('--demo', action='store_true')
    p_oracle.add_argument('--scan', type=str, help='Solidity file')
    p_oracle.add_argument('--threshold', type=float, default=0.4)
    p_oracle.add_argument('--output', type=str)

    # vrf
    p_vrf = subparsers.add_parser('vrf', help='VRF/randomness bias detector')
    p_vrf.add_argument('--demo', action='store_true')
    p_vrf.add_argument('--scan', type=str, help='Solidity file')
    p_vrf.add_argument('--test-file', type=str, help='Binary file to test')
    p_vrf.add_argument('--output', type=str)

    # factor
    p_factor = subparsers.add_parser('factor', help='BABEL tower factorization')
    p_factor.add_argument('--demo', action='store_true')
    p_factor.add_argument('--qday', action='store_true')
    p_factor.add_argument('--number', type=int, help='Number to factor')
    p_factor.add_argument('--output', type=str)

    # peaked
    p_peaked = subparsers.add_parser('peaked', help='Peaked circuit solver')
    p_peaked.add_argument('--challenge', action='store_true')
    p_peaked.add_argument('--demo', action='store_true')

    # scan (full audit)
    p_scan = subparsers.add_parser('scan', help='Full audit of Solidity codebase')
    p_scan.add_argument('path', help='File or directory to scan')
    p_scan.add_argument('--output', type=str)

    args = parser.parse_args()

    if args.command == 'targets':
        print(BANNER)
        print(TARGETS)
    elif args.command == 'ecdsa':
        cmd_ecdsa(args)
    elif args.command == 'zk':
        cmd_zk(args)
    elif args.command == 'oracle':
        cmd_oracle(args)
    elif args.command == 'vrf':
        cmd_vrf(args)
    elif args.command == 'factor':
        cmd_factor(args)
    elif args.command == 'peaked':
        cmd_peaked(args)
    elif args.command == 'scan':
        cmd_scan(args)
    else:
        print(BANNER)
        parser.print_help()


if __name__ == '__main__':
    main()
