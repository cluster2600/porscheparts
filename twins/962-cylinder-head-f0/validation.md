# Vérification F0 — 12 octobre 2026

## Vérifications locales

- Compilation du projet C# existant : réussite, zéro erreur. Deux avertissements
  SourceLink concernent l'archive locale PicoGK sans métadonnées Git.
- Trois générations natives PicoGK 2.3.0 / runtime 26.2, voxel de 0,75 mm.
  Le solide final mesure 160 × 160 × 90 mm et contient environ 353,19 cm³.
  Ce volume géométrique ne constitue pas une masse de pièce qualifiée.
- Inspection indépendante des trois STL : surfaces fermées, orientations
  cohérentes, une composante par volume. Suppression limitée aux triangles
  exactement dégénérés, avec nombre conservé dans le rapport.
- 197 322 sondes sur le volume d'eau, écart signé minimal aux volumes secs
  **3,598 mm**. Ce minimum échantillonné ne certifie pas une paroi minimale
  ni l'étanchéité. Six sondes vérifient les quatre réservations de guides et
  les deux réservations de bougies.
- Quatre tests ciblés passent dans l'environnement VTK ; dans le Python
  système, trois passent et le témoin VTK est ignoré faute de bibliothèque.
- Cinq entrées invalides rejetées sans STL : statut qualifié, cote déclarée
  publiée, mode d'export fractionnaire, peau trop fine et voxel non fini.
- Liens Markdown stricts : zéro lien cassé.
- Aperçu final inspecté visuellement : volumes visibles sans coupe du cadre ;
  la réservation de chambre située sous le plan de feu est masquée dans
  l'aperçu. Les meshes d'inspection conservent le volume sec complet.

Le premier candidat est rejeté pour intersection du collecteur de retour et
des passages de gaz, avec un écart signé de −7,858 mm. Il reste local sous
`work/962-head/native/`. Le retour final est surélevé et les prolongements
inutiles de la distribution supprimés. Les STL finaux sont dans
`work/962-head/delivery/` ; les empreintes et mesures sont versionnées dans
[study-report.json](derived/study-report.json).

Le [registre runtime](derived/runtime-provenance.json) garde les empreintes
des binaires réellement utilisés. L'archive PicoGK locale n'a pas de Git :
son rattachement au commit déclaré dans `sources.lock` n'a pas été revérifié
indépendamment pendant cette livraison. La licence Apache-2.0 a été lue.

## Vérifications du dépôt

`make check` a été exécuté sur la livraison finale : **3 764 tests**,
**2 échecs, 26 erreurs et 223 ignorés**, en 242,6 s. Les trois tests F0
compatibles avec le Python système passent ; son témoin VTK est ignoré et
passe séparément dans l'environnement VTK. Les problèmes globaux concernent
des modules non modifiés : incompatibilité NumPy/SciPy, Python 3.10 sans
`hashlib.file_digest` pour Qwen, et égalités de flottants trop strictes des
études d'impeller/stator sur ce Mac. Le journal local est
`work/962-head/make-check-final.log`. Les cibles après `test` ne sont pas
considérées exécutées ; le statut global reste en échec.

[PR brouillon 184](https://github.com/cluster2600/porscheparts/pull/184) créée et
branche distante vérifiée. La validation GitHub est encore en cours au
moment de cette livraison ; aucun succès CI n'est annoncé.

La PR reste un brouillon de recherche et de géométrie. Aucun merge ou
déploiement n'est autorisé par ces contrôles locaux.

## Vérifications physiques absentes

Pas de scan/CT d'un donneur 962, de métrologie, de CFD/CHT, de calcul mécanique,
de matériau qualifié, de contrôle de dépowdering, d'épreuve de pression, de
maintien des sièges/guides, de fatigue thermique ou d'essai moteur.
L'[interface-contract.json](interface-contract.json) conserve ces entrées
inconnues et les autorisations à `false`. Toute fabrication nécessite la
revue professionnelle et le plan de validation décrits dans le
[dossier](README.md#feuille-de-route-vers-un-jumeau-exploitable).
