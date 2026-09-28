#!/bin/sh
set -eu
exec /opt/geometry-qa/bin/python /opt/station-repo/scripts/run_picogk_station_demo.py "$@"
