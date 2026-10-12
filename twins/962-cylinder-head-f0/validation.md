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

## Raffinement et vues de la culasse

La CI du diagnostic précédent, commit
`427ec23e67bbed6b2a01483276a4188eb44a5102`, a réussi :
[run 687](https://github.com/cluster2600/porscheparts/actions/runs/38295662492).
Cette preuve ne valide pas les ajouts suivants.

Trois nouveaux exports PicoGK à 0,5 mm sont réellement calculés avec les
binaires vérifiés, sous le verrou commun ; seule la résolution des copies
d'entrées change. L'inspecteur original est réutilisé et le nouveau rapport
enregistre séparément les empreintes des véritables entrées exécutées.
Le [rapport](derived/refinement-report.json) conserve toutes les valeurs
de qualification à `false`. Les écarts eau/métal proches des surfaces restent
observés. Trois vues 1600 × 1200 sont inspectées visuellement et liées au
rapport par empreinte ; les images publiées sont identiques aux vues inspectées.
Les exports natifs ne sont pas recalculés lors des reprises d'inspection/rendu.

## Enveloppe ajoutée après revue visuelle

Le premier rendu extérieur présentait une charpente, sans enveloppe complète.
La variante [enclosed-solid.json](source/enclosed-solid.json) et le nouveau
générateur ajoutent un corps continu arrondi, puis soustraient eau et gaz.
Ce sont des hypothèses d'enveloppe, sans interfaces de moteur mesurées.
Le projet séparé compile contre les bibliothèques binaires PicoGK vérifiées,
car l'ancien chemin local de sources n'est plus disponible. Compilation
réussie sans avertissement ; export natif à 0,5 mm réellement exécuté sous
le verrou commun en 89,8 s. Le corps massif n'est pas optimisé sous charges.

Le [rapport](derived/enclosed-report.json) conserve binaires et sources,
fermeture/orientation/connexité du solide, sept sondes de matière et six
ouvertures. Les trois nouvelles vues sont inspectées visuellement. La coupe
virtuelle est fermée et vérifiée sur un cube analytique. Les vingt-cinq tests
ciblés passent avec VTK ; les liens Markdown passent sur 882 fichiers.
Les preuves initiales et les anciennes vues de routage restent intactes.
L'interface eau/métal et toutes les qualifications physiques restent ouvertes.

## Architecture photographique, Qwen, LatticeLibrary et VDB

Les vues de restauration de 962 C ont été inspectées ; leur licence et leur
absence d'échelle sont enregistrées, sans publier leurs pixels. La
[galerie](GALLERY.md) utilise les vrais STL d'une nouvelle architecture
ShapeKernel, avec quatre guides inclinés et deux puits d'allumage candidats.
Deux réponses Qwen complètes invalides ont été rejetées ; seule une expression
elliptique vérifiée a été intégrée. Les prompts, sorties et empreintes sont
conservés. Compilation des projets architecture et nervures : zéro erreur,
35 avertissements d'obsolescence dans ShapeKernel.

Les trois domaines de base sont fermés/orientés et ont une seule composante
après retrait documenté des triangles dégénérés. Le solide à nervures est
également d'une seule composante ; 56 coins internes de cellules sont dans
le corps de base. Les deux lofts de ports passent un contrôle indépendant
d'aire elliptique à 2 %. La séparation eau/sec minimale échantillonnée est
4,401 mm sur 805 530 points : aucune épaisseur physique n'est qualifiée.
Les [rapports](derived/architecture-report.json) et
[preuves VDB/nervures](derived/bionic-report.json) lient les sources aux sorties.

LatticeLibrary construit 36 cellules BCC externes, sans treillis dans l'eau.
Cinq champs VDB sont relus par nom. Trois domaines passent l'égalité native ;
1 153 186 valeurs scalaires et autant de vecteurs passent les comparaisons
exactes bidirectionnelles. Ce sont des champs géométriques, sans solveur.
Les 32 tests ciblés passent avec VTK ; les nouvelles images sont inspectées.
Les classifications aux frontières métal/eau restent non résolues : à
0,25 mm, 1 609 sondes ne sont attribuées à aucun des deux domaines. Le lissage
ne produit donc pas une interface conforme prête pour CHT.

## Contrôle global après intégration de main

`make check` a été exécuté sur
`1dc719f622811158f81bf1d36f29c0dc39942477` : **3 855 tests** en 251,879 s,
**2 échecs, 26 erreurs, 235 ignorés**. Les échecs concernent les égalités de
flottants impeller/stator ; les erreurs concernent les imports numériques
SciPy/NumPy et `hashlib.file_digest` sous Python 3.10, dans des modules non
modifiés par cette étude. Les cibles après `test` n'ont pas été exécutées.
Le log complet reste local dans `work/962-head/make-check-final-main.log`.
Les 32 tests culasse passent avec VTK ; le contrôle séparé des liens passe
sur 916 Markdown. Ce résultat global Mac n'est pas annoncé comme vert.

## Vérifications physiques absentes

Pas de scan/CT d'un donneur 962, de métrologie, de CFD/CHT, de calcul mécanique,
de matériau qualifié, de contrôle de dépowdering, d'épreuve de pression, de
maintien des sièges/guides, de fatigue thermique ou d'essai moteur.
L'[interface-contract.json](interface-contract.json) conserve ces entrées
inconnues et les autorisations à `false`. Toute fabrication nécessite la
revue professionnelle et le plan de validation décrits dans le
[dossier](README.md#feuille-de-route-vers-un-jumeau-exploitable).
