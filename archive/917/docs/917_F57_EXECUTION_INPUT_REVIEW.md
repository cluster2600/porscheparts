# F57 — point de décision avant poursuite industrielle

## État vérifié

La révision de travail conserve les STEP F53 2V/4V ayant passé les audits
OCCT. Les essais F54 d'épaississement n'ont pas corrigé les faibles
épaisseurs. Le maillage simplifié 4V conserve 1 050 éléments sous le seuil
strict. Ces tâches CAO restent inachevées ; leur échec ne doit pas être
attribué uniquement à des données fournisseur manquantes.

Les diagnostics F55 montrent l'effet du plafond et de l'absorption, mais
ne constituent pas une recette LPBF. F56 ajoute des références CP1 limitées,
sans fournir une carte complète à chaud ou un processus qualifié.

## Entrées indispensables non établies

| Élément demandé | Constat dans la source actuelle | Entrée nécessaire |
|---|---|---|
| Datums, filetages, porte-arbres/culbuteurs, ajustements | `internal-brep-contract-f47.json` classe les dimensions et interfaces comme hypothèses, sans échelle ni ajustement certifiés | Dossier d'interfaces moteur accepté par le responsable mécanique ; le scan seul et les dimensions d'une autre référence ne le remplacent pas |
| Procédé LPBF réel et compensation | F50 utilise une enveloppe Sapphire ; F56 décrit CP1/EOS séparément, sans transfert de qualification | Fournisseur, machine, matériau, traitement, paramètres et capabilité cohérents sur une route unique |
| Résistance et distorsion thermomécanique | `thermomechanical-screen-f50.json` concerne un témoin local, avec E, CTE, film d'air et serrage hypothétiques | Carte matériau à chaud, contacts/précharges et conditions thermiques justifiés pour la culasse complète |
| Validation de la fabrication | Aucun coupon ou contrôle de pièce fabriquée n'est apporté par F53–F56 | Qualification matière/procédé, revue professionnelle et plan de contrôle accepté |
| PhysicsNeMo | Pas de jeu admissible issu des calculs complets convergés | Cas CFD/CHT/FEA admissibles avant entraînement ; les diagnostics ne doivent pas devenir artificiellement des références |

## Conséquence pour l'exécution

Les calculs supplémentaires sur des cas témoins peuvent encore produire
des connaissances, mais ne ferment pas ces exigences industrielles.
Ils ne doivent pas être présentés comme une progression automatique vers
une culasse validée et imprimable. La puissance de calcul n'est pas le
verrou de ces entrées.

Il faut une coordination avec le responsable mécanique et un fournisseur
LPBF pour établir ces données. Aucune nouvelle mesure de l'utilisateur
n'est supposée disponible ; une acquisition ou validation externe est
nécessaire pour les informations absentes du scan. Aucun contact fournisseur,
achat ou transfert de géométrie privée n'est effectué par cet audit.

Le 6 septembre 2026, les diagnostics F55 ne tournent plus ; le conteneur
CAO consulté est inactif (`sleep infinity`). Aucune nouvelle location n'est
lancée. L'objectif complet reste non atteint ; ce dossier ne réduit pas
son périmètre et n'accorde aucune autorisation de fabrication.
