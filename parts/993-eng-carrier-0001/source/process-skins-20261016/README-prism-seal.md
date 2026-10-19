# Assemblage portable des preuves de prismes

`seal_prism_native_case.py` assemble les reçus réellement produits en un paquet
`prism-envelope-native-audit-v2`, sans lancer de calcul natif. Cette version
couvre les deux voies déclarées : centre `source_index=0` et gauche retouché
`source_index=2`. Le lecteur strict inchangé et épinglé décide l'acceptation.

```sh
AM_PYTHON -B parts/993-eng-carrier-0001/source/process-skins-20261016/seal_prism_native_case.py \
  --source-index 0 \
  --original-native-job ORIGINAL_JOB --final-snap-job FINAL_JOB \
  --distance-job DISTANCE_JOB --composed COMPOSED.json \
  --contacts CONTACTS.json --pairs PAIRS.npz \
  --frozen-plan PLAN.json --schema prism-face-schema.json --output NEW_PACKAGE
```

Les trois dossiers de calcul contiennent `audit.json` et
`execution-receipt.json` ; les deux dossiers natifs contiennent aussi
`native.json` et `result.npz`. Le premier contient `result.mesh64.exact`.
Pour la voie gauche, ajouter **ensemble** `--repair-candidate-dir REPAIR_DIR`
et `--first-snap-job FIRST_JOB`, avec `--source-index 2`. Le premier snap reste
un intermédiaire, y compris lorsque sa topologie était refusée. Le dossier de
retouche contient `result.npz`, `assessment.json`,
`execution-completion-attestation.json` et `repair_ancestral_line_sheet.py`.

Le paquet conserve les étiquettes d'origine exigées par les empreintes du reçu
de composition ; il ne réécrit aucun reçu. Chaque destination de
`local-evidence-map.json` est relative, sous `evidence/`, et son contenu est
copié puis vérifié par SHA-256. Les neuf inconnues de la voie gauche sont
dérivées du vrai masque et de la vraie carte finale ; le lecteur impose la
carte complète finale → retouche → premier snap → RAW, les identités orientées
des triangles inchangés et les lignes positives vides pour les inconnues.

Le dossier de sortie n'est publié qu'après `load_case(...).verify()`, contrôle
des originaux inchangés et contrôle des sources. Il contient les copies du
sealer et du lecteur, ainsi que `seal-assessment.json`. Un dossier de sortie
préexistant est refusé. La géométrie admise reste distincte des contacts et des
expositions de fabrication.

Six témoins logiciels couvrent le transport synthétique, la lecture stricte,
le déplacement du paquet, la corruption, la topologie et les contacts refusés,
le lecteur non épinglé, les arguments de retouche et le masque inconnu. Les
deux paquets réels existants ont aussi été réassemblés puis déplacés et relus
dans un Python isolé depuis `/` : maillages et cartes finale → RAW inchangés,
respectivement **0 et 9 inconnues**, aucun calcul natif relancé. Voir
[`prism-seal-results.json`](prism-seal-results.json).
