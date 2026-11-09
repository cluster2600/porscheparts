FROM opencfd/openfoam-run:2606@sha256:4229997e74defb81548222d511b8e3b95b98305e5df41b8e88b031813fe47eeb
USER root
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends g++ make openfoam2606-tutorials \
    && rm -rf /var/lib/apt/lists/* \
    && dpkg-query -W > /opt/system-packages.txt
COPY containers/stack-20261105/openfoam-com-smoke.sh /usr/local/bin/stack-smoke
RUN chmod 0555 /usr/local/bin/stack-smoke
RUN --network=none /usr/local/bin/stack-smoke
ENTRYPOINT ["/usr/local/bin/stack-smoke"]
