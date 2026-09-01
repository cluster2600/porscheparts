# Jumeau de référence de la culasse 935 Wolfe Classics

## Portée actuelle

Ce dossier contient la chaîne reproductible qui transforme le scan acheté en
artefacts de travail. Le fichier OBJ, les maillages dérivés et les résultats de
calcul restent hors Git. Le code et la méthode sont versionnés.

Le jumeau est actuellement un `F1_interface_proxy` : il permet la revue de
géométrie, la mesure provisoire, le contrôle de collision et la validation de la
chaîne de maillage CFD. Il ne représente pas encore une culasse 993 compatible,
fonctionnelle ou prête à fabriquer.

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
  twins/reference-935-cylinder-head/source/build_valve_variants.py \
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
PYTHON=/chemin/vers/python \
  twins/reference-935-cylinder-head/run_pipeline.sh \
  raw-scans/wolfe-classics-935-cylinder-head/original/935-xtreme-cylinder-head.obj \
  work/wolfe-classics-935-cylinder-head/pipeline
```

L'image `3dprinting993-mesh-cfd` ajoute Blender, Gmsh et OpenFOAM 13 pour les
calculs distants. Aucun scan n'est inclus dans l'image.

Une fois les volumes Gmsh générés, leur conversion et leur contrôle OpenFOAM
s'exécutent séparément :

```bash
twins/reference-935-cylinder-head/source/check_openfoam_mesh.sh \
  work/wolfe-classics-935-cylinder-head/pipeline/cfd/high_B/fluid-domain.msh \
  work/wolfe-classics-935-cylinder-head/pipeline/openfoam/high_B
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
