# Raffinement local et deux calculs élastiques réels — 17 octobre 2026

Cette capsule conserve le raffinement discret du maillage EF7 et les deux cas
élastiques réellement terminés sur ce maillage : appuis rigides et K1000.
Elle permet de **restaurer leurs octets et de refaire les analyses indépendantes**.
La réanalyse portable a été exécutée depuis `/` ; elle ne relance ni CCX, Gmsh,
CAD, raffinement, ni génération de supports.

## Résultats conservés et portée

Le raffinement adaptatif 002 a terminé avec RC0 en quatre passes :
160 964 nœuds et 86 544 T10, contre 159 121 nœuds et 85 315 T10 pour EF7.
Les anciens nœuds, les ensembles nodaux et les 3 218 facettes protégées sont
conservés. Le volume mesuré reste 285509.97867191856 mm³, égal à la valeur
mesurée de départ ; le contrôle des jacobiens est positif sur tous les éléments.
Les deux maxima d’arêtes des boîtes fixes sont respectivement
1.3844416177416714 et 1.2586178907902892 mm, sous les cibles inchangées
1.3844416177456211 et 1.2586178907907173 mm. Ces cibles sont la moitié de
l’arête maximale du tétraèdre du pic **initial**, pas du maximum de la boîte.
Le [dossier visuel 21](../../progress-figures-20261016/local-refinement-20261017/README.md)
illustre ce périmètre géométrique.

Les deux cas utilisent E = 107 000 MPa, ν = 0,31, Fz = −4 000 N et
My = +850 000 N·mm. K1000 conserve la raideur translationnelle totale de
1 000 N/mm par œil et par axe, répartie sur les nœuds. Le changement de maillage
ne modifie ni les charges, ni les rosters, ni la loi élastique. Les étiquettes
9 et 7 sont les identifiants historiques de maillage, pas une mesure locale h.

| Cas | Maillage | Pic von Mises IP (MPa) | Déplacement maximal (mm) | Élément / IP |
|---|---|---:|---:|---|
| Rigide | 9 | 700.7608420501294 | 2.76226589096363 | 38852 / 3 |
| Rigide | 7 | 617.7164972717483 | 2.7965981963118067 | 33077 / 2 |
| Rigide | local h/2 | 1108.2238229044212 | 2.797597854140128 | 85535 / 1 |
| K1000 | 9 | 1857.9107572863848 | 18.077756681193904 | 38852 / 3 |
| K1000 | 7 | 1676.5460429720838 | 18.24864939681427 | 63644 / 2 |
| K1000 | local h/2 | 3337.3220663444367 | 18.250699453907206 | 85535 / 1 |

Les deux pics migrent et augmentent, par rapport à EF7, de **79,4 % et 99,1 %**.
Ils se trouvent tous deux à l’élément 85535/IP1 sur le nouveau maillage.
Les valeurs et tous les ex æquo sont conservés dans [comparison.json](comparison.json).
Le contrôle géométrique est passé ; **la convergence des contraintes reste à
étudier**. Aucun seuil de résistance ni critère de convergence n’est ajouté.

Les bilans énergétiques indépendants des deux nouveaux cas passent le seuil
inchangé de 1e−4 : erreurs relatives 1.944009175858241e−9 et
1.725379805694871e−8. Les calculs natifs ont réellement terminé avec RC0 et leurs
conteneurs propriétaires sont supprimés ; leurs reçus et clôtures sont inclus.
Le modèle conserve ses hypothèses d’appuis et de chargement ; aucun procédé
LPBF qualifié ni admission globale des supports n’en est déduit.

## Trois archives intégrales

| Archive | Fichiers | Taille compressée (octets) | Contenu |
|---|---:|---:|---|
| [common.zip](common.zip) | 43 | 26 648 649 | EF7 original, ses parents CAD, les 14 sorties H2, plans, preuves et petits bilans de référence 9/7 |
| [rigid.zip](rigid.zip) | 29 | 65 927 531 | Dossier rigide complet, parents CAD, maillage, INP, DAT, FRD, NPZ, logs et reçus |
| [spring.zip](spring.zip) | 29 | 66 425 174 | Dossier K1000 complet, mêmes catégories de données et reçus |

Les **101 fichiers / 370 717 219 octets** d’origine sont tous conservés.
Aucun fichier natif de ces deux dossiers n’est omis, y compris les fichiers
vides et le binaire `ccx.prestart` extrait pour son contrôle préalable.
Les chemins relatifs au dépôt sont conservés. Les trois fichiers ZIP restent
chacun strictement sous 100 000 000 octets. L’archivage utilise DEFLATE niveau 6,
zlib 1.2.11, ordre lexical, date ZIP fixe 1980-01-01 et mode normalisé 100644.
Il restitue les octets, sans promettre les inodes ou les dates d’origine.
Les sources de cet emballage et ses reçus restent dans `sources/` et `evidence/`.

[manifest.json](manifest.json) lie les trois ZIP, chaque membre décompressé,
les sources et les utilitaires. [archive.json](archive.json) couvre l’inventaire
durable final, y compris ce README et les reçus de vérification ultérieurs.
Le manifeste interne utilisé lors de la réanalyse reste inchangé. La copie
commune finale ajoute explicitement les cinq parents CAD originaux aux premières
archives ; les deux reçus d’emballage conservent cette provenance, sans modifier
les originaux ni réemballer les deux cas mécaniques.

Les sources figées `audit_energy`, `simulate`, `locate`, pont T4/T10,
mesureur, ordonnanceur adaptatif et supervision CCX sont copiées à l’octet.
Les dix-huit copies initiales sont liées dans [copy-origins.json](copy-origins.json).
La roue publique scikit-fem 12.0.2, sa licence BSD-3-Clause et la provenance PyPI
sont incluses dans `software/` ; aucune installation n’est faite par la capsule.
Les quelque 2 500 fichiers du runtime ne sont pas embarqués.

## Réanalyse portable réellement exécutée

La session 81651 est collectée avec RC0, groupe propriétaire fermé sans signal,
en **16,047806 s** sous le superviseur inchangé (180 s, grâces 10+10).
Le script utilise 150 s internes, CPU 140/141 s, un thread BLAS et zéro worker.
L’enfant consomme 15,393499 s murales, 15,082749 s CPU et 589 053 952 octets RSS.
Les 536 pins de lancement et les 500 identités Python/NumPy restent inchangés.

`audit_energy.audit` original relit les vrais DAT/NPZ/decks restaurés avec son
seuil 1e−4, puis `locate.locate_case` original vérifie tous les IP et ex æquo.
Les **quatre rapports complets** (énergie et pics pour chaque cas) sont égaux
aux originaux, également à l’octet après sérialisation. Les étiquettes des cas,
le SHA du maillage H2, les pics 1108.2238229044212 / 3337.3220663444367 MPa et
85535/IP1 sont contrôlés. Aucun ancien résultat n’est simplement renommé.

La [clôture réelle](verification/portable-terminal-collection.json), la
[supervision](verification/reanalysis-supervision.json), le
[reçu de réanalyse](verification/reanalysis-receipt.json), les quatre rapports
et les journaux complets sont inclus. Le répertoire de restauration distinct
reste dans le `work/` du propriétaire du test ; ses gros fichiers ne sont pas
recopiés une seconde fois dans la capsule.

## Commandes de vérification et reproduction

Depuis n’importe quel répertoire, avec une copie complète de la capsule :

```sh
CARRIER_CAPSULE=/chemin/absolu/vers/local-refinement-20261017
CARRIER_MANIFEST=48917edd0ed4b83109ec6d5a8b4c874b82566b27a87dcf887d837725a018eaef
python3 -B "$CARRIER_CAPSULE/selfcheck.py"
python3 -B "$CARRIER_CAPSULE/restore.py" verify --manifest-sha256 "$CARRIER_MANIFEST"
```

La vérification des ZIP et la restauration ne dépendent que de la stdlib.
Une restauration seule utilise `restore.py restore /SORTIE/NEUVE` et le même
argument `--manifest-sha256` ; les sorties existantes ou symboliques sont refusées.
Pour la réanalyse, utiliser Python 3.10.11 et le NumPy 2.0.2 attesté, conservés
en lecture seule. Leurs empreintes attendues sont dans `runtime-provenance.json`.
Une **nouvelle sortie** est requise ; aucune opération ne réutilise ou n’écrase
le premier rejeu :

```sh
CARRIER_ANALYSIS_PYTHON=/chemin/vers/geometry-standalone/bin/python
CARRIER_NUMPY_SITE=/chemin/vers/cad-base/lib/python3.10/site-packages
CARRIER_OUTPUT=/chemin/absolu/vers/une-sortie-neuve
cd /
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  nice -n 10 "$CARRIER_ANALYSIS_PYTHON" -I -B "$CARRIER_CAPSULE/replay_analysis.py" \
  "$CARRIER_OUTPUT" --manifest-sha256 "$CARRIER_MANIFEST" \
  --numpy-site "$CARRIER_NUMPY_SITE"
```

Le plan de supervision historique complet et le petit wrapper `cwd=/` sont
inclus pour documenter le plafond externe réel et le nettoyage du groupe.
Les huit selfchecks stdlib couvrent chemins, intégrité des membres, collisions,
sorties symboliques, identités des cas et absence d’import scientifique au chargement.

**La capacité prouvée est une restauration et une réanalyse portable.**
Une nouvelle exécution de CCX ou du raffinement exige le dépôt, les runtimes et
l’image ARM64 attestée c977…/CCX 2.21 ; les sources et plans d’origine sont
conservés à cette fin. Le binaire préstart isolé ne suffit pas à fournir un
solveur autonome. La [capsule des restaurations logicielles](../../software-archive-restoration-20261017/README.md)
documente séparément les logiciels déjà restaurés.
