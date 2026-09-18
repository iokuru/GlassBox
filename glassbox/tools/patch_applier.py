from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional


PATCH_TEMPLATE = """--- a/{filename}
+++ b/{filename}
@@ {hunk_header} @@
{content}
"""


class PatchApplier:
    def __init__(self, project_root: str) -> None:
        self.root = Path(project_root)

    def apply_css_variable_fix(
        self, file_path: str, variable: str, new_value: str
    ) -> bool:
        target = self.root / file_path
        if not target.exists():
            return False
        content = target.read_text(encoding="utf-8")
        import re
        pattern = rf"({re.escape(variable)}\s*:\s*)[^;]+(;)"
        updated, count = re.subn(pattern, rf"\g<1>{new_value}\g<2>", content)
        if count == 0:
            return False
        target.write_text(updated, encoding="utf-8")
        return True

    def apply_color_replacement(
        self, file_path: str, old_hex: str, new_hex: str
    ) -> int:
        target = self.root / file_path
        if not target.exists():
            return 0
        content = target.read_text(encoding="utf-8")
        updated = content.replace(old_hex.lower(), new_hex.lower()).replace(
            old_hex.upper(), new_hex.upper()
        )
        count = content.count(old_hex.lower()) + content.count(old_hex.upper())
        if count > 0:
            target.write_text(updated, encoding="utf-8")
        return count

    def apply_motion_fix(
        self, component_file: str, target_selector: str, new_duration: float
    ) -> bool:
        path = self.root / component_file
        if not path.exists():
            return False
        content = path.read_text(encoding="utf-8")
        import re
        pattern = rf"(duration:\s*){[\d.]+}"
        updated, count = re.subn(pattern, rf"\g<1>{new_duration}", content)
        if count > 0:
            path.write_text(updated, encoding="utf-8")
        return count > 0

    def insert_css_rule(
        self, css_file: str, selector: str, rule_body: str
    ) -> bool:
        path = self.root / css_file
        if not path.exists():
            return False
        content = path.read_text(encoding="utf-8")
        new_rule = f"\n{selector} {{\n{textwrap.indent(rule_body, '  ')}\n}}\n"
        if selector in content:
            return False
        path.write_text(content + new_rule, encoding="utf-8")
        return True

    def replace_section_height(
        self, component_file: str, old_height: str, new_height: str
    ) -> bool:
        path = self.root / component_file
        if not path.exists():
            return False
        content = path.read_text(encoding="utf-8")
        if old_height not in content:
            return False
        updated = content.replace(old_height, new_height, 1)
        path.write_text(updated, encoding="utf-8")
        return True

    def from_repair_task(self, task: Dict[str, Any], clone_dir: str) -> Optional[str]:
        region = task.get("region", "")
        suggested = task.get("suggested_fix", "")
        metadata = task.get("metadata", {})

        if region.startswith("palette:") and "Replace" in suggested:
            import re
            hexes = re.findall(r"#[0-9a-fA-F]{6}", suggested)
            if len(hexes) == 2:
                old_hex, new_hex = hexes
                files_patched = []
                for css_file in ["src/index.css", "tailwind.config.js"]:
                    count = self.apply_color_replacement(css_file, old_hex, new_hex)
                    if count > 0:
                        files_patched.append(f"{css_file} ({count} replacements)")
                if files_patched:
                    return f"Color fix applied: {old_hex} -> {new_hex} in {', '.join(files_patched)}"

        if region.startswith("layout:") and "height" in suggested.lower():
            return "Layout height fix requires manual review — section height out of spec"

        return None
