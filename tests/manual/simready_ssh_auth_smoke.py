#!/usr/bin/env python3
"""Real SSH authentication smoke, only inside a disposable network-none container.

Never run directly on a workstation: this harness creates synthetic root
authorized_keys inside the disposable container. It does not read user keys.
"""

import hashlib
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import tempfile
import time


EXPECTED_WRAPPER_SHA256 = "ebbf1c1e65203519d8386d2685ff48b98fb181e6a6bc7e09322df92143765f4b"
PARENT_IMAGE = "ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:79e76882a8f493012eb4cc9ab061bce0ca2d075cd505d6e33a5200e7e1e9b126"


def main():
    report = {
        "schema_version": "1.0.0",
        "status": "failed",
        "parent_image": PARENT_IMAGE,
        "production_full_image_tested": False,
        "vast_key_injection_order_verified": False,
        "gpu_or_head_simulation_performed": False,
        "checks": {},
    }
    step = "container_isolation"
    daemon = None
    authorized = Path("/root/.ssh/authorized_keys")
    created_authorized = False
    try:
        assert os.geteuid() == 0 and Path("/.dockerenv").is_file()
        assert set(os.listdir("/sys/class/net")) == {"lo"}, "network isolation required"
        assert not authorized.exists() and not authorized.is_symlink(), "fresh container required"
        assert Path("/usr/sbin/sshd").resolve() == Path("/usr/local/bin/simready-sshd-runtime-wrapper")
        actual_sha = hashlib.sha256(Path("/usr/local/bin/simready-sshd-runtime-wrapper").read_bytes()).hexdigest()
        assert actual_sha == EXPECTED_WRAPPER_SHA256
        report["wrapper_sha256"] = actual_sha
        report["checks"]["loopback_only_no_published_port"] = True
        with tempfile.TemporaryDirectory(prefix="simready-auth-smoke-") as temporary:
            directory = Path(temporary)
            key, other_key = directory / "ephemeral", directory / "untrusted"
            step = "synthetic_key_generation"
            for identity in (key, other_key):
                subprocess.run(
                    ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "synthetic-container-only", "-f", str(identity)],
                    check=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, timeout=10,
                )
            log_path = directory / "sshd.log"
            step = "wrapper_listener_start"
            with log_path.open("wb") as log:
                daemon = subprocess.Popen(
                    ["/usr/sbin/sshd", "-D", "-e", "-p", "22222", "-o", "ListenAddress=127.0.0.1", "-o", f"PidFile={directory / 'sshd.pid'}", "-o", "LogLevel=VERBOSE"],
                    stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                )
            deadline = time.monotonic() + 10
            while True:
                assert daemon.poll() is None, "sshd exited before listener"
                try:
                    with socket.create_connection(("127.0.0.1", 22222), timeout=0.2):
                        break
                except OSError:
                    assert time.monotonic() < deadline, "listener timeout"
                    time.sleep(0.05)
            report["checks"]["exact_wrapper_started_listener"] = True
            known_hosts = directory / "known_hosts"
            known_hosts.write_text("simready-auth-local-smoke " + Path("/etc/ssh/ssh_host_ed25519_key.pub").read_text())
            known_hosts.chmod(0o600)

            def ssh(identity=key, host_keys=known_hosts):
                return subprocess.run(
                    ["ssh", "-F", "/dev/null", "-T", "-i", str(identity),
                     "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes", "-o", "ForwardAgent=no",
                     "-o", "PasswordAuthentication=no", "-o", "KbdInteractiveAuthentication=no",
                     "-o", "ConnectTimeout=3", "-o", "ConnectionAttempts=1",
                     "-o", "StrictHostKeyChecking=yes", "-o", "UpdateHostKeys=no",
                     "-o", "GlobalKnownHostsFile=/dev/null", "-o", "HostKeyAlias=simready-auth-local-smoke",
                     "-o", f"UserKnownHostsFile={host_keys}", "-p", "22222", "root@127.0.0.1",
                     "printf AUTHENTICATED_SYNTHETIC_KEY"],
                    stdin=subprocess.DEVNULL, capture_output=True, text=True,
                    timeout=8, env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
                )

            step = "authentication_before_delayed_injection"
            result = ssh()
            assert result.returncode == 255 and "permission denied" in result.stderr.lower()
            report["checks"]["missing_authorized_keys_rejects_key"] = True

            step = "authentication_after_delayed_injection"
            authorized.write_text(key.with_suffix(".pub").read_text())
            created_authorized = True
            authorized.chmod(0o600)
            authorized.parent.chmod(0o700)
            assert stat.S_IMODE(authorized.stat().st_mode) == 0o600
            assert stat.S_IMODE(authorized.parent.stat().st_mode) == 0o700
            result = ssh()
            assert result.returncode == 0 and result.stdout == "AUTHENTICATED_SYNTHETIC_KEY"
            report["checks"]["delayed_injection_allows_same_key_without_sshd_restart"] = True

            step = "other_identity_rejected"
            result = ssh(other_key)
            assert result.returncode == 255 and "permission denied" in result.stderr.lower()
            report["checks"]["other_identity_rejected"] = True

            step = "unsafe_permissions_rejected"
            authorized.chmod(0o666)
            result = ssh()
            assert result.returncode == 255 and "permission denied" in result.stderr.lower()
            report["checks"]["unsafe_authorized_keys_permissions_rejected"] = True
            report["checks"]["server_logged_bad_permissions"] = "bad ownership or modes" in log_path.read_text().lower()
            assert report["checks"]["server_logged_bad_permissions"]

            step = "onstart_permission_operations_restore_authentication"
            # Same operations as onstart's SSH block, without starting GPU services.
            os.chown(authorized.parent, 0, 0)
            authorized.parent.chmod(0o700)
            os.chown(authorized, 0, 0)
            authorized.chmod(0o600)
            result = ssh()
            assert result.returncode == 0 and result.stdout == "AUTHENTICATED_SYNTHETIC_KEY"
            report["checks"]["onstart_equivalent_permission_operations_restore_auth"] = True

            step = "wrong_host_identity_rejected"
            wrong_hosts = directory / "wrong_known_hosts"
            wrong_hosts.write_text("simready-auth-local-smoke " + other_key.with_suffix(".pub").read_text())
            result = ssh(host_keys=wrong_hosts)
            assert result.returncode == 255 and "host key verification failed" in result.stderr.lower()
            report["checks"]["wrong_host_key_rejected"] = True
            daemon.terminate()
            daemon.wait(timeout=5)
            daemon = None
        report["checks"]["ephemeral_private_keys_removed"] = not directory.exists()
        report["status"] = "passed"
    except Exception as exc:
        report["failed_step"] = step
        report["error_type"] = type(exc).__name__
    finally:
        if daemon is not None:
            daemon.terminate()
            try:
                daemon.wait(timeout=3)
            except subprocess.TimeoutExpired:
                daemon.kill()
                daemon.wait(timeout=3)
        if created_authorized:
            authorized.unlink(missing_ok=True)
        report["raw_ssh_output_recorded"] = False
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
