# Preuve numérique native F39

Cette enveloppe conserve le rapport complet d'un cycle `motored` de 720° et
les métadonnées de deux exécutions natives `linux/amd64` sur le nœud Intel
autorisé par l'utilisateur. Les deux rapports ont produit exactement le même
SHA-256, `86b5b1ede7b2a54e23b71e0bb4ddd99e753991873f507eb768819f7e5ba5718c`.

Le calcul matérialise 27 conduits 1D, trois plena 0D et douze cylindres 0D. Les
états finaux sont finis et strictement positifs, et le temps final correspond à
720° à 9 000 tr/min. Ces observations ne démontrent ni convergence cyclique,
ni conservation masse/énergie, ni combustion, ni puissance. Toutes les gates
physiques du rapport restent donc fermées.

La commande reproductible utilise l'image GHCR immuable référencée dans
`execution-metadata.json` :

```bash
make F39_OUTPUT=work/917-unsteady-network-f39-ddc7703-run1 \
  917-unsteady-network-f39
```

Le second run emploie un autre répertoire de sortie afin d'éviter toute
réutilisation de résultat, puis les deux fichiers sont comparés octet par octet.
