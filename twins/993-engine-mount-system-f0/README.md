# Supports moteur bioniques 993 — étude PicoGK F0

Ce dossier ajoute une **console centrale** et un **boîtier de support moteur**
paramétriques au travail déjà commencé sur la traverse Turbo. Il représente
séparément l'enveloppe souple du support : aucun bloc métallique monolithique
n'est présenté comme un silentbloc fonctionnel.

![Vue des triangles réellement exportés ; géométries hypothétiques et pose éclatée](media/engine-mount-study.png)

## Pièces et variantes

| Référence | Rôle | Traitement |
| --- | --- | --- |
| 993 115 021 53 | Traverse Turbo, PET 17 | R9 et ses preuves conservés hors de cette scène |
| 993 115 103 52 | Console centrale, PET 18 | Squelette à quatre racines, deux troncs et couronne courbe |
| 993 375 049 05, quantité 2 | Supports moteur, PET 21 | Cage ramifiée et enveloppe à six lobes distincte |
| 993 115 021 90 | Traverse Carrera/Carrera 4/S/4S | Identité déjà relevée ; géométrie non produite ici |
| 993 115 021 41 | Traverse RS | Identité déjà relevée ; géométrie non produite ici |

L'identité Turbo et les quantités viennent des
[exigences PET relues](../../parts/993-eng-carrier-0001/source/pet-redo/requirements.json).
Les deux autres traverses sont des variantes distinctes, pas des répliques
automatiques du modèle Turbo. Aucun changement de suffixe n'est une preuve de
compatibilité dimensionnelle.

## Ce qui est intégré

Le générateur réutilise le noyau PicoGK 2.3.0 et les courbes et implicites du
dépôt. **Toutes les nouvelles formes sont bioniques** :

- La console est un squelette ouvert. Quatre collerettes se ramifient en deux
  troncs courbes et une couronne, avec des sections progressives et des jonctions
  adoucies. Ses quatre perçages restent des positions hypothétiques.
- Le support est une cage ouverte à six branches courbes et quatre racines
  bifurquées depuis deux collerettes côté caisse. Les couronnes circulaires
  délimitent un volume d'accueil hypothétique ; il n'y a pas de coupelle pleine.
- L'enveloppe souple séparée présente une taille étranglée et six lobes.
  Son mécanisme interne, sa matière, sa raideur et son amortissement restent inconnus.

« Bionique » décrit ici une morphologie inspirée des ramifications du vivant,
**pas une optimisation topologique ou mécanique validée**. Aucun solveur n'a
justifié la répartition de matière. Les anciennes plaques, montants, coupelle
pleine et traverse F1 rectiligne ne figurent plus dans les exports de cette famille.
Les surfaces locales des collerettes autour des perçages restent planes pour
représenter des interfaces d'étude ; elles ne constituent pas une plaque porteuse.

L'échangeur HelixHeatX, les gyroïdes et les modèles d'impellers ne sont pas
incorporés au chemin de charge. Ils n'apportent pas de justification mécanique
à ce support. Aucun code propriétaire Noyron ou dessin OEM n'est copié.

Les deux nouvelles pièces sont enregistrées dans les fiches catalogue
[console](../../catalog/parts/993-eng-bracket-0001.json) et
[support](../../catalog/parts/993-eng-mounting-0001.json), statut `concept`.
Le maître partagé [C#](../../parts/picogk-catalog/engine/EngineMounts.cs) et les
trois [jeux de paramètres](source/) restent éditables.

## Contrôle et données manquantes

Le [contrat indépendant](interface-contract.json) conserve les centres,
axes, diamètres, faces, datums, tolérances et preuves de mesure inconnus à
`null`. Le nombre de fixations côté moteur de la console est également inconnu.
Le chemin de charge est qualitatif : moteur → console → quatre fixations de
traverse → traverse → deux supports → quatre fixations caisse.

La génération normale est bloquée ; `--shape-study` est obligatoire pour
l'exercice incomplet. Cet indicateur n'autorise jamais la fabrication.
Le [rapport](derived/study-report.json) lie entrées, exports natifs et exports
retenus par SHA-256. Seules les faces d'aire **exactement nulle** sont retirées.
Les STL natifs sont conservés sous `derived/native/`, puis un contrôle indépendant
vérifie arêtes fermées, orientation cohérente, volume positif et composante unique.
Ce contrôle ne détecte pas toutes les auto-intersections et ne prouve ni montage,
ni résistance, ni tenue en fatigue.

La [scène OpenUSD](derived/assembly.usda) utilise des millimètres et une
**pose éclatée illustrative**, avec cinq instances : console, deux cages et deux
enveloppes souples. Elle ne définit pas le placement réel sur une 993. La traverse
R9 demeure dans son dossier d'origine ; aucun modèle rectiligne archivé n'est
substitué à cette traverse dans la scène bionique.

La densité du runner est réglée à zéro pour désactiver son estimation :
sa sortie « masse 0 » n'est **pas** une masse physique. Aucun matériau n'est
sélectionné ou qualifié par cette étude.

## Vérifications de la révision bionique

Les exports doivent passer le contrôle indépendant des trois maillages et de
leurs empreintes. Les tests de géométrie contrôlent aussi les évidements qui
remplacent la plaque et la paroi pleine, les perçages et l'étranglement à six
lobes. Ce contrôle porte sur les formes produites, pas sur leurs performances.

La compilation C# et les trois générations natives passent. Les dix tests de
cette famille et cinq cas natifs invalides rejetés sans STL ont été vérifiés ;
la scène a été relue avec OpenUSD 26.5. La suite Python sous Linux arm64 passe
sans échec : 3 605 tests, dont 187 ignorés pour dépendances optionnelles. Le
`make check` global s'arrête ensuite à `917-manufacturing-f37-lpbf-audit-check`,
car Docker est absent du conteneur de validation. Les cibles globales suivantes
ne sont pas confirmées ; aucune validation physique ni acceptation de
fabrication n'est acquise.

## Reproduire

Construire le projet existant avec le checkout PicoGK épinglé par
[sources.lock](../../containers/m64-leap71/sources.lock) :

```sh
dotnet build parts/picogk-catalog/engine/Engine.csproj \
  -p:UpstreamRoot=/chemin/vers/upstream -o work/engine-mounts/bin
# Installer les bibliothèques natives de la même révision dans ce dossier.
python3 twins/993-engine-mount-system-f0/source/build_study.py \
  --shape-study --engine-dll work/engine-mounts/bin/Engine.dll \
  --output-dir work/engine-mounts/new-run
make engine-mount-study-check
```

La sortie doit être nouvelle. Une exécution interrompue ou rejetée ne possède
pas de `study-report.json` de complétion. La vérification des fichiers retenus
et les tests Python ne nécessitent pas le runtime PicoGK.

## Prochaine porte d'ingénierie

1. Mesurer ensemble traverse, console et supports de la variante exacte ;
   établir les interfaces côté moteur et caisse.
2. Mesurer les caractéristiques des supports souples, puis déterminer les
   charges, précharges, contacts et mouvements admissibles.
3. Reprendre les formes autour de ces données et les faire inspecter
   indépendamment avant calcul convergé, fatigue et revue professionnelle.
4. Sélectionner un matériau et un procédé qualifiés ; définir le plan de
   validation physique avant tout montage ou fabrication fonctionnelle.
