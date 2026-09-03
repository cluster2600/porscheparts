# Preuves Omniverse / SimReady F37

Ce dossier publie le prévol, les validations USD et le rendu OVRTX exécutés
sur le STL F37 local. Le STL et l'USDC dérivé ne sont pas versionnés : seules
leurs empreintes SHA-256 figurent dans `publication.json`.

La conversion officielle `usd-convert-cad` a produit un USD de 857 330
triangles. Le prévol et la validation USD minimale passent. Le validateur
NVIDIA accepte formellement le fichier mais signale `VG.007` sur 8 047 sommets.
Le dépôt traite cet avertissement comme bloquant parce que l'audit local annonce
zéro sommet non-manifold : il n'existe donc pas encore de consensus indépendant.

Le rendu `917-head-f37-ovrtx-final.png` provient du service OVRTX local sur GPU,
pas d'un générateur d'images. Les Content Agents n'ont pas été retenus comme
preuve : le runtime VLM de cette machine demandait `libcudart.so.13`, absent de
l'image. Omniverse n'a exécuté aucun calcul de résistance ou de thermique ; ces
calculs restent ceux de CalculiX, OpenFOAM et FluidX3D.

```text
metal_print_authorized = false
engine_start_authorized = false
```

Contrôle des empreintes et des gates :

```bash
python3 tests/test_917_f37_simready_evidence.py -v
```
