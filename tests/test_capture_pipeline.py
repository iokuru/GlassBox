import asyncio
import pytest
from sitedna.capture.cdp_session import MockCDPSession
from sitedna.capture.dom_extractor import DOMExtractor
from sitedna.capture.style_extractor import StyleExtractor
from sitedna.capture.font_fingerprinter import FontFingerprinter
from sitedna.capture.palette import PaletteExtractor, rgb_to_oklch, parse_css_color
from sitedna.capture.motion_capture import MotionCapture
from sitedna.capture.asset_harvester import AssetHarvester


@pytest.fixture
def mock_session():
    return MockCDPSession(url="https://example.com")


def run(coro):
    return asyncio.run(coro)


def test_dom_extractor_mock(mock_session):
    extractor = DOMExtractor(session=mock_session)
    result = run(extractor.extract())
    assert "sections" in result
    assert len(result["sections"]) >= 1
    assert result["sections"][0]["type"] in ("hero", "content", "panel")


def test_style_extractor_mock(mock_session):
    extractor = StyleExtractor(session=mock_session)
    result = run(extractor.extract())
    assert "font_families" in result
    assert "border_radii" in result
    assert isinstance(result["border_radii"], list)


def test_font_fingerprinter_mock(mock_session):
    fp = FontFingerprinter(session=mock_session)
    result = run(fp.fingerprint())
    assert "display" in result
    assert "matched" in result["display"]
    assert result["display"]["matched"]["score"] > 0.5
    assert result["display"]["is_serif"] is True


def test_palette_extractor_mock(mock_session):
    extractor = PaletteExtractor(session=mock_session)
    palette = run(extractor.extract())
    assert len(palette) > 0
    for item in palette:
        assert "role" in item
        assert "hex" in item
        assert item["hex"].startswith("#")


def test_oklch_conversion():
    L, C, H = rgb_to_oklch(20, 21, 23)
    assert 0 <= L <= 1
    assert C >= 0
    assert 0 <= H <= 360


def test_parse_css_color_hex():
    rgb = parse_css_color("#2563eb")
    assert rgb == (37, 99, 235)


def test_parse_css_color_rgb():
    rgb = parse_css_color("rgb(244, 241, 234)")
    assert rgb == (244, 241, 234)


def test_motion_capture_mock(mock_session):
    mc = MotionCapture(session=mock_session)
    result = run(mc.capture())
    assert "entry_animations" in result
    assert "scroll_linked" in result
    assert len(result["scroll_linked"]) > 0
    for sa in result["scroll_linked"]:
        assert "formula" in sa
        assert "scrollY" in sa["formula"]


def test_asset_harvester_mock(mock_session):
    harvester = AssetHarvester(session=mock_session)
    assets = run(harvester.harvest())
    assert len(assets) > 0
    for a in assets:
        assert "id" in a
        assert "kind" in a


def test_palette_extractor_with_colors(mock_session):
    extractor = PaletteExtractor(session=mock_session)
    colors = ["rgb(20, 21, 23)", "rgb(244, 241, 234)", "rgb(37, 99, 235)"]
    palette = run(extractor.extract(raw_colors=colors))
    assert len(palette) >= 2
    for item in palette:
        assert "oklch" in item
        assert "contrast_on_bg" in item
