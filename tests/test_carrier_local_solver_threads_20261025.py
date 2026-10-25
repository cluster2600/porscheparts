"""The patched-library trial keeps serial Fortran and explicitly bounded solver threads."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022'


class LocalSolverThreadTests(unittest.TestCase):
    def test_source_fetcher_refuses_a_different_manifest_before_creating_output(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);manifest=root/'manifest.json';manifest.write_text('{}');out=root/'sources';result=subprocess.run([sys.executable,str(SOURCE/'fetch_native_spooles_sources.py'),'--manifest',str(manifest),'--output',str(out)],capture_output=True,text=True,timeout=20)
            self.assertNotEqual(result.returncode,0);self.assertFalse(out.exists());self.assertFalse(out.with_name(out.name+'.fetching').exists())

    def test_dependency_build_refuses_an_unbounded_wall_budget_before_creating_output(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);out=root/'build';result=subprocess.run([sys.executable,str(SOURCE/'build_native_spooles_fixed.py'),'--sources',str(root),'--output',str(out),'--seconds','1801'],capture_output=True,text=True,timeout=20)
            self.assertNotEqual(result.returncode,0);self.assertFalse(out.exists())

    def test_owned_worker_records_the_actual_child_thread_environment_and_helper_hash(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);binary=root/'fake-ccx';binary.write_text('#!/bin/sh\nprintf "%s %s %s %s %s\\n" "$OMP_NUM_THREADS" "$CCX_NPROC_STIFFNESS" "$CCX_NPROC_RESULTS" "$CCX_NPROC_EQUATION_SOLVER" "$NUMBER_OF_CPUS"\nprintf "Job finished\\n"\n');binary.chmod(0o755);deck=root/'input.inp';deck.write_text('*STEP\n');out=root/'run'
            command=[sys.executable,str(SOURCE/'run_local_ccx_solver_parallel.py'),'--binary',str(binary),'--deck',str(deck),'--output',str(out),'--expected-binary',hashlib.sha256(binary.read_bytes()).hexdigest(),'--seconds','10','--rss-gib','1','--solver-threads','8']
            result=subprocess.run(command,capture_output=True,text=True,timeout=20);self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual((out/'stdout.log').read_text().splitlines()[0],'1 1 1 8 8')
            plan=json.loads((out/'plan.json').read_text());self.assertEqual(plan['equation_solver_threads_requested'],8);self.assertEqual(plan['assembly_threads_requested'],1)
            self.assertIn(hashlib.sha256((SOURCE/'run_local_ccx_serial.py').read_bytes()).hexdigest(),plan['input_sha256'].values())
            command[command.index(str(out))]=str(root/'invalid');command[-1]='9';bad=subprocess.run(command,capture_output=True,text=True,timeout=20);self.assertNotEqual(bad.returncode,0);self.assertFalse((root/'invalid').exists())

if __name__=='__main__':unittest.main()
