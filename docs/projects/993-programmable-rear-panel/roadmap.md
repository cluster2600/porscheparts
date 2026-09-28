# Feuille de route et backlog

Les durées sont des **hypothèses de planification**, à compter de l'autorisation
et de la disponibilité des pièces/prestataires, pas des délais promis.
Les montants renvoient aux postes uniques de [budget.csv](budget.csv) : ne pas les
additionner une deuxième fois. Aucune étape ne déclenche de dépense automatiquement.

| Étape / priorité | Dépendances | Responsable | Livrable | Durée indicative | Budget CHF / poste | Critère de sortie |
|---|---|---|---|---|---|---|
| G0 / P0 — cadrage réglementaire et variante | aucune | porteur + DTC / laboratoire éclairage TÜV | avis écrit sur fonctions d'origine et voies possibles | 1–3 semaines | 500–1 500 / regulatory_review | marché et référence définis ; route jugée faisable ou branche exposition seule décidée |
| G1 / P0 — pièce et scan | autorisation d'achat/prêt, accès physique | porteur + scanneur | dossier de mesures, données brutes, rapport d'incertitude | 1–2 semaines | 180 / donor ; 500–1 500 / scan | droits établis, surfaces/interfaces complètes, dimensions critiques vérifiées indépendamment |
| G2 / P0 — coupon optique | G1 pour échantillon représentatif ; coupon plan possible avant G1 | porteur + électronicien | mono/RGB derrière trois recettes de façade, mesures optiques/thermiques | 2–3 semaines | 250–700 / coupon | lisibilité et rendu éteint acceptés avec puissance mesurée ; choix pas/couleur |
| G3 / P0 — architecture et CAO | G0–G2 | porteur : toute CAO ; spécialiste : électronique | CAO native, plan interfaces, schéma/BOM revus, devis comparables | 3–6 semaines | 1 800–3 600 / mechanical ; 4 000–10 000 / electronics | démontabilité, chemin thermique, coût et alimentation sans modification démontrables |
| G4 / P1 — prototype intégré | G3 | spécialiste + porteur assemblage | PCBA et boîtier pleine largeur, traçabilité, firmware/app alpha | 4–8 semaines | 685–1 450 / historical_prototype ; 2 500–7 000 / firmware ; 3 000–10 000 / mobile_app | montage et défauts validés au banc ; sécurité BLE sur vrais téléphones |
| G5 / P1 — qualification | G4 et protocole accepté par laboratoire | laboratoire + spécialiste + porteur | rapports environnement/CEM/radio/optique, dossier réglementaire | 6–12 semaines ou plus | 2 000–6 000 / precompliance ; 5 000–20 000 / approval | résultats écrits et autorisations applicables, corrections retestées |
| G6 / P1 — présérie | G5 selon usage autorisé | porteur + EMS/optique | 10 unités traçables, banc de contrôle, emballage | 3–6 semaines | 1 000–3 000 / fixtures ; 500–1 500 / packaging_dev ; unités sur devis | temps réel, rendement, démontage et transport validés ; coût cible confirmé |
| G7 / P2 — série 100 puis 1 000 | G6, demandes réelles et autorisation distincte | porteur ; renfort étudiant éventuel | gamme assemblage, contrôle qualité, SAV, dossier origine par lot | à deviser | 223–420 / unité à 100 ; 138–271 à 1 000, historiques | pas de lancement avant financement, capacité et preuves de conformité |

**Ordre court :** cadrage réglementaire et recherche de pièce en parallèle ;
coupon avant grand PCB ; coût et faisabilité avant outillage. Arrêt ou reprise G2
si le filtre rouge impose une puissance incompatible avec l'enveloppe thermique.
Pas de compensation logicielle à un défaut des fonctions réglementaires.

## Backlog exécutable

| ID | Priorité | Action / preuve attendue | Dépendance |
|---|---|---|---|
| RP-01 | P0 | Identifier marché, millésime, carrosserie et référence ; photographier marquages et fonctions, sans identifiant véhicule public | G0 |
| RP-02 | P0 | Faire confirmer par DTC/TÜV le périmètre réflecteur/antibrouillard et le statut de l'affichage dynamique | RP-01 |
| RP-03 | P0 | Confirmer disponibilité/achat ou prêt de la pièce à 180 CHF ; ne pas envoyer de paiement depuis ce dossier | accord porteur |
| RP-04 | P0 | Envoyer après accord les RFQ scan et coupon/électronique ; récupérer droits, données et chiffrage séparé | RP-01/03 |
| RP-05 | P0 | Compléter measurements.csv ; définir datums, incertitudes et tolérances avec le porteur | scan |
| RP-06 | P0 | Comparer pas 2,5/4 mm et mono/RGB, mesurer transmittance et contraste | coupon |
| RP-06a | P0 | Faire transcrire et revoir le [circuit E0](electronics/coupon.md) : BOM et connexions préparées, encodeur hôte testé ; schéma natif/ERC/DRC puis assemblage et essais restent à faire | revue électronicien ; aucune commande lancée |
| RP-07 | P0 | Remplacer hypothèses budget par devis 1/10/100/1 000 ; identifier site réel de chaque opération | RP-04/06 |
| RP-08 | P1 | Porter la machine d'états sur MCU choisi ; authentification BLE et coupure matérielle, tests iOS/Android | choix MCU |
| RP-09 | P1 | Réaliser la CAO native et l'analyse d'empilement ; gabarit sans charge puis PCB intégré | RP-05/06 |
| RP-10 | P1 | Qualifier alimentation, RF, CEM, vieillissement optique, montage et emballage | prototype |
| RP-11 | P1 | Documenter coûts d'origine et activité essentielle ; faire revoir avant toute allégation suisse | devis + G6 |
| RP-12 | P2 | POC titre musical : iOS AMS, Android MediaSession, autoradio exact, chacun séparément | BLE stable |
| RP-13 | P2 | Déclinaisons : 964, autres 911 à bandeau identifiées, RUF et restomods au cas par cas | G6 |

Pour RP-13 : une fiche **par référence et marché**, accès à la pièce réelle,
fonctions homologuées, scan/dimensions/fixations, profondeur, alimentation,
optique et droits de marque. Aucune compatibilité 964/993, RUF/Porsche ou entre
restomods n'est présumée. Mutualiser éventuellement protocole et contrôle,
pas les interfaces mécaniques ni les dossiers d'homologation.

À l'augmentation des volumes : mesurer les heures d'assemblage avant de recruter ;
étudiants sous supervision avec formation ESD, instructions contrôlées et contrôle
final par le porteur. L'EPFL n'est ni partenaire ni garante de ce projet.
