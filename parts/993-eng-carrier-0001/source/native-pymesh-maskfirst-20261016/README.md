# Masque d'abord, cutter local, arbre exact unique

Cette variante calcule `(chain ∩ mask) \ (part ∩ B)` dans un seul CSGTree
Epeck. La boîte B strictement englobante de chain reprend exactement la
construction `nextafter` et les gardes de la version clip précédente.
L'identité avec `(chain ∩ mask) \ part` découle de `chain ⊂ B`.
Aucun résultat intermédiaire n'est converti en doubles.

```sh
python3 parts/993-eng-carrier-0001/source/native-pymesh-maskfirst-20261016/setup.py \
  /chemin/neuf/maskfirst --pymesh-runtime /chemin/pymesh
python3 /chemin/neuf/maskfirst/run.py CHAIN.npz MASK.npz PART.npz \
  /chemin/neuf/maskfirst/jobs/essai-001 --timeout-seconds 1200
```

Les feuilles ont l'ordre `chain, mask, part, clip_bbox`. Les attributs source
font référence à cet ordre, enregistré avec les nombres de faces. Le rootfs
PyMesh existant est explicite, vérifié et utilisé en lecture seule. Image,
modules Python, bibliothèques et sources sont empreintés avant/après. Budgets
explicites 600 ou 1 200 s, deux CPU, 4 Gio, sans swap et sans réseau.

Le témoin exécuté contient deux prismes superposés de hauteur 10 et 20 mm,
puis une soustraction Z8–Z12. Après export, snap51/5 et mesure exacte :
3 200 mm³, deux composants fermés/manifold/orientés, présence Z4/Z16 et
absence Z9/Z10/Z11. Les 15 alertes libigl sont des contacts ponctuels dans
le simplexe déjà partagé, vérifiés par le classifieur rationnel épinglé ;
aucune intersection supplémentaire. Les résultats bruts restent conservés.

Ce témoin établit le comportement logiciel de cette expression. Chaque vraie
sortie doit encore passer ses propres contrôles exacts, topologiques et de
dérive. Cette variante ne modifie ni le snap ni sa borne.

Moteur/licences : même image `pymesh/pymesh` et même binaire natif que
`native-pymesh-20261016`, identifiants vérifiés par le bootstrap. Le commit
C++ installé que l'image n'expose pas reste inconnu.
