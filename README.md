# Factory - Layered Image Prototype

This repository is a prototype. The ideas below are evolving; they are intended to guide experimentation and can be adapted as we learn.

A prototype factory for building Docker images from composable layers. The goal is to incrementally assemble, test, and cache reusable modules so future builds are faster and safer.

## Architecture Principles

- **Composable layers over monolithic Dockerfiles** – Templates + module fragments make it easy to swap stacks (e.g., CUDA vs. CPU) and keep changes localized.
  - Tradeoffs: more files/manifests to coordinate, ordering constraints between fragments, and no built-in type checks for cross-module contracts.
  - Mitigations: codify simple interfaces (env args/labels/paths), lint fragments, and add per-module smoke tests.

- **Manifest-driven versioning** – Explicit template/module versions make rebuilds deterministic and reproducible.
  - Tradeoffs: version matrix can grow quickly; drift if versions are changed ad‑hoc.
  - Mitigations: curate supported sets, pin versions in manifests, and use compatibility records as an allowlist/cache.

- **Configuration-first, read-only control plane** – Products/pipelines/artifacts live as JSON and are served read‑only via FastAPI for clarity and auditability.
  - Tradeoffs: no runtime edits; potential drift between JSON and on-disk modules; not a source of truth for execution state.
  - Mitigations: keep JSON in VCS, add write APIs + validation later, or back with a DB when multi-user edits are needed.

- **Evidence-backed compatibility records** – Every build/test writes a minimal verdict plus a pointer to evidence.
  - Tradeoffs: adds a little I/O; records can go stale as bases/drivers/security posture change.
  - Mitigations: include base digests and test hashes (already done), and apply expiry/policy checks before reuse.

- **Platform-aware build scripts** – Scripts honor `--platform` so cross-arch hosts (e.g., arm64 Macs) produce usable amd64 images.
  - Tradeoffs: cross-building can miss runtime-only issues; GPU validation won’t happen on non‑GPU hosts.
  - Mitigations: run smoke/integration tests on target architectures in CI; run GPU tests on GPU runners.

- **Host GPU dependency isolation** – CUDA lives in the `core` layer; hosts install the NVIDIA toolkit to expose GPUs.
  - Tradeoffs: bigger images and possible driver/CUDA version skew at runtime.
  - Mitigations: pin CUDA versions, document minimum driver/toolkit, and validate on GPU hosts.

## TL;DR

- Build the full image + smoke test locally with `./tools/run-ci-local.sh [product_id]` (defaults to `llm_factory`; add `llm_factory_cuda` for the GPU stack).
- Exercise the control-plane flow end-to-end using `./tools/run-ci-local-api.sh [product_id] [pipeline_id]`, which renders, builds, tests, and records evidence.
- Inspect plan matrices quickly via `./tools/explore-plan.sh --plan baseline_core_light --dry-run` or drop the flag to execute every combo.
- Focus on a single fragment with `./tools/test-fragment.sh --manifest-id core_smoke` (swap manifests to target other layers).
- Outputs land under `control_plane/data/compatibility/` (records/evidence/SBOM); cache builds make repeat runs faster.
- On GPU hosts, run `sudo ./tools/install-nvidia-container-toolkit.sh` once so CUDA containers see the hardware.

## Project Structure

```
factory/
├── model_serve_mock/           # Mock model-serving layer packaged in the final image
├── build/                      # Buildx bake file & cache ignore rules
├── ci/                         # CI workflow template
├── compatibility/              # Compatibility records and documentation
├── control_plane/              # FastAPI control plane & tests
├── dockerfiles/                # Rendered Dockerfile + versioned templates
├── manifests/                  # Manifests mapping templates/modules to versions
├── control_plane/data/modules/ # Layer fragments (security/core/light/model_serve_mock)
├── control_plane/data/schemas/ # JSON schemas (e.g., compatibility record)
├── tools/                      # Stitching and smoke-test scripts
└── README.md                   # This file
```

### Modules

| Layer     | Purpose                                   | Key files |
|-----------|-------------------------------------------|-----------|
| security  | OS patching & security packages           | `control_plane/data/modules/security/<version>/`
| core      | Stable runtimes & base tooling            | `control_plane/data/modules/core/<version>/`
| light     | Fast-moving libraries (e.g., transformers)| `control_plane/data/modules/light/<version>/`
| model_serve_mock | Mock model-serving layer & entrypoint | `control_plane/data/modules/model_serve_mock/<version>/`

Each module version declares metadata in `module.json` (including an `order`) and supplies a `Dockerfile.fragment`. The Stitch tool reads a manifest from the consolidated store (`control_plane/data/manifest.json`) via its ID (e.g. `llm_factory`) to select a template + fragment versions, injects those fragments into the template, and writes `dockerfiles/Dockerfile.rendered`.

Need to validate a fragment in isolation? Use the lightweight `core_smoke` template + manifest:

```
python3 tools/stitch.py --manifest-id core_smoke
docker build -f dockerfiles/Dockerfile.core_smoke -t llm-factory:core-smoke .
```

The template at `dockerfiles/templates/core_smoke/0.1.0/Dockerfile.tpl` only exposes the `#--MODULE:core--#` marker, so the rendered Dockerfile contains just the `core` fragment (`control_plane/data/modules/core/0.3.0/`). Swap the manifest's module version to exercise other iterations, or clone the template with different markers if you want to isolate additional modules.

Prefer a single command? `./tools/test-fragment.sh` wraps the render/build/run flow (defaults target the core smoke manifest) and lets you override the manifest, output, image tag, or the runtime smoke command.

#### CUDA Variant

Need GPU runtime? Use the `llm_factory_cuda` entry in the manifest store (`control_plane/data/manifest.json`), which swaps in the CUDA-enabled core module (`control_plane/data/modules/core/0.2.0/`) while still starting from `ubuntu:22.04`. The control-plane exposes this as product `llm_factory_cuda` and pipeline `layered_build_pipeline_cuda`.

### Compatibility Knowledge

- Schema: `control_plane/data/schemas/compatibility.schema.json`
- Records: `control_plane/data/compatibility/records/`
- Script: `tools/write-compatibility-record.py` (called by CI/local scripts to persist results)
- Evidence: `control_plane/data/compatibility/evidence/<build_id>.log` (smoke-test output captured per run)
- SBOMs: `control_plane/data/compatibility/sbom/<build_id>.json` (generated via Syft; scripts skip if Syft is absent)
- Error captures: `control_plane/data/compatibility/records/error-<build_id>.json` (written when a build fails; includes a tail of the evidence log for fast triage)

Pipelines persist the outcome of each build/test cycle (base digest + module versions + architecture + test hash → pass/fail + image digest). When the same combination appears again, the factory can decide to reuse the recorded result instead of rebuilding from scratch.

## Typical Workflow

```
python3 tools/stitch.py --manifest-id llm_factory
docker build -f dockerfiles/Dockerfile.rendered -t llm-factory:dev .
./tools/test-runner.sh llm-factory:dev
```

To mirror the CI pipeline locally, run:

```
./tools/run-ci-local.sh                # defaults to product llm_factory
./tools/run-ci-local.sh llm_factory_cuda
```

To execute the same flow via the control-plane API metadata:

```
./tools/run-ci-local-api.sh                              # defaults to llm_factory / layered_build_pipeline
./tools/run-ci-local-api.sh llm_factory_cuda layered_build_pipeline_cuda
```

If you plan to run the CUDA variant on a GPU-enabled host, install the NVIDIA Container Toolkit first:

```
sudo ./tools/install-nvidia-container-toolkit.sh
```

For multi-platform or cached builds, use Buildx Bake:

```
docker buildx bake -f build/bake.hcl
```

## BONUS

- Empirically check the host Docker layer limit (creates throwaway images until a build fails):
  ```
  ./tools/check-layer-limit.sh --max 150
  ```

`buildx bake` reads `build/bake.hcl` and can target multiple platforms in one run (amd64/arm64) while reusing registry/local caches. The factory scripts stick to single-platform builds; Bake is the quickest way to fan out builds once you have BuildKit drivers and cache storage configured.

## Control Plane Integration

`control_plane/data/product.json` links the `llm_factory` product to the manifest, versioned template, modules, and compatibility store. `control_plane/data/pipeline.json` defines a pipeline that renders, builds, tests, and records results.

## Next Steps

- Expand `build/bake.hcl` with additional bases (e.g., Debian) and architectures.
- Add SBOM/signing tools in dedicated modules or CI steps.
- Persist compatibility records to your database or OCI referrers in addition to the sample files.
