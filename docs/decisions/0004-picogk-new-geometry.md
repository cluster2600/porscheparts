# ADR 0004 — PicoGK pour la CAO générative neuve

## Statut

Accepté le 27 septembre 2026 (décision explicite du porteur de projet).

## Contexte

Le programme de jumeau complet du moteur 993 Turbo (M64/60) engage de la
géométrie nouvelle : pièces de refroidissement, volumes de refroidissement de
culasse, supports, conductus. Les chaînes existantes (build123d/CadQuery en
Python) restent la source maître des artefacts déjà produits. Le porteur a
tranché : la géométrie **nouvelle** est écrite en C# sur la chaîne voxel/SDF de
PicoGK, sans migrer l'existant.

## Décision

1. Toute géométrie créée à partir du 27 septembre 2026 dans le programme
   `M64-WHOLE-ENGINE-TWIN-0001` est implémentée en C# / PicoGK (workflow
   voxel-field, SDF implicites, booléens), et se termine par l'appel d'export
   de maillage compatible dépôt vérifié contre l'API PicoGK installée.
2. Périmètre installé et vérifié : conteneur `m64-engineering-worker`,
   .NET SDK 8.0.131, PicoGK 2.3.0 (commit `0e6cf6b6f499`, 2026-08-27),
   runtime natif `/usr/local/lib/picogk.so`. Le dotnet de l'hôte (6.0) ne
   suffit pas ; la compilation et l'exécution ont lieu dans le conteneur.
3. Les artefacts existants en Python/build123d ne sont pas migrés. Ils
   restent la référence dimensionnelle de leurs zones ; PicoGK ne remplace
   pas la vérité STEP là où elle existe déjà.
4. Les paramètres physiques (épaisseur de paroi, jeux, nombre d'aubes,
   densité de réseau, taille de voxel, résolution d'export) restent
   configurables, conformément à la charte.

## Conséquences

- Une nouvelle brique de projet .NET (`M64.csproj`, cible net8.0) est ajoutée
  au dépôt ; elle ne modifie aucune chaîne Python existante.
- La chaîne reproductible (décision 0002) reste respectée : build et exécution
  s'opèrent en ligne de commande dans le conteneur worker.
- Les niveaux de fidélité (ADR 0003) s'appliquent sans changement : une
  géométrie PicoGK est `F1_envelope` tant que ses interfaces ne sont pas
  mesurées.
