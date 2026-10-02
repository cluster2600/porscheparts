# Execution Kali et diagnostic PicoGK — 2 octobre 2026

Cette reprise execute des calculs, sans qualification de coque ou de procede.
Le [recu](../../derived/kali-compute-20261002.json) separe les executions
reussies, les echecs et les empreintes. Aucun scan brut, poids Qwen, secret,
conteneur partage ou preuve historique n'a ete modifie.

## Calculs executes

- **Kali 1, Python natif** : huit architectures du treillis F1 historique,
  source au commit `135dcc8ef6e71ac483e1ed3036217536562c80a1`.
- **Kali 2, Docker** : meme treillis puis CalculiX 2.21 sur le deck regenere.
  Les sorties Python et le deck sont identiques entre les machines. La rigidite
  numerique retenue reste 21 011,7 Nm/deg ; ecart CalculiX/Python :
  `7.817523457564439e-7` relatif, sous le seuil existant `1e-4`.
- **Kali 2, PicoGK** : reprise du tunnel a 4 et 2 mm avec les entrees Qwen
  precedentes, sans nouvelle inference. Voir le recu pour les resultats natifs
  et les ecarts Mac/Linux, qui ne constituent pas une tolerance de fabrication.
- **Kali 2, image mesh-cfd existante** : les 15 tests F37 bloques sur le socket
  Docker du Mac passent. Ils testent un outil LPBF du programme 917, pas la
  fabrication de la monocoque carbone.

Avec la DLL candidate, les trois interferences initiales sont retrouvees aux
deux resolutions et les sondes des ouvertures et parois passent. L'ecart maximal
Mac/Linux des volumes d'intersection non nuls est de 0,166 % a 4 mm et 0,0174 %
a 2 mm. La soustraction laisse un residu nul sur la meme grille, toujours avec
jeu additionnel nul. Aucune convergence generale n'est etablie.

Docker repond sur Kali 2. Le compte SSH de Kali 1 n'appartient pas au groupe
du socket Docker et `sudo -n` demande un mot de passe ; aucun droit n'a ete
change. Les calculs Python natifs de Kali 1 n'en ont pas besoin.

Le controle global reste non vert : la cible locale
`make 917-f46-vast-controller-check` retrouve l'ecart d'empreinte historique
du connecteur Vast. Aucun rapport historique n'est reecrit pour le masquer.
La suite globale complete n'a pas ete relancee sur Kali dans cette reprise.
Les sept tests locaux `test_964_*.py`, `bash -n` du lanceur et
`git diff --check` passent ; les compilations de la candidate, de la sonde et
du tunnel n'ont ni erreur ni avertissement.

## Defaut Linux reproduit et correction isolee

Le premier transfert tar a introduit `._Program.cs`, metadonnee macOS que le
compilateur prenait pour du C#. Le transfert suivant utilise
`COPYFILE_DISABLE=1 tar --no-xattrs --exclude='._*'` vers un dossier neuf.
Le premier echec et son journal sont conserves.

Avec la DLL PicoGK initiale, `Voxels.bIsInside` indique aussi `true` pour les
deux points exterieurs au cylindre temoin. La meme fonction native avec un
retour explicitement marshalise sur un octet retrouve les trois reponses
attendues. La declaration initiale ne precise pas cette taille. Ce diagnostic
est coherent avec la distinction entre le `bool` C++ et le booleen .NET
marshalise par defaut decrite par [Microsoft](https://learn.microsoft.com/en-us/dotnet/standard/native-interop/best-practices#boolean-parameters-and-fields).

`bool-return.patch` ajoute uniquement `[return: MarshalAs(UnmanagedType.I1)]`
a cette declaration, dans une **copie de compilation**. La DLL candidate est
compilee hors ligne depuis les sources contenues dans l'image, puis montee
uniquement dans le conteneur du calcul. L'image, la DLL installee sur Kali,
le programme de tunnel et les resultats Mac initiaux restent inchanges.

`Program.cs` est le test de regression executable : code de sortie non nul
avec la liaison initiale, nul avec la candidate. Il compare un point interieur
et deux points exterieurs eloignes de la surface. Ce test et les sondes du
tunnel ne qualifient **pas toutes les API** PicoGK ni tous les booleens natifs.
La candidate est un profil de cette etude, pas une mise a jour globale.

## Reproduction dans l'image existante

Image station, ID local immutable :
`sha256:4f58a4e28ab7706e7735b2185123c2d8fd6eb94a3d1842a9e352950ce503bdfb`.
Image F37 :
`sha256:49979f46f421459dae4bf21aaa898e2253b07301c3e5b2cabaa6eaf06f54d696`.
Aucun telechargement ni lancement cloud. Conteneurs non root, sans reseau,
systeme racine en lecture seule, capacites retirees ; 2 CPU, 2 GiB sans swap,
128 processus, arret a 600 secondes pour le parcours tunnel.

Monter ce dossier en `/source:ro` et un dossier neuf en `/output`. Avec
`DOTNET_CLI_HOME=/tmp/dotnet`, `NUGET_PACKAGES=/tmp/nuget` et
`LD_LIBRARY_PATH=/app:/opt/picogk-native/lib`, executer dans l'image :

```sh
mkdir /output/runtime-source
cp /upstream/PicoGK/Internals/Interop.cs /output/runtime-source/Interop.cs
cd /output/runtime-source
patch --fuzz=0 < /source/bool-return.patch
dotnet build /source/PicoGK.Candidate.csproj -c Release \
  -p:BaseIntermediateOutputPath=/output/runtime-obj/ -o /output/runtime-bin
dotnet build /source/Probe.csproj -c Release \
  -p:PicoGKPath=/output/runtime-bin/PicoGK.dll \
  -p:BaseIntermediateOutputPath=/output/probe-obj/ -o /output/probe-bin
dotnet /output/probe-bin/Probe.dll
```

Pour le temoin initial, compiler `Probe.csproj` dans un autre dossier avec
`PicoGKPath=/opt/station-demo/bin/PicoGK.dll`. Le code de sortie 1 attendu
est un echec du profil initial, pas un test a contourner.

Le script [linux-checks.sh](../qwen-picogk-tunnel/linux-checks.sh) consomme en
lecture seule une entree `/input` avec `manifest.sha256` verifie par
`sha256sum --check`, et une sortie neuve `/output`. Disposition de l'entree :

```text
inference/                 input.json + inference.json du Qwen Mac accepte
source/twins/964-chassis/source/qwen-picogk-tunnel/
                           Program.cs + Tunnel.csproj au commit c751517
legacy/twins/993-carbon-safety-cell/
                           design-space.json et les deux scripts historiques
                           build_structural_screening.py, verify_calculix.py
linux-checks.sh
manifest.sha256            empreintes des huit fichiers ci-dessus
```

Pour la reprise corrigee, monter aussi la DLL candidate en lecture seule sur
`/opt/station-demo/bin/PicoGK.dll` **dans ce seul conteneur**. Le programme
original du tunnel garde toutes ses assertions. La copie `legacy` de sortie
est seule autorisee a recevoir les nouveaux resultats CalculiX.

## Limite physique decisive

Le treillis n'inclut pas les ouvertures du nouveau tunnel ; sa rigidite ne leur
est pas transferable. Ni la geometrie voxelisee, ni le materiau equivalent
du treillis ne sont un maillage de coque stratifiee. Les jeux dynamiques,
les interfaces mesurees, les stratifies, les collages et renforts autour des
ouvertures, la cuisson, les moules et la correlation experimentale restent a
definir avant tout calcul structurel de produit ou toute fabrication.
