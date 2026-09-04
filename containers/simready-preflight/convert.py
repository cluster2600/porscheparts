#!/usr/bin/env python3
"""Adapt the NVIDIA skill checkout CLI to the packaged CAD converter CLI.

The CAD-to-SimReady skill invokes the upstream checkout interface::

    convert.py INPUT OUTPUT --report REPORT --quiet --log LOG

The PyPI runtime installed in this image exposes instead::

    usd-convert-cad -i INPUT -o OUTPUT

Keeping the translation here lets the preflight, conversion and validation
steps exercise the same immutable packaged runtime without a network checkout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


CONVERTER = Path("/opt/usd-convert-cad/bin/usd-convert-cad")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write(path: Path | None, content: str) -> None:
    """Publie un texte par remplacement atomique dans son répertoire."""

    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _temporary_output_path(output: Path) -> tuple[Path, Path]:
    """Crée un répertoire unique mais conserve le nom final du fichier USD.

    HOOPS dérive des noms de prim et leurs liaisons internes du basename de la
    sortie. Le basename doit donc rester identique à celui du fichier publié ;
    seul le répertoire temporaire peut être aléatoire.
    """

    directory = Path(
        tempfile.mkdtemp(
            dir=output.parent,
            prefix=f".{output.stem}.",
            suffix=".tmp",
        )
    )
    return directory / output.name, directory


def _validate_canonical_namespace(path: Path, output: Path) -> dict[str, object]:
    """Vérifie le namespace produit directement depuis le basename stable."""

    from pxr import Sdf, Tf, Usd

    stage = Usd.Stage.Open(str(path))
    if stage is None:
        raise RuntimeError("converted USD cannot be opened for namespace validation")
    default_prim = stage.GetDefaultPrim()
    if not default_prim or not default_prim.IsValid():
        raise RuntimeError("converted USD has no valid default prim")
    actual_path = default_prim.GetPath()
    canonical_name = Tf.MakeValidIdentifier(output.stem)
    if not canonical_name:
        raise RuntimeError("output stem cannot form a canonical USD identifier")
    canonical_path = Sdf.Path.absoluteRootPath.AppendChild(canonical_name)
    if actual_path != canonical_path:
        raise RuntimeError(
            f"default prim is {actual_path}, expected canonical path {canonical_path}"
        )
    root_paths = [prim.GetPath() for prim in stage.GetPseudoRoot().GetChildren()]
    if root_paths != [canonical_path]:
        raise RuntimeError(
            f"root prims are {root_paths}, expected only {canonical_path}"
        )
    if path.name != output.name:
        raise RuntimeError("temporary USD basename differs from final output basename")
    return {
        "canonical_namespace": True,
        "canonical_default_prim_path": str(canonical_path),
        "pre_normalization_default_prim_path": str(actual_path),
        "flattened_for_namespace_stability": False,
        "stable_temporary_output_basename": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compatibility adapter for the packaged NVIDIA CAD converter."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--log", type=Path)
    parser.add_argument("--up-axis", choices=("y", "z"), default="y")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    source = args.input.resolve()
    output = args.output.resolve()
    errors: list[str] = []
    if not source.is_file():
        errors.append(f"source asset does not exist: {source}")
    if source.suffix.lower() not in {".step", ".stp"}:
        errors.append(f"unsupported source suffix: {source.suffix.lower() or 'unknown'}")
    if output.suffix.lower() not in {".usd", ".usda", ".usdc"}:
        errors.append(f"unsupported output suffix: {output.suffix.lower() or 'unknown'}")
    if not CONVERTER.is_file():
        errors.append(f"packaged converter is missing: {CONVERTER}")

    source_sha256_before = _sha256(source) if source.is_file() else None
    temporary_output: Path | None = None
    temporary_directory: Path | None = None
    command_output = output
    if not errors:
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary_output, temporary_directory = _temporary_output_path(output)
        command_output = temporary_output
    command = [
        str(CONVERTER),
        "-i",
        str(source),
        "-o",
        str(command_output),
        "--instancing-style",
        "reference",
        "--composition-style",
        "none",
        "--filter-style",
        "deactivate",
        "--up-axis",
        args.up_axis,
        "--creator",
        "3dprinting993-simready-workflow",
    ]
    stdout = ""
    stderr = ""
    returncode = 2 if errors else 0
    source_sha256_after = source_sha256_before
    output_sha256 = None
    atomic_output_commit = False
    namespace = {
        "canonical_namespace": False,
        "canonical_default_prim_path": None,
        "pre_normalization_default_prim_path": None,
        "flattened_for_namespace_stability": False,
        "stable_temporary_output_basename": False,
    }
    try:
        if not errors:
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
            stdout = completed.stdout
            stderr = completed.stderr
            returncode = completed.returncode
            if completed.returncode != 0:
                errors.append(
                    stderr.strip()
                    or stdout.strip()
                    or f"usd-convert-cad exited with {completed.returncode}"
                )
            elif temporary_output is None or not temporary_output.is_file():
                errors.append(f"converter did not produce expected temporary output: {output}")
                returncode = 2
            else:
                source_sha256_after = _sha256(source)
                if source_sha256_after != source_sha256_before:
                    errors.append("source asset changed during conversion")
                    returncode = 2
                else:
                    try:
                        namespace = _validate_canonical_namespace(temporary_output, output)
                    except Exception as exc:
                        errors.append(f"USD namespace validation failed: {exc}")
                        returncode = 2
                    else:
                        os.replace(temporary_output, output)
                        temporary_output = None
                        output_sha256 = _sha256(output)
                        atomic_output_commit = True
    finally:
        if temporary_output is not None:
            temporary_output.unlink(missing_ok=True)
        if temporary_directory is not None:
            shutil.rmtree(temporary_directory)

    log = stdout + stderr
    _write(args.log, log if log.endswith("\n") or not log else log + "\n")
    report = {
        "schema_version": "1.0",
        "status": "passed" if not errors else "failed",
        "source_asset": str(source),
        "source_sha256": source_sha256_after,
        "source_stable_during_conversion": (
            source_sha256_before is not None
            and source_sha256_before == source_sha256_after
        ),
        "output_usd": str(output),
        "output_sha256": output_sha256,
        "atomic_output_commit": atomic_output_commit,
        "requested_up_axis": args.up_axis.upper(),
        **namespace,
        "converter": str(CONVERTER),
        "command": command,
        "returncode": returncode,
        "errors": errors,
    }
    report_text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    _write(args.report, report_text)
    if not args.quiet:
        if log:
            print(log, end="" if log.endswith("\n") else "\n")
        print(report_text, end="")
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
