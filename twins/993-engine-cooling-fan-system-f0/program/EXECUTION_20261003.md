# Audit et exécutions du 3 octobre 2026

[Programme](../README.md) · [Manifestes SHA-256](../results/program-20261003/manifest.json) · [Reproduction](REPRODUCE.md)

## Reprise sans écraser les travaux

La mission utilise une branche dédiée issue de `origin/main` au commit
`807588d5`. Les modifications non committées du checkout principal et de
`codex/fan-qwen-local-chain` restent intactes. Le dossier `.agents/skills`
n'existe pas dans ces checkouts ; les instructions racine et la compétence
NVIDIA installée ont été consultées. Aucun journal privé de session n'a été lu.

La PR [103](https://github.com/cluster2600/porscheparts/pull/103) est fusionnée :
elle documente des essais de maillage non acceptés. La PR
[105](https://github.com/cluster2600/porscheparts/pull/105), commit audité
`ffe5ed00`, reste une reprise séparée : ses réparations et contrôles de maillage
ont progressé depuis le contexte initial de cette mission. Aucun changement
local non committé de cette PR n'est incorporé ici. La culasse PR106 reste
hors de ce programme.

## Scan

Le [compte rendu d'entrée](SCAN_INTAKE.md) détaille les contrôles. L'audit
supplémentaire préserve les index OBJ originaux, sans soudure de sommets,
réparation, mise à l'échelle ou export. Il confirme deux composantes,
8 611 arêtes ouvertes et 26 triangles d'aire nulle. L'absence d'unité, de
calibration et d'identité bloque les calculs sur ce scan. Les résultats détaillés
et aperçus restent privés ; les justificatifs de provenance ne sont pas publiés.

## Sorties CFD #105 désormais terminées

Les deux cas existaient déjà sur leur worker. À la lecture du 3 octobre, aucun
`foamRun` ni moniteur ventilateur n'y tourne. Les deux journaux finissent par
`End` et `Finalising parallel run`, à **2 000 itérations**. Aucun solveur n'est
relancé dans cette mission, aucun seuil n'est assoupli.

Les [reçus natifs](../results/program-20261003/cfd/native-receipts.tar.gz)
conservent journaux, dictionnaires, manifestes d'entrée, audits MRF et intégrales.
L'[auditeur indépendant](../source/audit_completed_cfd.py) recalcule les deux
fenêtres de débit/couple et les résidus depuis ces journaux : il retrouve les
[résultats contrôle](../results/program-20261003/cfd/control-summary.json) et
[candidat](../results/program-20261003/cfd/pitch42-summary.json).

| Critère #105 | Contrôle 36° | Candidat 42° | Critère inchangé |
|---|---:|---:|---:|
| Cellules du maillage accepté | 8 182 775 | 8 170 973 | Standard + géométrie/topologie étendues |
| Bilan masse maximal relatif | 8,23e-6 | 4,80e-6 | < 1e-3 |
| Dérive débit entre fenêtres | 4,37e-4 | 8,51e-4 | < 1e-3 |
| Amplitude débit relative | 5,89e-4 | 1,05e-3 | < 2e-3 |
| Amplitude couple relative | **3,36e-3** | **2,37e-3** | < 2e-3 : **échec** |
| Résidu initial U maximal | **3,64e-3** | **3,23e-3** | <= 1e-4 : **échec** |
| Résidu initial p maximal | **2,30e-2** | **2,14e-2** | <= 1e-3 : **échec** |

Les moyennes exploratoires de sortie valent 0,387227 et 0,429768 m³/s,
avec 137,04 et 182,43 W transmis au fluide. Ces valeurs sont des diagnostics
numériques rejetés, **pas une comparaison de performances validée**. Elles
ne démontrent ni gain de refroidissement ni débit sur moteur.
Les [audits](../results/program-20261003/cfd/control-audit.json) des
[deux cas](../results/program-20261003/cfd/pitch42-audit.json) montrent que la
bonne conservation de masse ne suffit pas à accepter la convergence.

Le modèle est un rotor isolé dans un conduit axisymétrique, MRF sur tout le
domaine, **-3 000 tr/min autour de +Z**, OpenFOAM **Foundation 14**.
L'alternateur et le circuit moteur sont absents. Le champ stationnaire ne
prévoit ni bruit ni charge vibratoire résolue. La qualité pariétale et
l'indépendance au maillage ne sont pas qualifiées. Aucun nouveau rendu de champ
CFD n'est fabriqué à partir de ces moyennes.

## Structure, rotation et modal

Les [résultats centrifuges existants](../results/organic/structure/reference-structure-50k/summary.json)
portent sur une reconstruction paramétrique et un régime supposé de 10 000 tr/min.
Ils donnent 248,21 MPa de von Mises maximal et 0,243 mm de déplacement maximal,
avec `mesh_independence=false`. Les comparaisons organiques conservent leurs
échecs de convergence et pics de bore : aucune marge matière/fatigue n'est
déduite. Les anciens [tests Newton/PhysX de rotation rigide](../OMNIVERSE_DIGITAL_TWIN.md)
sont des contrôles de dynamique simplifiée, pas d'élasticité des pales.

Un nouveau calcul **modal non précontraint** réutilise exactement le jeu de
référence de 86 640 tétraèdres quadratiques, dont le hash est celui du rapport
centrifuge publié. Le préprocesseur garde maillage, matériau et blocage du bore,
remplace uniquement le pas centrifuge par `*FREQUENCY`, et demande douze modes.
CalculiX **2.17** termine en **49,65 s** sur Kali2 Linux amd64, dans l'image CAE
préexistante identifiée par SHA-256, avec réseau désactivé et limites 4 CPU/6 GiB.

[Rapport modal](../results/program-20261003/modal/summary.json) ·
[Fréquences natives comprimées](../results/program-20261003/modal/modal.dat.gz) ·
[Journal](../results/program-20261003/modal/log.ccx) ·
[Jeu exact comprimé](../results/program-20261003/modal/modal.inp.gz)

Les deux premiers modes valent **348,259 et 348,450 Hz** ; le douzième vaut
**1 870,084 Hz**. Les valeurs sont positives, sans partie imaginaire, et le
contrôle rad/s → Hz retrouve les sorties. Ce calcul ne contient pas de
précontrainte centrifuge, terme gyroscopique, roulement, courroie, contact,
température ou amortissement mesuré. Il n'est pas une analyse Campbell en
rotation. Aucun régime sûr ou interdit ni tenue en fatigue n'est annoncé.

## LPBF

La carte [ZRapid iSLM420DN / AlSi10Mg](../zrapid-print-process.json), le
[screening géométrique](../PRINT_RELEASE.md) et les calculs thermiques
[2 mm](../results/organic/e/thermal-2/thermal-summary.json) /
[1,5 mm](../results/organic/e/thermal-15/thermal-summary.json) sont conservés et
accessibles depuis la page d'entrée. Ils sont rattachés à leurs propres modèles
organiques. Leur énergie homogénéisée et leurs sensibilités ne constituent
pas une simulation industrielle qualifiée de contraintes ou distorsion.
Le scan privé n'est utilisé dans aucun de ces calculs. Aucune impression réelle.

## Asset OpenUSD organisé

[fan-program.usda](fan-program.usda) référence le paquet existant de la
reconstruction Turbo. La hiérarchie sépare référence, matériau candidat et
espace de résultats ; les composants inconnus restent des scopes identifiés.
Elle déclare `metersPerUnit=1`, `upAxis=Z`, temps en secondes, conversions de
rotation explicites, statut du scan et des champs, hash de la référence et
validation physique fausse. Le shader AlSi10Mg reste une présentation de matière
candidate. Aucun champ CFD ou thermique d'une autre géométrie n'est plaqué dessus.

L'[audit OpenUSD 0.26.8](../results/program-20261003/usd-validation.json) ouvre la
composition et la réouvre après export, contrôle les extents en mètres contre
la validation géométrique existante après conversion mm→m, et ne trouve aucune
dépendance non résolue ni anomalie du validateur OpenUSD. L'écart maximal
d'extremum est 8,24 µm **entre deux représentations du modèle**, sous la tolérance
numérique 10 µm ; ce n'est pas la précision d'une pièce réelle.

Il ne s'agit ni d'un nouveau calcul RTX, ni d'une validation du profil SimReady,
ni d'un jumeau numérique physiquement validé. Les anciens rendus et leurs
conditions restent dans l'[archive Omniverse](../OMNIVERSE_DIGITAL_TWIN.md).
Le premier accès Docker du Mac était bloqué par le confinement. La vérification
hors confinement retrouve **Docker 29.8.1** ; l'image CAE historique F33 y est
absente. Le résultat initial n'est donc pas une preuve d'absence du daemon.
Kali1 n'a pas d'accès Docker autorisé, Kali2 oui. Aucun GPU NVIDIA n'est disponible sur Kali,
aucune location nouvelle ni changement d'accès/sécurité n'est effectué.

## Vérification du dépôt

Les résultats de `make check`, du contrôle d'accueil/liens, du diff et de la CI
sont conservés dans le [rapport de vérification](VERIFICATION.md).
Ils ne doivent pas être confondus avec les critères physiques
encore ouverts du [plan de validation](VALIDATION_PLAN.md).
