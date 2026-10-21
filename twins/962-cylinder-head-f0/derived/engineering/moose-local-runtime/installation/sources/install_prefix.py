"""Held, fixed304 offline prefix installation; no MOOSE invocation or PDE solve."""

from argparse import Namespace
from http.cookiejar import DefaultCookiePolicy
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import time
from urllib.parse import urlsplit

PREP = Path(__file__).resolve().parent
ENGINEERING = PREP.parent
ROOT = ENGINEERING.parent.parent
INSTALL = ENGINEERING / "moose-local-miniforge-001"
SOURCE = ENGINEERING / "moose-local-extracted-001"
STATE = ENGINEERING / "moose-local-install-state-002"
CACHE = STATE / "pkgs"
PREFIX = ENGINEERING / "moose-local-installed-002"
CONFIG = PREP / "installer.yaml"
HELD = PREP / "held-preparation.json"
ACTUAL = ENGINEERING / "moose-local-prefix-install-execution-prep-002/actual-contract-001.json"
PLAN = ENGINEERING / "moose-local-resolver-root-execution-004/stdout.json"
EXTRACTION = SOURCE / "extraction-receipt.json"
EXTRACTION_PEER = ENGINEERING / "moose-local-extraction-result-peer-002/review.json"
TREE_LEDGER = ENGINEERING / "moose-local-extraction-result-peer-002/tree-identity-ledger.json"
SCRIPTS = ENGINEERING / "moose-local-link-scripts-root-review-001/review.json"
CHANNELS = ("https://conda.software.inl.gov/public", "https://conda.anaconda.org/conda-forge")
ENVIRONMENT = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "OMP_NUM_THREADS": "2",
               "OPENBLAS_NUM_THREADS": "2", "VECLIB_MAXIMUM_THREADS": "2"}


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def blocked(*args, **kwargs):
    raise RuntimeError("Forbidden auth-store lookup, plugin discovery or transaction operation")


def public_metadata(url):
    parsed = urlsplit(url)
    allowed = {f"{channel}/{subdir}/repodata.json" for channel in CHANNELS
               for subdir in ("osx-arm64", "noarch")}
    need(url in allowed and parsed.scheme == "https" and not parsed.username
         and not parsed.password and not parsed.query and not parsed.fragment,
         "Only the four fixed public HTTPS repodata URLs are permitted")


def check_search_path(search_path):
    need(isinstance(search_path, (tuple, list))
         and tuple(search_path) in ((), (str(CONFIG),)), "Unexpected Conda config search path")


def no_entrypoints(self, group, name=None):
    need(group == "conda" and name is None, "Unexpected entrypoint-discovery request")
    return 0


def checked_send(original, self, request, **kwargs):
    public_metadata(request.url)
    need(request.method in ("GET", "HEAD") and self.trust_env is False,
         "Only public metadata reads without environment auth are permitted")
    forbidden = sorted({key.lower() for key in request.headers
                        if key.lower() in ("authorization", "proxy-authorization", "cookie")})
    need(not forbidden, "Auth or cookie header refused: " + ",".join(forbidden))
    need(kwargs.get("verify", self.verify) is True and not kwargs.get("cert", self.cert)
         and not kwargs.get("proxies", self.proxies), "TLS, certificate or proxy policy refused")
    raise RuntimeError("Offline cache-only continuation: every outgoing request is refused")


def check_inputs(mapping):
    for relative, expected in mapping.items():
        need(not Path(relative).is_absolute() and ".." not in Path(relative).parts,
             "Only repository-relative selected inputs are permitted")
        path = ROOT / relative
        need(path.is_file() and not path.is_symlink() and digest(path) == expected,
             "A selected input changed")


def tree_rows(package):
    need(package.is_dir() and not package.is_symlink() and package.resolve() == package,
         "Canonical package tree required")
    entries = []
    for directory, directories, files in os.walk(package, followlinks=False):
        directories.sort()
        for name in sorted(directories + files):
            path = Path(directory) / name
            info = path.lstat()
            row = {"path": path.relative_to(package).as_posix(),
                   "mode": stat.S_IMODE(info.st_mode), "mtime_ns": info.st_mtime_ns}
            if stat.S_ISLNK(info.st_mode):
                need(path.resolve().is_relative_to(package), "Package link escapes its tree")
                row.update(kind="symlink", target=os.readlink(path))
            elif stat.S_ISDIR(info.st_mode):
                row["kind"] = "directory"
            else:
                need(stat.S_ISREG(info.st_mode), "Special package file refused")
                row.update(kind="file", bytes=info.st_size, sha256=digest(path))
            entries.append(row)
    info = package.stat()
    return {"mode": stat.S_IMODE(info.st_mode), "mtime_ns": info.st_mtime_ns,
            "entries": sorted(entries, key=lambda row: row["path"])}


def ordered_records(plan, extracted):
    need(plan.get("success") is True and plan.get("dry_run") is True
         and len(plan["actions"]["FETCH"]) == len(plan["actions"]["LINK"]) == 304,
         "Exact successful304 solve required")
    need(extracted.get("success") is True and extracted.get("all_archives_unchanged") is True
         and extracted.get("installation_executed") is False and len(extracted["completed"]) == 304,
         "Complete unchanged extraction required")
    need(extracted["verified_archives"] == {row["fn"]: {"bytes": row["size"], "sha256": row["sha256"],
                                                       "md5": row["md5"]} for row in plan["actions"]["FETCH"]},
         "Full FETCH archive identities differ from extraction")
    by_name = {row["name"]: row for row in plan["actions"]["FETCH"]}
    by_directory = {row["directory"]: row for row in extracted["completed"]}
    need(len(by_name) == len(by_directory) == 304, "Duplicate package identity refused")
    ordered = []
    for link in plan["actions"]["LINK"]:
        fetch = by_name[link["name"]]
        directory = f"{fetch['name']}-{fetch['version']}-{fetch['build']}"
        index = by_directory[directory]["index"]
        need(link["version"] == fetch["version"] and link["build_string"] == fetch["build"]
             and link["build_number"] == fetch["build_number"]
             and link["dist_name"] == directory and link["platform"] == fetch["subdir"]
             and link["base_url"] + "/" + link["platform"] == fetch["channel"]
             and all(index[key] == fetch[key] for key in ("name", "version", "build", "build_number", "subdir")),
             "Full FETCH/LINK/extracted identity mismatch")
        ordered.append((directory, fetch))
    need(len({name for name, _ in ordered}) == 304, "LINK order repeats a package")
    return ordered


def copy_verified(ordered, ledger):
    packages = {row["directory"]: row for row in ledger["packages"]}
    need(ledger.get("schema") == "962-independent-complete-extracted-tree-ledger/v1"
         and ledger["receipt_sha256"] == digest(EXTRACTION) and ledger["failure_count"] == 0
         and ledger["complete_packages"] == len(packages) == len(ledger["packages"]) == 304
         and set(packages) == {name for name, _ in ordered}, "Complete observed tree ledger required")
    need({path.name for path in SOURCE.iterdir()} == set(packages) | {"extraction-receipt.json"},
         "Unexpected extraction-root entry")
    snapshots = {}
    identity_keys = {"path", "kind", "bytes", "sha256", "target"}
    for name, fetch in ordered:
        row = packages[name]
        need(row["filename"] == fetch["fn"], "Tree ledger package filename differs")
        expected = sorted(({k: v for k, v in entry.items() if k in identity_keys}
                           for entry in row["complete_entry_ledger"]), key=lambda entry: entry["path"])
        snapshots[name] = tree_rows(SOURCE / name)
        observed = [{k: v for k, v in entry.items() if k in identity_keys}
                    for entry in snapshots[name]["entries"]]
        need(observed == expected, "Frozen full source tree changed")
    STATE.mkdir()
    CACHE.mkdir()
    for name, _ in ordered:
        source, copied = SOURCE / name, CACHE / name
        shutil.copytree(source, copied, symlinks=True, copy_function=shutil.copy2)
        need(tree_rows(copied) == snapshots[name], "Copied tree or metadata changed")
        for row in snapshots[name]["entries"]:
            if row["kind"] == "file":
                a, b = (source / row["path"]).stat(), (copied / row["path"]).stat()
                need((a.st_dev, a.st_ino) != (b.st_dev, b.st_ino), "Copy shares original file inode")
    return snapshots


def zero_pending(pfe):
    pfe.prepare()
    need(not pfe.cache_actions and not pfe.extract_actions, "Offline cache is incomplete; no fetch/extract fallback")


def approve_script(prefix, name, action, allowed):
    need(action in ("pre-link", "post-link"), "Unlink or unknown package action refused")
    path = Path(prefix) / "bin" / f".{name}-{action}.sh"
    if not path.exists() and not path.is_symlink():
        return None
    need(action == "post-link" and Path(prefix) == PREFIX and name in allowed
         and path.is_file() and not path.is_symlink() and path.resolve() == path
         and digest(path) == allowed[name], "Unapproved package script refused")
    return path


def main():
    need(len(sys.argv) == 1 and sys.flags.isolated and sys.flags.dont_write_bytecode
         and Path(sys.prefix).resolve() == INSTALL and dict(os.environ) == ENVIRONMENT,
         "Exact selected isolated -I -B interpreter and six-entry environment required")
    need(ACTUAL.is_file() and not ACTUAL.is_symlink(), "Separate installation child required")
    actual = json.loads(ACTUAL.read_text())
    need(actual.get("schema") == "962-offline-prefix-install-actual/v1"
         and actual.get("installation_authorized") is True and actual.get("PDE_authorized") is False
         and actual.get("MOOSE_invocation_authorized") is False
         and actual.get("manufacturing_authorized") is False, "Offline installation authority absent")
    pins = actual["input_sha256"]
    need(pins.get(str(HELD.relative_to(ROOT))) == digest(HELD), "Held source is not bound")
    held = json.loads(HELD.read_text())
    need(all(pins.get(key) == value for key, value in held["input_sha256"].items()), "Prepared pin omitted")
    check_inputs(pins)
    for key, path in (("extraction_result_peer", EXTRACTION_PEER), ("extracted_tree_ledger", TREE_LEDGER)):
        need(actual[key] == str(path.relative_to(ROOT)) and actual[key] in pins,
             "Exact external extraction proof must be directly pinned")
    need(json.loads(EXTRACTION_PEER.read_text())["decision"] == "CLEAR_COMPLETE_EXTRACTED_DATA_AND_METADATA_ONLY",
         "Independent complete extraction review required")
    for path in (STATE, PREFIX):
        need(not path.exists() and not path.is_symlink() and path.resolve() == path, "Fresh canonical install path required")
    need(shutil.disk_usage(PREP).free >= 12 * 1024**3, "Less than12GiB free before installation")
    ordered = ordered_records(json.loads(PLAN.read_text()), json.loads(EXTRACTION.read_text()))
    ledger = json.loads(TREE_LEDGER.read_text())
    scripts = json.loads(SCRIPTS.read_text())
    allowed = scripts["actual_macOS_post_link_scripts_reviewed"]
    need(set(allowed) == {"gtk3", "librsvg", "graphviz", "gdk-pixbuf"}
         and scripts["actual_pre_link_scripts"] == [] and scripts["unlink_allowed_in_fresh_install"] is False
         and scripts["extraction_receipt_sha256"] == digest(EXTRACTION), "Exact approved script review required")
    receipt = {"schema": "962-offline-prefix-install/v1", "success": False,
               "installation_attempted": False, "package_count": 304, "script_calls": [],
               "network_permitted": False, "MOOSE_invoked": False, "PDE_executed": False,
               "native_utility_or_ABI_qualification": False}
    started = time.monotonic()
    snapshots = None
    try:
        snapshots = copy_verified(ordered, ledger)  # every source/copy byte before Conda cache writes
        sys.addaudithook(lambda event, args: need(not event.startswith("socket."), "Network event refused"))
        # Retained resolver004 guard order: Configuration before Context, plugin guard before manager.
        from conda.common.configuration import Configuration
        original_search = Configuration._set_search_path

        def guarded_search(self, search_path, **kwargs):
            check_search_path(search_path)
            return original_search(self, search_path, **kwargs)

        Configuration._set_search_path = guarded_search
        from conda.base.context import Context, context
        Context._set_search_path = guarded_search
        Context.envs_dirs = property(lambda self: (str(STATE / "envs"),))
        context.__init__(search_path=(str(CONFIG),), argparse_args=Namespace(prefix=str(PREFIX)))
        from conda.plugins.manager import CondaPluginManager, get_plugin_manager
        need(get_plugin_manager.cache_info().currsize == 0, "Plugin manager preceded guard")
        CondaPluginManager.load_entrypoints = no_entrypoints
        import requests.sessions as sessions
        import requests.utils as request_utils
        import conda.gateways.connection as connection
        import conda.gateways.anaconda_client as anaconda_client
        import conda.gateways.connection.session as conda_session
        from requests.auth import AuthBase
        for module in (sessions, request_utils, connection, conda_session):
            module.get_netrc_auth = blocked
        anaconda_client.read_binstar_tokens = blocked
        conda_session.read_binstar_tokens = blocked
        conda_session.CondaHttpAuth.__call__ = blocked
        conda_session.CondaHttpAuth.handle_407 = blocked

        class PublicAuth(AuthBase):
            channel_name = "fixed-public-metadata"

            def __call__(self, request):
                public_metadata(request.url)
                return request

        class NoPublicCookies(DefaultCookiePolicy):
            def set_ok(self, cookie, request):
                return False

            def return_ok(self, cookie, request):
                return False

        original_session_init = sessions.Session.__init__

        def session_init(self):
            original_session_init(self)
            self.cookies.set_policy(NoPublicCookies())
            self.trust_env = False
            self.auth = PublicAuth()

        sessions.Session.__init__ = session_init
        original_conda_init = conda_session.CondaSession.__init__

        def conda_init(self, auth=None):
            need(auth is None, "Caller-supplied channel auth refused")
            original_conda_init(self, auth=PublicAuth())
            self.trust_env = False

        need(not getattr(conda_session.CondaSession._thread_local, "sessions", {}), "HTTP session preceded guards")
        conda_session.CondaSession.__init__ = conda_init
        original_send = sessions.Session.send
        sessions.Session.send = lambda self, request, **kwargs: checked_send(original_send, self, request, **kwargs)
        from conda.base.constants import SafetyChecks
        need(context.offline and context.no_plugins and context.always_copy and not context.register_envs
             and context.safety_checks == SafetyChecks.enabled and context.extra_safety_checks
             and tuple(context.pkgs_dirs) == (str(CACHE),) and context.envs_dirs == (str(STATE / "envs"),)
             and context.target_prefix == str(PREFIX) and not context.shortcuts and not context.dry_run
             and context.add_anaconda_token is False and context.ssl_verify is True and not context.proxy_servers
             and not context.client_ssl_cert and not context.client_ssl_cert_key
             and context.number_channel_notices == 0 and context.subdir == "osx-arm64"
             and context.verify_threads == context.execute_threads == 2
             and context.always_yes and not context.notify_outdated_conda and not context.auto_update_conda,
             "Effective offline install policy changed")
        from conda.models.records import PackageRecord, PackageCacheRecord
        from conda.core.package_cache_data import PackageCacheData
        from conda.core.link import PrefixSetup, UnlinkLinkTransaction
        from conda.gateways.disk.create import write_as_json_to_file, create_package_cache_directory
        import conda.core.link as link_module
        need(create_package_cache_directory(str(CACHE)) is True, "Standard package-cache initialization failed")
        # Seed complete records before a cache scan can synthesize incomplete directory records.
        records = [PackageRecord.from_objects(fetch) for _, fetch in ordered]
        for (name, _), record in zip(ordered, records):
            write_as_json_to_file(str(CACHE / name / "info/repodata_record.json"), record)
        cache = PackageCacheData(str(CACHE))
        need(cache.is_writable is True, "Initialized task cache must be writable")
        cache.load()
        for (name, fetch), record in zip(ordered, records):
            cache.insert(PackageCacheRecord.from_objects(record, extracted_package_dir=str(CACHE / name),
                         package_tarball_full_path=str(ENGINEERING / "moose-local-archives-002" / fetch["fn"])))
        original_run_script = link_module.run_script

        def guarded_script(prefix, prec, action="post-link", env_prefix=None, activate=False):
            need(action == "pre-link" and not activate and env_prefix == str(PREFIX)
                 or action == "post-link" and activate is True and env_prefix is None,
                 "Unexpected upstream script context")
            expected_prefix = CACHE / f"{prec.name}-{prec.version}-{prec.build}" if action == "pre-link" else PREFIX
            need(Path(prefix) == expected_prefix, "Unexpected script prefix")
            path = approve_script(prefix, prec.name, action, allowed)
            if path and prec.name == "librsvg":
                need(approve_script(PREFIX, "gdk-pixbuf", "post-link", allowed), "Nested gdk script missing")
            if path:
                receipt["script_calls"].append({"name": prec.name, "action": action,
                                               "sha256": allowed[prec.name], "attempted": True})
            # Approved scripts use explicit PREFIX paths; do not source an activation wrapper.
            result = original_run_script(prefix, prec, action, str(PREFIX), False)
            if path:
                need(digest(path) == allowed[prec.name], "Approved script changed during execution")
            return result

        link_module.run_script = guarded_script
        txn = UnlinkLinkTransaction(PrefixSetup(str(PREFIX), (), tuple(records), (), (), ()))
        zero_pending(txn._get_pfe())
        receipt["zero_cache_actions"] = receipt["zero_extract_actions"] = True
        txn.prepare()
        txn.verify()
        receipt["installation_attempted"] = True
        txn.execute()
        need({row["name"] for row in receipt["script_calls"]} == set(allowed)
             and len(receipt["script_calls"]) == 4, "Approved script-call coverage changed")
        metadata = sorted((PREFIX / "conda-meta").glob("*.json"))
        installed = [json.loads(path.read_text()) for path in metadata]
        need(len(installed) == 304 and {(row["name"], row["version"], row["build"]) for row in installed}
             == {(row.name, row.version, row.build) for row in records}, "Installed prefix records differ")
        receipt["prefix_records"] = [{"filename": path.name, "sha256": digest(path), "bytes": path.stat().st_size}
                                     for path in metadata]
        receipt["success"] = True
    except Exception as error:
        receipt["failure_type"] = type(error).__name__
        raise
    finally:
        receipt["wall_seconds"] = time.monotonic() - started
        try:
            check_inputs(pins)
            if snapshots is not None:
                need(all(tree_rows(SOURCE / name) == snapshots[name] for name, _ in ordered),
                     "Frozen extraction changed during installation")
            receipt["all_bound_inputs_and_extracted_trees_unchanged"] = True if snapshots is not None else None
        except Exception as error:
            receipt["all_bound_inputs_and_extracted_trees_unchanged"] = False
            receipt["final_verification_failure_type"] = type(error).__name__
            receipt["success"] = False
        if STATE.is_dir() and not STATE.is_symlink():
            with (STATE / "installation-receipt.json").open("x") as stream:
                json.dump(receipt, stream, indent=2)
                stream.write("\n")
        need(receipt["all_bound_inputs_and_extracted_trees_unchanged"], "Input drift; failed receipt retained")


if __name__ == "__main__":
    main()
