# Admission 6 mm et chambre candidate à deux pans

Ce lot apporte une **vraie modification CAO privée**, pas encore un domaine de
banc de débit ou une culasse validée. Le maître quatre logements `92640fd2…`
reste intact. Les scripts et le [reçu agrégé](../../evidence/intake-chamber-candidate-20260908.json) sont
publicables ; les B-Rep, STEP, coupes et coordonnées du scan restent privés.

## Résultat natif du 8 septembre 2026

`inspect_pilot.py` a relu les pièces exactes : les soupapes réellement importées
du module V2 sont ouvertes de 6 mm le long de leurs axes inclinés, puis le
recalage du module est appliqué une seule fois. Les sièges et guides restent
fixes. Les deux colliers de contrôle gorge/conduit (rayon 17,8 ; longueur 0,01)
sont entièrement recouverts à la précision d'intégration rapportée. Ce contrôle
local ne prouve pas l'étanchéité d'un assemblage.

Le négatif d'admission brut inclut encore environ 735,415 unités³ de chacune
des soupapes ouvertes et 797,705 unités³ de chacun des guides : ces solides
doivent être soustraits du futur domaine gaz. Les six composants d'admission
contrôlés ont une intersection volumique nulle avec le maître quatre logements.
Le fond original est plan et son centre plein : aucune chambre M64 n'y était
définie. La part de surface plane observée sous le disque de contrôle ne constitue
**pas** un taux d'étanchéité.

`build_candidate_chamber.py` construit un outil de coupe à deux pans, chacun
passant par la lèvre inférieure réelle des sièges correspondants (position
axiale locale 0,5). Leur inclinaison vient des axes existants ; leur intersection
détermine la profondeur, sans introduire un volume cible arbitraire. La partie
positive entre ce toit et le fond est bornée au cylindre de travail Ø100,
**hypothèse de conception non certifiée**. L'axe de bougie central est réservé
dans le contrat du prototype, mais aucun logement, filetage ou isolant fictif
n'a été ajouté. L'arête de toit n'est pas raccordée et la bougie n'est pas choisie.

| Grandeur distincte | Résultat en unités du scan³ |
|---|---:|
| Volume de l'outil de découpe à deux pans | 27 001,825308 |
| Matière effectivement retirée du maître (`common`) | 9 578,631048 |
| Volume gaz de la chambre assemblée, soupapes fermées | Non calculé |

Ces volumes ne donnent **aucun rapport volumétrique** : ni piston, ni hauteur
de deck, ni jeu au PMH ne sont définis. L'échelle reste une hypothèse de 1 unité
du scan pour 1 mm, non une mesure certifiée.

## Contrôles réellement exécutés

- Outil de chambre : un solide connecté, B-Rep valide et analyse BOP exécutée
  sans faute, erreur ou avertissement.
- Corps modifié : un solide ; B-Rep valide avant export et après relecture STEP.
  **L'analyse BOP complète du corps n'a pas été exécutée.** La validité B-Rep
  ne doit pas être rebaptisée BOP réussi.
- Les huit inserts réels (quatre sièges et quatre guides) ont chacun une
  intersection volumique nulle avec l'outil : aucune amputation géométrique.
- Volume de l'outil hors cylindre Ø100 : zéro. Surface du fond initial située
  hors de ce cylindre perdue : zéro. Cela conserve la surface géométrique testée,
  sans identifier ni qualifier une portée de joint Porsche.
- Écart maximal de boîte englobante : `2,22e-14` unité ; défaut de partition
  volumique : `−1,60e-6` unité³ pour un seuil déclaré `1e-3`.

L'export STEP du **seul volume de matière retirée** présente une différence
de volume de `+0,011580338` unité³ à la relecture (environ `1,209e-6` relatif).
Cet écart reste à expliquer ; il n'est pas masqué par un seuil choisi après coup.
Le corps candidat STEP présente pour sa part un écart de `−1,39e-7` unité³.
Les contrôles de validité et de nombre de solides des exports ne constituent
donc pas une qualification métrologique de leur volume.

Les grands diamètres extérieurs des sièges dépassent légèrement le disque
Ø100 en projection. Ce n'est pas automatiquement une collision : une partie
de l'insert peut être portée au-delà de l'alésage. Il faudra néanmoins vérifier
le support, la portée cylindre/culasse et la liaison thermique correspondante,
sans assimiler le disque de travail à une zone mécanique libre.

## Exécution et coupes

L'image CPU amd64 existante, OCCT/OCP 7.9.3.1, a été utilisée sans location,
installation ou simulation. Chaque conteneur est limité à deux CPU, 4 Gio,
128 processus et 300 secondes, sans réseau. Les sorties processus ont été
observées séparément des JSON géométriques ; les conteneurs ont été supprimés
et leur absence vérifiée.

| Étape | Durée du programme | Sortie SSH/Docker observée |
|---|---:|---:|
| Inspection des sources | 11,29 s | 0 |
| Extraction des coupes originales | 9,63 s | 0 |
| Prototype deux pans et contrôles | 14,78 s | 0 |
| Extraction des coupes du prototype | 12,30 s | 0 |
| Tessellation native des 13 solides pour la vue 3D | 4,04 s | 0 |

`render_sections.py` extrait par OCCT les intersections des **solides natifs**,
puis produit les images de coupe. Le bleu pointillé est explicitement le
négatif d'admission brut superposé : les conduits ne sont pas découpés dans ce
prototype de corps. La coupe centrale rend visible le nouvel évidement sous
les sièges. Les deux images et leurs sources privées sont identifiées par SHA
dans le reçu. Elles ne contiennent aucun champ CFD ou thermique inventé.

`render_underside.py` ajoute une vue par-dessous et une coupe centrale en encart.
Le rendu final privé utilise le vrai tampon de profondeur de VTK/PyVista,
sans lissage de géométrie, avec les 113 910 triangles du corps et les douze
composants du module. Les brouillons Matplotlib 3D sont supplantés : leur tri
approché des profondeurs masquait incorrectement des soupapes. Le gris final
est illustratif, pas une sélection d'alliage. Aucun PNG privé n'est ajouté au
dépôt automatiquement.

Tests ciblés :

```sh
python3 -m unittest discover -s tests -p test_m64_flowbench_intake_inspection.py -v
python3 -m unittest discover -s tests -p test_m64_flowbench_candidate_roof.py -v
```

Les six tests passent. Les trois tests de toit vérifient l'incidence des plans
sur les lèvres, la continuité de leur arête et le rejet d'une inclinaison nulle ;
ils ne sont pas des essais moteur.

La suite doit encore assembler les intérieurs des sièges, retirer les soupapes
et guides du gaz, fermer explicitement les sorties parasites et les
échappements, puis construire le récepteur de banc et les groupes de frontières.
Le `ported-candidate06` rejeté BOP n'a pas été utilisé comme corps de cette
étape. Aucun domaine complet, débit, coefficient de décharge ou résultat 700 PS
n'est revendiqué.
