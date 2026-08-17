# Research Hound — the extended research skill for Claude

[![CI](https://github.com/AlveeeRahman/research-hound/actions/workflows/ci.yml/badge.svg)](https://github.com/AlveeeRahman/research-hound/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/AlveeeRahman/research-hound/blob/main/LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)

**research-hound** is an [Agent Skill](https://code.claude.com/docs/en/skills) for Claude
Code that turns Claude into a methodical research partner: a six-stage scientific
workflow — critical thinking, literature review, brainstorming, schematics, writing,
evaluation — backed by **26 runnable scripts** that verify what a chat model would
otherwise just assert. It hunts down the weak citation, the untraceable claim, and the
statistical pitfall before a reviewer does.

## Get it on the scent

```bash
# All your projects (personal skill):
git clone https://github.com/AlveeeRahman/research-hound.git ~/.claude/skills/research-hound

# Or one project only (shareable with your team through git):
git clone https://github.com/AlveeeRahman/research-hound.git .claude/skills/research-hound
```

Python 3.9+; standard library only, except `requests` in the two network scripts
(citation verification and AI schematic generation). Then ask Claude in your own words:

> *"Search the literature on X and verify every citation."*
> *"Audit the claims in my methods section against my sources."*
> *"Is this analysis p-hacked?"*
> *"Score this manuscript against the rubric and report inter-rater agreement."*

## Audited, not just published

Genuine output of [skill-vision](https://github.com/AlveeeRahman/skill-vision) (the QA
skill for Claude skills) inspecting this repo:

```text
=== research-hound  [router] · ~2.7k tokens (description 233 every session + body 2.4k on trigger) ===
  CONFORMANT  (0 errors, 0 warnings, 25 notes)
```

In skill-vision's field audit of a 20-skill corpus, this skill took the **top quality
score of the entire corpus**. CI re-runs the same spec validation on every push.

## The six stages

| Stage | Guide | Deterministic tooling |
|---|---|---|
| Critical thinking | `guides/critical-thinking.md` | Evidence hierarchy, logical fallacies, statistical pitfalls, bias catalogs (`references/critical-thinking/`) |
| Literature review | `guides/literature-review.md` | `search_databases.py` (PubMed / arXiv / Semantic Scholar), `verify_citations.py`, `generate_pdf.py` |
| Brainstorming | `guides/brainstorming.md` | Ideation methods, scored triage, facilitation workflows |
| Schematics | `guides/schematics.md` | Diagram generation and iterative refinement scripts |
| Writing | `guides/writing.md` | `scaffold_manuscript.py` (IMRaD), `lint_manuscript.py`, `audit_claims.py`, `check_references.py`, `check_consistency.py`, `select_reporting_guidelines.py` (CONSORT / PRISMA / STROBE), `validate_authorship.py` |
| Evaluation | `guides/evaluation.md` | `validate_rubric.py`, `calculate_scores.py`, `summarize_agreement.py` (inter-rater), `weight_sensitivity.py`, `check_traceability.py` |

## How research-hound differs — the validation

### vs. Claude's built-in research

Claude's native web search and Deep Research are **retrieval and synthesis**: they find
sources and write summaries, in one pass, inside the chat. research-hound is a
**methodology harness** on top of the model:

- **Verification, not just citation.** `verify_citations.py` checks that references
  actually resolve and `audit_claims.py` traces each manuscript claim to its evidence —
  the two failure modes chat-only research cannot catch in itself.
- **Staged discipline.** Question interrogation before searching; searching before
  synthesis; a source ledger throughout; rubric scoring with inter-rater agreement at the
  end. Built-in research has no stages to hold it accountable.
- **Deterministic and reproducible.** Every check is a plain CLI your CI can re-run.
  A conversation cannot be re-run; `pytest`-style verification can.
- **Scientific-writing integrity rules.** Formatting guidance keeps equations, symbols,
  units, subscripts, and superscripts intact through drafting and format conversion, and
  the skill deliberately ships *no* boilerplate LaTeX template — templates that fabricate
  polish were removed in favor of integrity rules (see
  `references/writing/professional_report_formatting.md`).
- **Research-integrity guardrails.** Authorship and AI-confidentiality policy,
  responsible-AI brainstorming constraints, and reporting-guideline selection
  (CONSORT / PRISMA / STROBE) are first-class steps, not afterthoughts.

### vs. other research skills on GitHub

The field (`academic-research-skills-claude`, `DResearch-Skill`,
`paper-research-skill_claude`, and kin) is mostly **prompt-only guides or single-phase
deep-research loops** — instructions for the model, with nothing executable behind them.
research-hound's difference is substance: 46 reference documents organized by stage plus
26 scripts that make the claims checkable. Where a lighter skill fits better — a
one-shot news digest, a single-domain financial screen — use the lighter skill; this one
is for work that has to survive review.

## claude.ai / Desktop upload caveat

The frontmatter description is ~930 characters, tuned for Claude Code triggering. The
claude.ai web uploader caps descriptions at **200 characters** — shorten it in your zip
copy before uploading, and exclude `.git`:

```bash
zip -r research-hound.zip research-hound -x "research-hound/.git/*" "research-hound/.git"
```

## What's in the box

- **`SKILL.md`** — the six-stage routing instructions Claude loads (~2.7k tokens total context cost).
- **`guides/`** — one guide per stage.
- **`references/`** — 40+ stage-organized reference documents (evidence hierarchies, database strategies, citation styles, IMRaD structure, evaluation frameworks…).
- **`scripts/`** — 26 CLIs across five stages.
- **`assets/`** — supporting fixtures.

## License

[MIT](https://github.com/AlveeeRahman/research-hound/blob/main/LICENSE) — copyright (c) 2026 MrPirate.

*May your citations always resolve on the first fetch.*
