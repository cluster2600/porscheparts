# Levier intérieur de porte 993 AlSi10Mg — jumeau F0

## Décision

Ce levier est un candidat additif plus pertinent qu'une vis ou qu'une simple
plaque : petite série, chape et pont intégrés, cinq poches ouvertes et reprise
d'alésages possible dans une seule ébauche. Le gain n'est pas encore démontré
face à une pièce forgée ou usinée, mais l'intégration géométrique justifie le
criblage LPBF.

PorscheFanatics rattache la fonction aux références PET gauche
`993 555 851 00` et droite `993 555 852 00`. FVD publie pour sa paire
aftermarket une enveloppe `108 × 45 × 27 mm`, une masse totale `180 g` et un
aluminium « haute résistance » sans grade. Ces données ne décrivent ni les
surfaces OEM, ni le pivot, ni les fixations, ni la tringlerie. Le F0 est donc
un concept indépendant dans cette seule enveloppe, pas une copie montable.

## Route matière de criblage

La route cohérente retenue est `EOS Aluminium AlSi10Mg`, EOS M 290,
`AlSi10Mg_FlexM291 2.01`, couches de `30 µm`, état brut de fabrication. La
fiche EOS publie notamment une densité minimale de `2,67 g/cm³`, une limite
d'élasticité verticale de coupon de `233 MPa`, une résistance ultime minimale
de `461 MPa`, une endurance de coupon tourné entièrement alterné de `110 MPa`
à `20 millions` de cycles et une conductivité verticale de `100 W/(m·K)`.

Ces valeurs restent des propriétés de coupons. Elles ne sont pas des
admissibles de poignée : état de surface brut, entailles, porosité, orientation,
traitement, température, corrosion et lot doivent être qualifiés.

## Résultats réellement exécutés

| Domaine | Exécution | Résultat utile | Limite d'autorité |
|---|---|---|---|
| CAO | build123d 0.11.1 / OCCT 7.9.3.1 | BREP unique `108 × 45 × 27 mm`, STEP normalisé reproductible, volume `26 824,19 mm³` | formes fonctionnelles hypothétiques |
| Masse | `m=ρV` | `71,621 g` par levier, soit `143,241 g` la paire | la paire FVD peut inclure d'autres éléments |
| Analytique | flexion, cisaillement, Von Mises, flèche, pression, dilatation | `45,633 MPa`, `0,282 mm`, croissance libre `0,1426 mm` sous `150 N` et `+60 K` synthétiques | poutre nominale, pas l'interface réelle |
| LPBF | section réelle de toutes les couches | `2 664` couches, `roll_y_45`, supports proxy `2 714,4975 mm³`, p01 `2 mm`, aucun vide piégé au voxel `0,75 mm` | pas EOSPRINT ni simulation laser |
| CalculiX | six cas C3D10 sur trois maillages | maillage fin `31 666` nœuds ; p95 `45,227 MPa` froid et `46,546 MPa` chaud ; flèche max froide `1,033 mm` | appuis, force et températures synthétiques |
| Fatigue | Goodman zéro-vers-pic contre coupon EOS | ratio proxy `4,626`, aucune durée de vie calculée | non transférable à la pièce |
| OpenUSD | `usd-convert-cad 0.2.0`, OpenUSD 26.8 | asset binaire Z-up, millimètres | échange seulement |
| Validation NVIDIA | `nvidia_usd_validate 1.21.0` | asset et scène sans règle en échec | pas de profil SimReady complet |
| PhysX | ovstage 0.1.1.355824, ovphysx 0.5.11 CPU | témoin de `10 g` stabilisé de `35` à `29 mm` en `240` pas | contact logiciel, pas mécanisme de porte |
| PhysicsNeMo | non exécuté | six cas synthétiques ne constituent pas un dataset de surrogate | bloqué jusqu'à des cas corrélés |
| Content Agents / OVRTX | préflight exécuté puis arrêté | accès OpenBao sains, aucune instance active | aucune propriété LLM ni rendu final |

La comparaison des deux maillages les plus fins donne `1,143 %` de variation
du p95 froid et `0,276 %` du p95 chaud, sous le seuil numérique de criblage de
`10 %`. Cela indique seulement la stabilité de ce modèle. Le maximum local
froid atteint `174,657 MPa` et le maximum chaud `185,636 MPa` près des appuis
idéalisés ; ni ces pics ni le p95 ne valent marge de sécurité de la pièce.

## Pourquoi aucune impression n'est autorisée

- aucune mesure du levier OEM, des axes, portées, fixations, butées ou jeux ;
- aucune géométrie ni raideur de serrure, tringlerie, trim ou porte ;
- aucun effort réel, cas de mauvais usage, choc ou spectre cyclique ;
- aucune analyse de contact, usure, précharge, corrosion ou couple galvanique ;
- aucun calcul de bain de fusion, distorsion de build ou collision recoater ;
- aucun projet EOSPRINT, coupon de lot, première pièce, CT/CND ou métrologie ;
- aucun essai d'ouverture, d'endurance, de vieillissement ou d'évacuation ;
- aucune revue d'ingénierie automobile signée.

## Gates avant tout prototype

Dans cet ordre, parce que chaque étape conditionne la suivante :

1. Acquérir une paire identifiée et mesurer pivot, butées, interfaces, jeux,
   portées et trajectoire du mécanisme.
2. Mesurer l'effort d'ouverture et les cas hors axe, puis définir un spectre
   cyclique.
3. Ajouter rayons, surépaisseurs et orientation LPBF à partir du procédé
   effectivement retenu.
4. Contrôler dimensionnellement, puis conduire essais statiques, cycliques et
   ouverture d'urgence sur banc avant tout montage véhicule.

La comparaison avec CNC et tôle reste obligatoire : si les mesures montrent que
la chape peut être usinée ou assemblée simplement, le LPBF n'est pas retenu.

Les preuves, leurs empreintes et les refus de libération sont regroupés dans
[`twins/993-door-opener-lever-alsi10mg-f0/evidence/`](../../twins/993-door-opener-lever-alsi10mg-f0/evidence/).
