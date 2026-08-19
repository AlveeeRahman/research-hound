---
name: research-hound
description: Five-stage scientific research workflow - critical thinking (appraise evidence, spot bias and statistical misuse), literature review (PubMed/arXiv/Semantic Scholar search, synthesis, citation verification), brainstorming (scored idea triage), writing (IMRaD, claim-evidence tracing, CONSORT/PRISMA/STROBE checklists), and evaluation (rubric scoring, inter-rater agreement). Use for academic work - framing a research question, systematic reviews and meta-analyses, critiquing a study design, drafting a paper or grant, checking citations, peer review - including when only the artifact is named (my methods section, reviewer 2 says, is this p-hacking).
license: MIT (upstream K-Dense-AI/scientific-agent-skills, MIT)
allowed-tools: Read Edit Write Bash(python3 scripts/*)
compatibility: Python 3.10+. Every script runs offline on the standard library except one: scripts/literature-review/verify_citations.py needs requests and queries DOI resolvers to check that a reference resolves. Nothing else leaves the machine, and no script needs an API key. Write diagrams as Mermaid inline.
metadata:
  version: "1.1.1"
  composed-from: "scientific-critical-thinking, literature-review, scientific-brainstorming, scientific-writing, scholar-evaluation (K-Dense AI)"
---

# Research

Five stages of scientific work in one skill. Read only the guide for the stage you are in —
the guides are large, and loading all five crowds out the work itself.

## Two ways to use this skill

**Single-stage (the common case).** When the request names one kind of work — "brainstorm
hypotheses", "check my citations", "score these submissions" — go straight to that stage's
guide and do only that. Do not run the pipeline, do not walk the person through earlier
stages, do not append unrequested next steps. Asking for brainstorming means brainstorming.

**Full pipeline.** When the request is a whole project — "take this idea to a paper",
"run the full workflow", "I'm starting a new study" — follow the academic sequence below in
order, and say which stage you are entering as you go.

If it is genuinely unclear which mode applies, ask once. A misjudged full pipeline wastes
far more of the person's time than a misjudged single stage.

## The pipeline

```
1. CRITICAL      2. LITERATURE     3. BRAIN-           4. WRITING      5. EVAL-
   THINKING         REVIEW            STORMING                            UATION
   Is the           What is           What are the      Say it          Is it any
   question         already           candidates,       precisely,      good? Score
   sound?           known?            which survive?    traceably.      it honestly.
      │                │                   │                │               │
      └────────────────┴───────────────────┴────────────────┴───────────────┘
                     Findings at any stage can send you back upstream.
```

| Stage | Read | You are here when |
| ----- | ---- | ----------------- |
| **1. Critical thinking** | [guides/critical-thinking.md](guides/critical-thinking.md) | Framing a question, appraising evidence quality, critiquing a design, checking for bias, fallacy, or statistical misuse |
| **2. Literature review** | [guides/literature-review.md](guides/literature-review.md) | Searching PubMed/arXiv/Semantic Scholar, systematic review or meta-analysis, synthesising prior work, verifying citations, establishing the gap |
| **3. Brainstorming** | [guides/brainstorming.md](guides/brainstorming.md) | Generating hypotheses or study designs, running structured ideation, triaging many ideas down to a few |
| **4. Writing** | [guides/writing.md](guides/writing.md) | Drafting or revising IMRaD sections, tracing claims to evidence, citations, reporting checklists, authorship |
| **5. Evaluation** | [guides/evaluation.md](guides/evaluation.md) | Peer review, rubric scoring, inter-rater agreement, grant or submission assessment, traceability audits |

Figures are not a stage. Write them as Mermaid inline — Claude Code and claude.ai both
render a ` ```mermaid ` block, which covers flowcharts, CONSORT and PRISMA diagrams,
pathways and architectures — or build them in the plotting library you already analyse
in. `references/writing/figures_tables.md` carries the publication standards.

Start at the guide. It carries the stage's workflow and names the reference files that
matter for the step you are on. The index below exists so any one of them can also be
opened in a single step — a file reached only through another file tends to get skimmed
rather than read to the end.

**Why literature review sits at stage 2.** Brainstorming before searching the literature
generates ideas that are already published, and the cost of finding that out is measured in
months. The review is also what converts a broad question into a specific gap, which is the
input stage 3 actually needs. In academia this ordering is not a preference — it is what
separates a contribution from a rediscovery.

**The pipeline is a loop, not a conveyor.** Evaluation that finds an unsupported claim
sends you back to writing; writing that cannot source a claim sends you back to the review
in stage 2; a rubric that keeps producing ties usually means the criteria were never sharp
enough, which is a stage 1 problem wearing a stage 5 costume. Going backwards is the system
working.

## Entering mid-pipeline

Most requests name a stage implicitly. Route on the artifact, not the vocabulary:

| The person says | Stage |
| --------------- | ----- |
| "Is this study any good?" / "does this support the conclusion?" | 1 |
| "Is this p-hacking?" / "their control group looks wrong" | 1 |
| "What's been published on X?" / "search PubMed" / "systematic review" | 2 |
| "Are these citations real?" / "build my reference list" / "what's the gap?" | 2 |
| "Give me hypotheses" / "narrow these 40 ideas down" | 3 |
| "Tighten my discussion" / "which checklist applies?" / "check my citations" | 4 |
| "Reviewer 2 says..." / "score these submissions" / "build a rubric" | 5 |

Two of these are close enough to confuse. "Check my citations" splits by intent: verifying
that a reference *exists and is real* is stage 2 (`verify_citations.py`); checking that
they are *formatted and used correctly in the manuscript* is stage 4
(`check_references.py`). And both stages ship a `citation_styles.md` — stage 2's covers
styles for the review output, stage 4's covers them for the manuscript.

When the request spans stages ("turn this idea into a paper"), start at the earliest stage
that is not already settled and say which stage you are entering and why. Do not silently
skip stage 1 — an unexamined question produces a well-written paper about the wrong thing,
which is the most expensive failure in this pipeline.

## Conventions across all five stages

**Separate what is observed from what is inferred.** Every stage has a version of this
distinction — evidence versus interpretation, idea versus assessment of the idea, result
versus claim, rating versus rationale. Collapsing the two is the most common failure in
scientific work and the one that survives longest, because the prose still reads fluently.

**Traceability is not paperwork.** A claim needs a source, a rating needs a rationale, a
figure needs the data behind it. Several stages ship scripts that check exactly this
(`audit_claims.py`, `check_traceability.py`, `check_references.py`) — run them rather than
eyeballing, because these are precisely the errors that reading cannot catch.

**Uncertainty is a finding, not a weakness.** State confidence and its basis. "We could
not determine X" is a legitimate and often important result; smoothing it into a confident
sentence is a research-integrity problem, not a style choice.

**Prefer the deterministic tool.** Where a stage offers both scripted and judgement-based
routes, run the script first — it produces the same answer twice and catches what reading
misses. Judgement then goes where it belongs: on what the output means.

**AI-generated content must be disclosed.** Stage 3's AI generator sends prompts to a
third-party API, and journal policies on AI assistance are covered in stage 4
(`references/writing/authorship_ai_confidentiality.md`). Check both before submitting
anything, and never send unpublished sensitive material to an external API without
deciding that is appropriate.

## Reference index

Every reference file, linked directly. Open the one you need; do not read a stage's whole
folder.

- **critical-thinking** — [common_biases](references/critical-thinking/common_biases.md) · [core_capabilities](references/critical-thinking/core_capabilities.md) · [evidence_hierarchy](references/critical-thinking/evidence_hierarchy.md) · [experimental_design](references/critical-thinking/experimental_design.md) · [logical_fallacies](references/critical-thinking/logical_fallacies.md) · [scientific_method](references/critical-thinking/scientific_method.md) · [statistical_pitfalls](references/critical-thinking/statistical_pitfalls.md)
- **literature-review** — [citation_styles](references/literature-review/citation_styles.md) · [core_workflow](references/literature-review/core_workflow.md) · [database_strategies](references/literature-review/database_strategies.md) · [example_workflow](references/literature-review/example_workflow.md) · [search_and_citation](references/literature-review/search_and_citation.md)
- **brainstorming** — [brainstorming_methods](references/brainstorming/brainstorming_methods.md) · [facilitation_workflows](references/brainstorming/facilitation_workflows.md) · [idea_evaluation](references/brainstorming/idea_evaluation.md) · [responsible_ai](references/brainstorming/responsible_ai.md) · [sources](references/brainstorming/sources.md)
- **writing** — [authorship_ai_confidentiality](references/writing/authorship_ai_confidentiality.md) · [citation_styles](references/writing/citation_styles.md) · [cli_reference](references/writing/cli_reference.md) · [evidence_workflow](references/writing/evidence_workflow.md) · [figures_tables](references/writing/figures_tables.md) · [imrad_structure](references/writing/imrad_structure.md) · [journal_policies](references/writing/journal_policies.md) · [professional_report_formatting](references/writing/professional_report_formatting.md) · [reporting_guidelines](references/writing/reporting_guidelines.md) · [research_integrity_open_science](references/writing/research_integrity_open_science.md) · [source_ledger](references/writing/source_ledger.md) · [writing_principles](references/writing/writing_principles.md)
- **evaluation** — [evaluation_framework](references/evaluation/evaluation_framework.md) · [local_tooling](references/evaluation/local_tooling.md) · [responsible_assessment](references/evaluation/responsible_assessment.md) · [security_validation](references/evaluation/security_validation.md) · [source_ledger](references/evaluation/source_ledger.md)

Templates to copy and fill:

- **literature-review** — [review_template.md](assets/literature-review/review_template.md)
- **writing** — [REPORT_FORMATTING_GUIDE.md](assets/writing/REPORT_FORMATTING_GUIDE.md) · [authorship_template.json](assets/writing/authorship_template.json) · [claim_evidence_template.csv](assets/writing/claim_evidence_template.csv) · [consistency_manifest_template.json](assets/writing/consistency_manifest_template.json) · [manuscript_manifest_template.json](assets/writing/manuscript_manifest_template.json) · [manuscript_scaffold.md](assets/writing/manuscript_scaffold.md) · [reporting_coverage_template.json](assets/writing/reporting_coverage_template.json) · [reporting_guidelines.json](assets/writing/reporting_guidelines.json) · [source_manifest_template.json](assets/writing/source_manifest_template.json)
- **evaluation** — [evaluation_template.json](assets/evaluation/evaluation_template.json) · [evidence_manifest_template.json](assets/evaluation/evidence_manifest_template.json) · [process_checklist_template.json](assets/evaluation/process_checklist_template.json) · [ratings_template.csv](assets/evaluation/ratings_template.csv) · [rubric_template.json](assets/evaluation/rubric_template.json)

Scripts are run, not read — one directory per stage under `scripts/`:
literature-review (multi-database search, citation verification, PDF generation),
brainstorming (session scaffold, register validation, scored matrix), writing (scaffold, lint, claim audit, reference and consistency
checks, authorship and manifest validation, guideline selection), evaluation (rubric
validation, scoring, agreement, traceability, weight sensitivity, report scaffold).

Each `scripts/<stage>/` directory contains its own `_common.py`; the three are different
modules and must stay beside their siblings — they are imported by the scripts around
them, not run directly.

Stage 1 ships no scripts by design — appraising a question is judgement, and a tool that
scored it would invite exactly the false precision the stage exists to prevent.

### What leaves the machine

Every script exposes `--help` and runs offline on the standard library, with one
exception: `scripts/literature-review/verify_citations.py`. Check this before passing
anything unpublished to a script.

| Script | Needs | Sends your data where |
| --- | --- | --- |
| `scripts/literature-review/verify_citations.py` | `requests` | DOI resolvers (Crossref, DataCite) — the identifiers you are checking |

**No script here needs an API key, and nothing sends your prose, your data, or your
figures to a third-party model.** A previous version shipped an image generator that
posted your diagram prompt to a hosted model; it was removed rather than documented,
because a research skill that quietly uploads descriptions of unpublished work is the
wrong default no matter how clearly the upload is disclosed.

Write diagrams as Mermaid inline in your reply — Claude Code and claude.ai both render a
` ```mermaid ` block, which covers flowcharts, study-flow, CONSORT and PRISMA diagrams,
pathways and architectures. For anything with axes, plot it in the library you already
analyse in. `references/writing/figures_tables.md` carries the publication standards.

## Attribution

Composed from five skills in K-Dense AI's `scientific-agent-skills` repository:
`scientific-critical-thinking`, `literature-review`, `scientific-brainstorming`,
`scientific-writing`, and `scholar-evaluation`. Guide bodies are preserved from the
originals with cross-reference paths updated for this layout.
