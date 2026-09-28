# Reprise du ventilateur à partir des références de pièces

Recherches et reconstruction du 28 septembre 2026. Cible conservée : **993 Turbo
M64.60 avec alternateur PMB / Classic Retrofit 240 A**. Les quatre photographies
mélangent des variantes ; elles ne définissent pas un assemblage unique.

[Voir les quatre vues techniques](results/reference/reference-review.png) ·
[Télécharger la référence OpenUSD](results/reference/reference.usdz) ·
[Registre des sources et des inconnues](reference-research.json) ·
[Paramètres éditables PicoGK](source/picogk-reference/reference.json)

![Face, arrière, coupe et éclaté du rotor reconstruit](results/reference/reference-review.png)

## Ce qui a été recommencé

Le rotor est reconstruit séparément du modèle rejeté : **11 pales**, cuvette
ouverte à l'arrière, **12 fenêtres de ventilation**, nervures du fond et trois
perçages de fixation. Le moyeu à roulement est une pièce distincte. Les nombres
de pales et de fenêtres sont des observations des photographies FVD, pas des
cotes tirées d'un plan. Le catalogue Porsche ORIGINALE distingue lui aussi les
rotors Turbo et Carrera.

La source C# produit deux volumes PicoGK. La scène OpenUSD porte leurs identités
et conserve des composants explicitement non reconstruits pour le carter,
l'alternateur PMB, le cône, la petite turbine et l'entraînement. Elle n'intègre
**aucun ancien champ CFD ou thermique**. Il s'agit d'une reconstruction partielle
de référence, pas encore du jumeau complet demandé.

Le diamètre nominal de travail de 245 mm est une interprétation de l'enveloppe
commerciale FVD. La profondeur de cuvette, le pas, les cordes, les épaisseurs,
les rayons, les entraxes et les ajustements restent des hypothèses visibles
dans le fichier de paramètres. Les interfaces internes du roulement ne sont
pas reproduites. La profondeur totale publiée de 87 mm ne renseigne pas à elle
seule la profondeur de pale : elle n'a pas été utilisée comme telle.

## Identification et nomenclature

Le PET Porsche, illustration **105-00**, pages PDF **77–78**, distingue :

| Variante | Rotor | Carter |
|---|---|---|
| Carrera | 96410601531 | 99310666701 / 99310666703 |
| Turbo M64.60 | 96410601521 / 96410601522 | 99310666750 |

Références de la planche PET pertinentes au montage Turbo, à confirmer selon
la version de véhicule et l'entraînement finalement retenu. Les anciennes et
nouvelles références ne sont pas présentées comme des pièces à empiler ensemble.

| Position PET | Référence(s) | Fonction / information publiée |
|---|---|---|
| 1 | 99310603500 | capteur |
| 2 | 96410631502 | support |
| 3 | 99907200509 / 99907200501 | deux fixations M6 × 12, intitulé hexagon nut dans PET |
| 4 | N0147432 / 90006701203 | vis M6 × 30 |
| 5 | 99310666750 | carter Turbo |
| 6 | 99310625150 | sangle Turbo |
| 7 | 90006715202 | vis M8 × 55 |
| 8 | 96410627300 / 96410627301 | deux pions |
| 9 | 96410601522 | rotor Turbo, ancien suffixe 21 |
| 10 | 99310650950 / 99310651050 | demi-poulies ventilateur Turbo |
| 11 | 96410651701 | cales |
| 12 | 90097600401 | trois vis M6 × 30 |
| 13 | 99919234350 | courroie 9,5 × 760 |
| 14 | 99919237350 | courroie 9,5 × 753 ; ancienne 37250 en 757, note 7/97 |
| 15 | 99310626800 / 99310626801 | demi-poulies alternateur |
| 16 | 96410626830 / 96410626832 | cales 0,5 / 0,7 mm selon montage |
| 17 | 96410651530 | douille |
| 18 | 96410621132 | deux douilles |
| 19 | 93060304101 | cône arrière |
| 20 | N01152427 | quatre rondelles A6,4 |
| 21 | 90091001009 | quatre écrous VM6 |
| 22 | 90003401302 | écrou BM16 × 1,5 |
| 23 | 92860304501 | petite turbine alternateur |
| 24 | 90003400302 | écrou BM10 |
| 25 | 96410605131 | moyeu à roulement, ancien suffixe 30 |

La petite turbine **92860304501**, le cône **93060304101** et le moyeu
**96410605131** font partie du système d'origine. Leur maintien et leurs
interfaces avec le nouvel alternateur doivent être vérifiés ; le PET seul ne
prouve pas la compatibilité d'une modification.

**Divergence découverte sur le moyeu :** [Patrick Motorsports](https://patrickmotorsports.com/products/eng96410605131)
exclut explicitement la 993 Turbo pour 96410605131, alors que FVD la liste et
que cette planche PET ne porte pas d'exclusion explicite à la position 25.
Le moyeu reconstruit reste une référence à vérifier, sans compatibilité Turbo
attestée. Cette divergence devra être résolue par référence Porsche applicable
au montage exact avant achat ou fixation de ses ajustements.

## Dimensions trouvées et portée réelle

| Information publiée | Source | Utilisation correcte |
|---|---|---|
| Rotor Turbo : 245 × 245 × 87 mm ; 0,9 kg | FVD rotor | Enveloppe commerciale sans tolérances ; pas un plan de fabrication |
| Moyeu : 64 × 64 × 35 mm ; 0,26 kg | FVD hub | Enveloppe commerciale ; ni alésage ni entraxe attesté |
| Trois vis M6 × 30 ; écrou BM16 × 1,5 | PET | Désignations des fixations ; pas les ajustements associés |
| Cales 0,5 et 0,7 mm | PET | Références selon montage ; quantité à déterminer |
| Bagues WOSP : 7, 17, 2 mm | Notice WOSP | RS : 7 ; double poulie : 24 ; ancienne 964 Turbo : 26 mm |
| Bague contre roulement en retrait | WOSP / Classic Retrofit | À conserver ; épaisseur non publiée dans cette notice |
| AS-PL A01345S : F.1 160 mm, L.1 256 mm, 115 A | AS-PL | Autre alternateur ; aucune reprise comme dimensions PMB |

Les **26 mm WOSP ne sont pas une cote générique de 993 Turbo**. La bague
initiale contre le roulement est distincte des empilages indiqués. La notice
concerne LMA339/LMA498 ; la correspondance exacte du produit PMB doit encore être
confirmée. Le flyer WOSP indique LMA339 à 240 A et LMA498 à 180 A : ne pas
confondre cette désignation avec la fiche Classic Retrofit 175 A de la photo.

## Autres informations retrouvées, à ne pas transformer en certitudes

La [fiche PorscheFanatics](https://porschefanatics.com/parts/porsche-ag-eng96410601531/)
renvoie à la référence **Carrera 96410601531**. Son libellé « All models » est
plus large que la distinction du PET ; il ne prouve pas son emploi sur Turbo.
Cette fiche ne donne ni procédé de fabrication ni cotes fonctionnelles.

Les registres du dépôt contiennent aussi trois pistes de couples de serrage
(page 61 du manuel, transcription OCR **non vérifiée**) : sangle 8 N·m,
poulie d'alternateur 50 N·m et petite turbine 14 N·m. Le modèle n'y est pas
précisé. Ces valeurs sont consignées pour retrouver la page primaire ; elles
ne constituent pas des consignes de montage Turbo / PMB.

## Alternateur 240 A et entraînement

PMB identifie son produit comme le Classic Retrofit 240 A. Le fabricant annonce
une base Denso six phases à conducteurs hairpin, un carter spécifique 964/993
et plus de 100 A au ralenti. Ce sont des données commerciales du fabricant,
pas une cartographie thermique ni une mesure réalisée dans ce projet.

PMB et Classic Retrofit recommandent une **courroie multigorge avec tendeur**
pour le 240 A et leur unité 175 A pour les montages double poulie / RS.
Le remplacement ne se résume donc pas à augmenter le diamètre disponible dans
le rotor. Il manque la définition du kit d'entraînement choisi, les vitesses
respectives, les portées et l'empilage. L'arbre d'alternateur ne doit pas être
fusionné au carter fixe dans la simulation. Le moyeu à roulement et les deux
entraînements du montage d'origine empêchent d'imposer arbitrairement une
rotation solidaire de toutes les pièces.

La notice Classic Retrofit souligne aussi le rôle du cône arrière dans la
répartition des efforts des écrous. L'affirmation commerciale de compatibilité
avec les carters 964/993 ne remplace pas un contrôle d'interférences coté.

## Matière, débit et impression

Aucun document consulté ici ne donne un jeu complet de propriétés matière du
rotor Turbo avec nuance, procédé, traitement et courbes de fatigue. On ne peut
pas choisir une matière « optimale » sur le seul aspect d'une photographie.
AlSi10Mg demeure le candidat de l'étude précédente, **pas une matière validée**
pour cette reconstruction. Le choix final doit comparer masse, fatigue,
rigidité, défauts LPBF, finition des pales, usinage des portées et équilibrage.

Le nouveau modèle ne possède pas encore de carter ni de passage d'air PMB
reconstruits. Il ne permet donc pas de recalculer un débit moteur représentatif.
Les anciens chiffres sont archivés et ne sont pas transférés. L'optimisation
reprendra par une référence complète, puis une comparaison à régime et perte
de charge identiques : débit, pression, couple absorbé, température alternateur
et marges mécaniques. PhysicsNeMo doit utiliser des données CFD pertinentes ;
Omniverse sert à assembler et inspecter, sa visualisation ne valide pas le débit.

## Vérifications exécutées

La génération C# inclut des contrôles du passage central, des douze ouvertures,
de la présence de chacune des onze pales et de la cuvette. Le contrôle Python
vérifie les maillages exportés : fermeture, orientation, composante unique,
volume positif et conservation du volume après réduction pour la revue.
Les centres des douze fenêtres sont aussi vérifiés dans le maillage réduit.
La scène et son paquet USDZ sont ouverts et soumis aux validateurs OpenUSD.

`make check` passe : suite principale de 3 184 tests (148 ignorés), contrôles
complémentaires et 0 lien cassé dans 566 documents Markdown.

Les résultats exacts sont dans [validation.json](results/reference/validation.json).
Les quatre images sont des **vues techniques de maillages calculés**, produites
localement ; ce ne sont pas des captures RTX, ni des résultats de soufflerie.
Aucune location GPU n'a été lancée pour cette reprise géométrique.

## Reproduction

Avec le runtime PicoGK local déjà installé, le SDK .NET 9 et l'environnement
Python existant de cette étude, depuis la racine du dépôt :

```sh
docker run --rm \
  -v "$PWD/twins/993-engine-cooling-fan-system-f0/source/picogk-reference:/src:ro" \
  -v "$PWD/work/fan-aerodynamics/runtime/PicoGK.dll:/app/PicoGK.dll:ro" \
  -v "$PWD/work/fan-aerodynamics/reference-rebuild/build:/out" \
  mcr.microsoft.com/dotnet/sdk:9.0 \
  dotnet build /src/Reference.csproj -o /out -p:BaseIntermediateOutputPath=/tmp/obj/ -c Release
cp work/fan-aerodynamics/runtime/fan/*.dylib work/fan-aerodynamics/reference-rebuild/build/
work/fan-aerodynamics/runtime/dotnet/dotnet \
  work/fan-aerodynamics/reference-rebuild/build/Reference.dll \
  twins/993-engine-cooling-fan-system-f0/source/picogk-reference/reference.json \
  work/fan-aerodynamics/reference-rebuild/geometry-new
work/fan-aerodynamics/physicsnemo-venv/bin/python \
  twins/993-engine-cooling-fan-system-f0/source/build_reference_review.py \
  --source work/fan-aerodynamics/reference-rebuild/geometry-new \
  --output work/fan-aerodynamics/reference-rebuild/review-new
```

Les dossiers de sortie doivent être nouveaux pour préserver les essais. Le
SDK compile le C# ; l'exécution utilise le noyau natif PicoGK macOS existant.
Ces commandes ne constituent pas un installateur portable du noyau PicoGK.

## Sources consultées et limites de recherche

- **pet** : [Porsche PET 993, illustration 105-00, pages PDF 77–78](https://a.storyblok.com/f/332100/7be45d4171/kat517-usa-911-98-katalog.pdf).
- **originale** : [Porsche ORIGINALE 05, page PDF 7 / imprimée 83](https://a.storyblok.com/f/332100/d50d3473a6/originale-05-ww.pdf).
- **rotor** : [FVD 96410601522, dimensions commerciales et dix vues produit](https://www.fvd.net/fr/shop/turbine-965-993-turbo-96410601522~p252068).
- **hub** : [FVD 96410605131, enveloppe commerciale](https://www.fvd.net/en-us/shop/fan-hub-964-993-for-engine-cooling-fan-96410605131~p247931).
- **pmb** : [PMB alternateur 240 A choisi par utilisateur](https://pmbperformance.com/products/high-output-240a-alternator-for-porsche-964-and-993-90-99).
- **cr240** : [Classic Retrofit 240 A, recommandations entraînement](https://www.classicretrofit.com/en-us/products/porsche-964-993-240a-high-output-alternator).
- **install** : [Classic Retrofit installation 993, bagues et cône](https://classic-retrofit.com/forum/index.php?/topic/2521-993-alternator-install/).
- **wosp** : [WOSP LMA339/LMA498 Spacer Instructions, page unique](https://wosperformance.co.uk/ClientArea/files/Downloads/LMA339%20LMA498%20Spacer%20Instructions.pdf).
- **wosp_flyer** : [WOSP Porsche alternator flyer, LMA339 240 A / LMA498 180 A](https://www.wosperformance.co.uk/clientarea/files/downloads/Porsche%20911%20WOSP%20Alternator%20Flyer.pdf).
- **rothsport** : [Rothsport RS-079, conversion simple courroie](https://rothsport.com/products/964-993-rs-single-belt-conversion-hub).
- **aspl** : [AS-PL A01345S, 115 A, F.1 160 mm / L.1 256 mm](https://as-pl.com/fi/p/A01345S).
- **design911** : [Carter Turbo 99310666750, pos.5](https://www.design911.co.uk/p/engine-fan-housing-porsche-993-turbo-1994-98-99310666750/).

La recherche couvre les catalogues Porsche, les fiches fournisseur identifiées
et les notices publiques de montage. Elle n'est pas une garantie d'exhaustivité
sur Internet. Aucun plan de fabrication complet PMB ou rotor/carter Turbo n'a
été trouvé dans ces sources. Les catalogues, photos produit et photographies
utilisateur restent des références externes ; ils ne sont pas redistribués.
Les empreintes des PDF consultés sont conservées dans le registre JSON.

Pour terminer le jumeau dimensionnel, il reste à obtenir les portées/entraxes,
profils axiaux, géométrie des aubes fixes et du PMB, ainsi que le kit multigorge.
La nouvelle reconstruction permet de revoir la morphologie dès maintenant ;
elle ne ferme pas ces interfaces et n'autorise ni fabrication ni montage moteur.
