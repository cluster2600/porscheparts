# Schéma natif du coupon E0

2 octobre 2026 — **NON VALIDÉ POUR FABRICATION. BANC 3,3 V UNIQUEMENT.**

Ouvrir `coupon-e0.kicad_pro` dans **KiCad 9**, puis
[coupon-e0.kicad_sch](coupon-e0.kicad_sch). Le projet comporte trois feuilles A3 :
alimentation/commande, [drivers](drivers.kicad_sch), [128 LED](leds.kicad_sch).
Le [PDF de revue](../coupon-e0.pdf) est un export des mêmes feuilles.
Les fichiers natifs sont la source éditable ; après modification, réexporter le
PDF et relancer les contrôles. Aucune bibliothèque Python EDA n'est nécessaire.

## Ce qui est représenté

Le schéma transpose [coupon.md](../coupon.md), sa BOM et ses connexions :
172 composants, 541 broches, 172 nets, y compris 18 nets de broches laissées seules
(U6 OUT8–23, U7.11 et U8.1). Les labels globaux relient les trois feuilles.
Le test compare **tous** les groupes de broches de la netlist, les références et
les valeurs au contrat E0, en plus de l'ERC : une permutation de LED peut passer
l'ERC mais doit échouer à cette comparaison.

- U1–U6 : **DAP**, PowerPAD représenté par la broche KiCad **33**, à GND comme
  la broche 1. Ce numéro 33 est une convention CAO pour le pad, pas une patte
  supplémentaire dans la table des 32 broches TI.
- D1–D128 : symbole KiCad `Device:LED`, **1 = K, 2 = A**. Ces numéros sont une
  convention de symbole ; le repère cathode et l'association aux pastilles de
  l'empreinte Kingbright restent à examiner sur le dessin fabricant.
- TP1–TP8 : VCC, VLED, GND, SIN, SCLK, XLAT, BLANK, SOUT_TEST, dans cet ordre.
- Les deux PWR_FLAG déclarent l'alimentation externe sur VCC/GND à l'ERC ; ce ne
  sont ni des protections ni des composants à acheter. J2 ne transporte aucun
  rail du DK. Les connecteurs et S1 restent des références génériques à choisir.
- Toutes les empreintes sont **volontairement non attribuées**. Pas de PCB,
  de Gerber, de placement, de DRC PCB ni de commande d'assemblage.

## Contrôles reproductibles

Avec KiCad 9 et ses bibliothèques officielles installés, depuis la racine du dépôt :

```sh
python3 -m unittest discover -s tests -p 'test_993_rear_panel*.py' -v
kicad-cli sch erc --severity-all --exit-code-violations -o /tmp/coupon-e0-erc.rpt docs/projects/993-programmable-rear-panel/electronics/kicad/coupon-e0.kicad_sch
kicad-cli sch export pdf --exclude-pdf-property-popups --exclude-pdf-metadata -o /tmp/coupon-e0.pdf docs/projects/993-programmable-rear-panel/electronics/kicad/coupon-e0.kicad_sch
```

Sans `kicad-cli`, le test de schéma est explicitement ignoré : les tests Python
seuls ne valident pas le schéma. Le test travaille dans une copie temporaire et
exporte lui-même la netlist ; aucun export ancien n'est utilisé comme preuve.
Résultats et environnement réellement employés : [verification.md](../../verification.md).

## Revue avant routage

L'ERC ne simule ni tension, ni courant, ni timing, ni température. Un électronicien
doit revoir les séquences de deux alimentations, le risque d'alimentation parasite,
BLANK/IREF, le budget thermique, les empreintes et les connecteurs détrompés.
Le PCB devra définir contour, couches, cuivre, retours, découplage, vias thermiques,
distance optique et pas 2,5/4 mm. Aucun placement du schéma n'est une cote physique.
La limite du MCU bloqué avec DISPLAY_EN haut demeure : **S1 manuel et opérateur
présent** ; aucune coupure autonome garantie. Le plan E0-01 à E0-07 reste à exécuter
sur matériel après revue, routage/DRC et autorisation de fabrication.

## Provenance des symboles

Symboles officiels **KiCad Community, version 9.0.2**, distribués dans le paquet
Debian `kicad-symbols 9.0.2-1`, sous
[CC BY-SA 4.0 avec exception pour les circuits](https://www.kicad.org/libraries/license/)
(consulté le 2 octobre 2026). Les symboles utilisés sont incorporés dans les
feuilles pour leur ouverture ; aucune fiche fabricant propriétaire n'est copiée.

La petite bibliothèque locale `rear_panel_e0.kicad_sym` dérive de `74xx:74LVC125`
(héritage résolu, variante nommée SN74LVC125APW) et `74xGxx:74LVC1G04`
(broche NC 1 du boîtier DBV rendue explicite). Elle conserve la licence et
l'attribution KiCad Community ([texte de licence](LICENSE-symbols.txt)) ;
brochages recoupés avec TI [S32/S33](../../sources.md).
`sym-lib-table` utilise `${KIPRJMOD}`, sans chemin utilisateur. Le projet minimal
ne contient aucune exclusion ERC ni règle de contrôle désactivée.
