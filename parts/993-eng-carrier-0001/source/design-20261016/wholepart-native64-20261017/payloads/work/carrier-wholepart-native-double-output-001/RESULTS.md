# Pièce entière — résultat numérique natif double précision

**RC0, quatre états entiers et contrôles numériques passés**,182,199s total,
167,210s natif. Imagec977/binaireCCX2.21 inchangés,1CPU/6GiB/réseau none ;
conteneur supprimé, pas d'OOM,59pins inchangés. Aucune compilation/installation.
L'ancien piloteRC1 et ses25pins restent entièrement conservés.

Le seul changement de deck est prouvé avant lancement : quatre cartes
`*NODE FILE`→`*NODE OUTPUT,DOUBLE`. Le DAT ENTIER est byte-identique au premier
calcul. U est maintenant lu dans le FRD natif binary64, avec tous les IDs,
coordonnées bit-identiques et connectivités C3D10 vérifiés. Les charges,
matériaux, températures, sixjauges, gradients et limites d'acceptation sont les
mêmes. Le seuil strain10⁻⁷ n'a pas été assoupli.

|Contrôle|Erreur u maximale|Erreur strain maximale|Contrainte max composante|
|---|---:|---:|---:|
|Zéro|0mm|0|0MPa|
|Uniforme libre|9,959×10⁻¹³mm|1,243×10⁻¹⁴|1,876×10⁻⁹MPa|

Le lecteur de sortie résout donc la limite d'observation du DAT7chiffres.
Ce n'est pas une autre réponse mécanique : les autres champs natifs DAT sont
identiques. Les19tests logiciels, le petit C3D10 natif et le calcul entier sont
trois preuves séparées.

## Réponse sous le champ quadratique imposé

|Mesure|Bridé provisoirement|Libéré avec sixjauges|
|---|---:|---:|
|Déplacement maximal|9,866625µm|58,090066µm|
|Contrainte maximale de composante|15,98341MPa|3,394341MPa|
|Volume déformé intégré|285381,954121mm³|285381,333031mm³|

Le déplacement maximal dû au débridage est57,471042µm. L'entraxe des grands
alésages passe559,999602→559,986415mm, soit−13,187112µm. Les entraxes des deux
paires de boulons varient de−0,722619 et−0,720048µm. Les six diamètres projetés
varient de−0,190538 à−0,275019µm. Les centres/résidus et toutes les valeurs sont
conservés dans le reçu numérique ; il s'agit des mêmes nœuds, pas d'un nouveau
cylindre métrologique ajusté. Force et moment et detF passent aux quatre états.

La masse de matière EFρ₀V₀ reste **1,261483504kg**, variation0, indépendamment
du volume déformé. La multiplier par le volume final avecρ₀ inchangé serait
incorrect. Cette masse de maillage EF n'est pas une nouvelle mesure STEP.

Le champ est `ε*(Z)=−10⁻⁴((Z−Zmin)/H)² I`, échantillonné aux nœuds par une
température équivalente. E etν sont constants. Le bridage est le vrai plan
Zmin−22mm/3845nœuds, explicitement provisoire. Aucun dépôt/refroidissement
thermique, loi de plasticité thermique ni libération des sept supports physiques
n'est simulé : c'est une sensibilité mécanique entière reproductible,
**pas une prévision LPBF ni une admission de fabrication**.

## Rejeu et preuves

`plan.json`, `whole-preflight.json` et leurs59pins décrivent l'exécution.
`execution-001/solver-execution-receipt.json` conserve le vrai RC natif et le
nettoyage ; `execution-001/numerical-assessment.json` porte tous les contrôles ;
`whole-terminal-collection.json` atteste le vrai RC0 collecté. `result-summary.json`
lie ces preuves. `bundle.json` inventorie les fichiers work sans en faire une
copie supplémentaire. Aucun commit/publication avant revue root.
