# Evaluation (Stage 5 — appraise the output)

> Sub-guide of the `research` skill. Adapted from the K-Dense AI `scholar-evaluation` skill. Rubric-based scholarly assessment with traceability. Scripts under `scripts/evaluation/`, templates under `assets/evaluation/`.

## Contents

- [Purpose](#purpose)
- [Hard safety boundary](#hard-safety-boundary)
- [ScholarEval status](#scholareval-status)
- [Metric and prestige policy](#metric-and-prestige-policy)
- [Data boundary](#data-boundary)
- [Workflow](#workflow)
- [Interpretation rules](#interpretation-rules)
- [Bundled resources](#bundled-resources)

## Purpose

Provide developmental, evidence-traceable feedback on a **scholarly work**:
paper, draft, protocol, literature synthesis, or research idea. Use
qualitative judgment first. Optional scores only describe how submitted
evidence maps to a predeclared bounded rubric.

This skill also audits whether a low-stakes assessment process documents its
construct, provenance, rater quality, uncertainty, traceability, sensitivity,
fairness, accessibility, privacy, and human governance.

## Hard safety boundary

Never use this skill to automate, recommend, materially influence, or score:

- hiring, promotion, or tenure;
- admissions;
- grants or other funding;
- prizes, honors, or awards;
- discipline, dismissal, or sanctions; or
- any other high-impact personnel decision.

Never rank people. Never reduce a person to a composite score. Never infer
ability, character, integrity, protected traits, future performance, or worth.
A nominal human-in-the-loop does not remove this boundary.

If asked for a prohibited use, stop. Offer developmental comments on a
scholarly work or a process-only audit that does not process applications,
compare people, recommend an outcome, or advise a decision.

Do not issue publication-readiness, accept/reject, or “top-tier” judgments.

Read `references/evaluation/responsible_assessment.md` before any organizational use.

## ScholarEval status

The referenced ScholarEval project is an **experimental
literature-grounded research-idea evaluation framework**, not validated
psychometrics.

The verified primary record is Moussa et al., *ScholarEval: Research Idea
Evaluation Grounded in Literature*, arXiv:2510.16234v2, revised 2026-02-28.
It reports a retrieval-augmented soundness/contribution framework, a
117-idea four-discipline dataset, coverage experiments, and a user study.

Do not generalize those results to person assessment, consequential decisions,
all disciplines, or this skill's rubric. No peer-reviewed publication status
was verified during the dated review. See `references/evaluation/source_ledger.md`.

## Metric and prestige policy

Do not score or infer quality from:

- Journal Impact Factor or other journal measures;
- h-index, publication counts, or citation counts;
- altmetrics or attention;
- journal, conference, venue, institution, employer, or geographic prestige;
- author affiliation, reputation, network, or career path.

The rubric validator rejects common proxy-measure criteria.

If a qualified reviewer mentions an indicator descriptively outside the
scoring tools, record its exact purpose, source, coverage, field and time
effects, uncertainty, missingness, biases, gaming risk, and why it does not
directly measure quality. Never hide indicators inside an opaque composite.

## Data boundary

Bundled scripts accept only strict local JSON/CSV containing pseudonymous IDs,
bounded ratings, statuses, uncertainty, and local references.

Do not put raw private applications, CVs, letters, reviewer identities,
contact details, protected attributes, or source-document text in inputs,
outputs, logs, examples, or prompts. Keep source content in the authorized
records system and use opaque local references.

Allowed classifications are:

- `synthetic`
- `public_scholarly_work`
- `deidentified_low_stakes`

No script searches the web, loads environment files, reads credentials, calls a
model, executes supplied text, deserializes executable objects, or launches a
process.

Use Bash only to invoke the documented local `python3` commands.

## Workflow

### 1. Confirm allowed use and authorization

Record:

- developmental purpose;
- unit of assessment: `scholarly_work`;
- work type, stage, discipline, language, and audience;
- authorized source location and data classification;
- accountable committee owner;
- conflicts and recusals;
- accessibility and accommodation process;
- appeal or correction route; and
- data purpose, access, retention, and deletion.

Stop on a prohibited decision context or unnecessary private data.

### 2. Define the construct before criteria

State:

- what quality or support is being examined;
- excluded constructs;
- intended interpretation;
- contexts where the interpretation does not travel;
- evidence requirements; and
- known limitations.

Start with values and disciplinary context, not available metrics.

### 3. Adapt and validate the rubric

Begin with `assets/evaluation/rubric_template.json`, then obtain qualified disciplinary,
assessment-methods, stakeholder, accessibility, privacy, and fairness review.

The template deliberately records content validity as `not_established`.
Do not change that status without documented evidence for the exact intended
use.

Validate structure:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/evaluation/validate_rubric.py \
  --rubric assets/evaluation/rubric_template.json
```

Read `references/evaluation/evaluation_framework.md` for construct, anchor, validity, and
rater guidance.

### 4. Build traceable evidence records

Reviewers may read an authorized work outside the scripts. Record only stable
local locators and claim references in
`assets/evaluation/evidence_manifest_template.json`.

For every criterion, distinguish:

- observed evidence from interpretation;
- supporting from contrary evidence;
- available from unavailable evidence;
- `missing` from `not_applicable`; and
- uncertainty from absence.

Failure to find prior work does not prove novelty.

### 5. Rate independently

Use `assets/evaluation/evaluation_template.json`. Each criterion must be:

- `rated` with an anchor score, bounded uncertainty, evidence IDs, and a local
  rationale reference;
- `missing` with null score/uncertainty and a rationale reference; or
- `not_applicable` with null score/uncertainty and a rationale reference.

Do not encode missing or not-applicable as zero. Raters should train, calibrate,
disclose conflicts, rate independently, and document disagreement.

### 6. Run local quality checks

Bounded scoring, without labels or recommendation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/evaluation/calculate_scores.py \
  --rubric assets/evaluation/rubric_template.json \
  --evaluation assets/evaluation/evaluation_template.json
```

Evidence traceability:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/evaluation/check_traceability.py \
  --rubric assets/evaluation/rubric_template.json \
  --evaluation assets/evaluation/evaluation_template.json \
  --evidence assets/evaluation/evidence_manifest_template.json
```

Inter-rater agreement:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/evaluation/summarize_agreement.py \
  --rubric assets/evaluation/rubric_template.json \
  --ratings assets/evaluation/ratings_template.csv
```

Weight sensitivity requires two or more distinct scholarly-work evaluation
files:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/evaluation/weight_sensitivity.py \
  --rubric assets/evaluation/rubric_template.json \
  --evaluation /tmp/work-a-evaluation.json \
  --evaluation /tmp/work-b-evaluation.json
```

Process controls:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/evaluation/check_process.py \
  --process assets/evaluation/process_checklist_template.json
```

The checklist template is intentionally unconfirmed and fails closed.
Instructions and exact schemas are in `references/evaluation/local_tooling.md`.

### 7. Synthesize qualitative findings

Lead with criterion-level evidence, not the composite. For each criterion:

1. cite evidence references;
2. state `rated`, `missing`, or `not_applicable`;
3. explain the anchor interpretation;
4. report score and uncertainty only if rated;
5. note disagreements and context;
6. identify strengths and limitations; and
7. offer non-prescriptive improvement options.

Generate an empty-reference scaffold if useful:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/evaluation/generate_report_scaffold.py \
  --rubric assets/evaluation/rubric_template.json \
  --evaluation assets/evaluation/evaluation_template.json \
  --output /tmp/developmental-report-scaffold.json
```

The scaffold does not read source documents or draft findings.

### 8. Human review and release

Before releasing an organizational report, a qualified accountable human
committee must verify:

- construct and rubric provenance;
- content-validity evidence and limits;
- rater training, agreement, inter-rater reliability evidence, and drift;
- evidence traceability and source access;
- missingness, not-applicable rationales, and uncertainty;
- weight sensitivity and order instability;
- disciplinary and subgroup bias review;
- conflicts and recusals;
- accessibility and accommodations;
- privacy, minimization, retention, and output controls; and
- correction or appeal information.

Document dissent. Do not imply consensus, validity, or precision beyond the
evidence. Periodically evaluate the evaluation and retire harmful criteria.

## Interpretation rules

- A score is an ordinal rubric summary, not a natural measurement.
- Normalization does not repair incomplete evidence.
- The bundled uncertainty range is not a confidence interval.
- Agreement does not establish reliability, validity, fairness, or correctness.
- Stable results under tested weights do not establish validity.
- The overall score never overrides criterion evidence or qualified judgment.
- No output is a decision recommendation.

## Bundled resources

- `references/evaluation/responsible_assessment.md` — safety, metrics, governance,
  accessibility, privacy, and bias.
- `references/evaluation/evaluation_framework.md` — ScholarEval boundary, construct,
  criteria, anchors, validity, and interpretation.
- `references/evaluation/local_tooling.md` — strict schemas, formulas, commands, and
  output behavior.
- `references/evaluation/source_ledger.md` — authoritative sources and publication-status
  verification dated 2026-07-23.
- `references/evaluation/security_validation.md` — baseline remediation, validation, and
  residual security-scan record.
- `assets/evaluation/rubric_template.json` — bounded rubric template.
- `assets/evaluation/evaluation_template.json` — rating template.
- `assets/evaluation/evidence_manifest_template.json` — traceability template.
- `assets/evaluation/process_checklist_template.json` — fail-closed process checklist.
- `assets/evaluation/ratings_template.csv` — synthetic agreement data.
