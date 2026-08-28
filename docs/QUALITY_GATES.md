# Portes qualité

| Statut | Preuves requises | Ce que le statut ne signifie pas |
|---|---|---|
| `concept` | Besoin et sources initiales | Dimensions correctes |
| `dimensionally_reviewed` | Mesures critiques et revue CAO | Montage confirmé |
| `prototype_fitted` | Prototype monté avec preuve | Tenue en service |
| `functionally_tested` | Protocole et résultats d’essai | Homologation universelle |
| `engineering_reviewed` | Calculs et revue signée | Fabrication de série validée |
| `released` | Dossier complet selon classe de risque | Garantie ou approbation Porsche |

## Règles automatiques

Le validateur bloque notamment :

- une fiche sans source ni licence ;
- une génération autre que 993 ;
- un identifiant ou un statut inconnu ;
- une pièce titane sans exigences de traitement, contrôle et isolation ;
- une pièce critique libérée sans reviewer, preuve et inspection ;
- une mesure dont la valeur ne correspond pas à ses propres échantillons ;
- une incertitude plus fine que la moitié de la résolution de l’instrument ;
- une lecture déclarée issue d’un instrument alors qu’elle a été saisie à la main ;
- un niveau de preuve `A` sans répétitions ni état d’étalonnage connu.

Ces contrôles assurent la cohérence documentaire. Ils ne réalisent aucune analyse
mécanique.

## Revue humaine

Le reviewer vérifie :

- correspondance entre géométrie et mesures ;
- variantes réellement couvertes ;
- licences et attributions ;
- cohérence matière-procédé-environnement ;
- limites et hypothèses visibles ;
- absence d’affirmation dépassant les preuves.
