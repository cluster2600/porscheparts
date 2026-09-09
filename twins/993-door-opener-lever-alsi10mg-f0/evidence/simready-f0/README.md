# OpenUSD et ovphysx du levier F0

Le préflight CAD-to-SimReady a validé les accès OpenBao/GHCR/Vast, puis a
arrêté le workflow complet car aucune instance Material Agent, Physics Agent ou
OVRTX n'était active. Aucune propriété suggérée par LLM n'a donc été écrite.

Indépendamment, `usd-convert-cad 0.2.0` a converti le STEP en OpenUSD binaire
Z-up en millimètres. L'asset et une scène de contact rigide passent
`nvidia_usd_validate 1.21.0` sans règle en échec. `ovstage 0.1.1.355824` et
`ovphysx 0.5.11` exécutent ensuite `240` pas CPU : une sphère de `10 g` tombe
de `35` à `29 mm` et repose sur l'extrémité du levier.

Ce témoin prouve le branchement OpenUSD → ovstage → ovphysx et son nettoyage.
Il ne représente ni la main, ni le pivot, ni la serrure, ni l'ouverture de
porte. Le profil SimReady complet et le rendu OVRTX restent bloqués.
