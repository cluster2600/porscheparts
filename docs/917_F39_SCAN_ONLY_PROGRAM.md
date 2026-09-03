# Porsche 917 — programme F39 fondé uniquement sur le scan

## Décision d'entrée

Aucune cote supplémentaire n'est disponible. F39 ne bloque donc plus la CAO
sur l'attente d'une métrologie qui n'arrivera pas. Le scan devient l'unique
référentiel de forme et son unité est traitée conventionnellement comme un
millimètre pour les calculs.

Cette convention n'est pas une mesure. F39 développe une **nouvelle culasse
expérimentale autosuffisante** dans l'enveloppe du scan; il ne revendique ni
interchangeabilité avec une culasse Porsche 917 d'origine, ni montage garanti
sur des cylindres, goujons ou éléments de distribution historiques.

## Ce qui doit être redessiné

- B-Rep lisse et maillable, dérivé de la peau du scan avec carte d'écart;
- deck, chambre, conduits, sièges, guides et puits de bougie analytiques;
- quatre soupapes, doubles ressorts, culbuteurs, deux axes et porte-axes;
- alimentation, drainage et jets d'huile accessibles;
- ailettes, racines, carénage et déflecteurs d'air;
- surfaces d'usinage, filetages, surépaisseurs et références de contrôle;
- évacuations de poudre et supports LPBF accessibles.

Toutes les interfaces fonctionnelles sont nouvelles et cotées dans le modèle
paramétrique. Leur cohérence interne pourra être vérifiée; leur correspondance
avec une pièce Porsche historique restera inconnue.

## Critères numériques figés avant optimisation

| Porte | Critère F39 |
| --- | ---: |
| Paroi minimale générale | au moins 1,5 mm |
| Ponts thermiques critiques | cible initiale 3,0 mm |
| Poudre prisonnière | 0 mm³ aux résolutions étudiées |
| Supports inaccessibles | moins de 0,5 % de la surface |
| Maillage volumique | B-Rep maillable indépendamment |
| Température de pont | au plus 260 °C |
| Perte de charge refroidissement | au plus 6,7 kPa |
| Accord entre méthodes | écart relatif inférieur à 20 % |
| Convergence de grille | variation inférieure à 10 % |

Les seuils ne seront pas déplacés pour faire passer une variante. Une géométrie
qui échoue est modifiée puis recalculée.

## Deux niveaux de verdict

1. **Prototype numérique imprimable** : B-Rep fermé, épaisseurs, cavités,
   supports, maillage, CHT, structure et simulation LPBF satisfont les critères
   virtuels avec une matière encore conditionnelle.
2. **Pièce moteur autorisée** : exige en plus coupons matière, CT/CMM,
   ressuage, étanchéité, banc de flux, montage et banc moteur. Ce second niveau
   ne peut pas être obtenu uniquement avec le scan.

Le contrat vérifiable se trouve dans
`twins/reference-917-engine/scan-only-program-f39.json`. Toutes les portes de
fabrication et de démarrage restent fermées jusqu'aux preuves correspondantes.
