import json
import pytest
import asyncio
from sitedna.capture.pipeline import CapturePipeline
from sitedna.spec.schema import SiteDNA
from sitedna.codegen.scaffold import ScaffoldGenerator
from sitedna.codegen.tokens import generate_tailwind_config, generate_css_variables
from sitedna.codegen.layout import generate_app_component, generate_section_component
from sitedna.codegen.motion import generate_motion_variants, generate_scroll_hooks
import tempfile
import os


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def mock_spec() -> SiteDNA:
    pipeline = CapturePipeline(url="https://structured.money/", use_mock=True)
    return run(pipeline.capture())


def test_pipeline_produces_valid_spec(mock_spec):
    assert mock_spec.sitedna == "0.1"
    assert mock_spec.source.url == "https://structured.money/"
    assert len(mock_spec.tokens.palette) > 0
    assert mock_spec.tokens.type.display is not None


def test_pipeline_spec_serializable(mock_spec):
    raw = json.loads(mock_spec.model_dump_json())
    assert "sitedna" in raw
    assert "tokens" in raw
    assert "motion" in raw


def test_tailwind_config_contains_colors(mock_spec):
    config = generate_tailwind_config(mock_spec)
    assert "colors" in config
    assert "fontFamily" in config
    assert "#" in config


def test_css_variables_output(mock_spec):
    css = generate_css_variables(mock_spec)
    assert ":root" in css
    assert "--color-" in css


def test_app_component_contains_sections(mock_spec):
    app_tsx = generate_app_component(mock_spec)
    assert "import" in app_tsx
    assert "ReactLenis" in app_tsx
    for sec in mock_spec.layout.sections[:2]:
        words = sec.id.replace("-", "_").replace(".", "_").split("_")
        component_name = "".join(w.capitalize() for w in words) + "Section"
        assert component_name in app_tsx


def test_section_component_generated(mock_spec):
    if not mock_spec.layout.sections:
        pytest.skip("No sections in spec")
    sec = mock_spec.layout.sections[0]
    tsx = generate_section_component(sec, 0)
    assert "function" in tsx
    assert "framer-motion" in tsx or "motion" in tsx


def test_motion_variants_output(mock_spec):
    variants_ts = generate_motion_variants(mock_spec)
    assert "siteVariants" in variants_ts


def test_scroll_hooks_output(mock_spec):
    hooks_ts = generate_scroll_hooks(mock_spec)
    assert "useScrollAnimations" in hooks_ts


def test_scaffold_generator_creates_files(mock_spec):
    with tempfile.TemporaryDirectory() as tmpdir:
        gen = ScaffoldGenerator(spec=mock_spec, output_dir=tmpdir)
        files = gen.generate()
        assert sum(files.values()) > 0
        assert os.path.exists(os.path.join(tmpdir, "package.json"))
        assert os.path.exists(os.path.join(tmpdir, "src", "App.tsx"))
        assert os.path.exists(os.path.join(tmpdir, "src", "index.css"))
        assert os.path.exists(os.path.join(tmpdir, "tailwind.config.js"))
        assert os.path.exists(os.path.join(tmpdir, "src", "motion", "variants.ts"))


def test_scaffold_package_json_valid(mock_spec):
    with tempfile.TemporaryDirectory() as tmpdir:
        gen = ScaffoldGenerator(spec=mock_spec, output_dir=tmpdir)
        gen.generate()
        pkg = json.loads(open(os.path.join(tmpdir, "package.json")).read())
        assert "dependencies" in pkg
        assert "framer-motion" in pkg["dependencies"]
        assert "lenis" in pkg["dependencies"]
