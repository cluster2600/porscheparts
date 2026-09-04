# Preuve numérique native F40b

Cette enveloppe conserve le rapport complet de la campagne F40b exécutée deux
fois sur le nœud Intel autorisé, depuis le commit source `864d60a`. Les deux
exécutions sont byte-identiques et portent le même SHA-256 :
`b3045e91cf8c20606166caef132c2b15030a5204d220c093b89446b0476a1b35`.

Le cas reste strictement un **flat-12** numérique `motored` : douze cylindres,
27 conduits 1D et 24 ports équivalents. Ces 24 ports décrivent l'enveloppe
F39/F40 à deux ports par cylindre ; ils ne constituent ni 24 cylindres, ni une
validation de la future architecture moderne à quatre soupapes par cylindre.

Le réseau et son état ont été conservés pendant seize cycles moteur successifs
de 720°. La première fenêtre de trois deltas agrégés consécutifs conforme au
seuil de `0,001` se termine au cycle 16. Ses maxima sont :

- cycles 13 → 14 : `0,0005528999787436965` ;
- cycles 14 → 15 : `0,00019262889509060575` ;
- cycles 15 → 16 : `0,000030146002643767643`.

Cela démontre uniquement un état périodique **agrégé** pour ce cas nominal et
ces sept métriques globales. Aeolus1D 0.3.3 n'a pas fourni ici de traces
phase-résolues vérifiées : les normes L2/L∞ et la convergence phase-résolue
restent donc explicitement non évaluées. Les états finis et positifs ne
démontrent pas davantage les bilans de masse ou d'énergie.

La commande reproductible est :

```bash
make 917-extended-periodic-state-f40b \
  F40B_OUTPUT=/tmp/917-f40b
```

Le rapport référence l'image GHCR immuable indiquée dans
`execution-metadata.json`, mais le runner n'en vérifie pas lui-même le digest
au moment de l'exécution. Cette vérification reste donc une responsabilité de
l'orchestrateur et ne doit pas être déduite du seul JSON.

F40b ne modélise ni injection, ni combustion, ni turbocompresseur et ne calcule
aucune puissance ou aucun couple. Toutes les gates physiques restent fausses :
ce résultat n'autorise ni démarrage, ni fabrication, ni revendication de
1 600 hp/ch.
