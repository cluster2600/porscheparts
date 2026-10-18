# Construction incrémentale exacte des feuilles

Les points d’entrée `generate_prism_region_v5.py` et
`generate_legacy_region_v5.py` conservent les arguments, les contrôles et les
sorties de v4. Leur module privé `continuous_incremental_interfaces.py` conserve
la politique de réparation cf269 et emploie le constructeur 814. Les anciens
constructeurs, travaux refusés et sources figées restent présents.

La mise à jour incrémentale ne recalcule que les droites touchées par les deux
triangles d’un nouveau quadrilatère. Elle conserve les extrémités des arêtes
annulées, les événements orientés et l’ordre d’apparition des droites. Un essai
refusé ne modifie pas l’état accepté. Les coordonnées restent des fractions
exactes des valeurs IEEE enregistrées. Les identifiants de points accélèrent
uniquement l’égalité et le classement : une clé IEEE n’est acceptée qu’après
preuve de sa représentation rationnelle identique. Aucun calcul de coordonnées
n’emploie ces clés. Le verrou et la garde de réentrance protègent les substitutions
privées ; le module public reste intact.

Les cinq petites captures reproduisent exactement la WKB du résultat et le reçu
943. Les tests couvrent aussi les extrémités annulées, un rejet suivi d’une
acceptation, les voisins IEEE, les coordonnées non représentables, la réentrance
et un snapshot plat chargé depuis `/`. Le passage complet de la grande peau 1
contient 5 876 sommets, 5 875 appels et 5 874 ajouts acceptés, sans recours au
recalcul intégral : 324,729 s mesurées. Ce temps n’est pas un rapport de vitesse
contre un ancien passage complet, qui n’a pas terminé. Une reconstruction unique
par la fonction 943 d’origine des 17 622 triangles finalement acceptés donne la
même WKB et exactement la même aire rationnelle.

Ces preuves portent sur le constructeur. Les sept régions doivent encore
produire leurs checkpoints ; le scellement des six admissions, le tranchage des
supports aux 1 034 plans réels et l’audit complet des expositions restent des
étapes distinctes. Le cache de la pièce et les enveloppes natives admises sont
réutilisés sans recalcul. Le reçu compact est
`combinatorial-evidence/incremental-results.json` ; les résultats détaillés
locaux y sont liés par SHA.
