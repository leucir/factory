#!/usr/bin/env python3
"""Execute an exploration test plan across module combinations.

This CLI:
- Reads a plan from control_plane/data/test_plan.json
- Expands matrix combinations (e.g., core/light versions)
- For each combination renders the Dockerfile, builds, smoke-tests,
  optionally generates an SBOM, and writes a compatibility record.

Usage (dry run):
    ./tools/explore-plan.sh --plan baseline_core_light --dry-run

Usage (execute all combos):
    ./tools/explore-plan.sh --plan baseline_core_light

Prerequisites:
- Docker daemon available
- tools/test-runner.sh functional for the target image
"""

from __future__ import annotations

import argparse
import itertools
import json
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from manifest_utils import DEFAULT_MANIFEST_STORE, load_manifest

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLANS_PATH = ROOT / "control_plane" / "data" / "test_plan.json"
"""Default location for exploration plans."""

DEFAULT_PRODUCTS_PATH = ROOT / "control_plane" / "data" / "product.json"
"""Source of product metadata (image names, manifests, etc.)."""

COMPAT_ROOT = ROOT / "control_plane" / "data" / "compatibility"
"""Root directory where evidence and records are written."""

EVIDENCE_DIR = COMPAT_ROOT / "evidence"
"""Directory for build/test logs generated per combination."""

RECORDS_DIR = COMPAT_ROOT / "records"
"""Compatibility record output directory."""

DEFAULT_TEST_RUNNER = ROOT / "tools" / "test-runner.sh"
"""Fallback test runner path if plan metadata omits it."""

WRITE_RECORD_SCRIPT = ROOT / "tools" / "write-compatibility-record.py"
"""Helper script used to persist compatibility outcomes."""

STITCH_SCRIPT = ROOT / "tools" / "stitch.py"
"""Renderer that stitches module fragments into a Dockerfile."""
MANIFEST_STORE = ROOT / DEFAULT_MANIFEST_STORE


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the exploration runner."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, dest="plan_id", help="Plan identifier in the JSON store")
    parser.add_argument("--plan-file", type=Path, default=DEFAULT_PLANS_PATH, help="Path to test_plan.json")
    parser.add_argument(
        "--products-file", type=Path, default=DEFAULT_PRODUCTS_PATH, help="Path to product.json for metadata"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only expand the plan and print intended actions without building or testing",
    )
    parser.add_argument(
        "--notes",
        default="explore-plan",
        help="Notes field to include in compatibility records (ignored during dry-run)",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Do not remove the temporary manifest directory (useful for debugging)",
    )
    return parser.parse_args()


def load_json(path: Path) -> Dict[str, Any]:
    """Read a JSON file from disk and return it as a dict."""

    if not path.exists():
        raise FileNotFoundError(f"Missing JSON file: {path}")
    return json.loads(path.read_text())


def load_plan(plan_file: Path, plan_id: str) -> Dict[str, Any]:
    """Fetch a specific plan from the plan store; raise if missing."""

    plans = load_json(plan_file)
    if plan_id not in plans:
        raise KeyError(f"Plan '{plan_id}' not found in {plan_file}")
    return plans[plan_id]


def resolve_product_metadata(products_file: Path, product_id: str) -> Dict[str, Any]:
    """Return metadata (image/tag/build platform/test runner) for a product."""

    products = load_json(products_file)
    product = products.get(product_id, {})
    metadata = product.get("metadata", {})
    return {
        "image_name": product.get("docker_image_name", product_id or "explore-image"),
        "image_tag": product.get("docker_tag", "dev"),
        "build_platform": metadata.get("build_platform", ""),
        "manifest_id": metadata.get("manifest_id"),
        "test_runner": metadata.get("test_runner", str(DEFAULT_TEST_RUNNER)),
    }


def expand_combos(plan: Dict[str, Any]) -> Iterable[Dict[str, str]]:
    """Yield every module-version combination defined in the plan matrix."""

    fixed = plan.get("fixed", {})
    matrix = plan.get("matrix", {})
    axes = sorted(matrix.keys())
    if not axes:
        raise ValueError("Plan matrix is empty; nothing to explore")

    values = [matrix[key] for key in axes]
    for combination in itertools.product(*values):
        combo = dict(zip(axes, combination))
        combo.update({k: v for k, v in fixed.items() if v})
        yield combo


def combination_slug(combo: Dict[str, str]) -> str:
    """Produce a filesystem-safe slug from a combo mapping (for IDs/files)."""

    parts = [f"{key}-{value}" for key, value in sorted(combo.items())]
    safe = "_".join(parts)
    return safe.replace("/", "-")


def ensure_dirs() -> None:
    """Ensure evidence and records directories exist."""

    for path in (EVIDENCE_DIR, RECORDS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def write_manifest(base_manifest: Dict[str, Any], combo: Dict[str, str]) -> Tuple[Path, Dict[str, Any]]:
    """Create a temporary manifest reflecting the given module combination."""

    base_manifest = json.loads(json.dumps(base_manifest))
    modules = base_manifest.get("modules", [])
    for module in modules:
        name = module.get("name")
        if not name:
            continue
        key = name
        if key in combo:
            module["version"] = combo[key]
    temp_dir = Path(tempfile.mkdtemp(prefix="explore-plan-"))
    manifest_path = temp_dir / "manifest.json"
    manifest_path.write_text(json.dumps(base_manifest, indent=2) + "\n")
    return manifest_path, base_manifest


def tee_subprocess(cmd: List[str], log_file: Path) -> None:
    """Run a subprocess, teeing stdout/stderr to both console and log file."""

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    with process.stdout:  # type: ignore[arg-type]
        with log_file.open("a") as handle:
            for line in process.stdout:  # type: ignore[union-attr]
                sys.stdout.write(line)
                handle.write(line)
    ret = process.wait()
    if ret != 0:
        raise subprocess.CalledProcessError(ret, cmd)


def run_plan(args: argparse.Namespace) -> int:
    """Execute all combinations for the selected plan (or dry-run)."""

    ensure_dirs()
    plan = load_plan(args.plan_file, args.plan_id)
    product_id = plan.get("product_id", "")
    product_meta = resolve_product_metadata(args.products_file, product_id)
    manifest_id = plan.get("manifest_id") or product_meta.get("manifest_id")
    if not manifest_id:
        raise ValueError("Plan is missing 'manifest_id'")
    base_manifest = load_manifest(None, manifest_id, MANIFEST_STORE)

    image_name = product_meta["image_name"]
    base_tag = product_meta["image_tag"]
    build_platform = plan.get("build_platform") or product_meta.get("build_platform", "")
    test_runner_ref = plan.get("test_runner") or product_meta.get("test_runner") or str(DEFAULT_TEST_RUNNER)
    test_runner_path = Path(test_runner_ref)
    if not test_runner_path.is_absolute():
        test_runner_path = ROOT / test_runner_path
    test_runner = str(test_runner_path)

    combos = list(expand_combos(plan))
    if args.dry_run:
        print(f"[DRY-RUN] Would execute {len(combos)} combinations for plan '{args.plan_id}'")
        for combo in combos:
            print(" -", combination_slug(combo), combo)
        return 0

    summary: List[Tuple[str, str]] = []
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")

    for combo in combos:
        slug = combination_slug(combo)
        build_id = f"{args.plan_id}-{slug}-{timestamp}"
        evidence_path = EVIDENCE_DIR / f"{build_id}.log"
        image_tag = f"{image_name}:{base_tag}-{slug}"
        status = "pass"
        notes = args.notes
        manifest_path = None
        temp_dir: Path | None = None
        evidence_path.write_text(f"# Build ID: {build_id}\n")
        try:
            manifest_path, _ = write_manifest(base_manifest, combo)
            temp_dir = manifest_path.parent
            with evidence_path.open("a") as handle:
                handle.write(f"[PLAN] Manifest written to {manifest_path}\n")

            tee_subprocess([sys.executable, str(STITCH_SCRIPT), "--manifest", str(manifest_path)], evidence_path)

            build_cmd = [
                "docker",
                "build",
                "-f",
                "dockerfiles/Dockerfile.rendered",
                "-t",
                image_tag,
                ".",
            ]
            if build_platform:
                build_cmd[2:2] = ["--platform", build_platform]
            tee_subprocess(build_cmd, evidence_path)

            evidence_path.open("a").write("[PLAN] Skipping SBOM generation for exploratory run\n")

            tee_subprocess([test_runner, image_tag], evidence_path)

            record_cmd = [
                sys.executable,
                str(WRITE_RECORD_SCRIPT),
                "--manifest-id",
                manifest_id,
                "--manifest-store",
                str(MANIFEST_STORE),
                "--product-id",
                product_id,
                "--image",
                image_tag,
                "--status",
                status,
                "--notes",
                notes,
                "--build-id",
                build_id,
                "--evidence-path",
                str(evidence_path),
                "--records-dir",
                str(RECORDS_DIR),
            ]
            if manifest_path:
                record_cmd[2:2] = ["--manifest", str(manifest_path)]
            tee_subprocess(record_cmd, evidence_path)
        except subprocess.CalledProcessError as exc:
            status = "fail"
            evidence_path.open("a").write(f"[PLAN] Command failed: {shlex.join(exc.cmd)}\n")
            failure_notes = f"{notes} (failure exit={exc.returncode})"
            failure_cmd = [
                sys.executable,
                str(WRITE_RECORD_SCRIPT),
                "--manifest-id",
                manifest_id,
                "--manifest-store",
                str(MANIFEST_STORE),
                "--product-id",
                product_id,
                "--image",
                image_tag,
                "--status",
                status,
                "--notes",
                failure_notes,
                "--build-id",
                build_id,
                "--evidence-path",
                str(evidence_path),
                "--records-dir",
                str(RECORDS_DIR),
            ]
            if manifest_path:
                failure_cmd[2:2] = ["--manifest", str(manifest_path)]
            tee_subprocess(failure_cmd, evidence_path)
        finally:
            if not args.keep_temp and temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
        summary.append((slug, status))

    print("\n[SUMMARY]")
    for slug, status in summary:
        print(f" - {slug}: {status}")
    return 0


def main() -> None:
    """Entry point for the CLI."""

    args = parse_args()
    try:
        rc = run_plan(args)
    except Exception as exc:  # pragma: no cover - CLI safeguard
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    sys.exit(rc)


if __name__ == "__main__":
    main()
