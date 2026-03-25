#!/usr/bin/env python3
"""
ECDSA Signature Vulnerability Scanner for Smart Contracts

Scans Solidity smart contracts for common ECDSA/ecrecover vulnerabilities
that qualify for bug bounties on Immunefi, Sherlock, Code4rena, etc.

Vulnerability Classes Detected:
    1. Missing address(0) check after ecrecover
    2. Signature malleability (no s-value constraint to lower half)
    3. Missing nonce/replay protection
    4. Cross-chain replay (missing chainId in signed data)
    5. Raw ecrecover without OpenZeppelin ECDSA wrapper
    6. Signature reuse / missing invalidation
    7. Permit front-running vulnerabilities
    8. EIP-712 domain separator issues

Usage:
    python ecdsa_vuln_scanner.py <contract_file_or_directory>
    python ecdsa_vuln_scanner.py --etherscan <address> --api-key <KEY>
"""

import re
import os
import sys
import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Tuple
from enum import Enum


class Severity(Enum):
    CRITICAL = "critical"    # Direct fund theft possible
    HIGH = "high"            # Significant security impact
    MEDIUM = "medium"        # Conditional exploitation
    LOW = "low"              # Best practice violation
    INFO = "informational"   # Style / gas optimization


@dataclass
class Finding:
    vulnerability: str
    severity: Severity
    file_path: str
    line_number: int
    code_snippet: str
    description: str
    recommendation: str
    bounty_relevance: str
    estimated_payout: str


@dataclass
class ScanReport:
    files_scanned: int
    findings: List[Finding] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def to_json(self) -> str:
        data = {
            "files_scanned": self.files_scanned,
            "total_findings": len(self.findings),
            "by_severity": self.summary,
            "findings": [
                {**asdict(f), "severity": f.severity.value}
                for f in self.findings
            ]
        }
        return json.dumps(data, indent=2)


class ECDSAVulnScanner:
    """
    Scans Solidity source code for ECDSA signature handling vulnerabilities.
    """

    def __init__(self):
        self.findings: List[Finding] = []

    def scan_file(self, filepath: str) -> List[Finding]:
        """Scan a single Solidity file."""
        with open(filepath, 'r') as f:
            content = f.read()
        lines = content.split('\n')

        findings = []
        findings.extend(self._check_raw_ecrecover(filepath, content, lines))
        findings.extend(self._check_missing_zero_check(filepath, content, lines))
        findings.extend(self._check_signature_malleability(filepath, content, lines))
        findings.extend(self._check_missing_nonce(filepath, content, lines))
        findings.extend(self._check_missing_chainid(filepath, content, lines))
        findings.extend(self._check_missing_deadline(filepath, content, lines))
        findings.extend(self._check_signature_reuse(filepath, content, lines))
        findings.extend(self._check_permit_issues(filepath, content, lines))
        findings.extend(self._check_eip712_issues(filepath, content, lines))

        self.findings.extend(findings)
        return findings

    def scan_directory(self, dirpath: str) -> List[Finding]:
        """Recursively scan a directory for .sol files."""
        findings = []
        for root, dirs, files in os.walk(dirpath):
            # Skip common non-source directories
            dirs[:] = [d for d in dirs if d not in ('node_modules', '.git', 'cache', 'artifacts')]
            for fname in files:
                if fname.endswith('.sol'):
                    fpath = os.path.join(root, fname)
                    findings.extend(self.scan_file(fpath))
        return findings

    # ─── Vulnerability Checks ─────────────────────────────────────────────

    def _check_raw_ecrecover(self, filepath, content, lines) -> List[Finding]:
        """Check for raw ecrecover usage without OpenZeppelin wrapper."""
        findings = []
        pattern = re.compile(r'\becrecover\s*\(', re.IGNORECASE)

        # Check if OpenZeppelin ECDSA is imported
        uses_oz = bool(re.search(r'import.*ECDSA', content))

        for i, line in enumerate(lines):
            if pattern.search(line) and not line.strip().startswith('//'):
                # Check if this is inside a comment block
                before = '\n'.join(lines[:i])
                if before.count('/*') > before.count('*/'):
                    continue

                if not uses_oz:
                    findings.append(Finding(
                        vulnerability="RAW_ECRECOVER",
                        severity=Severity.HIGH,
                        file_path=filepath,
                        line_number=i + 1,
                        code_snippet=line.strip(),
                        description=(
                            "Raw ecrecover() used without OpenZeppelin ECDSA wrapper. "
                            "This is vulnerable to signature malleability attacks. "
                            "ecrecover returns address(0) for invalid signatures, "
                            "which can bypass authorization if not checked."
                        ),
                        recommendation=(
                            "Use OpenZeppelin's ECDSA.recover() which handles "
                            "malleability protection and zero-address checks."
                        ),
                        bounty_relevance="Immunefi Top 10 vulnerability class",
                        estimated_payout="$10K-$500K depending on impact"
                    ))
        return findings

    def _check_missing_zero_check(self, filepath, content, lines) -> List[Finding]:
        """Check for missing address(0) validation after ecrecover."""
        findings = []
        ecrecover_pattern = re.compile(
            r'(\w+)\s*=\s*ecrecover\s*\('
        )

        for i, line in enumerate(lines):
            match = ecrecover_pattern.search(line)
            if match:
                var_name = match.group(1)
                # Look ahead 10 lines for address(0) check
                context = '\n'.join(lines[i:min(i+10, len(lines))])
                zero_checks = [
                    f'{var_name} != address(0)',
                    f'{var_name} == address(0)',
                    f'require({var_name} !=',
                    f'if ({var_name} ==',
                    f'assert({var_name}',
                ]
                has_zero_check = any(check in context for check in zero_checks)

                if not has_zero_check:
                    findings.append(Finding(
                        vulnerability="MISSING_ZERO_ADDRESS_CHECK",
                        severity=Severity.CRITICAL,
                        file_path=filepath,
                        line_number=i + 1,
                        code_snippet=line.strip(),
                        description=(
                            f"ecrecover result stored in '{var_name}' without "
                            "checking for address(0). Invalid signatures return "
                            "address(0), potentially allowing unauthorized access "
                            "if compared against an uninitialized state variable."
                        ),
                        recommendation=(
                            f"Add: require({var_name} != address(0), "
                            '"Invalid signature");'
                        ),
                        bounty_relevance="Critical - direct auth bypass possible",
                        estimated_payout="$50K-$2M+ (auth bypass = fund theft)"
                    ))
        return findings

    def _check_signature_malleability(self, filepath, content, lines) -> List[Finding]:
        """Check for ECDSA signature malleability (unrestricted s-value)."""
        findings = []

        # If using ecrecover directly, check for s-value validation
        if 'ecrecover' not in content:
            return findings

        uses_oz_ecdsa = bool(re.search(r'ECDSA\.(recover|tryRecover)', content))
        if uses_oz_ecdsa:
            return findings  # OZ handles this

        # Check for s-value constraint (secp256k1n/2)
        has_s_check = any(pattern in content for pattern in [
            '0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0',
            'secp256k1n',
            's <= 0x7FFF',
            's < 0x7FFF',
            'lower half',
        ])

        if not has_s_check:
            # Find the ecrecover line
            for i, line in enumerate(lines):
                if 'ecrecover' in line and not line.strip().startswith('//'):
                    findings.append(Finding(
                        vulnerability="SIGNATURE_MALLEABILITY",
                        severity=Severity.HIGH,
                        file_path=filepath,
                        line_number=i + 1,
                        code_snippet=line.strip(),
                        description=(
                            "ECDSA signatures are malleable: for any (v,r,s), "
                            "a valid alternative (v',r,s') exists where "
                            "s' = secp256k1n - s. Without constraining s to "
                            "the lower half of the curve order, signatures "
                            "can be replayed with modified s-values."
                        ),
                        recommendation=(
                            "Require s <= 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
                            "5D576E7357A4501DDFE92F46681B20A0 (secp256k1n/2), "
                            "or use OpenZeppelin's ECDSA library."
                        ),
                        bounty_relevance="Immunefi Top 10: Signature Malleability",
                        estimated_payout="$10K-$100K"
                    ))
                    break
        return findings

    def _check_missing_nonce(self, filepath, content, lines) -> List[Finding]:
        """Check for missing nonce in signature verification (replay attack)."""
        findings = []

        has_sig_verify = any(x in content for x in ['ecrecover', 'ECDSA.recover'])
        if not has_sig_verify:
            return findings

        has_nonce = any(x in content.lower() for x in ['nonce', '_nonce', 'nonces'])

        if not has_nonce:
            # Find signature verification location
            for i, line in enumerate(lines):
                if any(x in line for x in ['ecrecover', 'ECDSA.recover']):
                    if not line.strip().startswith('//'):
                        findings.append(Finding(
                            vulnerability="MISSING_NONCE_REPLAY",
                            severity=Severity.HIGH,
                            file_path=filepath,
                            line_number=i + 1,
                            code_snippet=line.strip(),
                            description=(
                                "Signature verification without nonce tracking. "
                                "Valid signatures can be replayed multiple times, "
                                "potentially draining funds or repeating actions."
                            ),
                            recommendation=(
                                "Include an incrementing nonce per-signer in the "
                                "signed message and track used nonces on-chain."
                            ),
                            bounty_relevance="High - replay attacks can drain funds",
                            estimated_payout="$25K-$500K"
                        ))
                        break
        return findings

    def _check_missing_chainid(self, filepath, content, lines) -> List[Finding]:
        """Check for missing chain ID in signed data (cross-chain replay)."""
        findings = []

        has_sig = any(x in content for x in ['ecrecover', 'ECDSA.recover'])
        if not has_sig:
            return findings

        has_chainid = any(x in content for x in [
            'block.chainid', 'chainId', 'chain_id', 'DOMAIN_SEPARATOR',
            'domainSeparator', 'EIP712'
        ])

        if not has_chainid:
            for i, line in enumerate(lines):
                if any(x in line for x in ['ecrecover', 'ECDSA.recover']):
                    if not line.strip().startswith('//'):
                        findings.append(Finding(
                            vulnerability="MISSING_CHAINID_CROSSCHAIN_REPLAY",
                            severity=Severity.HIGH,
                            file_path=filepath,
                            line_number=i + 1,
                            code_snippet=line.strip(),
                            description=(
                                "Signature does not include chain ID. Signatures "
                                "valid on one chain can be replayed on another "
                                "(e.g., Ethereum mainnet sig replayed on Polygon)."
                            ),
                            recommendation=(
                                "Include block.chainid in the signed hash, "
                                "preferably via EIP-712 domain separator."
                            ),
                            bounty_relevance="Cross-chain replay = fund theft on L2s",
                            estimated_payout="$25K-$250K"
                        ))
                        break
        return findings

    def _check_missing_deadline(self, filepath, content, lines) -> List[Finding]:
        """Check for signatures without expiration/deadline."""
        findings = []

        has_sig = any(x in content for x in ['ecrecover', 'ECDSA.recover'])
        if not has_sig:
            return findings

        has_deadline = any(x in content.lower() for x in [
            'deadline', 'expir', 'validuntil', 'valid_until', 'block.timestamp'
        ])

        if not has_deadline:
            for i, line in enumerate(lines):
                if any(x in line for x in ['ecrecover', 'ECDSA.recover']):
                    if not line.strip().startswith('//'):
                        findings.append(Finding(
                            vulnerability="MISSING_SIGNATURE_DEADLINE",
                            severity=Severity.MEDIUM,
                            file_path=filepath,
                            line_number=i + 1,
                            code_snippet=line.strip(),
                            description=(
                                "Signature has no expiration timestamp. "
                                "Old signatures remain valid indefinitely, "
                                "increasing the window for replay attacks."
                            ),
                            recommendation=(
                                "Include a deadline timestamp in the signed "
                                "message and check block.timestamp <= deadline."
                            ),
                            bounty_relevance="Medium severity on most programs",
                            estimated_payout="$5K-$25K"
                        ))
                        break
        return findings

    def _check_signature_reuse(self, filepath, content, lines) -> List[Finding]:
        """Check for missing signature invalidation after use."""
        findings = []

        has_sig = any(x in content for x in ['ecrecover', 'ECDSA.recover'])
        if not has_sig:
            return findings

        # Check for signature tracking/invalidation
        has_tracking = any(x in content for x in [
            'usedSignatures', 'used_signatures', 'invalidated',
            'consumed', 'executed[', 'processed[',
            'delete ', 'nonces[',
        ])

        if not has_tracking:
            # Only flag if there's an action after verification (not view-only)
            has_state_change = any(x in content for x in [
                'transfer(', 'transferFrom(', 'mint(', 'burn(',
                '.call{value', 'selfdestruct', 'delegatecall',
            ])
            if has_state_change:
                for i, line in enumerate(lines):
                    if any(x in line for x in ['ecrecover', 'ECDSA.recover']):
                        if not line.strip().startswith('//'):
                            findings.append(Finding(
                                vulnerability="SIGNATURE_REUSE",
                                severity=Severity.HIGH,
                                file_path=filepath,
                                line_number=i + 1,
                                code_snippet=line.strip(),
                                description=(
                                    "Signature used for state-changing operation "
                                    "without tracking/invalidation. Same signature "
                                    "can be submitted multiple times."
                                ),
                                recommendation=(
                                    "Track used signatures in a mapping and reject "
                                    "duplicates, or use incrementing nonces."
                                ),
                                bounty_relevance="Critical - repeated fund extraction",
                                estimated_payout="$50K-$1M+"
                            ))
                            break
        return findings

    def _check_permit_issues(self, filepath, content, lines) -> List[Finding]:
        """Check for ERC-2612 permit implementation issues."""
        findings = []

        if 'permit' not in content.lower():
            return findings

        # Check for permit without proper domain separator caching
        has_permit_func = bool(re.search(r'function\s+permit\s*\(', content))
        if not has_permit_func:
            return findings

        # Check for immutable domain separator (doesn't update on chain fork)
        if 'immutable' in content and 'DOMAIN_SEPARATOR' in content:
            if 'block.chainid' not in content or '_domainSeparator()' not in content:
                for i, line in enumerate(lines):
                    if 'DOMAIN_SEPARATOR' in line and 'immutable' in line:
                        findings.append(Finding(
                            vulnerability="PERMIT_DOMAIN_SEPARATOR_NOT_RECOMPUTED",
                            severity=Severity.MEDIUM,
                            file_path=filepath,
                            line_number=i + 1,
                            code_snippet=line.strip(),
                            description=(
                                "DOMAIN_SEPARATOR is immutable and won't update "
                                "after chain fork, enabling cross-fork replay of "
                                "permit signatures."
                            ),
                            recommendation=(
                                "Recompute DOMAIN_SEPARATOR dynamically when "
                                "block.chainid differs from cached value."
                            ),
                            bounty_relevance="Medium - exploitable during chain forks",
                            estimated_payout="$5K-$50K"
                        ))
                        break
        return findings

    def _check_eip712_issues(self, filepath, content, lines) -> List[Finding]:
        """Check for EIP-712 implementation issues."""
        findings = []

        if 'abi.encodePacked' in content and 'ecrecover' in content:
            for i, line in enumerate(lines):
                if 'abi.encodePacked' in line:
                    # Check if this feeds into a hash used for ecrecover
                    context = '\n'.join(lines[max(0, i-5):min(i+5, len(lines))])
                    if 'keccak256' in context:
                        findings.append(Finding(
                            vulnerability="ABI_ENCODEPACKED_HASH_COLLISION",
                            severity=Severity.HIGH,
                            file_path=filepath,
                            line_number=i + 1,
                            code_snippet=line.strip(),
                            description=(
                                "abi.encodePacked used with dynamic types before "
                                "hashing for signature verification. This is vulnerable "
                                "to hash collision attacks since encodePacked doesn't "
                                "pad dynamic types."
                            ),
                            recommendation=(
                                "Use abi.encode() instead of abi.encodePacked() "
                                "for signature hash construction, or use EIP-712 "
                                "structured data hashing."
                            ),
                            bounty_relevance="High - signature forgery possible",
                            estimated_payout="$25K-$250K"
                        ))
        return findings

    def generate_report(self) -> ScanReport:
        """Generate scan report."""
        severity_counts = {}
        for f in self.findings:
            s = f.severity.value
            severity_counts[s] = severity_counts.get(s, 0) + 1

        return ScanReport(
            files_scanned=len(set(f.file_path for f in self.findings)),
            findings=self.findings,
            summary=severity_counts
        )


# ─── Contract Fetcher (Etherscan/Sourcify) ────────────────────────────────

def fetch_contract_source(address: str, api_key: str,
                          chain: str = "mainnet") -> Optional[str]:
    """Fetch verified contract source from Etherscan."""
    import urllib.request

    base_urls = {
        "mainnet": "https://api.etherscan.io/api",
        "polygon": "https://api.polygonscan.com/api",
        "arbitrum": "https://api.arbiscan.io/api",
        "optimism": "https://api-optimistic.etherscan.io/api",
        "base": "https://api.basescan.org/api",
    }

    base_url = base_urls.get(chain, base_urls["mainnet"])
    url = (f"{base_url}?module=contract&action=getsourcecode"
           f"&address={address}&apikey={api_key}")

    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read())
            if data["status"] == "1" and data["result"]:
                return data["result"][0]["SourceCode"]
    except Exception as e:
        print(f"Error fetching contract: {e}")
    return None


# ─── High-Value Target Identification ────────────────────────────────────────

IMMUNEFI_ECDSA_TARGETS = [
    {
        "name": "Axelar Network",
        "bounty": "$500K critical",
        "scope": "ECDSA module in tofn (Rust) + Solidity gateway",
        "url": "https://immunefi.com/bug-bounty/axelarnetwork/",
        "chain": "multichain",
    },
    {
        "name": "Threshold Network",
        "bounty": "$500K critical",
        "scope": "ECDSA contracts in keep-core/solidity/ecdsa",
        "url": "https://immunefi.com/bug-bounty/thresholdnetwork/",
        "chain": "mainnet",
    },
    {
        "name": "Sky (MakerDAO)",
        "bounty": "10% of funds up to $10M",
        "scope": "Smart contracts with signature verification",
        "url": "https://immunefi.com/bug-bounty/sky/",
        "chain": "mainnet",
    },
    {
        "name": "Wormhole",
        "bounty": "Up to $2M critical",
        "scope": "Cross-chain bridge signature verification",
        "url": "https://immunefi.com/bug-bounty/wormhole/",
        "chain": "multichain",
    },
    {
        "name": "Injective",
        "bounty": "$500K critical",
        "scope": "Blockchain/DLT + Smart Contracts",
        "url": "https://immunefi.com/bug-bounty/injective/",
        "chain": "injective",
    },
    {
        "name": "ENS",
        "bounty": "10% of funds up to $250K",
        "scope": "Smart contracts",
        "url": "https://immunefi.com/bug-bounty/ens/",
        "chain": "mainnet",
    },
]


def print_targets():
    """Print high-value ECDSA-related bounty targets."""
    print("\n" + "=" * 70)
    print("  HIGH-VALUE ECDSA BOUNTY TARGETS (Immunefi)")
    print("=" * 70)
    for t in IMMUNEFI_ECDSA_TARGETS:
        print(f"\n  {t['name']}")
        print(f"    Bounty: {t['bounty']}")
        print(f"    Scope: {t['scope']}")
        print(f"    URL: {t['url']}")
        print(f"    Chain: {t['chain']}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="ECDSA Vulnerability Scanner for Smart Contracts"
    )
    parser.add_argument('path', nargs='?', help='File or directory to scan')
    parser.add_argument('--etherscan', type=str, help='Contract address to fetch')
    parser.add_argument('--api-key', type=str, help='Etherscan API key')
    parser.add_argument('--chain', type=str, default='mainnet',
                       help='Chain (mainnet, polygon, arbitrum, optimism, base)')
    parser.add_argument('--targets', action='store_true',
                       help='Print high-value bounty targets')
    parser.add_argument('--output', type=str, help='Output JSON report path')

    args = parser.parse_args()

    if args.targets:
        print_targets()
        return

    scanner = ECDSAVulnScanner()

    if args.etherscan:
        if not args.api_key:
            print("Error: --api-key required with --etherscan")
            sys.exit(1)
        source = fetch_contract_source(args.etherscan, args.api_key, args.chain)
        if source:
            tmpfile = f"/tmp/contract_{args.etherscan[:10]}.sol"
            with open(tmpfile, 'w') as f:
                f.write(source)
            scanner.scan_file(tmpfile)
        else:
            print("Failed to fetch contract source")
            sys.exit(1)
    elif args.path:
        if os.path.isfile(args.path):
            scanner.scan_file(args.path)
        elif os.path.isdir(args.path):
            scanner.scan_directory(args.path)
        else:
            print(f"Error: {args.path} not found")
            sys.exit(1)
    else:
        parser.print_help()
        return

    report = scanner.generate_report()

    # Print findings
    print(f"\n{'='*70}")
    print(f"  SCAN RESULTS: {len(report.findings)} findings")
    print(f"{'='*70}")

    for f in report.findings:
        icon = {"critical": "!!!", "high": "!!", "medium": "!", "low": "~", "informational": "i"}
        print(f"\n  [{icon.get(f.severity.value, '?')}] {f.severity.value.upper()}: {f.vulnerability}")
        print(f"      File: {f.file_path}:{f.line_number}")
        print(f"      Code: {f.code_snippet[:80]}")
        print(f"      {f.description[:120]}...")
        print(f"      Bounty: {f.estimated_payout}")

    if args.output:
        with open(args.output, 'w') as f:
            f.write(report.to_json())
        print(f"\nReport saved to {args.output}")


if __name__ == '__main__':
    main()
