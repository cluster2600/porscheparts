# F51 — conversion privée B-Rep natif vers OpenUSD

## Résultat

F51 fournit une voie privée et reproductible pour visualiser les deux maîtres
OCCT F50 sans repasser par STEP :

`B-Rep OCCT natif → tessellation de surface Gmsh/OCCT → USD Crate`

La géométrie privée n'est pas versionnée. Les seuls artefacts publics sont les
scripts, les tests et la preuve expurgée
`twins/reference-917-engine/evidence/f51-native-usd-validation/native-brep-usd-f51.json`.

| Porte | 2V | 4V |
|---|---:|---:|
| Maître B-Rep F50 hashé et accepté | PASS | PASS |
| Peau triangulée fermée / manifold | PASS | PASS |
| Composant / mesh USD | 1 / 1 | 1 / 1 |
| Triangles | 220 560 | 253 078 |
| Écart bbox USD ↔ F43, unités scan | 1,973e-6 | 1,973e-6 |
| `metersPerUnit` / axe | 0,001 / Z | 0,001 / Z |
| Xform / proxy / ovale | 0 / non / non | 0 / non / non |
| `validate-usd-minimum` | PASS | PASS |
| NVIDIA Asset Validator générique | PASS | PASS |
| Diagnostics Geometry / Physics | PASS / PASS | PASS / PASS |
| Profil `Prop-Robotics-Neutral@2.1.0` | BLOCKED | BLOCKED |
| Rendu OVRTX | BLOCKED | BLOCKED |

Le B-Rep F50 a une bbox identique à l'autorité F43. La différence publiée entre
USD et F43 est donc calculée directement entre la bbox relue dans l'USD et la
bbox exacte du B-Rep. Elle est due à la quantification `float32` obligatoire des
points OpenUSD, sans transformation ni déplacement volontaire.

## Particularité 4V

La tessellation brute 4V contenait 23 arêtes dont les deux triangles voisins
avaient le même sens. La normalisation a inversé l'ordre des indices de 43
triangles reliés afin d'obtenir une surface orientable et fermée. Aucun point
n'a été ajouté, supprimé ou déplacé. Après cette opération purement
topologique : zéro arête libre, zéro arête non-manifold, zéro conflit de sens et
un seul composant.

## Workflow NVIDIA appliqué

La demande est classée `validation_only` et
`property_assignment_intent=skip`. Le preflight officiel a été exécuté avec
Content Agents explicitement désactivé. OpenUSD et Asset Validator sont prêts,
et le checkout SimReady Foundation utilisé est identifié par son commit dans la
preuve.

Les étapes sont exécutées dans cet ordre :

1. contrôle SHA-256 et audit BRepCheck exact du maître F50;
2. tessellation de la peau, sans heal, sewing, booléen ou changement d'échelle;
3. écriture USD avec coordonnées numériques inchangées, `metersPerUnit=0.001`,
   axe Z et aucun `XformOp`;
4. réouverture USD, audit des normales, de la topologie et de la bbox;
5. `validate-usd-minimum`, Asset Validator générique, Geometry et Physics;
6. tentative du profil formel SimReady, en mode fail-closed.

Le profil formel est **bloqué et à relancer** : le wrapper de référence cherche
`profiles/profiles.toml`, tandis que le checkout fourni distribue les profils
dans plusieurs fichiers TOML; le runtime a retourné zéro profil disponible.
Même après normalisation privée de l'empaquetage sans modifier les définitions,
aucun profil n'a été chargé. Ce n'est donc pas un résultat de conformité et
aucune propriété matériau, collider ou rigid-body n'a été inventée.

## Reproduction privée

Les scripts publiés attendent explicitement les maîtres et rapports privés :

- `tessellate_native_brep_for_usd_f51.py` contrôle le maître F50 et produit une
  archive de surface privée;
- `author_native_surface_usd_f51.py` écrit puis relit l'USD privé;
- `consolidate_native_usd_validation_f51.py` refuse toute chaîne incohérente et
  n'émet que le manifeste expurgé.

Les validateurs NVIDIA doivent être exécutés dans le runtime enregistré par le
preflight. Les fichiers privés restent adressés par leurs SHA-256 publiés.

## Limites et décision

La voie USD géométrique est acceptée pour les diagnostics et une future
visualisation OVRTX. Elle n'est pas une validation SimReady complète, une
simulation physique, une validation thermique, une validation d'impression ou
une autorisation de fabrication. Le maillage volumique strict F50, l'échelle
absolue et les interfaces Porsche 917 restent rouges. Aucun rendu de
substitution n'est publié, car aucun runtime OVRTX approuvé n'était disponible
et l'utilisation de Vast était interdite pour cette piste.
