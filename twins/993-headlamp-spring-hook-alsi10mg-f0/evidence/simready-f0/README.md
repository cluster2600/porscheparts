# OpenUSD, validation NVIDIA et ovphysx du crochet de phare F0

`usd-convert-cad 0.2.0` a converti le STEP en OpenUSD binaire avec
`metersPerUnit=0.001` et axe Z. L'asset puis la scène rigide passent
`nvidia_usd_validate 1.21.0` sans règle en échec.

La scène référence le maillage du crochet comme collisionneur statique. Une
sphère témoin de `10 g`, rayon `2 mm`, tombe sous gravité de `22 à 17 mm` et se
stabilise sur la face supérieure après `240` pas de `1/240 s`. L'exécution CPU
utilise `ovstage 0.1.1.355824` et `ovphysx 0.5.11`.

Ce cas prouve la séquence chargement USD → population ovstage → attachement
ovphysx → pas synchrones → relecture des positions → nettoyage. Il ne modélise
pas le ressort, le phare, l'adhésif, les contraintes ou la chaleur. Aucun rendu
OVRTX ni profil SimReady complet n'a encore été produit pour cette révision.
