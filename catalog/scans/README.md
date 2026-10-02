# Registre des scans bruts

Une fiche `catalog/scans/*.json` enregistre un scan 3D brut (OBJ) resté hors
Git, identifié par chemin absolu, SHA-256, taille en octets et mtime. Le brut
(100 Mo et plus) n'est jamais copié dans le dépôt, conformément à
`AGENTS.md`.

Une fiche de scan n'est pas une fiche de source : la fiche
`catalog/sources/` porte les droits et la méthode d'accès amont, la fiche de
scan porte l'empreinte et l'état du fichier local. Quand une fiche source
existe déjà (préfixe `SRC-`), la fiche de scan la référence via
`linked_source_ids` sans dupliquer ses affirmations.

Règles :

- `path` est absolu sur l'hôte de calcul (`kali2`) ; le fichier peut ne pas
  exister sur d'autres hôtes.
- `sha256`, `bytes` et `mtime` ont été recalculés sur l'hôte le jour porté par
  `recorded_on`. Toute divergence ultérieure invalide les dérivés.
- `resolution` est une déclaration (souvent issue du nom de fichier), jamais
  une précision métrologique vérifiée, tant que le pipeline
  `containers/obj-metrology-f15` ou une mesure physique ne l'a pas établie.
- Les OBJ ne portent aucune métadonnée d'unité ; mm est une convention
  supposée, signalée dans `notes`.
- `license` et la provenance sont marqués `unknown` tant qu'aucune preuve
  n'est archivée. Ne jamais inventer.

Valider avec `python3 scripts/validate_scans.py` (couvert par `make check`).
