# Ailettes bioniques — première étude PicoGK / ShapeKernel

Cette itération produit des **cellules d'ailettes synthétiques**, des éprouvettes
à trois ailettes, et une comparaison thermique reproductible. Elle ne remplace
pas la culasse M64/993 à quatre soupapes et ne constitue pas son optimisation
complète. La cible est confirmée par le propriétaire le 11 octobre 2026.

Le corps de référence reste intact. Il provient du scan 935 utilisé pour les
travaux M64 ; l'échelle absolue, les interfaces de la variante 993 et la
fabricabilité ne sont pas certifiées. Les dimensions ci-dessous sont des
dimensions **d'étude**, jamais des mesures Porsche.

## Géométrie et résultat limité

La cellule bionique retenue est une nervure effilée à bifurcation : une racine
épaisse conduit la chaleur vers deux branches plus fines. Le témoin est une
ailette droite ; des témoins simplement effilés sont également comparés.
Les feuilles sont extrudées suivant Y, direction supposée de l'air. Cette forme
ne dérive pas d'une optimisation topologique mécanique, d'une loi de Murray
ou d'un calcul d'écoulement.

| Paramètre d'étude | Valeur |
| --- | --- |
| Hauteur d'axe | 28 mm |
| Profondeur suivant l'air supposé | 60 mm |
| Pas de répétition | 14 mm |
| Volume d'une ailette, jonctions fusionnées | 5 040 mm³ |
| Racine / jonction / extrémité du candidat | 4,145 / 1,884 / 1,413 mm |
| Hauteur de bifurcation | 19,6 mm |
| Déport de chaque extrémité | ±2 mm |
| Épaisseur de la base d'éprouvette commune | 4 mm |

La meilleure cellule dans le domaine échantillonné est
`leaf-0.7-2.0-2.2-0.75`. Sur la grille thermique fine de 0,05 mm, sa
conductance `Q / (T_racine − T_air)` dépasse celle de l'ailette droite de
**7,90 à 14,58 %**, à volume de métal continu égal. La variation de sa
conductance entre 0,10 et 0,05 mm reste sous **0,379 %**. L'erreur de bilan
énergétique est contrôlée à chaque résolution et doit rester sous `1e-8`.
Ce résultat ne prouve ni un optimum global ni un gain sur le moteur.
Le classement des 51 cellules admissibles utilise la grille 0,20 mm ; seules
les trois cellules du contrôle de convergence sont ensuite raffinées.

Les neuf scénarios combinent `k = 12, 80, 160 W/(m·K)` et
`h = 40, 100, 200 W/(m²·K)`. Ce sont des sensibilités imposées ; aucun
alliage, procédé ou coefficient de convection réel n'est sélectionné.

![Coupes des STL réels et comparaison thermique](results/review.png)

## Méthode et contrôles indépendants

1. [study.py](study.py) compare 112 propositions à volume **nominal** égal.
   61 sont rejetées par les contraintes exploratoires d'épaisseur ou
   d'enveloppe. Le réseau thermique 1D est vérifié par une formule indépendante
   d'ailette droite à extrémité convective et par subdivision des sections.
   Ses jonctions idéales surestiment les surfaces disponibles près des branches.
2. [countercheck.py](countercheck.py) fusionne les trapèzes et rétablit un
   volume de métal **réellement égal**, sans compter deux fois la jonction.
   Il résout la conduction 2D dans la section complète et la convection
   imposée sur les seules surfaces exposées. Les faces en escalier utilisent
   une correction de surface suivant la normale de la frontière géométrique.
   La surface corrigée est confrontée au périmètre euclidien indépendant.
   La température reste supposée uniforme suivant Y ; l'air n'est pas résolu.
3. [Program.cs](Program.cs) utilise effectivement `BaseBox`, `LocalFrame` et
   `LineModulation` de ShapeKernel, puis les unions natives de PicoGK. Les
   exports sont calculés aux pas 0,30 et 0,15 mm. Une phase commune de grille
   est annulée à l'export. Aucun lissage ou réparation des STL n'est appliqué.
4. L'inspecteur existant
   [audit_surface_topology.py](../picogk-local-junction/audit_surface_topology.py)
   contrôle les triangles bruts : indexation exacte, composantes, liens de
   sommets, orientation et triangles exactement dégénérés. Une surface fermée
   ne prouve pas l'absence d'auto-intersection ni la fabricabilité.
5. [render.py](render.py) trace les coupes Y = 0 des **STL réellement produits**
   après contrôle d'empreinte. L'image n'est pas une génération artistique.

Les propositions du réseau 1D et du contrôle 2D diffèrent : le premier préfère
une bifurcation à 7 mm ; le second retient 19,6 mm. Le classement 1D n'est donc
pas adopté comme preuve. Les premiers calculs sans correction de surface des
faces obliques, puis avec un témoin mal aligné sur la grille, sont conservés
localement et **écartés**. Le résultat publié provient du calcul corrigé `fv-004`.

Les fichiers [baseline.json](baseline.json) et [candidate.json](candidate.json)
constituent les paramètres éditables ; le C# reste le générateur de géométrie.
Les [résultats complets](results/countercheck.json), le
[premier criblage](results/screen.json) et le
[reçu de vérification](results/verification.json) conservent les empreintes et
les limites. Les STL/VDB privés ou dérivés du scan ne sont pas ajoutés à Git.
Les exports d'éprouvettes synthétiques sont disponibles dans le dossier local
de calcul, identifié dans la réponse de livraison.

## Reproduction

Utiliser les versions déjà verrouillées dans
[sources.lock](../../../../containers/m64-leap71/sources.lock) : ShapeKernel
`7b9097842446a28bb5d49203724622e594ce7510` et le runtime PicoGK correspondant.
Vérifier le checkout ShapeKernel avant compilation. Le reçu contient aussi
l'empreinte du DLL PicoGK effectivement utilisé, version native `26.2.0`.
Il faut .NET 9, NumPy, SciPy fonctionnel et Matplotlib, déjà disponibles dans
les environnements locaux du projet. Aucun paquet n'est installé implicitement.

Depuis ce dossier, avec des chemins de sortie neufs :

```sh
python study.py /prive/fin-screen
python countercheck.py /prive/fin-screen/study.json /prive/fin-fv
dotnet build BionicFins.csproj -c Release \
  -p:PicoGKPath=/runtime/PicoGK.dll \
  -p:ShapeKernelRoot=/upstream/LEAP71_ShapeKernel -o /prive/fin-bin
dotnet /prive/fin-bin/BionicFins.dll --self-test
```

Les bibliothèques natives doivent être accessibles au chargeur. Chaque
exécution native prend le **verrou machine existant** ; depuis la racine du
dépôt, avec `dotnet` dans le PATH :

```python
import runpy, subprocess
lock = runpy.run_path('parts/picogk-catalog/tools/run_part.py')
lock['acquire']()
try:
    for name in ('baseline', 'candidate'):
        for step in ('0.3', '0.15'):
            subprocess.run([
                'dotnet', '/prive/fin-bin/BionicFins.dll',
                f'twins/m64-cylinder-head/source/bionic-fins/{name}.json',
                f'/prive/fin-{name}-{step}', step
            ], check=True)
finally:
    lock['LOCK'].unlink(missing_ok=True)
```

```sh
python render.py /prive/fin-fv/countercheck.json \
  /prive/fin-baseline-0.15 /prive/fin-candidate-0.15 /prive/fin-review.png
python -m unittest discover -s tests -p 'test_m64_bionic_fins.py' -v
```

La dernière commande s'exécute depuis la racine du dépôt. Sans SciPy fonctionnel,
les trois tests de volumes finis sont explicitement sautés ; les quatre tests
1D restent exécutables. Les sept tests passent dans le virtualenv local.
Le `make check` global lancé avec Python système ne passe pas : 3 635 tests,
2 échecs, 23 erreurs et 205 tests sautés. Les problèmes se situent dans les
contrôles existants de SciPy, Python 3.10 (`hashlib.file_digest` absent) et deux
comparaisons flottantes exactes des études de ventilateur. Aucune fusion proposée.

## Passer à la culasse complète

| Étape | Données nécessaires et résultat attendu |
| --- | --- |
| 1. Définir le domaine modifiable | Repère et échelle étalonnés ; interfaces de cylindre, goujons, porte-arbres, conduits, bougies et déflecteurs. Masque indépendant protégeant chambre, sièges, guides, ponts de soupapes, portées et chemins de charge. Aucun évidement du corps actuel n'est autorisé par cette étude. |
| 2. Définir le chargement thermique | Cartes de flux de chambre et d'échappement, conduction des sièges/guides, températures d'huile et de contact, cas ralenti/charge/transitoire, propriétés `k(T)` du matériau retenu. Ces valeurs restent inconnues. |
| 3. Définir l'air installé | Courbe pression–débit de la turbine et régime, débit par culasse, température d'entrée, conduits/déflecteurs, recirculation et rugosité. La surface seule ne suffit pas. |
| 4. Comparer en CHT 3D | Corps et air conjugués ; témoin conservé et variantes PicoGK. Minimiser les températures de sièges d'échappement et de ponts à puissance de ventilation comparable, avec limites de masse et pertes de charge. Étudier trois maillages et le bilan énergétique. |
| 5. Qualifier la géométrie bionique | Racines et branches dimensionnées par les flux locaux, dégagements d'air mesurés, dépoudrage/nettoyage, épaisseur/processus, déformations et fatigue thermomécanique. Essai d'éprouvette puis banc culasse, revue professionnelle avant fabrication fonctionnelle. |

Le chemin de chaleur recherché est chambre/échappement → ponts, sièges et
guides → racines conductrices → branches → air. Les efforts de combustion,
serrage de goujons et distribution conservent leur propre chemin de charge.
Les interfaces, charges et procédé manquants empêchent d'affirmer que la
culasse complète est optimisée ou imprimable.

Sources : [PicoGK / LEAP 71](https://leap71.com/PicoGK/),
[documentation ShapeKernel](https://github.com/leap71/LEAP71_ShapeKernel/blob/7b9097842446a28bb5d49203724622e594ce7510/Documentation/README-GettingStarted.md),
[cours d'échange thermique MIT](https://web.mit.edu/snively/www/2_005%20Coursenotes-1.pdf),
[solveur de transfert conjugué OpenFOAM](https://api.openfoam.com/2506/chtMultiRegionFoam_8C.html).
