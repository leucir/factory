"""Smoke tests for the explore-plan CLI (dry-run only)."""

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "explore-plan.py"


def test_explore_plan_dry_run():
    result = subprocess.run(
        [sys.executable, str(CLI), "--plan", "baseline_core_light", "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "[DRY-RUN]" in result.stdout
    assert "baseline_core_light" in result.stdout


def test_explore_plan_missing_plan_exits_nonzero():
    result = subprocess.run(
        [sys.executable, str(CLI), "--plan", "does-not-exist", "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "Plan 'does-not-exist' not found" in (result.stdout + result.stderr)

