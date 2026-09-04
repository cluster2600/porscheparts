# F38 — paquet analytique de distribution et porte-axes

Ce paquet contient uniquement des géométries OCCT analytiques séparées. Il ne
contient ni scan, ni peau de culasse issue du scan, ni faux assemblage monobloc.
L'échelle et les positions sont conditionnelles aux hypothèses F36/F37 et ne
constituent pas une preuve d'ajustement sur un moteur Porsche 917.

## Contenu

Les dix fichiers STEP du dossier `cad/` restent volontairement séparés :

| Groupe STEP | Corps | Fonction |
|---|---:|---|
| `rocker-carrier-f38-rounded-reinforced.step` | 1 | porte-axes conditionnel |
| `two-rocker-shafts-f38.step` | 2 | axes de culbuteurs |
| `four-rockers-f38.step` | 4 | culbuteurs individuels |
| `two-intake-valves-f38.step` | 2 | soupapes d'admission |
| `two-exhaust-valves-f38.step` | 2 | soupapes d'échappement |
| `four-valve-guides-f38.step` | 4 | guides de soupape |
| `four-valve-seats-f38.step` | 4 | sièges de soupape |
| `eight-valve-springs-f38.step` | 8 | deux ressorts concentriques par soupape |
| `four-lower-spring-cups-f38.step` | 4 | coupelles inférieures |
| `four-upper-spring-retainers-f38.step` | 4 | coupelles supérieures |

Le total est de 35 corps analytiques : **4 soupapes, 4 guides, 4 sièges,
8 ressorts, 2 axes, 4 culbuteurs**, un porte-axes et huit coupelles. Chaque STEP
publié a été réimporté indépendamment; le nombre de solides, la validité OCCT,
la fermeture et l'empreinte SHA-256 sont consignés dans
`f38-valvetrain-package-report.json`.

`917-f38-valvetrain-package.png` montre l'assemblage multi-corps et une demi-coupe
sans aucune géométrie de scan. Il s'agit d'une visualisation d'enveloppes, pas
d'une analyse cinématique ou de contact.

## Ce qui n'est pas prouvé

- interfaces et ajustement réel avec la culasse Porsche 917;
- profil de came, ratio réel, jeux, alignement et collision sur un cycle complet;
- contacts non linéaires aux axes, patins, queues, sièges et coupelles;
- raideur, précharge, coil-bind, surge et durée de vie des ressorts;
- lubrification des axes et des contacts;
- fatigue mécanique et thermomécanique;
- propriétés matière à chaud et traitements;
- résistance du porte-axes F38.

Un écran CalculiX F38 linéaire C3D4 a abouti sur trois maillages de 2,0, 1,5 et
1,25 mm. Au maillage fin, il donne 137,03 MPa au maximum brut, 31,63 MPa au
percentile 99 % et 0,0602 mm de déplacement. Le percentile 99 % converge sous
10 %, mais le maximum brut varie encore de 16,54 %. Les directions réelles,
contacts, matière et cycles ne sont pas validés : cet écran n'est pas une preuve
structurelle de libération. Les gros résultats restent locaux et le rapport est
référencé par empreinte. Le calcul linéaire F37 ne peut pas être transféré comme
preuve au dessin F38. Le STEP composé
`f38-four-valve-rocker-assembly.step` produit dans `work/` n'est volontairement
pas publié : il n'est pas monobloc et n'a pas été réimporté dans la passe bornée.

## Reproduction et contrôle

Le rendu analytique se reproduit depuis les STL de travail :

```bash
python3 twins/reference-917-engine/source/render_f38_valvetrain_package.py \
  --cad work/917-rocker-carrier-f38/cad \
  --output work/917-rocker-carrier-f38/917-f38-valvetrain-package.png
```

La publication contrôlée nécessite `build123d`/OCCT et refuse toute divergence
d'empreinte ou de nombre de solides :

```bash
python3 twins/reference-917-engine/source/publish_f38_valvetrain_package.py \
  --spec twins/reference-917-engine/f38-rocker-carrier-redesign.json \
  --source-report work/917-rocker-carrier-f38/cad/f38-rocker-carrier-cad-report.json \
  --cad work/917-rocker-carrier-f38/cad \
  --f38-calculix-report work/917-rocker-carrier-f38/calculix/f38-carrier-calculix-report.json \
  --image work/917-rocker-carrier-f38/917-f38-valvetrain-package.png \
  --output twins/reference-917-engine/evidence/f38-valvetrain-package
```

Le test autonome du paquet publié s'exécute avec :

```bash
make 917-f38-valvetrain-package-evidence-check
```

## Verdict

La géométrie d'échange est disponible et ses corps sont réimportables. Toutes
les portes d'interface, cinématique, contact, ressort, fatigue, matière,
fabrication et démarrage moteur restent fermées.
