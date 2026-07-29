# Idea Validation

## Chosen idea

**UAE Compliance Copilot** — an open-source, multi-agent system that ingests a UAE SME's financial records
(invoices, transactions, counterparties) and produces one unified compliance report covering:

1. VAT / Corporate Tax reconciliation and misclassification flags
2. FTA e-invoicing (PINT AE) field-readiness validation
3. Sanctions/PEP screening of counterparties
4. Reconciliation anomalies (duplicates, round-tripping, mismatched totals)

This directly combines pain points #1–4 from `research.md`, which are all instances of the same underlying failure:
manual, spreadsheet-based compliance reconciliation with no audit trail, at a moment (e-invoicing pilot live since
July 2026) when the cost of getting it wrong is rising.

## 1. Problem clarity

UAE SMEs and DNFBPs must manually reconcile financial records against VAT, Corporate Tax, e-invoicing, and AML rules
with no dedicated compliance staff, and errors carry direct fines (AED 2,500/invoice, AED 5,000/month for
e-invoicing non-compliance) plus audit risk.

## 2. Existing solutions

- **Generic accounting software** (Zoho Books, QuickBooks, Xero UAE editions) — records transactions and calculates
  VAT but does not proactively reconcile Corporate Tax vs. VAT, validate e-invoicing field completeness against the
  new PINT AE schema, or screen counterparties against sanctions lists. It is a system of record, not a compliance
  reviewer.
- **Big-4 / boutique advisory firms** — provide the reasoning UAE SMEs actually need, but are expensive, engaged
  periodically (quarterly/annually) rather than continuously, and don't scale down to small businesses.
- **Point AML/KYC screening tools** (Refinitiv World-Check, ComplyAdvantage) — solve sanctions screening well but
  in isolation from tax/e-invoicing compliance, and are priced for larger regulated entities, not SMEs or DNFBPs.
- **Gap**: nothing in the SME price range continuously reconciles *across* tax, e-invoicing readiness, and
  counterparty screening and explains findings in plain language.

## 3. Agentic fit

A single script or API call can't do this well because the four sub-problems require different reasoning styles
that build on each other: (a) intake/normalization of messy, inconsistently-formatted records, (b) deterministic
rule checking (field presence, duplicate detection) that must not hallucinate, (c) fuzzy entity-matching reasoning
for sanctions screening, and (d) synthesis of all of the above into a prioritized, explained action list for a
non-specialist business owner. Coupling all of this into one monolithic prompt would blow past context limits on
anything but a trivial dataset and would make it impossible to swap out or improve one capability (e.g., updating
the e-invoicing field schema) without touching everything else. A supervisor that delegates to scoped specialist
agents, each with its own tools and context, mirrors how a real advisory team divides this work and lets each
capability be tested, versioned, and improved independently — the definition of a good agentic-architecture fit.

## 4. Feasibility

Yes. The MVP needs: (a) Pydantic models for invoices/transactions/counterparties, (b) a bundled sample sanctions/PEP
list for fuzzy-match screening (no external API dependency required for the MVP — pluggable for OFAC/UN consolidated
list or a commercial provider later), (c) a rules engine for e-invoicing field validation based on publicly
documented mandatory fields, (d) an LLM-abstraction layer so any provider (cloud or local) can power the reasoning
steps, and (e) a lightweight DAG engine to orchestrate agents. All of this is buildable with standard open-source
Python tooling (pydantic, httpx, a stdlib-based fuzzy matcher) in a single session, and is fully testable with a
mock LLM provider so the test suite has zero external dependency.

## 5. Community value

Yes. While the rules content (VAT rates, e-invoicing fields, sanctions data source) is UAE-specific and swappable,
the architecture — supervisor + specialist agents + shared state + pluggable LLM providers (cloud/local/hybrid) +
graph orchestration — is a reusable pattern for *any* jurisdiction's compliance-reconciliation problem. Developers
in other markets (KSA, EU VAT/e-invoicing, US sanctions screening) can fork this and swap the rules/tools layer
while keeping the orchestration, LLM abstraction, and testing patterns intact.

## Decision: **GO**

Evidence is strong and current (live regulatory deadline), the problem cleanly decomposes into specialist agents,
an MVP is feasible in one session with zero required paid API keys for testing, and the architecture generalizes
beyond the UAE — satisfying all five validation criteria.
