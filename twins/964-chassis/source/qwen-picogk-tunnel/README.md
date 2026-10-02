# Reprise locale Qwen / PicoGK — tunnel, 2 octobre 2026

Etude geometrique executee, **pas une monocoque terminee**. Le nouveau parcours
reprend les hypotheses du [concept publie](https://github.com/cluster2600/porscheparts/blob/135dcc8ef6e71ac483e1ed3036217536562c80a1/twins/993-carbon-safety-cell/design-space.json),
sans reconstruire ni modifier le scan, les interfaces mesurees ou les preuves
historiques. Les anciennes CAO et simulations restent conservees.

## Resultat

Qwen2.5-Coder-1.5B-Instruct 4-bit avec l'adaptateur Mac
`coding-003/checkpoint-600` a reproduit exactement trois cylindres demandes :
coordonnees, rayons et extremites planes. C'est une **transcription contrainte**,
pas une conception autonome, un apprentissage nouveau ou une mesure.
`coding-007`, observe en entrainement au debut de cette reprise puis au statut
`no_validation_improvement`, n'a pas remplace le checkpoint retenu.
LM Studio, qui demande une authentification, n'a pas ete utilise.

PicoGK reconstruit cinq volumes locaux : deux parois, couvercle, nez et bande
de plancher du tunnel. Les positions sont reprises de `build_cad.py` du concept,
dont les dimensions sont **hypothetiques**. Ses anciens controles de section
ne couvraient pas les collisions longitudinales et celle du tour de levier.

| Enveloppe contre le tunnel initial | Intersection a 4 mm (mm3) | A 2 mm (mm3) | Calcul analytique (mm3) |
|---|---:|---:|---:|
| Tringlerie C2 | 0 | 0 | 0 |
| Tube central C4 contre le nez | 670 614 | 670 408 | 671 515 |
| Guidage C4 contre le nez | 30 111 | 30 294 | 30 561 |
| Tour de levier C2 contre le couvercle | 965 291 | 985 619 | 990 000 |

Deux mailles ne demontrent pas une convergence generale : l'erreur du tube
central ne diminue pas monotonement. Les trois interferences sont retrouvees
aux deux resolutions, avec un ecart maximal de volume a l'analytique de 2,50 %
a 4 mm et 0,88 % a 2 mm. Ces ecarts ne sont pas des tolerances de fabrication.

La variante soustrait ces enveloppes du nez et du couvercle. Le residu est nul
sur chaque meme grille, **par construction**, avec jeu additionnel nul. Les
sondes du passage avant, de l'ouverture de service et des parois sont conformes
au modele demande. Aucune deduction de rigidite, fatigue ou resistance au feu.
Une ouverture de couvercle exige encore une conception de trappe et de joints ;
un passage dans le nez exige renforts, protection et revue des chemins d'effort.

Le [recu de reprise](../../derived/qwen-picogk-tunnel-20261002.json) conserve les
reponses Qwen, les rapports natifs, les entrees et les empreintes. Les STL et
les coupes restent dans `work/qwen-picogk-monocoque-20261002/`, sans scan brut.
`tunnel-relief-study.stl` est un derive ; le master editable est `Program.cs`
avec les parametres JSON, pas un STEP/BREP de production.

## Reproduire avec les environnements deja installes

Tous les dossiers de sortie doivent etre nouveaux. Aucun telechargement de
poids, entrainement, changement de serveur, location Vast ou code Qwen arbitraire
n'est execute. La sortie Qwen est verifiee par le parseur PicoGK deja utilise
pour l'entrainement ; seuls les nombres compares exactement passent a C#.

```sh
MONO_TRAIN=/Users/maxime/.codex/worktrees/m64-local-architecture-qwen/3dprinting993
MONO_PICO=/Users/maxime/projects/3dprinting993/work/m64-private-20260907/nemo-picogk-20260928.ADELugEK
MONO_SOURCE=twins/964-chassis/source/qwen-picogk-tunnel
MONO_OUT=work/monocoque-qwen-new-run
mkdir -p "$MONO_OUT"
"$MONO_TRAIN/work/m64-qwen/venv/bin/python" "$MONO_SOURCE/prepare.py" \
  --training "$MONO_TRAIN" \
  --design /Users/maxime/projects/3dprinting993/twins/993-carbon-safety-cell/design-space.json \
  --output "$MONO_OUT/inference"
"$MONO_PICO/dotnet/dotnet" build "$MONO_SOURCE/Tunnel.csproj" -c Release \
  -p:PicoGKPath="$MONO_PICO/picogk-bin/PicoGK.dll" \
  -p:BaseIntermediateOutputPath="$PWD/$MONO_OUT/obj/" -o "$MONO_OUT/bin"
DYLD_LIBRARY_PATH="$MONO_PICO/picogk-bin" "$MONO_PICO/dotnet/dotnet" \
  "$MONO_OUT/bin/Tunnel.dll" "$MONO_OUT/inference/input.json" "$MONO_OUT/native-4mm" 4
DYLD_LIBRARY_PATH="$MONO_PICO/picogk-bin" "$MONO_PICO/dotnet/dotnet" \
  "$MONO_OUT/bin/Tunnel.dll" "$MONO_OUT/inference/input.json" "$MONO_OUT/native-2mm" 2
work/964-scan-recalage-20260925/runtime/bin/python "$MONO_SOURCE/sections.py" \
  "$MONO_OUT/native-4mm" "$MONO_OUT/sections.png"
python3 -m unittest discover -s tests -p 'test_964_*.py' -v
```

Runtime effectivement utilise : SDK .NET 9.0.317, runtime 9.0.19,
PicoGK source `0e6cf6b6f4993ec16dbcd72d8f27f26b999980f3` et bibliotheque native
Mac `picogk.26.2.dylib`. Ce profil ne modifie pas celui des anciens jobs Linux.

La [reprise suivante sur Kali](../picogk-abi-probe/README.md) documente les
calculs Docker et la correction isolee d'une liaison booleenne PicoGK sous
Linux. Elle ne remplace pas le present recu Mac et ne valide pas tous les
usages de la bibliotheque.

## Verification du 2 octobre 2026

- Build natif : aucune erreur ni avertissement ; executions a 4 et 2 mm terminees.
- Suite ciblee `test_964_*.py` : six tests reussis, y compris le controle des
  empreintes du recu et le maintien des interdictions de fabrication.
- `make check` : suite principale de 3 037 tests OK (120 ignores), puis arret
  dans `917-manufacturing-f37-lpbf-audit-check` : le socket Docker du Mac est
  absent. Le controle global n'est donc **pas valide** ; les etapes suivantes
  n'ont pas ete executees. Aucun serveur ni parametre Docker n'a ete change.
- `git diff --check` : reussi.

## Limites et suite

Les tests unitaires couvrent les coordonnees, rayons, extremites, nombres de
segments et formules de collision. Les deux executions natives couvrent la
geometrie demandee ; les coupes viennent des maillages, pas d'une image generee.
Cette separation suit les skills de strategie de test et de visualisation.
Les quatre variantes de vehicule ne sont **pas** validees par ces deux packages.
Le repere du concept est X arriere, Y gauche, Z haut ; aucune superposition
avec le scan 964, dont X est vers l'avant, n'est effectuee sans transformation.

La suite du produit reste le [plan de mesure](../../interface-measurement-plan.md),
puis les interfaces et surfaces completes, les stratifies et assemblages,
les calculs composites correles, l'outillage et les essais. La monocoque complete,
les moules, la fabrication et l'aptitude route/circuit restent non valides.
