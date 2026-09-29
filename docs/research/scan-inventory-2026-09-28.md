# Inventaire des scans 3D — intake 2026-09-28 (Wave-1)

Registreur : `catalog/scans/` (nouveau registre, voir son README). Les bruts
(100–202 Mo) restent hors Git, enregistrés par chemin absolu + SHA-256 + taille
+ mtime, recalculés sur l'hôte `kali2` le 2026-09-28 avec `sha256sum`.
Le triage géométrique préalable est dans
[obj-scan-intake-2026-09-27.md](obj-scan-intake-2026-09-27.md) ; la présente
page enregistre l'empreinte et positionne chaque scan comme preuve potentielle.

Aucun de ces scans n'est une mesure certifiée : ce sont des entrées brutes
`SINGLE_SOURCE`. Une cote n'existe qu'après promotion par le pipeline
`containers/obj-metrology-f15` (identité, échelle, segmentation) puis une
acquisition `M64-ACQ-*` avec incertitude déclarée. Les OBJ ne portent aucune
unité ; mm est une convention supposée partout.

## Inventaire complet (5 fichiers, 4 payloads uniques)

| Fiche | Payload | Octets | mtime | Déclaré | Piste | État d'enregistrement |
|---|---|---|---|---|---|---|
| `SCAN-FAN-DRIVE-0P21MM` | `6c0b12d4…` | 105 090 339 | 2026-09-27 | 0,21 mm (nom de fichier) | moteur / refroidissement | **nouvelle fiche**, aucune source amont — provenance et licence **inconnues** |
| `SCAN-917-ENGINE-CASE-W-CYL-0P5MM` | `428c4143…` | 107 128 223 | 2026-08-31 | 0,5 mm (page vendeur + nom) | moteur / carter-cylindres | déjà source `SRC-LOCAL-917-ENGINE-CASE-CYLINDERS-SCAN` et au pipeline 917 ; fiche = empreinte des **deux chemins identiques** |
| `SCAN-935-XTREME-CYLINDER-HEAD` | `4623d5d3…` | 104 598 077 | 2026-08-31 | inconnu | moteur / culasse-soupapes | déjà source `SRC-WOLFE-CLASSICS-935-BILLET-CYLINDER-HEAD-SCAN`, au pipeline `reference-935-cylinder-head` |
| `SCAN-964-WIDEBODY-UNDERSIDE` | `f3979091…` | 210 972 101 | 2026-09-25 | inconnu | carrosserie | **nouvelle fiche**, provenance et licence **inconnues** |
| (2ᵉ chemin du payload 917) | `428c4143…` | 107 128 223 | 2026-08-31 | idem | — | `Library/Mobile Documents/com~apple~CloudDocs/Downloads/917+engine+case+w+cyl+0.5mm.obj` — **byte-identique** au raw-scan 917 : copié, non scanné deux fois |

Correction d'hypothèse d'intake : le fichier iCloud `917+engine+case+w+cyl+0.5mm.obj`
n'est **pas** une variante haute résolution distincte ; son SHA-256 est celui
du scan 917 déjà référencé par les workpackages 917 (F11 `EXPECTED_SHA256`,
F15, F17). Il est enregistré comme `other_paths` de la fiche 917, sans doublon
de fiche source. (Note : le chemin réel sous iCloud est
`…/com~apple~CloudDocs/Downloads/917+engine+case+w+cyl+0.5mm.obj`.)

## Ce que chaque scan prouve — et ne prouve pas

| Scan | Peut prouver (après promotion F15) | Ne prouve pas |
|---|---|---|
| Fan Drive 0,21 mm | Géométrie brute de l'entraînement du ventilateur : positions/Ø des poulies et de la denture, hauteur axiale, implantation → nourrit `M64-ACQ-0005` (géométrie ventilateur, zone M64-Z-CL) et calibre l'étude aéraulique F2 (`simulation/993-fan-baseline`) | Nombre de dents (déjà non résolu au pas de 0,21 mm, couverture angulaire 0,03–0,24), rapport d'étage concluant (poulie libre + courroie élastique dans le champ : ratio observé 1,7–2,0 vs 1:1,6 `FACT_public`, non concluant), échelle, débit d'air |
| Carter 917 + cylindres | Référentiel de carter/cylindres à plat-12 pour revue de géométrie et métrologie comparative ; déjà consommé par le jumeau 917 (F11/F15/F17) | Identité variante 917, précision réelle des 0,5 mm déclarés, compatibilité 993/M64, interfaces fonctionnelles |
| Culasse 935 | Vérité terrain d'une culasse billette air-cooled : interfaces, registre, chambre, goujons ; alimente le jumeau `reference-935-cylinder-head` (déjà F1_interface_proxy, soupapes paramétriques F1) | Compatibilité 993, matière, masse, précision ; STL dérivés = `fit-check-only` |
| Soubassement 964 | Forme générale du soubassement widebody, éventuel référentiel d'environnement de montage côté caisse (piste body, à comparer `SRC-CARGEOMETRY-993-BODY`) | Cotes : 176 corps non triés, échelle non vérifiée, provenance non élucidée ; rien pour le moteur |

## Sous-systèmes moteur gagnant une vérité terrain mesurée

- **Refroidissement (ventilateur)** : Fan Drive 0,21 mm — premier scan dédié du
  circuit de refroidissement M64 ; débloque potentiellement `M64-ACQ-0005`
  (aujourd'hui bloqué : géométrie de roue non publiée, seul le débit 1 010 l/s
  @ ≈6 100 tr/min est public).
- **Cylindres / culasses** : culasse 935 (au pipeline, F1) et carter+cylindres
  917 (référence extérieure carter) ; le 935 est le candidat direct pour la
  chaîne culasse/M64, le 917 reste une référence morphologique.
- **Carrosserie** (hors moteur) : soubassement 964, non trié.

## Prochaines étapes de métrologie (pipeline existant `containers/obj-metrology-f15`)

1. **Fan Drive** — exécuter le pipeline F15 sur le brut monté en lecture seule
   (`--source …/Fan+Drive+0.21mm.obj`, contrat à créer sur le modèle de
   `twins/reference-917-engine/scan-segmentation-f15.json`) : empreinte,
   bornes, composantes. Puis coupe plane re-orientée perpendiculairement à
   chaque axe (plan local ajusté), seuillage crête/valley pour le comptage de
   dents, et séparation poulie libre / courroie avant tout ratio. Sortie
   attendue : promotion `M64-ACQ-0005` au statut F2 avec incertitude déclarée.
   Prérequis non technique : élucider provenance et licence du scan.
2. **935 culasse** — déjà passée F15 ; prochaine étape documentée :
   métrologie d'interfaces sur section calibrée et relecture visuelle de
   l'unité (l'enveloppe « probablement mm » reste non confirmée).
3. **917 carter** — relancer F15 seulement si un nouveau contrat de segmentation
   sémantique l'exige ; l'intégrité F11 est déjà scellée sur `428c4143…`.
4. **964 soubassement** — tri par composant avant toute fiche d'acquisition ;
   classer en piste body, ne pas le faire entrer dans les contrats moteur.
5. Pour chaque fiche dont `rights.license = unknown` (Fan Drive, 964) : ne rien
   publier, redistribuer ni revendre tant que l'origine du scan n'est pas
   documentée. Marqué honnêtement inconnu, pas inventé.

## Intégrité et traçabilité

- `sha256sum` (coreutils, hôte kali2) sur les 5 chemins, 2026-09-28 ;
  tailles et mtime via `stat`. Les deux duplicats 917 vérifiés égaux octet à
  octet par empreinte commune.
- Les empreintes 935 et 917 recoupent les `EXPECTED_SHA256` des
  `prepare_scan.py` des jumeaux — aucune dérive depuis l'entrée au pipeline.
- Validation : `python3 scripts/validate_scans.py` (nouveau, couverts par
  `make check`) — 4 fiches valides.
