# Politique de sécurité des pièces

Ce document décide **ce que le dépôt a le droit de publier**, et sous quelles
conditions. Il prime sur l'intérêt technique d'une pièce, sur la qualité d'un
calcul et sur l'envie de fabriquer.

Une seule phrase le résume : **un calcul n'autorise jamais une fabrication.**

## 1. Classes

| Classe | Définition | Publication autorisée |
|---|---|---|
| `non_critical` | Habillage ou pièce dont la rupture ne crée pas de danger immédiat | Après validation dimensionnelle et montage |
| `functional` | Pièce sollicitée dont la rupture peut immobiliser ou endommager le véhicule | Après essais fonctionnels documentés |
| `safety_critical` | Rupture susceptible de provoquer perte de contrôle, incendie ou blessure | Seulement après revue d'ingénierie formelle |
| `prohibited_pending_engineering` | Risque ou données insuffisantes | Jamais comme pièce libérée |

Ces quatre valeurs sont celles du schéma de fiche. Elles ne se paraphrasent pas.

### Domaines présumés critiques

Sont présumés critiques : freinage, direction, suspension, roues, retenue des
occupants, circuit de carburant, points de levage, fixations principales du
groupe motopropulseur et composants internes moteur fortement chargés.

« Présumé » veut dire que la charge de la preuve est inversée : ce n'est pas au
document de démontrer le danger, c'est à la fiche de démontrer l'innocuité. La
même liste est appliquée automatiquement par `scripts/select_candidates.py` et
par les criblages titane ; elle doit rester identique des deux côtés.

### Le mode de rupture prime sur le domaine

Une pièce peut n'appartenir à aucun domaine de la liste et rester
`safety_critical` par son mode de rupture. **L'incendie en est le cas le plus
courant et le plus oublié** : une conduite d'huile de turbocompresseur n'est ni
un frein ni un organe de direction, mais sa rupture dépose de l'huile sur un
carter de turbine largement au-dessus du point d'auto-inflammation. Elle est
critique, et aucune finesse de dessin ne l'en sort — voir
[`docs/993/993_CIRCUIT_HUILE_TURBO_202-16.md`](docs/993/993_CIRCUIT_HUILE_TURBO_202-16.md).

La question à poser n'est donc pas « à quel groupe la pièce appartient-elle »,
mais **« que se passe-t-il quand elle casse »**.

## 2. Une validation de montage ne prouve pas la sécurité

Une pièce qui entre dans son logement peut encore échouer par fatigue, fluage,
température, vibrations, corrosion, mauvais serrage ou défaut de fabrication.
Les statuts du catalogue ne doivent jamais être déduits d'une photographie seule.

De la même façon, **un criblage numérique n'est pas une preuve**. Le dépôt
produit des criblages géométriques, thermiques et de route ; ils servent à
écarter, pas à autoriser. Un rapport dont toutes les portes seraient vertes ne
libère toujours aucune pièce : seule la revue d'ingénierie signée le fait, au
terme du [pipeline de fabrication additive](docs/AM_VALIDATION_PIPELINE.md) dont
les onze étapes doivent toutes être `passed`.

## 3. Exigences minimales pour le métal

- Matière et lot traçables
- Procédé et paramètres qualifiés par le fabricant
- Orientation et supports documentés
- Traitement thermique documenté
- HIP justifié pour les sollicitations cycliques critiques
- Surfaces fonctionnelles usinées lorsque nécessaire
- Contrôle dimensionnel et contrôle non destructif adaptés
- Prévention du grippage et de la corrosion galvanique
- Plan de charge, calcul et essais conservés comme preuves

À quoi s'ajoutent deux vérifications que ce dépôt a appris à faire
explicitement, parce qu'elles se manquent facilement.

### La température de service contre le plafond de l'alliage

Un alliage a un plafond, et une pièce a une température. Les deux doivent être
écrits, et confrontés. Le Ti-6Al-4V est limité par le fluage vers 400 °C ; une
pièce déclarée à 427 °C ne passe pas, même si tout le reste de la route est
irréprochable. Cette confrontation est une porte de l'étape 04 et doit rester
fermée tant que la température réelle n'est pas mesurée.

**Une température synthétique n'est pas une température.** Quand un criblage
fixe une valeur pour pouvoir calculer, cela doit être dit, et la décision qui en
dépend reste suspendue à une mesure.

### Le démontage fait partie de la vie de la pièce

Une pièce qu'on démonte à l'entretien subit des serrages répétés. Le titane
grippe, contre lui-même comme contre l'acier, sans traitement de surface. Un
raccord démonté à chaque vidange, un filetage repris, un contact glissant non
traité : ce sont des motifs de refus, pas des détails de finition.

## 4. Le procédé et la matière sont deux questions

Une pièce peut être un excellent candidat à la fabrication additive et un
mauvais candidat au titane. Les deux jugements sont indépendants et doivent être
rendus séparément.

Le circuit d'huile de turbo en est l'exemple : onze pièces à consolider, des
passages internes, une petite série — et un refus du titane sur le grippage,
indépendamment du risque d'incendie. Inversement, une bague de finition
axisymétrique n'a aucune raison d'être frittée, quelle que soit sa matière.

Choisir une pièce parce qu'elle est la moins risquée **n'est pas la choisir**.
Le dépôt l'a fait une fois et l'a corrigé : voir
[`docs/decisions/0005-alsi10mg-nest-pas-un-choix.md`](docs/decisions/0005-alsi10mg-nest-pas-un-choix.md).
La sélection se fait sur la fonction, contre une grille écrite, et le résultat
doit rester réfutable ligne à ligne.

## 5. Déclassement et reclassement

**Abaisser** une classe ne demande aucune preuve : le doute suffit, et il suffit
toujours. En cas d'incertitude, la pièce descend à
`prohibited_pending_engineering` jusqu'à clarification.

**Relever** une classe demande, dans cet ordre : l'identité de la pièce établie
par une source de niveau A, la mesure d'un exemplaire, un cas de charge réel et
non synthétique, une carte matière qualifiée du procédé retenu, les essais
correspondant à la classe visée, et — pour `safety_critical` — une revue
d'ingénierie signée portant sur une révision précise et explicitement bornée.

Aucune de ces étapes ne se déduit d'une autre. Un changement de classe se
justifie dans la fiche, pas dans un message de commit.

## 6. Ce que le dépôt ne fera pas

- publier une pièce `prohibited_pending_engineering` comme libérée, quelle que
  soit la qualité de son dossier ;
- présenter un criblage comme une autorisation ;
- déduire une matière d'origine d'une déclaration de revendeur ;
- remplacer une mesure manquante par une hypothèse commode ;
- fabriquer ou faire fabriquer une pièce de structure autoportante ou de
  sécurité passive — voir le hors-périmètre de [ROADMAP.md](ROADMAP.md).

## 7. Signalement

Ouvrir une issue avec le préfixe `[SAFETY]` sans publier de donnée personnelle ni
de document propriétaire. En cas de doute, le statut de la pièce doit être abaissé
à `prohibited_pending_engineering` jusqu'à clarification.
