# Cas de charge — 993-ENG-CARRIER-0001

Document à remplir **avant** toute géométrie de remplacement. Aucune valeur n'est
pré-remplie : une hypothèse de charge inventée produirait un calcul qui rassure
sans rien prouver.

## 1. Ce que la pièce reprend

- Masse du groupe motopropulseur supportée par ce berceau : ____ kg
  - source de la valeur : ____
  - méthode : pesée, documentation officielle, ou répartition mesurée
- Position du centre de gravité par rapport aux points de fixation : ____
- Répartition entre ce berceau et les autres points d'ancrage : ____
- Couple de réaction moteur en première : ____ Nm, bras de levier ____ mm

## 2. Facteurs dynamiques retenus

| Cas | Facteur | Justification et source |
|---|---:|---|
| Vertical, route dégradée | | |
| Freinage longitudinal | | |
| Accélération latérale | | |
| Choc / passage de nid-de-poule | | |
| Sollicitation cyclique de fatigue | | |

Un facteur retenu sans source est une hypothèse : le noter comme telle.

## 3. Interfaces et conditions aux limites

- Points de fixation à la caisse : nombre, diamètre, classe de vis, couple de serrage
- Supports moteur : type, raideur, précharge
- Conditions imposées dans le modèle EF (encastrement, appuis, contacts)
- Jeux et tolérances d'assemblage

## 4. Environnement

- Température au voisinage de l'échappement et du moteur : ____
- Vibrations : plage de fréquences d'excitation moteur ____
- Corrosion : sel, humidité, contact avec caisse acier
- Durée de vie visée : ____ km ou ____ heures

## 5. Critères d'acceptation

À définir avant de calculer, sinon le critère s'adapte au résultat :

- Contrainte admissible et coefficient de sécurité retenu : ____
- Déplacement maximal admissible aux interfaces : ____
- Première fréquence propre minimale : ____ Hz
- Tenue en fatigue : nombre de cycles et amplitude ____

## 6. Comparaison de procédés

| Procédé | Masse | Coût | Raideur | Fatigue | Risque | Verdict |
|---|---|---|---|---|---|---|
| Pièce d'origine (référence) | | | | | | référence |
| Acier soudé / tubulaire | | | | | | |
| Aluminium usiné | | | | | | |
| Ti-6Al-4V LPBF | | | | | | |

Rappel de `docs/TITANIUM.md` : le titane n'est pas pertinent pour « une pièce
dont la flexion doit rester identique à une pièce acier ». Le module du
Ti-6Al-4V est d'environ 114 GPa contre 210 GPa pour un acier : à géométrie
identique, la pièce serait presque deux fois plus souple. Un gain de masse ne
se constate qu'après avoir redessiné les sections pour retrouver la raideur.

## 7. Revue

- Calcul revu par : ____ (nom de rôle, compétence, date)
- Revue de fabricabilité prestataire : ____
- Plan de validation approuvé : oui / non
- Décision : poursuivre / arrêter / redéfinir
