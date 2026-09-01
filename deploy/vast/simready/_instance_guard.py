#!/usr/bin/env python3
"""Valide les métadonnées non secrètes d'une instance Vast SimReady."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


IMAGE_RE = re.compile(r"[a-z0-9][a-z0-9._/-]*@sha256:[0-9a-f]{64}")
HOST_RE = re.compile(r"(?:[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?|(?:[0-9]{1,3}\.){3}[0-9]{1,3})")


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def decimal(value: object, label: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{label} invalide") from exc
    if not result.is_finite() or result <= 0:
        raise ValueError(f"{label} invalide")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wrapper", required=True)
    parser.add_argument("--instance-id", type=int, required=True)
    parser.add_argument("--expected-image", required=True)
    parser.add_argument("--expected-label", default="3dprinting993-simready-local-ai")
    parser.add_argument("--max-actual-dph", default=os.environ.get("MAX_ACTUAL_DPH", "2.50"))
    parser.add_argument("--allowed-status", action="append", default=[])
    parser.add_argument("--require-ssh", action="store_true")
    parser.add_argument("--skip-cost-cap", action="store_true")
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    instance: dict = {}
    allowed_statuses = args.allowed_status or ["running"]
    if args.instance_id <= 0:
        errors.append("instance_id doit être positif")
    if not IMAGE_RE.fullmatch(args.expected_image):
        errors.append("l'image attendue doit être épinglée par un digest sha256 complet")
    try:
        max_dph = decimal(args.max_actual_dph, "MAX_ACTUAL_DPH")
    except ValueError as exc:
        errors.append(str(exc))
        max_dph = Decimal("0")

    if not errors:
        try:
            completed = subprocess.run(
                [args.wrapper, "show", str(args.instance_id)],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            errors.append("le wrapper OpenBao Vast.ai est indisponible")
        else:
            if completed.returncode != 0:
                errors.append("le wrapper OpenBao Vast.ai a refusé la lecture de l'instance")
            elif len(completed.stdout.encode("utf-8")) > 131072:
                errors.append("la réponse du wrapper est trop volumineuse")
            else:
                try:
                    candidate = json.loads(completed.stdout)
                except json.JSONDecodeError:
                    errors.append("le wrapper a renvoyé un JSON invalide")
                else:
                    if isinstance(candidate, dict):
                        instance = candidate
                    else:
                        errors.append("le wrapper a renvoyé une structure invalide")

    if instance:
        if instance.get("id") != args.instance_id:
            errors.append("identifiant d'instance différent")
        if instance.get("label") != args.expected_label:
            errors.append("label d'instance différent")
        if instance.get("image") != args.expected_image:
            errors.append("digest d'image différent")
        if instance.get("status") not in allowed_statuses:
            errors.append("état d'instance non autorisé")
        if instance.get("num_gpus") != 1:
            errors.append("le contrat doit exposer exactement un GPU")
        try:
            actual_dph = decimal(instance.get("dph_total"), "dph_total contractuel")
        except ValueError as exc:
            errors.append(str(exc))
        else:
            if not args.skip_cost_cap and max_dph and actual_dph > max_dph:
                errors.append("dph_total contractuel supérieur au plafond")
        if args.require_ssh:
            host = instance.get("ssh_host")
            if not isinstance(host, str) or not HOST_RE.fullmatch(host):
                errors.append("hôte SSH invalide")
            try:
                port = int(instance.get("ssh_port"))
            except (TypeError, ValueError):
                errors.append("port SSH invalide")
            else:
                if not 1 <= port <= 65535:
                    errors.append("port SSH invalide")

    safe_instance = {
        key: instance.get(key)
        for key in ("id", "label", "status", "gpu", "num_gpus", "dph_total", "ssh_host", "ssh_port", "image")
    }
    payload = {
        "schema_version": "1.0.0",
        "status": "passed" if not errors else "blocked",
        "passed": not errors,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "criteria": {
            "expected_image": args.expected_image,
            "expected_label": args.expected_label,
            "max_actual_dph": str(max_dph),
            "allowed_statuses": allowed_statuses,
            "required_gpu_count": 1,
            "ssh_required": args.require_ssh,
            "cost_basis": "instance show dph_total après création, disque contractuel inclus",
            "cost_cap_enforced": not args.skip_cost_cap,
        },
        "instance": safe_instance,
        "errors": errors,
    }
    atomic_json(args.report.resolve(), payload)
    if errors:
        for error in errors:
            print(f"instance-guard: {error}", file=os.sys.stderr)
        return 1
    print(args.report.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
