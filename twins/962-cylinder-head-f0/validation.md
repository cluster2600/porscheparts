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
branche distante vérifiée. La validation GitHub du commit
`4c76e0efbc3c220bcaddb2ca94189135c6a6fc1f` a réussi :
[run 664](https://github.com/cluster2600/porscheparts/actions/runs/38283253271).
Cette preuve appartient à ce commit, pas aux ajouts produit ultérieurs.

La PR reste un brouillon de recherche et de géométrie. Aucun merge ou
déploiement n'est autorisé par ces contrôles locaux.

## Extension au programme kit 1 000 ch

Le [programme produit](KIT_962_PROGRAMME.md) et son
[registre](kit-program.json) ajoutent la cible commerciale et la qualification
par variante. Ils ne modifient ni le générateur C#, ni les paramètres de
géométrie, ni les sources et contrats dont les empreintes sont enregistrées.
Deux tests supplémentaires vérifient les unités des calculs de cadrage et
la séparation entre objectif de puissance, compatibilité et autorisation de
fabrication. Les six tests ciblés passent avec VTK ; dans le Python système,
cinq passent et le témoin VTK reste ignoré. Les liens Markdown et le diff
sont vérifiés. La validation globale Mac ci-dessus est celle du dossier
géométrique précédent ; elle n'est pas présentée comme une exécution du
nouveau programme produit. La CI de la nouvelle révision reste à observer.

## Extension au module thermique

L'[étude thermique](THERMAL_MODULE.md) ajoute un bilan algébrique TEC et un
schéma fonctionnel SVG/PNG inspecté visuellement. Le code distingue Qfroid,
Pélectrique aux TEC, Qchaud, pertes de conversion, auxiliaires et consommation
au bus. Six tests supplémentaires vérifient conservation de l'énergie,
séparation des pertes, rejet des entrées invalides/non finies et des
dépassements numériques, CLI et liaison des exemples à la source du calcul.
Les douze tests ciblés passent avec VTK ; onze passent dans le Python système
avec un témoin VTK ignoré. Ni COP réel, charge moteur, radiateur, bus véhicule,
boîtier, commande embarquée ou bénéfice automobile ne sont qualifiés.
La référence de refroidissement indépendante des TEC reste exigée.

## Confirmation de la cible produit

Le propriétaire confirme 1 000 ch métriques au vilebrequin et une qualification
sur banc puis sur piste. Le registre et son test distinguent cette décision
des exigences encore inconnues et des autorisations conservées à `false`.
Les douze tests ciblés passent avec VTK ; les liens Markdown et le diff sont
vérifiés. Aucun nouveau calcul géométrique ou essai physique n'est effectué.
Le `make check` Mac global n'est pas réexécuté pour cette clarification.

## Fusion du programme et préparation G1

La CI du commit `e033e041f6a3d11e6905f108b2f73c3837a69c32` a réussi :
[run 672](https://github.com/cluster2600/porscheparts/actions/runs/38286252107),
y compris l'étape `make check` Linux. La PR 184 a été fusionnée sur demande
du propriétaire ; le commit de fusion est
`a2f066864a765e9ece59c960c87e60a4d9b93a9d`.
Cela ne qualifie aucune pièce physique.

La suite ajoute le dossier G1 et la qualification matière, sans modification
de géométrie. Un contrôle CSV vérifie vingt identifiants uniques, couverture
des huit interfaces du contrat M64 et champs d'observation tous vides.
Le validateur M64 existant confirme ses interfaces incomplètes et conserve
la fabrication à `false`. Les douze tests 962 passent avec VTK ; aucun lien
Markdown cassé dans les 878 fichiers examinés, diff sans erreur.

`make check` Mac est réexécuté pour cette étape : 3 794 tests en 232,037 s,
2 échecs, 26 erreurs et 229 ignorés, puis arrêt à la cible `test`. Les erreurs
restent dans SciPy/NumPy et Python 3.10 sans `hashlib.file_digest` ; les deux
échecs sont les égalités de flottants impeller/stator des modules non modifiés.
Le journal reste local : `work/962-head/make-check-metrology.log`.
Les cibles globales suivantes ne sont pas considérées exécutées. La CI de
la nouvelle révision G1 doit être observée séparément.

## G1 merge and coolant boundary diagnostic

The G1 CI of commit `1dd4f65e770481cdbc8475606be05b69387158e1` passed:
[run 677](https://github.com/cluster2600/porscheparts/actions/runs/38291189844).
PR 188 was merged at the owner's request in
`d8fed9fa5e7f96d4fe1e0af27b0a51eb9f94177e`.

The follow-up uses the original STL files, with no rerun or modification of the
generator. The [boundary report](derived/boundary-audit.json) keeps
digests, sections and classifications at the four probing distances.
The nineteen targeted tests pass with VTK. Seven new controls check
the classifications on analytic surfaces, open or disconnected
sections, invalid inputs and the refusal of an STL modified before export.
The probing plot is inspected visually. The VTP sections stay
local in `work/962-head/boundary-audit-final2/`.

The coolant/metal gaps remain present in the evidence: no CFD status,
conformal interface, wall strength or physical qualification is granted.
The strict link check passes on 880 Markdown files. The Mac
`make check` ends in failure: 3,803 tests, 2 failures, 26 errors, 232 skipped,
251.837 s. The SciPy/NumPy and `hashlib.file_digest` errors as well as the
two floating-point equalities concern the same unmodified modules; the
nineteen 962 tests are verified separately with VTK. The log stays local
in `work/962-head/make-check-boundaries.log`; the targets after `test`
are not considered executed. The CI of this new revision remains
to be observed.

## Refinement and views of the cylinder head

The CI of the previous diagnostic, commit
`427ec23e67bbed6b2a01483276a4188eb44a5102`, passed:
[run 687](https://github.com/cluster2600/porscheparts/actions/runs/38295662492).
This evidence does not validate the following additions.

Three new PicoGK exports at 0.5 mm are actually calculated with the
verified binaries, under the shared lock; only the resolution of the input
copies changes. The original inspector is reused and the new report
records separately the digests of the actual inputs executed.
The [report](derived/refinement-report.json) keeps all qualification
values at `false`. The coolant/metal gaps near the surfaces remain
observed. Three 1600 × 1200 views are inspected visually and linked to the
report by digest; the published images are identical to the inspected views.
The native exports are not recalculated when inspection/rendering is resumed.

## Envelope added after visual review

The first exterior render showed a frame, with no complete envelope.
The [enclosed-solid.json](source/enclosed-solid.json) variant and the new
generator add a continuous rounded body, then subtract coolant and gas.
These are envelope assumptions, with no measured engine interfaces.
The separate project builds against the verified PicoGK binary libraries,
because the old local source path is no longer available. Build
succeeded with no warning; native export at 0.5 mm actually executed under
the shared lock in 89.8 s. The solid body is not optimized under load.

The [report](derived/enclosed-report.json) keeps binaries and sources,
closure/orientation/connectivity of the solid, seven material probes and six
openings. The three new views are inspected visually. The virtual
cut is closed and verified on an analytic cube. The twenty-five targeted
tests pass with VTK; the Markdown links pass on 882 files.
The initial evidence and the old routing views remain intact.
The coolant/metal interface and all physical qualifications remain open.

## Photographic architecture, Qwen, LatticeLibrary and VDB

The 962 C restoration views were inspected; their license and their
lack of scale are recorded, without publishing their pixels. The
[gallery](GALLERY.md) uses the actual STL files of a new ShapeKernel
architecture, with four inclined guides and two candidate ignition wells.
Two complete invalid Qwen responses were rejected; only one verified elliptical
expression was integrated. The prompts, outputs and digests are
kept. Build of the architecture and rib projects: zero errors,
35 deprecation warnings in ShapeKernel.

The three base domains are closed/oriented and have a single component
after documented removal of degenerate triangles. The ribbed solid is
also a single component; 56 internal cell corners are inside
the base body. The two port lofts pass an independent elliptical
area check at 2%. The minimum sampled coolant/dry separation is
4.401 mm over 805,530 points: no physical thickness is qualified.
The [reports](derived/architecture-report.json) and
[VDB/rib evidence](derived/bionic-report.json) link the sources to the outputs.

LatticeLibrary builds 36 external BCC cells, with no lattice in the coolant.
Five VDB fields are read back by name. Three domains pass native equality;
1,153,186 scalar values and as many vectors pass the exact
bidirectional comparisons. These are geometric fields, with no solver.
The 32 targeted tests pass with VTK; the new images are inspected.
The classifications at the metal/coolant boundaries remain unresolved: at
0.25 mm, 1,609 probes are assigned to neither domain. Smoothing
therefore does not produce a conformal interface ready for CHT.

## Global check after integrating main

`make check` was run on
`1dc719f622811158f81bf1d36f29c0dc39942477`: **3,855 tests** in 251.879 s,
**2 failures, 26 errors, 235 skipped**. The failures concern the
impeller/stator floating-point equalities; the errors concern the numerical imports
SciPy/NumPy and `hashlib.file_digest` under Python 3.10, in modules not
modified by this study. The targets after `test` were not executed.
The full log stays local in `work/962-head/make-check-final-main.log`.
The 32 cylinder head tests pass with VTK; the separate link check passes
on 916 Markdown files. This global Mac result is not announced as green.

## Linux CI result on the translated revision

The GitHub Actions workflow "Validate catalogue",
[run 38578122965](https://github.com/cluster2600/porscheparts/actions/runs/38578122965)
(`pull_request` event, 2026-10-14), passed on
`d4a8ce4dec818ac56da09abe712b9f4b21f7323c`, including the
"Validate repository" step that runs `make check`. This is a Linux CI
software check of the repository; it does not validate the geometry,
the coolant interface or any physical property of the study.

## Flow-sized 4 L study: delivery receipt versus repository copies

The [delivery receipt](derived/flow4l/delivery-report.json) pins the 37
entries of the local archive
`work/962-flow4l/delivery-001/mezger-4l-sp95-head-study.zip`. Its entry
`documentation/FLOW4L_STUDY.md` (SHA-256 `cfbea813…9a43b25`, 6,873 bytes) is
the pre-packaging snapshot from commit `e0c6feac`. The repository copy of
[FLOW4L_STUDY.md](FLOW4L_STUDY.md) was edited afterwards, in the commit that
added the receipt (`615fd71f`), to record the rejected `snappyHexMesh` and
native tetrahedral meshes and the archive itself. It therefore no longer
matches the receipt. The archive copy is the one the receipt attests.

The other repository-resident entries were re-hashed on 2026-10-16 and match
the receipt: `MEZGER_4L_SP95.md`, the 23 source files and the seven derived
reports and views. The three STL files, the VDB and `native-fields-report.json`
exist only in the archive, which is not on this host. Reissuing the receipt
from the current documentation needs a new native packaging run on the
owner's machine; until then, neither the receipt nor its pinned documentation
copies are edited here.

## Vérifications physiques absentes

Pas de scan/CT d'un donneur 962, de métrologie, de CFD/CHT, de calcul mécanique,
de matériau qualifié, de contrôle de dépowdering, d'épreuve de pression, de
maintien des sièges/guides, de fatigue thermique ou d'essai moteur.
L'[interface-contract.json](interface-contract.json) conserve ces entrées
inconnues et les autorisations à `false`. Toute fabrication nécessite la
revue professionnelle et le plan de validation décrits dans le
[dossier](README.md#feuille-de-route-vers-un-jumeau-exploitable).
