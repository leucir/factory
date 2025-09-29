# Executive Summary — Container as a product : The Factory (Prototype)

This is a prototype for building container images quickly, safely, and repeatably at scale. It turns image creation into a simple, manifest‑driven “factory” process so teams can ship more reliably with less toil.

## The Problem We’re Solving

Modern platforms ship many image variants (base OS + security + runtimes + app glue, across amd64/arm64 and GPU). Rebuilding these combinations is:
- Slow and repetitive (same layers built over and over)
- Hard to reason about (what changed, what passed, what is safe to reuse?)
- Expensive (compute, bandwidth, and human time)

### The pain for the Consumers (Platform/App Teams)

- Delayed access to updated images when fixes or features land; waits depend on the factory build cycles
- Inconsistent variants across architectures/GPU; missing or untested tags block delivery
- Low visibility into change and safety: unclear diffs, no easy SBOM/provenance to prove what’s inside
- Compliance/security uncertainty: patch status and attestations are not obvious or auditable


## Our Approach (Simple, Deterministic, Observable)

- **Simple**
  - One simple identifier tells the system exactly what to build - no complex configuration needed.
  - Building blocks can be mixed and matched easily - swap security, core, or app components without rebuilding everything.
  - The system has a clean, easy-to-use interface that reduces complexity.

- **Deterministic**
  - Everything is clearly defined and locked in place - the same input always produces the same output.
  - The system knows exactly which platform to build for and ensures consistent results every time.
  - The build process follows the exact recipe specified - no surprises or hidden changes.

- **Observable**
  - Every build produces clear records showing what happened, when it happened, and whether it succeeded.
  - When things go wrong, the system provides clear error reports to help fix problems quickly.
  - KPIs to show how the system is performing - build times, success rates, and efficiency metrics.



## Constructs that matter

Below, we present the key concepts and examples to guide you through this document and the rest of the repository.

### Core Entities

- **Product**: The final artifact produced by the factory. It defines what to build with metadata like image names, tags, and manifest references. Products are the "what" - they specify the end goal.

- **Manifest**: The blueprint that specifies which template and module versions to use for a build. Manifests are the "how" - they define the exact combination of fragments needed to create a specific product variant.

- **Template**: The base structure that gets populated with fragments. Templates provide the skeleton that fragments fill in with specific functionality. The Factory can have one or multiple templates.

- **Fragment**: Versioned layer components (security, core, light, app) that can be composed together. Fragments are the "building blocks" - reusable, testable pieces of functionality. We can add more or fewer fragments in a template.

### Key Capabilities

- **Structured Cache Library**: Optimize cache per manifest by maintaining architecture-specific cache layers (e.g., `llm-factory-cache:linux-amd64`) that can be shared across builds.

- **Matrix Combinations**: Easily create new products by combining different fragments or upgrading using new manifests. This enables systematic testing of component combinations.

- **Isolated Fragment Testing**: Test individual fragments in isolation to ensure they work correctly before combining them into full products.

- **Combined Fragment Testing**: Test how fragments work together in various combinations to catch integration issues early.

### Key Outcomes

- **Image**: The final Docker image produced by the factory (the product itself), built from the specified manifest and fragments, ready for deployment.

- **Cache**: Optimized layer caching that speeds up builds by reusing unchanged layers across different product variants.

- **SBOM**: Software Bill of Materials that provides transparency into what components and dependencies are included in each image.

- **Evidence**: Detailed build logs and test results that provide audit trails and debugging information for each build.

- **Record**: Compatibility records that capture build results, test outcomes, and metadata for tracking and compliance.

- **Error**: Structured error reports with log excerpts that enable quick triage and resolution of build failures.

### Infrastructure

- **Control Plane**: The brain of the system that manages product definitions, state, and automation. It serves read-only APIs for manifests, products, and test plans, providing the authoritative source of truth for what to build and how to build it.

- **Queues**: The scalability backbone that enables decoupling and control. Queues distribute work across executor pools, handle load balancing, and provide resilience through retry mechanisms and dead letter queues.

- **Executors**: The workforce that performs the actual build, test, and deployment work. Executors can be organized into pools by architecture (amd64, arm64) or capability (GPU), with each pool optimized for specific types of work.

- **Shared Stores**: The optimized set of technologies that cache and accelerate build and deployment processes. This includes OCI registries for layer caching, object storage for evidence and SBOMs, and compatibility record stores for tracking build outcomes.


## At a Glance

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

## Why It Matters (Outcomes)

- Faster lead time: high cache hit rates for stable layers; rebuild only what changed
- Lower cost: less redundant compute and network, better use of executor pools
- Better confidence: every image has evidence and an SBOM; “what passed” is clear
- Scales with you: multi‑arch and GPU‑aware, ready to fan out across pools
- Shift-left: Test and conformance at earlier stages in the product conception


## What’s Ready Now (Prototype)

- Initial Factory definition and major constructs design
- CLI workflows to render, build, test, and record products
- Consolidated manifest store, templates, and fragments
- Error, and additional governance artifacts produced and collected
- Unit tests for core CLI flows
- Architecture documents


## What’s Next

- Stand up per‑arch queues and minimal executor pools
- Enable registry cache and add prewarm jobs for stable layers
- First dashboards: queue depth, build durations, cache hit/miss
- Security hardening (image signing, provenance), and retention policies for caches/evidence/records
- Improved CLI, API, and UI to address experiences of all systems and personas involved

## Learn More

- Quick start and rationale: [README.md](README.md#tldr)
- Architecture background: [README.md](README.md#architecture-principles)
- Scale‑out details: [scale.md](scale.md)
- Caching strategy: [caching_layers.md](caching_layers.md)
- AI improving the factory: [ai4tech.md](ai4tech.md)
- An alternative using Github actions and Docker Bake: [gitaction_docker_solution.md](gitaction_docker_solution.md)

---

**Note**: This prototype was developed with AI assistance under full human supervision and control. AI was used to support the development process while maintaining human oversight and decision-making throughout.
