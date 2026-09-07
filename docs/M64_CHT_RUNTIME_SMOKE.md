# M64 — prévol logiciel CHT, pas simulation de culasse

Date : 2026-09-06. Statut : **exécution de référence réussie après correction du
tutoriel ; aucune validation physique ou industrielle du M64**.

## Cas et environnement effectivement exécutés

- Kali, image locale amd64
  `sha256:a233511bef9b4fbf0653ca94258061d61b3fccbd6b4e3ef6d71c669d70de1c17`.
- OpenFOAM Foundation 14, build `14-7b05503f98a8`.
- Tutoriel livré dans l'image :
  `/opt/openfoam14/tutorials/multiRegion/CHT/circuitBoardCooling`.
- `Allmesh-extrudeFromInternalFaces`, puis `foamMultiRun` séquentiel.
- Air `perfectGas`, `Cp=1004.4 J/kg/K`, masse molaire 28.96,
  viscosité 1.831e-5 Pa.s, Pr=0.705 ; solide `heSolidThermo` et source de chaleur.
- Équations d'énergie effectivement résolues : `h` côté fluide, `e` côté solide.
- Maillage fluide 2 000 cellules ; solide `baffle3D` 800 cellules.
  Les deux `checkMesh` retournent `Mesh OK`.
- Docker éphémère, réseau désactivé, plafond 2 CPU / 4 Go / 128 processus,
  `timeout 240`. Aucune location Vast, aucun autre job modifié.

Le contrôle de fin est réduit de 5 000 à **20 itérations stationnaires**, avec
écriture à 20. Les indications `Time = 20s` du journal ne représentent donc pas
20 secondes physiques de refroidissement transitoire.

## Échec initial et correction justifiée

Le premier essai est conservé sur Kali sous
`/tmp/m64-cht-smoke.IQcI1i/case` : sortie 136, exception flottante à l'itération 2
dans `GAMGSolver::scale`, région fluide. Dès l'itération 1, `k` est borné après
une valeur minimale de -6987.92. L'état initial est T=300 K, p=100000 Pa,
p_rgh=0 Pa : ce n'est pas une pression absolue initiale nulle.

Le journal signale `Neither fields nor equations specified`. Le tutoriel
contient des facteurs de relaxation dans une structure plate. Le code de cette
version, `src/OpenFOAM/matrices/solution/solution.C`, lignes 50–71, attend les
sous-dictionnaires `fields` et/ou `equations` ; ces facteurs n'étaient pas pris
en compte.

Une seule correction numérique a été testée dans une copie séparée : replacer
les **mêmes facteurs** dans `fields` (rho=1, p_rgh=0.7) et `equations`
(U=0.3, h=0.7, turbulence=0.3). Aucun seuil de convergence ni propriété physique
n'a été rendu plus permissif. L'exception disparaît et les 20 itérations se
terminent. Le premier wrapper avait en outre un contrôle `^End` trop strict
pour la sortie indentée ; ce contrôle textuel a été corrigé et une répétition
complète du cas a retourné **0**.

## Résultat reproductible et limites

Dernière répétition : `/tmp/m64-cht-smoke.kOKWNE/case` sur Kali.

| Champ interne à l'itération 20 | Minimum | Maximum |
|---|---:|---:|
| T air, 2 000 cellules | 300 K | 306.374 K |
| T solide, 800 cellules | 317.168 K | 428.410 K |

Les résidus initiaux de h (~0.00313) et e (~0.00105) à l'itération 20 restent
au-dessus des critères de convergence du tutoriel. **Ce résultat établit
seulement que la chaîne gaz–solide avec énergie s'exécute**, pas sa convergence
globale, son indépendance de maillage ou son bilan énergétique qualifié.

SHA-256 du journal final :
`656d92a4ffb393c2bc6c427ca36a561934b1e43f7e475a47a0d137d94d213cf2`.

SHA-256 du champ T fluide :
`3951e69bb308f001d4691b3f9792fa1ae5d7ca3e42c5ed5e3517e556463b6474`.

SHA-256 du champ T solide :
`d7c9fb57b0aa1b084fffbacaafdb1dd23ca192fb6f2b37d23821ec82ce6a3a5c`.

Le script `twins/m64-cylinder-head/run_cht_runtime_smoke.sh`
s'exécute dans l'image avec un répertoire neuf monté sur `/output` et l'argument
`repair-relaxation`. Sans cet argument il reproduit la configuration initiale
défaillante. Contrôle local `bash -n` réussi ; exécution Docker réelle réussie.

La culasse, ses ailettes, ses interfaces M64, le turbo et le circuit d'huile
ne figurent **pas** dans ce cas. Aucun résultat de résistance, de fatigue,
d'impression, d'Omniverse ou de certification n'en découle. Les étapes suivantes
restent la géométrie M64, ses conditions aux limites sourcées, la convergence
CHT, le bilan de flux et la comparaison à des références ou essais pertinents.
