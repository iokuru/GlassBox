from __future__ import annotations

from typing import Any, Dict, List
from sitedna.spec.schema import SiteDNA, SectionLayout


def section_id_to_component(sec_id: str) -> str:
    words = sec_id.replace("-", "_").replace(".", "_").split("_")
    return "".join(w.capitalize() for w in words) + "Section"


def generate_section_component(sec: SectionLayout, index: int) -> str:
    component_name = section_id_to_component(sec.id)
    height = sec.height or "100vh"
    is_sticky = bool(sec.sticky)
    sticky_style = ""
    if is_sticky:
        top = sec.sticky.get("top", "0") if sec.sticky else "0"
        sticky_style = f"position: 'sticky', top: '{top}',"

    overlap_margin = ""
    if sec.overlap_with:
        overlap_margin = "marginTop: '-100vh',"

    return f"""// {component_name}.tsx — auto-generated from SiteDNA section '{sec.id}'
import {{ motion, useScroll, useTransform }} from 'framer-motion';
import {{ useRef }} from 'react';

export function {component_name}() {{
  const ref = useRef<HTMLElement>(null);
  const {{ scrollYProgress }} = useScroll({{
    target: ref,
    offset: ['start start', 'end start'],
  }});

  return (
    <section
      ref={{ref}}
      style={{{{
        height: '{height}',
        {sticky_style}
        {overlap_margin}
        position: 'relative',
        overflow: 'hidden',
      }}}}
      className="section-{sec.id}"
    >
      {{/* Section {index + 1}: {sec.id} */}}
      {{/* Add your content here */}}
    </section>
  );
}}
"""


def generate_app_component(spec: SiteDNA) -> str:
    sections = spec.layout.sections
    imports = []
    usages = []

    for i, sec in enumerate(sections):
        name = section_id_to_component(sec.id)
        imports.append(f"import {{ {name} }} from './components/{name}';")
        usages.append(f"      <{name} />")

    imports_str = "\n".join(imports)
    usages_str = "\n".join(usages)

    bg_token = next((t for t in spec.tokens.palette if "bg.base" in t.role), None)
    bg_color = bg_token.hex if bg_token else "#141517"
    fg_token = next((t for t in spec.tokens.palette if "fg.primary" in t.role), None)
    fg_color = fg_token.hex if fg_token else "#f4f1ea"

    return f"""// App.tsx — auto-generated from SiteDNA
import {{ ReactLenis }} from 'lenis/react';
{imports_str}
import './index.css';

export default function App() {{
  return (
    <ReactLenis root>
      <div
        style={{{{
          backgroundColor: '{bg_color}',
          color: '{fg_color}',
          fontFamily: 'var(--font-display)',
          overflowX: 'hidden',
        }}}}
      >
{usages_str}
      </div>
    </ReactLenis>
  );
}}
"""


def generate_grid_overlap_wrapper() -> str:
    return """// GridOverlapWrapper.tsx — for overlapping sections with sticky behaviour
import { ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

export function GridOverlapWrapper({ children }: Props) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr',
        gridTemplateRows: '1fr',
      }}
    >
      {children}
    </div>
  );
}
"""
