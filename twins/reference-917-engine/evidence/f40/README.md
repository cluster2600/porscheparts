# Preuve numérique native F40

Cette enveloppe conserve le rapport complet de la campagne F40 exécutée deux
fois sur le nœud Intel autorisé. Les deux exécutions ont produit exactement le
même SHA-256 :
`e58b4dbbcaad291eb967d550eec866319fb2672e655710e6236c45ce99713975`.

Le moteur modélisé reste un **flat-12** : douze cylindres, douze pistons et
douze bielles. Les « 24 cycles » de la campagne désignent six variantes
numériques multipliées par quatre cycles moteur de 720°, et non 24 cylindres.
Chaque variante contient 27 conduits 1D, trois volumes de jonction et douze
cylindres 0D ; les 24 ports correspondent à deux soupapes modélisées par
cylindre dans cette enveloppe F39/F40.

Les six cas ont terminé leurs quatre cycles avec des champs finis et des états
strictement positifs. En revanche, le dernier delta agrégé reste compris entre
4,12 % et 4,49 %, très au-dessus du seuil F40 de 0,1 %. La convergence aux
frontières de cycle reste donc fausse et les sensibilités maillage, CFL et état
initial ne sont volontairement pas qualifiées.

La commande reproductible utilise l'image GHCR immuable référencée dans
`execution-metadata.json` :

```bash
make 917-unsteady-convergence-f40 \
  F40_WORKERS=6 \
  F40_OUTPUT=/tmp/3dprinting993-f40-intel-final1
```

Le rapport ne modélise ni injection, ni combustion, ni turbo et ne calcule
aucune puissance. Il n'autorise ni démarrage, ni fabrication, ni revendication
de 1 600 hp/ch.
