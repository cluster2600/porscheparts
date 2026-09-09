# Porsche 917 — F42.2, matériau et processus LPBF

## Verdict

La sélection finale reste **bloquée**. Cinq alliages aluminium effectivement
proposés en LPBF ont été comparés à partir de sources fabricant uniquement.
Aucun dossier public ne fournit simultanément traction, conductivité, fatigue
et fluage numériques sur toute la bande 260–350 °C.

Le candidat de développement provisoire est **Constellium Aheadd HT1 avec
traitement HT2**, parce que sa fiche publie le seul point de traction proche de
la cible : `Rp0,2 = 216 MPa`, `Rm = 265 MPa` et `A = 5 %` à 250 °C en direction
Z. Ce choix autorise des coupons, pas une pièce. La fiche s'arrête à 250 °C et
ne publie ni cycle HT2 complet, ni `k(T)`, ni fatigue/fluage à chaud.

Cette limite est décisive : F42.1 donne encore 267,54 °C au meilleur point
CalculiX réellement exécuté et 279,91 °C pour la meilleure option du réseau.
HT1 ne peut donc pas être déclaré compatible avec le champ actuel.

## Comparaison primaire

| Alliage/processus | Preuve LPBF | Données publiques utiles | Limite 260–350 °C | Décision |
|---|---|---|---|---|
| EOS AlSi10Mg, M290 30 µm, T6 | TRL 9 | RT Z : 250/310 MPa, A=11 %; k=165/155 W/mK sans T publiée | aucune traction/k(T)/fatigue/fluage dans la bande | référence seulement |
| EOS AlF357, M290 30 µm, T6-like | TRL 7 | RT Z : 265/330 MPa, A=11,5 %; k=150 W/mK sans T publiée | aucune propriété numérique dans la bande | candidat secondaire |
| EOS–Constellium CP1, M290 60 µm | TRL 3 | RT Z : 300/340 MPa, A=10 %; traitement 4 h à 400 °C | stabilité 250–300 °C qualitative, pas de k(T)/traction chaude | alternative haute conductivité |
| Constellium Aheadd HT1 HT2 | coupons M290 60 µm | 270/293 MPa à 200 °C; 216/265 MPa à 250 °C, direction Z | rien de numérique entre 260 et 350 °C | candidat coupons provisoire |
| APWORKS Scalmalloy | production LPBF APWORKS | RT : 480/520 MPa, A=13 %, densité 2,67 | aucune carte chaude publique | rejeté pour calcul chaud actuel |

Les valeurs sont typiques et restent liées à l'état, l'orientation, la machine
et le traitement de la source. Aucune interpolation ou conversion de
conductivité électrique en conductivité thermique n'a été effectuée.

Sources fabricant :

- [EOS AlSi10Mg](https://www.eos.info/metal-solutions/data-sheets/all-processes-and-materials?id=eos-aluminium-alsi10mg)
- [EOS AlF357](https://www.eos.info/metal-solutions/data-sheets/all-processes-and-materials?id=eos-aluminium-alf357)
- [EOS–Constellium CP1](https://www.eos.info/metal-solutions/data-sheets/all-processes-and-materials?id=eos-aluminium-constellium-cp1)
- [Constellium Aheadd CP1](https://assets.foleon.com/eu-central-1/de-uploads-7e3kk3/41170/product_sheet_aheadd_cp1_nov_2021docx.e81a7d073ebf.pdf)
- [Constellium Aheadd HT1](https://assets.foleon.com/eu-central-1/de-uploads-7e3kk3/41170/aheadd_ht1_fact_sheet_230620.ccac52e244fb.pdf)
- [APWORKS Scalmalloy](https://www.apworks.de/scalmalloy)

## Route processus provisoire

L'enveloppe F41/F42 n'est pas modifiée. La séquence à qualifier est : lot
poudre, machine et paramètres gelés; coupons témoins dans le même build;
détente sur plateau selon le fournisseur; dépoudrage avec bilan massique;
séparation fil; traitement propre à l'alliage; CT; comparaison HIP/non-HIP;
usinage des datums; CT/CND; usinage final; CMM, propreté, pression, débit et
étanchéité.

Recettes publiques pouvant être reproduites uniquement sur leur processus :

- AlSi10Mg EOS T6 : 30 min à 530 °C, trempe eau immédiate, 6 h à 165 °C puis
  refroidissement air. EOS avertit qu'une hausse de porosité est possible;
- AlF357 T6-like : 30 min à 540 ±6 °C, trempe eau immédiate, 6 h à
  165 ±6 °C puis refroidissement air;
- CP1 EOS : 4 h à 400 °C sans exigence de trempe;
- HT1 : HT2 fabricant, mais le cycle exact n'est pas public;
- Scalmalloy : route APWORKS contrôlée, recette publique insuffisante.

Le **HIP n'est pas prescrit**. Une moitié des coupons candidats doit rester sans
HIP et l'autre suivre une recette définie par le fournisseur. Le HIP ne sera
retenu que si CT, traction chaude, fatigue et stabilité dimensionnelle montrent
un gain sans perte inacceptable. Température, pression et durée restent nulles
avant accord matière–machine.

Les surépaisseurs d'usinage restent également nulles : aucun essai de
compensation ou capabilité n'existe. Le deck, le registre cylindre, les alésages
de sièges/guides, les interfaces porte-culbuteurs, filetages, galeries d'huile et
plans de joints devront tous être repris après qualification de la route.

## Sièges, guides et corrosion

La nuance des sièges et des guides n'est pas sélectionnée. Chaque couple
aluminium/siège et aluminium/guide doit être évalué selon ASTM G71 dans un
électrolyte réellement représentatif : condensat salin et huile contaminée par
l'eau caractérisés sur banc. Il faut mesurer courant galvanique, perte de
masse, piqûres et corrosion de crevasse, puis vérifier retrait, fretting,
étanchéité et maintien de l'interférence après cycles thermiques.

Les ajustements ne seront calculés qu'après mesure des CTE du corps, du siège et
du guide. Les anodisations ou conversions externes doivent être masquées sur
deck, chambre, alésages d'interférence, filetages et liaisons électriques. Aucun
produit d'assemblage ou revêtement de joint n'est autorisé sans essai dédié.

## Plan coupons et validation

Les éprouvettes utilisent le même lot poudre, la même machine, les mêmes
paramètres, positions de plateau et traitements que la pièce. Le plan couvre XY
et Z, bas/milieu/haut du build. Cinq répétitions par orientation, température et
état constituent un minimum d'ingénierie à réviser statistiquement, pas une
exigence des normes.

- poudre/métallographie : ISO/ASTM 52907 et 52908;
- CT des artefacts de défaut et de chaque tête : ASTM E1570 et
  ISO/ASTM TR 52905, résolution fixée après étude de probabilité de détection;
- traction à 20, 200, 260, 300 et 350 °C : ASTM E21-20/ISO 6892-2:2026;
- diffusivité, densité, chaleur massique, conductivité et CTE de 20 à 350 °C :
  ASTM E1461 et E228;
- HCF, LCF, TMF en/hors phase et fluage à 20, 260, 300 et 350 °C : ASTM E466-21,
  E606/E606M-21, E2368-25 et E139-24;
- corrosion galvanique et maintien des joints sièges/guides : ASTM G71.

Les seuils d'acceptation restent volontairement nuls. Ils dépendent du spectre
CHT/contraintes final, de la taille critique de défaut et de la fiabilité
requise. Les cadres de production et de contrôle sont
[ISO/ASTM 52904:2024](https://www.iso.org/standard/82919.html) et
[ISO/ASTM 52908:2023](https://www.iso.org/standard/81779.html).

## Interdictions maintenues

Il n'existe encore ni carte admissible, ni lot/machine qualifié, ni décision
HIP, ni CT avec probabilité de détection, ni interférence siège/guide validée,
ni CHT corrélée, ni essai moteur. L'impression métal et le démarrage restent
interdits.
