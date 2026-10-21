# Sensibilité aux incréments CalculiX :16→32 états

Cette capsule rassemble les preuves réelles déjà produites. Elle ne lance ni
solveur ni audit. Les36 copies source représentent434700octets ; les DAT/FRD
de1,99Go et les maillages restent externes, référencés par leurs empreintes.
Les chemins historiques contenus dans les reçus et scripts sont conservés sans
réécriture : cette capsule seule n'est pas un environnement autonome de calcul.

La [comparaison réelle](refined-32/comparison.json) lie les deux audits
[ENER32](refined-32/ener.json) et [Piola32](refined-32/piola.json), le solveur
terminé avec code0 et conteneur retiré, ainsi que les deux audits terminés avec
code0. Les32 états du cycle charge puis décharge passent les seuils inchangés :

| Mesure |16 états, Δt1/8 |32 états, Δt1/16 |Seuil fixé |
|---|---:|---:|---:|
| Maximum relatif ENER |0,001585140971 |0,000731617082 |0,001 |
| Maximum relatif Piola |0,000005637878 |0,000087742489 |0,0001 |
| Résidu max‖u‖ après décharge, mm |0,09925853846 |0,09908998769 |Non défini |

Le maximum Piola augmente ; il reste sous1e−4. Le résidu change de
−0,00016855077mm, sans seuil d'acceptation. Les contrôles de déterminantF positif
et de domaine plastique mesuré passent sur les32 états. Un seul raffinement
des incréments ne prouve ni une convergence de maillage ni un ordre asymptotique.
Le refus historique ENER16 à t=1/8 reste dans [l'audit16](baseline-16/ener.json)
et n'est pas remplacé par le succès32.

Le [rattachement actuel](current-reference-binding.json) vérifie le maillage
NPZ `b156b03a…` et le deck linéaire `903956e4…` de `run-001`. La
[liaison historique16](binding/constitutive-binding-result.json) et sa
[preuve indépendante](binding/constitutive-binding-independent-002.json)
restent conservées. Les deux decks non linéaires ne diffèrent que par leurs
deux lignes STATIC :0,125→0,0625 pour l'incrément initial et maximal. Les
[différences exactes](deck/deck.diff), les plans et les identités de maillage
historique/refiné sont joints. Aucune équivalence des deux exports STEP n'est
déduite de cette identité discrète.

La [loi copiée](law/flat-set-1-plastic.inp), sa
[provenance](law/provenance.json) et sa [licence CC-BY4.0](law/DATA_LICENSE.json)
proviennent du premier spécimen plat publié de Ti Grade23 ELI, orientationZ,
après détente670°C5h. Elles décrivent une sensibilité isotrope J2 avant
striction ; ν=0,31 est l'hypothèse du modèle, non une valeur fournie par le jeu
de données. Cette loi ne devient pas une propriété admissible Grade5 de la
pièce. Aucune extrapolation après striction ou loi de dommage n'est ajoutée.

Le [manifeste](manifest.json) conserve les chemins source, tailles et SHA de
chaque copie, ainsi que les références externes. Les gros DAT/FRD ne sont pas
relus par cette opération de packaging : leurs SHA sont ceux déjà liés par les
reçus terminés du solveur, des audits et de la comparaison. Le maillage NPZ et
le deck linéaire actuels, eux, ont été rehashés lors de cette préparation.

Pour le futur guide, la [proposition de rattachement](guide-attachment-proposal.json)
ajoute un sous-dossier et un reçu complémentaire après les gardes historiques16.
Elle ne modifie aucun guide, aucune recette, aucune ancienne preuve ou index
logiciel. Le livrable global des supports et le guide final restent en attente.
