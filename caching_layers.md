# Caching Strategy for Layered Builds (Prototype)

This repository is a prototype. The ideas below are evolving; they are intended to guide experimentation and can be adapted as we learn.

## Problem

As the number of manifest combinations grows (Base OS × Security × Core × Light × App variants, multi‑arch, GPU), naïve builds become slow and costly:

- Repeating expensive steps (apt installs, Python dependency resolution, compiles) across hosts and architectures
- Rebuilding identical layers when only a later fragment changes
- Poor cross‑host reuse in distributed executor pools (amd64/arm64/GPU)

We need a cache strategy that maximizes reuse of stable layers (Base OS, Security, Core fragments) while still allowing rapid iteration in fast‑moving layers (Light/App fragments).

## Approach (BuildKit + OCI Cache)

Modern Docker uses BuildKit, which breaks a build into a DAG and keys each step by inputs:

- Dockerfile instruction + args/env
- Relevant input files’ content
- Base image digest and target platform (linux/amd64 vs linux/arm64)

When a key matches, BuildKit reuses the output from cache. We combine:

- Local cache: implicit on each builder; plus `RUN --mount=type=cache` for directories like `/var/cache/apt` and pip’s cache (already used in this repo)
- Remote registry cache: export cache metadata to an OCI registry so other hosts can import and reuse identical steps

### Recommended pattern

- Maintain per‑platform cache refs in a registry:
  - `<registry>/llm-factory-cache:linux-amd64`
  - `<registry>/llm-factory-cache:linux-arm64`
- Use Buildx with registry cache exporter/importer:

```
# Build and push (amd64), exporting cache
docker buildx build \
  --platform linux/amd64 \
  -f dockerfiles/Dockerfile.rendered \
  -t <registry>/llm-factory:dev \
  --cache-from=type=registry,ref=<registry>/llm-factory-cache:linux-amd64 \
  --cache-to=type=registry,ref=<registry>/llm-factory-cache:linux-amd64,mode=max \
  --push .

# Consume cache on another amd64 host (load to local Docker)
docker buildx build \
  --platform linux/amd64 \
  -f dockerfiles/Dockerfile.rendered \
  -t <registry>/llm-factory:dev \
  --cache-from=type=registry,ref=<registry>/llm-factory-cache:linux-amd64 \
  --load .
```

- Keep `RUN --mount=type=cache` for apt/pip; it accelerates iterative runs on a single host
- Prewarm stable layers (Base OS/Security/Core) periodically in each pool so executors hit cache immediately

### Inline cache (optional)

Alternatively embed cache metadata in released images (`--cache-to=type=inline` and `--cache-from <image>`). Works, but registry cache refs provide better separation and smaller runnable images.

## Where this integrates

- Executors (see scale.md) should pull a work item (manifest_id + platform), stitch, and build with `--cache-from/--cache-to` targeting the pool’s cache ref
- Control plane can seed nightly builds to update cache for stable layers and new base digests
- Compatibility records already include `manifest_id`; add optional fields for cache ref and builder metadata if needed later

## Invalidation semantics

Cache entries are invalidated automatically when any upstream key changes, including:

- Base image digest updates (e.g., Ubuntu security patches)
- Dockerfile instruction or build arguments
- Input file content (requirements.txt, fragments)
- Target platform (linux/amd64 vs linux/arm64)

Earlier steps may still be reused even if later steps change (e.g., App fragment edits won’t invalidate Core).

## Trade‑offs

- Pros
  - Faster builds and higher throughput across executor pools
  - Lower network and compute costs by avoiding repeated downloads/compiles
  - Deterministic reuse keyed on manifest/template/module versions
- Cons
  - Registry storage pressure (mode=max exports many intermediates); needs GC/retention
  - Operational complexity (Buildx setup, registry auth, per‑arch refs)
  - Risk of stale reuse if invalidation inputs are misconfigured (e.g., forgetting to include a file in COPY)

## Suggestions (Prototype)

- Gate cache usage behind env flags in scripts (e.g., `USE_BUILDX=1`, `CACHE_REF=...`) to toggle quickly
- Start with per‑arch refs in a single registry; add per‑cluster refs if cross‑region latency hurts
- Track cache hit/miss metrics per pool to validate effectiveness
- Document a retention policy (e.g., keep last N cache tags per manifest_id+arch)

This document reflects a prototype’s direction. Expect the strategy to evolve as we add more executors, GPU variants, and CI integration.

