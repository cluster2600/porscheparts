#!/usr/bin/env python3
"""Offline tests for the bounded OpenBao GitHub wrapper."""

from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "deploy/openbao/openbao-github"


def load_wrapper():
    loader = SourceFileLoader("openbao_github", str(WRAPPER))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load wrapper")
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class OpenBaoGithubWrapperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.wrapper = load_wrapper()

    def test_scope_is_fixed_to_one_repository_and_two_direct_workflows(self) -> None:
        self.assertEqual(self.wrapper.REPOSITORY, "cluster2600/3dprinting993")
        self.assertEqual(
            self.wrapper.ALLOWED_WORKFLOWS,
            {
                "917-engine-wave-f40-vast-image.yml",
                "917-component-factory-f41-vast-image.yml",
            },
        )
        self.assertEqual(
            self.wrapper.ALLOWED_RUN_WORKFLOWS,
            self.wrapper.ALLOWED_WORKFLOWS | {"containers.yml"},
        )
        self.assertEqual(self.wrapper.ALLOWED_SECRET_PATH, "secrets/data/github")

    def test_push_uses_header_environment_not_url_or_arguments(self) -> None:
        token = "g" * 40
        completed = SimpleNamespace(returncode=0, stdout="ok", stderr="")
        with patch.object(self.wrapper, "current_branch_contract", return_value="codex/test"), patch.object(
            self.wrapper.subprocess, "run", return_value=completed
        ) as run:
            self.wrapper.push_current(token)
        args = run.call_args.args[0]
        environment = run.call_args.kwargs["env"]
        self.assertNotIn(token, " ".join(args))
        self.assertNotIn(token, self.wrapper.REMOTE_URL)
        self.assertEqual(args[-1], "HEAD:refs/heads/codex/test")
        self.assertEqual(environment["GIT_TERMINAL_PROMPT"], "0")
        self.assertEqual(environment["GIT_CONFIG_KEY_0"], "credential.helper")
        self.assertEqual(environment["GIT_CONFIG_VALUE_0"], "")
        self.assertEqual(environment["GIT_CONFIG_KEY_1"], "http.https://github.com/.extraheader")
        self.assertTrue(environment["GIT_CONFIG_VALUE_1"].startswith("Authorization: Basic "))

    def test_push_error_never_prints_token_or_remote_diagnostics(self) -> None:
        token = "t" * 40
        completed = SimpleNamespace(
            returncode=1,
            stdout=f"accidental {token}",
            stderr="remote diagnostic should remain private",
        )
        with patch.object(self.wrapper, "current_branch_contract", return_value="codex/test"), patch.object(
            self.wrapper.subprocess, "run", return_value=completed
        ):
            with self.assertRaisesRegex(self.wrapper.SafeError, "diagnostics withheld") as raised:
                self.wrapper.push_current(token)
        self.assertNotIn(token, str(raised.exception))
        self.assertNotIn("remote diagnostic", str(raised.exception))

    def test_branch_contract_rejects_dirty_or_non_codex_worktree(self) -> None:
        values = iter([self.wrapper.REMOTE_URL, "main", ""])
        with patch.object(self.wrapper, "git_stdout", side_effect=lambda _args: next(values)):
            with self.assertRaisesRegex(self.wrapper.SafeError, "codex"):
                self.wrapper.current_branch_contract()

        values = iter([self.wrapper.REMOTE_URL, "codex/test", "?? private.obj"])
        with patch.object(self.wrapper, "git_stdout", side_effect=lambda _args: next(values)):
            with self.assertRaisesRegex(self.wrapper.SafeError, "clean"):
                self.wrapper.current_branch_contract()

    def test_dispatch_is_exact_and_rejects_unapproved_workflows(self) -> None:
        with patch.object(
            self.wrapper,
            "github_request",
            return_value=(204, {}),
        ) as request:
            self.wrapper.dispatch_workflow(
                "secret",
                "917-engine-wave-f40-vast-image.yml",
                "codex/f40",
            )
        self.assertEqual(request.call_args.kwargs["method"], "POST")
        self.assertEqual(request.call_args.kwargs["payload"], {"ref": "codex/f40"})
        with self.assertRaisesRegex(self.wrapper.SafeError, "allowlist"):
            self.wrapper.dispatch_workflow("secret", "containers.yml", "codex/f40")

    def test_repository_auth_requires_push_permission(self) -> None:
        with patch.object(
            self.wrapper,
            "github_request",
            return_value=(200, {"full_name": self.wrapper.REPOSITORY, "permissions": {"push": False}}),
        ):
            with self.assertRaisesRegex(self.wrapper.SafeError, "push permission"):
                self.wrapper.repository_auth_check("secret")

    def test_simready_publication_is_fixed_to_one_image_and_push(self) -> None:
        parent = (
            "ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:"
            + "a" * 64
        )
        with (
            patch.object(
                self.wrapper,
                "github_request",
                return_value=(204, {}),
            ) as request,
            patch.object(
                self.wrapper,
                "current_branch_contract",
                return_value="codex/simready-fix",
            ),
            patch.object(
                self.wrapper,
                "SIMREADY_WORKFLOW_FOR_LOCAL_AI",
                parent,
            ),
            patch.object(self.wrapper.Path, "read_text", return_value=(
                "ARG TARGETPLATFORM=linux/amd64\n"
                f"FROM --platform=${{TARGETPLATFORM}} {parent}\n"
            )),
        ):
            self.wrapper.dispatch_simready_local_ai("secret", "codex/simready-fix")
        self.assertEqual(request.call_args.kwargs["method"], "POST")
        self.assertEqual(
            request.call_args.kwargs["payload"],
            {
                "ref": "codex/simready-fix",
                "inputs": {"image": "simready-local-ai", "push": True},
            },
        )
        self.assertIn("containers.yml/dispatches", request.call_args.args[1])

        with self.assertRaisesRegex(self.wrapper.SafeError, "codex"):
            self.wrapper.dispatch_simready_local_ai("secret", "main")

    def test_simready_chain_publication_is_strictly_allowlisted(self) -> None:
        base_parent = (
            "ghcr.io/cluster2600/3dprinting993-simready@sha256:" + "a" * 64
        )
        workflow_parent = (
            "ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:"
            + "b" * 64
        )
        for image in ("simready", "simready-workflow", "simready-local-ai"):
            source = "FROM ubuntu:24.04\n"
            if image == "simready-workflow":
                source = f"FROM {base_parent}\n"
            elif image == "simready-local-ai":
                source = f"FROM --platform=${{TARGETPLATFORM}} {workflow_parent}\n"
            with (
                self.subTest(image=image),
                patch.object(
                    self.wrapper,
                    "github_request",
                    return_value=(204, {}),
                ) as request,
                patch.object(
                    self.wrapper,
                    "current_branch_contract",
                    return_value="codex/simready-chain",
                ),
                patch.object(self.wrapper, "SIMREADY_BASE_FOR_WORKFLOW", base_parent),
                patch.object(
                    self.wrapper, "SIMREADY_WORKFLOW_FOR_LOCAL_AI", workflow_parent
                ),
                patch.object(self.wrapper.Path, "read_text", return_value=source),
            ):
                self.wrapper.dispatch_simready_image(
                    "secret", image, "codex/simready-chain"
                )
                self.assertEqual(
                    request.call_args.kwargs["payload"],
                    {
                        "ref": "codex/simready-chain",
                        "inputs": {"image": image, "push": True},
                    },
                )
        with self.assertRaisesRegex(self.wrapper.SafeError, "allowlist"):
            self.wrapper.dispatch_simready_image(
                "secret", "both", "codex/simready-chain"
            )

    def test_simready_parent_must_be_the_exact_allowlisted_digest(self) -> None:
        repository = self.wrapper.SIMREADY_PARENT_REPOSITORIES["simready-workflow"]
        valid = repository + "@sha256:" + "a" * 64
        self.assertEqual(
            self.wrapper.validate_simready_parent_ref(valid, repository), valid
        )
        for rejected in (
            repository + ":latest",
            repository + "@sha256:" + "a" * 63,
            "ghcr.io/cluster2600/wrong@sha256:" + "a" * 64,
        ):
            with self.subTest(rejected=rejected), self.assertRaisesRegex(
                self.wrapper.SafeError, "allowlisted immutable digest"
            ):
                self.wrapper.validate_simready_parent_ref(rejected, repository)

    def test_first_dockerfile_base_ignores_platform_option(self) -> None:
        parent = "ghcr.io/cluster2600/parent@sha256:" + "a" * 64
        source = (
            "# syntax=docker/dockerfile:1.7\n"
            "ARG TARGETPLATFORM=linux/amd64\n"
            f"FROM --platform=${{TARGETPLATFORM}} {parent}\n"
        )
        self.assertEqual(self.wrapper.first_dockerfile_base(source), parent)

    def test_simready_chain_blocks_children_until_parent_is_qualified(self) -> None:
        with (
            patch.object(self.wrapper, "SIMREADY_BASE_FOR_WORKFLOW", None),
            patch.object(
                self.wrapper,
                "current_branch_contract",
                return_value="codex/simready-chain",
            ),
            self.assertRaisesRegex(self.wrapper.SafeError, "parent digest is not qualified"),
        ):
            self.wrapper.dispatch_simready_image(
                "secret", "simready-workflow", "codex/simready-chain"
            )

    def test_production_workflow_parent_pin_matches_allowlist(self) -> None:
        source = (ROOT / "containers/simready-workflow.Dockerfile").read_text(
            encoding="utf-8"
        )
        self.assertEqual(
            self.wrapper.first_dockerfile_base(source),
            self.wrapper.SIMREADY_BASE_FOR_WORKFLOW,
        )

    def test_source_never_uses_keychain_raw_bao_or_credential_url(self) -> None:
        source = WRAPPER.read_text(encoding="utf-8")
        for forbidden in (
            "security find-",
            "security dump-keychain",
            "subprocess.run([\"bao\"",
            "subprocess.run([\"vault\"",
            "x-access-token:{token}@",
            "TOKEN=",
        ):
            self.assertNotIn(forbidden, source)
        self.assertNotIn("osxkeychain", source)

    def test_wrapper_compiles_and_diff_is_clean(self) -> None:
        completed = subprocess.run(
            ["python3", "-m", "py_compile", str(WRAPPER)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
