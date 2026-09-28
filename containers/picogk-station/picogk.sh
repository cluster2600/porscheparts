#!/bin/sh
set -eu
export LD_LIBRARY_PATH=/app:/opt/picogk-native/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
exec dotnet "$@"
