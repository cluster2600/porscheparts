# Suite libre pour construire le jumeau numérique

## Décision

Le projet retient une chaîne ouverte où le LLM assiste l'ingénieur mais ne
produit jamais une cote faisant autorité. La géométrie de fabrication reste un
solide paramétrique versionné ; les scans et les réponses du modèle sont des
entrées à vérifier.

| Fonction | Choix principal | Rôle dans le projet |
|---|---|---|
| Agent CAO/code | Qwen3-Coder-30B-A3B-Instruct + Qwen Code | écrire et corriger les maîtres build123d, tests et fiches JSON |
| Lecture multimodale | Qwen3-VL-8B-Instruct | classer photos et plans, relever des candidats à vérifier |
| Serveur LLM | vLLM | API locale compatible OpenAI sur la machine GPU |
| CAO paramétrique | build123d + FreeCAD | solides BREP, STEP et assemblage contraint |
| Reconstruction | COLMAP/GLOMAP + Open3D | photos vers nuage/maillage, recalage et écarts |
| Maillage calcul | Gmsh | maillage volumique reproductible |
| Structure/thermique | CalculiX | EF linéaire, non linéaire, statique et thermique |
| Fluide/thermique | OpenFOAM | écoulement, convection et transferts thermiques |
| Visualisation | FreeCAD, Blender, ParaView | inspection CAO, contexte visuel et résultats de calcul |
| Données | Git + JSON + STEP | provenance, versions, interfaces et règles d'acceptation |

Les modèles Qwen sont publiés sous Apache-2.0. Le modèle Coder est un MoE de
30,5 milliards de paramètres, dont environ 3,3 milliards actifs par jeton, et
sa fiche officielle fournit directement une commande `vllm serve`. FreeCAD
utilise Open CASCADE, comprend un atelier Assembly intégré et importe/exporte
STEP. build123d sait construire des arbres d'assemblage et exporter l'ensemble
en STEP.

Sources primaires :
[Qwen3-Coder](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct),
[Qwen3-VL](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct),
[FreeCAD](https://www.freecad.org/features.php),
[assemblages build123d](https://build123d.readthedocs.io/en/latest/assemblies.html),
[COLMAP](https://colmap.github.io/tutorial.html),
[Gmsh](https://gmsh.info/),
[CalculiX](https://www.calculix.de/) et
[OpenFOAM](https://openfoam.org/version/13/).

## Ce que fait chaque LLM

`Qwen3-Coder-30B-A3B-Instruct` est le modèle principal. Il peut transformer une
fiche de mesures validée en script build123d, proposer les contraintes
d'assemblage et écrire les tests. Son résultat doit passer `make check`, être
ouvert dans FreeCAD et être comparé aux sources.

`Qwen3-VL-8B-Instruct` sert au tri initial de photos, captures et dessins. Il
peut repérer une référence, un tableau ou une vue utile, mais une cote lue par
vision reste `candidate` jusqu'à une lecture humaine et une seconde preuve.

Neural Concept n'entre pas dans le socle initial : c'est un produit commercial
de modèle de substitution, utile seulement après constitution d'un ensemble de
simulations ou d'essais corrélés. Avant ce stade, il ajoute du coût sans résoudre
le manque de géométrie et de conditions limites.

## Dimensionnement Vast.ai

Les tailles ci-dessous sont des cibles pratiques à confirmer avec le format de
poids et la longueur de contexte au moment de la location.

| Offre | Usage recommandé | Limite |
|---|---|---|
| RTX 4090, 24 Go | Qwen3-VL-8B, COLMAP ; Coder 30B quantifié lancé seul | contexte et cache KV à limiter |
| RTX A6000 / RTX 6000 Ada, 48 Go | choix de base : Coder 30B quantifié ou FP8, puis VL/reconstruction séparément | éviter deux gros modèles simultanés |
| A100/H100, 80 Go ou 2 × 48 Go | grands contextes et modèles plus lourds | coût rarement justifié pour la première zone |

Le meilleur premier choix est donc **une carte de 48 Go**, 16 vCPU, 64 Go de
RAM et 150 à 250 Go de disque. La photogrammétrie et le LLM sont exécutés l'un
après l'autre. La CAO/EF peut ensuite tourner avec
`3dprinting993-cadsim` sur une offre CPU moins chère.

Vast exécute les instances comme des conteneurs Docker Linux et réserve la
taille disque à la création. Ses volumes persistants restent liés à la machine
physique et ne constituent donc pas une sauvegarde portable. Voir la
[documentation Docker](https://docs.vast.ai/guides/instances/docker-environment)
et la [documentation des volumes](https://docs.vast.ai/guides/instances/storage/volumes).

## Lancement du LLM sur Vast.ai

La location est payante : ces commandes sont un modèle de lancement, pas une
autorisation de créer l'instance. Après sélection d'une offre 48 Go et création
d'un volume, lancer l'image officielle vLLM avec le port 8000 exposé :

```bash
vastai create instance <offer_id> \
  --image vllm/vllm-openai:latest \
  --disk 80 --ssh --direct \
  --env '-p 8000:8000 -v <volume_name>:/data'
```

Dans l'instance :

```bash
vllm serve Qwen/Qwen3-Coder-30B-A3B-Instruct \
  --host 0.0.0.0 --port 8000 \
  --enable-auto-tool-choice --tool-call-parser hermes
```

Pour une exécution reproductible, remplacer `latest` par la version d'image
testée avant la première location. Ne jamais placer de jeton dans la commande,
le dépôt ou l'historique shell ; utiliser le mécanisme de secret propre à
l'instance.

## Flux de construction du twin

1. Enregistrer la source, ses droits et ce qu'elle prouve.
2. Extraire des **cotes candidates** avec Qwen3-VL, puis les vérifier.
3. Produire le maître build123d/FreeCAD et exporter STEP.
4. Recaler scans et solide dans Open3D, avec une référence métrique connue.
5. Définir repères, joints, contacts et jeux dans le registre du twin.
6. Assembler dans FreeCAD et reproduire l'assemblage par script build123d.
7. Exécuter collisions et règles d'acceptation avec les incertitudes.
8. Mailler avec Gmsh puis simuler avec CalculiX ou OpenFOAM si nécessaire.
9. Corréler à des mesures physiques avant toute déclaration de validation.

Le premier lot géométrique est
`TWIN-993-WHEEL-HUB-INTERFACES-0001`. Il contient quatre proxys STEP de roues,
mais attend encore les géométries de moyeu et de frein avant le premier contrôle
spatial réel.

## Données et sécurité

- Les photos et scans bruts restent dans `/data` ou un stockage objet privé,
  jamais dans Git.
- Un volume Vast est temporaire et lié à son hôte ; synchroniser les résultats
  à chaque fin de session.
- STEP et les rapports dérivés n'entrent dans le dépôt que si leur licence et
  leur provenance autorisent la redistribution.
- Le LLM ne valide ni ajustement, ni matière, ni sécurité d'une pièce.
- Les pièces de roue, freinage, direction et suspension restent bloquées pour
  fabrication sans revue d'ingénierie professionnelle.
