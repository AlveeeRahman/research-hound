---
name: research-hound
description: Six-stage scientific research workflow - critical thinking (interrogate a question, appraise evidence, spot bias and statistical misuse), literature review (multi-database search across PubMed/arXiv/Semantic Scholar, synthesis, citation verification), brainstorming (ideation with scored triage), schematics (diagrams), writing (IMRaD drafting, claim-evidence tracing, manuscript linting, CONSORT/PRISMA/STROBE checklists), and evaluation (rubric scoring, inter-rater agreement, traceability). Use for academic or scientific work - framing a research question, searching or synthesising literature, systematic reviews and meta-analyses, critiquing a study design, generating hypotheses, drafting a paper, thesis or grant, making figures, checking citations, peer-reviewing, or scoring against a rubric - including when only an artifact is named (my methods section, reviewer 2 says, is this p-hacking, what has been published on X).
license: See upstream K-Dense AI scientific-agent-skills
allowed-tools: Read Write Edit Bash
compatibility: Python 3.10+ for the bundled scripts. All run offline on the standard library except two, which need the requests package (uv pip install requests) - scripts/literature-review/verify_citations.py, which queries DOI resolvers and imports requests unguarded, and scripts/schematics/generate_schematic_ai.py, which also needs OPENROUTER_API_KEY and sends prompts to a third-party API. scripts/schematics/generate_schematic.py is the offline diagram alternative.
metadata:
  version: "1.1"
  composed-from: "scientific-critical-thinking, literature-review, scientific-brainstorming, scientific-schematics, scientific-writing, scholar-evaluation (K-Dense AI)"
---

# Research

Six stages of scientific work in one skill. Read only the guide for the stage you are in —
the guides are large, and loading all six crowds out the work itself.

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
1. CRITICAL      2. LITERATURE     3. BRAIN-        4. SCHEM-      5. WRITING     6. EVAL-
   THINKING         REVIEW            STORMING         ATICS                        UATION
   Is the           What is           What are the     What does      Say it        Is it any
   question         already           candidates,      it look        precisely,    good? Score
   sound?           known?            which survive?   like?          traceably.    it honestly.
      │                │                   │              │              │             │
      └────────────────┴───────────────────┴──────────────┴──────────────┴─────────────┘
                     Findings at any stage can send you back upstream.
```

| Stage | Read | You are here when |
| ----- | ---- | ----------------- |
| **1. Critical thinking** | `guides/critical-thinking.md` | Framing a question, appraising evidence quality, critiquing a design, checking for bias, fallacy, or statistical misuse |
| **2. Literature review** | `guides/literature-review.md` | Searching PubMed/arXiv/Semantic Scholar, systematic review or meta-analysis, synthesising prior work, verifying citations, establishing the gap |
| **3. Brainstorming** | `guides/brainstorming.md` | Generating hypotheses or study designs, running structured ideation, triaging many ideas down to a few |
| **4. Schematics** | `guides/schematics.md` | Drawing a mechanism, flowchart, pipeline, or study-flow figure; refining a diagram |
| **5. Writing** | `guides/writing.md` | Drafting or revising IMRaD sections, tracing claims to evidence, citations, reporting checklists, authorship |
| **6. Evaluation** | `guides/evaluation.md` | Peer review, rubric scoring, inter-rater agreement, grant or submission assessment, traceability audits |

**Why literature review sits at stage 2.** Brainstorming before searching the literature
generates ideas that are already published, and the cost of finding that out is measured in
months. The review is also what converts a broad question into a specific gap, which is the
input stage 3 actually needs. In academia this ordering is not a preference — it is what
separates a contribution from a rediscovery.

**The pipeline is a loop, not a conveyor.** Evaluation that finds an unsupported claim
sends you back to writing; writing that cannot source a claim sends you back to the review
in stage 2; a rubric that keeps producing ties usually means the criteria were never sharp
enough, which is a stage 1 problem wearing a stage 6 costume. Going backwards is the system
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
| "Draw the mechanism" / "make a study-flow diagram" | 4 |
| "Tighten my discussion" / "which checklist applies?" / "check my citations" | 5 |
| "Reviewer 2 says..." / "score these submissions" / "build a rubric" | 6 |

Two of these are close enough to confuse. "Check my citations" splits by intent: verifying
that a reference *exists and is real* is stage 2 (`verify_citations.py`); checking that
they are *formatted and used correctly in the manuscript* is stage 5
(`check_references.py`). And both stages ship a `citation_styles.md` — stage 2's covers
styles for the review output, stage 5's covers them for the manuscript.

When the request spans stages ("turn this idea into a paper"), start at the earliest stage
that is not already settled and say which stage you are entering and why. Do not silently
skip stage 1 — an unexamined question produces a well-written paper about the wrong thing,
which is the most expensive failure in this pipeline.

## Conventions across all six stages

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

## What's bundled

```
research/
├── guides/           # one per stage — start here
├── references/
│   ├── critical-thinking/  # scientific method, evidence hierarchy, experimental design,
│   │                       # logical fallacies, common biases, statistical pitfalls
│   ├── literature-review/  # core workflow, database strategies, search & citation,
│   │                       # citation styles, worked example
│   ├── brainstorming/      # methods, facilitation workflows, idea evaluation, responsible AI
│   ├── schematics/         # best practices, iterative refinement
│   ├── writing/            # IMRaD, citation styles, figures/tables, reporting guidelines,
│   │                       # journal policies, integrity/open science, source ledger, CLI
│   └── evaluation/         # evaluation framework, responsible assessment, security validation
├── scripts/
│   ├── literature-review/  # multi-database search, citation verification, PDF generation
│   ├── brainstorming/      # session scaffold, register validation, scored matrix
│   ├── schematics/         # deterministic + AI diagram generation
│   ├── writing/            # scaffold, lint, claim audit, reference/consistency checks,
│   │                       # authorship + manifest validation, guideline selection
│   └── evaluation/         # rubric validation, scoring, agreement, traceability,
│                           # weight sensitivity, report scaffold
└── assets/
    ├── literature-review/  # review document template
    ├── writing/            # manuscript scaffold + manifest/claim/authorship templates
    └── evaluation/         # rubric, ratings, evidence manifest, checklist templates
```

Each `scripts/<stage>/` directory contains its own `_common.py`; the three are different
modules and must stay beside their siblings — they are imported by the scripts around
them, not run directly.

Every script exposes `--help` and runs offline on the standard library, with one
exception: `scripts/schematics/generate_schematic_ai.py` needs `requests`
(`uv pip install requests`) and an `OPENROUTER_API_KEY`, and transmits your prompt to a
third-party service. It exits with an install hint rather than a traceback if `requests`
is absent. `scripts/schematics/generate_schematic.py` is the offline alternative.

Stage 1 ships no scripts by design — appraising a question is judgement, and a tool that
scored it would invite exactly the false precision the stage exists to prevent.

## Attribution

Composed from six skills in K-Dense AI's `scientific-agent-skills` repository:
`scientific-critical-thinking`, `literature-review`, `scientific-brainstorming`,
`scientific-schematics`, `scientific-writing`, and `scholar-evaluation`. Guide bodies are
preserved from the originals with cross-reference paths updated for this layout.

`literature-review` shipped its own copies of `generate_schematic.py` and
`generate_schematic_ai.py` that are byte-identical to the schematics stage's. They are not
duplicated here — the literature-review guide points at `scripts/schematics/` instead.
