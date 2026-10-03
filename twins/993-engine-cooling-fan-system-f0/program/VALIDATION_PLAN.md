# Plan de validation du ventilateur

[Programme](../README.md) · [État des exécutions](EXECUTION_20261003.md)

Les cinq étapes ci-dessous sont ordonnées par dépendance. Un contrôle logiciel
réussi ne clôt pas un contrôle physique. Chaque résultat doit identifier sa
géométrie, son hash, sa variante, ses unités, son runtime et ses conditions.

| Étape | Travail et sortie vérifiable | Dépendance réelle / état |
|---|---|---|
| 1. Identifier et mesurer | Provenance/droits, référence Carrera/Turbo/935, unité/calibration indépendante, scan complet et repère | Bloqué pour la pièce réelle : informations du scan et métrologie absentes |
| 2. Construire la référence | Géométrie source éditable, rotor/moyeu séparés ; datums, portées, alésages, perçages, tolérances, jeu carter et chaîne d'entraînement mesurés | Paramétrique exploratoire disponible ; référence fonctionnelle incomplète |
| 3. Calculer | Maillages fidèles et acceptés avant CFD ; centrifuge/contact/thermique, modes en rotation, courbes débit/pression/couple à conditions identiques, bilans et sensibilités | Statique/modal exploratoires ; CFD isolée #105 rejetée en convergence |
| 4. Préparer LPBF | Matière/machine/lot/paramètres qualifiés, orientations/supports/usinage/traitement, coupons, distortion/résidus/recoater et inspection | Scénario géométrique/thermique disponible ; calibration et données physiques absentes |
| 5. Composer le jumeau | OpenUSD : unités/axes/temps/matériaux, paramètres et champs natifs identifiés, états de validation visibles, puis confrontation aux mesures | Asset de revue contrôlé ; jumeau physique non validé |

## Géométrie et chemin des efforts

Mesurer les datums rotor/moyeu/roulement, portées et faces, entraxes et diamètres
de perçages, empilage cône/entretoises/poulies et faux-rond. Résoudre les
divergences documentées sur le moyeu 96410605131. Identifier le kit d'entraînement
selon la variante d'alternateur à sélectionner (175 A / 240 A et autres montages
documentés), rapport moteur/ventilateur/alternateur, signe de rotation et enveloppe
de vitesses/overspeed. Aucun rapport n'est supposé solidaire. Tracer la reprise
des charges centrifuges, couple d'entraînement, courroie, appuis et dilatation.

## Calcul mécanique et dynamique

Le matériau isotrope E = 70 GPa, nu = 0,33, rho = 2 670 kg/m³ et le bore encastré
des écrans existants sont des hypothèses. Qualifier les propriétés orientées et
à température pour l'état LPBF/traité/usiné retenu. Comparer des maillages et
appuis/contact réalistes ; distinguer pics de singularité et contraintes de
racine. Ajouter précontrainte centrifuge, effets gyroscopiques, courroie et
raideurs de roulements pour une analyse modale en rotation et Campbell.
Une fréquence propre non précontrainte ne donne ni vitesse interdite validée
ni marge en fatigue. Définir cycles, défauts, surface, corrosion, fretting,
équilibrage et essais en enceinte avec un ingénieur responsable.

## CFD

Conserver les contrôles standard et étendus ainsi que l'audit des surfaces.
La simplification MRF sur tout le domaine ne vaut que pour le conduit
axisymétrique isolé #105 ; ajouter un alternateur fixe nécessite une interface
rotative adaptée. MRF stationnaire ne résout ni interactions transitoires,
bruit, vibration ni fatigue. Tracer la famille/version OpenFOAM ; les sorties
finales examinées sont **Foundation 14**, pas OpenCFD v2312.

Les critères #105 restent inchangés : deux fenêtres complètes de 100 itérations,
bilan masse < 0,1 %, dérive débit/couple < 0,1 %, amplitude relative < 0,2 %,
résidus initiaux max U <= 1e-4 et p/k/omega <= 1e-3. Les deux cas les échouent.
Il faut ensuite indépendance maillage, résolution pariétale/y+, turbulence et
conditions d'entrée/sortie, courbe ventilateur et résistance moteur mesurées.
Le [cadre NASA](https://www.grc.nasa.gov/www/wind/valid/tutorial/verassess.html)
sépare convergence itérative, conservation et convergence spatiale/temporelle.

La poursuite des deux cas de plus de huit millions de cellules n'est pas
lancée. Le worker historique a été supprimé par une autre tâche pendant la
sauvegarde autorisée. Les journaux finaux des deux cas sont conservés ; les
32 partitions finales du contrôle sont sauvegardées et vérifiées localement.
Les champs complets du candidat ne sont pas présents dans ce transfert
interrompu. Vérifier les archives de l'autre tâche avant tout recalcul ; voir
l'[état de récupération](EXECUTION_20261003.md#sauvegarde-des-champs-finaux).
Aucune nouvelle location n'est autorisée. Kali est disponible
avec environ 15 GiB par hôte, sans preuve de mémoire suffisante pour ces mêmes cas.
Définir un pilote plus petit traçable et vérifier sa fidélité serait une étape
de récupération numérique ; il ne résoudrait pas les interfaces manquantes.

## Fabrication additive

Réutiliser la [carte ZRapid / AlSi10Mg](../zrapid-print-process.json) comme
**scénario de recherche** : iSLM420DN, un laser actif supposé, axe rotor selon
Z plateau, couches 40 µm, supports homogénéisés et matériau constant.
Le calcul énergétique moyenné ne résout pas bain fondu, phase, plasticité,
contraintes résiduelles, libération du plateau ou collision recoater. Il ne
peut pas prédire une précision finale ou valider une durée/coût de production.
Les sensibilités absorption, pas spatial et temps restent utiles pour cet
écran seulement. [NIST](https://www.nist.gov/programs-projects/metrology-am-model-validation)
décrit le besoin de données mesurées pour valider les modèles AM.

Le plan fournisseur doit fixer orientation/supports réellement retirables,
vidange de poudre, surépaisseurs et datums d'usinage, traitement thermique/HIP
justifié, inspection dimensionnelle/CT/FPI, fatigue et équilibrage final.
La [barrière de fabrication](../PRINT_RELEASE.md) demeure ouverte. Aucune
fabrication réelle, commande ou prise de contact fournisseur n'est effectuée.

## OpenUSD et Omniverse

L'asset de revue utilise mètres, axe +Z, temps en secondes ; aucun champ CFD
ancien n'est attaché à la référence. Vérifier les extents du modèle après
composition avec le facteur mm→m et rouvrir l'export. Ne pas inventer de
géométrie pour les composants absents. Les shaders sont de présentation ; ils
ne qualifient pas l'alliage. [Unités OpenUSD](https://openusd.org/release/api/group___usd_geom_linear_units__group.html) :
sans déclaration, la longueur utilise 0,01 m par unité. Pour un futur champ de
rotation, USDPhysics exprime la vitesse angulaire en degrés/s, le solveur utilise
rad/s et le régime tr/min : convertir explicitement et vérifier signe/axe.

[Kit-CAE](https://docs.omniverse.nvidia.com/guide-kit-cae/latest/kit-cae-v2.html)
et ses [plugins OpenUSD](https://github.com/NVIDIA-Omniverse/cae-openusd-plugins)
peuvent composer des résultats scientifiques ; les lecteurs couvrent un
sous-ensemble des formats. Garder les sorties solveur natives, associations
cellule/point, unités de champs et métadonnées de run. Aucun nouveau rendu RTX
ou déploiement Content Agents n'est lancé sans GPU disponible dans le périmètre.
