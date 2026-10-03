# Proxy de topologie du rotor 935 par PicoGK

Le 3 octobre 2026, la revue en vue axiale, radiale et oblique a rejeté la
fermeture Screened Poisson `run-009` : bien que sa topologie numérique soit
fermée, elle invente des ponts et des volumes au moyeu. Elle ne représente pas
un rotor et ne doit servir ni de référence visuelle, ni de maillage de calcul.

La référence de cette étape est donc un **proxy de topologie visuel** construit
avec PicoGK. Ce proxy est volontairement distinct d'une CAO récupérée depuis
le scan et de toute pièce imprimable.

## Ce que le scan établit visuellement

La vue haute du composant principal montre un disque arrière, dix pales
courbes relevées et un moyeu central. Le fichier préparé contient aussi une
petite deuxième composante isolée ; elle n'est pas fusionnée au rotor par
cette reconstruction. Cette séparation évite que le défaut de couverture au
centre ne devienne une fausse géométrie de moyeu.

## Construction PicoGK

Le programme
[Program.cs](../../../twins/935-horizontal-cooling-system-f0/source/picogk-rotor-visual-proxy/Program.cs)
contrôle l'empreinte du scan préparé, en extrait seulement son enveloppe dans
le plan PCA, puis construit l'union implicite de :

- un disque arrière ;
- un moyeu annulaire relevé ;
- dix pales courbes, décalées de façon régulière.

Les rayons, hauteurs, épaisseurs, courbure, alésage et sections de pales sont
des **hypothèses visuelles paramétrées par ratios**. PicoGK emploie un pas de
voxel exprimé dans l'unité source inconnue ; il n'est jamais présenté comme un
pas en millimètres. Les coordonnées du scan, les maillages et le reçu détaillé
restent sous `work/`.

Une exécution privée a utilisé PicoGK Core 26.2.0. Après soudure des sommets
pour l'audit, le proxy est une composante fermée avec orientation cohérente et
les contrôles MeshLab n'ont relevé ni auto-intersection ni non-manifold. Ces
contrôles qualifient seulement la cohérence du proxy généré.

## Exécution reproductible

L'exécution nécessite un runtime PicoGK officiel déjà qualifié, .NET 9 et un
nouveau dossier privé. Les fichiers de sortie ne doivent jamais être ajoutés
au dépôt.

```sh
dotnet build twins/935-horizontal-cooling-system-f0/source/picogk-rotor-visual-proxy/ScanGuidedRotorProxy.csproj \
  -p:PicoGKAssembly=/PRIVATE/PicoGK.dll -o /PRIVATE/bin
dotnet /PRIVATE/bin/ScanGuidedRotorProxy.dll \
  /PRIVATE/pose-normalized-open-scan.obj PREPARED_SHA256 work/NEW
```

## Limites qui restent ouvertes

Le proxy ne confirme ni variante 935, ni échelle, ni face arrière, ni profil
aérodynamique, ni sens de rotation, ni alésage, ni système de fixation. Il ne
fournit donc ni masse, ni inertie, ni régime, ni contrainte, ni débit, ni
pression. Les relevés métrologiques des interfaces et une reconstruction
surfacique séparée restent nécessaires avant le jumeau mécanique ou fluide.
