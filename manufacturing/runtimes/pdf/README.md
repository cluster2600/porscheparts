# Runtime PDF du guide atelier

Ce lock cible **CPython 3.12 sur macOS arm64**. Le venv neuf a été vérifié avec
CPython **3.12.14**, ReportLab **4.4.9**, Pillow **12.3.0** et
charset-normalizer **3.5.2**. Les trois dépendances de base sont entièrement
épinglées ; aucun extra de ReportLab n'est activé.

Les noms de roues, URLs et SHA256 ont été contrôlés sur les métadonnées primaires
PyPI de [ReportLab](https://pypi.org/project/reportlab/4.4.9/),
[Pillow](https://pypi.org/project/pillow/12.3.0/) et
[charset-normalizer](https://pypi.org/project/charset-normalizer/3.5.2/), puis
sur les octets téléchargés. [wheels.json](wheels.json) conserve ces identités.
Les roues natives sont `cp312`, Pillow étant limité à `macosx_11_0_arm64` et
charset-normalizer fourni en `macosx_10_13_universal2`.

Depuis la racine du dépôt, avec un Python 3.12 installé et un dossier **neuf** :

```sh
python3.12 -c 'import platform,sys; assert sys.version_info[:2] == (3,12) and sys.platform == "darwin" and platform.machine() == "arm64"'
python3.12 -m venv work/part-workflow/runtimes/pdf-base-001
work/part-workflow/runtimes/pdf-base-001/bin/python -m pip --isolated install \
  --index-url https://pypi.org/simple --only-binary=:all: --require-hashes \
  -r manufacturing/runtimes/pdf/requirements-macos-arm64-python312.lock.txt
work/part-workflow/runtimes/pdf-base-001/bin/python -m pip --isolated check
work/part-workflow/runtimes/pdf-base-001/bin/python -B -m unittest \
  tests.test_part_workflow_guide -v
```

Pour une installation hors réseau, placer les trois roues exactes de
`wheels.json` dans un dossier et remplacer `--index-url ...` par
`--no-index --find-links /chemin/roues`. C'est ce mode qui a été exécuté après
le téléchargement et la vérification indépendants des SHA. Aucun runtime
existant n'a été modifié.

La valeur à fournir à la recette pour `pdf_python` est
`work/part-workflow/runtimes/pdf-base-001/bin/python`. Ce dossier contient le
venv ; son `runtime.json` est un reçu local d'installation, pas un installateur.
Le binaire Python n'est pas inclus dans ce lock de paquets.

[results.json](results.json) conserve la vérification effectuée : `pip check`,
les deux tests du guide et un vrai petit PDF **synthétique** avec image PNG.
Les tests du guide simulent volontairement l'export PDF ; le témoin séparé
exerce réellement ReportLab et Pillow. Il ne s'agit ni du dossier du carrier,
ni d'une admission de ses supports ou de sa fabrication.

Le renderer existant utilise Arial système lorsqu'il est présent et Helvetica
sinon. Les empreintes des polices effectivement disponibles figurent dans le
reçu local. Le lock ne distribue pas les polices système et ne garantit pas un
PDF identique à l'octet entre machines ou dates d'export. Aucun script de guide
gelé n'a été modifié.
