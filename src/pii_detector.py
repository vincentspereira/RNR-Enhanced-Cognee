"""
Enhanced Cognee - Phase 9 Production Hardening: PII Detector
=============================================================
Config-gated Personally Identifiable Information (PII) detection and
redaction module.

When Microsoft Presidio is available the module delegates to it for
high-accuracy NLP-based entity detection.  When Presidio is not installed
it falls back to regex pattern matching covering the most common PII
categories.

The detector is DISABLED by default (enabled=False) to avoid unintended
data-scrubbing of content that is legitimately stored in memory.

ASCII-only: no Unicode in string literals, comments, or log messages.

Author: Enhanced Cognee Team
Version: 1.0.0 (Phase 9)
"""

import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional Presidio imports
# ---------------------------------------------------------------------------

try:
    from presidio_analyzer import AnalyzerEngine, RecognizerResult
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig

    _PRESIDIO_AVAILABLE = True
    logger.debug("Presidio libraries loaded successfully")
except ImportError:
    _PRESIDIO_AVAILABLE = False
    logger.debug("presidio_analyzer / presidio_anonymizer not installed - regex fallback active")

# ---------------------------------------------------------------------------
# Regex fallback patterns
# ---------------------------------------------------------------------------

_REGEX_PATTERNS: Dict[str, re.Pattern] = {
    "EMAIL": re.compile(
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
        re.ASCII,
    ),
    "PHONE": re.compile(
        r"\b\d{3}[.\-]?\d{3}[.\-]?\d{4}\b",
        re.ASCII,
    ),
    "SSN": re.compile(
        r"\b\d{3}-\d{2}-\d{4}\b",
        re.ASCII,
    ),
    "CREDIT_CARD": re.compile(
        r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
        re.ASCII,
    ),
}

# Default entity types to detect
_DEFAULT_ENTITIES: List[str] = ["EMAIL", "PHONE", "SSN", "CREDIT_CARD"]

# Confidence threshold above which text is considered unsafe
_HIGH_CONFIDENCE_THRESHOLD: float = 0.85

# Singleton reference
_pii_detector: Optional["PIIDetector"] = None


# ---------------------------------------------------------------------------
# PIIDetector
# ---------------------------------------------------------------------------


class PIIDetector:
    """
    PII detection and redaction for Enhanced Cognee memory entries.

    Presidio is used when available; regex patterns are used as fallback.
    The detector is disabled by default - pass enabled=True to activate it.

    Example usage::

        detector = PIIDetector(enabled=True)
        findings = await detector.detect("Call me at 555-123-4567")
        clean   = await detector.redact("My email is bob@example.com")
        safe    = await detector.is_safe("Hello world")
    """

    def __init__(
        self,
        enabled: bool = False,
        entities: Optional[List[str]] = None,
        redaction_char: str = "*",
    ) -> None:
        """
        Initialize the PII detector.

        Args:
            enabled:        When False all methods return permissive results
                            without scanning the text.  Defaults to False.
            entities:       List of entity type names to detect.  Defaults
                            to EMAIL, PHONE, SSN, CREDIT_CARD.
            redaction_char: Character used to fill masked spans when using
                            the char-replacement strategy.  Not used for the
                            bracket-label redaction produced by ``redact()``.
        """
        self.enabled = enabled
        self.entities: List[str] = entities if entities is not None else list(_DEFAULT_ENTITIES)
        self.redaction_char = redaction_char

        self._use_presidio: bool = _PRESIDIO_AVAILABLE and enabled

        if enabled and not _PRESIDIO_AVAILABLE:
            logger.warning(
                "PIIDetector: enabled=True but Presidio is not installed. "
                "Falling back to regex patterns. Install presidio-analyzer "
                "and presidio-anonymizer for higher accuracy."
            )

        # Initialise Presidio engines lazily only when needed
        self._analyzer: Optional[object] = None
        self._anonymizer: Optional[object] = None

        if self._use_presidio:
            self._init_presidio()

        logger.debug(
            "PIIDetector initialised: enabled=%s, presidio=%s, entities=%s",
            self.enabled,
            self._use_presidio,
            self.entities,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _init_presidio(self) -> None:
        """Instantiate Presidio engines (called once on first use)."""
        try:
            self._analyzer = AnalyzerEngine()
            self._anonymizer = AnonymizerEngine()
            logger.debug("Presidio AnalyzerEngine and AnonymizerEngine ready")
        except Exception as exc:
            logger.warning(
                "PIIDetector: Presidio initialisation failed (%s). "
                "Falling back to regex patterns.",
                exc,
            )
            self._use_presidio = False
            self._analyzer = None
            self._anonymizer = None

    def _detect_regex(self, text: str) -> List[Dict]:
        """Run regex-based PII detection and return normalised finding dicts."""
        findings: List[Dict] = []
        for entity_type, pattern in _REGEX_PATTERNS.items():
            if entity_type not in self.entities:
                continue
            for match in pattern.finditer(text):
                findings.append(
                    {
                        "entity_type": entity_type,
                        "start": match.start(),
                        "end": match.end(),
                        "score": 0.9,  # Regex matches are high confidence
                    }
                )
        return findings

    def _detect_presidio(self, text: str) -> List[Dict]:
        """Run Presidio-based PII detection and return normalised finding dicts."""
        if self._analyzer is None:
            return []

        # Map our entity names to Presidio names where they differ
        presidio_entity_map: Dict[str, str] = {
            "CREDIT_CARD": "CREDIT_CARD",
            "EMAIL": "EMAIL_ADDRESS",
            "PHONE": "PHONE_NUMBER",
            "SSN": "US_SSN",
        }
        presidio_entities = [
            presidio_entity_map.get(e, e) for e in self.entities
        ]
        # Reverse map for normalising back to our names
        reverse_map: Dict[str, str] = {v: k for k, v in presidio_entity_map.items()}

        try:
            results: List[RecognizerResult] = self._analyzer.analyze(
                text=text,
                entities=presidio_entities,
                language="en",
            )
            findings: List[Dict] = []
            for r in results:
                entity_type = reverse_map.get(r.entity_type, r.entity_type)
                findings.append(
                    {
                        "entity_type": entity_type,
                        "start": r.start,
                        "end": r.end,
                        "score": float(r.score),
                    }
                )
            return findings
        except Exception as exc:
            logger.warning("PIIDetector: Presidio analysis error (%s), falling back to regex", exc)
            return self._detect_regex(text)

    def _redact_text(self, text: str, findings: List[Dict]) -> str:
        """
        Replace detected PII spans with bracketed labels.

        Applies replacements from right to left so that earlier span
        offsets remain valid after each substitution.
        """
        if not findings:
            return text

        # Sort by start position descending so right-to-left substitution works
        sorted_findings = sorted(findings, key=lambda f: f["start"], reverse=True)
        result = text
        for finding in sorted_findings:
            label = "[REDACTED-" + finding["entity_type"] + "]"
            result = result[: finding["start"]] + label + result[finding["end"] :]
        return result

    # ------------------------------------------------------------------
    # Public async interface
    # ------------------------------------------------------------------

    async def detect(self, text: str) -> List[Dict]:
        """
        Detect PII entities in the provided text.

        Args:
            text: The text to scan.

        Returns:
            A list of finding dicts, each with keys:
            - entity_type (str): Normalised entity label (EMAIL, PHONE, etc.)
            - start (int): Byte offset of the match start in *text*.
            - end (int): Byte offset of the match end in *text*.
            - score (float): Confidence score in range [0, 1].

        Returns an empty list when the detector is disabled.
        """
        if not self.enabled or not text:
            return []

        if self._use_presidio:
            return self._detect_presidio(text)
        return self._detect_regex(text)

    async def redact(self, text: str) -> str:
        """
        Replace PII spans in *text* with bracketed redaction labels.

        For example, an email address becomes ``[REDACTED-EMAIL]``.

        Args:
            text: The text to redact.

        Returns:
            Redacted text string.  Returns the original text unchanged
            when the detector is disabled.
        """
        if not self.enabled or not text:
            return text

        findings = await self.detect(text)
        return self._redact_text(text, findings)

    async def is_safe(self, text: str) -> bool:
        """
        Determine whether *text* is free of high-confidence PII.

        A piece of text is considered unsafe when at least one finding
        has a confidence score above the threshold (0.85).

        Args:
            text: The text to evaluate.

        Returns:
            True if no high-confidence PII was found (or detector disabled).
            False if one or more high-confidence PII entities were detected.
        """
        if not self.enabled or not text:
            return True

        findings = await self.detect(text)
        return not any(f["score"] > _HIGH_CONFIDENCE_THRESHOLD for f in findings)


# ---------------------------------------------------------------------------
# Module-level singleton helpers
# ---------------------------------------------------------------------------


def init_pii_detector(
    enabled: bool = False,
    entities: Optional[List[str]] = None,
) -> PIIDetector:
    """
    Create and register the global PIIDetector singleton.

    Args:
        enabled:  Whether PII scanning is active.  Defaults to False.
        entities: Entity type names to detect.  None uses the defaults.

    Returns:
        The newly created PIIDetector instance.
    """
    global _pii_detector
    _pii_detector = PIIDetector(enabled=enabled, entities=entities)
    logger.info(
        "PIIDetector singleton initialised: enabled=%s, entities=%s",
        enabled,
        _pii_detector.entities,
    )
    return _pii_detector


def get_pii_detector() -> Optional[PIIDetector]:
    """
    Return the global PIIDetector singleton.

    Returns:
        The PIIDetector instance, or None if ``init_pii_detector`` has
        not been called yet.
    """
    return _pii_detector
