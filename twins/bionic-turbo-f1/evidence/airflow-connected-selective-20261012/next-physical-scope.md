# Prochaine portée — non exécutée

075 montre qu'un déplacement extérieur non nul peut coexister avec un raccord
conservé et toutes les cellules tournantes intactes si l'étape native de lissage
interne des déplacements est désactivée dans ce témoin. Ce n'est ni une règle
universelle de maillage ni un changement du solveur CFD.

La cible complète n'est pas récupérée sommet par sommet. Les sommets communs
aux fermetures peuvent être attirés vers celles-ci ; des faces restent gauchies
dans le domaine fixe et le volume total diffère de 063. Les surfaces physiques
et leur conservation doivent donc rester une validation distincte, notamment
pour l'anneau arrière. Ne pas assimiler la distance au sommet source à une
distance signée à la surface STL ni à un jeu géométrique ou thermique.

Avant un vrai sous-domaine autour des pales, établir comment conserver le raccord
et les fermetures physiques pendant la projection, puis pendant le raffinement.
Reprendre les outils natifs existants ; ne pas lancer snappy en bloc. Une zone
frozenPoints seule n'immobilise pas automatiquement les points internes.
La subdivision radiale et les raccords doivent rester admissibles selon les
critères natifs, comme l'ont montré les refus 071/072. Préserver la correction
roue–écrou 033 et les sources CFD exactes. Aucun contrôle de cette étape n'est
préparé ici et aucune performance forcée du turbo n'est démontrée.
