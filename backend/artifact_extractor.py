import re
from typing import Dict, List, Set

class ArtifactExtractor:
    """Extract investigation artifacts from scraped content."""
    
    def __init__(self):
        self.patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'btc': r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b|bc1[a-z0-9]{39,59}\b',
            'eth': r'\b0x[a-fA-F0-9]{40}\b',
            'xmr': r'\b4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}\b',
            'ltc': r'\b[LM3][a-km-zA-HJ-NP-Z1-9]{26,33}\b',
            'telegram': r'@[a-zA-Z0-9_]{5,32}\b|t\.me/[a-zA-Z0-9_]{5,32}',
            'phone': r'\+?[1-9]\d{1,14}|\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',
            'ipv4': r'\b(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
            'onion': r'\b[a-z2-7]{16,56}\.onion\b',
            'domain': r'\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}\b',
            'md5': r'\b[a-fA-F0-9]{32}\b',
            'sha1': r'\b[a-fA-F0-9]{40}\b',
            'sha256': r'\b[a-fA-F0-9]{64}\b',
            'cve': r'\bCVE-\d{4}-\d{4,}\b',
            'url': r'https?://(?:[a-zA-Z]|[0-9]|[$\-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            'jwt': r'eyJ[A-Za-z0-9_\-\.]+\.eyJ[A-Za-z0-9_\-\.]+\.[A-Za-z0-9_\-\.]*',
            'aws_key': r'AKIA[0-9A-Z]{16}',
            'api_key': r'(?:api[_\-]?key|apikey|api_secret)["\s:=]+[a-zA-Z0-9\-_\.]{16,}',
            'pgp_key': r'-----BEGIN PGP PUBLIC KEY BLOCK-----[\s\S]+?-----END PGP PUBLIC KEY BLOCK-----',
            'xmpp': r'\b[A-Za-z0-9._%+-]+@(?:jabber\.[a-z.]+|chat\.[a-z.]+|xmpp\.[a-z.]+|secure\.[a-z.]+|conversations\.im|rows\.io|systemli\.org|calyxinstitute\.org)\b',
            'tox_id': r'\b[a-fA-F0-9]{76}\b',
            'session_id': r'\b05[a-fA-F0-9]{64}\b',
        }
        
        # Reserved IP ranges to exclude
        self.reserved_ips = {
            r'^127\.',
            r'^192\.168\.',
            r'^10\.',
            r'^172\.(?:1[6-9]|2[0-9]|3[01])\.',
            r'^0\.0\.0\.0',
            r'^255\.255\.255\.255',
        }
    
    def _is_valid_ipv4(self, ip: str) -> bool:
        """Check if IP is not in reserved ranges."""
        for reserved_pattern in self.reserved_ips:
            if re.match(reserved_pattern, ip):
                return False
        return True
    
    def _is_valid_domain(self, domain: str) -> bool:
        """Filter out false positive domains."""
        excluded_extensions = ('.png', '.jpg', '.gif', '.css', '.js', '.woff', '.ttf', '.ico', '.svg')
        if domain.endswith(excluded_extensions):
            return False
        if domain.count('.') > 3:
            return False
        return True
    
    def _normalize_hash(self, hash_val: str) -> str:
        """Normalize hash to lowercase."""
        return hash_val.lower() if hash_val else hash_val
    
    def extract(self, content: str) -> Dict[str, Set[str]]:
        """Extract all artifacts from content."""
        artifacts = {key: set() for key in self.patterns.keys()}
        
        for artifact_type, pattern in self.patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            
            if artifact_type == 'ipv4':
                matches = [m for m in matches if self._is_valid_ipv4(m)]
            elif artifact_type == 'domain':
                matches = [m for m in matches if self._is_valid_domain(m)]
            elif artifact_type in ('md5', 'sha1', 'sha256', 'tox_id', 'session_id'):
                matches = [self._normalize_hash(m) for m in matches]
            elif artifact_type == 'email':
                matches = [e for e in matches if len(e) > 5 and e.count('.') >= 1]
            elif artifact_type in ('cve', 'url', 'jwt', 'aws_key'):
                pass
            elif artifact_type == 'api_key':
                matches = [m[:64] for m in matches]
            
            artifacts[artifact_type].update(matches)
        
        return {k: v for k, v in artifacts.items() if v}
    
    def format_artifacts(self, all_artifacts: Dict[str, Dict[str, Set[str]]]) -> str:
        """Format artifacts for display."""
        output = []
        artifact_labels = {
            'email': 'Email Addresses',
            'btc': 'Bitcoin Addresses',
            'eth': 'Ethereum Addresses',
            'xmr': 'Monero Addresses',
            'ltc': 'Litecoin Addresses',
            'telegram': 'Telegram Handles',
            'phone': 'Phone Numbers',
            'ipv4': 'IP Addresses',
            'onion': 'Onion Domains',
            'domain': 'Domains',
            'md5': 'MD5 Hashes',
            'sha1': 'SHA1 Hashes',
            'sha256': 'SHA256 Hashes',
            'cve': 'CVE Identifiers',
            'url': 'URLs',
            'jwt': 'JWT Tokens',
            'aws_key': 'AWS Access Keys',
            'api_key': 'API Keys',
            'pgp_key': 'PGP Public Keys',
            'xmpp': 'XMPP Handles',
            'tox_id': 'Tox IDs',
            'session_id': 'Session IDs',
        }
        
        for url, artifacts in all_artifacts.items():
            if not artifacts:
                continue
            output.append(f"\n**Source:** {url}")
            for artifact_type, values in sorted(artifacts.items()):
                if values:
                    label = artifact_labels.get(artifact_type, artifact_type.title())
                    max_display = 20 if artifact_type in ('domain', 'url') else 10
                    if artifact_type == 'pgp_key':
                        display_values = [f"PGP Public Key Block ({len(val)} chars)" for val in sorted(values)[:max_display]]
                    else:
                        display_values = sorted(values)[:max_display]
                    output.append(f"  - {label}: {', '.join(display_values)}")
        
        return '\n'.join(output) if output else "No artifacts extracted."
