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

Le générateur `scripts/generate_993_reference_frame_usd.py` transpose les sept
dimensions dans un repère OpenUSD en mètres :
`twins/vehicle-993/usd/993-reference-frame-f1.usda`. La cage, les deux voies,
l'empattement, la garde au sol et l'axe médian y restent des références. La
position longitudinale des essieux est centrée seulement pour l'affichage, car
les porte-à-faux ne sont pas sourcés. Le contrat
`twins/vehicle-993/reference-frame-openusd-f1.json` conserve donc zéro pièce
positionnée et zéro surface de carrosserie. Il ajoute aussi quatre contraintes
massiques documentées — masse à vide, masse totale et charges maximales par
essieu — sans les convertir en distribution de masse ni en `UsdPhysics.MassAPI`.

```bash
make vehicle-993-reference-frame
make vehicle-993-reference-frame-check
make vehicle-993-reference-frame-index-check
```

La préflight NVIDIA CAD-to-SimReady reste bloquée sur les services et
validateurs indisponibles. L'actif OpenUSD n'a donc reçu ni matériau, ni
physique, ni conformité SimReady.

## Suite logique

1. Ajouter le profil ROW après l'enregistrement machine de ses valeurs et de
   leur page de référence.
2. Acquérir sous licence une géométrie de caisse ou organiser une campagne de
   scan avec échelle, repères, incertitude et droits de réutilisation.
3. Remplacer progressivement la cage par des surfaces et sous-ensembles
   identifiés, en reliant chaque interface à une mesure ou une source.
4. Rattacher les trois pilotes intérieurs à des mesures physiques avant de les
   intégrer comme géométries ajustées.
