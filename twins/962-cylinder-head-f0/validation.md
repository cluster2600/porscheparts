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

## Fusion G1 et diagnostic des frontières d'eau

La CI G1 du commit `1dd4f65e770481cdbc8475606be05b69387158e1` a réussi :
[run 677](https://github.com/cluster2600/porscheparts/actions/runs/38291189844).
La PR 188 est fusionnée sur demande du propriétaire dans
`d8fed9fa5e7f96d4fe1e0af27b0a51eb9f94177e`.

La suite utilise les STL originaux, sans réexécution ni modification du
générateur. Le [rapport de frontières](derived/boundary-audit.json) conserve
empreintes, sections et classifications aux quatre distances de sondage.
Les dix-neuf tests ciblés passent avec VTK. Sept nouveaux témoins vérifient
les classifications sur des surfaces analytiques, les sections ouvertes ou
déconnectées, les entrées invalides et le refus d'un STL modifié avant export.
Le graphe de sondage est inspecté visuellement. Les sections VTP restent
locales dans `work/962-head/boundary-audit-final2/`.

Les écarts eau/métal restent présents dans la preuve : aucun statut de CFD,
interface conforme, tenue de paroi ou qualification physique n'est accordé.
Le contrôle strict des liens passe sur 880 fichiers Markdown. Le `make check`
Mac termine en échec : 3 803 tests, 2 échecs, 26 erreurs, 232 ignorés,
251,837 s. Les erreurs SciPy/NumPy et `hashlib.file_digest` ainsi que les
deux égalités de flottants concernent les mêmes modules non modifiés ; les
dix-neuf tests 962 sont vérifiés séparément avec VTK. Le journal reste local
dans `work/962-head/make-check-boundaries.log` ; les cibles après `test`
ne sont pas considérées exécutées. La CI de cette nouvelle révision reste
à observer.

## Vérifications physiques absentes

Pas de scan/CT d'un donneur 962, de métrologie, de CFD/CHT, de calcul mécanique,
de matériau qualifié, de contrôle de dépowdering, d'épreuve de pression, de
maintien des sièges/guides, de fatigue thermique ou d'essai moteur.
L'[interface-contract.json](interface-contract.json) conserve ces entrées
inconnues et les autorisations à `false`. Toute fabrication nécessite la
revue professionnelle et le plan de validation décrits dans le
[dossier](README.md#feuille-de-route-vers-un-jumeau-exploitable).
