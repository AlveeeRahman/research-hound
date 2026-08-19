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

research-hound is a set of local CLIs plus instructions for Claude. Most of it never
leaves your machine. Three scripts do open network connections, and it is worth knowing
exactly which:

| Script | Reaches | What is sent |
| --- | --- | --- |
| `scripts/literature-review/verify_citations.py` | `doi.org`, `api.crossref.org` | The DOIs and citation strings you ask it to verify. |
| `scripts/schematics/generate_schematic_ai.py` | `openrouter.ai` | Your diagram prompt, plus your `OPENROUTER_API_KEY`. |
| `scripts/schematics/generate_schematic.py` | `openrouter.ai` | A wrapper around the script above — same traffic, not an offline alternative. |

Everything else in `scripts/` runs offline against the standard library. That claim is
enforced, not asserted: `.github/repository-metadata.yml` declares the network surfaces
and `.github/seo/seo.py verify` fails CI if a script starts making calls that the
manifest does not list.

If you want a diagram with no third-party call, write Mermaid inline instead of using
the schematics scripts.

## Handling `OPENROUTER_API_KEY`

Pass it through the environment. Do not paste it into a prompt, commit it, or place it
in a file inside a repository Claude can read — a key in the working tree is a key in
the context window.

## Scope

In scope: path traversal, arbitrary code execution, or credential disclosure from
running the bundled scripts on untrusted input.

Out of scope: the accuracy of Claude's own output, third-party API behaviour, and
anything requiring an attacker who already has write access to your machine.
