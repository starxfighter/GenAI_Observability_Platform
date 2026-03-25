"""
PII Detection and Redaction Module

Provides comprehensive PII detection and redaction capabilities for the
GenAI observability platform. Supports various PII types, configurable
rules, and multiple redaction strategies.
"""

import re
import json
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Pattern, Set, Tuple, Union
import logging

logger = logging.getLogger(__name__)


class PIIType(str, Enum):
    """Types of Personally Identifiable Information."""

    # Contact Information
    EMAIL = "email"
    PHONE_NUMBER = "phone_number"
    ADDRESS = "address"

    # Identity Documents
    SSN = "ssn"
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    NATIONAL_ID = "national_id"

    # Financial
    CREDIT_CARD = "credit_card"
    BANK_ACCOUNT = "bank_account"
    IBAN = "iban"

    # Healthcare
    MEDICAL_RECORD = "medical_record"
    HEALTH_INSURANCE_ID = "health_insurance_id"

    # Authentication
    PASSWORD = "password"
    API_KEY = "api_key"
    SECRET_KEY = "secret_key"
    AUTH_TOKEN = "auth_token"
    JWT_TOKEN = "jwt_token"

    # Personal
    NAME = "name"
    DATE_OF_BIRTH = "date_of_birth"
    AGE = "age"

    # Network
    IP_ADDRESS = "ip_address"
    MAC_ADDRESS = "mac_address"

    # Custom
    CUSTOM = "custom"


class RedactionStrategy(str, Enum):
    """Strategies for redacting PII."""

    # Replace with placeholder
    MASK = "mask"  # [REDACTED]
    TYPE_MASK = "type_mask"  # [EMAIL_REDACTED]

    # Partial masking
    PARTIAL = "partial"  # j***@example.com

    # Hash the value
    HASH = "hash"  # sha256 hash
    HASH_PREFIX = "hash_prefix"  # First 8 chars of hash

    # Replace with fake data
    FAKE = "fake"  # Generate fake data

    # Remove entirely
    REMOVE = "remove"

    # Encrypt
    ENCRYPT = "encrypt"


@dataclass
class PIIPattern:
    """A pattern for detecting PII."""

    pii_type: PIIType
    pattern: str
    description: str = ""
    confidence: float = 0.9
    enabled: bool = True
    compiled_pattern: Optional[Pattern] = field(default=None, repr=False)

    def __post_init__(self):
        if self.compiled_pattern is None:
            try:
                self.compiled_pattern = re.compile(self.pattern, re.IGNORECASE)
            except re.error as e:
                logger.error(f"Invalid regex pattern for {self.pii_type}: {e}")
                self.enabled = False


@dataclass
class PIIMatch:
    """A detected PII match."""

    pii_type: PIIType
    value: str
    start: int
    end: int
    confidence: float
    pattern_description: str = ""


@dataclass
class RedactionResult:
    """Result of a redaction operation."""

    original_text: str
    redacted_text: str
    matches: List[PIIMatch]
    redaction_map: Dict[str, str]  # Maps redacted placeholders to original values (if needed)


class PIIDetector:
    """
    Detects PII in text using configurable patterns.
    """

    # Default patterns for common PII types
    DEFAULT_PATTERNS: List[PIIPattern] = [
        # Email
        PIIPattern(
            pii_type=PIIType.EMAIL,
            pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            description="Email address",
            confidence=0.95,
        ),
        # US Phone Numbers
        PIIPattern(
            pii_type=PIIType.PHONE_NUMBER,
            pattern=r'\b(?:\+1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
            description="US phone number",
            confidence=0.85,
        ),
        # International Phone Numbers
        PIIPattern(
            pii_type=PIIType.PHONE_NUMBER,
            pattern=r'\b\+[1-9]\d{1,14}\b',
            description="International phone number (E.164)",
            confidence=0.9,
        ),
        # US SSN
        PIIPattern(
            pii_type=PIIType.SSN,
            pattern=r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b',
            description="US Social Security Number",
            confidence=0.9,
        ),
        # Credit Card Numbers (Luhn-compatible patterns)
        PIIPattern(
            pii_type=PIIType.CREDIT_CARD,
            pattern=r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12}|3(?:0[0-5]|[68][0-9])[0-9]{11})\b',
            description="Credit card number (Visa, MC, Amex, Discover, Diners)",
            confidence=0.95,
        ),
        # Credit Card with spaces/dashes
        PIIPattern(
            pii_type=PIIType.CREDIT_CARD,
            pattern=r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            description="Credit card number with separators",
            confidence=0.85,
        ),
        # IPv4 Address
        PIIPattern(
            pii_type=PIIType.IP_ADDRESS,
            pattern=r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
            description="IPv4 address",
            confidence=0.9,
        ),
        # IPv6 Address
        PIIPattern(
            pii_type=PIIType.IP_ADDRESS,
            pattern=r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b',
            description="IPv6 address",
            confidence=0.9,
        ),
        # MAC Address
        PIIPattern(
            pii_type=PIIType.MAC_ADDRESS,
            pattern=r'\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b',
            description="MAC address",
            confidence=0.95,
        ),
        # AWS Access Key
        PIIPattern(
            pii_type=PIIType.API_KEY,
            pattern=r'\b(?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b',
            description="AWS Access Key ID",
            confidence=0.98,
        ),
        # AWS Secret Key
        PIIPattern(
            pii_type=PIIType.SECRET_KEY,
            pattern=r'\b[A-Za-z0-9/+=]{40}\b',
            description="Potential AWS Secret Access Key",
            confidence=0.7,
        ),
        # Generic API Keys
        PIIPattern(
            pii_type=PIIType.API_KEY,
            pattern=r'\b(?:api[_-]?key|apikey|api_secret)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?',
            description="Generic API key",
            confidence=0.85,
        ),
        # JWT Tokens
        PIIPattern(
            pii_type=PIIType.JWT_TOKEN,
            pattern=r'\beyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*\b',
            description="JWT token",
            confidence=0.95,
        ),
        # Bearer Tokens
        PIIPattern(
            pii_type=PIIType.AUTH_TOKEN,
            pattern=r'\b[Bb]earer\s+[a-zA-Z0-9_\-\.]+\b',
            description="Bearer token",
            confidence=0.9,
        ),
        # Password in common formats
        PIIPattern(
            pii_type=PIIType.PASSWORD,
            pattern=r'(?:password|passwd|pwd)["\']?\s*[:=]\s*["\']?([^\s"\']{3,})["\']?',
            description="Password in key-value format",
            confidence=0.9,
        ),
        # Date of Birth
        PIIPattern(
            pii_type=PIIType.DATE_OF_BIRTH,
            pattern=r'\b(?:0[1-9]|1[0-2])[/\-](?:0[1-9]|[12][0-9]|3[01])[/\-](?:19|20)\d{2}\b',
            description="Date of birth (MM/DD/YYYY)",
            confidence=0.7,
        ),
        # Date of Birth (ISO format)
        PIIPattern(
            pii_type=PIIType.DATE_OF_BIRTH,
            pattern=r'\b(?:19|20)\d{2}[-/](?:0[1-9]|1[0-2])[-/](?:0[1-9]|[12][0-9]|3[01])\b',
            description="Date of birth (YYYY-MM-DD)",
            confidence=0.7,
        ),
        # US Passport
        PIIPattern(
            pii_type=PIIType.PASSPORT,
            pattern=r'\b[A-Z]\d{8}\b',
            description="US Passport number",
            confidence=0.6,
        ),
        # IBAN
        PIIPattern(
            pii_type=PIIType.IBAN,
            pattern=r'\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}(?:[A-Z0-9]?){0,16}\b',
            description="International Bank Account Number",
            confidence=0.9,
        ),
        # US Bank Account/Routing
        PIIPattern(
            pii_type=PIIType.BANK_ACCOUNT,
            pattern=r'\b\d{9,17}\b',
            description="Potential bank account number",
            confidence=0.3,  # Low confidence - needs context
        ),
    ]

    def __init__(
        self,
        patterns: Optional[List[PIIPattern]] = None,
        use_defaults: bool = True,
        min_confidence: float = 0.5,
    ):
        """
        Initialize the PII detector.

        Args:
            patterns: Custom patterns to use
            use_defaults: Whether to include default patterns
            min_confidence: Minimum confidence threshold for matches
        """
        self.patterns: List[PIIPattern] = []
        self.min_confidence = min_confidence

        if use_defaults:
            self.patterns.extend(self.DEFAULT_PATTERNS)

        if patterns:
            self.patterns.extend(patterns)

    def add_pattern(self, pattern: PIIPattern) -> None:
        """Add a custom pattern."""
        self.patterns.append(pattern)

    def remove_pattern_type(self, pii_type: PIIType) -> None:
        """Remove all patterns of a specific type."""
        self.patterns = [p for p in self.patterns if p.pii_type != pii_type]

    def detect(
        self,
        text: str,
        types: Optional[List[PIIType]] = None,
    ) -> List[PIIMatch]:
        """
        Detect PII in the given text.

        Args:
            text: Text to scan for PII
            types: Optional list of PII types to detect (None = all)

        Returns:
            List of PII matches found
        """
        if not text:
            return []

        matches: List[PIIMatch] = []
        seen_spans: Set[Tuple[int, int]] = set()

        for pattern in self.patterns:
            if not pattern.enabled:
                continue

            if types and pattern.pii_type not in types:
                continue

            if pattern.confidence < self.min_confidence:
                continue

            if pattern.compiled_pattern is None:
                continue

            for match in pattern.compiled_pattern.finditer(text):
                span = (match.start(), match.end())

                # Avoid duplicate overlapping matches
                if span in seen_spans:
                    continue

                # Check for overlapping matches - keep higher confidence
                overlapping = False
                for existing_span in list(seen_spans):
                    if self._spans_overlap(span, existing_span):
                        overlapping = True
                        break

                if not overlapping:
                    seen_spans.add(span)
                    matches.append(
                        PIIMatch(
                            pii_type=pattern.pii_type,
                            value=match.group(),
                            start=match.start(),
                            end=match.end(),
                            confidence=pattern.confidence,
                            pattern_description=pattern.description,
                        )
                    )

        # Sort by position
        matches.sort(key=lambda m: m.start)
        return matches

    def _spans_overlap(self, span1: Tuple[int, int], span2: Tuple[int, int]) -> bool:
        """Check if two spans overlap."""
        return not (span1[1] <= span2[0] or span2[1] <= span1[0])

    def contains_pii(
        self,
        text: str,
        types: Optional[List[PIIType]] = None,
    ) -> bool:
        """Check if text contains any PII."""
        return len(self.detect(text, types)) > 0


class PIIRedactor:
    """
    Redacts PII from text using configurable strategies.
    """

    def __init__(
        self,
        detector: Optional[PIIDetector] = None,
        default_strategy: RedactionStrategy = RedactionStrategy.TYPE_MASK,
        type_strategies: Optional[Dict[PIIType, RedactionStrategy]] = None,
        encryption_key: Optional[bytes] = None,
        preserve_format: bool = False,
    ):
        """
        Initialize the PII redactor.

        Args:
            detector: PII detector instance (creates default if None)
            default_strategy: Default redaction strategy
            type_strategies: Per-type redaction strategies
            encryption_key: Key for encryption strategy
            preserve_format: Whether to preserve original format (e.g., keep @ in emails)
        """
        self.detector = detector or PIIDetector()
        self.default_strategy = default_strategy
        self.type_strategies = type_strategies or {}
        self.encryption_key = encryption_key
        self.preserve_format = preserve_format

        # Fake data generators for FAKE strategy
        self._fake_generators: Dict[PIIType, Callable[[], str]] = {
            PIIType.EMAIL: lambda: "redacted@example.com",
            PIIType.PHONE_NUMBER: lambda: "+1-555-000-0000",
            PIIType.SSN: lambda: "000-00-0000",
            PIIType.CREDIT_CARD: lambda: "0000-0000-0000-0000",
            PIIType.IP_ADDRESS: lambda: "0.0.0.0",
            PIIType.NAME: lambda: "John Doe",
        }

    def redact(
        self,
        text: str,
        types: Optional[List[PIIType]] = None,
        strategy: Optional[RedactionStrategy] = None,
    ) -> RedactionResult:
        """
        Redact PII from text.

        Args:
            text: Text to redact
            types: Optional list of PII types to redact
            strategy: Override redaction strategy for this call

        Returns:
            RedactionResult with redacted text and metadata
        """
        if not text:
            return RedactionResult(
                original_text=text,
                redacted_text=text,
                matches=[],
                redaction_map={},
            )

        matches = self.detector.detect(text, types)

        if not matches:
            return RedactionResult(
                original_text=text,
                redacted_text=text,
                matches=[],
                redaction_map={},
            )

        # Build redacted text
        redacted_parts: List[str] = []
        redaction_map: Dict[str, str] = {}
        last_end = 0

        for match in matches:
            # Add text before this match
            redacted_parts.append(text[last_end:match.start])

            # Get redaction strategy
            strat = strategy or self.type_strategies.get(
                match.pii_type, self.default_strategy
            )

            # Apply redaction
            redacted_value, mapping = self._apply_strategy(match, strat)
            redacted_parts.append(redacted_value)

            if mapping:
                redaction_map[redacted_value] = mapping

            last_end = match.end

        # Add remaining text
        redacted_parts.append(text[last_end:])

        redacted_text = "".join(redacted_parts)

        return RedactionResult(
            original_text=text,
            redacted_text=redacted_text,
            matches=matches,
            redaction_map=redaction_map,
        )

    def _apply_strategy(
        self,
        match: PIIMatch,
        strategy: RedactionStrategy,
    ) -> Tuple[str, Optional[str]]:
        """
        Apply a redaction strategy to a match.

        Returns:
            Tuple of (redacted_value, original_for_mapping)
        """
        value = match.value

        if strategy == RedactionStrategy.MASK:
            return "[REDACTED]", value

        elif strategy == RedactionStrategy.TYPE_MASK:
            return f"[{match.pii_type.value.upper()}_REDACTED]", value

        elif strategy == RedactionStrategy.PARTIAL:
            return self._partial_mask(value, match.pii_type), value

        elif strategy == RedactionStrategy.HASH:
            hash_value = hashlib.sha256(value.encode()).hexdigest()
            return f"[HASH:{hash_value}]", None

        elif strategy == RedactionStrategy.HASH_PREFIX:
            hash_value = hashlib.sha256(value.encode()).hexdigest()[:8]
            return f"[HASH:{hash_value}]", None

        elif strategy == RedactionStrategy.FAKE:
            fake_value = self._generate_fake(match.pii_type)
            return fake_value, value

        elif strategy == RedactionStrategy.REMOVE:
            return "", value

        elif strategy == RedactionStrategy.ENCRYPT:
            encrypted = self._encrypt(value)
            return f"[ENC:{encrypted}]", None

        else:
            return "[REDACTED]", value

    def _partial_mask(self, value: str, pii_type: PIIType) -> str:
        """Apply partial masking based on PII type."""
        if pii_type == PIIType.EMAIL:
            parts = value.split("@")
            if len(parts) == 2:
                local = parts[0]
                domain = parts[1]
                masked_local = local[0] + "*" * (len(local) - 1) if local else "*"
                return f"{masked_local}@{domain}"

        elif pii_type == PIIType.PHONE_NUMBER:
            # Keep last 4 digits
            digits = re.sub(r"\D", "", value)
            if len(digits) >= 4:
                return "*" * (len(digits) - 4) + digits[-4:]

        elif pii_type == PIIType.CREDIT_CARD:
            # Keep first 4 and last 4 digits
            digits = re.sub(r"\D", "", value)
            if len(digits) >= 8:
                return digits[:4] + "*" * (len(digits) - 8) + digits[-4:]

        elif pii_type == PIIType.SSN:
            # Keep last 4 digits
            digits = re.sub(r"\D", "", value)
            if len(digits) >= 4:
                return "***-**-" + digits[-4:]

        elif pii_type == PIIType.IP_ADDRESS:
            # Mask last octet
            parts = value.split(".")
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.{parts[2]}.*"

        # Default: mask middle portion
        if len(value) > 4:
            visible = max(1, len(value) // 4)
            return value[:visible] + "*" * (len(value) - visible * 2) + value[-visible:]

        return "*" * len(value)

    def _generate_fake(self, pii_type: PIIType) -> str:
        """Generate fake data for a PII type."""
        generator = self._fake_generators.get(pii_type)
        if generator:
            return generator()
        return "[REDACTED]"

    def _encrypt(self, value: str) -> str:
        """Encrypt a value (simplified - use proper encryption in production)."""
        if self.encryption_key:
            # In production, use proper encryption (e.g., Fernet)
            import base64

            combined = self.encryption_key + value.encode()
            return base64.urlsafe_b64encode(
                hashlib.sha256(combined).digest()
            ).decode()[:32]
        return hashlib.sha256(value.encode()).hexdigest()[:32]

    def set_type_strategy(
        self,
        pii_type: PIIType,
        strategy: RedactionStrategy,
    ) -> None:
        """Set redaction strategy for a specific PII type."""
        self.type_strategies[pii_type] = strategy

    def add_fake_generator(
        self,
        pii_type: PIIType,
        generator: Callable[[], str],
    ) -> None:
        """Add a custom fake data generator."""
        self._fake_generators[pii_type] = generator


class JSONPIIRedactor:
    """
    Redacts PII from JSON objects, preserving structure.
    """

    def __init__(
        self,
        redactor: Optional[PIIRedactor] = None,
        sensitive_keys: Optional[List[str]] = None,
        redact_all_strings: bool = False,
    ):
        """
        Initialize JSON PII redactor.

        Args:
            redactor: PIIRedactor instance
            sensitive_keys: Keys whose values should always be redacted
            redact_all_strings: Whether to scan all string values for PII
        """
        self.redactor = redactor or PIIRedactor()
        self.sensitive_keys = set(k.lower() for k in (sensitive_keys or []))
        self.redact_all_strings = redact_all_strings

        # Default sensitive keys
        self.sensitive_keys.update({
            "password", "passwd", "pwd", "secret", "api_key", "apikey",
            "access_token", "refresh_token", "auth_token", "bearer",
            "authorization", "credential", "credentials", "private_key",
            "ssn", "social_security", "credit_card", "card_number",
        })

    def redact(
        self,
        data: Union[Dict, List, str],
        path: str = "",
    ) -> Union[Dict, List, str]:
        """
        Redact PII from a JSON object.

        Args:
            data: JSON object (dict, list, or string)
            path: Current path for nested objects (used internally)

        Returns:
            Redacted JSON object
        """
        if isinstance(data, dict):
            return self._redact_dict(data, path)
        elif isinstance(data, list):
            return self._redact_list(data, path)
        elif isinstance(data, str):
            return self._redact_string(data, path)
        else:
            return data

    def _redact_dict(self, data: Dict, path: str) -> Dict:
        """Redact PII from a dictionary."""
        result = {}
        for key, value in data.items():
            new_path = f"{path}.{key}" if path else key
            key_lower = key.lower()

            # Check if key is sensitive
            if key_lower in self.sensitive_keys:
                if isinstance(value, str):
                    result[key] = "[REDACTED]"
                else:
                    result[key] = self.redact(value, new_path)
            else:
                result[key] = self.redact(value, new_path)

        return result

    def _redact_list(self, data: List, path: str) -> List:
        """Redact PII from a list."""
        return [self.redact(item, f"{path}[{i}]") for i, item in enumerate(data)]

    def _redact_string(self, data: str, path: str) -> str:
        """Redact PII from a string."""
        if self.redact_all_strings or self._should_scan_path(path):
            result = self.redactor.redact(data)
            return result.redacted_text
        return data

    def _should_scan_path(self, path: str) -> bool:
        """Determine if a path should be scanned for PII."""
        # Always scan certain paths
        scan_patterns = [
            "message", "content", "text", "body", "prompt", "response",
            "input", "output", "data", "payload",
        ]
        path_lower = path.lower()
        return any(p in path_lower for p in scan_patterns)


# Convenience functions
def redact_pii(
    text: str,
    strategy: RedactionStrategy = RedactionStrategy.TYPE_MASK,
    types: Optional[List[PIIType]] = None,
) -> str:
    """
    Convenience function to redact PII from text.

    Args:
        text: Text to redact
        strategy: Redaction strategy to use
        types: Optional list of PII types to redact

    Returns:
        Redacted text
    """
    redactor = PIIRedactor(default_strategy=strategy)
    result = redactor.redact(text, types=types)
    return result.redacted_text


def detect_pii(
    text: str,
    types: Optional[List[PIIType]] = None,
) -> List[PIIMatch]:
    """
    Convenience function to detect PII in text.

    Args:
        text: Text to scan
        types: Optional list of PII types to detect

    Returns:
        List of PII matches
    """
    detector = PIIDetector()
    return detector.detect(text, types)


def redact_json(
    data: Union[Dict, List, str],
    redact_all: bool = False,
) -> Union[Dict, List, str]:
    """
    Convenience function to redact PII from JSON.

    Args:
        data: JSON data to redact
        redact_all: Whether to scan all string values

    Returns:
        Redacted JSON data
    """
    redactor = JSONPIIRedactor(redact_all_strings=redact_all)
    return redactor.redact(data)
