# Enveloppe 3D de référence 993

Ce répertoire contient le premier objet 3D du jumeau : une cage d'encombrement
et de repères paramétrique pour le profil USA de la 993. Elle est construite à
partir de sept dimensions déclarées dans le manuel Porsche, et non à partir d'un
scan ou d'une pièce.

La cage ne représente pas la carrosserie. Elle ne contient ni courbure, ni
porte-à-faux sourcé, ni roue, ni interface, ni volume intérieur. Les essieux
sont centrés dans la longueur uniquement pour visualiser l'empattement ; cette
position est une hypothèse graphique et non une cote Porsche.

## Source et génération

Le modèle éditable est
[`source/reference_envelope.scad`](source/reference_envelope.scad). Le manifeste
et la correspondance vers les pages du manuel sont dans
[`reference-envelope.json`](reference-envelope.json).

Régénérer les deux fichiers depuis le registre de mesures :

```bash
python3 scripts/generate_twin_envelope.py
```

Si OpenSCAD est installé, produire un maillage de visualisation :

```bash
mkdir -p twin/993/derived
openscad -o twin/993/derived/reference_envelope.stl \
  twin/993/source/reference_envelope.scad
```

Le STL est un dérivé visuel. Il ne constitue ni une géométrie de carrosserie ni
une preuve d'ajustement. Le manifeste conserve donc `accuracy_mm: null` et
`fitment_claim: false`.

## Suite logique

1. Ajouter le profil ROW après l'enregistrement machine de ses valeurs et de
   leur page de référence.
2. Acquérir sous licence une géométrie de caisse ou organiser une campagne de
   scan avec échelle, repères, incertitude et droits de réutilisation.
3. Remplacer progressivement la cage par des surfaces et sous-ensembles
   identifiés, en reliant chaque interface à une mesure ou une source.
4. Rattacher les trois pilotes intérieurs à des mesures physiques avant de les
   intégrer comme géométries ajustées.
