# Étude « Fan+Drive » — compte rendu intermédiaire (relance requise)

Date : 2026-09-27. Lane `fan_scan_study` INTERROMPUE (expiration du délai) avant conclusion.
Ce document consigne les hypothèses et données intermédiaires pour la reprise.

## Actif analysé

- `Fan+Drive+0.21mm.obj` — sha256 `6c0b12d4…`, 1,26 M sommets, 105 MB, importé le 2026-09-27
  dans `/home/lolman/imports/mac-obj` (provenance d'acquisition : à documenter — seule la
  résolution de maillage « 0.21 mm » est affirmée par le nom de fichier).
- Enveloppe : 325.2 × 398.6 × 450.1 « unités » (OBJ sans métadonnée d'unité, vérifié : aucun
  commentaire d'en-tête). Units = mm **supposés**, non confirmés.

## Données intermédiaires (JSON sur disque, `work/obj-intake-20260927/`)

- `fan-drive-extract.json`, `fan-drive-slab-metrics.json` (métriques de slabs angulaires),
  `fan_drive_features.py` (pipeline reproductible), `triage_obj.py`, `reports/obj-intake.json`.
- Pignon à denture : OD ≈ 127.6 mm (hauteur de denture 67.9 mm).
- Poulie : r_max ≈ 127.8 mm.
- Harmoniques angulaires sur le slab inférieur : pics aux harmoniques **4 à 7 selon
  l'anneau/le seuil choisis** — non concluants (occlusion par les brides de carter).

## Hypothèses à tester à la reprise

1. Le nombre de pales réel (la charte dit « 11 pales prévues », sans aucune preuve documentaire).
2. Les diamètres de poulie primitif/ mené (rapport ≈ 1:1,6 publié au niveau A Carrera — la
   géométrie du scan doit reproduire ce rapport si l'échelle est la bonne ; c'est le meilleur
   test d'auto-calibration).
3. Confirmer qu'il s'agit bien d'un ensemble M64/60 (repères d'usinage, refs) avant d'en tirer
   une cote.

## Verdict

Le comptage de pales par voie logicielle reste **OUVERT** (M64-ACQ-0005) ; rien dans ce
fichier n'est une mesure confirmée. Reprise : exécuter `fan_drive_features.py` sur le slab
supérieur dégagé, caler l'échelle sur le rapport de poulies, puis consigner un verdict.
