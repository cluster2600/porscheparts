# Politique de sécurité des pièces

## Classes

| Classe | Définition | Publication autorisée |
|---|---|---|
| `non_critical` | Habillage ou pièce dont la rupture ne crée pas de danger immédiat | Après validation dimensionnelle et montage |
| `functional` | Pièce sollicitée dont la rupture peut immobiliser ou endommager le véhicule | Après essais fonctionnels documentés |
| `safety_critical` | Rupture susceptible de provoquer perte de contrôle, incendie ou blessure | Seulement après revue d’ingénierie formelle |
| `prohibited_pending_engineering` | Risque ou données insuffisantes | Jamais comme pièce libérée |

Sont présumés critiques : freinage, direction, suspension, roues, retenue des
occupants, circuit de carburant, points de levage, fixations principales du
groupe motopropulseur et composants internes moteur fortement chargés.

## Une validation de montage ne prouve pas la sécurité

Une pièce qui entre dans son logement peut encore échouer par fatigue, fluage,
température, vibrations, corrosion, mauvais serrage ou défaut de fabrication.
Les statuts du catalogue ne doivent jamais être déduits d’une photographie seule.

## Exigences minimales pour le métal et le titane

- Matière et lot traçables
- Procédé et paramètres qualifiés par le fabricant
- Orientation et supports documentés
- Traitement thermique documenté
- HIP justifié pour les sollicitations cycliques critiques
- Surfaces fonctionnelles usinées lorsque nécessaire
- Contrôle dimensionnel et contrôle non destructif adaptés
- Prévention du grippage et de la corrosion galvanique
- Plan de charge, calcul et essais conservés comme preuves

## Signalement

Ouvrir une issue avec le préfixe `[SAFETY]` sans publier de donnée personnelle ni
de document propriétaire. En cas de doute, le statut de la pièce doit être abaissé
à `prohibited_pending_engineering` jusqu’à clarification.
