# Draftwright — deux essais bornés refusés, sans adoption

Les deux essais ci-dessous ont atteint leur budget de **480 secondes**. Aucun
dessin PDF/SVG/DXF/PNG ni rapport de lint n'a été produit. Il n'existe donc
aucune annotation exportée à vérifier, ni amélioration de lisibilité établie.
Draftwright n'est pas adopté dans la recette du carrier ou le paquet logiciel.

| Essai réellement exécuté | Budget | Durée observée | Code retour | Dernier constat |
|---|---:|---:|---:|---|
| CLI automatique officiel | 480 s | 480,0331986248493 s | −15 | Délai atteint, aucun fichier de dessin écrit ; journaux vides. |
| Feuille déclarative `Sheet.build()` | 480 s | 480,03615249996074 s | −15 | `STEP_loaded`, puis `F0_declarations_ready` ; aucun retour de `Sheet.build()` avant SIGTERM. |

Le second essai est une construction déclarative distincte du premier, dans
le même environnement de dessin isolé. Il n'est pas présenté comme une
réussite ou une réexécution du CLI automatique. Les scripts prévoient ensuite
un lint de placement et des exports ; **ces étapes n'ont pas été atteintes**.
Les deux processus ont été récoltés après interruption ; les reçus conservent
les vrais codes et les durées, ainsi que les limites à un thread et `nice 10`.

## Sources et preuves conservées

Source officielle : [pzfreo/draftwright](https://github.com/pzfreo/draftwright),
commit [f1a5db9b4490e9b233ae5b7cac1138633929c693](https://github.com/pzfreo/draftwright/tree/f1a5db9b4490e9b233ae5b7cac1138633929c693),
version déclarée **0.5.0.dev0**, licence **AGPL-3.0**.
[UPSTREAM-LICENSE](UPSTREAM-LICENSE) est une copie exacte de la licence du
commit inspecté. L'environnement consigné utilise Python 3.13.16,
build123d 0.11.1, OCP-novtk 7.9.3.1 et Quiddity 0.3.10 ; la provenance conserve
les versions, URL et empreintes des distributions.

Le [reçu compact](results.json) relie les deux essais et les copies exactes :

- `automatic/` : plan, exécution, évaluation terminale, manifeste, provenance,
  inspection STEP indépendante, scripts ponctuels et petits journaux ;
- `declared/` : plan, exécution, revue terminale, manifeste, déclarations,
  preuve avant export et scripts de construction/revue.

Les deux répertoires originaux `work/carrier-draftwright-20261017/` et
`work/carrier-draftwright-declared-20261017/` sont conservés. Les chemins
absolus des reçus sont des métadonnées historiques ; les copies ne les
réécrivent pas. Aucun STEP, arbre logiciel amont, environnement virtuel ou
grosse dépendance n'est dupliqué ici.

## Huit valeurs du STEP, indépendantes des dessins

Le STEP retenu a le SHA
`de0e55a3150dacc5428bbc301d18d2e43477f038c3f4df295d9373af8e906b63`.
L'inspection OCP indépendante sélectionne les **six alésages principaux** :
quatre Ø11 d'axe Z aux positions (±50, ±20), et deux Ø13,5 d'axe Y aux
abscisses ±280. Elle ne dénombre pas tous les cylindres du modèle, qui comporte
aussi des perçages secondaires.

Les huit nombres nominaux établis sont : **592, 73, 52 mm** d'encombrement,
**Ø11 mm**, **100 × 40 mm** pour le motif central, **Ø13,5 mm** et **560 mm**
d'entraxe des yeux. La boîte numérique du noyau, conservée sans correction,
vaut 592,0000002 × 73,00000021004072 × 52,00000020000001 mm. L'égalité affichée
à trois décimales n'ajoute aucune tolérance de fabrication.

Ces preuves portent sur le STEP nominal F0 ; elles ne valident **aucune
annotation**, puisqu'aucun dessin n'a été obtenu. Elles ne deviennent pas des
cotes OEM mesurées. Le STEP et les fichiers source empreintés dans les essais
sont inchangés. La relecture d'archivage confirme aussi les 293 pins de la
recette v6 et le CORE retenu, sans modification de recette ou de runtime partagé.

## Limites de reproduction

Ce dossier conserve des constats traçables, pas une installation autonome.
Les scripts historiques sont copiés **sans modification** et calculent leurs
chemins à partir de l'ancienne disposition sous `work/`. Les exécuter depuis
ce bundle ne constitue pas un rejeu portable ; aucun nouvel essai n'est lancé
par cet archivage.

Une reproduction d'exécution demanderait le commit amont exact, le STEP exact
et un environnement séparé conforme aux versions et sources consignées.
`requirements-frozen.txt` contient notamment un chemin local vers Draftwright
et n'est pas un lock `pip --require-hashes`. Le rapport pip complet et les
archives de dépendances restent dans les originaux ; seule leur provenance
compacte est copiée. L'installation initiale refusait l'exigence « toutes les
dépendances en roues » : ANTLR 4.9.3 a nécessité la construction de sa roue
pure Python, sans compilation du noyau natif ni relâchement des versions.

Les délais observés décrivent ces deux exécutions concurrentes avec d'autres
travaux sur cette machine. Sans profil interne ni dessin, ils ne localisent
pas le coût et ne démontrent pas un échec universel de Draftwright. Aucun
troisième essai, nouveau dessin, lint ou adoption n'est déduit de ces archives.
