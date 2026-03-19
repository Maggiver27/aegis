# AEGIS Fixed Review Prompt
Version: 1.1
Date: 2026-03-19
Authority: AEGIS v9.0

Review this module/change strictly against AEGIS governance.

## Required Checks

### 1. Current Step Check
- Is the work limited to the current active MSC step?
- Did it introduce future MSC components early?
- Did it introduce Trading, Development, or later-stage concerns?

### 2. Law 1 — Separation Law
- Are layer responsibilities preserved?
- Did any file mix Core, Domain, Integration, or Storage concerns incorrectly?

### 3. Law 2 — Control Law
- Does all intentional execution follow:
  Capability Registry ? Validation ? Permissions ? Action Bus ? Handler
- Did any code bypass or short-circuit this path?

### 4. Law 3 — Boundary Law
- Did any module absorb neighboring responsibilities?
- Is the module/function scope clean and narrow?

### 5. Law 4 — Evolution Law
- Does the change respect the locked build order?
- Did it create forward dependencies that violate staged growth?

### 6. Action Bus / Event Bus Separation
- Is Action Bus used only for intentional execution?
- Is Event Bus used only for state-change notification?
- Is there any contamination, overlap, or semantic blending?

### 7. Composition Root Compliance
- Is dependency wiring centralized?
- Was object creation scattered into modules that should not own composition?
- Does the change violate Core-owned composition?

### 8. Test Boundary Compliance
- Do tests validate only current-step responsibility?
- Do tests depend on future steps or hidden scaffolding?

### 9. Completion Integrity
- Is the implementation minimal, complete, and step-correct?
- Are there hidden assumptions, speculative hooks, or convenience abstractions?

## Output Format

### A) Strengths
List what is correct.

### B) Real Issues
List actual governance violations only.

### C) Why It Matters
Explain impact on AEGIS integrity.

### D) Severity
Rate each issue:
- ?? High
- ?? Medium-High
- ?? Medium
- ?? Low

### E) Improvement Proposals
Give exact corrective actions only.

## Final Rule
If the change violates build order, Law 2, Action Bus / Event Bus separation, or Composition Root ownership, it does not pass.

## Post-Review Action
If this review passes:
- Update `docs/governance/msc_ledger.md`
- Set `Reviewed = Yes`
- Set `Passed = Yes`
- `Signed Off` requires explicit human confirmation only

If this review fails:
- Do not update the ledger
- List the violations that must be resolved before re-review
