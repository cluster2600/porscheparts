# Pièce entière : retrait imposé et débridage

Planche scientifique tirée des quatre champs natifs en double précision du pilote CCX. Le calcul numérique et ses contrôles passent ; le modèle est une **sensibilité sous champ quadratique imposé et bridage provisoire**, sans prévision LPBF, dépôt, cycle thermique ou sept supports physiques simulés. Les anciens résultats DAT et leur refus de précision sont conservés dans leur dossier historique.

Le jeu local `plot-data.npz` conserve les 103 534 nœuds et les quatre champs complets. Les positions sont celles du véritable INP calculé et les 31 408 facettes sont les facettes sources, sans ajout ni subdivision. La couleur est la moyenne des trois valeurs nodales de |u| par facette ; la légende conserve le maximum nodal global. Cette vue ne revendique pas une représentation exacte des faces quadratiques courbes.

La vue inférieure amplifie uniquement la forme par **500**. La couleur et les mesures restent celles du champ réel. Après libération, max |u| = 58,090 µm ; l’incrément de débridage atteint 57,471 µm et l’entraxe principal varie de −13,187 µm. La masse EF lagrangienne reste 1,261484 kg (ρ₀V₀) ; elle ne résulte pas de ρ₀ multiplié par le volume déformé. Le contrôle uniforme donne une erreur de déformation de 1,24×10⁻¹⁴, sous le seuil inchangé de 10⁻⁷.

## Reproduire la planche

Copier ce dossier avec ses fichiers locaux épinglés. Aucun ancien chemin `work` n’est nécessaire au rendu. Employer le runtime historique AM011 : Python 3.11.15, NumPy 1.26.4, Matplotlib 3.11.2 et VisPy 0.17.0. Avec un chemin absolu vers le dossier et une sortie inexistante :

```sh
CARRIER_RENDER_PYTHON=/chemin/work/part-workflow/runtimes/pyslm-coverage-011/env/bin/python
CARRIER_FIGURE=/chemin/carrier-wholepart-release-figure-001
CARRIER_OUTPUT=/chemin/sortie-neuve
MPLCONFIGDIR=/chemin/mplconfig-prive OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  "$CARRIER_RENDER_PYTHON" -I -B "$CARRIER_FIGURE/render.py" "$CARRIER_OUTPUT"
```

Le rendu est limité à 60 secondes, sans solveur ni worker de section. Les chemins de sortie existants ou contenant un lien symbolique sont refusés. `inputs.json` lie les six entrées locales et les versions. `render-001/receipt.json` lie les exports, la police et les entrées avant/après. Le véritable rejeu depuis `/`, avec copies locales byte-identiques, a rendu les trois exports PNG/SVG/PDF byte-identiques en 4,683 s. Les deux refus réels (sortie existante et lien pendant) sont conservés dans `portable-replay.json`.

## Provenance et limites de reproduction

`evidence.json` conserve les résumés et contrôles numériques réels. Son autorité est le bundle natif `carrier-wholepart-native-double-output-001/bundle.json`, SHA256 `5e87583ce00de4f98fccd745065d630e2ad69207baa1cc985890ab8a108b024b` ; le FRD source a pour SHA256 `649d937d219720c3276dd633134836f07e27cca9281479d40abb4056763f278e`. Le bundle complet n’est pas dupliqué ici. `extract_plot_data.py` est le producteur historique exact : son rejeu nécessite ce bundle complet et le maillage source épinglé, et refuse d’écraser les données locales. Il n’est pas nécessaire pour reproduire la planche fournie.

`manifest.json` inventorie les données, sources, exports et reçus ; les caches graphiques et la copie externe de rejeu sont exclus. Aucune admission globale d’impression ni publication finale ne découle de cette planche.
