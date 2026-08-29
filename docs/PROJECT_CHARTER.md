# Charte du projet

## Vision

Rendre reproductibles des pièces de Porsche 993 devenues rares, fragiles ou
inadaptées, en les développant dans un jumeau numérique fonctionnel construit
par zones. Les sources CAO, interfaces, mesures, incertitudes et niveaux réels
de validation restent publiés et modifiables.

L’accent titane signifie que le projet maîtrise le chemin allant d’une mesure ou
d’un scan jusqu’à une demande de fabrication Ti-6Al-4V contrôlable. Il ne signifie
pas que toutes les pièces doivent être imprimées en titane.

## Utilisateurs

- Propriétaires et restaurateurs de Porsche 993
- Ateliers indépendants
- Concepteurs CAO et spécialistes de rétroconception
- Prestataires d’impression polymère et métal
- Ingénieurs capables de revoir calculs, procédés et essais

## Livrables

Pour chaque pièce publiée :

1. une fiche structurée et sourcée ;
2. un modèle paramétrique ou STEP ;
3. un plan de mesure ;
4. un fichier de prototype ;
5. les instructions de fabrication pertinentes ;
6. les preuves de montage et d’essai ;
7. une licence explicite ;
8. une version et un historique des changements.

Pour chaque zone du jumeau : géométrie hôte, repère, composants, interfaces,
règles d'acceptation, précision, rapport numérique et corrélation physique.

## Mesures de réussite

- Pourcentage de pièces avec licence et provenance complètes
- Pourcentage de pièces disposant d’un fichier source modifiable
- Nombre de prototypes dont le montage est documenté
- Nombre de sous-jumeaux au niveau `F2_interface` ou supérieur
- Écart entre les marges numériques prévues et les contrôles physiques
- Nombre de pièces testées sur plusieurs véhicules ou variantes
- Taux de défauts ou de corrections après publication
- Nombre de pièces titane avec traçabilité matière et rapport de contrôle

## Gouvernance des décisions

- Une issue porte la discussion initiale.
- Une décision durable est résumée dans `docs/decisions/`.
- Une pull request modifie la fiche et les fichiers concernés.
- La validation automatique vérifie la structure, pas la sécurité mécanique.
- Une pièce peut être rétrogradée immédiatement si une preuve nouvelle contredit
  son statut.

## Définition de « terminé »

Une pièce n’est terminée que lorsque le statut de sa fiche correspond aux preuves
présentes dans le dépôt. `released` signifie prête à être reproduite dans les
limites documentées, pas homologuée pour la route ni garantie universellement.
