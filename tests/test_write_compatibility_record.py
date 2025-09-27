import hashlib
import json
import subprocess
from pathlib import Path


def test_write_compatibility_record(tmp_path: Path):
    project_root = Path(__file__).resolve().parents[1]
    output = tmp_path / "record.json"

    build_id = "test-build-123"
    evidence = tmp_path / "evidence.log"
    evidence.write_text("test evidence")
    sbom = tmp_path / "sbom.json"
    sbom.write_text("{\"sbom\": true}")

    subprocess.run(
        [
            "python",
            str(project_root / "tools" / "write-compatibility-record.py"),
            "--manifest-id",
            "llm_factory",
            "--image",
            "llm-factory:test",
            "--status",
            "pass",
            "--notes",
            "unit-test",
            "--test-suite",
            "unit-tests",
            "--build-id",
            build_id,
            "--evidence-path",
            str(evidence),
            "--sbom-path",
            str(sbom),
            "--output",
            str(output),
        ],
        check=True,
        cwd=project_root,
    )

    record = json.loads(output.read_text())
    assert record["template_id"] == "llm_factory"
    assert record["build_id"] == build_id
    assert record["result"]["status"] == "pass"
    assert record["result"]["notes"] == "unit-test"
    expected_hash = hashlib.sha256(b"unit-tests").hexdigest()
    assert record["test_suite_hash"] == expected_hash
    assert record["metadata"]["image"] == "llm-factory:test"
    assert record["metadata"]["evidence_path"] == str(evidence)
    assert record["metadata"]["sbom_path"] == str(sbom)
