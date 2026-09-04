# Porsche 917 — définition de fabrication F37 de la culasse quatre soupapes

## Décision au 2 septembre 2026

F37 transforme le prototype géométrique F36-013 en un **dossier de définition
fonctionnelle contrôlable**. Le porte-axes, quatre culbuteurs, deux axes, les
surépaisseurs d'usinage, les outils de finition et le noyau des galeries d'huile
sont produits en B-Rep analytiques OCCT et exportés en STEP. Les six familles
de formes sont fermées, valides et réimportées sans dérive de volume mesurable.
La peau extérieure à ailettes reste conforme au scan utilisé pour F36.

Ce résultat ne constitue cependant **ni une culasse Porsche 917 identifiée
dimensionnellement, ni une pièce libérée pour impression, ni une pièce autorisée
à démarrer**. Le scan ne confirme ni son échelle absolue, ni les interfaces du
moteur. La culasse n'existe pas encore comme un unique B-Rep de production et
les calculs restent des criblages numériques sous hypothèses.

```text
metal_print_authorized = false
engine_start_authorized = false
```

Les valeurs en millimètres, kilogrammes et mégapascals de ce document sont
conditionnelles à l'hypothèse `1 unité OBJ = 1 mm`, sauf indication contraire.

## Niveau de preuve

Le dossier sépare volontairement cinq niveaux qui ne doivent pas être
confondus :

1. **intégrité de source** : empreintes SHA-256 du scan local, du contrat et des
   rapports ;
2. **géométrie numérique** : peau F36 étanche et interfaces F37 analytiques ;
3. **criblage physique virtuel** : CFD, conduction, élasticité linéaire,
   cinématique, hydraulique et audit LPBF ;
4. **corrélation physique** : éprouvettes, CT/CND, banc d'huile, banc de flux,
   spintron, thermocouples et banc moteur ;
5. **autorisation de fabrication et d'essai** : revue et signature d'un
   ingénieur responsable et d'un fournisseur qualifié.

F37 atteint partiellement les niveaux 1 à 3. Les niveaux 4 et 5 sont ouverts.

La chaîne de preuves retenue pour cette édition est la suivante. Un recalcul
qui modifie une seule empreinte invalide tous les rapports descendants jusqu'à
leur régénération.

| Élément | Chemin local | SHA-256 de cette édition |
| --- | --- | --- |
| Contrat F37 | `twins/reference-917-engine/f37-manufacturing-definition.json` | `b954612301f68b69c5cd16eebabf21f1e57c54340740898c946ae159d842b4eb` |
| Rapport CAO | `work/917-scan-conforming-f37/cad/f37-cad-report.json` | `2a9fac821474d5dd218cc029e7ff3ed6bc1841a38d3189194f44261ab48bb8b4` |
| STEP porte-axes | `work/917-scan-conforming-f37/cad/rocker-carrier-as-printed.step` | `b1e2ea048fced92bd4087b4cc467b1c651a570a6770d2b010ad07c716984d827` |
| Rapport de maillage culasse intégré | `work/917-scan-conforming-f37/head-mesh-proof/f37-printable-head-mesh-report.json` | `ffafa6eaf8c357361e8d65721ff613df3b1c981253f20aa447d367cce51ae44b` |
| Rapport cinématique | `work/917-scan-conforming-f37/kinematics/f37-rocker-kinematic-report.json` | `0388bb58684638184a021548d83f82c420744aa8d61ee9fd5b8fa3eb53855f74` |
| Rapport huile | `work/917-scan-conforming-f37/oil/f37-oil-hydraulic-report.json` | `46c6cf3101deb2d11a17bd90371faa49e3d47adb240fe5e42b7856c46de75571` |
| Rapport résistance analytique | `work/917-scan-conforming-f37/strength/f37-carrier-strength-report.json` | `e5c7cb7a29dec2e675f51b1fec753a31b5ae7aaafbc6db22aabeb9aeea500131` |
| Rapport CalculiX porte-axes | `work/917-scan-conforming-f37/carrier-calculix/f37-carrier-calculix-report.json` | `5908f397ec17b1f48bf1d691672133b35614e7b28062a6df34363828cc9737c2` |
| Rapport LPBF | `work/917-scan-conforming-f37/lpbf/f37-lpbf-manufacturing-report.json` | `bf9845e3238cb9ab4a32317a783c4281fbd29dc360877018f1369e1c5c474d22` |
| Validation NVIDIA Geometry | `twins/reference-917-engine/evidence/f37-simready/geometry.json` | `83517e19fc413096640962ff0cd820d2ed9c8ed803f0d00bafed48f40b9411a6` |
| Rapport rendu OVRTX | `twins/reference-917-engine/evidence/f37-simready/ovrtx-render.json` | `a2bd757bf533caeaf05313e3ca00a3042b967575ef69e0d4d5fc497939801663` |
| Image OVRTX finale | `twins/reference-917-engine/evidence/f37-simready/917-head-f37-ovrtx-final.png` | `6cba1f68fbcf3f80f987824aa5faff9cf9d579543edab0827aa992ca950d350f` |

Le rapport CAO référence bien le contrat `b95461…` et réimporte le STEP
porte-axes `b1e2ea…` sans dérive de volume. Le rapport cinématique référence le
rapport CAO `2a9fac…`; les rapports huile et résistance référencent
respectivement le contrat courant et la cinématique courante. Le rapport
CalculiX référence le même contrat et le même STEP. Le rapport LPBF référence
lui aussi le contrat `b95461…` et le rapport CAO `2a9fac…`. Le rapport de
maillage intégré référence ces mêmes contrat, rapport CAO, peau F36 et noyaux.

Le sous-ensemble publiable est recopié dans
`twins/reference-917-engine/evidence/f37-manufacturing-definition/` et lié par
`publication.json`. Il contient les STEP, rapports JSON et planches PNG, mais
aucun scan brut ni STL de la culasse complète.

La conversion et le rendu GPU exacts sont publiés séparément sous
`twins/reference-917-engine/evidence/f37-simready/`. L'USDC dérivé reste local,
mais son empreinte est liée au manifeste. Le prévol, l'ouverture USD et le
rendu passent; l'avertissement NVIDIA `VG.007 = 8 047` est conservé comme
blocage de projet malgré le statut formel `PASS` du validateur.

## Géométrie de référence

La source F36-013 est liée au fichier local par l'empreinte
`1e946dc72684da2dcded6959e3ef53cd49df634813ff3c3a3690c3b883aeec42`.
Le maillage final comporte 827 084 triangles, forme un seul corps étanche et
possède une orientation cohérente.

| Contrôle de géométrie | Résultat F36-013 | Lecture correcte |
| --- | ---: | --- |
| Écart médian à la peau du scan | 0,082 unité OBJ | passe le contrôle de reconstruction |
| Écart p95 | 0,439 unité OBJ | inférieur au seuil de 1,5 |
| Écart p99 | 0,710 unité OBJ | information, pas tolérance de fabrication |
| Écart maximal | 2,938 unités OBJ | extrême local à revoir |
| Distance interne minimale échantillonnée | 6,379 unités OBJ | distance au stock rebouché, pas une carte CT |
| Volume conditionnel | 1 059 854,924 mm³ | seulement si l'échelle supposée est juste |
| Masse nue conditionnelle | 2,829813 kg | à 2 670 kg/m³, hors inserts et distribution |
| Surface extérieure conditionnelle | 0,184870 m² | utilisée dans l'écran thermique |

La chambre candidate mesure 90,812 mm, le registre 113,526 mm et le motif des
quatre goujons 86,743 × 85,916 mm. Ces valeurs viennent de la reconstruction du
scan; elles ne prouvent pas un ajustement sur un moteur 917.

Une vue locale de l'état F37 est générée dans
`work/917-scan-conforming-f37/917-head-f37-manufacturing-definition.png`. Elle
montre la peau F36, le porte-axes, les culbuteurs, les axes, les galeries et les
volumes d'usinage. Une image est une aide de revue, jamais une preuve de cote ou
de résistance.

### Maillage intégré de revue

Une soustraction booléenne exacte a été appliquée localement à la peau F36 après
ajout de quatre fondations d'appui et perçages de goujons. Le résultat contient
857 330 triangles et 427 985 sommets, reste un seul corps étanche à orientation
cohérente. L'audit personnalisé des liens de sommets retourne zéro sommet non
manifold sur 427 985. Le rapport tête final lie par SHA-256 une attestation
séparée au même STL d'empreinte `3c7159…`; la conversion officielle y émet
`VG.007 = 8 047`, tandis que le USDA directement indexé passe Geometry sans
issue. Les définitions des deux routes doivent être réconciliées; jusque-là,
`independent_topology_validators_agree = false` et
`geometry_redesign_required = true` bloquent explicitement l'impression. Les
quatre plans d'appui à `z = 60 mm` sont détectés; leur aire plane
individuelle vaut de 351,42 à 354,12 mm². Les cinq accès d'huile déclarés
traversent la peau parent selon l'échantillonnage d'axe.

L'intersection booléenne exacte du noyau d'huile et du noyau gaz vaut 0 mm³,
après correction du chemin d'alimentation latéral. Les quatre fondations
ajoutent conditionnellement 16 867,52 mm³ et l'huile retranche 11 951,81 mm³.
Le volume final vaut 1 064 770,63 mm³, soit une masse conditionnelle de
2,84294 kg à 2 670 kg/m³. Ces contrôles ferment la collision huile–gaz et les
appuis détectés pendant la revue, mais pas la divergence de manifold. Ils ne
démontrent ni une épaisseur minimale par CT, ni un B-Rep de production, ni
l'usinabilité, ni l'imprimabilité métallique. Le STL de 42,9 Mo reste donc
local et n'est pas publié comme fichier de fabrication.

### Diagnostic de la conversion NVIDIA

Le diagnostic des indices du USDC officiel a isolé la divergence. Le
convertisseur `usd-convert-cad` construit 843 308 points pour 857 330 triangles
et laisse 667 342 arêtes de bord. Le calcul indépendant selon la définition
NVIDIA retrouve exactement 8 047 sommets portant plus de deux arêtes de bord.
Une soudure **exacte par coordonnées**, sans lissage ni voxelisation, ramène le
même maillage à 427 985 points, zéro arête de bord et zéro sommet VG.007-proxy.
Le rapport reproductible est local dans
`work/917-scan-conforming-f37/nvidia-repair-candidate/f37-nvidia-usd-topology-analysis.json`.

Les trois routes ont ensuite été contre-validées avec NVIDIA Geometry :

| Route | Résultat Geometry | Lecture correcte |
| --- | ---: | --- |
| STL candidat → `usd-convert-cad` | `VG.007 = 8 047` | la réexportation STL ne corrige pas l'indexation |
| OBJ indexé → `usd-convert-cad` | `VG.007 = 9 479` | le convertisseur recrée aussi des coutures |
| USDA directement indexé, normales uniformes par face | 0 erreur, 0 failure, 0 info, 0 warning | diagnostic Geometry propre, mais route de production non remplacée |

Le candidat conserve un corps étanche, le même volume à
`2,19×10⁻¹⁶` relatif près, un Hausdorff des ensembles de sommets nul, la
collision huile–gaz nulle et les quatre plans d'appui. Cela confirme un problème
de **représentation/indexation de conversion**, pas le droit de redessiner ou de
libérer la peau. Le STL, l'OBJ et le USDA complets restent exclusivement dans
`work/` et ne doivent pas être publiés.

L'attestation locale
`work/917-scan-conforming-f37/nvidia-repair-candidate/f37-nvidia-geometry-validation-attestation.json`
d'empreinte `1a03735f57635c5807791388e5620f31eceff3533d7c05b0a41528f5266d3471`
lie le USDA `e9d37090…`, le rapport NVIDIA `855f7a70…`, l'image conteneur
immuable et la commande du même run. Le wrapper de compétence a toutefois
normalisé le rapport brut temporaire : cette attestation n'est ni une signature
de la machine Vast, ni une CAO B-Rep, ni une validation de fabrication. Les
gates d'impression métal et de démarrage restent faux.

Les rapports normalisés des routes STL/OBJ ne portent pas l'empreinte du fichier
source donné au convertisseur. Ils localisent donc le défaut de représentation,
mais ne constituent pas une chaîne de fabrication signée.

## Architecture quatre soupapes

| Fonction | Définition candidate | État |
| --- | --- | --- |
| Admission | 2 soupapes Ø31,5 mm, tige Ø7 mm, axe incliné de −18° | emballage statique seulement |
| Échappement | 2 soupapes Ø26,0 mm, tige Ø7 mm, axe incliné de +18° | emballage statique seulement |
| Angle inclus | 36° | hypothèse d'architecture |
| Levée nominale | 12,0 mm | hypothèse, profil de came absent |
| Allumage | 2 bougies latérales inclinées, insert M10×1 candidat | inserts non libérés |
| Distribution | 4 culbuteurs individuels sur 2 axes Ø14 mm | statique CAO passée, dynamique absente |
| Porte-axes | pièce démontable bridée par 4 goujons de culasse allongés | empilage et précharge non libérés |
| Lubrification | alimentation/collecteur Ø6, dosage 4×Ø3, porte-axes Ø5, retours 2×Ø8 | réseau numérique connexe, banc absent |

Les axes des deux rangées de culbuteurs sont `y = −18/+18 mm`, `z = 96 mm`.
Le porte-axes occupe conditionnellement 110 × 106,086 × 50,5 mm et s'appuie à
`z = 60 mm` sur les quatre centres de goujons extraits de F36. Les alésages
d'axes sont imprimés à 13,4 mm puis repris à 14 mm. L'ajustement `14 H7/g6`
reste un candidat : les limites numériques ISO, la dilatation différentielle et
la retenue axiale doivent être confirmées par le fournisseur.

## Nomenclature fonctionnelle complète

Les pièces visibles dans la documentation commerciale fournie par l'utilisateur
ont été utilisées uniquement pour identifier les fonctions. Aucun numéro de
pièce 964/993 n'est transféré comme géométrie ou preuve de compatibilité 917.

| Élément | Qté par culasse | Route candidate | Matière candidate | Statut |
| --- | ---: | --- | --- | --- |
| Culasse nue | 1 | LPBF puis HT1/HT2 et usinage | Constellium Aheadd HT1 | non libérée |
| Soupape d'admission | 2 | achetée, forgée/corroyée et usinée | Ti-6Al-4V | non imprimée avec la culasse |
| Soupape d'échappement | 2 | achetée, corroyée et usinée | INCONEL alloy 751 | non imprimée avec la culasse |
| Guide de soupape | 4 | insert acheté, monté serré | acier fritté haute température | données fournisseur absentes |
| Siège d'admission | 2 | insert acheté, monté serré, rectifié | acier rapide fritté | données fournisseur absentes |
| Siège d'échappement | 2 | insert acheté, monté serré, rectifié | alliage fritté infiltré cuivre | données fournisseur absentes |
| Joint de queue | 4 | acheté | FKM ou PTFE haute température | sélection fournisseur absente |
| Pastille de réglage | 4 | achetée, rectifiée par classe | acier à roulement trempé | gamme d'épaisseurs non définie |
| Coupelle inférieure | 4 | achetée | acier trempé | géométrie non mesurée |
| Double ressort | 4 jeux | acheté, grenaillé et préformé | fil Cr-Si | écran mathématique passé, spintron absent |
| Coupelle supérieure | 4 | achetée, forgée/usinée | Ti-6Al-4V ou acier trempé | choix non gelé |
| Demi-lune | 8 | achetée, trempée/rectifiée | acier allié | géométrie non mesurée |
| Culbuteur doigt | 4 | acheté, corroyé/taillé/nitruré | 42CrMo4 QT nitruré | enveloppe CAO, contact non défini |
| Axe de culbuteur Ø14 | 2 | acheté, trempé et rectifié | 100Cr6 | ajustement et rétention non libérés |
| Porte-axes | 1 | billet usiné, démontable | EN AW-2618A T61 | carte chaude et fatigue non qualifiées |
| Goujon de culasse allongé | 4 | acheté, filetage roulé | acier allié haute température | longueur/précharge non libérées |
| Écrou de culasse | 4 | acheté | acier allié haute température | empilage de bridage non libéré |
| Goupille de positionnement | 2 | achetée, rectifiée | acier trempé | interfaces non mesurées |
| Insert de bougie M10×1 | 2 | acheté et posé après usinage | à définir avec le fournisseur | candidat uniquement |
| Bouchon de galerie M8×1 | 2 | acheté et posé après nettoyage | à définir | candidat uniquement |
| Sonde de température M10×1 | 1 | achetée | thermistance ou RTD | axe candidat seulement |
| Produit d'étanchéité | 1 dose | consommable qualifié | selon gamme fournisseur | non représenté en CAO |

Les dimensions nominales d'insert actuellement criblées sont : guides
Ø15 × 56 mm avec alésages tête Ø14,94 mm, sièges admission Ø34,7 × 7 mm dans
Ø34,58 mm, sièges échappement Ø29,2 × 7 mm dans Ø29,1 mm. Elles ne doivent pas
être communiquées comme cotes de commande avant réception de plans fournisseur
et calcul de la chaîne thermique.

## Choix matière et comparaison

### Culasse

| Candidat | Route | Donnée chaude disponible dans l'écran | Décision actuelle |
| --- | --- | --- | --- |
| Aheadd HT1 + HT2 | LPBF aluminium | Rp0,2 typique 216 MPa à 250 °C | retenu pour poursuivre les calculs |
| AlSi10Mg traité | LPBF aluminium | aucune limite à 250 °C dans l'entrée utilisée | rejeté pour le point 260 °C |
| EN AW-2618A | billet usiné | benchmark commercial, pas de carte LPBF | non comparable à une route imprimée |

Le choix Aheadd HT1 est un **choix de criblage**, pas une valeur admissible.
La [fiche officielle Aheadd HT1](https://assets.foleon.com/eu-central-1/de-uploads-7e3kk3/41170/aheadd_ht1_fact_sheet_230620.ccac52e244fb.pdf)
fournit des valeurs typiques. Il faut produire sur la machine, le lot de poudre,
l'orientation et le traitement retenus des éprouvettes de traction, de
conductivité et de fatigue à température.

### Soupapes et organes de distribution

L'admission est candidate en Ti-6Al-4V forgé/corroyé; la
[fiche TIMETAL 6-4](https://www.timet.com/documents/datasheets/alpha-and-beta-alloys/timetal-6-4.pdf)
est une source matière, pas une qualification de soupape. L'échappement est
candidat en INCONEL alloy 751 corroyé; la
[fiche Special Metals](https://www.specialmetals.com/documents/technical-bulletins/inconel/inconel-alloy-751.pdf)
documente l'usage en soupapes d'échappement. Les guides, sièges, ressorts,
culbuteurs, axes, coupelles, demi-lunes et goujons doivent être achetés à des
fournisseurs capables de fournir plans, certificats et données à chaud.

## Modèles mathématiques appliqués

### Soupapes, ressorts et ajustements

```text
Force des gaz sur une soupape : F_gaz = p × pi × d² / 4
Raideur de ressort hélicoïdal : k = G × d_fil⁴ / (8 × D_moyen³ × N_actif)
Accélération harmonique écran : a_max = h/2 × (2 pi/beta_cam)² × omega_cam²
Diamètre chaud : D_T = D_20 × [1 + alpha × (T - 20 °C)]
Pression de frettage écran : p = [delta_d/(2D)] / (1/E_tête + 1/E_insert)
```

Le candidat double ressort robuste Cr-Si donne 420 N sur siège, 1 418,27 N
ouvert et 1 459,86 N dans le pire cas de hauteur. La marge dynamique calculée
vaut 1,759 à l'admission et 1,339 à l'échappement; la marge minimale avant
spires jointives vaut 3,06 mm et la contrainte de Wahl maximale 908,47 MPa.
Ces portes mathématiques passent, mais aucun profil de came mesuré, certificat
ressort, essai de fatigue ou spintron ne les confirme.

Les écrans de montage donnent à chaud 0,0407 mm de jeu de tige admission,
0,0500 mm à l'échappement, 0,0292 mm d'interférence guide–culasse et environ
0,0249/0,0270 mm d'interférence siège admission/échappement. Les propriétés
des inserts sont hypothétiques; ces valeurs ne sont pas des cotes libérées.

### Cinématique des culbuteurs

```text
Levée came nominale : h_came = h_soupape / rapport_culbuteur
Levier tangentiel : r_eff = |t(r) · u_soupape| × ||r||
Rotation écran : theta = h_soupape / r_eff
```

Les quatre cas F37 donnent un levier soupape de 29,048 mm, un levier tangentiel
de 28,715 mm, une levée de came nominale de 10,435 mm et une rotation de
23,944°. Les interférences statiques porte-axes–culbuteurs et axes–culbuteurs
sont nulles dans les enveloppes B-Rep. Le résultat ne couvre ni le rayon de
contact réel, ni le profil de came, ni la lubrification du contact, ni la
flexion dynamique.

### Circuit d'huile — deux formulations

```text
Hagen–Poiseuille : delta_p = 128 × mu × L × Q / (pi × D⁴)
Darcy–Weisbach : delta_p = f × L/D × rho × v²/2, avec f = 64/Re
Pertes singulières : delta_p = K × rho × v²/2
Sensibilité de dosage : Q proportionnel à D⁴ à delta_p égal
```

À 0,60 L/min total, dont 0,15 L/min par culbuteur, le pire chemin calculé perd
1,968 kPa avec `mu = 0,012 Pa·s` à chaud et 11,912 kPa avec
`mu = 0,08 Pa·s` à froid. Tous les Reynolds restent inférieurs à 151. Pour des
branches finies à 3,00 ± 0,05 mm, l'écart de débit parallèle théorique atteint
13,315 %, sous la cible de 15 %.

Hagen–Poiseuille et Darcy avec `f = 64/Re` sont algébriquement équivalents en
régime laminaire. Leur accord à l'arrondi machine contrôle l'implémentation,
mais ne constitue pas une deuxième validation physique. Le noyau d'huile est
un solide connexe et les axes centraux des cinq accès déclarés croisent
numériquement la peau F36. Ce test ne vérifie cependant ni tout le volume des
débouchés avec ses tolérances, ni leur accessibilité réelle, ni leur état après
impression; aucun contrôle CT ni essai de débit, pression, drainage ou
dépoudrage n'a été réalisé.

### Porte-axes, culbuteurs et axes

```text
Contrainte de flexion : sigma = M × c / I = M / W
Flèche poutre : E I y''(x) = M(x)
Pression de palier écran : p_b = F / (d × largeur)
Facteur de sécurité écran : FoS = limite_candidate / contrainte_calculée
```

La charge ressort de calcul vaut `1 460 × 1,3 = 1 898 N` par soupape. Avec le
rapport de bras 1,15, l'effort came idéal vaut 2 182,7 N. L'enveloppe colinéaire
borne la magnitude de réaction au pivot à
`(1 + 1,15) × 1 898 = 4 080,7 N`. Sa direction réelle reste inconnue sans profil
de came et géométrie de contact; l'enveloppe est donc appliquée suivant l'axe de
soupape comme direction-écran, sans prétendre fermer la résultante. Sur une
portée de 86,743 mm, l'écran Euler–Bernoulli du rail H24 × Y34 donne :

| Indicateur | Résultat | Porte virtuelle |
| --- | ---: | --- |
| Contrainte de flexion du porte-axes | 81,202 MPa | FoS chaud 2,463, passe écran |
| Flèche fermée | 0,138794 mm | passe la cible 0,150 mm |
| Écart flèche analytique/numérique | 5,80×10⁻⁸ relatif | contrôle d'implémentation passé |
| Pression de palier axe | 19,432 MPa | enveloppe de magnitude, écran seulement |
| Contrainte culbuteur | 206,440 MPa | charge côté ressort; FoS 4,360, passe écran |
| Contrainte axe | 56,804 MPa | enveloppe pivot; FoS 21,125, passe écran |
| Cisaillement nominal des goujons partagés Ø10,0 mm | 51,957 MPa | enveloppe pivot; FoS écran 7,699, passe |

La flèche analytique garde une marge numérique de 11,21 µm sur la cible. Une
seconde méthode, CalculiX statique linéaire sur tétraèdres C3D4, a été exécutée
sur le STEP H24/Y34/fenêtre Y36 `b1e2ea04…`, avec 4 080,7 N par zone suivant la
direction-écran de chaque axe de soupape :

| Pas nominal | Éléments | Déplacement max | von Mises p95 | p99 | maximum |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 2,00 mm | 144 620 | 0,088327 mm | 32,262 MPa | 52,495 MPa | 167,171 MPa |
| 1,50 mm | 326 540 | 0,092259 mm | 32,254 MPa | 51,425 MPa | 199,886 MPa |
| 1,25 mm | 554 013 | 0,093252 mm | 32,243 MPa | 50,792 MPa | 208,734 MPa |

Entre les deux mailles les plus fines, le déplacement change de 1,065 % et le
p95 de 0,0345 %. Les deux critères de convergence à 5 % passent. Le p99 reste
sous la limite-écran candidate de 200 MPa à 200 °C et la flèche fine de
0,093252 mm passe la cible de 0,150 mm. Le maximum local augmente néanmoins de
199,886 à 208,734 MPa entre ces mêmes mailles, dépasse la limite-écran et n'est
pas démontré convergé. Le gate `finest_maximum_below_200c_screen_yield` est donc
`false`.

Ces marges ne doivent pas être interprétées comme des tolérances libérées. Le
maillage global C3D4 ne constitue pas un sous-modèle convergé des concentrations
de contrainte aux galeries, perçages et rayons d'entaille. Les deux modèles sont
linéaires et ne contiennent pas le contact axe–culbuteur–porte-axes, la
précharge, le gradient thermique, la plasticité, la fatigue ou le serrage réel.
Le module et la limite à 200 °C sont des valeurs écran, pas une carte matière
2618A qualifiée avec les lots et traitements retenus. Les portes
`actual_resultant_direction_complete`, `rocker_pivot_resultant_load_complete`,
`nonlinear_contact_complete` et `qualified_material_card` restent donc fausses;
une FEA non linéaire locale et une corrélation sur banc restent nécessaires.

### Dissipation thermique et CFD externe

```text
h_eff = Q_air / [A_ext × (T_paroi - T_amont)]
div[k(T) grad(T)] = 0
-k grad(T)·n = q_chambre
-k grad(T)·n = h × (T - T_air) sur les surfaces refroidies
```

FluidX3D emploie un LBM D3Q19/TRT avec scalaire thermique D3Q7 à paroi imposée.
Sur les grilles 96, 192, 288 et 384, `h_eff` évolue de 961 à 536 W/m²K. Entre
les deux grilles les plus fines, le débit change de 0,65 %, mais la chaleur de
7,11 % et la perte de charge issue de la traînée de 23,43 % : l'indépendance de
grille à 5 % **échoue**.

Le balayage de carénage sélectionne virtuellement un jeu de 20 mm :
`h_eff = 1 108 W/m²K`, débit calculé 0,813 kg/s, perte de charge issue de la
traînée 8,02 kPa et puissance d'air estimée 6,15 kW. Cette valeur est le meilleur
point de l'échantillon respectant `h >= 800 W/m²K` et `delta_p <= 10 kPa`; ce
n'est pas une carte de ventilateur validée.

Le modèle de conduction CalculiX à pas 2,5 mm, flux chambre moyen
0,45 W/mm² et `h = 1 108 W/m²K` donne 237,98 °C au maximum et 154,57 °C au
p95, soit 22,02 °C de marge sur l'écran à 260 °C. Le changement de maille 3,0
vers 2,5 mm reste sous 5 %. En revanche, une conductivité diminuée de 20 % donne
301,34 °C : la porte thermique devient rouge.

Le cas OpenFOAM géométriquement résolu dispose d'un maillage récupéré de
200 305 cellules et 56 315 faces sur le patch `head`. Il termine à
0,850012 kg/s, rejette 2,949 kW et prédit une perte de charge statique de
0,684 kPa, soit `h_eff = 81,55 W/m²K`. Le bilan énergétique ferme à 0,42 % et
la variation du flux entre les deux derniers échantillons vaut 0,008 %. Le
contrôle `checkMesh` standard passe, mais le contrôle strict garde une cellule
de déterminant inférieur à 0,001 et 12 564 cellules concaves.

À débit comparable, FluidX3D ultra ajusté prédit 23,148 kW,
`h_eff = 556,5 W/m²K` et 1,696 kPa. Les écarts relatifs à OpenFOAM atteignent
684,9 % sur la chaleur et 147,8 % sur la perte de charge : les deux méthodes ne
se valident pas mutuellement. Le calcul solide lié à l'OpenFOAM nominal, avec
`h = 81,55 W/m²K`, atteint 617,42 °C au maximum et 525,64 °C au p95; il échoue
l'écran à 260 °C. Le carénage de 20 mm a maintenant été exécuté sous OpenFOAM
sur deux mailles RANS et deux diagnostics laminaires. Tous sont rejetés : les
erreurs de bilan énergie vont de 41,78 à 82,04 %, l'écart RANS entre mailles
atteint 16,26 % sur `h`, et la meilleure observation RANS liée à CalculiX donne
468,09 °C. Deux essais de domaine axial allongé se sont aussi arrêtés par
instabilité. Le résultat LBM favorable ne peut donc pas servir de base de
fabrication et aucune configuration de refroidissement n'est sélectionnée.

### Résistance de la culasse

CalculiX applique jusqu'à 24,686 MPa de pression de cylindre et un gradient
thermique prescrit sur un modèle hexaédrique voxel. Le p95 et le déplacement
convergent globalement, mais le maximum demeure au bord d'un appui de goujon.

| Pas | Éléments | Déplacement max | von Mises p95 | p99 | maximum |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 4,00 mm | 23 174 | 0,9125 mm | 36,59 MPa | 82,19 MPa | 393,50 MPa |
| 3,00 mm | 51 034 | 0,8844 mm | 38,86 MPa | 77,60 MPa | 418,05 MPa |
| 2,50 mm | 84 758 | 0,8794 mm | 40,87 MPa | 79,50 MPa | 377,91 MPa |
| 2,25 mm | 114 065 | 0,8782 mm | 41,16 MPa | 78,20 MPa | 430,63 MPa |

Le p99 reste inférieur à la limite chaude candidate de 216 MPa, mais les
maxima de 378 à 431 MPa la dépassent. Une singularité de liaison est possible,
mais non démontrée. La zone doit rester rouge jusqu'à un calcul avec contact,
précharge, congé réel et matériau non linéaire qualifié, puis corrélation.

Les deux enveloppes thermodynamiques 0D conservées comme charges de calcul sont
11,885 MPa / 620,41 hp en atmosphérique et 24,686 MPa / 1 601,20 hp en turbo.
Ce sont des résultats Cantera/Wiebe non corrélés, pas une puissance garantie du
moteur ni une validation de la culasse.

L'[audit du solveur moteur mobile](917_F37_ICE_ENGINE_FOAM.md) confirme que
`iceEngineFoam` n'est pas livré dans OpenFOAM Foundation 13. Le chemin disponible
`foamRun + XiFluid + multiValveEngine` a réellement franchi un changement de
topologie sur le tutoriel officiel 2D à deux soupapes. Ce smoke test n'emploie
pas la géométrie F37 et ne ferme donc aucune porte de combustion ou de cycle.

## Criblage d'impression 3D métallique

La comparaison de 34 orientations retient `scan_y_down` comme meilleur score
virtuel. Sous l'hypothèse d'échelle :

| Grandeur LPBF | Résultat |
| --- | ---: |
| Enveloppe orientée | 125,25 × 96,75 × 206,25 mm |
| Couches à 50 µm | 4 125 |
| Temps d'exposition à 60 cm³/h | 17,75 h, hors surcoûts |
| Aire de surplomb descendant | 112,85 cm² |
| Volume proxy de supports-colonnes | 759,95 cm³ |
| Fraction grossière sans appui | 1,259 %, **échec** face à 0,5 % |
| Épaisseur p01 échantillonnée | 0,75 mm, **échec** face à 1,5 mm |
| Volume fermé détecté au voxel grossier | 0,184 cm³ (23 voxels), **échec** |
| Masse conditionnelle à 2 670 kg/m³ | 2,842938 kg |

Le calcul CalculiX « plaque bloquée » à maille 3 mm prédit p95 = 165,57 MPa,
p99 = 473,94 MPa, maximum = 1 634,42 MPa et déplacement = 1,327 mm lors d'un
refroidissement uniforme de 280 à 20 °C. Au-delà de l'élasticité, ces
contraintes ne sont pas physiques : le résultat sert seulement de signal de
risque. Il manque l'activation des couches, la trajectoire laser, la plasticité,
les supports réels, le contact plateau, l'anisotropie, la séparation et le
traitement thermique.

Le rapport LPBF courant a été régénéré sur le contrat et le rapport CAO de cette
édition; ses empreintes d'entrée concordent. Cette cohérence de provenance ne
change pas son verdict : les trois échecs épaisseur/support/volume fermé restent
des portes de conception et `metal_print_authorized` reste à `false`.

## Carte des surépaisseurs et finitions

Les valeurs suivantes sont des hypothèses d'usinage conditionnelles :

| Zone | Surépaisseur |
| --- | ---: |
| Deck de combustion | +1,00 mm axial |
| Registre cylindre | +0,50 mm radial |
| Logements de sièges | +0,30 mm radial |
| Alésages de guides | +0,20 mm radial |
| Passages de goujons | +0,30 mm radial |
| Appuis du porte-axes | +0,80 mm axial |
| Alésages des axes | +0,30 mm radial |

Les pilotes/finitions candidats sont : inserts de bougie M10×1 sur pilote
8,3 mm, goujons et porte-axes repris à Ø10,74 mm depuis Ø10,14 mm, bouchons de
galerie M8×1 sur pilote 7,0 mm, sonde M10×1 sur pilote 8,5 mm. Profondeur utile,
classe de filetage, rayon de fond, engagement, couple, insert, rugosité et
contrôle ne sont pas encore libérés.

## Matrice de vérification

`PASSE` signifie seulement que le critère numérique énoncé est satisfait.

| Domaine | Critère | Résultat | État |
| --- | --- | --- | --- |
| Source | F36 lié par SHA-256 et corps étanche unique | oui | PASSE numérique |
| Échelle | unité physique confirmée | non | **BLOQUÉ** |
| Interfaces 917 | cylindre, goujons, admission, échappement mesurés | non | **BLOQUÉ** |
| CAO F37 | 6 familles B-Rep valides et STEP réimportables | oui | PASSE numérique |
| CAO culasse | un B-Rep complet unique incluant toutes les fonctions | non | **BLOQUÉ** |
| Maillage culasse | un corps étanche et intersection huile–gaz nulle | oui | PASSE audit local |
| Maillage culasse | accord des validateurs sur les sommets manifold | non, 0 contre 8 047 | **ÉCHEC** |
| Porte-axes/culasse | assise et collision 3D vérifiées sur peau finale | non | **BLOQUÉ** |
| Cinématique | quatre culbuteurs, enveloppes sans collision statique | oui | PASSE statique |
| Cinématique | profil de came/contact/flexion/spintron corrélés | non | **BLOQUÉ** |
| Porte-axes | enveloppe de magnitude pivot 2,15× appliquée | 4 080,7 N/zone | PASSE écran de magnitude |
| Porte-axes | direction réelle/résultante pivot complète | non | **BLOQUÉ** |
| Porte-axes | FoS analytique à chaud >= 2 | 2,463 | PASSE écran |
| Porte-axes | flèche analytique <= 0,150 mm | 0,138794 mm | PASSE écran |
| Porte-axes | convergence CalculiX déplacement/p95 < 5 % | 1,065 % / 0,0345 % | PASSE numérique |
| Porte-axes | flèche CalculiX fine <= 0,150 mm | 0,093252 mm | PASSE écran |
| Porte-axes | maximum local CalculiX sous 200 MPa | 208,734 MPa | **ÉCHEC** |
| Porte-axes | contact non linéaire et carte chaude qualifiée | non | **BLOQUÉ** |
| Structure culasse | p99 sous 216 MPa | oui | PASSE écran global |
| Structure culasse | pointe locale sous 216 MPa | non | **ÉCHEC** |
| Huile | pertes analytiques sous les plafonds | oui | PASSE écran |
| Huile | débouchés, drainage, propreté et banc corrélés | non | **BLOQUÉ** |
| Refroidissement | point LBM seul lié sous 260 °C | 237,98 °C | PASSE écran non sélectionné |
| Refroidissement | conductivité −20 % sous 260 °C | 301,34 °C | **ÉCHEC** |
| CFD | convergence temporelle FluidX3D | oui | PASSE numérique |
| CFD | indépendance spatiale FluidX3D à 5 % | non | **ÉCHEC** |
| CFD | deuxième solveur OpenFOAM géométriquement résolu terminé | oui | PASSE exécution |
| CFD | accord FluidX3D/OpenFOAM sur chaleur et perte de charge | non | **ÉCHEC** |
| Refroidissement | écran solide lié au `h` OpenFOAM sous 260 °C | 617,42 °C | **ÉCHEC** |
| CFD carénage 20 mm | bilan énergie et accord de deux mailles RANS | non | **ÉCHEC** |
| Refroidissement carénage 20 mm | meilleur écran solide lié RANS sous 260 °C | 468,09 °C | **ÉCHEC** |
| LPBF | enveloppe dans 250 × 250 × 325 mm | oui, conditionnel | PASSE écran |
| LPBF | fraction grossière non supportée < 0,5 % | 1,259 % | **ÉCHEC** |
| LPBF | épaisseur p01 >= 1,5 mm | 0,75 mm | **ÉCHEC** |
| LPBF | volume fermé au voxel de 2 mm = 0 | 0,184 cm³ | **ÉCHEC** |
| LPBF | simulation procédé calibrée/coupons qualifiés | non | **BLOQUÉ** |
| Inspection | CT, FPI, CMM, étanchéité et débit acceptés | non | **BLOQUÉ** |
| Essais | banc de flux, spintron, thermique, moteur | non | **BLOQUÉ** |

## Reproduction

Les commandes supposent que le scan et les maillages dérivés, volontairement
non versionnés, sont présents sous `work/`.

### CAO fonctionnelle F37 sur environnement x86-64

```bash
python twins/reference-917-engine/source/build_f37_manufacturing_definition.py \
  --contract twins/reference-917-engine/f37-manufacturing-definition.json \
  --geometry-report work/917-scan-conforming-f36/run-013/geometry-report.json \
  --head-stl work/917-scan-conforming-f36/run-013/917-head-scan-conforming-4v-f36.local.stl \
  --output work/917-scan-conforming-f37/cad

python twins/reference-917-engine/source/render_f37_manufacturing_definition.py \
  --head work/917-scan-conforming-f36/run-013/917-head-scan-conforming-4v-f36.local.stl \
  --cad-dir work/917-scan-conforming-f37/cad \
  --output work/917-scan-conforming-f37/917-head-f37-manufacturing-definition.png
```

### Cinématique, huile et résistance

```bash
python3 twins/reference-917-engine/source/screen_f37_rocker_kinematics.py \
  --contract twins/reference-917-engine/f37-manufacturing-definition.json \
  --geometry-report work/917-scan-conforming-f36/run-013/geometry-report.json \
  --cad-report work/917-scan-conforming-f37/cad/f37-cad-report.json \
  --valve-lift-mm 12 \
  --output work/917-scan-conforming-f37/kinematics

python3 twins/reference-917-engine/source/screen_f37_oil_system.py \
  --contract twins/reference-917-engine/f37-manufacturing-definition.json \
  --output work/917-scan-conforming-f37/oil

python3 twins/reference-917-engine/source/screen_f37_carrier_strength.py \
  --contract twins/reference-917-engine/f37-manufacturing-definition.json \
  --kinematics work/917-scan-conforming-f37/kinematics/f37-rocker-kinematic-report.json \
  --output work/917-scan-conforming-f37/strength
```

La FEA 3D CalculiX du porte-axes se reproduit par la cible canonique ci-dessous.
Elle vérifie l'identifiant de l'image avant exécution et consigne les versions,
la commande ainsi que les SHA-256 des entrées et sorties :

```bash
make 917-manufacturing-f37-carrier-fea
```

L'appel Python direct n'est pas la recette publiée, car il ne prouve pas à lui
seul que l'environnement CalculiX/Gmsh épinglé a été employé. L'identifiant
`sha256:4a19…` atteste le snapshot Docker local exécuté, mais aucun digest GHCR
récupérable ni verrouillage complet des paquets APT n'est publié. La
reproductibilité de cet environnement est donc classée
`local_runtime_snapshot_not_portably_reproducible`.
Les quatre charges de 1 898 N sont décomposées suivant les axes de soupape
inclinés de ±18° dans le plan local yz; le cas ne supprime donc pas les
composantes latérales opposées des deux rangées.

### CFD/thermique et LPBF

```bash
python3 twins/reference-917-engine/source/build_f36_final_cfd_thermal_evidence.py \
  --raw work/917-scan-conforming-f36/final-cross-solver-013/raw-remote \
  --openfoam-case work/917-scan-conforming-f36/final-cross-solver-013/openfoam/coarse \
  --openfoam-case work/917-scan-conforming-f36/final-cross-solver-013/openfoam/shroud-gap10-nonslip-coarse \
  --openfoam-case work/917-scan-conforming-f36/final-cross-solver-013/openfoam/shroud-gap20-kepsilon-base7p5 \
  --openfoam-case work/917-scan-conforming-f36/final-cross-solver-013/openfoam/shroud-gap20-kepsilon-base5 \
  --openfoam-case work/917-scan-conforming-f36/final-cross-solver-013/openfoam/shroud-gap20-kepsilon-long-base7p5 \
  --openfoam-case work/917-scan-conforming-f36/final-cross-solver-013/openfoam/shroud-gap20-kepsilon-long-base5 \
  --openfoam-case work/917-scan-conforming-f36/final-cross-solver-013/openfoam/shroud-gap20-laminar-base7p5 \
  --openfoam-case work/917-scan-conforming-f36/final-cross-solver-013/openfoam/shroud-gap20-laminar-base5 \
  --output work/917-scan-conforming-f36/final-cross-solver-013

python3 twins/reference-917-engine/source/compile_f37_lpbf_manufacturing_plan.py \
  --printability work/917-scan-conforming-f37/lpbf-exact/lpbf-printability-report.json \
  --f37-head-mesh-report work/917-scan-conforming-f37/head-mesh-proof/f37-printable-head-mesh-report.json \
  --locked-plate work/917-scan-conforming-f36/lpbf-locked-plate-p3/report.json \
  --f37-contract twins/reference-917-engine/f37-manufacturing-definition.json \
  --f37-cad-report work/917-scan-conforming-f37/cad/f37-cad-report.json \
  --output work/917-scan-conforming-f37/lpbf
```

### Contrôles automatisés

```bash
make 917-manufacturing-f37-cad
make 917-manufacturing-f37-head-mesh
make 917-manufacturing-f37-screens
make 917-manufacturing-f37-render
make 917-manufacturing-f37-check

python3 tests/test_917_f36_final_cfd_thermal.py -v
F37_EVIDENCE_DIR=work/917-scan-conforming-f37/cad \
  python3 tests/test_917_f37_manufacturing_definition.py -v
make 917-scan-conforming-4v-f36-check
make check
```

## Gamme industrielle exigée avant fabrication

1. Confirmer l'échelle et les interfaces 917 par une métrologie indépendante ou
   des pièces de référence traçables.
2. Reconstruire un B-Rep unique de la culasse, intégrer effectivement les
   galeries, appuis, pilotes, surépaisseurs et rayons, puis vérifier chaque
   débouché et chaque accès outil.
3. Fermer la flèche du porte-axes et les pointes de contrainte avec une FEA 3D
   convergée, contacts, précharges, propriétés dépendantes de la température et
   fatigue thermomécanique.
4. Qualifier lot poudre, machine, orientation, paramètres, supports, coupons,
   traitement sur plaque, HT2 et HIP si justifié.
5. Trancher les vrais supports et démontrer retrait, dépoudrage et propreté sans
   contact sur une surface fonctionnelle.
6. Usiner depuis des datums A/B/C libérés; vérifier la chaîne de cotes à froid
   et à chaud, les ajustements, filetages, rugosités, couples et précharges.
7. Réaliser CT volumique, ressuage fluorescent, CMM, planitude, rugosité,
   étanchéité, pression et débit des quatre branches.
8. Corréler le refroidissement par thermocouples et la distribution par banc de
   flux et spintron; procéder ensuite à un banc moteur progressif instrumenté
   après revue professionnelle.

## Limites non négociables

- Une peau reconstruite et étanche n'est pas la métrologie d'une culasse 917.
- Une CAO valide ne prouve ni l'usinabilité complète ni l'assemblage à chaud.
- Un audit topologique local ne prévaut pas sur un désaccord entre validateurs;
  la cause des 8 047 sommets signalés doit être reproduite et corrigée.
- Deux équations équivalentes ne sont pas deux essais indépendants.
- Une température stationnaire nominale n'est pas une fatigue thermomécanique.
- Un calcul OpenFOAM terminé mais en fort désaccord avec FluidX3D n'est pas une
  validation croisée du refroidissement.
- Un audit de voxel et une image de tranche ne sont pas un fichier machine
  qualifié.
- Une valeur typique fournisseur n'est pas une contrainte admissible du lot
  imprimé.

Tant qu'une seule porte physique de la matrice reste ouverte, la mention
« imprimable » doit être comprise comme **géométrie candidate à préparer pour
une revue LPBF**, et non comme autorisation de construire une pièce moteur.
Les identifiants locaux historiques `printable-proof` et
`f37-printable-head-mesh-report.json` obéissent à cette définition restrictive :
ils nomment un artefact d'audit topologique, jamais une preuve d'imprimabilité.
