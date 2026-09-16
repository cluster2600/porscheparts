#!/usr/bin/env python3
"""Ecrire la paire de manifestes engine-twin-v1, a lancer sur le Mac juste avant la location.

created_epoch est l'instant d'execution : l'echeance court des la generation.
Les deux roles partagent le meme suffixe hexadecimal ; chaque fichier est cree
en 0600, jamais ecrase. Aucun appel reseau, aucune location.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import time

REPO = Path(__file__).resolve().parents[3]
GUARD = Path(__file__).resolve().with_name("deadline_guard.py")
MODEL = "Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8"
REVISION = "dcaee4d4dfc5ee71ad501f01f530e5652438fde0"
IMAGES = {
    "llm": "vllm/vllm-openai@sha256:7a0f0fdd2771464b6976625c2b2d5dd46f566aa00fbc53eceab86ef50883da90",
    "compute": "ghcr.io/cluster2600/3dprinting993-simready-local-ai@sha256:5a69a6805a275ef708e264600cb933663159a2846b069eafe0459c28e5f69699",
}
DOWNLOAD_GB = {"llm": 45, "compute": 40}
UPLOAD_GB = {"llm": 1, "compute": 15}
VARIANTS = {
    "qwen38-flash-next": {
        "image": "ghcr.io/cluster2600/qwen38-flash-next-vast@sha256:6b3b1790dd3140c27a5b5f85181dccef06c8d96c02f3003bb3c9b267b8758e34",
        "model": "orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
        "revision": "c1209bda15a6bbc4c68b585e93d40c0d85f50306",
        # Mesure du 2026-09-15 : image 8 634 500 849 + poids 183 535 695 549 octets, + 1 Go de reserve.
        "download_gb": 200,
        "qualification": "llm-flashnext-qualification.json",
    },
}


def write_private(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def build(directory: Path, hours: float, budget: float, suffix: str, now: int,
          roles=("llm", "compute"), attempt: int = 1, variant: str | None = None) -> dict:
    manifests = {}
    for role in roles:
        other = "compute" if role == "llm" else "llm"
        job = f"engine-twin-{role}-20260915-{suffix[:8]}" + (f"-a{attempt}" if attempt > 1 else "")
        v = VARIANTS[variant] if (variant and role == "llm") else None
        qualification = directory / (v["qualification"] if v else f"{role}-qualification.json")
        manifests[role] = {
            "schema_version": "1.0.0", "profile": "engine-twin-v1", "role": role, "job_id": job,
            "attempt_label": f"3dprinting993-engine-twin-{role}-{suffix}",
            "sibling_label": f"3dprinting993-engine-twin-{other}-{suffix}",
            "image_ref": v["image"] if v else IMAGES[role], "model": v["model"] if v else MODEL,
            "model_revision": v["revision"] if v else REVISION,
            "created_epoch": now, "deadline_epoch": now + int(hours * 3600), "budget_usd": budget,
            "download_budget_gb": v["download_gb"] if v else DOWNLOAD_GB[role], "upload_budget_gb": UPLOAD_GB[role],
            "qualification_path": str(qualification),
            "qualification_sha256": hashlib.sha256(qualification.read_bytes()).hexdigest(),
            "guard_path": str(GUARD), "guard_sha256": hashlib.sha256(GUARD.read_bytes()).hexdigest(),
            "guard_ready_path": str(directory / f"{job}.guard-ready.json"),
        }
        if v:
            manifests[role]["variant"] = variant
    return manifests


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("directory", type=Path, help="dossier prive absolu contenant les deux qualifications")
    ap.add_argument("--hours", type=float, default=6.0)
    ap.add_argument("--budget-usd", type=float, default=30.0, help="par role")
    ap.add_argument("--wrapper", default=str(Path.home() / ".local/bin/openbao-vastai"))
    ap.add_argument("--suffix", help="rejoindre une session existante : suffixe hexadecimal de 20 caracteres de la soeur en marche")
    ap.add_argument("--role", choices=["llm", "compute"], help="avec --suffix : un seul role")
    ap.add_argument("--attempt", type=int, default=1, help="nouvelle tentative apres un reçu consomme (job_id distinct)")
    ap.add_argument("--variant", choices=sorted(VARIANTS), help="variante du role llm (ex. qwen38-flash-next)")
    args = ap.parse_args()
    import re
    if (args.suffix is None) != (args.role is None):
        sys.exit("--suffix et --role vont ensemble")
    if args.suffix is not None and not re.fullmatch(r"[0-9a-f]{20}", args.suffix):
        sys.exit("suffixe hexadecimal de 20 caracteres requis")
    if not 1 <= args.attempt <= 9:
        sys.exit("attempt dans [1, 9]")
    directory = args.directory
    if not directory.is_absolute() or directory.is_symlink() or not directory.is_dir():
        sys.exit("dossier prive absolu, existant et sans lien symbolique requis")
    if directory.stat().st_mode & 0o077:
        sys.exit("le dossier doit etre en 0700")
    if not 600 / 3600 <= args.hours <= 6 or not 1 < args.budget_usd <= 30:
        sys.exit("hours dans [1/6, 6] et budget par role dans ]1, 30]")
    roles = (args.role,) if args.role else ("llm", "compute")
    manifests = build(directory, args.hours, args.budget_usd, args.suffix or secrets.token_hex(10), int(time.time()),
                      roles, args.attempt, args.variant)

    # Relecture par le chargeur du wrapper installe : meme contrat que le lancement.
    from importlib.machinery import SourceFileLoader
    import importlib.util
    loader = SourceFileLoader("openbao_vastai_installed", args.wrapper)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    wrapper = importlib.util.module_from_spec(spec)
    loader.exec_module(wrapper)
    paths = {}
    for role, manifest in manifests.items():
        path = directory / f"{manifest['job_id']}.json"
        write_private(path, json.dumps(manifest, indent=2, sort_keys=True).encode() + b"\n")
        wrapper.engine_twin_load_manifest(path)
        paths[role] = str(path)
    print(json.dumps({"manifests": paths, "deadline_epoch": next(iter(manifests.values()))["deadline_epoch"],
                      "attempt_labels": {r: m["attempt_label"] for r, m in manifests.items()}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
