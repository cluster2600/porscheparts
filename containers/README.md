# Images de calcul

Deux images reproductibles pour le travail qui ne tient pas sur un poste
ordinaire. Elles ne sont pas nécessaires pour contribuer au catalogue.

| Fichier | Image | Besoin |
|---|---|---|
| `recon.Dockerfile` | `3dprinting993-recon` | GPU CUDA : photos vers maillage |
| `cadsim.Dockerfile` | `3dprinting993-cadsim` | Processeurs : CAO, maillage, EF, CFD, découpe |

Tous les outils embarqués s’exécutent sans interface graphique, afin qu’un script
puisse rejouer une chaîne complète à l’identique.

```bash
make container-cadsim
make container-smoke
```

`examples/cad_to_fea.py` fait tourner la chaîne complète — solide paramétrique,
STEP, maillage tétraédrique, calcul CalculiX — sans une seule interaction
graphique. C’est la vérification utile : un outil qui répond `--version` ne
prouve rien.

`smoke-test.sh` échoue si un outil annoncé ne répond pas ; `entrypoint.sh` rend
l’environnement du conteneur visible dans les sessions injectées par un
hébergeur ; `provision-vastai.sh` installe à la demande ce qui est trop lourd
pour l’image.

Déploiement, coûts et hygiène des données :
[../docs/COMPUTE_ENVIRONMENT.md](../docs/COMPUTE_ENVIRONMENT.md).
Justification des choix logiciels :
[../docs/decisions/0002-scriptable-toolchain.md](../docs/decisions/0002-scriptable-toolchain.md).
