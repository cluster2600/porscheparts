# 0003 — No automated harvesting from resellers

Date: August 28, 2026

## Context

The digital twin fills up part number by part number, and only one source
published a per-part mass while also answering automated requests: the Rose
Passion catalogue, structured by PET illustrations just like the assembly
skeleton. A targeted retrieval tool was therefore studied.

## What the check established

`https://www.rosepassion.com/robots.txt`, retrieved on August 28, 2026, opens
with these four lines:

```
User-agent: ClaudeBot
Disallow: /
User-agent: Claude-Web
Disallow: /
```

The site closes all of its pages to these agents, naming them first. There is
no `Crawl-delay` directive: there is no tolerated rate; the answer to "at what
pace" is "not at all".

The terms of sale, for their part, are closed to **all** robots. They were
therefore not read, and the question of reusing the product data remains
**unanswered** — not answered favorably.

## Decision

**No tool in this repository will query this catalogue automatically.** The
script that was studied was written, then deleted without being committed.

The obvious workaround is named here so that it is excluded: sending a custom
`User-Agent` would match the client to the permissive `*` group, where product
pages are allowed. That is precisely what the implementation had done, and it is
circumvention — renaming yourself to get past a refusal that names you is not
obtaining permission.

## What remains open

- **A human reading in a browser.** `robots.txt` governs robots, not a person.
  Reuse of the data remains subject to the terms, which are still to be read.
- **Written authorization from the seller**, or a data extract supplied by
  them, which would also settle the reuse question.

## Associated correction

The record `SRC-ROSEPASSION-993-PARTS` and `catalog/reference/README.md` stated
that this reseller "responds to automated retrieval". That confused "the server
returns a page" with "the operator authorizes automated access". Both texts are
corrected.
