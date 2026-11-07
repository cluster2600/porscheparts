# syntax=docker/dockerfile:1.7
# Share the tested current solver stack while retaining this lane's shell entrypoint.
FROM porscheparts/cae-integrated-f33:stack-20261105
ENTRYPOINT ["/bin/bash", "-lc"]
CMD ["python /opt/stack/gmsh-volume-smoke.py && python /opt/stack/ccx-smoke.py /tmp/ccx-smoke && openfoam-engine-f35-smoke"]
