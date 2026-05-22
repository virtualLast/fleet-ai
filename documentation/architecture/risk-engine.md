# Behavioural Risk Engine v2 — Dimension Composition Semantics (Final)

## 0. Purpose

This document defines how the three risk dimensions:

- **Persistent Risk**
- **Acute Risk**
- **Breadth Risk**

interact to produce:

- final risk classification
- intervention decisions
- confidence signals

> This is a **decision contract**, not a mathematical model.

---

## 1. Persistent Risk (Frequency + Severity Weighted)

### Definition
Persistent risk measures **how often unsafe behaviours occur, weighted by their severity**.

### Key properties
- Frequency matters (repetition across journeys)
- Severity modifies impact
- Both low-severity and high-severity behaviours contribute
- Rare but severe behaviour does **NOT** belong here unless it repeats

### Behaviour rules
 Behaviour pattern | Contribution |
---|---|
 Frequent low-severity | Contributes meaningfully |
 Frequent high-severity | Contributes strongly |
 Rare high-severity | Handled by Acute Risk, not Persistent |

### Role in system
- Represents behavioural habit
- Drives long-term coaching and monitoring decisions

---

## 2. Acute Risk (Single-Journey Severity Engine)

### Definition
Acute risk measures **severity of events within a single journey, including both spikes and repeated bursts**.

### Key properties
- Treats:
  - single extreme event
  - repeated medium spikes in one journey
  
  as part of the same acute scoring model
- Does **NOT** consider long-term patterns

### Behaviour rules
- High severity events dominate score
- Repeated medium spikes still contribute significantly
- Focus is *"how dangerous was this journey"*

### Role in system
- Represents immediate operational danger
- Primary trigger for urgent intervention

---

## 3. Breadth Risk (Weighted Behavioural Diversity)

### Definition
Breadth risk measures **how many different types of unsafe behaviour are present, using weighted behaviour importance**.

### Key properties
- Not simple counting
- Behaviour types are weighted
- Some behaviours contribute more than others (e.g. FCW > smoking)
- All behaviours belong to categories, but category grouping is **NOT** used to reduce breadth

### Important consequence
- FCW, HMW, PCW are treated as **separate behaviours**, not grouped

### Role in system
- Represents systemic behavioural instability across domains
- Supports risk interpretation and escalation strength

---

## 4. Dimension Independence Rules

### Hard separation constraints

 Dimension | Must NOT |
---|---|
 Persistent Risk | Reflect single-journey spikes; replicate acute scoring logic |
 Acute Risk | Reflect cross-journey repetition; represent behavioural habits |
 Breadth Risk | Be a simple count; ignore behavioural weighting |

---

## 5. Composition Philosophy (Critical)

### Core model
Final classification is **NOT a pure additive score**.

Instead:
- rule-based system
- with overrides
- with confidence modulation

### 5.1 Dimension roles

 Dimension | Role |
---|---|
 Acute | Primary safety override signal |
 Persistent | Behavioural habit signal |
 Breadth | Escalation strength signal |

---

## 6. Interaction Rules

### Rule A — Acute Override (Hard Priority)
High acute risk can override all other signals.
- Acute risk dominates when severe

### Rule B — Persistent Escalation
High persistent risk can elevate final classification even if acute risk is low.
- Represents long-term unsafe driving behaviour

### Rule C — Breadth as Escalation Driver (NOT primary classifier)
Breadth can:
- increase final risk level
- increase severity outcome

**BUT:** only when persistent or acute risk is already non-trivial.

### Rule D — Breadth cannot independently classify risk alone
- Breadth alone cannot create high risk classification
- It can only escalate existing risk signals

---

## 7. Intervention System (Multi-Trigger Model)

### Core design
Interventions are **NOT** derived from final classification alone.
Each dimension can independently trigger action.

### 7.1 Trigger rules

 Dimension | Trigger capability | Priority |
---|---|---|
 Acute Risk | Immediate intervention | Highest priority trigger |
 Persistent Risk | Coaching / monitoring | Behavioural correction focus |
 Breadth Risk | Intervention when combined with other signals | Never primary trigger alone |

### 7.2 Action combination rule
If multiple triggers fire:
> The system takes the **highest severity intervention**, not stacked actions.

---

## 8. Behaviour Categories (Registry Behaviour Rules)

### Key rule changes from v1
- Categories exist for **explanation only**
- Breadth uses individual behaviours, not category collapsing
- ADAS events are **NOT** grouped into a single hazard bucket

### Behaviour weighting usage
Weights apply to:
- Persistent scoring
- Acute scoring
- Breadth scoring

*(consistent cross-dimension weighting model)*

---

## 9. Explainability Contract

Every output must include:
- which dimension drove decision
- which behaviours contributed most
- whether acute override occurred
- whether breadth escalation occurred
- whether persistent escalation occurred

> No hidden logic allowed.

---

## 10. Final Classification Logic (Conceptual)

Final risk is determined using:
1. Acute risk evaluation
2. Persistent risk evaluation
3. Breadth escalation adjustment
4. Rule-based overrides
5. Intervention mapping (separate system)

---

## 11. Non-Goals

- No ML-based scoring
- No probabilistic inference
- No learned weighting
- No AI involvement in classification
- No hidden coupling between dimensions
- No category-level aggregation for breadth simplification

## Decision Precedence Rules

When multiple dimensions produce conflicting signals, the system must follow this strict precedence order:

 - 1. Acute Override (Highest Priority)
       If Acute Risk is classified as severe, it determines the final risk level.
Persistent and Breadth may adjust explanation, but cannot reduce or replace Acute-driven classification.
 - 2. Persistent-Driven Classification
If Acute Risk is not in a severe state, Persistent Risk becomes the primary driver of final classification.
Persistent Risk defines baseline risk level (low/medium/high).
 - 3. Breadth Escalation (Modifier Only)
Breadth Risk may increase the final risk level by one step maximum (e.g. low → medium, medium → high).
Breadth Risk cannot independently determine final classification.
Breadth Risk cannot override Acute or Persistent decisions.
 - 4. No Multi-Primary Conflict State
The system must always produce a single dominant driver dimension:
acute OR persistent (never both as co-equals)
Breadth is never a primary driver.

## Decision Trace Model

Every risk assessment MUST include a structured decision trace capturing how the final result was derived.

Structure
```json
DecisionTrace:
  primary_driver: "acute | persistent"
  dimensions:
    acute_risk: {score, level}
    persistent_risk: {score, level}
    breadth_risk: {score, level}
  rules_triggered:
    - "acute_override"
    - "persistent_classification"
    - "breadth_escalation"
  overrides_applied: boolean
  breadth_escalation_applied: boolean
  persistent_escalation_applied: boolean
  contributing_behaviours: [top N behaviours]
```

Purpose
Guarantees explainability of every decision
Prevents hidden scoring logic in implementation
Enables regression testing of rule execution (not just outputs)
