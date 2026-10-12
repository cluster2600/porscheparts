# Couronne homothétique dans le passage CFD — 062

La couronne candidate est vérifiée sur les deux surfaces CFD inchangées.
Il s'agit d'une preuve géométrique conservative, sans nouveau maillage
volumique ni lancement de solveur. Les calculs 014–061 restent conservés.

Le profil central 030 reste inchangé et conserve son seuil de séparation
radiale de 0,905690 mm (borne obtenue : 0,905690010 mm). La demi-largeur
relative vaut eta = 0,905690 / (2 × 32) = 0,01415140625 ; les deux ratios
sont 0,98584859375 et 1,01415140625. Ce choix borne le déplacement radial
par la demi-largeur déjà utilisée dans le fond 030. Ce n'est pas une
marge physique ou une tolérance de solveur.

Pour chacune des 356 bandes des deux variantes, les extrémités et toutes
les stations intérieures du profil sont contrôlées. Le facteur cos(pi/128)
borne les cordes intérieures. La séparation radiale minimale aux bornes
rotor/stator vaut 0,4618015016 mm, au-dessus de 0,452845 mm requis pour
cette couronne. Le second lecteur reproduit séparément le parcours des
segments affines et les 712 résultats publiés. Ces bornes ne mesurent pas
un jeu euclidien ou thermique.

L'auditeur relit intégralement les STL exacts et vérifie leurs SHA-256,
les quatre patches et tous leurs comptes. L'anneau du stator à z = −3,75 mm
couvre toute la largeur arrière, cordes comprises, sur 360 degrés. Les
7 586 facettes candidates à l'intersection de l'extension arrière sont
toutes stator et exactement dans ce plan, pour chaque variante. Les
sélections conservatrices des disques, de l'extension avant et des ports
sont vides. Les tests d'enroulement utilisent la frontière fluide fermée
complète. Avec l'absence d'intersections et la connexité de la couronne,
ils placent la partie supérieure dans le fluide et la partie sous le
stator hors fluide ; le disque supérieur reste à z = 33 mm et le disque
inférieur à z = −4 mm.

Toutes les 516 216 facettes rotor sont bornées entièrement à l'intérieur
de la frontière intérieure, sur chaque segment affine qu'elles touchent.
La convexité de la norme fournit la borne radiale par les sommets, tandis
que le minimum du profil est pris sur toute l'étendue axiale concernée.
La borne minimale vaut 0,4624228585 mm ; la facette témoin est conservée.
Les tableaux rotor des deux variantes restent identiques.

Les sources antérieures sont appelées sans modification. Les entrées
légères sont copiées et hachées dans l'archive ; les STL volumineux restent
dans les archives des phases précédentes, avec leurs empreintes exactes
référencées ici. Aucun nouveau champ physique n'existe pour 062.

Limites : ces résultats ne qualifient ni le raccord volumique, ni les
cellules autour des pales, ni les couches, ni le repos global du turbo.
La séparation roue–écrou corrigée en 033 reste à préserver. Aucun débit,
gain de puissance, convergence ou jumeau calibré n'est validé.

## Reproduction

Depuis la racine du dépôt, les commandes sont celles du reçu d'exécution.
Restaurer les chemins des entrées légères selon input-inventory.json ; les
surfaces exactes sont conservées dans les releases
[référence 022](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-conformal022-rejected-2026-10-12)
et [candidate 014](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-candidate014-rejected-2026-10-12).
Utiliser une copie neuve du dossier de campagne : les scripts refusent
d'écraser leurs sorties. Le contrôle central utilise le profil030 et les
bandes023 inchangés, avec leurs empreintes publiées dans le rapport.

L'[archive 062](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-collar-geometry-2026-10-12)
conserve 22 fichiers (325 624 octets), SHA-256
`a6122f1eafeaa18d6760220580a7dc4e51bc58556701b8cb9e6958fee2daf26f`.
Les cinq actifs distants sont vérifiés par tailles et digests ; les payloads
sont relus localement. La correction de métadonnées du premier paquet est
explicitée dans validation.md.
