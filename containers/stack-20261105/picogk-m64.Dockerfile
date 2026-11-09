FROM porscheparts/m64-leap71-native:stack-20261105
RUN test "$(dotnet --version)" = 10.0.403 \
    && apt-get update && apt-get install -y --no-install-recommends openssh-server ca-certificates python3-venv time libgl1 libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && find /etc/ssh -maxdepth 1 -type f -name 'ssh_host_*' -delete \
    && mv /usr/sbin/sshd /usr/lib/openssh/sshd.real \
    && mkdir -p /run/sshd /opt/picogk-witness /opt/provenance /workspace \
    && install -m 0600 /dev/null /root/.no_auto_tmux
ENV PATH=/opt/geometry-qa/bin:$PATH MPLBACKEND=Agg PYTHONUNBUFFERED=1
COPY containers/stack-20261105/geometry-qa.requirements.txt /opt/provenance/geometry-qa-requirements.txt
RUN python3 -m venv /opt/geometry-qa \
    && /opt/geometry-qa/bin/pip install --no-cache-dir --require-hashes -r /opt/provenance/geometry-qa-requirements.txt \
    && /opt/geometry-qa/bin/pip check \
    && /opt/geometry-qa/bin/pip freeze > /opt/provenance/geometry-qa-resolved.txt
COPY containers/m64-leap71/geometry-python-smoke.py containers/m64-leap71/RuntimeWitness.cs /opt/picogk-witness/
COPY containers/stack-20261105/RuntimeWitness.csproj /opt/picogk-witness/
COPY containers/m64-leap71/vast-entrypoint.sh /usr/local/bin/picogk-entrypoint
COPY containers/m64-leap71/vast-onstart.sh /usr/local/bin/picogk-vast-onstart
COPY containers/stack-20261105/picogk-smoke.sh /usr/local/bin/smoke-test.sh
COPY containers/simready-sshd-runtime-wrapper.sh /usr/local/bin/picogk-sshd-runtime-wrapper
COPY containers/m64-leap71/sshd-policy.conf /etc/ssh/sshd_config.d/00-picogk.conf
COPY containers/stack-20261105/sources.lock /opt/provenance/
COPY containers/stack-20261105/HeadVoxels.csproj /opt/m64-source/
COPY twins/m64-cylinder-head/source/picogk/Program.cs /opt/m64-source/
RUN dotnet build /opt/picogk-witness/RuntimeWitness.csproj -c Release -o /opt/picogk-witness/bin \
    && dotnet build /opt/m64-source/HeadVoxels.csproj -c Release -o /opt/m64 -p:UpstreamRoot=/upstream -p:GeneratePackageOnBuild=false \
    && chmod 0755 /usr/local/bin/picogk-entrypoint /usr/local/bin/picogk-vast-onstart /usr/local/bin/smoke-test.sh /usr/local/bin/picogk-sshd-runtime-wrapper \
    && ln -s /usr/local/bin/picogk-sshd-runtime-wrapper /usr/sbin/sshd \
    && dpkg-query -W > /opt/provenance/debian-packages.tsv \
    && dotnet --info > /opt/provenance/dotnet-info.txt \
    && sha256sum /app/picogk.26.2.so > /opt/provenance/native-library.sha256
RUN --network=none /usr/local/bin/smoke-test.sh picogk-m64
EXPOSE 22
WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/picogk-entrypoint"]
CMD ["sshd"]
