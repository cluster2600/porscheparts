#!/bin/sh
set -eu
# The publisher exposes the launcher without installing its context helpers on sys.path.
context_dir=$(cat /opt/free-tools/context-dir)
test -f "$context_dir/salomeContextUtils.py"
module_bins=$(cat /opt/free-tools/bin-pythonpath)
export PYTHONPATH="$context_dir:$module_bins${PYTHONPATH:+:$PYTHONPATH}"
exec salome shell -- python3 /opt/free-tools/salome_worker.py "$@"
