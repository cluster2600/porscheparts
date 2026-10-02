# Porsche document corpus for Qwen

Owner-requested integration of the local PorscheFanatics data, 2 October 2026.
This adds actual catalogue records and manual tables to a private searchable
corpus and a separate source-grounded fine-tuning experiment. It supplements
the earlier lessons about evidence limits.

The first index contains 14,101 records: 12,864 PET occurrences, 15 site-reviewed
parts, 111 technical-data entries, 195 torque rows, 235 procedure-index entries,
674 full PET text pages and seven full ICE-review text pages. The union has
6,013 part references and 452 source-specific illustration groups. The listed
PET subset alone contains 5,998 distinct references. Full page extraction is
not complete interpretation of drawings, quantities, variant restrictions or
assembly topology. The existing site transcription does not expose every PDF
column; full text pages are available to cross-check it.

Raw documents, full text, SQLite database, training cases and weights stay in
ignored `work/qwen-porsche-corpus-001/`. No source copies are published.
Records preserve source, page and transcription status. Known OCR errors are
not silently corrected. Catalogue co-occurrence permits finding the parts on
an illustration, not inventing contact/joint graphs or measured mounting holes.

```sh
python3 training/qwen-porsche-corpus/corpus.py query \
  --output work/qwen-porsche-corpus-001/index --text '993 115 021 53'
python3 training/qwen-porsche-corpus/corpus.py query \
  --output work/qwen-porsche-corpus-001/index --text '99311502153' --assembly --limit 100
python3 training/qwen-porsche-corpus/corpus.py query \
  --output work/qwen-porsche-corpus-001/index --text 'data synchronization'
python3 -m unittest discover -s tests -p test_qwen_porsche_corpus.py -v
```

`corpus.py build --site <site checkout> --output <new directory>` reuses the
existing site's JSON. Add `--document source-id=/path/document.pdf` for each
local document (or page-separated layout text). It reads every page using
`pdftotext`, records blank pages and hashes its inputs. Queries use exact part
references and SQLite FTS5; multilingual semantic search is not implemented.
The database is read-only when queried, and an existing index is never replaced.

The first training protocol contains 677 training, 40 validation and 40 test
examples sampled from actual source records. Targets ask for a supplied field
and its provenance, including missing-information cases. All appearances of a
part number share one partition; manual partitions are grouped by page. Prompt
recipes are shared, so this measures extraction on held-out source entities,
not broad independent-task mastery. The complete indexed corpus is larger than
the sampled fine-tuning set, and source-conditioned retrieval is not memorisation
of every part in model weights.

The experiment continues engineering 005/1200 for a fixed 320 steps, learning
rate 5e-6, batch two, 16 LoRA layers, 1,024-token sequences and seed 1042.
Inputs and script hashes are frozen before baseline evaluation. Test cases open
only if validation reaches at least 95% in each category without losing a
baseline pass. It remains a separate experimental adapter, with no default
replacement, coding-retention qualification or manufacturing approval.

```sh
python3 training/qwen-porsche-corpus/train.py prepare \
  --index work/qwen-porsche-corpus-001/index --output work/qwen-porsche-corpus-001/run
/Users/maxime/.codex/worktrees/m64-local-architecture-qwen/3dprinting993/work/m64-qwen/venv/bin/python \
  training/qwen-porsche-corpus/train.py run --output work/qwen-porsche-corpus-001/run
```

The full workshop PDF and Leffingwell book have not yet been located in the
inspected local site copies. This is an access/location gap, not evidence that
they do not exist on the Mac. The site's workshop data currently supplies tables
and a procedure index, not full procedures. The identified Leffingwell title is
[*Porsche Turbo: The Inside Story of Stuttgart's Turbocharged Road and Race Cars*](https://play.google.com/store/books/details/Randy_Leffingwell_Porsche_Turbo?id=x1rfCgAAQBAJ).
The earlier photographed title was imprecise. No purchase or substitute book
download has been made.

The full [PET PDF](https://a.storyblok.com/f/332100/f97ce31af4/kat017-e-911-98-katalog.pdf)
and [ICE review](https://journal.cbiore.id/index.php/jese/article/download/5/5/14)
were retrieved directly for the private page index. Complete workshop and book
integration remains outstanding; the pipeline can ingest their local files
when located. Training status and scores must be read from execution receipts,
not inferred from this preparation document.
