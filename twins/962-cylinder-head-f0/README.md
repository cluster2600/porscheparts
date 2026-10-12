# Culasse 962 C : recherche et candidat PicoGK F0

**Nouvelle cible : un kit moteur inspiré du 962 pour bases 911, 964 et 993,
avec un objectif de développement de 1 000 ch.** Le
[programme produit](KIT_962_PROGRAMME.md) définit le périmètre, les variantes,
la fabrication et les critères de qualification. F0 reste un témoin de
géométrie ; ses interfaces et son rapport ne deviennent pas ceux d'un M64.

Cette livraison ouvre le jumeau numérique demandé : culasse refroidie par eau,
quatre soupapes et deux bougies par cylindre, architecture ramifiée et conduits
adaptés à une étude LPBF. **F0 est une étude géométrique sans interfaces mesurées,
sans simulation thermique et sans autorisation de fabrication.** Ce n'est pas
encore le jumeau calibré d'une culasse 962 identifiée.

![Solide, circuit d'eau et coupe du candidat](derived/preview.png)

## Ce que les sources établissent

Le [dossier Porsche « 40 Years Group C »](https://newsroom.porsche.com/dam/jcr:a6f33b52-c47d-47b4-98c1-7e963661f587/40%2520Years%2520Group%2520C.pdf),
pages 7 et 18–20, distingue les 962 IMSA à deux soupapes refroidies par air des
962 C à quatre soupapes. Le 3 litres entièrement refroidi par eau apparaît aux
essais du Mans 1985. La famille compte des variantes de 2 994 et 3 164 cm³.
Les culasses et cylindres sont en aluminium ; la nuance n'est pas précisée.
Certaines unités cylindre–culasse sont soudées par faisceau d'électrons.
Deux arbres à cames par banc sont entraînés par engrenages ; les soupapes sont
actionnées par poussoirs et réglées par pastilles.

Porsche décrit **deux circuits d'eau indépendants avec une pompe par banc**,
et de grosses conduites près des canaux d'échappement. Le dessin interne,
l'ordre exact des galeries, les débits et les pressions restent inconnus.

| Information | Résultat de recherche | Utilisation dans F0 |
|---|---|---|
| Alésage/course publiés | 92,3 × 66 mm pour le 956 Type 935/76 | Référence distincte du donneur 962 |
| Alésage/course exacts du donneur 962 C | Non établis par un plan primaire | Alésage **95 mm choisi**, hypothèse |
| Cotes hors tout, entraxes, fixations | Inconnus | Aucun montage revendiqué |
| Chambres, sièges, angles, guides | Inconnus | Passages de réservation |
| Nuance et traitement d'origine | Inconnus | Aucune équivalence matière |
| Double allumage d'origine | Non établi | Deux bougies exigées pour le candidat |

Le registre [research.json](research.json) conserve les sources, pages,
empreintes des PDF consultés, droits et inconnues. Aucun PDF constructeur,
scan ou dessin tiers n'est redistribué. Les valeurs du modèle ne sont pas des
cotes Porsche. Le catalogue 993 reste la source de vérité des pièces 993 ;
cette étude 962 séparée n'y ajoute pas de pièce fonctionnelle.

## Apport de la FIA

L'[annexe J FIA 1986](https://historicdb.fia.com/sites/default/files/regulations/1439541317/appendix_j_1986.pdf),
article 257.2.1, page imprimée 195 (page PDF 41), définit l'ensemble moteur
comme bloc, cylindres et culasses et autorise ses modifications. La page a été
vérifiée visuellement, en complément de l'OCR. Ce règlement Groupe C1
n'est pas un plan de culasse et ne qualifie pas une modification contemporaine.

La recherche « 962 » dans la [base FIA des voitures](https://historicdb.fia.com/cars/list/?search=962)
n'a retourné aucune voiture lors de cette consultation. Ce résultat limité
ne prouve pas l'absence d'un dossier FIA/ASN privé. Les fiches d'une 911,
d'une 959, d'une 917 ou d'une Dauer routière ne doivent pas être converties en
preuve des interfaces d'une 962 C. Pour une compétition historique, vérifier
séparément la spécification de période, le HTP et le règlement de l'épreuve
avec l'ASN ; aucune éligibilité n'est acquise par F0.

## Matière : conductivité et tenue à chaud

| Candidat | Donnée effectivement consultée | Position pour l'étude |
|---|---|---|
| Aheadd CP1, Al–Zr–Fe LPBF | **187 W/m·K** à température ambiante ; Rp0,2 323 MPa, Rm 342 MPa après 400 °C/4 h, éprouvettes verticales | Premier candidat léger à comparer |
| CuCrZr LPBF | Une [étude expérimentale 2025](https://www.sciencedirect.com/science/article/pii/S1044580325001007) annonce **340 W/m·K** ; résumé indexé consulté, texte intégral inaccessible | Candidat prioritaire pour la conductivité, valeur non utilisable comme propriété de calcul |
| CuCrZr EOS M400-1, couches 80 µm | Fiche mai 2025 : 88 % IACS après 550 °C/3 h ; Rp0,2 vertical 230 MPa ; densité ≥ 8,84 g/cm³ | Recette fournisseur à qualifier ; IACS est une conductivité **électrique**, pas thermique |
| CuCP, cuivre commercialement pur | [EOS](https://www.eos.info/metal-solutions/metal-materials/copper) le propose pour la conductivité | Témoin thermique à mesurer ; pas de choix structurel automatique |

Sources : [fiche Constellium CP1, novembre 2021](https://assets.foleon.com/eu-central-1/de-uploads-7e3kk3/41170/product_sheet_aheadd_cp1_nov_2021docx.e81a7d073ebf.pdf)
et [fiche EOS CuCrZr, mai 2025](https://www.eos.info/05-datasheet-images/Assets_MDS_Metal/EOS_CopperAlloy_CuCrZr/Material_DataSheet_EOS%20_Copper_CuCrZr_en.pdf).
Ces mesures proviennent de procédés et éprouvettes différents. Ni 187 ni 340
W/m·K ne constitue une courbe k(T) ou un allowable de culasse.

**Choix de travail : CP1 pour la référence légère, CuCrZr pour la variante
prioritaire à forte conductivité.** La sélection finale dépendra de k(T), de
la température locale, de la fatigue thermomécanique, du fluage, du maintien
des sièges et guides, et de la masse autorisée. Il faut mesurer ces propriétés
sur le procédé exact retenu. Le matériau qui conduit le mieux à froid peut
être un mauvais corps de culasse à chaud.

Une variante CP1 avec inserts CuCrZr est une piste ultérieure : sa résistance
de contact, ses assemblages, dilatations et couples galvaniques demandent une
qualification propre. Aucun assemblage multi-matériau n'est simulé ici.
Titane et Inconel ne sont pas sélectionnés sur la seule exigence de transfert
thermique ; aucun classement chiffré non vérifié ne leur est attribué.

## Géométrie moderne effectivement générée

Le générateur [Head962Study.cs](../../parts/picogk-catalog/engine/Head962Study.cs)
réutilise les primitives et le runner du catalogue PicoGK existant. La source
C# et les trois JSON sont les entrées éditables ; les STL sont des sorties
dérivées, pas une histoire paramétrique STEP.

- Une unité par cylindre, avec quatre passages de gaz/guides et deux puits de
  bougie distincts. Deux passages sont destinés à l'admission, deux à
  l'échappement. Ce sont des réservations, sans sièges, filets ni soupapes
  fonctionnelles ; les axes verticaux F0 ne reproduisent pas les angles OEM.
- Quatre boucles conformes autour des passages, une distribution basse et
  une collecte haute sur un niveau séparé, pour éviter les croisements.
- Sections horizontales en goutte : partie inférieure arrondie et toit à 45°
  dans le repère de construction Z. Les remontées sont circulaires verticales.
  C'est une intention DfAM ; les coudes, jonctions, surplombs et évacuation de
  poudre doivent être éprouvés sur coupons.
- Une peau autour des volumes secs et humides, un plateau de chambre et des
  renforts ramifiés reliant les réservations. Cette morphologie bionique ne
  provient pas d'une optimisation sous charges de combustion.
- Trois exports cohérents : solide, volume d'eau, volumes secs. Aucun
  réseau fermé de lattice ou gyroid n'est ajouté aux canaux.

L'enveloppe 160 × 160 × 90 mm, la chambre sphérique, le diamètre de passage
16 mm, les puits de bougie 8 mm, les canaux de base 6 mm et la peau nominale
4 mm sont **des hypothèses de démonstration**. Le modèle ne reproduit ni
les goujons ni le porte-arbres ; il ne peut pas être monté sur un moteur.
Le volume sec exporté dépasse volontairement le solide pour ouvrir les ports.

Schéma **proposé pour la variante moderne**, à qualifier, et non relevé OEM :

```mermaid
flowchart LR
  R[Échangeur et retour froid] --> P[Pompe du banc]
  P --> F[Collecteur de distribution]
  F --> H[Branches conformes autour des zones chaudes]
  H --> C[Collecteur de retour]
  C --> R
  C -. purge au point haut en position montée .-> D[Dégazage à concevoir]
```

Reproduire ce circuit indépendamment pour l'autre banc. Les branches entre
cylindres, les radiateurs, le dégazage et les pompes ne sont pas modélisés.
Les boucles F0 alimentent les quatre passages de façon symétrique ; une future
distribution favorisant l'échappement devra être décidée à partir du flux de
chaleur et de la perte de pression, pas de l'apparence. Un canal plus fin ou
plus rugueux peut augmenter l'échange local tout en dégradant le débit total.

## Vérification et reproduction

Le [rapport](derived/study-report.json) conserve les empreintes des sources
et des trois STL locaux, leurs dimensions, volumes, fermeture, orientation
et connexité. L'inspection indépendante sonde la distance entre eau et
volumes secs. Ce contrôle échantillonné ne certifie pas l'épaisseur minimale,
les intersections globales, la tenue à la pression ni l'absence de poches d'air.
La peau nominale n'est pas une tolérance de fabrication.

Construire le projet existant avec le checkout PicoGK référencé par
[sources.lock](../../containers/m64-leap71/sources.lock), son runtime natif
compatible, et un répertoire neuf sous `work/` :

```sh
dotnet build parts/picogk-catalog/engine/Engine.csproj \
  -p:UpstreamRoot=/chemin/vers/upstream -p:GeneratePackageOnBuild=false \
  -o work/962-head/bin
# Placer les dylib/so du runtime PicoGK compatible près de Engine.dll.
dotnet work/962-head/bin/Engine.dll twins/962-cylinder-head-f0/source/solid.json work/962-head/native
dotnet work/962-head/bin/Engine.dll twins/962-cylinder-head-f0/source/coolant.json work/962-head/native
dotnet work/962-head/bin/Engine.dll twins/962-cylinder-head-f0/source/dry-passages.json work/962-head/native
python twins/962-cylinder-head-f0/source/inspect_study.py work/962-head/native work/962-head/inspected
python3 -m unittest discover -s tests -p test_962_head_study.py -v
```

Exécuter PicoGK en série sous le verrou fourni par
[run_part.py](../../parts/picogk-catalog/tools/run_part.py) si d'autres travaux
PicoGK tournent sur la même machine. L'inspecteur utilise NumPy, trimesh et
VTK ; la livraison a utilisé un environnement temporaire sous `work/`, sans
nouvelle dépendance dans l'application. Les STL complets restent locaux dans
`work/962-head/inspected/`. Seuls le rapport et l'aperçu sont versionnés.

## Feuille de route vers un jumeau exploitable

1. **Identifier le donneur.** Fixer type moteur, année, numéro de pièce et
   architecture soudée/démontable. Mesurer plan de feu, goujons, axes, sièges,
   guides, chambre, raccords, porte-arbres et entraînement. Scanner l'extérieur
   et faire une CT industrielle des galeries ; conserver incertitudes et droits.
2. **Reconstruire la référence.** Créer les interfaces protégées et un modèle
   mesuré, avec écarts scan/CAO. Calibrer les deux circuits à partir d'essais de
   débit, pression et températures. Les champs inconnus du
   [contrat](interface-contract.json) doivent rester `null` jusque-là.
3. **Comparer référence et candidat.** CHT eau–métal–gaz, réseau hydraulique,
   partage entre branches, points chauds, ébullition et cavitation ; calcul
   thermomécanique avec pression cylindre, précharge, sièges et guides.
   Comparer à puissance de pompe et conditions d'entrée identiques.
4. **Qualifier le procédé et les coupons.** CP1/CuCrZr sur la machine exacte,
   k(T), traction à chaud, fatigue, fluage, corrosion ; coupons de canaux et
   jonctions, nettoyage et CT. Définir orientation, supports retirables,
   traitement thermique/HIP éventuel, reprises d'usinage et contrôles.
5. **Revue d'ingénierie puis prototype.** Plan approuvé, épreuve hydrostatique
   et fuite, cycles thermiques, maintien des sièges/guides, banc de combustion
   et endurance. La fabrication et l'utilisation moteur restent bloquées tant
   que ces preuves ne sont pas liées au dossier.

Le fichier [validation.md](validation.md) distingue les vérifications locales,
le résultat de `make check` et les validations physiques encore absentes.
