# Plan de validation — aucun essai physique réalisé

Chaque essai doit produire version pièce/PCB/firmware, numéro interne non personnel,
conditions, instruments/étalonnage, données, critère défini **avant** essai et signature
du responsable. Les seuils physiques ci-dessous restent à fixer avec le spécialiste
et le laboratoire ; une case vide est un blocage, jamais un « conforme » implicite.

Le [protocole de mise au point E0-01 à E0-07](electronics/coupon.md) précise les
premiers contrôles de banc, les hypothèses chiffrées d'arrêt et la limite connue
en cas de MCU bloqué. Aucun de ces essais physiques n'a encore été réalisé.

| ID / porte | Essai | Responsable / preuve | Critère avant passage |
|---|---|---|---|
| V01 / G0 | Inventaire réglementaire original | porteur + laboratoire ; référence, marquages, photos | toutes fonctions et marchés identifiés ; avis écrit sur voie possible |
| V02 / G1 | Scan et mesures critiques indépendantes | scanneur + porteur ; rapport couverture/incertitude | datums et tolérances convenus, aucun trou interpolé sur fixation sans mesure |
| V03 / G2 | Coupons teinte/épaisseur/entrefer | porteur ; spectre ou transmission R/G/B, haze, lux/contraste, photos réglages fixes | seuils de contraste/lisibilité à 1/3/5 m et angles convenus ; test jour, soleil et nuit, absence d'éblouissement évaluée. Distances = protocole proposé, pas cotes pièce |
| V04 / G2 | Puissance et température coupon | électronicien ; tension/courant moyens et pointes, thermocouples | plafond thermique défini par composants/matières ; mesures fermées et dégradées sans dépassement |
| V05 / G3 | Gabarit puis montage | porteur ; CAO native, rapport écart et photos | mêmes interfaces ; pas perçage/épissure ; absence contact carrosserie, dilatation, jeux et serrage validés |
| V06 / G4 | Alimentation au banc | spécialiste ; profils démarrage/transitoires/polarité/court-circuit sur générateur adapté | niveaux ISO et critères convenus ; pas feu/fumée, récupération définie, fonctions réglementaires préservées |
| V07 / G4 | Firmware et radio réels | spécialiste ; matrice OS/modèle/version + logs | MITM/rejeu/non-propriétaire rejetés ; flux max, MTU 23, coupures à chaque offset ; watchdog et noir vérifiés électriquement |
| V08 / G4 | DFU sécurisé | spécialiste ; images signées/invalides, coupure énergie par étape | signature/anti-retour appliqués, aucune image partielle démarrée, récupération locale et clés protégées |
| V09 / G5 | Climat/UV/eau/vibrations | laboratoire ; protocole et avant/après optique/montage | plage T, nombre cycles, dose UV, vibration et niveau IP convenus ; pas fuite, corrosion, jaunissement/jeu hors tolérance. Aucune revendication IP avant essai complet |
| V10 / G5 | CEM/ESD/RF | laboratoire compétent ; rapports liés à révision exacte | limites/normes choisies respectées ; immunité avec comportement sûr et réception BLE vérifiée en montage |
| V11 / G5 | Photométrie/réflexion/installation | laboratoire + autorité | chaque fonction requise et visibilité conformes ; documents et marquages légalement autorisés, pas simple extinction logicielle |
| V12 / G6 | Présérie 10 pièces | porteur + EMS ; temps, rendement, FAI/AOI, test 100 % | critères d'acceptation avant fabrication ; zéro unité expédiée sans trace test, reprise documentée |
| V13 / G6 | Réparabilité | porteur ; démontage/remontage documenté | échange façade/PCB/joint sans détruire le reste ; étanchéité et optique retestées |
| V14 / G6 | Transport emballé | fournisseur + porteur ; chute/vibration/compression selon méthode convenue | aucune rayure, fissure, détérioration fixation ; contrôle électrique avant/après ; hauteur/charges selon masse finale et circuit logistique |
| V15 / G7 | Budget et origine | porteur + conseil ; devis, factures, heures, registre | coût livré acceptable ; preuve indépendante du ratio et activité essentielle avant allégation suisse |

## Pannes à injecter

Coupure alimentation, brownout, MCU bloqué, watchdog, capteur thermique ouvert/
court-circuit, surchauffe, LED/driver court-circuit, mémoire altérée, câble partiellement
branché, humidité et liaison téléphone perdue. L'écran programmable doit revenir
au noir sans altérer l'éclairage obligatoire. Vérifier cette indépendance en panne
matérielle, pas seulement avec `STOP` dans l'application.

## Traçabilité et réception

Mesures/rapports privés stockés avec identifiants et droits ; publier un résumé
sanitisé et son hash si autorisé. Toute modification optique, driver, alimentation,
firmware ou fournisseur fait l'objet d'une analyse des essais à refaire. Les tests
Python de ce dossier vérifient un contrat hôte ; ils ne ferment aucune porte
mécanique, électrique, radio, sécurité routière ou qualification fabrication.
