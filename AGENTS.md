# AGENTS.md

This file provides context and instructions for AI coding agents working on this project


## Build Workflow (Mandatory Multi-Phase Execution)

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
    4. Mark the step as complete

**Rules:**
- Do not batch multiple steps together
- Do not proceed if tests fail
- Fix issues before continuing

---

## 6. Code Review & Summary Phase (CodeRabbit Enforced)

**Objective:**  
Perform an automated code review using CodeRabbit CLI, resolve issues, and produce a verified final summary.

### 6.1 Generate Review Output

The agent must run:

```bash
cr --plain --base dev > review_actions.txt
```

**Requirements:**
- The command must be executed after all TODO steps are complete
- The output must be saved to:
  review_actions.txt

---

### 6.2 Process Review Feedback (MANDATORY ITERATION)

The agent must:

1. Read and analyse all items in `review_actions.txt`
2. Categorise findings:
    - Bugs / correctness issues
    - Code quality issues
    - Style / consistency issues
    - Suggestions / improvements

---

### 6.3 Apply Fixes

- All actionable issues must be resolved
- Changes must follow the same rules as the Action Phase:
    - Make small, controlled updates
    - Run test suite after each logical fix group
    - Ensure all tests pass before continuing

---

### 6.4 Re-Run Review (Loop Until Clean)

After applying fixes, the agent must re-run:

```bash
cr --plain --base dev > review_actions.txt
```

**Iteration Rule:**
- This process must repeat until:
    - No critical or high-impact issues remain  
      OR
    - Remaining issues are explicitly documented and justified

---

### 6.5 Handling Unresolved Items

If any review items are not addressed, the agent must:

- Explicitly list them
- Provide justification for deferring them
- Mark them as:
    - Accepted risk, or
    - Requires developer decision

---

### 6.6 Final Validation

Before completing the phase:
- Run full test suite
- Confirm all tests are passing

---

### 6.7 Final Summary Output

Provide a clear summary including:
- Files changed
- Key fixes applied from CodeRabbit feedback
- Number and type of issues resolved
- Any remaining issues and justification
- Confirmation that:
    - Tests are passing
    - CodeRabbit review has been completed

---

## Global Stop Condition

At any point, the agent must halt and request clarification if:
- Relevant code cannot be identified
- The request conflicts with existing architecture
- Requirements are ambiguous or incomplete

The agent must not guess or invent solutions without sufficient grounding in the codebase.