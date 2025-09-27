#!/usr/bin/env python3
"""Generate a compatibility record JSON document from build metadata."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import uuid
from pathlib import Path
from typing import Dict, Tuple

from manifest_utils import DEFAULT_MANIFEST_STORE, load_manifest

DEFAULT_MANIFEST = None
DEFAULT_RECORDS_DIR = Path("control_plane/data/compatibility/records")
MODULE_KEYS = ["security", "core", "light", "model_serve_mock"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, help="Path to manifest JSON (overrides --manifest-id)")
    parser.add_argument("--manifest-id", default="llm_factory", help="Manifest identifier in the manifest store")
    parser.add_argument("--manifest-store", type=Path, default=DEFAULT_MANIFEST_STORE, help="Path to manifest store JSON")
    parser.add_argument("--product-id", dest="product_id", default="llm_factory", help="Product identifier")
    parser.add_argument("--image", dest="image", default="", help="Built image tag or ID (optional)")
    parser.add_argument("--status", choices=["pass", "fail"], default="pass", help="Compatibility result status")
    parser.add_argument("--arch", default="linux/amd64", help="Target architecture")
    parser.add_argument("--test-suite", dest="test_suite", default="smoke-tests", help="String describing the test suite")
    parser.add_argument("--test-suite-file", dest="test_suite_file", type=Path, help="File whose contents should be hashed for the test suite")
    parser.add_argument("--base-digest", dest="base_digest", default="", help="Digest or identifier of the base image")
    parser.add_argument("--notes", default="", help="Optional notes to store in the record")
    parser.add_argument("--output", type=Path, help="Explicit path to write the record")
    parser.add_argument("--records-dir", type=Path, default=DEFAULT_RECORDS_DIR, help="Directory to place the record when --output is not provided")
    parser.add_argument("--build-id", dest="build_id", default="", help="Unique identifier for this build execution")
    parser.add_argument("--evidence-path", dest="evidence_path", type=Path, help="Path to associated evidence file")
    parser.add_argument("--sbom-path", dest="sbom_path", type=Path, help="Path to SBOM file for the image")
    return parser.parse_args()


def compute_test_suite_hash(args: argparse.Namespace) -> str:
    if args.test_suite_file:
        data = args.test_suite_file.read_bytes()
    else:
        data = args.test_suite.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def inspect_image(image: str) -> str:
    if not image:
        return ""
    try:
        output = subprocess.check_output(["docker", "image", "inspect", image, "--format", "{{.Id}}"], text=True)
        return output.strip()
    except subprocess.CalledProcessError:
        return ""


def ensure_records_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def make_output_path(args: argparse.Namespace, build_id: str) -> Path:
    if args.output:
        return args.output
    timestamp = build_id or dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ensure_records_dir(args.records_dir)
    filename = f"{args.product_id}-{timestamp}.json"
    return args.records_dir / filename


def build_record(args: argparse.Namespace) -> Tuple[Dict, str]:
    manifest = load_manifest(args.manifest, args.manifest_id, args.manifest_store)
    template_cfg = manifest.get("template", {})
    template_id = template_cfg.get("id", "unknown_template")
    template_version = template_cfg.get("version", "unknown")

    modules = {m.get("name"): m.get("version", "unknown") for m in manifest.get("modules", [])}

    build_id = args.build_id or uuid.uuid4().hex

    record: Dict = {
        "build_id": build_id,
        "template_id": template_id,
        "template_version": template_version,
        "base_digest": args.base_digest or manifest.get("base_image", "unknown_base"),
        "manifest_id": args.manifest_id,
        "security_version": modules.get("security", "unknown"),
        "core_version": modules.get("core", "unknown"),
        "light_version": modules.get("light", "unknown"),
        "model_serve_mock_version": modules.get("model_serve_mock", "unknown"),
        "arch": args.arch,
        "test_suite_hash": compute_test_suite_hash(args),
        "result": {
            "status": args.status,
            "image_digest": inspect_image(args.image) or args.image,
            "tested_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
            "notes": args.notes,
        },
        "metadata": {
            "manifest_id": args.manifest_id,
            "manifest_store": str(args.manifest_store),
            "manifest_path": str(args.manifest) if args.manifest else "",
            "product_id": args.product_id,
            "image": args.image,
            "evidence_path": str(args.evidence_path) if args.evidence_path else "",
            "sbom_path": str(args.sbom_path) if args.sbom_path else "",
        },
    }
    return record, build_id


def main() -> None:
    args = parse_args()
    record, build_id = build_record(args)
    output_path = make_output_path(args, build_id)
    output_path.write_text(json.dumps(record, indent=2) + "\n")
    print(f"Compatibility record written to {output_path}")
    print(f"Build ID: {build_id}")


if __name__ == "__main__":
    main()
