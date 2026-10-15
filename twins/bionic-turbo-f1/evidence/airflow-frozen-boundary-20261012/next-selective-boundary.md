# Prochaine portée, non exécutée

068/069 réfutent la conservation des coordonnées initiales avec le lissage
préalable, même si les points sont dans frozenPoints. 070 est un contrôle
borné : toutes les parois sont gelées et la cible est déjà conforme au maillage.
Il ne prouve pas la protection d'un raccord voisin d'une paroi effectivement
projetée, et n'établit aucune protection du raffinement.

Avant un vrai sous-domaine, définir un contrôle local avec deux rôles distincts :
faces de raccord à conserver, et autre paroi avec déplacement cible non nul
et connu. Conserver la connectivité de raccord, contrôler tous ses points et
les cellules voisines, puis admission native. Toute cible synthétique doit
rester explicitement distincte des surfaces physiques du turbo et ne doit
pas fournir de nouvelles dimensions de pièce. Reprendre les outils natifs
existants avant un générateur. Ne pas extrapoler nSmoothPatch=0 en production.

Le périmètre de freezeExposedPoints reste celui des points du patch adapté
transmis à la fonction. Une pointZone arbitraire dans un patch non adapté ne
constitue pas automatiquement une condition de déplacement fixe. Les étapes
de raffinement, de couches et le raccord aux parois physiques restent à prouver.
Aucun nouveau cas de cette piste n'est préparé, aucun écoulement n'est lancé.
