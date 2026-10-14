# Kit 962 : campagne d'interfaces du donneur, gate G1

**Cible confirmée : 1 000 ch métriques au vilebrequin, banc puis piste.**
Le donneur reste à identifier ; le M64/60 est un candidat, pas une sélection.
Ce dossier prépare la mesure. Il ne contient aucune nouvelle cote Porsche.

Le [contrat M64 existant](../m64-cylinder-head/interface-contract.json) et son
[validateur documentaire](../m64-cylinder-head/validate_interface_contract.py)
restent les références pour les interfaces M64. Leur vérification le
12 octobre 2026 laisse huit interfaces critiques incomplètes, la variante
non sélectionnée et quatre preuves de qualification absentes. Le
[contrat 962 F0](interface-contract.json) décrit une autre référence : ses
cotes hypothétiques ne doivent pas être transférées au donneur.

## Pièces et repères avant la mesure

Identifier type moteur exact, millésime, banc, position cylindre, références
de carter/cylindre/culasse/porte-arbres et modifications déjà présentes.
Conserver les identifiants personnels et numéros du véhicule hors Git.
Rapprocher les références du [registre documentaire M64](../../docs/reports/M64_INTERFACE_SOURCE_REGISTER.md).
Une 964 Turbo 3.3 ne doit pas être assimilée à un M64 de Turbo 3.6.

Présenter un ensemble apparié carter–cylindre–culasse–porte-arbres, plus les
joints et pièces de distribution correspondants. Documenter état, usure,
réparations et démontage ; une mesure sur une pièce usée n'est pas une
tolérance de fabrication. Relever chaque pièce/banc avant de conclure à une
symétrie ou à l'interchangeabilité.

Le métrologue doit définir un repère reproductible : surface de référence,
axe de registre/cylindre et orientation donnée par une caractéristique
identifiée. Ce sont des **repères à établir**, pas des datums OEM connus.
Consigner transformation vers le repère d'assemblage et température de mesure.
Ne pas aligner le scan à l'œil sur le F0.

## Feuille de mesure et méthode

La [feuille CSV](donor-measurements.template.csv) est un index des contrôles,
à copier sous `work/` pour chaque pièce/session. Les champs de résultat sont
vides. Dupliquer chaque ligne pour chaque goujon, axe, port, cylindre ou
point réellement contrôlé ; `feature_instance` doit lever toute ambiguïté.
Enregistrer les répétitions brutes dans `raw_evidence_ref`, pas seulement une
moyenne. Déclarer unité, instrument, étalonnage, méthode, incertitude et état
de revue. Une cellule vide reste une inconnue, jamais zéro.

| Famille d'interface | Acquisition proposée | Livrable à obtenir |
|---|---|---|
| Goujons et fixation | MMT sur carter, cylindre et culasse appariés | Chaque axe et position dans le repère, filet/engagement, faces d'appui ; référence du goujon |
| Registre et plan de feu | Alésomètre/MMT, profondeur et profil | Diamètres, profondeur, portée, rainure/joint, forme et état de surface |
| Porte-arbres/distribution | MMT et relevé de l'ensemble | Axes, entraxes, paliers, plans, arrivée chaîne/engrenages, chemin d'huile et enveloppe |
| Huile | Relevé externe puis CT si intérieur inaccessible | Positions, sections et connexions alimentation/retours ; aucun débit déduit d'un diamètre |
| Admission/échappement | MMT, joints et scan référencé | Axes, faces, fixations, enveloppes et sections des ports |
| Sièges/guides/bougies | Métrologie de la référence puis dessin fournisseur | Axes et emmanchements de la pièce 2V ; nouveaux axes 4V/double allumage à concevoir séparément |

MMT signifie machine à mesurer tridimensionnelle. Le choix des instruments
et leur incertitude doivent convenir aux tolérances recherchées. Un pied à
coulisse peut contrôler une échelle ; il ne remplace pas une mesure d'axes.
Trois reprises indépendantes au minimum par dimension critique constituent
un premier contrôle de répétabilité, sans fixer à elles seules l'incertitude.

La cotation fonctionnelle et les tolérances du nouveau dessin doivent être
établies par le motoriste/concepteur : ne pas utiliser l'incertitude de mesure
comme tolérance, ni reconstruire une tolérance à partir d'un seul donneur.

## CT et raccordement au jumeau

Si un CT est nécessaire, demander couverture, résolution et incertitude
évaluée, segmentation, données natives et surfaces, avec droits de réemploi
précisés. Comparer au moins trois caractéristiques accessibles mesurées
indépendamment, réparties dans le volume ; une taille de voxel ne prouve pas
l'exactitude. Tracer artefacts, surfaces non résolues et orientation montée.
Le CT d'une culasse 2V renseigne ses interfaces et passages d'origine, pas
la faisabilité d'une nouvelle chambre 4V et de son circuit d'eau.

Conserver scans et rapports bruts dans un espace privé autorisé. Publier
uniquement les résultats partageables, locateurs, empreintes et décisions.
Le [modèle de fiche de mesure existant](../../catalog/templates/measurement-record.json)
peut servir aux dimensions scalaires, après remplacement de **tous** ses
exemples. Les coordonnées, axes, profils et incertitudes de recalage demandent
un rapport métrologique propre ; le CSV seul ne les valide pas.

Pour le bas moteur, compléter la hauteur d'empilage, la position du piston au
PMH, les registres du carter et l'entraxe des cylindres. La revue de conservation
du carter exige aussi paliers, sections porteuses, fixation des goujons,
vilebrequin/bielles/pistons exacts et état après inspection. La feuille culasse
ne constitue pas à elle seule un dossier de résistance du bas moteur.

Une acquisition acceptée alimente le contrat du **donneur exact**, puis un
nouveau modèle contraint, inspecté indépendamment. Le générateur F0 et ses
empreintes restent conservés. Le chemin d'effort à vérifier est chambre/plan
de feu → cylindre et fixation → carter, avec effets de la précharge et de la
dilatation ; un couple de serrage ne suffit pas à connaître la précharge.

## Sortie de G1

G1 exige identité du donneur, interfaces revues avec sources et tolérances,
repère commun, incompatibilités explicites et décision de conservation du
bas moteur. Les charges de combustion, températures, précharge et durée de
vie doivent être fournies pour la revue mécanique ; 1 000 ch ne les définit
pas. Réussir une fiche ou le validateur documentaire n'autorise ni fabrication
ni essai moteur. La [qualification matière](MATERIAL_QUALIFICATION.md) et
les gates suivantes du [programme](KIT_962_PROGRAMME.md) restent ouvertes.

Ce dossier n'envoie aucune demande à un laboratoire et ne commande ni pièce
ni CT. La sélection et l'accès au donneur restent à confirmer.
