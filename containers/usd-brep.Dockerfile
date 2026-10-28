FROM python:3.12-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337
COPY usd-brep.requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --require-hashes -r /tmp/requirements.txt
COPY examples/usd_brep_smoke.py /opt/usd_brep_smoke.py
WORKDIR /work
ENTRYPOINT ["python"]
CMD ["/opt/usd_brep_smoke.py", "--output", "/work/usd-brep"]
