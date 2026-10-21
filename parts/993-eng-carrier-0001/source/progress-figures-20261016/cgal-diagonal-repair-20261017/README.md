# Deux exemples réels de retriangulation CGAL

Planche pédagogique pour expliquer à un mécanicien le changement de diagonale
des quads GRID3341/3475 et SKIN8753/8754. Les IDs et les deux triangles après
CGAL proviennent des lignes natives effectivement retournées, dans leur ordre
et leur orientation. N1/N2 désignent ces lignes, pas de nouveaux IDs de faces
carrier. Les faces avant proviennent du plan d'opérations immuable.

**Les dessins sont des schémas topologiques hors échelle.** Le même contour et
les mêmes positions dessinées sont réutilisés avant/après. Ces positions de
présentation ne représentent pas les XYZ réels. La preuve native conserve les
quatre coordonnées d'origine exactement. La diagonale interne seule change.
SKIN est exactement non coplanaire : l'identité exacte des surfaces 3D avant et
après n'est pas revendiquée. Aucune borne quantitative n'est ajoutée à la planche.

`data.json` contient seulement les deux exemples, le résumé réel 146/146 et les
quatre références d'origine avec SHA-256 : plan050b, quads080, reçu natif5d012 et
liaison orientée26e2. Ces petits extraits sont inclus pour un rendu autonome.
Les originaux restent intacts. Le helper de normalisation orientée est copié à
l'octet depuis la liaison gelée. Aucun maillage n'est publié ou modifié.

## Reproduction

Runtime existant : Python3.10.11, Matplotlib3.10.8, NumPy2.2.6, Pillow11.3.0.
Depuis n'importe quel répertoire courant :

```sh
python3 -B /absolute/path/carrier-cgal-repair-gallery-preparation-001/render.py /absolute/path/FRESH_OUTPUT
```

Le renderer vérifie données, sources et runtime, limite sa durée à60s et les
bibliothèques numériques à un thread, sans processus de travail. Il produit
PNG/SVG/PDF et un reçu contenant chaque triangle/diagonale réellement dessinés.
Les métadonnées temporelles SVG/PDF sont retirées pour permettre le rejeu exact.

Le résultat illustre146 quads traités par CGAL ; aucune admission globale n'est
revendiquée. Cette planche ne lance aucun calcul CGAL ni certifieur.
