# Active Scope ù AEGIS
Version: 1.0
Date: 2026-03-19
Authority: AEGIS v9.0

## Governing Authority
- Blueprint: AEGIS v9.0
- Roadmap: active roadmap authority
- Stage: MSC

## Current Active Step
- MSC-2 Core Configuration Loader

## Composition Root Location
`app/core/composition/composition_root.py`

All dependency wiring for MSC components must be centralized through this file.
No module may create cross-component runtime dependencies outside this location unless explicitly approved.

## In Scope
- Only code, tests, and minimal supporting files required for MSC-2 Core Configuration Loader
- YAML runtime profile loading for the canonical profile:
  `config/profiles/laptop.runtime.yaml`

## Out of Scope
- MSC-3 and later
- Trading
- Development
- Plugins
- Memory / Knowledge
- Advanced monitoring
- Device Control
- External providers
- UI beyond what MSC-1 strictly requires
- UI beyond what MSC-2 strictly requires

## Advancement Condition
This step may move forward only when:
1. implementation is complete
2. tests for this step pass
3. AEGIS review prompt returns pass
4. ledger row is marked signed off

## Notes
No forward scaffolding.
No speculative architecture.
No mixing Action Bus and Event Bus semantics.
No scattered dependency wiring.
YAML runtime profile loading is allowed only for MSC-2 and must use `config/profiles/laptop.runtime.yaml`.
