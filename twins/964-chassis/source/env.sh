# ADR-0002 toolchain for the 964 chassis twin.
# Two venvs: numpy pins of open3d and OCP are incompatible in one environment.
export TWIN_ROOT=/home/maxime/work/964twin
export LD_LIBRARY_PATH=$TWIN_ROOT/syslibs/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}
alias pymesh="$TWIN_ROOT/.venv/bin/python"      # trimesh, open3d, pymeshlab, scipy
alias pycad="$TWIN_ROOT/.venv-cad/bin/python"   # build123d, gmsh
