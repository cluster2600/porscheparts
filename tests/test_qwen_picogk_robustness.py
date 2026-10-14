"""Check the registered synthetic course without loading model weights."""
from pathlib import Path
import subprocess
import sys
import unittest


class PicoGKRobustnessTest(unittest.TestCase):
    def test_course_contract(self):
        script = Path(__file__).resolve().parents[1]/'training/qwen-picogk-robustness-20261013/run.py'
        result = subprocess.run([sys.executable, str(script), 'self-check'], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)

    def test_paired_correction_contract(self):
        script = Path(__file__).resolve().parents[1]/'training/qwen-picogk-robustness-20261013/correction.py'
        result = subprocess.run([sys.executable, str(script), 'self-check'], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)

    def test_timeout_fallback_still_rejects_changed_input(self):
        script = Path(__file__).resolve().parents[1]/'training/qwen-picogk-robustness-20261013/correction.py'
        code = '''
import importlib.util, pathlib, subprocess, sys, tempfile
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('bounded_correction',sys.argv[1])
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as directory:
    work=pathlib.Path(directory); source=work/'input'; source.write_text('registered')
    m.pilot.save(work/'FROZEN.json',{'files':{str(source):m.pilot.digest(source)}})
    actual=subprocess.run
    with patch.object(subprocess,'run',side_effect=[subprocess.TimeoutExpired('batch',15),actual([sys.executable,'-c','print("[\\"wrong-hash\\"]")'],capture_output=True,text=True)]):
        try: m.verify(work)
        except ValueError: pass
        else: raise AssertionError('Timeout fallback accepted a wrong hash')
'''
        result = subprocess.run([sys.executable, '-c', code, str(script)], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
