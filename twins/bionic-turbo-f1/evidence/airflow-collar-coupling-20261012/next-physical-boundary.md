# Étape suivante non exécutée

065–067 vérifient une séparation et un réassemblage conformes de la couronne
existante. Les cartes natives et la comparaison indépendante conservent chaque
cellule, chaque face orientée et ses propriétaires, les coordonnées et la zone.
Le raccord testé se situe sur l'interface MRF de ce témoin ; il ne représente
pas encore un raccord entre la frontière latérale de la couronne et un cœur
contenant les pales. Aucun traitement de surface n'intervient entre séparation
et réunion. Ce contrôle ne démontre donc aucune protection pendant snappy.

Prochaine exigence : conserver les faces de la frontière latérale d'un sous-domaine
pendant le traitement d'une paroi physique, puis les raccorder à la couronne.
Les sources de snappySnapDriver et makeDisplacementField sont relues et hachées :
les patches non adaptés commencent avec une condition de déplacement slip,
pas une immobilisation générale. Cette condition de déplacement du mailleur
n'est pas une condition physique d'écoulement. Il faut établir les contraintes
de mouvement ET de raffinement avant un contrôle local représentatif ;
limitRegions seul n'est pas une garantie.

Ne pas extrapoler stitchMesh -perfect : sa tolérance interne vaut 0,001 fois
l'arête minimale. Le résultat présent est plus strictement comparé, avec égalité
des coordonnées décodées et bijection complète des faces/cellules. Un assemblage
ultérieur doit repasser cette preuve, les coquilles, connexions, jeux, qualité,
couches et repos global. Aucun nouveau calcul de cette étape n'est préparé.

Lecture complémentaire du membre déjà haché snappySnapDriver.C :
freezeExposedPoints (lignes 743–809) sélectionne la pointZone frozenPoints et
les points intérieurs de frozenFaces, puis annule leur déplacement dans le
patch exposé. L'appel est aux lignes 2866–2873, avant setDisplacement. Mais
preSmoothPatch intervient auparavant (ligne 2744) et utilise son propre
lissage (lignes 896–943). Cette fonction n'établit donc pas à elle seule une
protection de toutes les étapes, ni du raffinement. Examiner le périmètre
complet avant de concevoir un test. Aucun usage de ces zones effectué ici.
