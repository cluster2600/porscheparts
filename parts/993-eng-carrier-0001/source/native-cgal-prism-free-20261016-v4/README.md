# Prismes exacts — finalisation rationnelle équilibrée, version 4

Cette version conserve intégralement les booléens, l'ordre spatial, les
prismes, les interfaces, les checkpoints et les recherches de parents de
[la version 3](../native-cgal-prism-free-20261016-v3/README.md). Le commit CGAL
expérimental reste `b4e8c1887ce6a0abeb618634125e5cfcd301ce16`, sans patch amont.

Seule la finalisation change : chaque déterminant du volume est forcé en
rationnel exact avant une réduction équilibrée. Les flux de géométrie et de
parents sont fermés avant le reçu JSON, lui-même écrit puis renommé
atomiquement. Le worker conserve le code retour natif avant de lire ce reçu,
même s'il manque ou s'il est invalide. Cela évite l'arbre différé linéaire
`K::FT +=`, dont le plantage a été reproduit sur 254 624 termes dans le
[finalizer indépendant](../native-cgal-prism-finalize-20261016/README.md).
La version 3 et son refus historique ne sont pas modifiés.

```sh
python3 parts/993-eng-carrier-0001/source/native-cgal-prism-free-20261016-v4/setup.py \
  /chemin/neuf/prism-v4 --boolean-runtime /chemin/prism-v2
python3 /chemin/neuf/prism-v4/run.py prism_free ROOFS.npz \
  /chemin/neuf/prism-v4/jobs/essai-001 --second-input MASK.npz \
  --part-input PART.npz --timeout-seconds 1200
```

Le runtime version 2 explicite doit d'abord être installé par son propre
`setup.py`, avec son archive CGAL et les dépendances du bootstrap documenté.
L'installation vérifie archive, sources, en-têtes et bibliothèques ; elle
réutilise ces dépendances en lecture seule. Le nouveau binaire, ses sources et
ses dépendances sont empreintés dans un nouveau manifeste. Aucun chemin d'un
ancien dossier `work` n'est recherché implicitement.

Le témoin de prismes superposés et découpe intermédiaire donne exactement
3200 mm³. Les géométries rationnelle et float, le NPZ, les parents primaires et
le CSR complet sont byte-identiques à la version 3. Un nouveau reçu de dérive
composée vérifie cette exécution et les preuves snap/distances déjà calculées
sur ces mêmes données : 1,776e−15 mm, sous la borne témoin de 1,231e−13 mm.
Ces témoins logiciels n'admettent aucune enveloppe réelle.

Le schéma des huit faces de prisme et la portée des parents restent dans
`prism-face-schema.json`. Tous les parents contenant l'enfant entier sont
conservés, y compris les ambiguïtés ; l'absence d'un rôle ne prouve pas
l'absence d'un contact partiel. Le contrôleur d'interfaces doit conserver ses
preuves indépendantes de côté matière et de couverture.

Chaque essai garde son plan et ses critères avant le calcul. Le succès natif
ne suffit pas : snap 51 bits / 5 itérations, topologie fermée et manifold,
intersections, contacts et dérive composée sous la borne gelée restent des
gates séparées. La borne composée finale porte sur tous les sommets et
barycentres déclarés, pas sur un Hausdorff continu du snap. Les refus restent
intacts. Les calculs sont bornés à 2 CPU, 4 Gio, zéro swap, réseau nul et
600 ou 1200 s explicites.
