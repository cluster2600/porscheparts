# Intégration LEAP 71 — prévol M64

Suite du 7 septembre : voir [l'exécution PicoGK sur le corps réel](M64_PICOGK_EXECUTION.md).
Le présent document conserve les étapes historiques du prévol.

État vérifié le 6 septembre 2026 : **compilation C# et runtime C++ réussis ;
smoke géométrique headless réussi sur Kali Linux amd64**. Le premier échec
sur l'image managed Linux arm64 reste documenté ci-dessous. Aucune culasse modifiée,
aucune simulation thermique réalisée, aucune machine Vast louée pour ce prévol.

## Sources et fonction exacte

Les quatre dépôts officiels ont été récupérés à leurs commits inscrits dans
`containers/m64-leap71/sources.lock`. Leurs fichiers LICENSE sont Apache-2.0.
Le bootstrap conserve les licences dans chaque clone ; aucune source tierce
n'est recopiée dans ce dépôt. La distribution d'un runtime compilé devra aussi
conserver les obligations de ses dépendances, qui ne sont pas toutes réduites
à la licence PicoGK.

- [PicoGK](https://github.com/leap71/PicoGK) : noyau de géométrie volumique
  basé sur OpenVDB, pas solveur thermique.
- [ShapeKernel](https://github.com/leap71/LEAP71_ShapeKernel) : formes et
  opérations de construction au-dessus de PicoGK.
- [HelixHeatX](https://github.com/leap71/LEAP71_HelixHeatX) : exemple de
  génération d'échangeur hélicoïdal. Le tutoriel distingue expressément le
  noyau géométrique de la connaissance d'ingénierie à programmer.
- [PicoGKRuntime](https://github.com/leap71/PicoGKRuntime) : bibliothèque C++,
  dépendante notamment d'OpenVDB et GLFW. Ce dépôt est disponible ; un binaire
  Linux compatible a ensuite été construit et testé dans la variante native.

## Résultat réel et reproduction

```sh
docker build -t 3dprinting993-m64-leap71:managed-preflight containers/m64-leap71
docker run --rm --network none 3dprinting993-m64-leap71:managed-preflight
```

Le premier ordre a réussi sur Docker **linux/arm64**, en compilant PicoGK,
ShapeKernel et tous les fichiers `src` de HelixHeatX : **44 avertissements
amont, zéro erreur**. Les avertissements concernent notamment nullabilité et
API obsolètes ; les sources amont n'ont pas été modifiées pour les masquer.
L'image .NET de base est fixée par digest, les quatre dépôts par SHA complet.
Les dépendances NuGet transitives ne sont pas encore verrouillées par un
`packages.lock.json` : ce bootstrap n'est pas une preuve de build bit-à-bit.

Le second ordre a été réellement exécuté, hors réseau : **code 1,
DllNotFoundException, bibliothèque `picogk.26.2` absente**. Le test veut créer
une sphère de rayon 5 mm à voxels de 0,5 mm et vérifier un maillage non vide.
Il n'a pas atteint cette construction. Cette sphère est uniquement un témoin
logiciel, jamais une approximation de culasse ni une proposition de forme.

`PicoGK.csproj` au commit fixé cible **net9.0 / PicoGK 2.3.0** et embarque des
binaires `osx-arm64` et `win-x64`, pas `linux-x64` ni `linux-arm64`.
Le programme de smoke utilise `new Library(...)`, sans `Library.Go` ni viewer.
Cela évite de demander une fenêtre, mais ne prouve pas le fonctionnement
headless du runtime C++ absent. `HelixHeatX.Task()` appelle des fonctions de
visualisation : il n'est pas déclaré headless par ce simple bootstrap.

## Place dans le projet de culasse

Conserver les interfaces usinées, références, portées et le master B-Rep OCCT.
PicoGK est un candidat pour générer **des variantes internes de refroidissement**
dans des volumes explicitement autorisés : conduits courbes, transitions et
surfaces d'échange. Il ne donne ni interfaces M64, ni loi matière, ni budget de
perte de charge. Ne pas greffer l'échangeur HelixHeatX complet dans la culasse.
Le contour Porsche reste une contrainte d'entrée, pas une variable libre.

Un volume voxelisé étanche n'est pas un B-Rep exact ni un plan d'usinage.
L'export maillé demande une étude de résolution, une comparaison au master,
un audit des parois et des communications entre cavités. Un éventuel raccord
au B-Rep doit être reconstruit et contrôlé, pas renommé STEP. Les passages
d'huile restent soumis à débit, pertes de charge, étanchéité, dépoudrage et
risque de contamination avant tout choix de conception.

Les variantes devront ensuite être évaluées par CFD/CHT et calcul structurel
indépendants ; une géométrie HelixHeatX ne constitue aucun résultat thermique.

## Prochain verrou logiciel avant achat de calcul

1. Construire PicoGKRuntime 26.2 sur la plateforme cible avec sous-modules
   fixés ; ne pas utiliser une mise à jour `--remote` non verrouillée.
2. Vérifier dépendances dynamiques, nom ABI `picogk.26.2`, puis passer le smoke
   natif hors affichage sur **linux/amd64**. Autre voie possible : tester d'abord
   le binaire macOS arm64 fourni sur la machine locale avec .NET 9.
3. Ajouter un témoin de canal avec critères géométriques et convergence voxel,
   puis seulement intégrer les domaines de refroidissement autorisés.

Aucun besoin GPU géométrique n'est démontré par ce prévol. Louer une machine
GPU ne résout pas à lui seul l'absence du runtime. Le fichier JSON de résultats
sépare compilation, exécution et aptitude à une utilisation Vast.

## Tentative native distincte sur Kali x86

`Dockerfile.native` construit le runtime officiel et ses sous-modules épinglés
dans une image Linux amd64. `native-submodules.lock` consigne les trois gitlinks
effectivement récupérés, sans `--remote` : OpenVDB 13, GLFW et ImGui.

Le premier configure a réellement échoué : Boost Debian 1.74 est inférieur au
minimum 1.82 exigé par le chargement différé OpenVDB. La variante suivante
désactive ce chargement différé et les fonctions Imath/EXR via leurs options
officielles. Les vérifications de versions ne sont **pas** désactivées. Le
configure a ensuite réussi avec TBB 2021.8, Blosc 1.21.3 et Zlib 1.2.13 ;
la compilation C++ a démarré. Cette variante n'a pas les fonctions de
chargement différé ou EXR de la configuration par défaut.

Reproduction de cette tentative, distincte de l'image managed :

```sh
timeout 600 docker build -f containers/m64-leap71/Dockerfile.native \
  -t 3dprinting993-m64-leap71:native-preflight containers/m64-leap71
timeout 60 docker run --rm --network none \
  3dprinting993-m64-leap71:native-preflight
```

**Résultat natif réel :** compilation des 70 unités C++ et lien réussis en
380,7 secondes ; C# compilé, 44 avertissements et zéro erreur. L'exécution
`docker run --rm --network none` sous timeout 60 secondes a retourné le code 0 :

```text
NATIVE_GEOMETRY_SMOKE_PASS triangles=3660
```

Le témoin est une sphère de rayon 5 mm, résolution voxel 0,5 mm, convertie en
3660 triangles par le runtime natif. Aucun viewer ni serveur X n'a été créé.
`ldd` ne signale aucune dépendance absente. Cela valide cette opération
géométrique headless, pas toutes les API, la précision dimensionnelle d'une
culasse, la génération complète HelixHeatX ou un calcul thermique.
L'agent principal a répété indépendamment le smoke sur la même image avec
`--cpus 2 --memory 4g --network none` : même résultat, code 0, 3660 triangles.

Image locale Kali amd64 :
`sha256:f38695f9ecc99ceef65c5e1fe02adf5dbfa95ee1ae925f95fd47bdba9ebb6178`.
Bibliothèque `/app/picogk.26.2.so` :
`sha256:fc62c8ae58d9e277b1b9ef1b2bb1e761159d5bab81f752c9243fb6bbd150d54b`.
Pas de publication GHCR ni de digest de registre validé à cette étape.

`native-preflight-result.json` consigne ce résultat distinct. L'ancien rapport
`preflight-result.json` est conservé sans réécriture.
