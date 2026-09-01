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

## Contrainte d'exploitation : aucun accès physique

Le mainteneur de ce dépôt n'a accès ni à une 993, ni à une pièce détachée, ni à
un instrument de mesure. Rien n'y sera pesé, mesuré, imprimé, monté ni essayé en
interne.

Ce n'est pas une lacune à combler, c'est le cadre de travail. Il en découle trois
conséquences, qui valent règles :

1. **Une fiche produite ici plafonne au statut `concept`.**
   `dimensionally_reviewed` exige des mesures et `prototype_fitted` un montage :
   ni l'un ni l'autre n'est atteignable sans contributeur extérieur.
2. **Les critères de sortie des phases 2 et 3 dépendent d'un tiers.** Ils ne
   sont pas abandonnés, ils sont conditionnés. Le dépôt prépare tout ce qui peut
   l'être — plans de mesure, formats d'enregistrement, outils de capture et de
   validation — pour qu'une contribution soit exploitable dès qu'elle arrive.
3. **Les outils de capture servent à valider ce que d'autres transmettent.**
   `scripts/capture_caliper.py` et `scripts/capture_photoset.py` existent pour
   qu'un chiffre venu de l'extérieur porte son instrument, son incertitude et sa
   méthode, au lieu d'être un nombre sur un forum.

Ce que le dépôt peut livrer seul reste substantiel : registre de sources
vérifiées, sélection de candidats dans un catalogue d'usine, arbitrages matière
et procédé chiffrés, calculs, et environnement de calcul reproductible.
