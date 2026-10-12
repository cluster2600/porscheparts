# Intégration des ailettes bioniques dans la culasse quatre soupapes

La demande du 12 octobre 2026 est réalisée comme **intégration géométrique
dans une copie de travail du corps existant**. Le corps candidat contient
six nervures ramifiées, trois sur chaque flanc. Les quatre soupapes, quatre
sièges et quatre guides du module conservé restent distincts et inchangés.
Le scan maître et le BRep de référence ne sont ni écrasés ni remplacés.

Le modèle de référence provient des travaux sur le scan 935 ; son adaptation
à une variante M64/993 et son échelle absolue ne sont pas certifiées. Les
coordonnées restent des unités de scan supposées millimétriques. Ce fichier
ne délivre aucune pièce fonctionnelle ou autorisation de fabrication.

**Livrable retenu : `native-004/head-bionic.brep`**, CAO native éditable,
accompagnée de `head-bionic.stl` et des vues `native-004-views/`.
Le BRep sauvegardé puis relu et son maillage passent les contrôles géométriques.
Le STEP est conservé comme export d'étude **non qualifié** : sa relecture
standard passe, mais le contrôle exact échoue sur 57 faces. Il ne remplace pas
le BRep retenu.

## Implantation dans le corps réel

[contract.json](contract.json) fixe indépendamment les deux zones périphériques
du prototype : `X ∈ [-61,-48]` ou `[48,61]`, `Y ∈ [-35,35]`,
`Z ∈ [12,48]`. Il ne s'agit pas d'un masque d'épaisseur ou de résistance
accepté par un ingénieur. Le matériau extérieur de ces zones est remodelé :
ce travail ne se limite pas à ajouter des nervures décoratives sur le corps.

Les racines sont posées à `|X| = 47,2` et aux hauteurs `Z = 16, 30, 44`.
Elles recouvrent géométriquement le corps conservé avant le découpage du masque.
Le profil vient du [candidat d'ailette](../bionic-fins/candidate.json) déjà testé :
racine épaisse, deux branches effilées, mêmes épaisseurs et déports des branches.
Sa portée radiale est **comprimée de 28 à 11,8 unités**, jusqu'à `|X| = 59`,
et sa profondeur passe de 60 à 70. Ce n'est donc pas la cellule thermique
d'origine posée sans modification dans la culasse.

[Program.cs](Program.cs) construit réellement les feuilles avec PicoGK et
ShapeKernel (`BaseBox`, `LocalFrame`, `LineModulation`), les fusionne, retire
le matériau du corps uniquement dans le masque et réunit le corps conservé
avec les nouvelles feuilles. L'échelle et le repère du corps restent ceux des
entrées privées, avec une phase de grille commune annulée à l'export.

Les essais de voxelisation du corps complet sont rejetés pour leurs petits
fragments parasites. [build_native.py](build_native.py) conserve ensuite le
corps en CAO OpenCASCADE, coupe uniquement les deux zones et y fusionne la
**contrepartie analytique du même profil PicoGK**. Le BRep de base ne passe
pas par une voxelisation. Cette contrepartie n'est pas un STEP exporté depuis
un maillage PicoGK. Son volume d'ailettes diffère de **0,0988 %** de celui du
calcul PicoGK fin, ce qui contrôle la représentation du profil, pas son
efficacité thermique.

Les soupapes, sièges et guides se trouvent hors du masque et de son halo de
contrôle. Les interfaces moteur, goujons, porte-arbres, brides, bougies et
tolérances réelles ne sont pas certifiées par cette séparation de maillages.
La chaleur doit passer du corps aux racines puis aux branches et à l'air ;
les efforts de combustion, serrage et distribution nécessitent une vérification
thermomécanique propre au corps ainsi remodelé.

## Livrables privés et inspection

Les calculs sont conservés sous `work/m64-bionic-integration-20261012/` dans
le worktree de cette tâche. Les dossiers `coarse-001/` et `fine-001/` contiennent :

| Fichier | Interprétation |
| --- | --- |
| `head-bionic.stl` | Corps de culasse candidat avec ailettes intégrées |
| `baseline.stl` | Témoin voxelisé au même pas et à la même phase |
| `fins.stl` | Six nervures nouvelles, diagnostic séparé |
| `added.stl` / `removed.stl` | Différences matérielles brutes avec le témoin |
| `integration.json` | Entrées, empreintes, raccordements et contrôles du producteur |

`native-004/` contient en plus le BRep retenu et l'export STEP non qualifié.
`native-004-views/` contient les vues `assembled.png`, `opposite.png` et la
coupe `section.png`. [render.py](render.py) utilise **tous les triangles réels**,
sans lissage, décimation ou synthèse d'image. Les autres composants restent
dans leur position enregistrée. Orange désigne les zones remodelées, gris le
corps conservé ; les couleurs n'attribuent aucune propriété de matériau.

Ces STL et vues dérivent d'un scan privé : ils ne sont pas ajoutés à Git.
Seuls les sources, contrats, tests et résumés non géométriques sont publiés.
Le résumé de cette itération est dans [verification.json](verification.json).

[audit.py](audit.py) relit les fichiers bruts et leurs empreintes. Il vérifie
les incidences d'arêtes, l'orientation, les composantes, triangles de surface
nulle et normales non finies, sans réparation ni suppression. La connectivité
par graphe sparse est confrontée à l'inspecteur existant sur des témoins
analytiques, ouverts et disjoints. Les fichiers sont bornés à vingt millions
de triangles chacun. Les liens de sommets et les intersections géométriques
ne sont pas certifiés par cet audit.

Les contrôles suivants sont distincts :

- chaque racine recouvre positivement le corps conservé avant le clip du masque ;
- les champs de différence ne produisent aucune surface hors du halo de
  `0,6 unité` des deux zones, aux pas calculés ;
- tous les sommets des différences exportées doivent rester dans ce même halo ;
- les douze références de soupapes/sièges/guides restent séparées du halo par
  leurs boîtes géométriques et leur contenu reste lié aux empreintes d'entrée ;
- un corps fermé à une composante est exigé par le contrôle complet de surface.

Le témoin et le candidat au pas **0,30** comportent chacun le même minuscule
fragment de **12 triangles** hors du masque, près de `X ≈ 36,44`.
Leur contrôle à une composante échoue. Ce résultat est conservé comme rejet ;
le fragment n'est ni supprimé ni réparé. Au pas **0,15**, témoin et candidat
comportent quatre composantes et sont également rejetés. Le modèle natif ne
reprend aucun de ces maillages du corps.

Sur le livrable natif retenu, témoin et candidat ont une composante fermée,
des incidences et orientations cohérentes, zéro triangle de surface nulle et
des normales finies. Le BRep possède un solide et une coque valides, vérifiés
indépendamment après relecture. Les différences de matériau restent dans le
masque, sans volume solide ajouté ou retiré hors de celui-ci. Le bilan de
volume relatif vaut `1,69e-12`, avec une quadrature adaptative demandée à
`1e-10`. Le contrôle initial à seuil absolu `1e-6 unité³` était inadapté à
cette précision relative ; ses rejets restent dans les journaux locaux.

L'enveloppe maximale en X passe de `59,145` à `59,348` unités sur le maillage
natif, soit environ **+0,203 unité**. Ce dépassement local des extrémités
inclinées est à vérifier dans le moteur installé ; aucune compatibilité
d'encombrement ou marge à chaud n'est déduite du rendu.

Le gain thermique de 8–15 % calculé sur la cellule synthétique n'est **pas
transféré** à ce corps. La compression radiale, le raccordement, les obstacles,
la convection et les pertes de charge ont changé. Ni simulation CHT de cette
culasse, ni analyse de résistance/fatigue, ni essai matériel n'ont été exécutés.
Les passages d'air, la tenue des racines et l'enveloppe installée restent à
qualifier ; les boîtes et champs voxelisés ne prouvent pas un montage moteur.

## Reproduction et validation logicielle

Utiliser le DLL PicoGK et le checkout ShapeKernel verrouillés pour
[l'étude initiale](../bionic-fins/README.md#reproduction). Le contrat lie les
entrées privées au corps et au module retenus ; aucune entrée de substitution
n'est acceptée implicitement. Les dossiers de sortie doivent être neufs.

```sh
dotnet build Integration.csproj -c Release \
  -p:PicoGKPath=/runtime/PicoGK.dll \
  -p:ShapeKernelRoot=/upstream/LEAP71_ShapeKernel -o /prive/integration-bin
```

Depuis la racine du dépôt, avec le verrou PicoGK machine existant :

```python
import runpy, subprocess
lock = runpy.run_path('parts/picogk-catalog/tools/run_part.py')
lock['acquire']()
try:
    for step in ('0.3', '0.15'):
        subprocess.run([
            'dotnet', '/prive/integration-bin/Integration.dll', '/prive/inputs',
            'twins/m64-cylinder-head/source/bionic-fin-integration/contract.json',
            'twins/m64-cylinder-head/source/bionic-fins/candidate.json',
            f'/prive/head-bionic-{step}', step
        ], check=True)
finally:
    lock['LOCK'].unlink(missing_ok=True)
```

Avec NumPy et SciPy fonctionnels pour l'audit, VTK et Matplotlib pour les vues :

```sh
python audit.py --inputs /prive/inputs --directory /prive/head-bionic-0.15 \
  --output /prive/fine-inspection.json
python render.py --inputs /prive/inputs --directory /prive/head-bionic-0.15 \
  --output /prive/head-views
```

Pour produire le modèle natif retenu, avec OCP 7.9.3.1 et le BRep privé dont
l'empreinte est imposée par le contrat :

```sh
python build_native.py --head /prive/candidate-private.brep --inputs /prive/inputs \
  --picogk /prive/head-bionic-0.15 --output /prive/native-head-bionic
python audit.py --inputs /prive/inputs --directory /prive/native-head-bionic \
  --output /prive/native-inspection.json
python render.py --inputs /prive/inputs --directory /prive/native-head-bionic \
  --output /prive/native-head-views
```

L'audit natif relit aussi les deux exports CAO : seul le BRep passe le
contrôle exact dans cette itération. Le statut global reste
`native_geometry_screen_passed_step_export_unqualified`, sans décision de
fabrication.

Les tests ciblés s'exécutent depuis la racine :

```sh
python -m unittest discover -s tests -p 'test_m64_bionic_fin*.py' -v
```

Douze tests ciblés passent dans le virtualenv existant. Les invocations avec
`NaN`, profil modifié ou sortie existante sont refusées sans écrasement.
La compilation passe avec 37 avertissements de dépréciation des sources
ShapeKernel amont. `make check` a été exécuté : 3 638 tests, deux échecs,
23 erreurs et 205 tests sautés, dans les contrôles existants Python/SciPy et
comparaisons flottantes du ventilateur. Ce contrôle global ne passe pas et
aucune fusion n'est proposée.
