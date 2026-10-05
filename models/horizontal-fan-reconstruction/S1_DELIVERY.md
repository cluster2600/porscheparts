# Vue CAO réelle : assemblage S1 et brut V2

[Accueil de l'étude](README.md) · [Dimensions et dossier S1](ASSEMBLY_MANUFACTURING_S1.md) · [STEP assemblage](results/assembly/S1/S1-assembly.step) · [STEP brut V2](results/lpbf/V2-stock-scenario/V2-stock-scenario.step)

![Assemblage S1 réel et scénario de brut V2, dimensions supposées](results/assembly/fan-S1-assembly-and-V2-stock-study.png)

La vue de gauche montre les dix-neuf solides de l'assemblage CAO publié, avec
le plénum, les poulies, la trajectoire de courroie, l'extension d'arbre et les
stocks des supports. Les coordonnées des STL issus des solides STEP sont
conservées. Les transparences du carter et du plénum servent à voir le rotor et
le renvoi. Les couleurs identifient les composants ; elles ne représentent pas
des champs calculés de contrainte, de pression ou de température.

La vue de droite montre séparément le brut V2, avec stock supposé de 0,5 mm
radial sur l'alésage et axial sur la face du moyeu. Ce brut n'est pas installé
dans l'assemblage de gauche. Les axes sont en millimètres. Le diamètre 275 mm,
les neuf pales et les dimensions du plénum et de l'entraînement sont des
hypothèses d'étude. Aucun relevé indépendant ne confirme l'échelle, l'identité
935/993 ou les interfaces de montage. La fiche de mesure comporte 52
caractéristiques physiques encore vides, et le gate complet conserve 55 besoins
non satisfaits, dont l'identification catalogue et les validations de fabrication
et d'ingénierie.

Le [reçu du rendu](results/assembly/fan-S1-assembly-and-V2-stock-study.json)
relie l'image aux vingt STL sources — dix-neuf solides S1 et le brut V2 —,
aux rapports de géométrie, au script et à ses dépendances par SHA256. Le
[rendu reproductible](source/render_s1_delivery.py) projette ces tessellations
réelles avec matplotlib ; aucune géométrie ni résultat de calcul n'est inventé.
Les contrôles BRep et STEP, les hypothèses dimensionnelles, les six orientations
LPBF et leurs limites figurent dans le [dossier S1](ASSEMBLY_MANUFACTURING_S1.md).

Cette vue facilite la revue d'encombrement. Elle ne constitue ni une preuve de
montage, ni un dessin fonctionnel libéré, ni une simulation process qualifiée.
L'[asset OpenUSD S1](omniverse/S1-layout.usda) conserve son rôle de scène liée
aux preuves, sans validation du jumeau numérique ou qualification NVIDIA SimReady.
Les champs CFD locaux restent ceux de leurs géométries et conditions originales ;
ils ne sont pas attribués à ce nouvel assemblage d'enveloppes.
