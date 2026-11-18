#!/usr/bin/env python3
"""Static readback of the pinned OpenCFD v2406 linux/arm64 image (issue #397).

The image is read from a `docker save` OCI archive. Nothing from the image is
executed and no container is created: layers are walked in order with their
whiteouts, files are hashed, and a few ELF files are parsed in Python to read
their machine, `.comment` strings, dynamic imports, exported binary64 constants
and the fused multiply-add instructions inside named geometry functions.

    docker pull --platform linux/arm64 docker.io/opencfd/openfoam-run@sha256:<digest>
    docker save --platform linux/arm64 -o <private>/image-arm64.tar <same reference>
    python3 readback_image.py --image <private>/image-arm64.tar \
        --source-archive <private>/OpenFOAM-v2406.tgz --extract <private dir> --write

The receipt holds hashes and observations only; extracted payloads stay in the
private directory, outside Git.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CONTRACT = HERE / "conversion-contract.json"
RECEIPT = HERE / "runtime-readback-20261118.json"
OPENFOAM = "usr/lib/openfoam/openfoam2406/"
SYSTEM_LIBS = (
    "usr/lib/aarch64-linux-gnu/libc.so.6",
    "usr/lib/aarch64-linux-gnu/libm.so.6",
    "usr/lib/aarch64-linux-gnu/libgcc_s.so.1",
    "usr/lib/aarch64-linux-gnu/libstdc++.so.6.0.33",
)
EXTRACT = (
    "bin/checkMesh", "lib/libOpenFOAM.so",
)
META_MANIFEST = OPENFOAM + "META-INFO/manifest.txt"
FE_IMPORTS = ("fesetround", "fesetenv", "feupdateenv", "fesetexceptflag", "feenableexcept",
              "fedisableexcept", "fegetround", "fegetenv")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_id(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


# --------------------------------------------------------------------------
# OCI archive and layers
# --------------------------------------------------------------------------

def read_oci(image: Path) -> tuple[dict, dict]:
    """Return the manifest record (digests verified) and the image configuration."""
    outer = tarfile.open(image)
    index = json.load(outer.extractfile("index.json"))
    entries = index["manifests"]
    if len(entries) != 1:
        raise SystemExit(f"expected one manifest in the saved archive, found {len(entries)}")
    digest = entries[0]["digest"]

    def blob(dig: str) -> bytes:
        data = outer.extractfile("blobs/sha256/" + dig.split(":", 1)[1]).read()
        if "sha256:" + sha256_bytes(data) != dig:
            raise SystemExit(f"blob {dig} does not hash to its name")
        return data

    manifest = json.loads(blob(digest))
    config = json.loads(blob(manifest["config"]["digest"]))
    layers = []
    for layer in manifest["layers"]:
        data = blob(layer["digest"])
        if len(data) != layer["size"]:
            raise SystemExit(f"layer {layer['digest']} size differs from its manifest")
        layers.append({"digest": layer["digest"], "size": layer["size"], "media_type": layer["mediaType"]})
    record = {"manifest_digest": digest, "config_digest": manifest["config"]["digest"], "layers": layers,
              "blobs_verified": 2 + len(layers)}
    return record, config, outer, manifest


def union_view(outer: tarfile.TarFile, manifest: dict, wanted, extract_dir: Path | None) -> dict:
    """Walk the layers in order; keep path -> {sha256, size, type, layer} with whiteouts applied."""
    view: dict[str, dict] = {}
    for index, layer in enumerate(manifest["layers"]):
        stream = outer.extractfile("blobs/sha256/" + layer["digest"].split(":", 1)[1])
        hardlinks = []
        with tarfile.open(fileobj=stream, mode="r|*") as tar:
            for member in tar:
                name = member.name.lstrip("./")
                base = name.rsplit("/", 1)[-1]
                parent = name.rsplit("/", 1)[0] + "/" if "/" in name else ""
                if base == ".wh..wh..opq":
                    for key in [k for k in view if k.startswith(parent)]:
                        del view[key]
                    continue
                if base.startswith(".wh."):
                    target = parent + base[4:]
                    for key in [k for k in view if k == target or k.startswith(target + "/")]:
                        del view[key]
                    continue
                if not wanted(name):
                    continue
                if member.isfile():
                    data = tar.extractfile(member).read()
                    entry = {"type": "file", "size": len(data), "sha256": sha256_bytes(data), "layer": index}
                    if extract_dir is not None and keep(name):
                        target = extract_dir / name
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(data)
                    view[name] = entry
                elif member.issym():
                    view[name] = {"type": "symlink", "target": member.linkname, "layer": index}
                elif member.islnk():
                    hardlinks.append((name, member.linkname.lstrip("./")))
                elif member.isdir():
                    continue
        for name, target in hardlinks:
            if target in view:
                view[name] = dict(view[target], hardlink_to=target)
    return view


def keep(name: str) -> bool:
    return (name in SYSTEM_LIBS or name == META_MANIFEST or name.endswith("/etc/controlDict")
            or name == "usr/lib/os-release" or name == "var/lib/dpkg/status"
            or any(name.endswith("/" + suffix) for suffix in EXTRACT))


# --------------------------------------------------------------------------
# Minimal ELF64 little-endian reader
# --------------------------------------------------------------------------

class Elf:
    def __init__(self, data: bytes):
        if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
            raise ValueError("not an ELF64 little-endian file")
        self.data = data
        self.machine = struct.unpack_from("<H", data, 0x12)[0]
        shoff = struct.unpack_from("<Q", data, 0x28)[0]
        shentsize, shnum, shstrndx = struct.unpack_from("<HHH", data, 0x3A)
        self.sections = []
        for i in range(shnum):
            name, kind, flags, addr, offset, size, link, info, align, entsize = struct.unpack_from(
                "<IIQQQQIIQQ", data, shoff + i * shentsize)
            self.sections.append({"name_off": name, "type": kind, "addr": addr, "offset": offset,
                                  "size": size, "link": link, "entsize": entsize})
        names = self.sections[shstrndx]
        for section in self.sections:
            section["name"] = self.cstr(names["offset"] + section["name_off"])

    def cstr(self, offset: int) -> str:
        end = self.data.index(b"\0", offset)
        return self.data[offset:end].decode("utf-8", "replace")

    def section(self, name: str):
        return next((s for s in self.sections if s["name"] == name), None)

    def symbols(self, table: str = ".dynsym") -> list[dict]:
        section = self.section(table)
        if section is None:
            return []
        strings = self.sections[section["link"]]
        result = []
        for offset in range(section["offset"], section["offset"] + section["size"], 24):
            name, info, other, shndx, value, size = struct.unpack_from("<IBBHQQ", self.data, offset)
            result.append({"name": self.cstr(strings["offset"] + name), "shndx": shndx,
                           "value": value, "size": size, "type": info & 0xF})
        return result

    def comment(self) -> list[str]:
        section = self.section(".comment")
        if section is None:
            return []
        raw = self.data[section["offset"]:section["offset"] + section["size"]]
        return sorted({part.decode("utf-8", "replace") for part in raw.split(b"\0") if part})

    def read_at(self, address: int, size: int) -> bytes | None:
        for section in self.sections:
            if section["addr"] <= address < section["addr"] + section["size"] and section["type"] != 8:
                start = section["offset"] + address - section["addr"]
                return self.data[start:start + size]
        return None

    def section_of(self, address: int) -> str | None:
        for section in self.sections:
            if section["addr"] and section["addr"] <= address < section["addr"] + section["size"]:
                return section["name"]
        return None


def classify(word: int) -> str | None:
    """AArch64 fused multiply-add classes (scalar FMADD family, vector FMLA/FMLS)."""
    if (word >> 24) == 0x1F:
        precision = {0: "single", 1: "double", 3: "half"}.get((word >> 22) & 3, "other")
        kind = ("fmadd", "fmsub", "fnmadd", "fnmsub")[((word >> 21) & 1) * 2 + ((word >> 15) & 1)]
        return f"{kind}.{precision}"
    if word & 0xBF20FC00 == 0x0E20CC00:
        return ("fmla" if not word & (1 << 23) else "fmls") + ".vector." + ("double" if word & (1 << 22) else "single")
    if word & 0xBF80B400 == 0x0F801000:
        return ("fmla" if not word & (1 << 14) else "fmls") + ".element." + ("double" if word & (1 << 22) else "single")
    return None


MSR_FPCR = (0xFFFFFFE0, 0xD51B4400)


def scan_function(elf: Elf, symbol: dict) -> dict:
    code = elf.read_at(symbol["value"], symbol["size"]) or b""
    counts: dict[str, int] = {}
    for offset in range(0, len(code) - 3, 4):
        kind = classify(struct.unpack_from("<I", code, offset)[0])
        if kind:
            counts[kind] = counts.get(kind, 0) + 1
    return {"symbol": symbol["name"], "bytes": len(code), "instructions": len(code) // 4,
            "fused": dict(sorted(counts.items())), "fused_total": sum(counts.values())}


def count_msr_fpcr(elf: Elf) -> int:
    text = elf.section(".text")
    if text is None:
        return 0
    code = elf.data[text["offset"]:text["offset"] + text["size"]]
    mask, value = MSR_FPCR
    return sum(1 for offset in range(0, len(code) - 3, 4)
               if struct.unpack_from("<I", code, offset)[0] & mask == value)


def double_bits(data: bytes) -> str:
    return "0x%016x" % struct.unpack("<Q", data)[0]


def literal_bits(literal: str) -> str:
    return "0x%016x" % struct.unpack("<Q", struct.pack("<d", float(literal)))[0]


def analyse_elf(path: Path, contract: dict, library: bool) -> dict:
    data = path.read_bytes()
    elf = Elf(data)
    dynsym = elf.symbols()
    imports = sorted({s["name"] for s in dynsym if s["shndx"] == 0 and s["name"]})
    defined = {s["name"]: s for s in dynsym if s["shndx"] != 0 and s["name"]}
    result = {
        "sha256": sha256_bytes(data), "bytes": len(data),
        "elf_machine": elf.machine, "elf_machine_name": {183: "AArch64", 62: "x86-64"}.get(elf.machine, "other"),
        "comment": elf.comment(),
        "has_symtab": elf.section(".symtab") is not None,
        "dynamic_symbols": len(dynsym),
        "imports_of_interest": [name for name in imports if name in
                                {"strtold", "strtod", "__trunctfdf2", "__letf2", "__getf2", "__extenddftf2",
                                 "cos", "sin", "acos", "sqrt", *FE_IMPORTS}],
        "fe_environment_imports": [name for name in imports if name in FE_IMPORTS],
        "set_fast_math_symbol": any("set_fast_math" in s["name"] for s in dynsym + elf.symbols(".symtab")),
        "msr_fpcr_in_text": count_msr_fpcr(elf),
    }
    if library:
        constants = []
        for item in contract["runtime_target"]["exported_constants"]:
            symbol = defined.get(item["symbol"])
            if symbol is None:
                constants.append({"symbol": item["symbol"], "found": False})
                continue
            raw = elf.read_at(symbol["value"], 8)
            constants.append({"symbol": item["symbol"], "found": True, "size": symbol["size"],
                              "section": elf.section_of(symbol["value"]), "literal": item["literal"],
                              "bits": double_bits(raw) if raw else None,
                              "literal_binary64_bits": literal_bits(item["literal"]),
                              "equal": bool(raw) and double_bits(raw) == literal_bits(item["literal"])})
        result["exported_constants"] = constants
        functions = []
        for fragment in contract["runtime_target"]["geometry_functions"]:
            for name, symbol in sorted(defined.items()):
                if fragment in name and symbol["type"] == 2:
                    functions.append(scan_function(elf, symbol))
        result["geometry_functions"] = functions
        names = list(defined)
        result["type_evidence"] = {
            "geometry_signatures_with_Vector_double": sum(1 for f in functions if "6VectorIdEE" in f["symbol"]),
            "geometry_signatures_with_Vector_float": sum(1 for f in functions if "6VectorIfEE" in f["symbol"]),
            "label_list_int32_signatures": sum(1 for f in functions if "5UListIiEE" in f["symbol"]),
            "label_list_int64_signatures": sum(1 for f in functions if "5UListIlEE" in f["symbol"]),
            "pTraits_double_symbols": sum(1 for n in names if n.startswith("_ZN4Foam7pTraitsIdE")),
        }
        result["strings"] = {key: data.find(key.encode()) >= 0
                             for key in ("_be01ca78-20240625", ";label=", ";scalar=", "LSB", "2406")}
    return result


# --------------------------------------------------------------------------
# Readback
# --------------------------------------------------------------------------

def source_blob_ids(archive: Path, members: list[str]) -> dict:
    with tarfile.open(archive) as tar:
        out = {}
        for member in members:
            data = tar.extractfile("OpenFOAM-v2406/" + member).read()
            out[member] = {"sha256": sha256_bytes(data), "git_blob": git_blob_id(data)}
        return out


def meta_manifest(path: Path) -> dict:
    entries = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "\t" in line:
            head, name = line.split("\t", 1)
            parts = head.split()
            if len(parts) == 3:
                entries[name] = parts[2]
    return entries


def readback(image: Path, archive: Path, extract: Path) -> dict:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    target = contract["runtime_target"]
    matrix = json.loads((REPO / target["matrix"]).read_text(encoding="utf-8"))
    row = next(r for r in matrix["rows"] if r["id"] == target["row"])
    record, config, outer, manifest = read_oci(image)
    platform_dir = target["platform_directory"] + "/"
    view = union_view(outer, manifest,
                      lambda name: name.startswith(OPENFOAM) or name in SYSTEM_LIBS
                      or name in ("usr/lib/os-release", "var/lib/dpkg/status"),
                      extract)
    executables = {name[len(platform_dir + "bin/"):]: entry["sha256"] for name, entry in sorted(view.items())
                   if name.startswith(platform_dir + "bin/") and entry["type"] == "file"}
    libraries = {name[len(platform_dir + "lib/"):]: entry["sha256"] for name, entry in sorted(view.items())
                 if name.startswith(platform_dir + "lib/") and entry.get("sha256")}
    aggregate = lambda table: sha256_bytes("".join(f"{v}  {k}\n" for k, v in sorted(table.items())).encode())
    pinned = row["executables"]
    comparisons = {name: {"pinned": digest, "observed": executables.get(name),
                          "equal": executables.get(name) == digest} for name, digest in sorted(pinned.items())}
    elf_check = analyse_elf(extract / platform_dir / "bin/checkMesh", contract, library=False)
    elf_lib = analyse_elf(extract / platform_dir / "lib/libOpenFOAM.so", contract, library=True)
    runtime_libs = {}
    for name in SYSTEM_LIBS:
        data = (extract / name).read_bytes()
        info = {"sha256": sha256_bytes(data), "bytes": len(data), "comment": Elf(data).comment()}
        if name.endswith("libc.so.6"):
            start = data.find(b"GNU C Library")
            info["version_banner"] = data[start:data.index(b"\n", start)].decode() if start >= 0 else None
        if "libstdc++" in name:
            versions = sorted({int(part.split(b".")[-1]) for part in
                               __import__("re").findall(rb"GLIBCXX_3\.4\.\d+", data)})
            info["max_glibcxx"] = f"GLIBCXX_3.4.{versions[-1]}" if versions else None
        runtime_libs[name] = info
    os_release = (extract / "usr/lib/os-release").read_text(encoding="utf-8")
    pretty = next((line.split("=", 1)[1].strip('"') for line in os_release.splitlines()
                   if line.startswith("PRETTY_NAME=")), None)
    status = (extract / "var/lib/dpkg/status").read_text(encoding="utf-8", errors="replace")
    packages = {}
    for block in status.split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line and not line.startswith(" "))
        if fields.get("Package") in {"openfoam2406", "libc6", "libstdc++6", "libgcc-s1"}:
            packages[fields["Package"]] = fields.get("Version")
    members = sorted({fact["member"] for fact in contract["source_archive"]["facts"]} | {
        "src/OpenFOAM/primitives/Scalar/scalar/scalar.H",
        "src/OpenFOAM/primitives/Scalar/doubleScalar/doubleScalar.H",
        "src/OSspecific/POSIX/signals/sigFpe.C",
        "applications/utilities/mesh/manipulation/checkMesh/checkGeometry.C",
    })
    blobs = source_blob_ids(archive, members)
    manifest_entries = meta_manifest(extract / META_MANIFEST)
    meta = {member: {"archive_git_blob": info["git_blob"], "image_manifest_git_blob": manifest_entries.get(member),
                     "equal": manifest_entries.get(member) == info["git_blob"]}
            for member, info in blobs.items()}
    committed_native_meta = json.loads((REPO / "twins/bionic-turbo-f1/evidence/airflow-native-binary-20261012/file-manifest.json")
                                       .read_text(encoding="utf-8"))
    archived = next(f["sha256"] for f in committed_native_meta["files"]
                    if f["path"] == "bionic-wall-flux-audit-20261012/native-meta/manifest.txt")
    checks = {
        "manifest-digest": record["manifest_digest"] == target["image"].split("@", 1)[1],
        "image-platform": (config.get("os"), config.get("architecture")) == ("linux", "arm64"),
        "executable-hashes": all(c["equal"] for c in comparisons.values() if c["observed"] is not None)
        and comparisons["checkMesh"]["equal"],
        "elf-machine": elf_check["elf_machine"] == 183 and elf_lib["elf_machine"] == 183,
        "long-double-path": {"strtold", "__trunctfdf2"} <= set(elf_lib["imports_of_interest"]),
        "exported-constants": all(c.get("equal") for c in elf_lib["exported_constants"]),
        "build-strings": elf_lib["strings"]["_be01ca78-20240625"]
        and elf_lib["type_evidence"]["geometry_signatures_with_Vector_double"] > 0
        and elf_lib["type_evidence"]["geometry_signatures_with_Vector_float"] == 0
        and elf_lib["type_evidence"]["label_list_int32_signatures"] > 0
        and elf_lib["type_evidence"]["label_list_int64_signatures"] == 0,
        "meta-info-manifest": all(m["equal"] for m in meta.values()),
    }
    return {
        "schema": "bionic-turbo-runtime-static-readback/v1",
        "issue": 397,
        "purpose": "Static readback of the pinned linux/arm64 image on the WSL x86_64 host. Nothing from the image was executed; no container was created; nothing was deleted.",
        "contract": {"path": "twins/bionic-turbo-f1/fp-chain-20261118/conversion-contract.json",
                     "sha256": sha256_bytes(CONTRACT.read_bytes())},
        "reference": target["image"],
        "oci": record,
        "config": {"os": config.get("os"), "architecture": config.get("architecture"),
                   "variant": config.get("variant"), "created": config.get("created"),
                   "diff_ids": config.get("rootfs", {}).get("diff_ids")},
        "os_release": pretty,
        "dpkg_versions": packages,
        "platform_directory": target["platform_directory"],
        "executables": {"count": len(executables), "aggregate_sha256": aggregate(executables),
                        "aggregate_rule": "sha256 of '<sha256>  <name>' lines sorted by name, newline-terminated"},
        "libraries": {"count": len(libraries), "aggregate_sha256": aggregate(libraries),
                      "libOpenFOAM.so": libraries.get("libOpenFOAM.so")},
        "pinned_executables": comparisons,
        "checkMesh": elf_check,
        "libOpenFOAM": elf_lib,
        "runtime_libraries": runtime_libs,
        "etc_controlDict_sha256": view.get(OPENFOAM + "etc/controlDict", {}).get("sha256"),
        "meta_info": {
            "build_info_sha256": view.get(OPENFOAM + "META-INFO/build-info", {}).get("sha256"),
            "api_info_sha256": view.get(OPENFOAM + "META-INFO/api-info", {}).get("sha256"),
            "manifest_sha256": view.get(META_MANIFEST, {}).get("sha256"),
            "manifest_sha256_archived_from_mac_2026_10_12": archived,
            "manifest_equal_to_archived": view.get(META_MANIFEST, {}).get("sha256") == archived,
            "source_members": meta,
        },
        "source_archive_sha256": sha256_bytes(archive.read_bytes()),
        "checks": checks,
        "all_checks_passed": all(checks.values()),
        "not_observed": "Execution of any of these files. Behaviour of strtold, the binary128 narrowing, printf, libm cos and the fused instructions at run time is not observed by a static readback.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--source-archive", type=Path, required=True)
    parser.add_argument("--extract", type=Path, required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    if REPO in args.extract.resolve().parents or REPO in args.image.resolve().parents:
        parser.error("image and extracted payloads are private outputs; keep them outside the repository")
    result = readback(args.image, args.source_archive, args.extract)
    text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.write:
        RECEIPT.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    print("static readback: " + ("all checks passed" if result["all_checks_passed"] else "CHECK FAILED"), file=sys.stderr)
    return 0 if result["all_checks_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
