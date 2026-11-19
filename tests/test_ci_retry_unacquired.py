"""The automatic re-run of CI jobs GitHub never gave a runner (#733)."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ci_retry_unacquired.py"
WORKFLOW = ROOT / ".github" / "workflows" / "retry-unacquired.yml"

spec = importlib.util.spec_from_file_location("ci_retry_unacquired", SCRIPT)
retry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retry)

# Shapes taken from the REST API on 2026-11-19 (run 44561136365, PR #731).
UNACQUIRED = {"name": "carrier-cad", "status": "completed", "conclusion": "cancelled", "runner_name": "", "steps": []}
PASSED = {"name": "check", "status": "completed", "conclusion": "success", "runner_name": "GitHub Actions 12",
          "steps": [{"name": "Set up job", "conclusion": "success"}]}
RAN_AND_FAILED = {"name": "check", "status": "completed", "conclusion": "failure", "runner_name": "GitHub Actions 7",
                  "steps": [{"name": "Validate repository", "conclusion": "failure"}]}
RAN_AND_TIMED_OUT = {**RAN_AND_FAILED, "name": "carrier-pyslm", "conclusion": "timed_out"}


class DecisionTests(unittest.TestCase):
    def test_reruns_when_every_failed_job_was_never_acquired(self):
        rerun, why = retry.decide([PASSED, UNACQUIRED, {**UNACQUIRED, "name": "carrier-pyslm", "runner_name": None}])
        self.assertTrue(rerun)
        self.assertIn("carrier-cad", why)
        self.assertIn("carrier-pyslm", why)

    def test_never_reruns_a_job_that_ran_and_failed(self):
        for real in (RAN_AND_FAILED, RAN_AND_TIMED_OUT):
            rerun, why = retry.decide([UNACQUIRED, real])
            self.assertFalse(rerun, real["conclusion"])
            self.assertIn(real["name"], why)

    def test_a_cancelled_job_that_had_started_counts_as_ran(self):
        started = {**UNACQUIRED, "runner_name": "GitHub Actions 3", "steps": [{"name": "Set up job"}]}
        self.assertFalse(retry.decide([started])[0])
        # a runner was named but no step was recorded: still not "never acquired"
        self.assertFalse(retry.decide([{**UNACQUIRED, "runner_name": "GitHub Actions 3"}])[0])

    def test_nothing_failed_means_no_rerun(self):
        self.assertEqual(retry.decide([PASSED]), (False, "no failed job"))
        self.assertEqual(retry.decide([]), (False, "no failed job"))

    def test_command_line_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            cases = {"rerun.jsonl": ([PASSED, UNACQUIRED], retry.RERUN), "keep.jsonl": ([UNACQUIRED, RAN_AND_FAILED], retry.KEEP)}
            for name, (jobs, code) in cases.items():
                path = Path(tmp) / name
                path.write_text("".join(json.dumps(job) + "\n" for job in jobs), encoding="utf-8")
                run = subprocess.run([sys.executable, "-I", str(SCRIPT), str(path)], capture_output=True, text=True)
                self.assertEqual(run.returncode, code, run.stdout + run.stderr)
            run = subprocess.run([sys.executable, "-I", str(SCRIPT)], capture_output=True, text=True)
            self.assertNotIn(run.returncode, (retry.RERUN, retry.KEEP))


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text(encoding="utf-8")

    def test_it_follows_the_validate_workflow_by_its_name(self):
        name = next(line.split(":", 1)[1].strip() for line in
                    (ROOT / ".github" / "workflows" / "validate.yml").read_text(encoding="utf-8").splitlines()
                    if line.startswith("name:"))
        self.assertIn(f'workflows: ["{name}"]', self.text)
        self.assertIn("types: [completed]", self.text)

    def test_it_is_bounded_and_only_acts_on_failed_runs(self):
        self.assertIn("github.event.workflow_run.conclusion == 'failure'", self.text)
        self.assertIn("github.event.workflow_run.run_attempt < 3", self.text)
        self.assertIn("timeout-minutes: 5", self.text)

    def test_it_runs_no_code_from_the_triggering_run(self):
        # workflow_run checks out the default branch unless told otherwise; never the event's head.
        self.assertNotIn("head_sha", self.text)
        self.assertNotIn("head_branch", self.text)
        self.assertNotIn("ref:", self.text)
        self.assertIn("persist-credentials: false", self.text)

    def test_it_reruns_only_on_the_scripts_yes(self):
        self.assertIn("python3 scripts/ci_retry_unacquired.py", self.text)
        self.assertIn('if [ "$code" -eq 0 ]; then', self.text)
        self.assertIn('gh run rerun "$RUN_ID" --failed', self.text)
        self.assertIn(f'elif [ "$code" -ne {retry.KEEP} ]; then', self.text)
        self.assertIn("actions: write", self.text)


if __name__ == "__main__":
    unittest.main()
