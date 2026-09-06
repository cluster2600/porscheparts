# F56 — références CP1 et dilatation thermique

Les fiches fabricant consultées le 6 septembre 2026 distinguent deux routes
CP1 à couches de 60 µm : M 290 (`AlCP1_060_M291`, plateau 125 °C) et
M 400-4 (`AlCP1_060_M404`, plateau 150 °C). Elles indiquent argon, lame HSS,
tamis 90 µm, EOSPRINT 2.13 minimum et traitement 4 h à 400 °C. Le processus
CP1 doit être demandé à EOS ; ces indications ne livrent pas une stratégie
laser complète et librement reproductible.

Sources : [EOS M 290](https://www.eos.info/metal-solutions/data-sheets/aluminium/pds-eos-aluminium-constellium-cp1-eos-m-290-60um),
[EOS M 400-4](https://www.eos.info/metal-solutions/data-sheets/aluminium/pds-eos-aluminium-constellium-cp1-eos-m-400-4-60um).

## Calcul conditionnel, séparé des simulations existantes

Les coefficients publiés sont 19, 21 et 22 µm/(m·K), associés aux intervalles
25–100, 25–200 et 25–300 °C. En les interprétant comme des coefficients moyens
depuis 25 °C, les déformations aux bornes sont respectivement 0,001425,
0,003675 et 0,00605. L'outil interpole ces déformations, pas les coefficients
comme s'ils étaient des valeurs instantanées. Il refuse toute extrapolation.

L'état de traitement propre aux valeurs CTE n'est pas explicité dans la
section consultée : cette interprétation doit être confirmée avant une
intégration au solveur. Ce calcul de dilatation libre **n'est pas un résultat
de distorsion de la culasse**. Il ne fournit pas les propriétés manquantes
de conduction, plasticité, fatigue ou fluage à chaud.

## Fournisseur et route finale non arrêtés

Constellium documente une qualification CP1 chez Burloak en 2023 : c'est
une piste fournisseur identifiable, pas une confirmation actuelle de capacité,
de délai, de machine ou de recette pour cette culasse. Cette source ne
confirme pas une fabrication en Chine. Aucun contact ni commande n'a été passé.
[Source Constellium](https://www.constellium.com/constelliums-additive-manufacturing-powder-solutions-qualified-by-burloak-technologies).

Les anciens résultats AlSi10Mg/Sapphire ne sont pas transférés à CP1/EOS.
Le candidat HT1 mentionné en F42.2 n'est pas remplacé par cette recherche.
La sélection finale reste ouverte ; aucune fabrication n'est autorisée.

Vérification : quatre tests passent (bornes, interpolation, refus hors domaine,
séparation des deux processus). Carte : `cp1-process-reference-f56.json`.
