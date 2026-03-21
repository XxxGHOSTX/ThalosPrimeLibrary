<!-- PROPRIETARY AND CONFIDENTIAL -->
<!-- Copyright © 2026 Tony Ray Macier III. All Rights Reserved. -->

# Architecture — Thalos Prime Sovereign Discovery Platform

**Owner:** Tony Ray Macier III
**Version:** 2.0.0

## System Diagram

```mermaid
graph TD
    A[Network/Log Ingest] --> B{Sentinel Discovery}
    B -- Unauthorized AI Found --> C[Risk Analyzer]
    C -- High Risk Event --> D[Control Plane]
    D -- Derive Seed --> E[Artifact Engine]
    E -- Generate Fix --> F[Deterministic PR]
    H[User Inquiry] --> I[Concierge Assistant]
    I -- Context Request --> D
    D -- Hashed Proof --> I
    I -- Response --> H
```

## Module Interaction

```mermaid
graph LR
    subgraph Core_Services
        CP[Control Plane]
        SS[Seed Manager]
        LM[State Store]
    end
    subgraph Data_Plane
        SN[Sentinel Scanner]
        RA[Risk Analyzer]
        AE[Artifact Engine]
    end
    subgraph Interface
        CA[Concierge Assistant]
        MCP[MCP Gateway]
    end
    CP --> SS
    CP --> LM
    SN --> CP
    RA --> CP
    AE --> SN
    CA --> CP
    CA --> MCP
```

## Component Boundaries
- `/services/control-plane` — Brainstem: determinism, seeding, session state
- `/services/discovery-sentinel` — Eyes: passive network audits, shadow IT detection
- `/services/artifact-engine` — Hands: production-ready code and infrastructure templates
- `/core` — Primitives: stable reusable logic
- `/system` — Orchestration: pipeline coordination
