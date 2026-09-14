# Porsche 917 — validation Omniverse / SimReady de la culasse F37

## Résultat

Le STL F37 final local a été transféré sur une instance Vast.ai vérifiée et
converti avec l'exécutable officiel NVIDIA `usd-convert-cad`. La chaîne a
ensuite exécuté le prévol, la validation USD minimale, l'Asset Validator
générique, la catégorie Geometry et un rendu OVRTX 1 600 × 1 200.

| Contrôle | Résultat |
| --- | --- |
| Image OCI | digest SHA-256 épinglé |
| GPU | Quadro RTX 8000, 49 152 MiB |
| `usd-convert-cad` | terminé, 857 330 triangles |
| Validation USD minimale | passe |
| Asset Validator | passe avec un avertissement |
| Geometry Validator | passe avec `VG.007 = 8 047` sommets |
| Rendu OVRTX | passe, image non uniforme |
| Content Agents | non terminé, runtime VLM incompatible avec le CUDA disponible |
| Solveur physique Omniverse | non exécuté |

![Rendu OVRTX final](../twins/reference-917-engine/evidence/f37-simready/917-head-f37-ovrtx-final.png)

## Interprétation d'ingénierie

Le rendu prouve que l'USDC s'ouvre et représente la peau complète de la pièce.
Il ne prouve ni un assemblage Porsche 917, ni la matière à chaud, ni la tenue
thermomécanique, ni l'imprimabilité LPBF.

Le validateur NVIDIA classe `VG.007` comme `WARNING`, donc son rapport retourne
`PASS`. Le projet applique une politique plus stricte : l'audit local annonce
zéro sommet non-manifold alors que NVIDIA en annonce 8 047 sur la conversion du
même STL. Cette divergence doit être reproduite et corrigée avant de considérer
le maillage comme libérable.

La plateforme Omniverse sert ici à la conversion, à l'audit et à la
visualisation. La résistance reste calculée par CalculiX et la thermique par
OpenFOAM/FluidX3D/CalculiX. Aucun schéma Physics ajouté à l'USDC ne remplacerait
ces solveurs ni leur corrélation physique.

## Traçabilité

Les rapports et l'image sont publiés sous
`twins/reference-917-engine/evidence/f37-simready/`. `publication.json` conserve
le digest de l'image de calcul, les commits amont, les SHA-256 du STL et de
l'USDC non publiés, les SHA-256 de toutes les preuves publiées et tous les gates
de libération à `false`.

```bash
make 917-f37-simready-evidence-check
```

Cette commande ne relance pas le service distant ; elle vérifie hors `work/`
que les preuves publiées n'ont pas dérivé et qu'aucun STL, OBJ, PLY, 3MF ou USD
de la culasse n'est entré dans Git.
