# Porsche 917 — F42, contrôle Omniverse et SimReady

## Verdict

La culasse F41 possède maintenant un USD fermé, minimal, lisible, validé et
rendu nativement par OVRTX sur une RTX PRO 6000 Blackwell 96 Go, mais **pas un
actif SimReady automobile complet**. Les validateurs NVIDIA confirment
l'ouverture de la scène, son prim par défaut, ses unités, son axe et l'absence
d'erreurs de schéma détectées. Ils ne démontrent aucune résistance mécanique,
dissipation thermique ou fabricabilité.

Le statut publié est `needs_rerun`, car deux gates restent rouges : le routeur
officiel CAD vers USD n'a pas publié son résultat canonique et le profil
SimReady demandé n'est pas disponible dans l'environnement.

## Géométrie examinée

| Propriété | Valeur |
|---|---:|
| Meshes | 1 |
| Sommets | 34 313 |
| Triangles | 68 678 |
| Arêtes uniques | 103 017 |
| Arêtes de bord | 0 |
| Arêtes non-manifold | 0 |
| Axe | Z |
| Unité | 0,001 m |
| Enveloppe | 119,114 × 206,094 × 82,000 mm |
| Étanchéité après soudure exacte | oui |
| Déplacement dû à la soudure | 0 |

Le STEP privé porte le SHA-256
`b3110e5d6d102c7af865b4f5a8067281ed4b9452e331eb68433e4119d36c609a`.
Le STL soudé privé porte le SHA-256
`7ac7235c6c5a50e053f398df6f5470057a5939b5129d8ba605f9d45a33a50210`.
Le USD exact rendu porte le SHA-256
`48d0f0d2179ae361fbbdddf2960493506b40da90a69ed20961fa5bdb7366e8d1`.
Ces empreintes donnent une provenance reproductible sans publier la géométrie.

## Deux chemins contrôlés

1. Le chemin officiel NVIDIA a préparé le runtime puis exécuté le prévol, la
   conversion et les validateurs. La conversion crée un USD temporaire, mais
   l'adaptateur refuse sa publication atomique : le convertisseur choisit un
   prim racine variable alors que l'adaptateur attend un chemin canonique.
2. Un chemin de contrôle déterministe réindexe le STL privé déjà soudé par
   égalité exacte des coordonnées. Il refuse toute arête ouverte, non-manifold
   ou face dégénérée, ajoute seulement les normales de face et l'extent requis
   par NVIDIA, puis définit `/HeadF41Baseline`. Aucun point n'est déplacé. Le
   contrôle USD minimal et les validateurs asset, géométrie et schéma physique
   passent sur cet actif exact.

Le second chemin prouve qu'un USD assaini est validable. Il ne transforme pas
l'échec du premier chemin en réussite du workflow complet.

## Résultats des validateurs

| Gate | Résultat | Portée |
|---|---|---|
| Prévol conversion/validation | PASS | runtime prêt |
| USD minimal | PASS | scène ouvrable, unités et prim valides |
| Asset Validator | PASS | 0 issue de schéma |
| Geometry Validator | PASS | 0 issue de schéma géométrique |
| Physics Validator | PASS | 0 issue, mais aucune propriété physique |
| Profil SimReady | FAIL | profil absent du runtime |
| Rendu OVRTX natif | PASS | PNG 1 024 × 1 024, non uniforme |
| Turntable OVRTX | PASS | 24/24 frames, 1 280 × 720 |
| Vidéo | PASS | H.264, YUV420p, 24 frames, 3 s |

Le PNG et la vidéo publiés sont des rendus OVRTX de contrôle visuel. Ils ne
représentent aucun champ thermique, contrainte, flux, couche d'impression ou
fonctionnement mécanique. Le rendu CPU précédent reste archivé comme contrôle
historique seulement.

La machine louée pour cette gate avait 32 vCPU, 128 560 Mo de RAM et une RTX
PRO 6000 Blackwell de 97 887 MiB. L'image d'exécution est épinglée par digest,
les médias et rapports sont liés par SHA-256, puis l'instance a été détruite et
son absence vérifiée après récupération.

## Conditions de fermeture

Pour fermer complètement la gate SimReady, il faut verrouiller le namespace de
sortie dans l'adaptateur CAD, fournir un profil SimReady automobile versionné et
ajouter des matériaux physiques qualifiés sans les inventer. OVRTX est fermé ;
les validations CFD, thermiques, structurelles et LPBF restent des gates
indépendantes.
