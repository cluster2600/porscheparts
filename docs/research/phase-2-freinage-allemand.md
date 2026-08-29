# Phase 2 — Recherche germanophone sur le freinage

Date de consultation : 29 août 2026.

## Décision

Aucun composant de freinage n'entre encore dans `catalog/components/`.
Les documents constructeur permettent d'identifier plusieurs disques, leur
application, leur position et leurs dimensions. Ils ne donnent cependant pas
de masse nette et ne décrivent pas une nuance matière complète. Ajouter une
masse issue d'un vendeur violerait la règle d'admission du jumeau.

Cette décision ne remet pas en cause la compatibilité commerciale déclarée par
les fabricants. Elle signifie seulement que les quatre champs obligatoires du
projet — taille, masse, matière et application 993 — ne sont pas tous sourcés.

## Références qualifiées mais incomplètes

| Position | Référence fabricant | Référence Porsche recoupée | Dimensions déclarées | Matière déclarée | Champ bloquant |
|---|---|---|---|---|---|
| avant gauche | Brembo `09.8420.11` | à recouper avant admission | Ø 304 x 32 mm, hauteur 72 mm, centrage 103 mm, 5 trous, minimum 30 mm | haut carbone, ventilé | masse nette, nuance complète et référence Porsche directe |
| avant droite | Brembo `09.8421.11` | à recouper avant admission | Ø 304 x 32 mm, hauteur 72 mm, centrage 103 mm, 5 trous, minimum 30 mm | haut carbone, ventilé | masse nette, nuance complète et référence Porsche directe |
| arrière, quantité 2 | Brembo `09.C085.11` | à recouper dans PET avant admission | Ø 299 x 24 mm, hauteur 65 mm, centrage 103 mm, 5 trous, minimum 22 mm | haut carbone, ventilé | masse nette, nuance complète et référence Porsche |
| avant | ATE `24.0132-0142.1` | `993 351 043 01` | Ø 304 x 32 mm, hauteur 72 mm, centrage 103 mm, 5 trous, minimum 30 mm | haut carbone, allié, ventilé | masse nette et famille/nuance complète |
| avant | ATE `24.0132-0143.1` | `993 351 044 01` | Ø 304 x 32 mm, hauteur 72 mm, centrage 103 mm, 5 trous, minimum 30 mm | haut carbone, allié, ventilé | masse nette et famille/nuance complète |

Le catalogue ATE contient une colonne dimensionnelle `I`. La valeur `15,4`
des deux lignes 993 est une cote du dessin de disque, pas un poids. Elle ne doit
pas alimenter `physical.mass`.

## Sources retenues

- [Catalogue Brembo du 993 Carrera 3.8](https://www.bremboparts.com/europe/de/catalogue/porsche-911-993-3-8-carrera/000004674-1),
  source fabricant pour l'application et les dimensions des trois références ;
- [fiche Brembo `09.8421.11`](https://www.bremboparts.com/europe/de/catalogue/disc/09-8421-11),
  source fabricant pour le côté droit, les dimensions et la désignation haut
  carbone ;
- [catalogue ATE Classic Porsche](https://www.ate.de/media/2826/atec3classic_2014-porsche.pdf),
  source fabricant pour les références Porsche, le schéma des cotes et le
  recoupement des dimensions avant.

Les valeurs de poids affichées par différentes boutiques n'ont pas été
retenues : elles ne sont ni publiées par le fabricant ni accompagnées d'un
protocole de pesée, et elles peuvent désigner poids net, poids emballé ou poids
d'expédition.

## Porte de sortie

Une référence pourra être admise après obtention de l'un des éléments suivants :

1. fiche fabricant ou TecDoc traçable donnant la masse nette unitaire et la
   matière ;
2. pesée documentée de la référence exacte, avec instrument et incertitude,
   complétée par une déclaration matière fabricant ;
3. mesure d'un disque OEM identifié sans ambiguïté, avec référence Porsche et
   état d'usure enregistrés.

Le freinage reste une classe critique : même admis dans l'inventaire numérique,
un composant ne serait ni déclaré fabricable ni libéré sans revue d'ingénierie
professionnelle et plan de validation approuvé.
