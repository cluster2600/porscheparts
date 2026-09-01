# Assemblages moteur Omniverse F0

Ce dossier compose les géométries disponibles en scènes OpenUSD légères sans
inventer une compatibilité mécanique. Les scans et les USD générés restent sous
`work/` et hors Git ; seuls la configuration, le générateur et les rapports de
méthode sont versionnés.

## Scènes

- `917-engine-assembly-f0.usda` charge le scan 917 en `payload`. À ce stade le
  scan reste un maillage unique : la scène prépare sa future décomposition,
  mais ne prétend pas déjà contenir un carter, des cylindres ou des accessoires
  indépendants.
- `993-935-valvetrain-test-rig-f0.usda` garde la culasse 935 dans un banc de
  comparaison séparé et référence les trois soupapes 993 F1. Chaque soupape
  expose `liftStudy` à 0, 2, 5 et 10 mm et `materialStudy` pour les variantes
  documentaires acier, Ti-6Al-4V et INCONEL 751.
- `engine-research-overview-f0.usda` montre les deux scènes côte à côte. Ce
  fichier n'est pas l'assemblage d'un seul moteur.

Les positions de soupapes sont un éclaté de présentation. Elles ne représentent
pas les axes des sièges, encore inconnus. Les matériaux utilisent seulement
`UsdPreviewSurface` et des métadonnées d'étude : aucune loi thermique,
élastoplastique, de fatigue ou de contact n'est assignée.

## Génération reproductible

L'image est épinglée par digest et a été construite sur GitHub avant exécution :

```bash
twins/omniverse-engine-assembly/run_pipeline.sh
```

La commande convertit les trois STEP avec `usd-convert-cad`, puis génère les
scènes avec OpenUSD. Aucun secret NVIDIA ni service Content Agents n'est requis
pour ce jalon déterministe.

Le rendu GPU est une vérification séparée. Comme les scènes utilisent des
références et payloads locaux, la copie temporaire envoyée à OVRTX doit être
aplatie si le paquet de rendu ne transporte pas ses dépendances. Cette opération
ne modifie jamais les scènes sources. Toujours activer l'inspection de pixels et
refuser un PNG uniforme. Le rapport d'exécution est conservé dans
[`../../docs/reports/omniverse-engine-assembly-f0-2026-09-01.md`](../../docs/reports/omniverse-engine-assembly-f0-2026-09-01.md).

## Étapes suivantes

1. segmenter le scan 917 en composants traçables sans modifier le brut ;
2. mesurer des datums physiques et confirmer l'échelle ;
3. créer les vrais axes de sièges et guides sur une culasse cible identifiée ;
4. remplacer les propriétés d'affichage par des cartes matière dépendantes de
   la température et du procédé ;
5. ajouter contacts, joints, collisions et cas de charge seulement après preuve
   des interfaces ;
6. relancer Material Agent puis Physics Agent lorsque l'accès NIM est valide,
   avant toute conformance SimReady finale.
