# M64 — G1, squelette paramétrique CadQuery

14 septembre 2026. Code : [`m64_head_skeleton.py`](../../twins/m64-cylinder-head/source/parametric/m64_head_skeleton.py),
paramètres : [`parameters.json`](../../twins/m64-cylinder-head/source/parametric/parameters.json),
preuves : [`evidence/g1-parametric-20260914/`](../../twins/m64-cylinder-head/evidence/g1-parametric-20260914/manifest.json).

**Ce n'est ni une géométrie maître ni une autorisation de fabrication**
(`master_geometry: false`, `manufacturing_authorized: false`).

## Contenu

Un cylindre. On y trouve le bloc, le centrage sous le plan d'étanchéité et un
dégagement de portée. La chambre est un volume simplifié. S'y ajoutent quatre
lamages de siège et quatre alésages de guide inclinés (2 admission, 2
échappement), le puits de bougie central, quatre trous de goujons et deux
alésages porte-arbres. Le repère est décrit dans `parameters.json`.

## Règle de provenance (fail-closed)

- `sourced` : le paramètre doit citer un `contract_path` non nul, porté par une
  entrée à source enregistrée et localisateur, avec la même unité et une valeur
  identique. Un chemin vers `critical_interfaces` exige le statut `found`.
- `unsourced` : il s'agit d'un placeholder. Il ne peut citer aucun chemin, et il
  est refusé dès que le contrat source l'interface correspondante (`found`).
- Toute autre provenance, valeur modifiée ou source retirée est refusée.

## Résultat de génération

| Élément | Valeur |
|---|---|
| Paramètres sourcés | 3 : Ø de chambre = alésage de 100 mm (P3, référence historique) ; soupapes de 40 / 33 mm (S2, benchmark Swindon) |
| Paramètres non sourcés | **19**, listés dans le manifeste, dont registre, portée, goujons, axes et inclinaisons des soupapes, guides, bougie et arbres |
| BRepCheck_Analyzer | valide |
| Volume | 1 074 651,8 mm³, **sans signification physique** (dimensions du bloc non sourcées) |
| Sorties | STEP (368 Ko), coupe SVG XZ à y = `valve_y_offset`, manifeste avec SHA-256 (STEP, coupe, paramètres, contrat, générateur) |

L'en-tête STEP contient un horodatage : l'empreinte change à chaque régénération.
Le manifeste renvoie à l'exemplaire versé.

Le diamètre de 14 mm du puits de bougie reste **non sourcé**. Le filetage M14 × 1,25
n'est qu'un fait partiel du contrat : 993 Carrera, table non relue.

## Tests

`tests/test_m64_g1_parametric_skeleton.py` couvre la génération valide et non
maître, le refus d'une valeur sourcée modifiée, le refus d'une source retirée du
contrat, le refus d'un placeholder présenté comme sourcé et la cohérence de la liste
des paramètres non sourcés.

## Suite

Remplacer les placeholders à mesure que les mesures de la
[liste G0](M64_G0_INTERFACE_CONTRACT_20260914.md) entrent au contrat. Le recalage
sur le scan reste à faire quand il sera disponible.
