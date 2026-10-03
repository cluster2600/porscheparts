# Commandes reproductibles

[Programme](../README.md) · [État des calculs](EXECUTION_20261003.md)

Exécuter depuis la racine du dépôt. Les scripts refusent d'écraser leurs sorties.
Choisir des répertoires neufs. Les scripts nouveaux auditent le scan en privé et
des reçus existants ; ils ne créent aucun modèle fonctionnel à partir de cotes
inconnues. La CI utilise Python 3.12, NumPy 2.2.6 et Matplotlib 3.10.8.

## Contrôles du programme

```sh
make fan-program-check
make check
python3 scripts/check_doc_links.py --strict
git diff --check
```

Le premier contrôle n'a pas besoin de solveur ni de GPU. `make check` inclut des
audits Docker historiques de la culasse 917 ; un runtime absent doit être
signalé, jamais présenté comme un test réussi. Le test du scan nécessite NumPy.

## Scan local privé

Avec Python et NumPy, indiquer le fichier de l'utilisateur sans le copier dans
un chemin versionné :

```sh
python3 twins/993-engine-cooling-fan-system-f0/source/audit_private_scan.py \
  "$PRIVATE_SCAN" work/fan-scan-audit-new/report.json
```

Le rapport contient des coordonnées privées : garder `work/` ignoré et ne pas
publier les aperçus. Le script ne fait ni réparation ni rescaling. Les sources
scan et les justificatifs ne sont pas nécessaires aux tests synthétiques.

Pour la copie de préparation réversible, toujours privée :

```sh
python3 twins/993-engine-cooling-fan-system-f0/source/prepare_private_scan.py \
  "$PRIVATE_SCAN" work/fan-private-preparation-new \
  --expected-sha256 244d4caeb2c4ac4a692b650ec9d766bee2a8124335a0236a55a1d30c1b2b98ba
```

Cette commande normalise seulement la pose globale et retire les faces d'aire
exactement nulle. Elle conserve les trous et le défaut éventuel d'alignement
relatif ; elle refuse un fichier ne correspondant pas au hash d'entrée.

## Modèles et variantes

Les commandes et dépendances PicoGK de la reconstruction et des variantes sont
conservées dans [REFERENCE_REBUILD](../REFERENCE_REBUILD.md) et
[ORGANIC_BLADE_STUDY](../ORGANIC_BLADE_STUDY.md). Employer leurs paramètres
éditables, conserver `generation.json`, hash source et contrôles du maillage.
Une exportation STEP à partir d'une surface ne rendrait pas les datums connus.
Le candidat 42° et le pipeline CFD corrigé se trouvent au commit **ffe5ed00** de
la [PR105](https://github.com/cluster2600/porscheparts/pull/105), avec leurs
[preuves de maillage](https://github.com/cluster2600/porscheparts/releases/tag/fan-cfd-mesh-recovery-2026-10-02).
Ne pas lancer deux campagnes pour les mêmes variantes.

## Audit des calculs CFD terminés

```sh
mkdir -p work/fan-final-audit-new
tar -xzf twins/993-engine-cooling-fan-system-f0/results/program-20261003/cfd/native-receipts.tar.gz \
  -C work/fan-final-audit-new
python3 twins/993-engine-cooling-fan-system-f0/source/audit_completed_cfd.py \
  work/fan-final-audit-new/control-full-frame-flow work/fan-final-audit-new/control-audit.json
python3 twins/993-engine-cooling-fan-system-f0/source/audit_completed_cfd.py \
  work/fan-final-audit-new/pitch42-full-frame-flow work/fan-final-audit-new/pitch42-audit.json
```

Une sortie zéro signifie que le reçu correspond aux données natives. Les deux
flags `integral_checks_passed` et `nonlinear_residual_checks_passed` restent faux.
Pour refaire la CFD, suivre les commandes et garde-fous #105 ; ce paquet contient
les preuves et conditions finales, pas les champs volumiques/maillages complets.
Leur récupération depuis les archives de campagne et un runtime suffisamment
dimensionné restent nécessaires. Aucun seuil ne doit être relâché.

## Refaire le calcul modal

```sh
mkdir -p work/fan-modal-new
gzip -dc twins/993-engine-cooling-fan-system-f0/results/program-20261003/modal/modal.inp.gz \
  > work/fan-modal-new/modal.inp
cp twins/993-engine-cooling-fan-system-f0/results/program-20261003/modal/preparation.json \
  work/fan-modal-new/preparation.json
cd work/fan-modal-new
OMP_NUM_THREADS=4 ccx modal > log.ccx 2>&1
cd ../..
python3 twins/993-engine-cooling-fan-system-f0/source/summarize_modal_screen.py \
  work/fan-modal-new work/fan-modal-new/summary.json
```

CalculiX 2.17 a été utilisé, image existante
`sha256:1dc508c2bfab4d9911707fbfd9cacdf43faf84956a1502805194e3e70e18ae68`.
Le jeu exact suffit à refaire ce calcul sans scan. Pour préparer un autre cas à
partir d'un **jeu centrifuge audité du même modèle**, employer
`twins/993-engine-cooling-fan-system-f0/source/prepare_modal_screen.py SOURCE_INP NEW_DIRECTORY --modes 12`.
Cela produit des modes non précontraints ; ne pas les appeler Campbell.

## LPBF et asset OpenUSD

Les commandes géométriques, thermiques et de sensibilité existent dans
[ORGANIC_BLADE_STUDY](../ORGANIC_BLADE_STUDY.md) ; fournir la carte
[zrapid-print-process.json](../zrapid-print-process.json), identifier matériau,
machine, orientation, source exacte et hypothèses. Les calculs ne sont pas un
programme machine, ne prédisent pas de distorsion qualifiée et n'autorisent pas
de fabrication.

Ouvrir `program/fan-program.usda` dans une application compatible OpenUSD.
Avec le runtime `usd-core` 26.8 disponible, on peut reproduire la composition
sous un **nouveau nom dans le même dossier** pour garder les références relatives :

```sh
python3 twins/993-engine-cooling-fan-system-f0/source/build_program_asset.py \
  twins/993-engine-cooling-fan-system-f0/program/fan-program-reproduction.usda \
  work/fan-usd-reproduction-new.json
```

Les résultats des solveurs restent dans leurs dossiers avec conditions/hashes.
L'asset ne simule pas la mécanique ou le fluide par simple ouverture. Kit-CAE et
le rendu RTX constituent des étapes distinctes, à vérifier dans un runtime
compatible lorsqu'une ressource GPU autorisée est disponible.
