# Prochaine opération de raccord — non exécutée

081 conserve exactement les quadrilatères du raccord de 079 et les fermetures,
après une projection extérieure non nulle. Revenir à un raccord natif avec la
région tournante INCHANGÉE de 078, avant de traiter le raffinement. Aucun cas de
cette piste n'est préparé.

Le patch walls unique utilisé pour la projection contient aussi le raccord.
Il faut retrouver ses faces à partir de la carte valide et de la preuve de
connectivité, puis recréer des patches distincts avec les outils natifs, sans
supposer qu'une plage de labels survit à une nouvelle numérotation. Préserver
chaque maillage intermédiaire et reconstruire une bijection finale des points,
faces orientées, cellules, owner/neighbour et rotorZone. Ne pas copier les
anciennes cartes comme si elles adressaient le résultat final.

Le nom stitchMesh -perfect n'est pas une preuve d'identité : sa tolérance native
exige une comparaison indépendante. Conserver le raccord, les points tournants,
la zone, les connexions et les fermetures ; pas de trou, double paroi ou face
coplanaire artificiellement dupliquée. Vérifier qualité native, géométrie et
bilan de rotation par cellule avant toute suite CFD. Les patches mappedWall
vides de 066 sont un refus connu, à traiter explicitement dans une nouvelle
préparation sans changer une connexion physique.

Les surfaces extérieures 081 restent SYNTHÉTIQUES. Leurs points sont proches
de la cible, mais les faces sont gauchies et le volume n'est pas identique.
Ne pas transformer la borne de 22,433753 µm sur des surfaces triangulées
appariées en tolérance physique admissible ou jeu thermique. Ne pas transposer
les repos 064/076 à un maillage différent.

La protection pendant le raffinement et les couches reste non démontrée.
Préserver les pièces réelles, le profil 027/030 et la séparation roue–écrou 033.
Aucune projection en bloc sur le turbo, rotation de tout le domaine ou critère
abaissé. Les sources et preuves 080/081 deviennent immuables à la publication.
