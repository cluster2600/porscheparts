# Finalisation indépendante d'un checkpoint exact existant

Ce programme ne construit aucune géométrie et ne relance aucun booléen. Il lit
les deux checkpoints fermés, rationnel et float64, produits avant l'audit de la
[version 3](../native-cgal-prism-free-20261016-v3/README.md). Le lanceur vérifie
leurs empreintes dans le reçu d'origine, les trois entrées, les sources,
l'installation et les dépendances. L'ancien refus reste inchangé.

La finalisation refait la recherche des **tous** parents géométriques par
centroïde exact puis containment des trois sommets, les contrôles globaux
d'auto-intersection et de collinéarité, le volume signé rationnel et la mesure
de conversion exact→float. Les coordonnées et indices sont recopiés tels quels.
Les parents restent des témoins de containment de l'enfant entier : ils ne
constituent pas une filiation causale exhaustive et n'excluent aucun contact
partiel avec une autre face. Le schéma des huit triangles de chaque prisme et
les rôles sont conservés dans `prism-face-schema.json`.

Chaque déterminant du volume est immédiatement évalué dans le type rationnel
exact, puis additionné par réduction équilibrée. Aucun arbre différé linéaire
`K::FT +=` n'est créé. Les flux de parents sont fermés avant la sérialisation
du reçu, écrit dans un fichier temporaire puis renommé. Le worker enregistre
le code retour natif avant de lire le JSON, même si ce dernier manque.

Le petit témoin de finalisation donne exactement 3200 mm³ : les fichiers de
géométrie et les 98 parents sont byte-identiques à la version 3, et tous les
tableaux NPZ sont identiques. L'ordre des membres du conteneur ZIP diffère ;
son SHA est donc différent et cette équivalence est documentée explicitement.
Ses quatre triangles dégénérés après export float restent refusés au stade
brut ; les preuves snap/distances/contacts déjà exécutées sur les mêmes
tableaux sont conservées, sans rebaptiser leurs reçus.

Un témoin logiciel séparé, `witness_lazy_volume.py`, a reproduit un SIGSEGV
avec 254 624 additions différées de 1/3 ; le calcul rationnel équilibré renvoie
exactement 254624/3. Le signal natif de l'ancien job réel n'avait pas été
enregistré : le témoin soutient une cause probable, sans réécrire ce fait.
Voir aussi le cas primaire [CGAL issue 1118](https://github.com/CGAL/cgal/issues/1118).

## Installation Linux explicite

Le prérequis est le runtime prismes version 2, installé par son propre
`setup.py` versionné avec l'archive CGAL épinglée et les prérequis du bootstrap.
Son archive, son manifeste, ses sources, ses bibliothèques et ses en-têtes sont
vérifiés. Il n'est ni modifié ni recherché dans un ancien dossier `work`.

```sh
python3 parts/993-eng-carrier-0001/source/native-cgal-prism-finalize-20261016/setup.py \
  /chemin/neuf/prism-finalize --boolean-runtime /chemin/prism-v2
python3 /chemin/neuf/prism-finalize/run.py /chemin/job-origine \
  /chemin/neuf/prism-finalize/jobs/finalisation-001 \
  --roofs /chemin/roofs.npz --mask /chemin/mask.npz --part /chemin/part.npz
```

Le manifeste installé épingle les sources, le binaire, les en-têtes compilés,
les bibliothèques et Python/libigl. CGAL reste au commit expérimental
`b4e8c1887ce6a0abeb618634125e5cfcd301ce16` ; aucun code amont n'est patché.
Les licences et la provenance sont copiées dans ce dossier. L'installateur ne
télécharge rien et réutilise les dépendances explicites en lecture seule.

Le calcul reste borné à 2 CPU, 4 Gio, zéro swap, 600 s et réseau nul. La compilation
a les mêmes limites. Le job ne peut écrire que dans son nouveau dossier.

## Admission séparée

Un succès de cette finalisation permet seulement de poursuivre vers le snap
CGAL 6.1.3, 51 bits / 5 itérations, les distances exactes et l'adjudication des
contacts. La topologie manifold stricte et tous les contrôles d'origine restent
nécessaires. Le reçu conserve `admitted:false` à ce stade.

`audit_composed_drift.py` relie ensuite les reçus native/snap/distance et le
seuil d'origine. Il vérifie indépendamment toutes les conversions et indices,
puis compare rationnellement `sqrt(D²)+sqrt(E²)` à cette borne sans la relever.
La portée finale est l'ensemble fini déclaré de tous les sommets et
barycentres exacts ; ce n'est pas un certificat de Hausdorff continu du snap.
Les refus précédents et le checkpoint non admis sont conservés intégralement.
