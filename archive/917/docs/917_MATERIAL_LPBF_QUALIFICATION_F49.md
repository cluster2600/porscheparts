# F49 — matière et procédé LPBF pour les culasses turbo 2V/4V

F49 sélectionne une **route d'éprouvettes**, pas une matière libérée. Le candidat
principal est **Aheadd CP1, couches de 50 µm sur Velo3D Sapphire, puis 400 °C
pendant 4 h**. A20X A205-T7 reste le candidat de repli si les essais montrent
que la résistance de CP1 à chaud est insuffisante. Cette décision s'applique de
la même manière aux variantes 2V et 4V.

Le lot ne crée aucune CAO, aucun maillage et aucune cote d'interface. Il lie par
SHA-256 les écrans F45, la politique interne F47 et les chargements F47. La
peau externe reste exclusivement celle des contours de scan F43, identique en
octets pour 2V et 4V : F49 interdit toute modification de forme, toute mise à
l'échelle uniforme ou directionnelle et toute réutilisation d'un ancien proxy.
Les cylindres analytiques circulaires restent limités aux fonctions internes
explicitement autorisées par F47. Les pressions et températures de
gaz F47 restent des enveloppes 0D non corrélées; elles ne définissent ni la
température du métal, ni une pression d'épreuve.

## Décision matière

| Route | Preuve publique utile | Lacune bloquante | Rôle F49 |
| --- | --- | --- | --- |
| Aheadd CP1, 400 °C/4 h | 323 MPa de Rp0,2, 342 MPa de Rm, 12,8 % d'allongement et 187 W/mK à l'ambiante; stabilité annoncée 250–300 °C | aucune courbe publique de traction, conductivité, fatigue, fluage ou relaxation à chaud pour la route exacte | premier candidat d'éprouvettes |
| A20X A205-T7 | Rp0,2 publiée de 311 MPa à 200 °C et 215 MPa à 250 °C | conductivité et gamme complète thermo-mécanique absentes; recette T7 propriétaire; domaine d'emploi annoncé seulement jusqu'à 190 °C | repli résistance à chaud |
| AlSi10Mg-T6 | procédé EOS M290 mature et conductivité ambiante 155–165 W/mK | carte chaude et tenue fatigue/TMF absentes; la fiche EOS avertit que T6 peut accroître la porosité | témoin de procédé mature |
| AlF357, famille AlSi7Mg | Rp0,2 265 MPa, Rm 330 MPa, A 11,5 % et 150 W/mK à l'ambiante | carte chaude, densité de la route et allowables de défaut absents | second témoin Al-Si |
| 2618-T61 usiné/forgé | nuance encore couverte par AMS4132J:2026; données historiques à chaud disponibles | ce n'est pas une poudre LPBF; les points NASA sont lus sur un graphe d'extrusion T6511 après 100 h, donc non transférables | référence conventionnelle seulement |

Sources primaires principales : [fiche CP1 Constellium](https://assets.foleon.com/eu-central-1/de-uploads-7e3kk3/41170/product_sheet_aheadd_cp1_nov_2021docx.e81a7d073ebf.pdf),
[fiche CP1 Velo3D](https://velo3d.com/wp-content/uploads/2025/04/Velo3D-Material-Datasheet-Aluminum-CP1.pdf),
[capacité CP1 de PWR](https://www.pwr.com.au/products/additive-manufacturing),
[A20X ECKART](https://www.eckart.net/en/download/document/view/id/51/),
[AlSi10Mg et AlF357 EOS](https://www.eos.info/metal-solutions/metal-materials/aluminium),
[AMS7074](https://saemobilus.sae.org/standards/ams7074-aluminum-alloy-powder-11zr-10fe-aheadd-cp1),
[AMS4132J](https://saemobilus.sae.org/standards/ams4132j-aluminum-alloy-die-hand-forgings-rolled-rings-23cu-16mg-11fe-10ni-018si-007ti-2618-t61-solution-precipitation-heat-treated)
et [données NASA 2618](https://ntrs.nasa.gov/api/citations/19930022454/downloads/19930022454.pdf).

Les valeurs Velo3D proviennent d'une seule machine et de 56 éprouvettes
verticales usinées. Leurs minima à 20 °C — 297 MPa de Rp0,2, 331 MPa de Rm et
13,9 % d'allongement — sont un repère de réception si la route est reproduite à
l'identique, jamais un allowable de conception.

## Machine et placement à qualifier

La machine de référence est une **Velo3D Sapphire standard chez PWR**. Le
constructeur publie un volume cylindrique de 315 mm de diamètre sur 400 mm de
haut, deux lasers de 1 kW et un racleur sans contact. PWR publie l'emploi de CP1
en 50 et 100 µm. Aucun engagement du fournisseur pour cette pièce n'est acquis.

Le test d'encombrement utilise uniquement l'enveloppe minimale demandée
225 × 120 × 98 mm. Pour un roulis de criblage de 35° autour de l'axe long :

\[
W' = W\cos\phi + H\sin\phi,\qquad
H' = W\sin\phi + H\cos\phi
\]

\[
D_{requis}=\sqrt{L^2+W'^2}.
\]

Il donne 225 × 154,509 × 149,106 mm et
\(D_{requis}=272,943\) mm : l'enveloppe nue tient, avec 42,057 mm de jeu
diamétral et 250,894 mm en hauteur. Ce calcul exclut les surépaisseurs, le
plateau, les supports et la marge du racleur. `final_build_fit_verified` reste
donc faux. Le fournisseur doit comparer 25°, 35° et 45° dans Flow avant de
choisir l'orientation.

## Supports, usinage et dépoudrage

- Aucun support n'est autorisé dans les passages de gaz ou d'huile.
- Aucun contact de support n'est accepté sur deck, siège, guide, palier ou
  autre surface fonctionnelle.
- Les supports externes doivent être sacrificiels, accessibles et attachés à
  des plages non fonctionnelles destinées à être usinées.
- L'accès de dépoudrage et son contrôle par endoscope/CT doivent être démontrés
  avant le fichier machine.
- Une projection de supports ou une image de tranche n'est pas une preuve de
  retrait, de rigidité ni de non-collision avec le racleur.

Les surépaisseurs ci-dessous sont des **valeurs de départ à négocier avec le
prestataire LPBF et l'usineur**, pas des cotes libérées : deck et brides de ports
+1,0 mm axial; logements de sièges +0,30 mm radial; guides +0,20 mm radial;
passages de goujons +0,30 mm radial; appuis de porte-arbres +0,80 mm axial;
alésages d'arbres +0,30 mm radial. Les filetages sont imprimés pleins ou en
pilotes puis usinés; type d'insert, engagement et classe restent à définir.

## Traitement thermique et HIP

La route de base CP1 reprend strictement la fiche Constellium : 400 °C pendant
4 h, sans trempe. Elle ne doit pas être appelée T6. Le fabricant indique qu'un
HIP à 400 °C est possible, mais ne publie ni pression ni durée. F49 impose donc
deux branches cofabriquées :

1. CP1 400 °C/4 h sans HIP;
2. CP1 avec cycle HIP fournisseur à 400 °C, paramètres encore nuls, puis gamme
   finale approuvée.

Le choix HIP ne sera fait qu'après comparaison CT, traction à chaud,
conductivité, HCF/LCF/TMF et stabilité dimensionnelle. Le T7 A20X est une gamme
propriétaire distincte et n'est jamais transposé à CP1.

## Éprouvettes à chaud

Le criblage exige au moins trois constructions indépendantes. Chaque route est
échantillonnée en X, Y, Z et 45°, à 20, 150, 200, 250 et 300 °C, avec trois
répétitions par cellule pour le criblage. Ce nombre ne suffit pas à créer un
allowable statistique; le plan de population final reste à signer.

Les essais obligatoires sont :

- traction à 20 °C suivant
  [ASTM E8/E8M-25](https://store.astm.org/e0008_e0008m-25.html) et à chaud
  suivant [ASTM E21-20](https://store.astm.org/e0021-20.html), avec Rp0,2, Rm,
  allongement et striction;
- diffusivité suivant [ASTM E1461-13(2022)](https://store.astm.org/e1461-13.html),
  chaleur massique et masse volumique sur le même état, puis
  \(k(T)=\alpha(T)\rho(T)c_p(T)\);
- module, coefficient de Poisson, dilatation, plasticité et dureté à chaud;
- HCF, LCF, TMF, fluage et relaxation aux températures de service;
- métallographie, défauts entaillés, surfaces brutes/usinées, orientations et
  témoins de parois minces, surplombs, supports et dépoudrage.

Les rapports chargent la matière depuis le même lot, la même position plateau,
la même construction, le même traitement et le même état de surface que la
pièce. Les courbes minimales à chaud, les facteurs statistiques et les
abattements défaut/surface sont volontairement `null` jusqu'aux résultats.

## Contrat AdditiveFOAM

Le modèle thermique de procédé doit fermer une équation de type

\[
\rho c_p\frac{\partial T}{\partial t}
=\nabla\cdot(k\nabla T)+Q_{laser}-Q_{pertes}+Q_{latent}.
\]

Il requiert la trajectoire et le profil du laser fournisseur, l'absorptivité,
\(k(T)\), \(c_p(T)\), masse volumique, solidus/liquidus, chaleur latente,
émissivité, contact plateau/supports et données de bain fondu sur éprouvette.
Aucune de ces entrées route-machine n'est complète aujourd'hui.

Le solveur doit rester sous son plafond numérique de 3 300 K, conserver des
champs finis et converger entre les deux derniers niveaux : moins de 5 % sur
les dimensions du bain et le volume liquide, moins de 3 % sur T-p99. Le bilan
énergétique ne reçoit pas de seuil inventé : il sera fixé avec le cas étalon.
AdditiveFOAM n'a pas été exécuté ni calibré pour CP1 dans F49.

## Contrat thermomécanique

Les variantes 2V et 4V reçoivent la même carte matière et les mêmes règles. La
carte doit fournir en fonction de la température : conductivité, capacité
calorifique, masse volumique, module, coefficient de Poisson, dilatation,
plasticité, HCF/LCF/TMF, fluage, relaxation et abattements défaut/surface/
orientation.

F47 est lié par hash, mais ses charges ne sont pas corrélées. Il manque aussi le
maillage solide, les ensembles de surfaces, le cycle de mission, les limites de
plastification/fatigue/fluage et la planéité admissible des plans de joint.
Une analyse ne pourra être acceptée qu'après convergence maillage/pas/cycles et
corrélation par thermocouples, pression cylindre et essais de fuite.

## CT, CND et critères d'acceptation

Le site et l'équipement doivent être qualifiés suivant
[ISO/ASTM 52920:2023](https://www.iso.org/standard/76911.html) et
[ISO/ASTM TS 52930:2021](https://www.iso.org/standard/79527.html). La poudre est
gérée suivant [ISO/ASTM 52928:2024](https://www.iso.org/standard/78527.html) et
la fiche matière suivant
[ISO/ASTM 52929:2025](https://www.iso.org/standard/84733.html). Les données de
surveillance Assure doivent être archivées suivant
[ISO/ASTM 52953:2025](https://www.iso.org/standard/84117.html); cette archive ne
vaut pas acceptation de la pièce.

Le CT industriel suit la série ISO 15708 courante 2024–2025. Taille de voxel,
POD et défaut admissible par zone restent nuls jusqu'à ce que la fatigue et un
artefact à défauts connus fixent la détectabilité nécessaire. Le ressuage suit
[ASTM E1417/E1417M-21e1](https://store.astm.org/e1417_e1417m-21.html), avec
procédure, zones et limites signées avant fabrication. CMM, épreuve de pression,
fuite inter-circuits, débit et propreté restent également sans seuil tant que
le plan d'interface et les charges corrélées manquent.

## Verdict

- **Candidat matière/processus :** CP1 50 µm, 400 °C/4 h, à éprouver.
- **Repli :** A20X A205-T7, à éprouver avec sa gamme propriétaire.
- **Machine :** Sapphire chez PWR, compatible avec l'enveloppe nue seulement.
- **Autorisation d'imprimer :** non.
- **Autorisation de démarrer le moteur :** non.

Le contrat déterministe est
`twins/reference-917-engine/material-lpbf-qualification-f49.json`; le tableau
matière est dans
`twins/reference-917-engine/evidence/f49-material-lpbf/material-comparison.csv`.

## Reproduction

```bash
make 917-material-lpbf-f49
make 917-material-lpbf-f49-check
```
