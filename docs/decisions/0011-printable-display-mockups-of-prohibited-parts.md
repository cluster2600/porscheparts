# 0011 — A prohibited part may be published as an engraved display mock-up

Date: 2026-09-25

## Context

After the switch blank kit (0009) and the trim ring (0010), the project owner
asked for a printable **complex** part. Every complex part the repository
designed is an engine or structural part, classed
`prohibited_pending_engineering` or `functional`. None may be fitted, in any
material, and a polymer copy would fail at once in service.

## Decision

A `prohibited_pending_engineering` part may be published as a **1:1 display and
fit mock-up**, under three conditions:

1. the words **MOCK-UP** and **NOT FOR USE** are engraved into the printed
   geometry itself, not only written in the documentation;
2. the mock-up is generated from the unchanged master, with its SHA-256
   recorded, and any placement for printing is described;
3. the record's safety class and validation status do not change.

The first such mock-up is the F0 connecting rod,
`parts/993-eng-connecting-rod-ti64-f0-0001/print/`: rod and cap, engraved,
sliced in 4 h 57 min, bolted with two M8 × 45.

## Consequences

The repository's most complex designs can be held and inspected without
anything suggesting they can be used. SAFETY.md is unchanged: a mock-up is not a
release, and no engraved or un-engraved copy may enter a vehicle.
