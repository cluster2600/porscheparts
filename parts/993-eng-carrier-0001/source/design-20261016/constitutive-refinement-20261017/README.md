# Cycle mécanique : comparaison de 16 et 32 états

Le raffinement du cycle charge puis décharge conserve le maillage, la loi,
les charges et les appuis. Seules les deux lignes définissant les incréments
changent : `0.125` devient `0.0625` pour le pas initial et maximal.
Les deux audits respectent leurs seuils inchangés sur les **32 états**.

| Contrôle | 16 états | 32 états | Seuil |
|---|---:|---:|---:|
| Maximum relatif ENER | 0,001585140971 | 0,000731617082 | 0,001 |
| Maximum relatif Piola | 0,000005637878 | 0,000087742489 | 0,0001 |
| Déplacement résiduel maximal, mm | 0,09925853846 | 0,09908998769 | Non défini |

Le maximum Piola augmente tout en restant sous son seuil. Le résidu varie de
−0,00016855077 mm. Le déterminant de déformation reste positif et la déformation
plastique reste dans le domaine mesuré de la loi sur tous les états.
Ce seul raffinement ne démontre pas une convergence de maillage.

- [Comparaison des deux cycles](refined-32/comparison.json).
- [Audit ENER des 32 états](refined-32/ener.json) et [audit Piola](refined-32/piola.json).
- [Rattachement au maillage et au deck actuels](current-reference-binding.json).
- [Différence exacte des decks](deck/deck.diff).
- [Planche en PDF](../../progress-figures-20261016/energy-increments-20261017/render/carrier-bilans-numeriques-16-32-etats.pdf).

Le maillage NPZ `b156b03a…` et le deck linéaire `903956e4…` sont identiques à
ceux du passage CAD actuel. Le [contrôle indépendant](independent-review.json)
a revérifié les 36 copies, les huit fichiers externes, dont les DAT et FRD,
et recalculé la comparaison à partir de tous les états JSON. Le refus ENER
historique à 16 états reste conservé dans [son audit](baseline-16/ener.json).

La [loi de référence](law/flat-set-1-plastic.inp) provient du spécimen Flat1
publié par Qixiang Luo, Lu Yin, Timothy W. Simpson et Allison M. Beese :
Ti Grade 23 ELI, orientation Z, détente à 670 °C pendant 5 h.
Sa [provenance](law/provenance.json) et sa [licence CC-BY-4.0](law/DATA_LICENSE.json)
sont incluses. Les résultats portent sur cette loi et les conditions du calcul.

Le [manifeste de publication](manifest.json) scelle les fichiers inclus.
Le [manifeste de préparation](preparation-manifest.json) et le
[texte de préparation original](README-preparation.md) sont conservés à l'octet.
Les scripts et reçus gardent leurs chemins historiques. Les DAT/FRD de 1,99 Go
et le maillage restent externes ; leurs empreintes sont jointes. Cette capsule
rassemble les preuves et ne constitue pas à elle seule un environnement de calcul.
