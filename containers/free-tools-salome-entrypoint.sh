#!/bin/bash
set -e
# Use the distribution's own Python/library environment without starting a session.
source /opt/SALOME-9.16.0-native-DB12-SRC/env_launch.sh
set -u
exec "$PYTHONBIN" /opt/free-tools/salome_worker.py "$@"
