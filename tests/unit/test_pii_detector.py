"""
Unit tests for src/pii_detector.py
Covers: PIIDetector (all methods), singleton helpers.
Presidio is mocked via sys.modules patching; regex fallback is tested directly.
ASCII-only assertions.
"""

from __future__ import annotations

import sys
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


# ===========================================================================
# Force Presidio to appear absent so we always test the regex path cleanly.
# Individual test classes that need the Presidio path mock it explicitly.
# ===========================================================================

def _import_without_presidio():
    """Re-import pii_detector with Presidio stubs removed from sys.modules."""
    for key in list(sys.modules):
        if "presidio" in key or "pii_detector" in key:
            sys.modules.pop(key, None)

    # Ensure presidio_analyzer is NOT importable in this env
    sys.modules["presidio_analyzer"] = None  # type: ignore
    sys.modules["presidio_anonymizer"] = None  # type: ignore
    sys.modules["presidio_anonymizer.entities"] = None  # type: ignore

    import importlib
    import src.pii_detector as mod
    importlib.reload(mod)
    return mod


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture(autouse=True)
def _clear_singleton():
    """Reset global _pii_detector between tests."""
    import src.pii_detector as mod
    mod._pii_detector = None
    yield
    mod._pii_detector = None


# ===========================================================================
# TestPIIDetectorInit
# ===========================================================================

class TestPIIDetectorInit:

    @pytest.mark.unit
    def test_disabled_by_default(self):
        from src.pii_detector import PIIDetector
        d = PIIDetector()
        assert d.enabled is False

    @pytest.mark.unit
    def test_enabled_flag_set(self):
        from src.pii_detector import PIIDetector
        d = PIIDetector(enabled=True)
        assert d.enabled is True

    @pytest.mark.unit
    def test_default_entities(self):
        from src.pii_detector import PIIDetector, _DEFAULT_ENTITIES
        d = PIIDetector()
        assert d.entities == list(_DEFAULT_ENTITIES)

    @pytest.mark.unit
    def test_custom_entities(self):
        from src.pii_detector import PIIDetector
        d = PIIDetector(entities=["EMAIL"])
        assert d.entities == ["EMAIL"]

    @pytest.mark.unit
    def test_custom_redaction_char(self):
        from src.pii_detector import PIIDetector
        d = PIIDetector(redaction_char="#")
        assert d.redaction_char == "#"

    @pytest.mark.unit
    def test_presidio_not_available_fallback_logged(self, caplog):
        from src.pii_detector import PIIDetector, _PRESIDIO_AVAILABLE
        if _PRESIDIO_AVAILABLE:
            pytest.skip("Presidio is installed - skipping regex-fallback warning test")
        import logging
        with caplog.at_level(logging.WARNING, logger="src.pii_detector"):
            d = PIIDetector(enabled=True)
        assert d._use_presidio is False


# ===========================================================================
# TestDetectDisabled
# ===========================================================================

class TestDetectDisabled:
    """When enabled=False, detect/redact/is_safe return permissive values."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_detect_returns_empty_when_disabled(self):
        from src.pii_detector import PIIDetector
        d = PIIDetector(enabled=False)
        result = await d.detect("my email is bob@example.com")
        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_detect_returns_empty_for_empty_text(self):
        from src.pii_detector import PIIDetector
        d = PIIDetector(enabled=True)
        result = await d.detect("")
        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_detect_returns_empty_for_none_text(self):
        from src.pii_detector import PIIDetector
        d = PIIDetector(enabled=False)
        # None treated as falsy - should return []
        result = await d.detect(None)  # type: ignore
        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_redact_returns_original_when_disabled(self):
        from src.pii_detector import PIIDetector
        d = PIIDetector(enabled=False)
        text = "Call me at 555-123-4567"
        result = await d.redact(text)
        assert result == text

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_redact_returns_original_for_empty_text(self):
        from src.pii_detector import PIIDetector
        d = PIIDetector(enabled=True)
        result = await d.redact("")
        assert result == ""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_is_safe_returns_true_when_disabled(self):
        from src.pii_detector import PIIDetector
        d = PIIDetector(enabled=False)
        assert await d.is_safe("my SSN is 123-45-6789") is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_is_safe_returns_true_for_empty_text(self):
        from src.pii_detector import PIIDetector
        d = PIIDetector(enabled=True)
        assert await d.is_safe("") is True


# ===========================================================================
# TestRegexDetection
# ===========================================================================

class TestRegexDetection:
    """Tests for the _detect_regex fallback path."""

    @pytest.fixture
    def detector(self):
        from src.pii_detector import PIIDetector
        d = PIIDetector(enabled=True)
        d._use_presidio = False  # force regex path
        return d

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_detects_email(self, detector):
        findings = await detector.detect("Contact bob@example.com for info")
        types = [f["entity_type"] for f in findings]
        assert "EMAIL" in types

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_detects_phone_dashes(self, detector):
        findings = await detector.detect("Call 555-123-4567 now")
        types = [f["entity_type"] for f in findings]
        assert "PHONE" in types

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_detects_phone_no_separator(self, detector):
        findings = await detector.detect("Call 5551234567 now")
        types = [f["entity_type"] for f in findings]
        assert "PHONE" in types

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_detects_ssn(self, detector):
        findings = await detector.detect("SSN: 123-45-6789")
        types = [f["entity_type"] for f in findings]
        assert "SSN" in types

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_detects_credit_card(self, detector):
        findings = await detector.detect("Card: 4111 1111 1111 1111")
        types = [f["entity_type"] for f in findings]
        assert "CREDIT_CARD" in types

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_pii_returns_empty(self, detector):
        findings = await detector.detect("Hello, this is plain text with no sensitive data.")
        assert findings == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_finding_has_correct_keys(self, detector):
        findings = await detector.detect("bob@test.com")
        assert len(findings) > 0
        for f in findings:
            assert "entity_type" in f
            assert "start" in f
            assert "end" in f
            assert "score" in f

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_finding_start_end_are_valid_offsets(self, detector):
        text = "Email: alice@domain.org"
        findings = await detector.detect(text)
        for f in findings:
            assert f["start"] >= 0
            assert f["end"] <= len(text)
            assert f["start"] < f["end"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_score_is_high_confidence(self, detector):
        findings = await detector.detect("test@example.com")
        for f in findings:
            assert f["score"] == 0.9

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_entity_filter_respected(self):
        from src.pii_detector import PIIDetector
        d = PIIDetector(enabled=True, entities=["EMAIL"])
        d._use_presidio = False
        # SSN present but not in entity list
        findings = await d.detect("SSN 123-45-6789 and email bob@x.com")
        types = [f["entity_type"] for f in findings]
        assert "SSN" not in types
        assert "EMAIL" in types

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_multiple_pii_in_text(self, detector):
        text = "Email bob@a.com and call 555-123-4567"
        findings = await detector.detect(text)
        types = [f["entity_type"] for f in findings]
        assert "EMAIL" in types
        assert "PHONE" in types


# ===========================================================================
# TestRedaction
# ===========================================================================

class TestRedaction:
    """Tests for redact() using the regex path."""

    @pytest.fixture
    def detector(self):
        from src.pii_detector import PIIDetector
        d = PIIDetector(enabled=True)
        d._use_presidio = False
        return d

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_email_is_redacted(self, detector):
        result = await detector.redact("Contact alice@example.com")
        assert "alice@example.com" not in result
        assert "[REDACTED-EMAIL]" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_phone_is_redacted(self, detector):
        result = await detector.redact("Call 555-123-4567")
        assert "555-123-4567" not in result
        assert "[REDACTED-PHONE]" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_ssn_is_redacted(self, detector):
        result = await detector.redact("SSN: 123-45-6789")
        assert "123-45-6789" not in result
        assert "[REDACTED-SSN]" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_text_without_pii_unchanged(self, detector):
        text = "No personal info here."
        result = await detector.redact(text)
        assert result == text

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_multiple_redactions_in_one_pass(self, detector):
        text = "Email bob@x.com call 555-000-1234"
        result = await detector.redact(text)
        assert "[REDACTED-EMAIL]" in result
        assert "[REDACTED-PHONE]" in result

    @pytest.mark.unit
    def test_redact_text_empty_findings_returns_original(self):
        from src.pii_detector import PIIDetector
        d = PIIDetector(enabled=True)
        d._use_presidio = False
        result = d._redact_text("plain text", [])
        assert result == "plain text"

    @pytest.mark.unit
    def test_redact_text_right_to_left_ordering(self):
        """Ensure right-to-left replacement keeps offsets valid."""
        from src.pii_detector import PIIDetector
        d = PIIDetector(enabled=True)
        text = "a@b.com and c@d.com"
        findings = d._detect_regex(text)
        result = d._redact_text(text, findings)
        assert "a@b.com" not in result
        assert "c@d.com" not in result


# ===========================================================================
# TestIsSafe
# ===========================================================================

class TestIsSafe:
    """Tests for is_safe()."""

    @pytest.fixture
    def detector(self):
        from src.pii_detector import PIIDetector
        d = PIIDetector(enabled=True)
        d._use_presidio = False
        return d

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_safe_text_returns_true(self, detector):
        assert await detector.is_safe("Hello world, nothing sensitive.") is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_email_makes_text_unsafe(self, detector):
        assert await detector.is_safe("Contact bob@example.com") is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_phone_makes_text_unsafe(self, detector):
        assert await detector.is_safe("Call 555-123-4567") is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_ssn_makes_text_unsafe(self, detector):
        assert await detector.is_safe("SSN 123-45-6789") is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_low_score_finding_kept_safe(self):
        """A finding with score <= threshold is still considered safe."""
        from src.pii_detector import PIIDetector, _HIGH_CONFIDENCE_THRESHOLD
        d = PIIDetector(enabled=True)
        d._use_presidio = False

        # Patch detect to return a low-score finding
        async def _low_score(text):
            return [{"entity_type": "EMAIL", "start": 0, "end": 5, "score": 0.5}]

        d.detect = _low_score
        # score 0.5 <= 0.85 threshold -> text should still be considered safe
        result = await d.is_safe("hello")
        assert result is True


# ===========================================================================
# TestPresidioPath (mocked)
# ===========================================================================

class TestPresidioPath:
    """Tests for the _detect_presidio path using mocked Presidio engines."""

    @pytest.mark.unit
    def test_detect_presidio_returns_empty_when_no_analyzer(self):
        from src.pii_detector import PIIDetector
        d = PIIDetector(enabled=True)
        d._use_presidio = True
        d._analyzer = None  # no analyzer initialised
        result = d._detect_presidio("text with 555-123-4567")
        assert result == []

    @pytest.mark.unit
    def test_detect_presidio_maps_entity_names(self):
        from src.pii_detector import PIIDetector
        d = PIIDetector(enabled=True)
        d._use_presidio = True

        mock_result = MagicMock()
        mock_result.entity_type = "EMAIL_ADDRESS"
        mock_result.start = 0
        mock_result.end = 10
        mock_result.score = 0.95

        mock_analyzer = MagicMock()
        mock_analyzer.analyze = MagicMock(return_value=[mock_result])
        d._analyzer = mock_analyzer

        findings = d._detect_presidio("alice@x.com")
        assert len(findings) == 1
        assert findings[0]["entity_type"] == "EMAIL"
        assert findings[0]["score"] == 0.95

    @pytest.mark.unit
    def test_detect_presidio_falls_back_to_regex_on_exception(self):
        from src.pii_detector import PIIDetector
        d = PIIDetector(enabled=True)
        d._use_presidio = True

        mock_analyzer = MagicMock()
        mock_analyzer.analyze = MagicMock(side_effect=RuntimeError("presidio crashed"))
        d._analyzer = mock_analyzer

        result = d._detect_presidio("Call 555-123-4567")
        # Should fall back to regex and find the phone number
        types = [f["entity_type"] for f in result]
        assert "PHONE" in types

    @pytest.mark.unit
    def test_init_presidio_failure_disables_presidio(self):
        """If AnalyzerEngine() raises, _use_presidio is set to False.

        Works even when Presidio is not installed: patch.object with
        create=True will inject the missing name into the module namespace
        for the duration of the patch.
        """
        from src.pii_detector import PIIDetector
        import src.pii_detector as pii_mod

        d = PIIDetector.__new__(PIIDetector)
        d.enabled = True
        d.entities = ["EMAIL"]
        d.redaction_char = "*"
        d._use_presidio = True
        d._analyzer = None
        d._anonymizer = None

        # create=True so this works whether or not Presidio is installed
        with patch.object(pii_mod, "AnalyzerEngine",
                          side_effect=Exception("init failed"),
                          create=True), \
             patch.object(pii_mod, "AnonymizerEngine",
                          new=MagicMock(),
                          create=True):
            d._init_presidio()

        assert d._use_presidio is False
        assert d._analyzer is None

    @pytest.mark.unit
    def test_init_presidio_success_via_module_patch(self):
        """Patch AnalyzerEngine/AnonymizerEngine into the module to cover lines 147-150."""
        import src.pii_detector as mod

        mock_analyzer = MagicMock()
        mock_anonymizer = MagicMock()

        # Temporarily inject mocks at module level so _init_presidio sees them
        orig_analyzer = getattr(mod, "AnalyzerEngine", None)
        orig_anonymizer = getattr(mod, "AnonymizerEngine", None)
        try:
            mod.AnalyzerEngine = MagicMock(return_value=mock_analyzer)
            mod.AnonymizerEngine = MagicMock(return_value=mock_anonymizer)

            d = mod.PIIDetector.__new__(mod.PIIDetector)
            d.enabled = True
            d.entities = ["EMAIL"]
            d.redaction_char = "*"
            d._use_presidio = True
            d._analyzer = None
            d._anonymizer = None

            d._init_presidio()

            assert d._analyzer is mock_analyzer
            assert d._anonymizer is mock_anonymizer
            assert d._use_presidio is True
        finally:
            if orig_analyzer is None:
                if hasattr(mod, "AnalyzerEngine"):
                    delattr(mod, "AnalyzerEngine")
            else:
                mod.AnalyzerEngine = orig_analyzer
            if orig_anonymizer is None:
                if hasattr(mod, "AnonymizerEngine"):
                    delattr(mod, "AnonymizerEngine")
            else:
                mod.AnonymizerEngine = orig_anonymizer

    @pytest.mark.unit
    def test_init_presidio_failure_via_module_patch(self):
        """Cover lines 151-159: _init_presidio failure path disables presidio."""
        import src.pii_detector as mod

        orig_analyzer = getattr(mod, "AnalyzerEngine", None)
        try:
            mod.AnalyzerEngine = MagicMock(side_effect=Exception("engine broken"))

            d = mod.PIIDetector.__new__(mod.PIIDetector)
            d.enabled = True
            d.entities = ["EMAIL"]
            d.redaction_char = "*"
            d._use_presidio = True
            d._analyzer = None
            d._anonymizer = None

            d._init_presidio()

            assert d._use_presidio is False
            assert d._analyzer is None
        finally:
            if orig_analyzer is None:
                if hasattr(mod, "AnalyzerEngine"):
                    delattr(mod, "AnalyzerEngine")
            else:
                mod.AnalyzerEngine = orig_analyzer

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_detect_calls_presidio_path_when_use_presidio_true(self):
        """Cover line 260: detect() routes to _detect_presidio when _use_presidio=True."""
        from src.pii_detector import PIIDetector
        d = PIIDetector(enabled=True)
        d._use_presidio = True

        mock_analyzer = MagicMock()
        mock_result = MagicMock()
        mock_result.entity_type = "EMAIL_ADDRESS"
        mock_result.start = 0
        mock_result.end = 10
        mock_result.score = 0.95
        mock_analyzer.analyze = MagicMock(return_value=[mock_result])
        d._analyzer = mock_analyzer

        findings = await d.detect("alice@x.com")
        assert len(findings) == 1
        assert findings[0]["entity_type"] == "EMAIL"


# ===========================================================================
# TestSingleton
# ===========================================================================

class TestSingleton:

    @pytest.mark.unit
    def test_init_returns_instance(self):
        from src.pii_detector import init_pii_detector, PIIDetector
        d = init_pii_detector(enabled=False)
        assert isinstance(d, PIIDetector)

    @pytest.mark.unit
    def test_get_returns_same_instance(self):
        from src.pii_detector import init_pii_detector, get_pii_detector
        d1 = init_pii_detector(enabled=False)
        d2 = get_pii_detector()
        assert d1 is d2

    @pytest.mark.unit
    def test_get_returns_none_before_init(self):
        from src.pii_detector import get_pii_detector
        import src.pii_detector as mod
        mod._pii_detector = None
        assert get_pii_detector() is None

    @pytest.mark.unit
    def test_init_with_custom_entities(self):
        from src.pii_detector import init_pii_detector
        d = init_pii_detector(enabled=True, entities=["EMAIL", "PHONE"])
        assert d.entities == ["EMAIL", "PHONE"]

    @pytest.mark.unit
    def test_reinit_replaces_singleton(self):
        from src.pii_detector import init_pii_detector, get_pii_detector
        d1 = init_pii_detector(enabled=False)
        d2 = init_pii_detector(enabled=True)
        assert get_pii_detector() is d2
        assert d1 is not d2
