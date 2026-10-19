# Planche 24 — champs mécaniques du congé C1

La planche représente les deux calculs linéaires C1 réellement clos : appuis rigides et appuis K1000. Les charges sont Fz = −4 000 N et My = +850 000 N·mm. K1000 désigne 1 000 N/mm **au total par œil et par axe**, répartis sur les nœuds de chaque œil.

| Cas | Déplacement nodal maximal | Contrainte de von Mises maximale aux points d’intégration |
|---|---:|---:|
| Rigide | 2,794104 mm | 907,278068 MPa |
| K1000 | 18,171491 mm | 2 663,075178 MPa |

Toutes les facettes de frontière du maillage réel sont utilisées. La couleur de chaque facette provient du maximum des quatre points d’intégration de son élément ; les maxima globaux sont conservés séparément dans les marqueurs et tableaux. Les deux champs de contrainte partagent une échelle commune. La déformée est affichée à **×1**, avec une caméra et des axes communs. Les facettes linéaires utilisent les coins des éléments T10 ; elles ne représentent pas une interpolation courbe des faces quadratiques déformées.

Le maximum global des deux cas est l’élément 84037, IP1. Les valeurs non arrondies, coordonnées et tous les ex æquo restent dans les données et reçus. La comparaison avec l’ancienne géométrie est descriptive ; aucune convergence des contraintes ni limite admissible de résistance n’est établie ici. Le maître est le BREP C1 ; son échange STEP reste refusé.

## Dessin et preuve de rejeu

[PNG](carrier-C1-contraintes-deplacements.png), [SVG](carrier-C1-contraintes-deplacements.svg) et [PDF](carrier-C1-contraintes-deplacements.pdf) sont les trois exports définitifs de présentation 002. La racine a vu le PNG et la page 1 du PDF : vues globales dégagées et zooms séparés. Le premier dessin 001 et sa réserve de disposition restent conservés dans le miroir historique.

Le [rejeu réellement clos](verification/root-terminal-review-001.json) a restauré 186 membres des archives C1, ajouté 44 petits fichiers du miroir, puis exécuté une seule fois le renderer figé depuis `/`. Les trois exports sont **octet pour octet identiques** au dessin 002 relu. Les quatre ensembles complets de contrôles, maxima, caméra et runtime sont aussi égaux. L’appel possédé a retourné 0, son enfant a été récolté et le groupe est vide : 18,371726 s au total, 17,370262 s dans le wrapper, pic RSS de 753 942 528 octets. Aucun solveur, maillage ni noyau CAO n’a été relancé.

Les 56 fichiers testés et leur [manifeste 003](sources/manifest-003.json) sont copiés **sans modification** sous `sources/`. Les README de préparation y gardent leur statut historique non armé ; le présent README décrit la publication et le résultat réellement clos. Les plans, journaux, commandes, GO et reçus bruts sont conservés sous `verification/`. `archive.json` inventorie toute cette capsule, hors lui-même, avec taille, empreinte et origine de chaque copie.

## Dépendances obligatoires

Cette capsule dépend des trois archives et du `restore.py` inchangé de la [capsule C1](../../design-20261016/native-C1-20261017/README.md), manifeste `faa9069cc12e4ac69c784ab4af50e74de65c0c26403172721c500b8d5641e1d1`. Elle ne duplique **aucun NPZ, INP, ZIP ni runtime**. Son rejeu n’est donc pas autonome sans la capsule C1.

Le runtime existant est lié par ses chemins absolus : 211 fichiers du plan figé, plus 8 fichiers Pillow observés lors d’un import séparé, sans installation. Le wrapper revérifie les 219 empreintes avant/après et recapture les modules NumPy, Matplotlib et Pillow après les trois exports : les 217 modules effectivement chargés appartiennent à cette autorité. Cette fermeture ne prétend pas inventorier tous les fichiers de Python ou du système.

## Reproduire le dessin

Depuis le dépôt, choisir un répertoire de sortie **absent**. Le script suivant crée un nouveau plan à partir du plan historique : seuls les chemins de dépendance, de sortie et du GO conservé sont adaptés. Le manifeste, les sources et les paramètres restent inchangés.

```sh
python3 - <<'PYPLAN'
from pathlib import Path
import hashlib, json
repo = Path.cwd().resolve()
cap = repo / 'parts/993-eng-carrier-0001/source/progress-figures-20261016/C1-fields-20261017'
plan = json.loads((cap / 'verification/plan-003.json').read_text())
plan['dependency_directory'] = str(repo / 'parts/993-eng-carrier-0001/source/design-20261016/native-C1-20261017')
plan['output_directory'] = str(repo / 'work/C1-fields-replay-NEW')
plan['root_GO'] = str(cap / 'verification/root-review-GO-003.json')
path = repo / 'work/C1-fields-replay-NEW-plan.json'
with path.open('x') as stream:
    json.dump(plan, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(path)
print(hashlib.sha256(path.read_bytes()).hexdigest())
PYPLAN
```

Avec le chemin et le nouveau SHA affichés, le prévol ne restaure ni ne dessine :

```sh
/Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10 -B \
  parts/993-eng-carrier-0001/source/progress-figures-20261016/C1-fields-20261017/sources/replay_v3.py \
  preflight work/C1-fields-replay-NEW-plan.json --plan-sha256 NOUVEAU_SHA
```

L’appel au wrapper impose nice 10 et un thread BLAS ; le renderer figé place lui-même son répertoire courant à `/` :

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
/usr/bin/nice -n 10 /Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10 -B \
  parts/993-eng-carrier-0001/source/progress-figures-20261016/C1-fields-20261017/sources/replay_v3.py \
  replay work/C1-fields-replay-NEW-plan.json --plan-sha256 NOUVEAU_SHA
```

Ce dernier appel conserve les bornes internes : phase de 150 s avec réserve de 95 s pour le dessin, CPU initial 140–141 s puis 90–91 s dans le renderer. La preuve historique ajoute une supervision de groupe de 180 s, grâces 10 + 10 s ; elle n’est pas implicitement recréée par l’appel direct ci-dessus. Son [source exact](verification/work/carrier-process-20261017/source010-exposure-preflight-003/supervise.py) et son [plan exécuté](verification/launch-plan-003.json) sont conservés. Pour une nouvelle campagne possédée, ce même superviseur doit recevoir un plan local aux chemins rebasés, aux empreintes complètes et aux sorties neuves ; ses gardes de racine et de groupe restent obligatoires.

Le rejeu vérifie les entrées restaurées et leurs empreintes, le miroir, la dépendance et le runtime avant/après. Il refuse tout écrasement ou collision et exige les trois empreintes définitives. Les archives C1 permettent la réanalyse mécanique séparée ; ce dessin ne relance aucune analyse mécanique.
