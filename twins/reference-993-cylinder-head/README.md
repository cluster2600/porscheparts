# Jumeau de référence de la culasse Porsche 993 Turbo (M64 cible)

## Portée actuelle

Ce dossier contient la chaîne reproductible qui transforme le scan acheté en
artefacts de travail. Le fichier OBJ, les maillages dérivés et les résultats de
calcul restent hors Git. Le code et la méthode sont versionnés.

La chaîne produit un artefact `F1_interface_proxy`, mais le niveau **vérifié**
reste `F0_reference` tant que l'échelle et les interfaces physiques ne sont pas
mesurées. Le proxy permet la revue de géométrie, la mesure provisoire, le
contrôle de collision et la validation de la chaîne de maillage CFD. Il ne
représente pas encore une culasse 993 compatible, fonctionnelle ou prête à
fabriquer.

Règle stricte de forme pour cette itération: aucune modification de silhouette
ne doit être introduite sans preuve de nécessité thermique/mécanique/massique.
Le contour externe 935/964 connu doit rester conservé tant qu'une amélioration
chiffrée démontrée (débit, thermique, tenue, usinabilité) ne prouve pas le
gain net.

## Artefacts produits

| Artefact | Usage | Limite |
|---|---|---|
| copie OBJ immuable | traçabilité du scan acheté | hors Git |
| maillage 300 000 triangles | segmentation et mesure | écart p95 de simplification 0,059 unité OBJ |
| enveloppe sans éléments externes | inspection de la culasse | coupes non fermées, classification moyenne |
| rapport des interfaces | registre, chambre, goujons et ouvertures | échelle OBJ non confirmée |
| STEP paramétrique F1 | datum CAO et contrôle d'encombrement | enveloppe simplifiée |
| STL `fit-check-only` | maquette polymère non fonctionnelle | interdit dans un moteur |
| deux domaines CFD étanches | validation Gmsh et études locales | seulement les tronçons proches des brides |
| trois proxies de soupapes STEP/STL | masse, collision et préparation de la dynamique | profils sous tête et gorges non mesurés ; STL `fit-check-only` |
| rapport `physics-readiness.json` | audit des preuves et des modèles physiques | bloque volontairement les solveurs et la fabrication si une entrée manque |

## Réingénierie et choix provisoires

`reengineering-contract.json` relie la géométrie aux conservations de masse,
quantité de mouvement et énergie, à la conduction thermique, à la
thermoélasticité, à la dynamique de distribution et à la fatigue. Il décrit
aussi le front de Pareto : débit corrélé, température, déformation des sièges,
fatigue, masse mobile et capabilité de fabrication.

La présélection actuelle, qui n'est pas une libération de production, est :

  - culasse : AlSi10Mg LPBF comme référence thermique et industrielle, confronté
  à AlF357 pour la ductilité et les charges dynamiques ;
- soupape d'admission : Ti-6Al-4V forgé ou usiné, revêtement et extrémité
  qualifiés, afin de réduire la masse mobile ;
- soupape d'échappement : INCONEL 751 en barre ou forge, explicitement conçu
  pour ce service chaud ;
- ressort : acier ultra-propre chrome-silicium trempé à l'huile, nitruré et
  grenaillé en plusieurs passes, fourni par un spécialiste.

Les soupapes, ressorts, sièges, guides et filetages sont des composants rapportés
et qualifiés. Ils ne font pas partie d'une impression monobloc. Leur
dimensionnement reste bloqué par le profil de came, les masses, la pression gaz,
le régime, les jeux et les températures réels.

La branche `4v_concept` compare deux admissions et deux échappements à la
`2v_scan_baseline`. Elle reste séparée de la géométrie mesurée et doit gagner
sur un front de Pareto complet : débit, rendement volumétrique, masse mobile,
pertes de ressort, température et contrainte entre sièges, encombrement,
usinage et évacuation de poudre.

## Soupapes et variante titane

Le pipeline génère maintenant trois géométries paramétriques F1 : admission
993 de 49 mm, échappement Carrera de 42,5 mm et échappement Turbo de 43,5 mm,
toutes avec une queue déclarée de 8 mm. Les valeurs publiques sont conservées
avec leur niveau de preuve ; la longueur de l'admission reste une hypothèse de
109 mm dérivée d'un encombrement produit de 110 mm.

Le modèle compare la masse du même volume avec une densité d'acier générique,
du Ti-6Al-4V et, pour l'échappement, de l'INCONEL 751. La documentation Special
Metals décrit précisément le 751 comme un alliage destiné aux soupapes
d'échappement, fourni en barre et traité par précipitation. Elle ne valide pas
une route LPBF. La variante titane est donc prioritaire pour l'étude de
l'admission ; côté échappement elle reste un cas comparatif à challenger par les
températures, l'oxydation, l'usure et la fatigue à chaud.

```bash
docker run --rm --platform linux/amd64 --entrypoint /opt/venv/bin/python \
  -v "$PWD:/workspace" -w /workspace \
  ghcr.io/cluster2600/3dprinting993-mesh-cfd@sha256:a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f \
  twins/reference-993-cylinder-head/source/build_valve_variants.py \
  work/valve-variants-f1
```

Les STEP sont des masters de simulation éditables. Les STL portent la mention
`fit-check-only` et ne doivent jamais être montés dans un moteur. Une soupape
fonctionnelle exige au minimum la gorge de clavette, le rayon sous tête, la
marge, l'angle et la largeur de siège, les jeux de guide, le profil de came, les
courbes de ressort, les masses mobiles, le traitement, la finition et une
validation dynamique et thermomécanique.

La version à 100 000 triangles est rejetée pour la métrologie : son écart p95
mesuré atteint environ 6,15 unités OBJ. Elle ne peut servir qu'à un aperçu très
grossier.

## Exécution locale

L'environnement Python doit fournir `trimesh`, `pymeshlab`, `scikit-image`,
`build123d`, `gmsh`, `numpy` et `scipy`.

```bash
cd /Users/maxime/projects/3dprinting993
PYTHON=/usr/bin/python3 \
  twins/reference-993-cylinder-head/run_pipeline.sh \
  /Users/maxime/projects/3dprinting993/raw-scans/993-cylinder-head/original/scan.obj \
  work/993-cylinder-head/pipeline
```

> Sans scan 993 dans le dépôt, on exécute temporairement la même chaîne sur le proxy existant : `work/993-cylinder-head-fast/input/935-xtreme-cylinder-head-working-copy.obj`
> pour établir une base de discussion, mais **ce n’est pas une version validée**.

L'audit de readiness peut être relancé sans retraiter le maillage lourd :

```bash
python3 twins/reference-993-cylinder-head/source/build_physics_readiness.py \
  --pipeline work/993-cylinder-head/pipeline \
  --contract twins/reference-993-cylinder-head/reengineering-contract.json \
  --inputs twins/reference-993-cylinder-head/engineering-inputs.template.json \
  --output work/993-cylinder-head/pipeline/reports/physics-readiness.json
```

Le fichier `engineering-inputs.template.json` reste volontairement vide. Une
preuve externe n'est acceptée que par chemin et empreinte SHA-256 ; trois cotes
physiques cohérentes sont requises pour valider l'échelle.

L'image `3dprinting993-mesh-cfd` ajoute Blender, Gmsh et OpenFOAM 13 pour les
calculs distants. Aucun scan n'est inclus dans l'image.

Une fois les volumes Gmsh générés, leur conversion et leur contrôle OpenFOAM
s'exécutent séparément :

```bash
twins/reference-993-cylinder-head/source/check_openfoam_mesh.sh \
  work/993-cylinder-head/pipeline/cfd/high_B/fluid-domain.msh \
  work/993-cylinder-head/pipeline/openfoam/high_B
```

Ce contrôle vérifie la topologie et la géométrie du maillage. Il ne constitue
pas encore une solution CFD et n'invente aucune condition aux limites.

## Interfaces provisoires

Les valeurs suivantes sont exprimées en unités OBJ ; les millimètres ne sont
pas encore établis :

- registre extérieur visible : diamètre 113,53 ;
- épaulement de chambre à la coupe retenue : diamètre 90,81 ;
- motif des quatre passages de goujons : environ 86,74 × 85,92 ;
- diamètre moyen visible des passages : 10,74 ;
- ouverture du conduit côté B bas : environ 40 à 45,6 ;
- ouverture du conduit côté B haut : environ 41,4 à 42,6.

Ces ajustements décrivent le maillage visible. Les résidus d'ajustement ne sont
pas une incertitude métrologique complète. Une cote physique est nécessaire
pour valider l'échelle et un scan ne révèle pas automatiquement les galeries
d'huile, filetages, sièges ou alésages de guides.

## Comparaison 993

Le dépôt ne contient encore aucune géométrie 993 vérifiée pour le motif des
goujons, les registres de cylindre, les brides ou les conduits. La valeur de
100 pour l'alésage 993 provient d'une transcription OCR encore non vérifiée et
ne correspond pas au même élément que le registre de 113,53 ou l'épaulement de
90,81. Aucune compatibilité ne peut donc être conclue.

## Verrous de sécurité

- Ne jamais fabriquer une version moteur depuis le STL de contrôle.
- Ne jamais extrapoler les galeries internes à partir de la surface externe.
- Exiger une revue d'ingénierie professionnelle avant toute culasse chargée.
- Associer toute version métal à une matière, un procédé, un traitement, une
  orientation, un usinage, un plan de contrôle et une traçabilité matière.
- Conserver le maillage brut et tous ses dérivés hors Git conformément à
  l'instruction du propriétaire, même si celui-ci confirme une licence ouverte
  et réutilisable dont l'identifiant standardisé reste à archiver.
- Ne pas libérer une soupape métal depuis les proxies F1 ; exiger une définition
  complète, une qualification matière/procédé et des essais de distribution à
  chaud sous revue d'ingénierie professionnelle.
