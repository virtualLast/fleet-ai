# AGENTS.md

This file provides context and instructions for AI coding agents working on this project.

---

# Build Workflow (Mandatory Multi-Phase Execution)

All agents must follow this workflow when implementing any change.
No phase may be skipped. Progression between phases is gated.

Failure to comply with any requirement must result in the agent halting and requesting clarification.

---

## 1. Research Phase (No Code Changes Allowed)

**Objective:**  
Develop a concrete understanding of how the existing codebase handles similar functionality.

**Output:**  
documentation/research/<task-name>.md

**Requirements:**
- Identify all relevant code:
    - File paths
    - Classes, functions, methods
- Describe existing patterns:
    - Architecture (e.g. service layer, controllers, hooks)
    - Naming conventions
    - Error handling
    - Logging
- Map data flow:
    - Entry points → processing → persistence → response
- List dependencies:
    - Internal modules/services
    - External libraries/APIs
- Identify constraints and risks:
    - Legacy coupling
    - Fragile areas
    - Performance or security considerations

**Evidence Rule (MANDATORY):**
- Every claim must reference actual code:
    - File path + function/class name
- Vague summaries are not allowed

**Prohibited:**
- Writing implementation code
- Making assumptions without code references

---

## 2. Implementation Plan Phase

**Objective:**  
Define how the requested change will be implemented using findings from the Research Phase.

**Output:**  
documentation/implementation/<task-name>.md

**Requirements:**
- Reference the research document explicitly
- Define:
    - Files to create/update/delete
    - Functions/classes to add or modify
    - Data structures and flow
- Include code examples/snippets where useful
- Maintain consistency with existing patterns

**Deviation Rule:**
- Any deviation from existing patterns must be:
    - Explicitly stated
    - Justified

---

## 3. TODO Plan Phase

**Objective:**  
Break the implementation into precise, executable steps.

**Output:**  
documentation/todo/<task-name>.md

**Requirements:**
- Steps must be:
    - Atomic (small, single-purpose)
    - Sequential (clear execution order)
- Each step must include:
    - What is being changed
    - Where (file/class/function)
    - Reference to implementation plan where relevant
    - A test/validation instruction

**Example Format:**
- [ ] Add method authenticateWithToken() to AuthService
  - Follow pattern from authenticate() (see research doc)
  - Add/update unit tests
  - Run test suite and confirm all tests pass

**Prohibited:**
- Large, vague steps (e.g. “implement feature”)

---

## 4. Review & Approval Phase (Hard Gate)

**Objective:**  
Ensure human validation before any code changes are made.

**Requirements:**
- The agent must:
    - Explicitly request approval
    - Provide paths to:
        - Research document
        - Implementation plan
        - TODO plan
- The agent must halt execution

**Hard Rule:**
- No code changes may be made until the developer responds with explicit approval (e.g. “APPROVED”)

---

## 5. Action Phase (Controlled Execution)

**Objective:**  
Execute the TODO plan safely and incrementally.

**Requirements:**
- Follow TODO steps in order
- For each step:
    1. Implement the change
    2. Run the test suite
    3. Confirm all tests pass
    4. Confirm `make check` passes
    5. Mark the step as complete

**Rules:**
- Do not batch multiple steps together
- Do not proceed if tests fail
- Fix issues before continuing

---

## 6. Code Review & Summary Phase (CodeRabbit Enforced)

**Objective:**  
Perform iterative automated code review using CodeRabbit CLI, resolve actionable findings, and produce a verified final implementation summary.

### 6.1 Review Output Location (MANDATORY)

All CodeRabbit review outputs must be written to:

```text
documentation/review/
```

Review files must NEVER be overwritten.

Each review pass must create a new file using the format:

```text
<task-name>-review-<number>.txt
```

Example:

```text
documentation/review/fleet-risk-summary-review-1.txt
documentation/review/fleet-risk-summary-review-2.txt
documentation/review/fleet-risk-summary-review-3.txt
```

The review number must increment for every CodeRabbit execution within the task lifecycle.

---

### 6.2 Generate Initial Review

The agent must run:

```bash
cr --plain --base <target-branch> > documentation/review/<task-name>-review-1.txt
```

---

### 6.3 Process Review Feedback (MANDATORY ITERATION)

The agent must:

1. Read and analyse all review findings
2. Categorise findings into:
   - Bugs / correctness issues
   - Security concerns
   - Performance concerns
   - Code quality issues
   - Style / consistency issues
   - Suggestions / maintainability improvements
3. Determine which findings are:
   - Actionable
   - Non-actionable
   - False positives
   - Requiring developer decision

---

### 6.4 Apply Fixes

The agent must:

- Resolve all actionable issues
- Preserve behavioural correctness
- Avoid introducing speculative refactors
- Run relevant tests after each logical fix group

---

### 6.5 Re-Run Review (MANDATORY LOOP)

After fixes are applied, the agent must generate a new review file:

```bash
cr --plain --base <target-branch> > documentation/review/<task-name>-review-<next-number>.txt
```

The review/fix cycle must continue until one of the following is true:

- No actionable findings remain
- Remaining findings are explicitly classified as:
  - Accepted risk
  - False positive
  - Requires developer decision

The agent must NEVER overwrite previous review files.

The agent must NEVER claim a review is clean without re-running CodeRabbit after the final code changes.

---

### 6.6 Handling Unresolved Findings

If unresolved findings remain, the agent must explicitly document:

- The finding
- Why it was not addressed
- Associated risk
- Whether developer input is required

Unresolved findings must appear in the final summary.

---

### 6.7 Final Validation

Before completing the phase, the agent must:

- Run the full test suite
- Confirm all tests pass
- Confirm no new linting/type issues were introduced
- Confirm review outputs were persisted correctly

---

### 6.8 Final Summary Output

Provide a final implementation summary including:

- Files changed
- Key fixes applied
- Review iterations performed
- Review files generated
- Issues resolved
- Remaining unresolved findings
- Test results
- Final implementation status

---

## 7. Documentation Requirement for New Code (Mandatory)

Whenever an agent adds or changes implementation code, documentation must also be updated.

---

## Global Stop Condition

At any point, the agent must halt and request clarification if:
- Relevant code cannot be identified
- The request conflicts with existing architecture
- Requirements are ambiguous or incomplete

---


## Project Guidelines

### Writing function / method documentation

Function and method documentation must clearly explain behavior, assumptions, and boundaries.

Required elements (when applicable):
- What the function/method does
- Inputs and important assumptions/constraints
- Return value/output shape
- Side effects (cache writes, file I/O, API calls, logging side effects)
- Error/exception behavior

Style rules:
- Use concise single-line docstrings for simple helper functions.
- Use multi-line docstrings for non-trivial logic, orchestration, or validation behavior.
- Start with an action-oriented summary line (e.g., `Return ...`, `Generate ...`, `Normalize ...`).

Example (simple helper):

```python
def _safe_int(value: object, fallback: int = 0) -> int:
    """Safely coerce a value into int with fallback for invalid inputs."""
```

Example (non-trivial function):

```python
def generate_driver_behaviour_summary(collection_scope: str, collection_data: list[dict]) -> str:
    """Generate one plain-text summary for a normalized collection dataset.

    Args:
        collection_scope: Fleet/driver scope identifier for cache and trace context.
        collection_data: Input rows used to compute deterministic behavior and AI summary.

    Returns:
        A plain-language summary string.

    Raises:
        ValueError: If input payload is empty or malformed.
    """
```

### Writing tests

Tests must be properly documented with three key elements:
 - What is being tested
 - Why we have this test
 - How the test is structured

Additional test-writing guidelines:
- Use behavior-oriented test names that describe expected outcomes.
- Keep structure clear with `Arrange / Act / Assert` flow.
- Keep tests deterministic (stable data, controlled mocks/monkeypatching, fixed ordering).
- Prefer one behavior assertion focus per unit test unless integration scope intentionally validates a full flow.
- Assert both primary outputs and relevant side effects (cache writes, API calls, persisted fields) when applicable.
- Use fixtures/monkeypatch only where needed, and avoid hidden coupling between tests.

Example test documentation block:

```python
"""What: Verify behaviour cache keys are stable across row order and scalar type differences.
Why: Cache misses for equivalent payloads increase API latency and cost.
How: Build keys from equivalent payload permutations and assert equality.
"""
```

Example test structure:

```python
def test_generate_driver_behaviour_summary_returns_cached_result(monkeypatch):
    """What: Return cached summary on cache hit.
    Why: Avoid unnecessary AI calls and preserve deterministic response latency.
    How: Stub cache loader to return existing entry and verify generator is not called.
    """

    # Arrange
    payload = [{"driverId": "D-1", "tailgating": 0}]

    # Act
    result = generate_driver_behaviour_summary("scope-1", payload)

    # Assert
    assert result == "cached summary"
```

### Working in TDD flow

When implementing behavior changes, prefer short Red → Green → Refactor cycles:
- Red: Add or update one deterministic test that fails for the target behavior.
- Green: Implement the minimal change required to make that test pass.
- Refactor: Improve readability/design without changing behavior, and keep tests green.

TDD execution rules:
- Keep each cycle atomic and focused on a single behavior outcome.
- Confirm the new/updated test fails for the expected reason before applying the fix.
- Run relevant tests after each Green and Refactor step.
- Keep tests documented with `What / Why / How` and structured with `Arrange / Act / Assert`.

If strict test-first ordering is not feasible (for example, urgent hotfixes or legacy constraints), document the reason explicitly and add backfill test coverage immediately after stabilization.