# Executive Summary — Layered Image Factory (Prototype)

This is a prototype for building container images quickly, safely, and repeatably at scale. It turns image creation into a simple, manifest‑driven “factory” process so teams can ship more reliably with less toil.

## The Problem We’re Solving

Modern platforms ship many image variants (base OS + security + runtimes + app glue, across amd64/arm64 and GPU). Rebuilding these combinations is:
- Slow and repetitive (same layers built over and over)
- Hard to reason about (what changed, what passed, what is safe to reuse?)
- Expensive (compute, bandwidth, and human time)

## Our Approach (Simple, Deterministic, Observable)

- Simple
  - One handle to build: a manifest ID that defines template + module versions; tools accept `--manifest-id` everywhere.
  - Composable fragments keep the mental model small (swap Security/Core/Light/App without touching a monolith).
  - A read‑only control plane and small CLI surface area reduce moving parts.

- Deterministic
  - Everything is pinned in a consolidated store (template + module versions + base image); builds are reproducible by design.
  - Explicit platform selection (`--platform`) and idempotency keys (manifest + base digest + arch) ensure consistent outputs.
  - The stitch step renders exactly what the manifest declares—no hidden state.

- Observable
  - Each run emits a compatibility record (verdict + timestamps), an evidence log, and an SBOM.
  - Failures also write a succinct `error-<build_id>.json` with the log tail for fast triage.
  - First dashboards track queue depth, build/test durations, and cache hit/miss to prove value over time.

## At a Glance

```mermaid
flowchart LR
  classDef cp fill:#E3F2FD,stroke:#1E88E5,color:#0D47A1,stroke-width:2px
  classDef q  fill:#FFF3E0,stroke:#FB8C00,color:#E65100,stroke-width:2px
  classDef ex fill:#E8F5E9,stroke:#43A047,color:#1B5E20,stroke-width:2px
  classDef st fill:#F3E5F5,stroke:#8E24AA,color:#4A148C,stroke-width:2px

  CP[Control Plane]:::cp --> Q[Queues]:::q
  Q --> EX[Executors]:::ex
  EX --> ST[Shared Stores]:::st
  ST --> CP
```

## Why It Matters (Outcomes)

- Faster lead time: high cache hit rates for stable layers; rebuild only what changed
- Lower cost: less redundant compute and network, better use of executor pools
- Better confidence: every image has evidence and an SBOM; “what passed” is clear
- Scales with you: multi‑arch and GPU‑aware, ready to fan out across pools

## Scale‑Out Plan (brief)

- Executor pools per platform (amd64 / arm64 / gpu) pull work from queues
- Registry cache prewarmed with Base/Security/Core for fast startup
- Results are published asynchronously; control plane summarizes status



## Caching Highlights

- Use Buildx with registry cache per architecture (e.g., `llm-factory-cache:linux-amd64`)
- Always build with `--platform`; don’t mix caches across arches
- Keep `RUN --mount=type=cache` for apt/pip to speed local iterations



## What’s Ready Now (Prototype)

- CLI workflows to render, build, test, and record products
- Consolidated manifest store addressed by `manifest_id`
- Error capture (`error-<build_id>.json`) with log tails for quick triage
- Unit tests for core CLI flows
- Architecture documents

## What’s Next

- Stand up per‑arch queues and minimal executor pools
- Enable registry cache and add prewarm jobs for stable layers
- First dashboards: queue depth, build durations, cache hit/miss
- Security hardening (image signing, provenance), and retention policies for caches/evidence/records

## Learn More

- Quick start and rationale: [README.md](README.md#tldr)
- Architecture background: [README.md](README.md#architecture-principles)
- Scale‑out details: [scale.md](scale.md)
- Caching strategy: [caching_layers.md](caching_layers.md)
