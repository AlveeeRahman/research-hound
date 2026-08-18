"""Shared, dependency-free file-safety primitives for research-hound's stage harnesses.

Three stages (brainstorming, evaluation, writing) each reimplemented "read a bounded
JSON file without following a symlink" independently. Two of them checked
`path.is_symlink()` / `path.is_file()` as separate calls before opening the file — a
TOCTOU (time-of-check-to-time-of-use) gap where the target can be swapped for a
symlink between the check and the read. The third (brainstorming) opened with
`O_NOFOLLOW` and inspected the *open file descriptor* via `os.fstat`, which is
race-free. This module makes that the one implementation every stage routes through.

What lives here: the file-open primitive, JSON parsing with pluggable duplicate-key
rejection, atomic JSON writing, and `rounded()`. What does NOT live here: each stage's
own structure-bounds scan (evaluation's private-field-key rejection and node/depth
limits, writing's own node/depth limits) — those encode stage-specific rules on top of
a safely-opened file, not file-safety itself, and stay in each stage's `_common.py`.

Callers should catch `SafeIOError` and re-raise their own stage's exception type so
existing `except CliError` / `except _common.ValidationError` / `except InputError`
call sites in the runnable scripts need no changes.
"""

from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any, Callable


class SafeIOError(ValueError):
    """A deterministic, user-facing file-safety failure.

    Never interpolate a raw supplied *value* into this message — only paths, sizes,
    and counts. Evaluation processes potentially sensitive scholarly-review data and
    depends on error messages never leaking input content; that guarantee has to hold
    here too, since evaluation's `_common.py` translates this into its own error type.
    """


def open_bounded(
    raw_path: str | Path,
    *,
    suffixes: set[str],
    max_bytes: int,
    encoding: str = "utf-8",
    label: str | None = None,
) -> tuple[Path, str]:
    """Read a bounded regular file without following a final symlink.

    Race-free: opens with `O_NOFOLLOW` and inspects the open file descriptor via
    `os.fstat`, so nothing can be swapped between the check and the read.

    `label` (e.g. "JSON input") is folded into error messages when a caller supplies
    one, matching the wording each stage's scripts already show their users.
    """
    tag = label or "path"
    path = Path(raw_path).expanduser()
    if path.name in {"", ".", ".."}:
        raise SafeIOError(f"{tag} must name a file")
    if path.suffix.lower() not in suffixes:
        expected = ", ".join(sorted(suffixes))
        raise SafeIOError(f"{tag} must use one of these suffixes: {expected}")
    if path.is_symlink():
        raise SafeIOError(f"refusing to read {tag} through a symlink")

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise SafeIOError(f"cannot open {tag} as a regular file: {path}") from exc

    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise SafeIOError(f"{tag} is not a regular file: {path}")
        if metadata.st_size > max_bytes:
            raise SafeIOError(
                f"{tag} is {metadata.st_size} bytes; limit is {max_bytes}"
            )
        with os.fdopen(descriptor, "r", encoding=encoding, newline="") as handle:
            descriptor = -1
            return path, handle.read()
    except UnicodeDecodeError as exc:
        raise SafeIOError(f"{tag} is not valid {encoding} text") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SafeIOError("JSON contains a duplicate object key")
        result[key] = value
    return result


def _reject_nonfinite_constant(constant: str) -> None:
    raise SafeIOError(f"non-finite JSON constant is not allowed: {constant}")


def load_json(
    raw_path: str | Path,
    *,
    max_bytes: int,
    suffixes: set[str] = frozenset({".json"}),
    reject_duplicate_keys: bool = True,
    object_pairs_hook: Callable[[list[tuple[str, Any]]], Any] | None = None,
    label: str | None = None,
) -> tuple[Path, Any]:
    """Read strict, bounded JSON: race-free open, non-finite and (optionally)
    duplicate-key rejection at parse time. Does not walk the parsed structure for
    depth/size/domain rules — callers layer their own bounds check on the result.
    """
    path, text = open_bounded(
        raw_path, suffixes=set(suffixes), max_bytes=max_bytes, label=label
    )
    hook = object_pairs_hook
    if hook is None and reject_duplicate_keys:
        hook = _reject_duplicate_keys
    try:
        data = json.loads(
            text,
            object_pairs_hook=hook,
            parse_constant=_reject_nonfinite_constant,
        )
    except (json.JSONDecodeError, RecursionError) as exc:
        raise SafeIOError(f"invalid JSON in {path}: {exc}") from exc
    return path, data


def _safe_output_target(raw_path: str | Path, suffix: str) -> Path:
    """Resolve a user-selected output path in an existing directory."""
    requested = Path(raw_path).expanduser()
    if requested.name in {"", ".", ".."}:
        raise SafeIOError("output must name a file")
    if requested.suffix.lower() != suffix:
        raise SafeIOError(f"output filename must end in {suffix}")
    if requested.is_symlink():
        raise SafeIOError("refusing to write through an output symlink")
    try:
        parent = requested.parent.resolve(strict=True)
    except FileNotFoundError as exc:
        raise SafeIOError("output parent directory does not exist") from exc
    if not parent.is_dir():
        raise SafeIOError("output parent is not a directory")
    target = parent / requested.name
    if target.is_symlink():
        raise SafeIOError("refusing to replace an output symlink")
    if target.exists() and not target.is_file():
        raise SafeIOError("output exists and is not a regular file")
    return target


def write_json(
    raw_path: str | Path,
    payload: Any,
    *,
    force: bool = False,
) -> Path:
    """Write deterministic JSON with private permissions and safe overwrite.

    Without `force`: exclusive-create (`O_CREAT | O_EXCL | O_NOFOLLOW`), fails if the
    target already exists. With `force`: atomic replace via a temp file in the same
    directory plus `os.replace`, so a reader never observes a partially-written file.
    """
    target = _safe_output_target(raw_path, ".json")
    try:
        text = (
            json.dumps(
                payload,
                allow_nan=False,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
    except (TypeError, ValueError, RecursionError) as exc:
        raise SafeIOError(f"payload cannot be serialized as strict JSON: {exc}") from exc

    if not force:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = -1
        created = False
        try:
            descriptor = os.open(target, flags, 0o600)
            created = True
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                descriptor = -1
                handle.write(text)
        except FileExistsError as exc:
            raise SafeIOError(
                f"output already exists: {target}; pass --force to replace it"
            ) from exc
        except OSError as exc:
            if created:
                target.unlink(missing_ok=True)
            raise SafeIOError(f"could not write output: {target}") from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        return target

    if target.exists() and not target.is_file():
        raise SafeIOError("output exists and is not a regular file")

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=target.parent,
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            descriptor = -1
            handle.write(text)
        if target.is_symlink():
            raise SafeIOError("refusing to replace an output symlink")
        os.replace(temporary, target)
    except OSError as exc:
        raise SafeIOError(f"could not replace output: {target}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)
    return target


def rounded(value: float | None) -> float | None:
    """Return stable display precision without changing any documented formula."""
    if value is None:
        return None
    return round(value, 6)
