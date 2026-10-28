# Planche 22 — forme réelle du congé R1 natif

Cette planche montre la coupe YZ des deux CAO à **X = 81,6750002098722 mm**, abscisse du pic EF initial 85535/IP1. Le STEP de référence et le prototype BREP C1-002 sont conservés dans les mêmes coordonnées ; les deux panneaux ont les mêmes axes et le même cadrage. Le contour avant reste visible en pointillé sur le panneau après. L’encart situe le zoom dans la coupe complète.

**Prototype CAO, échange STEP en contrôle.** Le reçu natif C1-002 reste explicitement **refusé** pour le contrôle de retrait de matière après relecture STEP. Cette figure utilise directement le BREP natif candidat. Le reçu constate séparément un booléen natif ancien−nouveau vide et un ajout natif de 35,534438081499616 mm³. Ces constats ne sont pas transformés en admission du STEP, de fabrication ou de résistance.

## Le R1 est construit, pas redessiné

Le rayon 1 mm appartient à la construction du congé 3D native. Le renderer ne dessine pas un arc de cercle de rayon 1 à sa place : `BRepAlgoAPI_Section` extrait les arêtes réelles de chaque CAO dans le même plan avec `Approximation(False)`, puis `GCPnts_QuasiUniformDeflection` échantillonne ces courbes pour le dessin à 0,001 mm. La coupe d’un congé 3D n’est pas présentée comme un cercle R1 dans ce plan.

Les données complètes contiennent les **24/25 arêtes** et **699/1 700 points XYZ** réellement évalués avant/après, leurs types de courbes et le SHA des bits binary64. Aucun point n’est déplacé vers le plan ni lissé. L’écart X maximal observé, 2,842170943040401×10⁻¹⁴ mm, a été contrôlé contre la tolérance native des arêtes. Le zoom ne modifie que les limites d’affichage ; toutes les arêtes de la coupe sont conservées.

## Portée portable et parents

Le rejeu autonome de cette capsule porte **uniquement sur le dessin des points déjà extraits**. Il n’importe pas OCP, ne recalcule pas de coupe CAO et ne reconstruit aucun congé. Il nécessite Python/Matplotlib et la police du runtime de rendu attesté ; les gros runtimes ne sont pas copiés.

Les deux CAO parentes ne sont pas incluses. Elles restent liées par empreinte dans les données, les plans et les reçus :

- STEP de référence `work/part-workflow/run-001/cad/carrier.step` : `de0e55a3150dacc5428bbc301d18d2e43477f038c3f4df295d9373af8e906b63` ;
- BREP natif C1-002 `candidate-native.brep` : `a42e6942722957076410d4a89b24f9bd0f11677dfa8319103d6733a0db8a1cf9` ;
- reçu natif entier copié dans `evidence/native-prototype-assessment.json` : `403d77960c019c367bec96adee0078f519fda98623b2468e2c5d33fee3219b25`.

Les plans d’extraction sont historiques et requièrent le checkout/runtimes/parents d’origine. La capsule n’affirme pas que leur commande d’extraction est autonome. `source-provenance.json` lie chaque copie identique à l’octet à son original ; `history/work-README.md` conserve la note de travail initiale. Le reçu `publication.json` garde son état antérieur au rejeu de la copie finale. La preuve de publication et de rejeu est un [reçu séparé adjacent](../native-fillet-root-publication-20261017.json), ajouté après le véritable retour du rendu.

## Vérifier et rejouer les points

Depuis `/`, sans lire les CAO parentes :

```sh
python3 -B /CHEMIN/CAPSULE/verify.py
python3 -B /CHEMIN/CAPSULE/selfcheck.py
/Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10 -B \
  /CHEMIN/CAPSULE/figure.py render \
  /CHEMIN/CAPSULE/data-001/section-data.json \
  388ca637aa7df954717baa6ac34f3553a7bfbad91184af83534b58a9fede5c9c \
  /NOUVEAU/CHEMIN/render-fresh
```

La sortie doit être inexistante, sans lien symbolique. Les trois exports historiques sont :

| Format | SHA-256 |
|---|---|
| PNG | `dc411915be9b194cf1a5f90a24b931a83d34c49d1dce4dcf45bb79b2db9bcf89` |
| SVG | `9dacc78758b2b0ad07a90771a413ddaa695761f1e912c8146f3fecbdd91e1487` |
| PDF | `a4a933a2b87e7422eefb809e29cc89dd7a6a785a022a1fd3a71f68ed569ae771` |

Le PNG et la page 1 du PDF de travail ont réellement été vus par root avant son GO de copie. Aucun export CAO, calcul mécanique, changement de géométrie ou validation globale n’est exécuté par ce rejeu.
