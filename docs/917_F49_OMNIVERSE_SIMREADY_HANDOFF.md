# Lot Omniverse / SimReady F49 des culasses 2V et 4V

## État vérifié

Le lot est **préparé mais bloqué avant inspection et conversion**. Aucun STEP
F49 n'est encore accepté par le contrat de solide, donc aucun USD F49, aucune
affectation Material/Physics et aucun rendu OVRTX F49 ne sont revendiqués.

Le seul extérieur autorisé est la peau F43 reconstruite depuis 44 contours du
scan. Les variantes 2V et 4V doivent réutiliser exactement le même STEP source
F43 (`38f8ed…0f24`), sans changement d'échelle et sans enveloppe synthétique.
Les lignées F39/F42 et les deux STEP F47 diagnostiqués invalides sont refusés
comme source, comme remplacement et comme rendu de produit courant.

L'image
`ghcr.io/cluster2600/3dprinting993-simready-local-ai@sha256:5a69a680…69699`
est publiquement récupérable. Son manifeste est `linux/amd64`; le run GitHub
`33730827271` est vert et atteste les smokes CPU/imports. Cette preuve ne
qualifie pas un GPU réel, le démarrage des services Content Agents, une
conversion CAD ni un rendu OVRTX F49. Ces vérifications restent des gates du
préflight sur l'hôte NVIDIA.

## Entrées futures exactes

| Variante | STEP privé attendu | État actuel |
|---|---|---|
| 2V | `work/917-f49-solid/917-head-2v-f49-private.step` | bloqué |
| 4V | `work/917-f49-solid/917-head-4v-f49-private.step` | bloqué |

Le rapport privé attendu est
`work/917-f49-solid/f49-solid-private-audit.json`; sa synthèse publique doit
être `twins/reference-917-engine/evidence/f49-solid/f49-solid-public-report.json`.
Le gabarit
`twins/reference-917-engine/remote-simready/f49/input-manifest.template.json`
reste volontairement rempli de `false` et de `null`. Il ne faut jamais le
promouvoir artificiellement.

## Gate d'entrée obligatoire

Après acceptation réelle des deux STEP, copier le gabarit hors dépôt, renseigner
les receipts SHA-256/taille et uniquement les résultats effectivement obtenus,
puis exécuter :

```bash
python3 twins/reference-917-engine/remote-simready/f49/validate_inputs.py \
  --manifest /chemin/prive/input-manifest.f49.json \
  --report /chemin/prive/f49-simready/00_input/input-gate.json
```

Un code de sortie non nul interdit le préflight et toute inspection du STEP.
Le gate impose notamment : BRepCheck exact, zéro faute BOPAlgo après
round-trip STEP, un solide fermé/manifold, maillage volumique Gmsh, signature
externe F43 verrouillée hors ouvertures et identité d'échelle `[1,1,1]`.

## Workflow NVIDIA atomique

Le fichier `remote-simready/f49/commands.json` est le contrat de commandes. Il
n'est pas un runner : chaque commande est lancée séparément, après lecture du
rapport précédent, pour une seule variante et un répertoire de sortie dédié.
L'ordre est imposé :

1. gate d'entrée F49 ;
2. préflight NVIDIA avec cibles `conversion,validation,content-agents` ;
3. vérification/déploiement des services OVRTX, Material et Physics ;
4. identification du contexte sur le STEP source accepté ;
5. `convert-to-usd`, puis `validate-usd-minimum` ;
6. Material Agent, puis Physics Agent ;
7. conformance `Prop-Robotics-Neutral@1.0.0` ;
8. validations Asset, Geometry, Physics et SimReady ;
9. réparation FET ciblée si le rapport l'exige, puis revalidation ;
10. rendu final du dernier USD par `ovrtx-render-service` avec détection
    d'image vide/uniforme.

Les chemins de sortie ne sont jamais devinés : chaque étape doit extraire le
`output_usd_path` concret du rapport de l'étape précédente. Avec
`property_assignment_intent=run`, aucune normalisation FET n'est autorisée
avant Material et Physics. Un échec de déploiement, conversion, affectation ou
conformance arrête la chaîne. Après création d'un USD significatif, les quatre
validateurs restent diagnostiques et leurs constats sont tous conservés.

## Matériau, physique et images

Le prompt Material limite l'affectation à une apparence aluminium neutre. Le
CP1 reste un candidat LPBF à qualifier par coupons à chaud; aucune carte de
propriétés n'est inventée. Le prompt Physics n'autorise que des collisions
statiques sur la géométrie existante : pas de rigid body, masse, inertie,
charge, joint, mouvement ni proxy de collision.

Les images finales doivent venir du service OVRTX sur les USD finaux 2V et 4V.
Elles doivent employer la même caméra pour la comparaison et inclure des
coupes du modèle accepté. Une capture d'un ancien modèle, un rendu d'agent, une
image uniforme ou une reconstruction visuelle de remplacement est refusée.

## Ce que SimReady ne valide pas

Un profil SimReady propre confirme l'intégrité et les métadonnées du paquet USD
pour Omniverse. Il ne valide ni l'ajustement Porsche, ni le matériau à chaud,
ni CFD/CHT/FEA/fatigue, ni le procédé LPBF, ni le démarrage moteur. Les gates
de fabrication, impression métal et démarrage restent fermées dans le contrat
F49, indépendamment du résultat Omniverse.
