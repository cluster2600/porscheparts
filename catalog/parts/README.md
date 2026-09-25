# Parts catalog

This directory contains one JSON record per part. A record is not evidence of
compatibility: its `validation.status` field states the level actually reached.

Create a record from `catalog/templates/part-record.json`, use a lowercase
filename matching `part_id`, then run `make check`.
