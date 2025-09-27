#!/usr/bin/env python3
"""Render a Dockerfile by stitching versioned module fragments into a template."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

END_MARKER = "#--ENDMODULE--#"
MANIFEST_STORE = Path("control_plane/data/manifest.json")
MODULES_ROOT = Path("control_plane/data/modules")
TEMPLATES_ROOT = Path("dockerfiles/templates")
DEFAULT_OUTPUT = Path("dockerfiles/Dockerfile.rendered")

from manifest_utils import load_manifest


class ModuleSpec(dict):
    """Typed helper for module metadata."""

    @property
    def name(self) -> str:  # pragma: no cover - trivial accessor
        return self["name"]

    @property
    def order(self) -> int:
        return int(self.get("order", 100))

    @property
    def version(self) -> str:
        return self.get("version", "unknown")

    @property
    def fragment_path(self) -> Path:
        return Path(self["fragment_path"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Path to a standalone manifest JSON (overrides --manifest-id)",
    )
    parser.add_argument(
        "--manifest-id",
        default="llm_factory",
        help="Manifest identifier inside the manifest store",
    )
    parser.add_argument(
        "--manifest-store",
        type=Path,
        default=MANIFEST_STORE,
        help="Path to manifest store JSON",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Override output Dockerfile path (default comes from manifest or dockerfiles/Dockerfile.rendered)",
    )
    return parser.parse_args()


def resolve_template(manifest: dict) -> Path:
    template_cfg = manifest.get("template") or {}
    template_path = template_cfg.get("path")
    if not template_path:
        template_id = template_cfg.get("id", "default")
        template_version = template_cfg.get("version", "latest")
        template_path = TEMPLATES_ROOT / template_id / template_version / "Dockerfile.tpl"
    path = Path(template_path)
    if not path.exists():
        raise FileNotFoundError(f"Template not found at {path}")
    return path


def load_module(module_cfg: dict) -> ModuleSpec:
    name = module_cfg["name"]
    version = module_cfg.get("version", "latest")
    module_path = module_cfg.get("path")
    if module_path:
        module_dir = Path(module_path)
    else:
        module_dir = MODULES_ROOT / name / version
    metadata_path = module_dir / "module.json"
    fragment_path = module_dir / "Dockerfile.fragment"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Missing module metadata at {metadata_path}")
    if not fragment_path.exists():
        raise FileNotFoundError(f"Missing Dockerfile fragment at {fragment_path}")
    metadata = json.loads(metadata_path.read_text())
    metadata.setdefault("name", name)
    metadata.setdefault("version", version)
    metadata["fragment_path"] = str(fragment_path)
    return ModuleSpec(metadata)


def load_modules(manifest: dict) -> List[ModuleSpec]:
    modules_cfg = manifest.get("modules", [])
    modules = [load_module(cfg) for cfg in modules_cfg]
    modules.sort(key=lambda module: module.order)
    return modules


def inject_fragment(template: str, module: ModuleSpec) -> str:
    marker = f"#--MODULE:{module.name}--#"
    if marker not in template:
        raise ValueError(f"Marker {marker} not found in template for module version {module.version}")
    start = template.index(marker)
    end = template.index(END_MARKER, start)
    fragment = module.fragment_path.read_text().strip()
    fragment = f"{fragment}\n"
    return template[:start] + fragment + template[end + len(END_MARKER) :]


def render_manifest(manifest: dict, output_path: Path | None = None) -> Path:
    template_path = resolve_template(manifest)
    modules = load_modules(manifest)

    template = template_path.read_text()
    for module in modules:
        template = inject_fragment(template, module)

    output = Path(output_path or manifest.get("output", DEFAULT_OUTPUT))
    output.parent.mkdir(parents=True, exist_ok=True)
    if not template.endswith("\n"):
        template += "\n"
    output.write_text(template)
    print(
        "Rendered Dockerfile → %s (template %s, modules %s)"
        % (output, template_path, ", ".join(f"{m.name}:{m.version}" for m in modules))
    )
    return output


def main() -> None:  # pragma: no cover - CLI wrapper
    args = parse_args()
    manifest = load_manifest(args.manifest, args.manifest_id, args.manifest_store)
    render_manifest(manifest, args.output)


if __name__ == "__main__":
    main()
