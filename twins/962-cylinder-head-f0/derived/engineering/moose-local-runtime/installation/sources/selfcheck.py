"""Unrun stdlib/AST checks; no Conda, archive decoder or real package import."""

import ast
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
from types import SimpleNamespace
import unittest

SOURCE = Path(__file__).with_name("install_prefix.py")
SOURCE_SHA256 = "b08b67c3d636ee5d7e217667eb26135ef98f73de86732d50cd29a8a37d6f43e3"
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA256
TREE = ast.parse(SOURCE.read_text())
NAMES = {"need", "digest", "tree_rows", "ordered_records", "copy_verified", "zero_pending", "approve_script"}
NS = {"Path": Path, "hashlib": hashlib, "os": os, "shutil": shutil, "stat": stat}
exec(compile(ast.Module(body=[n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name in NAMES],
                        type_ignores=[]), str(SOURCE), "exec"), NS)


class Guards(unittest.TestCase):
    def test_standard_initializer_and_observed_none_cache_exclusion(self):
        source = SOURCE.parent.parent / "moose-local-miniforge-001/lib/python3.14/site-packages/conda/core/package_cache_data.py"
        package_class = next(n for n in ast.parse(source.read_text()).body
                             if isinstance(n, ast.ClassDef) and n.name == "PackageCacheData")
        functions = [deepcopy(n) for n in package_class.body if isinstance(n, ast.FunctionDef)
                     and n.name in ("_check_writable", "all_caches_writable_first")]
        for function in functions: function.decorator_list = []
        marker = {"exists": False}
        def grouped(key, values):
            groups = {}
            for value in values: groups.setdefault(key(value), []).append(value)
            return groups
        namespace = dict(join=os.path.join, PACKAGE_CACHE_MAGIC_FILE="urls.txt", TRACE=0,
                         isfile=lambda path: marker["exists"], file_path_is_writable=lambda path: True,
                         log=SimpleNamespace(log=lambda *a: None, debug=lambda *a: None), groupby=grouped)
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), "exec"), namespace)
        cache = SimpleNamespace(pkgs_dir="/synthetic-task-cache")
        cache.is_writable = namespace["_check_writable"](cache)
        self.assertIsNone(cache.is_writable)
        self.assertEqual(namespace["all_caches_writable_first"](lambda _: cache, ("cache",)), ())
        marker["exists"] = True  # fake standard initializer outcome; no actual Conda/cache operation
        cache.is_writable = namespace["_check_writable"](cache)
        self.assertIs(cache.is_writable, True)
        self.assertEqual(namespace["all_caches_writable_first"](lambda _: cache, ("cache",)), (cache,))
        main = next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        init = next(n for n in ast.walk(main) if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Name) and n.func.id == "create_package_cache_directory")
        scan = next(n for n in ast.walk(main) if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute) and n.func.attr == "load"
                    and isinstance(n.func.value, ast.Name) and n.func.value.id == "cache")
        copy = next(n for n in ast.walk(main) if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Name) and n.func.id == "copy_verified")
        writable = next(n for n in ast.walk(main) if isinstance(n, ast.Compare)
                        and isinstance(n.left, ast.Attribute) and n.left.attr == "is_writable")
        self.assertLess(copy.lineno, init.lineno)
        self.assertLess(init.lineno, writable.lineno)
        self.assertLess(writable.lineno, scan.lineno)
        self.assertIsInstance(writable.ops[0], ast.Is)
        self.assertIs(writable.comparators[0].value, True)

    def test_full_record_order_and_refusal(self):
        fetch, links, completed, verified = [], [], [], {}
        for n in range(304):
            f = {"name": f"pkg{n}", "version": "1", "build": "b0", "build_number": 0,
                 "subdir": "noarch", "channel": "https://conda.anaconda.org/conda-forge/noarch",
                 "fn": f"pkg{n}-1-b0.conda", "size": 1, "sha256": "a" * 64, "md5": "b" * 32}
            fetch.append(f)
            links.append({"name": f["name"], "version": "1", "build_string": "b0", "build_number": 0,
                          "dist_name": f"pkg{n}-1-b0", "platform": "noarch",
                          "base_url": "https://conda.anaconda.org/conda-forge"})
            completed.append({"directory": f"pkg{n}-1-b0", "index": f})
            verified[f["fn"]] = {"bytes": 1, "sha256": "a" * 64, "md5": "b" * 32}
        plan = {"success": True, "dry_run": True, "actions": {"FETCH": fetch, "LINK": links[::-1]}}
        extracted = {"success": True, "all_archives_unchanged": True, "installation_executed": False,
                     "completed": completed, "verified_archives": verified}
        self.assertEqual([x[0] for x in NS["ordered_records"](plan, extracted)],
                         [f"pkg{n}-1-b0" for n in reversed(range(304))])
        for change in ("duplicate", "build", "checksum"):
            p, e = deepcopy(plan), deepcopy(extracted)
            if change == "duplicate": p["actions"]["LINK"][1] = p["actions"]["LINK"][0]
            if change == "build": p["actions"]["LINK"][0]["build_string"] = "other"
            if change == "checksum": e["verified_archives"][fetch[0]["fn"]]["sha256"] = "c" * 64
            with self.assertRaises(RuntimeError): NS["ordered_records"](p, e)

    def test_fresh_copy_full_bits_metadata_and_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            source = root / "extracted"
            source.mkdir()
            ordered = [(f"toy{n}", {"fn": f"toy{n}.conda"}) for n in range(304)]
            for name, _ in ordered: (source / name).mkdir()
            package = source / "toy0"
            (package / "data").write_bytes(b"exact toy bytes\x00")
            (package / "alias").symlink_to("data")
            receipt = source / "extraction-receipt.json"
            receipt.write_text("{}\n")
            identity_keys = {"path", "kind", "bytes", "sha256", "target"}
            ledger = {"schema": "962-independent-complete-extracted-tree-ledger/v1",
                      "receipt_sha256": NS["digest"](receipt), "failure_count": 0, "complete_packages": 304,
                      "packages": [{"directory": name, "filename": fetch["fn"], "complete_entry_ledger":
                                    [{k: v for k, v in row.items() if k in identity_keys}
                                     for row in NS["tree_rows"](source / name)["entries"]]}
                                   for name, fetch in ordered]}
            NS.update(SOURCE=source, EXTRACTION=receipt, STATE=root / "state", CACHE=root / "state/pkgs")
            snapshots = NS["copy_verified"](ordered, ledger)
            self.assertEqual(NS["tree_rows"](NS["CACHE"] / "toy0"), snapshots["toy0"])
            self.assertNotEqual((package / "data").stat().st_ino, (NS["CACHE"] / "toy0/data").stat().st_ino)
            NS.update(STATE=root / "state2", CACHE=root / "state2/pkgs")
            (package / "data").write_bytes(b"drift")
            with self.assertRaises(RuntimeError): NS["copy_verified"](ordered, ledger)
            self.assertFalse(NS["STATE"].exists())

    def test_script_and_zero_pending_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp).resolve()
            (prefix / "bin").mkdir()
            NS["PREFIX"] = prefix
            script = prefix / "bin/.toy-post-link.sh"
            script.write_text("echo synthetic\n")
            allowed = {"toy": NS["digest"](script)}
            self.assertEqual(NS["approve_script"](prefix, "toy", "post-link", allowed), script)
            guard = next(n for n in ast.walk(TREE) if isinstance(n, ast.FunctionDef) and n.name == "guarded_script")
            native_calls = []
            NS.update(allowed=allowed, receipt={"script_calls": []}, CACHE=prefix / "cache",
                      original_run_script=lambda *args: native_calls.append(args) or True)
            exec(compile(ast.Module(body=[guard], type_ignores=[]), str(SOURCE), "exec"), NS)
            prec = SimpleNamespace(name="toy", version="1", build="b0")
            self.assertTrue(NS["guarded_script"](str(prefix), prec, "post-link", activate=True))
            self.assertEqual(native_calls[0][-2:], (str(prefix), False))
            with self.assertRaises(RuntimeError): NS["guarded_script"](str(prefix), prec, "post-link")
            self.assertIsNone(NS["approve_script"](prefix, "missing", "pre-link", allowed))
            for name, action in (("toy", "pre-unlink"), ("toy", "unknown")):
                with self.assertRaises(RuntimeError): NS["approve_script"](prefix, name, action, allowed)
            (prefix / "bin/.toy-pre-link.sh").write_text("echo refused\n")
            with self.assertRaises(RuntimeError): NS["approve_script"](prefix, "toy", "pre-link", allowed)
            script.write_text("drift\n")
            with self.assertRaises(RuntimeError): NS["approve_script"](prefix, "toy", "post-link", allowed)
        for cache, extraction, refused in (((), (), False), ((object(),), (), True), ((), (object(),), True)):
            calls = []
            pfe = SimpleNamespace(prepare=lambda: calls.append(1), cache_actions=cache, extract_actions=extraction)
            if refused:
                with self.assertRaises(RuntimeError): NS["zero_pending"](pfe)
            else: NS["zero_pending"](pfe)
            self.assertEqual(calls, [1])

    def test_retained_native_boundary_and_config(self):
        main = next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        calls = [n for n in ast.walk(main) if isinstance(n, ast.Call)]
        self.assertEqual(sum(isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
                             and n.func.value.id == "txn" and n.func.attr == "execute" for n in calls), 1)
        original = next(n for n in calls if isinstance(n.func, ast.Name) and n.func.id == "original_run_script")
        self.assertIsInstance(original.args[-1], ast.Constant)
        self.assertIs(original.args[-1].value, False)
        config = json.loads(SOURCE.with_name("installer.yaml").read_text())
        self.assertTrue(config["offline"] and config["always_copy"] and config["extra_safety_checks"])
        self.assertEqual(config["safety_checks"], "enabled")
        self.assertFalse(config["register_envs"] or config["shortcuts"] or config["dry_run"])
        self.assertFalse(any(isinstance(n, (ast.Import, ast.ImportFrom)) and
                             any(x.name.startswith(("numpy", "scipy", "gmsh")) for x in n.names)
                             for n in TREE.body))


if __name__ == "__main__":
    unittest.main()
