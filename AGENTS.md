# Repository instructions

This repository builds an evidence-backed catalogue of reproducible Porsche 993
parts for additive and conventional manufacturing.

## Working rules

- Treat `catalog/parts/*.json` as the catalogue source of truth.
- Prefer editable source geometry (`.FCStd`, `.scad`, `.step`) over derived
  meshes (`.3mf`, `.stl`).
- Never label a part as dimensionally accurate, fitted, tested, safe, or
  released without linked evidence in its catalogue record.
- A publicly visible model or photograph is not automatically reusable. Record
  its licence and provenance before adding it.
- Do not commit raw scans, proprietary manuals, supplier quotes, personal data,
  credentials, or vehicle identifiers.
- Do not release braking, steering, suspension, restraint, fuel-system, wheel,
  or highly loaded engine parts without documented professional engineering
  review and an approved validation plan.
- For titanium parts, document alloy, build process, orientation, heat
  treatment, machining, inspection, fatigue assumptions, and galvanic isolation.
- Keep changes surgical and run `make check` before proposing a merge.

## Emplacement du depot

Le depot doit vivre sur un **systeme de fichiers Linux natif**, par exemple
`/home/<user>/porscheparts`, et **non sur un montage DrvFs de WSL** du type
`/mnt/c/...`.

Ce n'est pas une preference. `tests/test_917_parametric_layout_master_f30.py`
echoue systematiquement depuis `/mnt/c` sur
`test_authoring_publishes_only_wireframe_contract_with_completion_marker`, avec
un statut `failed_closed_no_output` et une erreur interne `authoring_failed:OSError`.
La cause est que l'authoring publie sa sortie par des operations POSIX relatives
a un descripteur de repertoire — creation d'un repertoire de transit puis
renommage atomique — que DrvFs ne sert pas correctement. Le script echoue donc
fermé, ce qui est le comportement voulu, mais pour une raison d'environnement et
non de donnee.

Verifie : le meme commit passe sur ext4 et echoue sur `/mnt/c`, y compris sur des
commits anterieurs a toute modification. Sur ext4 la suite complete donne
**915 tests OK**, 30 ignores, en 31 secondes contre 190 secondes sur DrvFs.

## Le nom `3dprinting993` subsiste, et ce n'est pas un oubli

Le depot s'appelle desormais `porscheparts`. Quatre familles d'occurrences de
l'ancien nom ont ete **volontairement conservees**, parce qu'elles ne designent
pas le depot :

| occurrence | pourquoi elle ne change pas |
|---|---|
| `ghcr.io/cluster2600/3dprinting993-*` et tags docker locaux | GHCR est un espace de noms distinct de GitHub : renommer le depot ne renomme aucun package. Les images sont epinglees par digest SHA-256 et verifiees par des tests de lock. |
| cles USD `3dprinting993:*` en `customData` | gravees dans les stages USD deja produits. Les renommer imposerait de tout regenerer et de rompre la comparaison avec les stages existants. |
| chemins `/opt/3dprinting993/...` | chemins **internes aux images**, partie du contrat d'image et assertes par les tests d'image. |
| URL de run GitHub Actions dans les fichiers de preuve | ce sont des **attestations historiques** : ce run a bien eu lieu sous l'ancien nom. Reecrire l'histoire falsifierait la provenance. |

Regle generale qui s'en deduit, et qui vaut au-dela du renommage :

**Ne jamais editer un fichier dont le SHA-256 est epingle par un lock ou un
contrat de preuve.** Sont concernes les `containers/*.lock.json`, leurs entrees
de recette — Dockerfiles, `.github/workflows/containers.yml`, requirements — et
tout `evidence/**`. Un simple renommage de chaine y casse la chaine de provenance,
et `make check` le detecte : c'est ce qui s'est produit le 2026-09-04, sur dix
fichiers.

## Repository language

Project documentation is written in French. Stable identifiers, schema field
names, filenames, and command-line messages remain in English.
