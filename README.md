# Factory - Layered Image Prototype

This repository is a prototype. The ideas below are evolving; they are intended to guide experimentation and can be adapted as we learn.

A prototype factory for building Docker images from composable layers. The goal is to incrementally assemble, test, and cache reusable modules so future builds are faster and safer.

## Architecture Principles

- **Container‑as‑a‑product**
  - Treat each image as a first‑class product with a clear spec: template ID/version + module versions + target platform. The spec lives in the consolidated manifest store (`control_plane/data/manifest.json`) and is addressed by `manifest_id`.
  - Products are reproducible and testable: every build emits evidence, an SBOM, and a compatibility record. Past records help decide when to rebuild vs. reuse.
  - The control plane exposes read‑only APIs so multiple teams can consume the same product definitions without coupling to the build implementation.

- **Planes (separation of concerns)**
  - Control plane: read‑only API, manifest store, plan expansion, and (in a future phase) work scheduling. It describes “what” should be built and records “what happened”.
  - Compute plane: build executors that render, build, and test on platform‑specific hosts (amd64/arm64/GPU). It executes the “how” and pushes images, evidence, and records.
  - Data plane: shared stores (OCI registry/cache, evidence/SBOM object storage, compatibility records). It preserves “what was produced”.
  - This prototype implements a minimal control plane and local executors; see Design Docs for the scale‑out plan.

- **Composable layers over monolithic Dockerfiles** – Templates + module fragments make it easy to swap stacks (e.g., CUDA vs. CPU) and keep changes localized.
  - Injection points are explicit via template markers `#--MODULE:<name>--# … #--ENDMODULE--#` and stitched by `tools/stitch.py`.
  - Module metadata (`module.json`) provides `order` so assembly is deterministic across versions.
  - Local dev loop: render one fragment with `core_smoke` or run matrix explorations with `tools/explore-plan.sh`.
  - Caching synergy: stable layers (Security/Core) hit cache even when fast‑moving layers (Light/App) change.
  - Considerations & mitigations: more files/manifests to coordinate and ordering constraints between fragments; no built‑in type checks across modules. Address by codifying simple interfaces (env args/labels/paths), linting fragments, and adding per‑module smoke tests.

- **Manifest-driven versioning** – Explicit template/module versions make rebuilds deterministic and reproducible.
  - The consolidated store (`control_plane/data/manifest.json`) keys manifests by `manifest_id` (e.g., `llm_factory`, `llm_factory_cuda`).
  - Tools accept `--manifest-id`/`--manifest-store`; test plans and records reference the ID for portability.
  - Idempotency keys naturally derive from template/module versions, base digest, and target platform.
  - Considerations & mitigations: the version matrix can grow quickly and drift if versions change ad‑hoc. Address by curating supported sets, pinning manifest entries, and using compatibility records as an allowlist/cache.

- **Configuration-first, read-only control plane** – Products/pipelines/artifacts live as JSON and are served read‑only via FastAPI for clarity and auditability.
  - JSON lives under `control_plane/data/`; the API simply reflects what’s on disk for transparency in this prototype.
  - Write paths (scheduling, promotions) can be added later with validation and a backing DB to avoid drift.
  - Records and evidence are treated as data plane concerns; the control plane links to them and summarizes rollups.
  - Considerations & mitigations: no runtime edits and potential drift between JSON and on‑disk modules; not a system‑of‑record for execution state. Address by keeping JSON in VCS, introducing write APIs with validation, or backing with a DB for multi‑user edits.

- **Evidence-backed compatibility records** – Every build/test writes a minimal verdict plus a pointer to evidence.
  - Records capture `manifest_id`, module versions, base digest, arch, test hash, result, and pointers to evidence/SBOM.
  - Failures emit `error-<build_id>.json` with a log tail to accelerate triage without opening full logs.
  - Results are idempotent and auditable; re‑runs with identical inputs can be short‑circuited.
  - Considerations & mitigations: adds some I/O and records can go stale as bases/drivers/security posture change. Address by recording base digests and test hashes and enforcing expiry/policy checks before reuse.

- **Platform-aware build scripts** – Scripts honor `--platform` so cross-arch hosts (e.g., arm64 Macs) produce usable amd64 images.
  - Smoke tests inherit platform via `DOCKER_DEFAULT_PLATFORM` to avoid runtime mismatches during `docker run`.
  - Buildx + registry cache lets pools (amd64/arm64) share intermediate layers where possible.
  - Per‑arch queues/executors (see scale.md) keep placement simple while maximizing cache hits.
  - Considerations & mitigations: cross‑building can miss runtime‑only issues and GPU validation won’t happen on non‑GPU hosts. Address by running smoke/integration tests on target architectures and executing GPU tests on GPU runners.

- **Host GPU dependency isolation** – CUDA lives in the `core` layer; hosts install the NVIDIA toolkit to expose GPUs.
  - GPU variant (`llm_factory_cuda`) swaps Core in the manifest; executors in a GPU pool pick up those jobs.
  - Keep the base image consistent (e.g., Ubuntu 22.04) to simplify layer reuse across CPU/GPU stacks.
  - Validate driver/runtime pairs on GPU hosts; gate promotion on GPU smoke tests.
  - Considerations & mitigations: bigger images and possible driver/CUDA version skew at runtime. Address by pinning CUDA versions, documenting minimum driver/toolkit, and validating on GPU hosts.

## High‑Level Diagram

```mermaid
flowchart LR
  classDef cp fill:#E3F2FD,stroke:#1E88E5,color:#0D47A1,stroke-width:2px
  classDef q  fill:#FFF3E0,stroke:#FB8C00,color:#E65100,stroke-width:2px
  classDef ex fill:#E8F5E9,stroke:#43A047,color:#1B5E20,stroke-width:2px
  classDef st fill:#F3E5F5,stroke:#8E24AA,color:#4A148C,stroke-width:2px

  CP[Control Plane]:::cp
  Q[Queues]:::q
  EX[Executors]:::ex
  ST[Shared Stores]:::st

  CP -- manifests/plans --> Q
  Q  -- work --> EX
  EX -- images + records + evidence --> ST
  ST -- summaries --> CP
```

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
├── modules/                    # Layer fragments (security/core/light/model_serve_mock)
├── control_plane/data/manifest.json   # Consolidated manifest store (keys → manifest definitions)
├── schemas/                    # JSON schemas (e.g., compatibility record)
├── tools/                      # Stitching and smoke-test scripts
└── README.md                   # This file
```

### Modules

| Layer     | Purpose                                   | Key files |
|-----------|-------------------------------------------|-----------|
| security  | OS patching & security packages           | `modules/security/<version>/`
| core      | Stable runtimes & base tooling            | `modules/core/<version>/`
| light     | Fast-moving libraries (e.g., transformers)| `modules/light/<version>/`
| model_serve_mock | Mock model-serving layer & entrypoint | `modules/model_serve_mock/<version>/`

Each module version declares metadata in `module.json` (including an `order`) and supplies a `Dockerfile.fragment`. The Stitch tool reads a manifest from the consolidated store (`control_plane/data/manifest.json`) via its ID (e.g. `llm_factory`) to select a template + fragment versions, injects those fragments into the template, and writes `dockerfiles/Dockerfile.rendered`.

Need to validate a fragment in isolation? Use the lightweight `core_smoke` template + manifest:

```
python3 tools/stitch.py --manifest-id core_smoke
docker build -f dockerfiles/Dockerfile.core_smoke -t llm-factory:core-smoke .
```

The template at `dockerfiles/templates/core_smoke/0.1.0/Dockerfile.tpl` only exposes the `#--MODULE:core--#` marker, so the rendered Dockerfile contains just the `core` fragment (`modules/core/0.3.0/`). Swap the manifest's module version to exercise other iterations, or clone the template with different markers if you want to isolate additional modules.

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

## Design Docs

- Scaling plan: see [scale.md](scale.md)
- Caching strategy: see [caching_layers.md](caching_layers.md)

## Control Plane Integration

`control_plane/data/product.json` links the `llm_factory` product to the manifest, versioned template, modules, and compatibility store. `control_plane/data/pipeline.json` defines a pipeline that renders, builds, tests, and records results.

## Next Steps

- Expand `build/bake.hcl` with additional bases (e.g., Debian) and architectures.
- Add SBOM/signing tools in dedicated modules or CI steps.
- Persist compatibility records to your database or OCI referrers in addition to the sample files.
