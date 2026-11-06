# Corrected right-hand region — image of the real data

The [illustrated page](../right-supports.html) shows source region 008 of the
`real-support-source-008-full-004` pass. Its material graph passes:
112,898 faces, 897 groups and 20 components with upper and lower contacts.
The global admissions and the layer audit remain separate.

The render loads the checkpoint with `PreparedRegion`, which checks the
identities of the inputs, sources, runtime, surfaces, metadata and graph.
The detailed grid is group `grid-1-49-3`; its triangles are projected
into their real plane Y = 92.445 mm. The plane assertion passes, with no offset.

```sh
work/part-workflow/runtimes/pyslm-coverage-011/env/bin/python -B \
  scripts/render_carrier_region.py \
  work/carrier-process-20261016/real-support-source-008-full-004 \
  work/part-workflow/region-images-new
```

The first render, whose top view was unreadable for vertical sheets, remains
kept and editorially refused in `work/part-workflow/region-images-001`. The
present render and its page have been reviewed; their digests are recorded in
`visual-qa.json`.
