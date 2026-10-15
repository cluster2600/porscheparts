# Prochaine portée — non exécutée

La région extérieure 065 a une seule cellule dans l'épaisseur radiale. La fermer
par des parois non couplées supprime une direction de contribution au tenseur
natif du déterminant ; 071 et 072 sont donc rejetés avant toute projection.
La baisse n'est pas une preuve de nouveaux éléments géométriquement écrasés :
072 conserve exactement les coordonnées et faces source. Le refus natif demeure.

Revenir à un témoin où les cellules voisines du raccord gardent une contribution
radiale interne. Un contrôle de déplacement dans le domaine complet 063 pourrait
réutiliser les cellules existantes, mais ne qualifierait pas à lui seul le
traitement d'un sous-domaine isolé. Une subdivision radiale conforme pourrait
également être étudiée ; elle exigerait admission native, parenté des faces et
conservation de la frontière, sans préjuger de sa qualité. Aucune de ces pistes
n'est préparée ni calculée ici. Ne pas déclarer artificiellement un patch couplé
sans son partenaire pour faire passer checkMesh.

Le prochain contrôle sélectif doit conserver un raccord tout en produisant un
déplacement non nul connu d'une autre paroi, avant un test de raffinement distinct.
Le turbo réel, ses pales, ses jeux et ses connexions restent inchangés. L'étape
071/072 ne remplace pas les validations requises pour le cœur adapté autour des
pales et pour les couches de paroi. Aucune performance CFD n'est déduite.
