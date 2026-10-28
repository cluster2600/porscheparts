# Restauration réelle de trois archives logicielles

Cette capsule conserve les preuves de trois expériences exécutées le
17 octobre 2026 : chargement de l’archive CalculiX, restauration du rootfs
PyMesh et compilation de l’archive source CGAL expérimentale b4e8.
Les originaux sous `work/` sont conservés. Chaque copie documentaire est liée
à son chemin d’origine et à son SHA256 dans [manifest.json](manifest.json).

| Expérience réelle | Architecture | Retours et résultats | Durée totale observée |
|---|---|---|---:|
| CalculiX 2.21 | Linux ARM64, Docker local | Chargement 0 ; version 201 conservée ; petit solveur 0 ; huit nœuds à 300,5 K puis 301 K |17,086 s|
| PyMesh 0.3 | Linux x86_64, Kali1 | Restauration0 et smoke 0 ; union des prismes 4000 mm³ ; topologie fermée orientée |20,541 s|
| CGAL b4e8 | Linux x86_64, Kali1 | Extraction/configuration/compilation/smoke 0 ; volumes rationnels 4000/2000/3200 mm³ |38,526 s|

Les reçus complets sont [CalculiX](ccx/execution-receipt.json),
[PyMesh](pymesh/execution-receipt.json) et
[CGAL b4e8](cgal-b4e8/execution-receipt.json). Ils conservent commandes, retours
réels, empreintes, ressources et nettoyage. Les JSON de selfcheck et le
[selfcheck CGAL](cgal-b4e8/selfcheck.py) sont des contrôles supplémentaires ;
ils ne remplacent pas les exécutions natives.

## Ce qui a été vérifié

- **CalculiX :** l’archive OCI locale a été acceptée par Docker. L’image c977
  était déjà présente ; cette expérience ne revendique pas un daemon vierge.
  Image, architecture et tags préexistants sont restés identiques. Deux
  conteneurs neufs possédés ont été supprimés. Le vrai retour 201 de `ccx -v`
  reste 201. Le petit témoin C3D8 a retourné 0 ; les huit températures sont
 300,5 K à 0,005 s et 301 K à 0,01 s, selon les critères de sa
  [fixture historique](preparation/fixture/contract.json).
- **PyMesh :** le rootfs exact a été extrait dans un préfixe neuf. Python 3.6.11,
  NumPy 1.19.0, PyMesh 0.3 et le binaire natif 17cd ont été attestés. Les 8 346
  fichiers du runtime et 3 077 liens ont été vérifiés avant/après le smoke.
  L’union connue a produit 4000 mm³, sans arête ouverte, arête nonmanifold,
  incohérence d’orientation ou sommet nonmanifold. Les deux scopes sont fermés.
- **CGAL :** l’archive b4e8 identique à celle livrée a été extraite en 17 487
  fichiers, puis l’adaptateur existant a été recompilé à un seul CPU avec
  `-O1` et assertions conservées. Les trois seuls témoins binaires existants
  passent : union 4000, intersection 2000 et différence 3200 mm³. Volumes
  rationnels exacts, filiation complète, topologie et contrôles exacts avant
  et après conversion sont conservés. Les quatre scopes sont fermés. Aucun
  témoin `self_union` n’a été relancé ou promu.

Les phases natives sont séquentielles et sans réseau. CalculiX et CGAL ont
un plafond de 6 Gio ; PyMesh a été limité à 2 Gio pendant le calcul global voisin.
Chaque phase a un CPU, aucun swap supplémentaire et un thread natif. Les
plans et reçus précisent les délais et réserves de nettoyage. Ces limites
de groupe/conteneur ne constituent pas une mesure du RSS maximal.

## Portée hors réseau

Les restaurations ont réutilisé des archives locales déjà disponibles, sans
téléchargement. CalculiX dépend du Docker existant et de son cache déclaré.
PyMesh s’appuie sur le runtime embarqué dans son rootfs et sur le sandbox
Linux installé. CGAL b4e8 dépend du compilateur, Boost/GMP/MPFR et du runtime
NumPy/libigl préexistants sur Kali ; ces fichiers ont été attestés en lecture
seule, et non réinstallés sur une machine vierge.

**La réinstallation froide complète hors réseau de CGAL stable 6.1.3 n’est
pas démontrée.** Son archive `CGAL-6.1.3.tar.xz` attendue au SHA 7d8580bb et le
paquet MPFR ne figurent pas parmi les trois archives livrées. L’archive
expérimentale b4e8 ne peut pas les remplacer silencieusement.
Ces expériences n’exécutent aucun workflow carrier complet, aucun support
régional, aucun calcul de distance globale et aucune admission collective.

## Sources existantes et reproduction

Les outils ne sont pas réimplémentés par cette capsule. Les copies des appelants
sont les sources exécutées, conservées à l’octet avec leurs plans historiques.
Leurs anciens préfixes, tokens et sorties sont des preuves ; ne pas les relancer
tels quels. Une nouvelle exécution exige un plan neuf, des destinations fraîches,
les dépendances attestées et l’autorisation adaptée aux ressources.

- [Installateur PyMesh existant](../native-pymesh-20261016/setup.py)
  et [lanceur historique](../native-pymesh-20261016/run.py).
- [Installateur CGAL expérimental](../native-cgal-self-union-20261016/setup.py),
  [worker original](../native-cgal-self-union-20261016/worker.py),
  [témoins originaux](../native-cgal-self-union-20261016/witnesses.py) et
  [C++ original](../native-cgal-self-union-20261016/soup_boolean.cpp).
- [Installateur CGAL stable](../native-cgal-20261016/setup.py), conservé comme
  procédure distincte avec ses prérequis ; il n’a pas été rejoué ici.
- Le protocole Docker réutilisé est conservé sous
  [historical-protocol/ener-supervisor.py](historical-protocol/ener-supervisor.py).

Les trois grosses archives, environnements, exécutables, caches et headers
restaurés sont exclus. Le manifeste intégral des 17 487 fichiers source CGAL
reste dans `work/`, lié par SHA ; une
[sélection explicite](cgal-b4e8/source-restoration-selection.json) conserve sa
provenance et ses compteurs. Les petits résultats de témoins sont inclus.
Les licences/provenances des sources restent celles de leurs outils et archives,
notamment CGAL GPL/LGPL ou licence commerciale et MPFR LGPL.

Vérification de cette capsule, depuis n’importe quel répertoire :

```sh
python3 -B /chemin/du/depot/parts/993-eng-carrier-0001/source/software-archive-restoration-20261017/verify.py
```

Cette commande ne lance ni Docker, ni SSH, ni compilateur, ni import natif.
