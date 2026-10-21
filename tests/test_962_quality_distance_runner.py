"""A timed-out RSS observer must kill and reap its native child."""
import importlib.util
from pathlib import Path
import signal
import subprocess
import unittest
from unittest.mock import Mock, patch

PATH = Path(__file__).resolve().parents[1]/"twins/962-cylinder-head-f0/source/run_quality_distance_002.py"
SPEC = importlib.util.spec_from_file_location("quality_distance_runner_002", PATH)
MODULE = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MODULE)


class MonitorCleanup(unittest.TestCase):
    def test_monitor_timeout_kills_and_reaps_worker_before_retained_refusal(self):
        process = Mock(pid=12345); process.poll.return_value = None
        def reaped(timeout):
            process.poll.return_value = -signal.SIGKILL
            return -signal.SIGKILL
        process.wait.side_effect = reaped
        with patch.object(MODULE.time, "monotonic", return_value=0.), \
                patch.object(MODULE.subprocess, "run", side_effect=subprocess.TimeoutExpired("ps", 2)), \
                patch.object(MODULE.os, "killpg") as kill:
            result = MODULE.monitor(process, 0., dict(process_group_deadline_seconds=300,
                rss_stop_bytes=4294967296, rss_poll_seconds=.1))
        kill.assert_called_once_with(12345, signal.SIGKILL)
        process.wait.assert_called_once_with(timeout=3)
        self.assertEqual(result["stopped_by_watchdog"], "monitor_exception_refusal")
        self.assertIn("TimeoutExpired", result["monitor_error"])
        self.assertIs(result["worker_reaped"], True)
        self.assertIs(result["worker_running_after_monitor"], False)


if __name__ == "__main__":
    unittest.main()
