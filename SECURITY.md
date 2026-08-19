# Security policy

## Supported versions

The latest tagged release is the supported one. Fixes land on `main` and ship in the
next tag; there are no long-lived maintenance branches.

## Reporting a vulnerability

Report privately through GitHub's
[private vulnerability reporting](https://github.com/AlveeeRahman/research-hound/security/advisories/new)
rather than a public issue, and give it a few days for a first response.

Useful things to include: what an attacker gets, the smallest input that shows it, and
the Python version you saw it on.

## What this skill does with your data

research-hound is a set of local CLIs plus instructions for Claude. Exactly one script
opens a network connection:

| Script | Reaches | What is sent |
| --- | --- | --- |
| `scripts/literature-review/verify_citations.py` | `doi.org`, `api.crossref.org` | The DOIs and citation strings you ask it to verify. |

Everything else in `scripts/` runs offline against the standard library. No script reads
or requires an API key. The same surface is recorded in
`.github/repository-metadata.yml`, so a change to what leaves the machine has a single
place to be written down.

**Nothing here sends your prose, your data or your figures to a hosted model.** An
earlier version bundled an image generator that posted the diagram prompt to a
third-party API and needed a key for it. It was removed rather than documented more
loudly: a research skill that uploads descriptions of unpublished work is the wrong
default however clearly the upload is disclosed. Write diagrams as Mermaid inline
instead — it renders in Claude Code and claude.ai and never leaves the machine.

## Scope

In scope: path traversal, arbitrary code execution, or credential disclosure from
running the bundled scripts on untrusted input.

Out of scope: the accuracy of Claude's own output, third-party API behaviour, and
anything requiring an attacker who already has write access to your machine.
