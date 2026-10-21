# Recherche des parents par centroïde exact — version3

Cette version conserve le booléen exact, les prismes, les interfaces et les
gardes de [la version précédente](../native-cgal-prism-free-20261016/README.md).
Le commit CGAL reste `b4e8c1887ce6a0abeb618634125e5cfcd301ce16`, non patché.
Seule la recherche des candidats parents change : tout triangle convexe
contenant les trois sommets enfant contient aussi leur centroïde exact.
L'AABB est donc interrogé par ce point au lieu du triangle entier ; le même
test exact des trois sommets suit, et **tous** les parents sont conservés.
Aucun centroïde ou sommet n'est arrondi pour cette recherche.

```sh
python3 parts/993-eng-carrier-0001/source/native-cgal-prism-free-20261016-v3/setup.py \
  /chemin/neuf/prism-v3 --boolean-runtime /chemin/prism-v2
python3 /chemin/neuf/prism-v3/run.py prism_free ROOFS.npz \
  /chemin/neuf/prism-v3/jobs/essai-001 --second-input MASK.npz \
  --part-input PART.npz --timeout-seconds 1200
```

Le runtime précédent est explicite et vérifié : binaire, sources, dépendances
compilées, archive et bibliothèques. Ses en-têtes CGAL/MPFR sont réutilisés en
lecture seule. Pour une installation depuis zéro, construire d'abord ce runtime
avec son `setup.py` versionné et l'archive au SHA documenté, puis lancer ce
second installateur. Aucun répertoire historique `work` n'est recherché.

Le booléen écrit maintenant un checkpoint exact et float **non admis** avant
la classification des parents. Le lanceur empreinte ces fichiers même si
l'audit expire ensuite. Ce checkpoint ne remplace aucun gate. Les lignes de
progression distinguent la fin du booléen et les lots de parents classifiés.

Le témoin composé a été exécuté avec cette version. Géométrie rationnelle,
géométrie float, NPZ, parents primaires et CSR complet sont byte-identiques
à la version précédente :98correspondances,22faces à parents multiples.
Le checkpoint et les sorties finales sont identiques aussi. Les reçus
snap51/5, distances exactes et contacts existants sont réutilisés sur cette
identité vérifiée, sans recalcul identique. Un nouveau reçu composé relie
l'exécution native3 à ces preuves et vérifie tous les sommets/connectivités :
borne finie totale1,776e−15 mm, sous1,231e−13 mm sur ce témoin.

La version2 réelle gauche a été refusée à1200 s pendant l'audit des parents,
après retour du booléen avant91 s ; ce refus reste intact. La version3 a son
propre plan/essai et doit passer ses contrôles complets avant admission.

Le schéma des8faces et les limites de parenté restent dans
`prism-face-schema.json`. Le CSR couvre tous les parents contenant l'enfant
entier, pas les petites faces qui n'en couvrent qu'une partie. Il ne constitue
pas une filiation causale exhaustive. L'analyse de contact conserve ses
contrôles indépendants de rôle, orientation et côté matière. Le primaire
minimum ne suffit jamais à décider un contact.

Budgets inchangés : deux CPU,4 Gio, zéro swap, réseau nul,600/1200 s explicites.
Snap51/5, borne d'origine et contrôles de topologie/contact restent inchangés.
Les licences CGAL/MPFR et tous les refus conservent leurs provenance et SHA.
