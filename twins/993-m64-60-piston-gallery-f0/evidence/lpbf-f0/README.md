# Criblage LPBF pleine pièce du piston F0

Le maillage étanche dérivé du STEP a été tranché sur chaque couche de `50 µm`
avec le noyau géométrique F50. La sortie publique conserve les métriques de
couche, le rapport, leurs empreintes et une synthèse graphique ; le maillage de
calcul n'est pas nécessaire pour relire ces résultats.

Résultat principal : `2 390` couches, orientation candidate `roll_y_45`, quatre
îlots, `8,365 cm³` de supports conservateurs et aucune couche interne vide. La
pièce nue tient dans l'enveloppe nominale de la Velo3D Sapphire standard.

Les limites sont contraignantes : `6,25 %` des 2 000 sondes d'épaisseur sont
sous `1,5 mm`, les supports ne proviennent pas de Flow, la simulation
AdditiveFOAM CP1 n'est pas exécutable avec les données publiques, la distorsion
et le recoater ne sont pas validés. Aucune impression métal n'est autorisée.

![Résultats du tranchage intégral](993-eng-piston-cp1-gallery-f0-0001-lpbf-geometry-screen.png)

La préparation Omniverse place ensuite ce même piston dans l'orientation
`roll_y_45`, au contact du plateau et dans l'enveloppe nominale de la Sapphire.
La scène passe OpenUSD minimum, NVIDIA Asset Validator, Geometry et Physics.
Le recoater animé reste un guide : aucun champ de distorsion ni calcul de
collision recoater n'est appliqué.

![Préparation LPBF dans Omniverse](piston-lpbf-build-screen.png)

Le verdict borné et les empreintes sont dans
[`omniverse-build-screen-summary.json`](omniverse-build-screen-summary.json).
