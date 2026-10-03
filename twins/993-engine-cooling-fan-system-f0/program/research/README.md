# Recherche documentaire 911 / 935 / 993

[Programme ventilateur](../../README.md) · [Synthèse en français](SYNTHESIS.md) · [Index complet](source-index.json) · [Règles d'intégration](INTEGRATION.md)

Les quatre lots livrés le 3 octobre 2026 sont intégrés : **20 fichiers originaux,
140 fiches sources et 130 groupes d'URL**. La couverture est limitée aux pages
et requêtes consultées. Les 130 groupes ne sont pas 130 mesures indépendantes :
traductions, copies et témoignages peuvent reprendre une même origine. Aucune
publication ne valide le modèle du projet, l'identité 935/993 du scan ou une
pièce à fabriquer.

## Accès aux quatre lots

| Lot | Rapport et limites | Données complètes | Couverture livrée |
|---|---|---|---|
| OEM / histoire | [Rapport](corpus/oem/research_report.md) | [Registre](corpus/oem/oem_research.json), [sources](corpus/oem/sources.json), [paramètres CSV](corpus/oem/oem_parameters.csv) | 32 sources, 114 records ; PET, variantes, conditions historiques |
| Aftermarket / fabricants | [Rapport](corpus/aftermarket/aftermarket_fan_supplier_review.md), [requêtes et limites](corpus/aftermarket/aftermarket_search_log.json) | [Catalogue](corpus/aftermarket/aftermarket_catalog.json), [85 assertions quantitatives CSV](corpus/aftermarket/aftermarket_parameters.csv), [sources CSV](corpus/aftermarket/aftermarket_source_manifest.csv), [produits CSV](corpus/aftermarket/aftermarket_products.csv) | 44 sources, 28 produits ; rotor, moyeu, carter et système complet séparés |
| Forums multilingues | [Rapport](corpus/forums/multilingual_forum_research.md), [couverture et lacunes](corpus/forums/coverage_and_gaps.md) | [Corpus](corpus/forums/forum_corpus.json), [sources CSV](corpus/forums/forum_sources.csv), [assertions CSV](corpus/forums/forum_claims.csv), [9 points de banc rapportés](corpus/forums/reported_bench_series.csv) | 36 sources, 45 assertions ; filiation et axes de régime parfois inconnus |
| Géométrie / performance | [Notes](corpus/geometry/engineering-notes.md), [mesures à obtenir](corpus/geometry/measurement-checklist.md) | [Preuves](corpus/geometry/evidence.json), [contrat de 104 paramètres](corpus/geometry/parameter-contract.json) | 28 sources, 22 assertions ; neuf grandeurs calculées et sept portes d'acceptation |

Les rapports originaux en anglais sont conservés à l'identique pour leur
traçabilité. La synthèse et les instructions d'intégration sont en français.
Aucun plan, photographie, manuel, fichier CAO ou scan de tiers n'est réédité
ici. Le [manifeste d'import](corpus/import-manifest.json) conserve le SHA-256
du transfert et de chaque texte original.

## Traçabilité et déduplication

L'[index commun](source-index.json) conserve chaque identifiant source d'origine,
son lot, son fichier et son pointeur JSON ou sa position CSV. Les identifiants
`AF-P###` et `OEM-R###` ajoutés par l'index désignent des lignes originelles sans
identifiant ; ils ne remplacent pas leur contenu. La normalisation groupe les
URL identiques et les ancres de page d'un même PDF, sans fusionner éditions,
variantes, conditions ou conclusions. La filiation déclarée dans les lots
reste nécessaire pour reconnaître les autres copies.

PorscheFanatics et les pages du projet sont signalées comme non indépendantes.
Les autres liens peuvent être indépendants du projet sans être une mesure
primaire ni une corroboration entre eux. Les états d'accès, locators, droits,
incertitudes et contradictions restent dans les records originaux.

Le [registre préliminaire](dossier.json) conserve la première tranche de huit
sources et ses hypothèses historiques ; **il ne représente pas le corpus
complet**. L'index complet et les quatre lots sont les références de recherche.
Le catalogue `catalog/parts/*.json` demeure la source de vérité des pièces.
Aucun paramètre documentaire n'est automatiquement promu dans la géométrie,
le maillage, les conditions aux limites ou les propriétés matière.

## Contrôles reproductibles

```sh
make fan-program-check
python3 twins/993-engine-cooling-fan-system-f0/source/build_research_index.py --check
python3 twins/993-engine-cooling-fan-system-f0/source/check_research_registry.py
```

Ces contrôles vérifient les hashes des vingt originaux, les références source
de tous les records indexés et l'absence de promotion en validation
d'ingénierie. Pour régénérer uniquement l'index après un import documenté,
exécuter `build_research_index.py` sans `--check` ; préserver les originaux.
