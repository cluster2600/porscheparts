# Protocole de banc du système horizontal 935

Ce protocole prépare les essais futurs de la référence et de la variante.
Il ne donne aucune vitesse autorisée. Le régime maximal, les seuils de vibration,
les températures, les charges et les conditions de lubrification restent à
définir par la revue mécanique et les données des composants. Le
[contrat de mesure](../../../twins/935-horizontal-cooling-system-f0/measurement-contract.json)
conserve les quinze canaux existants et leurs inconnues.

## Dossier à figer avant essais

Associer un identifiant de spécimen et les empreintes CAO/maillage à la
nomenclature, aux interfaces, au matériau réel de chaque pièce, au procédé
d'impression, à l'orientation, aux traitements, à l'usinage et à l'inspection.
Contrôler les portées, les jeux, les fixations et les retenues d'arbres.
Consigner l'équilibrage, la configuration du carter et les stations de pression.
La référence historique et la variante sont deux configurations distinctes.

Le banc utilise une motorisation commandée, des mesures indépendantes de vitesse
à l'entrée et au rotor, une mesure de couple et une enceinte adaptée au rotor.
Le protocole d'arrêt découle des limites documentées des pièces et du banc.
L'essai de survitesse éventuel fait l'objet d'un protocole spécifique, après
la caractérisation initiale. Ce document ne déclenche aucun essai physique.

## Acquisition et calculs

| Mesures | Implantation et exploitation |
|---|---|
| Vitesses entrée/sortie | Capteurs indépendants ; sens positif par axe et vue définis ; rapport signé et glissement mesurés. |
| Couple entrée et rotor | Chaînes étalonnées ; `P = 2π n τ / 60` pour `n` en rpm ; pertes par différence des puissances après stabilisation. |
| Débit | Dispositif de mesure de débit étalonné dans le circuit du banc ; conserver débit volumique réel, débit massique, température et pression absolue. |
| Pressions | Stations et sondes identifiées en amont/aval ; distinguer statique et totale ; conserver le même référentiel que la CFD. |
| Vibrations | Accéléromètres du support et mesure de phase du rotor ; spectres, ordres et évolution avec le régime. |
| Températures | Air entrant/sortant, carter, appuis et lubrifiant selon accessibilité ; horodatage commun. |
| Lubrification | Pression, température et alimentation réellement définies pour le renvoi ; contrôler les pertes et les fuites. |

Documenter numéro de capteur, position/repère, étalonnage avant/après,
fréquence d'échantillonnage, filtrage, synchronisation, unité et incertitude.
La fréquence d'acquisition des vibrations doit résoudre les ordres étudiés,
avec filtre antirepliement ; elle dépend des régimes et de la denture identifiés.
La fréquence de passage des pales vaut `Z |n| / 60`. Le comptage géométrique
actuel donne neuf régions de pales ; confirmer ce nombre sur le spécimen.

Conserver les données brutes et les fenêtres moyennées. Estimer l'incertitude
de débit, pression, couple et puissance à partir des chaînes de mesure.
Ne pas confondre les erreurs admissibles des essais avec les seuils de
convergence des solveurs.

## Séquence

1. Transmission seule : montée contrôlée dans l'enveloppe autorisée, contrôle
   du rapport, des sens, des vibrations, de la lubrification et des pertes.
2. Rotor et carter sur banc : pour chaque régime retenu, faire varier la
   résistance du circuit ; mesurer débit, pression et couple jusqu'au domaine
   admissible documenté. Garder une station de mesure commune entre variantes.
3. Répétabilité : reprendre des points, répéter à température stabilisée et
   comparer montée/descente. Consigner les dérives et les interventions.
4. Validation : réserver des points avant tout ajustement du modèle ; comparer
   prédictions et mesures avec leurs incertitudes et les tolérances préétablies.
5. Système installé : ajouter les passages et charges du moteur seulement
   lorsque la variante, les interfaces et le réseau sont identifiés.

La comparaison vise davantage d'air utile à puissance absorbée comparable,
en comptant la transmission. Conserver aussi masse, inertie, jeux en rotation,
températures et vibration. Une hausse du débit libre ne prouve pas une hausse
du refroidissement installé.

## Archivage et statut

Chaque série référence la configuration, les fichiers natifs, les versions,
les capteurs, les conditions et les empreintes SHA-256. Séparer les données
de calibration des points réservés à la validation. Le statut
« fonctionnement physiquement validé » nécessite les résultats de ces essais
et leur revue ; il reste faux dans les livrables numériques actuels.
