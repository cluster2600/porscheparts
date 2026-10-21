"""Run the fixed portable analyser with cwd=/; no scientific code here."""
import os
import runpy
import sys
os.chdir('/')
sys.argv=sys.argv[1:]
runpy.run_path(sys.argv[0],run_name='__main__')
