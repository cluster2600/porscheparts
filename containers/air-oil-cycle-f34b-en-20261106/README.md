# English F34b generation

This additive generation implements the English source decision in issues
#581 and #607. Historical sources, manifests, image recipes and locks remain
unchanged. The four translated files live under `source/`; executable syntax
is identical except for the seed bundle comment and test failure messages.

`inputs.lock.json` binds every public input copied into a new context. The
context preparer refuses an existing destination and any destination inside
the repository, checks source hashes before writing, then regenerates the
manifest and seed bundle. It compares every field with the historical outputs:
only the expected prose and provenance hashes may differ. No solver runs.
The 3 MB manifest stays outside Git; its hash and size are in
`generation.lock.json`.

From the repository root, with Python 3.12:

```sh
python3 tests/test_air_oil_f34b_english_generation.py -v
python3 containers/air-oil-cycle-f34b-en-20261106/prepare_context.py /tmp/f34b-en-new
cd /tmp/f34b-en-new
python3 -m unittest discover -s tests -p 'test_*f34b*.py' -v
docker buildx build --platform linux/amd64 --load --tag f34b-en:validation \
  --file containers/air-oil-cycle-f34b.Dockerfile .
docker run --rm --platform linux/amd64 --user 9133:9133 \
  --network none --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --pids-limit 64 --cap-drop ALL --security-opt no-new-privileges \
  f34b-en:validation
```

The local build and offline smoke passed on Docker Desktop's Linux filesystem
under amd64 emulation on an arm64 Mac. `smoke.json` is the fresh runtime
receipt. The local image ID is recorded as local identity, not a published
registry digest. The host tests skip the Cantera fixture because Cantera is
provided by the image; the actual image smoke exercises Cantera 3.2.0.

The separate manual workflow `air-oil-cycle-f34b-english.yml` repeats the
generation and local build on an Ubuntu runner and retains receipts. It has
read-only permissions and does not publish an image. The translated static
image test checks the frozen historical publication workflow copied into the
context as a policy fixture; it does not attest the new workflow's execution.

The [native AMD64 run on November 7](https://github.com/cluster2600/porscheparts/actions/runs/42340207413)
passed on commit `441936f9ffd0281d1622ec3928e385e2e47f3e35`. Its six generation
tests passed; the 46 translated-context tests passed with one host Cantera skip,
then the built image exercised Cantera offline as user `9133:9133`. The exact
artifact members are retained in [native-validation-20261107/](native-validation-20261107/),
with their hashes, source bindings, archive digest and image configuration ID in
[the new native validation lock](native-validation-20261107.lock.json).
Independent readback matches the generated outputs to the existing generation
lock and the solver payload to the source. The earlier emulated-build lock and
smoke remain unchanged. Neither image configuration ID is a registry digest.

This generation preserves the historical Python/Cantera/NumPy dependency pins
to isolate translation. Integration with the dependency upgrades in #404–#406,
registry publication, anonymous digest access and a registry digest lock
remain pending. No physical, DOE execution, training or release gate is
promoted by the build or smoke test.
