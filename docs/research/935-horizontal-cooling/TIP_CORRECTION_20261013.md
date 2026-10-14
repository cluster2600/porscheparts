# 935 — correction de la pointe de la pale 03

La pointe auparavant prolongée à profil constant utilise maintenant ses
propres contours acquis. Les arcs observés des sections incomplètes sont
conservés ; seules leurs lacunes sont fermées par des cordes locales.
**L'écart RMS scan → candidat passe de 1,174 à 0,181 unité source** sur la
zone contrôlée. Cette correction concerne une pale, pas l'ensemble des
interfaces historiques ni les huit autres pointes.

Le [reçu numérique](tip-correction-20261013.json) contient les empreintes,
contrôles et résultats. Géométries, coupes, cartes d'écarts, images, cas,
champs et essais rejetés restent dans l'[archive privée](https://github.com/cluster2600/porscheparts-935-private/releases/tag/tip-correction-20261013).
Le calcul tourne sur le Mac : PicoGK natif `osx-arm64`, Gmsh dans Docker
local en émulation amd64, CalculiX natif Linux aarch64 dans Docker local.
Aucune location Vast et aucune géométrie 993/917 ne sont utilisées.

## Pourquoi corriger cette zone

Le maximum de déplacement des trois calculs précédents se trouvait près
de la pointe extrapolée, au-delà du dernier profil acquis à la station 122.
L'association à la pale 03 était angulaire, sans segmentation exacte du
champ mécanique. Ce signal justifie une inspection du scan ; il ne justifie
pas d'épaissir une pale pour faire baisser artificiellement le déplacement.

La segmentation utilise les composantes connexes du scan au-delà du rayon
94 unités source. Neuf composantes significatives sont identifiées. Leurs
phases sont comparées à celles des profils existants ; seule la composante
correspondant à la pale 03 fournit les nouvelles coupes.

Deux contours fermés sont retrouvés aux stations 134 et 136. Le sommet
observé projeté sur l'axe radial atteint 136,410. Une coupe fermée à
136,160 laisse une garde de 0,25 unité source. **Sa fermeture terminale
reste artificielle**, et cette garde n'est pas une tolérance d'usinage.
Les noms des fichiers ne fixent pas les unités ; tous les résultats en mm
supposent encore 1 mm par unité source.

## Réparation limitée et essai rejeté

Un premier essai interpolait les contours 122 et 134 aux stations
124…132. Sa médiane était meilleure, mais son RMS scan → candidat montait
à 1,978 unité et son maximum à 9,009 : cette interpolation coupait une
zone encore observée. Le candidat, ses sources et ses trois calculs sont
conservés comme essai rejeté ; ils ne sont pas la correction retenue.

La correction retenue conserve tous les points d'extrémité des segments
acquis des cinq coupes ouvertes : 124, 126, 128, 130 et 132. Les sept liens
manquants mesurent 0,171 à 8,709 unités source et restent bornés par une
limite explicite de 9. Des points supplémentaires sur chaque corde évitent
qu'une spline libre courbe la lacune. Le lissage conserve le paramètre
antérieur de 0,025 et les 128 points par profil. Les coupes fermées ne
reçoivent aucun lien ajouté. Les profils sont enregistrés cycliquement
entre stations de cette même pale.

La provenance distingue les contours fermés acquis, les arcs acquis avec
cordes de réparation et la fermeture terminale artificielle. Une corde
n'est pas une surface mesurée. L'interpolation entre sections reste une
reconstruction ; le scan d'origine n'est jamais modifié.

Les huit autres pales et tous les profils antérieurs de la pale 03 jusqu'à
122 sont conservés exactement. Un audit indépendant des STL à 0,6 compare
les triangles dont les trois sommets se projettent avant la station 120 :
**1 294 915 triangles ont exactement les mêmes coordonnées et orientations**.
Cette garde locale ne constitue pas un audit global d'auto-intersections.

## Géométrie et écarts

PicoGK construit les profils, le rotor et les champs aux résolutions
supposées 1,2, 0,6 et 0,3 mm. Les trois STL ont une composante, sont fermés,
orientés de façon cohérente et ne contiennent aucune face d'aire nulle.
Entre les deux derniers : volume +0,0724 %, variation maximale des inerties
principales 0,1185 %. Le seuil numérique de 1 % est satisfait pour ces
grandeurs ; il ne qualifie pas l'échelle ni les dimensions historiques.

La comparaison utilise 6 000 points indépendants, tirés selon l'aire des
triangles, et la distance aux triangles du candidat. La zone observée est
la composante de la pale 03 dont tous les sommets se projettent au-delà de
124. Les mêmes points et graines sont utilisés avant/après.

| Direction et indicateur, en unités source | Ancienne pointe | Correction |
|---|---:|---:|
| Scan → candidat, RMS | 1,1745 | 0,1814 |
| Scan → candidat, médiane | 0,5117 | 0,0284 |
| Scan → candidat, P95 | 2,8048 | 0,3696 |
| Scan → candidat, maximum échantillonné | 5,3398 | 2,1017 |
| Candidat → scan ouvert, RMS | 3,0160 | 0,3385 |
| Candidat → scan ouvert, P95 | 6,4371 | 0,4417 |
| Candidat → scan ouvert, maximum échantillonné | 8,1796 | 3,6653 |

La seconde direction inclut les lacunes du scan : elle ne mesure pas
l'exactitude d'une surface absente. Les extrema restent dans les fichiers
privés ; aucune tolérance générale n'est déduite du seul RMS. Les vues du
rotor et de sa pointe ainsi que six sections ont été inspectées visuellement.

## Comparaison mécanique

Trois calculs AlSi10Mg à 6 000 tr/min reprennent exactement la loi matière,
l'encastrement supposé de l'alésage et le chargement centrifuge précédents.
L'échelle, le procédé et les appuis réels restent non qualifiés. Chaque
audit couvre tous les nœuds, les huit points d'intégration de chaque C3D8
et les réactions des nœuds fixés. Les bilans de forces et de moments passent.

| Pas supposé, mm | Éléments corrigés | Déplacement ancien, mm | Déplacement corrigé, mm | Réduction | Von Mises max. corrigé, MPa |
|---|---:|---:|---:|---:|---:|
| 1,50 | 131 084 | 0,8156 | 0,5249 | 35,6 % | 144,38 |
| 1,35 | 177 185 | 0,9410 | 0,6036 | 35,9 % | 188,37 |
| 1,20 | 244 240 | 1,1604 | 0,7598 | 34,5 % | 197,46 |

La réduction est cohérente à pas identique, mais le déplacement varie encore
de **25,9 % entre les deux maillages fins** : la convergence mécanique est
refusée. La contrainte maximale varie de 4,82 %, et le P95 des pics par
élément hors r = 25 mm de 2,81 %. Ces deux indicateurs ne compensent pas
l'échec du déplacement. Aucun régime admissible n'est déduit de ces valeurs.
Les résultats du maillage fin sont aussi exportés comme champs VDB PicoGK
discrets, avec leurs empreintes et un contrôle de relecture.

Sur le maillage fin, le maximum est désormais associé angulairement à la
pale 02, à la station 128,9, au sein de sa plage acquise. Cette association
n'est pas une segmentation exacte du champ ; elle ne justifie pas de
modifier ce profil mesuré pour faire passer le calcul.

## Reproduction

Le [programme de récupération](../../../twins/935-horizontal-cooling-system-f0/source/recover_tip_sections.py)
prend un cas privé et un dossier de sortie neuf :

```sh
python recover_tip_sections.py tip-local-repair-case.json work/new-tip-sections
dotnet SectionLoft.dll work/new-tip-sections/sections.json SHA256 1 0.6 work/new-lofts
dotnet Assembly935.dll final-rotor-case.json SHA256 work/new-rotor
dotnet CandidateRotor.dll work/new-rotor/rotor_candidate.stl SHA256 0.6 work/new-grid 1.5,1.35,1.2
python prepare_candidate_fea.py final-fea-case.json work/new-fea
bash run_candidate_fea.sh work/new-fea/rotor.inp SHA256 work/new-solve
python assess_mac_fea.py work/new-fea work/new-solve work/new-assessment
dotnet MacStudy935.dll fea-fields fields-case.json work/new-fields
```

Les SHA256 sont ceux des arguments immédiatement précédents ; les cas
fixent et vérifient aussi les empreintes des dépendances. Les sources C#,
outils de préparation et d'audit précédents restent inchangés. Les cas et
scripts exécutés sont archivés avec les entrées privées nécessaires. Pour
le parseur mécanique existant, `log.rotor` est une copie vérifiée de
`ccx.log`, pas une nouvelle exécution. Les tests ciblés couvrent la
conservation, la provenance et le rejet des profils invalides.

## Suite de la qualification

La correction ne fournit ni le serrage réel du moyeu, ni les interfaces
de l'arbre, ni les conditions thermiques et aérodynamiques de la 935.
Les huit autres pointes extrapolées doivent être inspectées avec la même
discipline. Le prochain lot peut ensuite remplacer l'encastrement supposé
de l'alésage par un appui documenté et reprendre la convergence mécanique.
Les anciennes valeurs CFD ne sont pas attribuées à cette nouvelle géométrie.
Fabrication, tenue en fatigue, régime admissible et fonctionnement physique
restent non validés.
