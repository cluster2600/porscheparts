# Porsche 917 — F48, domaines CFD natifs 2V / 4V

## Objet

F48 découple le domaine fluide du B-Rep de culasse F47. Le diagnostic des
p-courbes du solide n'est donc ni masqué ni réparé par un proxy. La géométrie
CFD est reconstruite nativement à partir des cylindres fonctionnels F47 :
alésage/chambre, throats et conduits circulaires. La bougie est exclue du volume
gaz parce qu'une bougie montée est un solide frontière, pas un volume de fluide.

## Construction

Chaque variante est la fusion OpenCASCADE d'un cylindre de chambre/alésage,
des throats verticaux et des conduits circulaires jusqu'aux frontières
d'admission et d'échappement. Le résultat contient exactement un volume fermé;
les bouchons numériques des conduits servent de patches de conditions aux
limites. Toutes les surfaces frontières sont nommées et affectées une seule
fois.

Le domaine complet est maillé. Il n'existe donc pas de plan `symmetry`. Ajouter
un tel patch sans couper réellement la géométrie créerait une condition aux
limites fausse.

Le constructeur ne contient aucune primitive elliptique, ovale ou proxy. Les
courbes coniques que le noyau OCC peut nommer `Ellipse` sont uniquement les
traces d'intersection mathématiques de cylindres circulaires obliques.

## Convergence géométrique et qualité

Les niveaux coarse, medium et fine utilisent respectivement des tailles
maximales de 6,0, 4,0 et 2,5 unités scan, identiques pour 2V et 4V. Les six
maillages ont zéro tétraèdre inversé, zéro minSICN sous 0,1 et un p01 supérieur
à 0,36. Le volume OCC est strictement identique sur les trois niveaux de chaque
variante.

Ce contrôle démontre la maillabilité et la cohérence du domaine analytique. Il
ne démontre ni l'exactitude des ports réels, ni les coefficients de débit, ni
la combustion, ni les transferts thermiques conjugués.

## Huile

La galerie principale et les deux accès supérieurs forment un volume distinct,
maillé et entièrement patché (`oil_x_minus`, `oil_x_plus`, `oil_cleanout`,
`oil_walls`). Ce domaine sert à une future étude de lubrification. Il ne doit
pas être utilisé comme chemise de refroidissement liquide et aucun drainage,
débit ou niveau d'huile n'est encore validé.

## Portes

La seule porte ouverte est la construction/qualité de maillage des domaines
fluides analytiques déclarés. Restent fermés :

- échelle absolue et interfaces Porsche 917;
- solution OpenFOAM/ICE/combustion et corrélation au banc;
- CHT avec une culasse solide maillable;
- épaisseur, contraintes, fatigue et durée de vie;
- dépoudrage, procédé matière, CT/CND et fabrication;
- démarrage moteur.

Le rapport chiffré et les hashes sont sous
`twins/reference-917-engine/evidence/f48-cfd-domains/`.
