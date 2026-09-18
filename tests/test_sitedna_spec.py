import pytest
from sitedna.spec.schema import SiteDNA, CaptureSource, DesignTokens, ColorToken, MotionSpec
from sitedna.spec.validate import validate_sitedna, confidence_summary


def make_minimal_spec(url="https://example.com") -> SiteDNA:
    return SiteDNA(
        source=CaptureSource(
            url=url,
            captured_at="2026-01-01T00:00:00Z",
            viewport=(1440, 900),
        )
    )


def test_minimal_spec_fails_gracefully():
    spec = make_minimal_spec()
    result = validate_sitedna(spec)
    assert result.valid
    assert "tokens" in result.confidence
    assert result.confidence["tokens"] <= 0.3


def test_spec_with_palette_improves_confidence():
    spec = make_minimal_spec()
    spec.tokens.palette = [
        ColorToken(role="bg.base", oklch="0.18 0.01 260", hex="#141517"),
        ColorToken(role="fg.primary", oklch="0.96 0.01 90", hex="#f4f1ea"),
    ]
    result = validate_sitedna(spec)
    assert result.confidence["tokens"] > 0.2


def test_validation_result_bool():
    spec = make_minimal_spec()
    result = validate_sitedna(spec)
    assert bool(result) is True


def test_confidence_summary_returns_string():
    spec = make_minimal_spec()
    result = validate_sitedna(spec)
    summary = confidence_summary(result)
    assert isinstance(summary, str)
    assert "tokens" in summary
    assert "#" in summary or "." in summary


def test_missing_url_fails():
    spec = make_minimal_spec("")
    result = validate_sitedna(spec)
    assert not result.valid
    assert any("url" in e for e in result.errors)
