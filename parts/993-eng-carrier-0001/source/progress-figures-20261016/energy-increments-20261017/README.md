# Bilans numériques du carrier : 16 et 32 états

Planche scientifique française fondée exclusivement sur les deux audits ENER et
Piola réellement exécutés et leur comparaison `31a9b7a7c78c…`.
Les huit petits JSON sources sont copiés à l'octet dans `data/` et liés à leurs
originaux par `inputs.json`. Les originaux restent intacts.

La planche montre les 16 et 32 états complets de chaque bilan, sans décimation
ni ajout d'un état initial. Les traits servent à guider la lecture. Les axes
verticaux logarithmiques sont explicitement indiqués. Les seuils ENER `1e-3`
et Piola `1e-4` restent ceux des audits. La hausse du maximum Piola est visible.
Le résidu à charge nulle porte les deux valeurs mesurées et leur différence ;
aucun seuil d'acceptation du résidu n'est défini.

Ce raffinement des incréments ne démontre pas la convergence du maillage.

## Attribution des données matière

Qixiang Luo, Lu Yin, Timothy W. Simpson et Allison M. Beese.
Données publiées sous licence CC-BY-4.0 :
[Zenodo, record 6587905](https://zenodo.org/records/6587905) et
[Data in Brief, 108911](https://doi.org/10.1016/j.dib.2023.108911).
La copie `data/material-DATA_LICENSE.json` documente cette provenance ; elle
est manifestée séparément et ne change aucune des huit données de comparaison.

## Reproduction

Runtime existant, sans installation : Python 3.10.11, Matplotlib 3.10.8,
NumPy 2.2.6, Pillow 11.3.0 et police DejaVu Sans fournie par Matplotlib.
Le renderer fonctionne depuis un autre répertoire courant :

```sh
python3 -B /absolute/path/carrier-energy-gallery-preparation-001/selfcheck.py
python3 -B /absolute/path/carrier-energy-gallery-preparation-001/render.py /absolute/path/FRESH_OUTPUT
```

`render.py` limite son temps mural à 60 s, fixe les bibliothèques numériques à
un thread et ne crée aucun processus de travail. Il vérifie les empreintes des
données copiées et de ses sources, les versions et les fichiers chargés du
runtime avant/après le rendu. Il écrit PNG, SVG, PDF et un reçu avec tous les
points représentés et leurs empreintes. Aucun solveur ni audit n'est relancé.
Les métadonnées temporelles SVG/PDF sont supprimées pour la reproductibilité.

Les chemins d'origine dans le manifeste servent à la traçabilité ; ils ne sont
pas nécessaires pour refaire la figure depuis les petites données copiées.
