# Évidence turbocompresseur K16 (M64-ACQ-0003) — relevé du 2026-09-27

Relevé external (lane K16, read-only). Ce document consignait l'évidence locale/trouvée
en attendant la relivraison perdue en transit; les chiffres ci-dessous restent
**non revus par le programme** et ne promeuvent aucune géométrie au-delà de F0.

## Identité et données retenues

- Paire K16 identifiée par numéro de pièce : **5316-988-6735 (droit) / 5316-988-6736 (gauche)**
  (`catalog/sources/src-turbomaster-993-k16-6736-left-unit.json`, données vendeur, level C).
- Roues (compresseur/turbine) : références et données internes TurboMaster/Invasion Auto
  (`src-invasionautoproducts-993-k16-internal-data.json`) — données internes au vendeur,
  usage « reference » seulement, redistribution interdite.
- A/R turbine : **8.0** (source vendeur citée dans le registre).
- Wastegate : intégrée à la turbine (type K16), mentionnée dans la fiche.

## Ce qui manque toujours (bloqueur du jumeau turbo)

- **Carte compresseur (map pression/débit à plusieurs régimes) : absente** de tout le corpus
  local et des sources consultées → **M64-ACQ-0003 reste bloquant** pour toute simulation
  significative du circuit d'admission. Sans elle, le débit aux limites ne peut que rester
  un chiffre ponctuel (cf. conflit 1 210 vs 1 010 l/s documenté dans
  `docs/research/m64-public-engine-data-2026-09-27.md`).
- Cartes de rendement et de puissance turbine : absentes.
- Températures T3 mesurées : absentes (le dossier collecteur utilise 900 K synthétique).

## Note de méthode

Ce fichier a été écrit par le coordonnateur après la relivraison avortée de la lane
(erreur réseau) pour ne pas perdre l'évidence consignée. Les sources exactes sont les
fiches `catalog/sources/src-turbomaster-*` et `src-invasionauto*` citées plus haut ;
les niveaux de preuve restent ceux du registre (`level C vendeur`, à relire).
