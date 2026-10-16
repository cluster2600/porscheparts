# Réplique 962 C 3,0 L : référence et métrologie

La référence retenue est la **962 C 3,0 L à culasses et cylindres refroidis
par eau**. Le type moteur exact, le millésime, les références de pièces et
l'exemplaire de contrôle restent à sélectionner. La fidélité ne peut donc
pas encore être chiffrée. Le présent dossier prépare leur acquisition ; il
ne fournit aucune cote Porsche et n'autorise aucune fabrication.

Le [dossier Porsche, pages 18–20](https://newsroom.porsche.com/dam/jcr:a6f33b52-c47d-47b4-98c1-7e963661f587/40%2520Years%2520Group%2520C.pdf)
décrit les ensembles cylindre–culasse en aluminium soudés par faisceau
d'électrons (« blind cylinders »), la distribution par engrenages, deux
arbres à cames par banc, les poussoirs et pastilles, et un circuit d'eau
indépendant par banc. Il décrit aussi le contrôle du volume des chambres.
Ce texte établit une architecture historique, pas les cotes de notre référence.

Les ensembles séparés montrés par le restaurateur dans
[l'analyse existante](ORIGINAL_ARCHITECTURE.md) comprennent des modifications
déclarées. Ne pas en déduire une interface démontable d'usine : établir pour
l'exemplaire choisi soudure, réparations et transformations. Ne pas sectionner
une pièce historique pour compléter le modèle. Les deux bougies des candidats
F0/4 L constituent une proposition moderne ; leur nombre et leurs axes ne sont
pas une définition OEM. Les [interfaces M64](DONOR_METROLOGY.md) concernent une
conversion distincte et ne remplacent pas cette campagne 962.

## Ensemble de référence et repère

Réunir culasse–cylindre appariés, porte-arbres, distribution, soupapes,
sièges/guides, raccords d'eau et d'huile, joints, fixations et interfaces de
carter correspondants. Identifier chaque pièce, banc et position cylindre,
sa référence et son état ; conserver les numéros identifiants privés hors Git.
La comparaison des pièces doit établir toute symétrie ou interchangeabilité.

Le métrologue établit un repère reproductible à partir de surfaces, axes et
orientation identifiés sur l'ensemble réel, puis la transformation vers le
repère moteur. Aucun datum OEM n'est supposé. Consigner température de mesure,
état libre ou assemblé, bridage et conditions de serrage connues. Séparer
déformation, usure, réparation et forme d'origine ; ne pas recalibrer un scan
sur le générateur hypothétique pour rendre les écarts artificiellement faibles.

## Contrôles à acquérir

| Zone | Acquisition proposée et résultat attendu |
|---|---|
| Extérieur et assemblage | Scan référencé et MMT : enveloppe, poches, congés, plans, registres, chaque axe de fixation et portée ; référence des fixations et chemin d'effort |
| Cylindre et chambre | Alésage, profil, hauteur d'empilage, plan de feu et surface de chambre ; volume mesuré avec soupapes et obturation définies, état et méthode traçables |
| Soupapes et allumage | Chaque axe de siège/guide, angle et position, géométrie et emmanchement ; nombre, axe, filet et portée des bougies constatés |
| Admission et échappement | Faces, fixations, axes, sections et profils internes des ports ; raccordement aux collecteurs identifiés |
| Porte-arbres et distribution | Plans et paliers, axes d'arbres et d'engrenages, entraxes, interfaces de poussoirs/pastilles et enveloppes ; calage et jeux à documenter séparément |
| Huile et eau | CT si nécessaire : connexions, sections, continuité des galeries, épaisseurs et zones non résolues ; rattachement aux réseaux du banc |
| Étanchéité et état thermique | Soudure cylindre–culasse, portées/joints réellement présents, états de surface ; matériaux et conditions thermiques nécessaires à la dilatation à établir |

MMT : machine à mesurer tridimensionnelle. Définir couverture, résolution,
étalonnage et incertitude selon le contrôle recherché. Pour un CT, conserver
reconstruction, segmentation, artefacts, zones non résolues et contrôles
indépendants accessibles ; la taille du voxel ne constitue pas une précision.
Le plan de répétabilité et les critères d'acceptation appartiennent au dossier
du métrologue. Aucune tolérance de fabrication ne se déduit d'une seule pièce
ou de la seule incertitude de mesure.

La [feuille CSV](replica-measurements.template.csv) est un index à copier sous
`work/` pour chaque session. Les résultats sont vides ; vide signifie inconnu.
Renseigner identité exacte, composant, banc, position, contrôle, caractéristique,
méthode réalisée, unité, incertitude, datums, instrument, étalonnage et preuves.
Dupliquer les lignes pour chaque axe, siège, port ou fixation. Les profils,
vecteurs, coordonnées, répétitions et transformations restent dans des rapports
référencés : une valeur scalaire ou une ligne CSV ne suffit pas à les définir.

## Maître éditable et dérivés de cylindrée

Reconstruire un maître CAO éditable de la référence mesurée : références
fonctionnelles contraintes, surfaces de chambre et de ports, réseaux internes,
interfaces de cylindre, porte-arbres et carter. Chaque contrainte doit pointer
vers une mesure acceptée ou rester explicitement inconnue. Préserver les
[études existantes](FLOW4L_STUDY.md) et leurs preuves comme études séparées.

Avant de revendiquer la fidélité, produire une carte d'écarts du maître vers
les mesures indépendantes, avec repère, couverture, incertitude de recalage,
zones masquées et critères de revue. Inspecter séparément les interfaces,
chambres et galeries ; une belle surface externe ne valide pas l'intérieur.

La course peut changer la cylindrée sans changer l'alésage de la culasse,
mais impose de vérifier piston au PMH, hauteur d'empilage, jeux, compression et
distribution. Un changement d'alésage impose une étude distincte de chambre,
plan de feu, cylindre, épaisseurs et refroidissement. Ne pas agrandir tout le
modèle : entraxes, fixations, paliers et raccords historiques restent contraints
par la référence, sauf modification explicitement identifiée et revue.
Chaque dérivé jusqu'à 4,0 L reçoit sa définition alésage/course, sa liste
d'écarts au maître et ses propres preuves mécaniques, thermiques et d'assemblage.

## Provenance et sortie de campagne

Conserver accès autorisé, propriétaire de la source, droits de mesure et de
réemploi, locateur privé, empreinte, date et décision de revue. Scans, CT,
plans propriétaires et données personnelles restent hors Git ; publier seulement
les éléments partageables. Le [registre](research.json) conserve les références
documentaires ; une photographie publique n'accorde aucun droit de reproduction.
La sortie attendue est une référence exacte identifiée, des mesures revues et
un maître inspecté. La [qualification matière](MATERIAL_QUALIFICATION.md), la
revue professionnelle et les validations physiques restent ensuite nécessaires.
