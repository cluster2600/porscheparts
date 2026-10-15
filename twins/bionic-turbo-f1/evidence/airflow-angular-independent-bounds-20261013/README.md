# Relecture indépendante complète des angles restants

La lacune de vérification des comptes angulaires PR237 est comblée sur les 153 boîtes non exclues, sans nouveau ratio, subdivision, candidat, dictionnaire, cas natif ou solveur. La faisabilité géométrique et l'admission complète restent ouvertes.

`verify_angles.py` reconstruit indépendamment les faces par gabarits hex réduits puis les moments et les angles à 192 bits, avec les sources épinglées PR236/238. Le périmètre et l'ordre sont prescrits dans `preflight.md` avant calcul. Huit manifestes ancrés au commit main exact `522b972cc9bf6fd3d3e130303e795790b947ffe7` et leurs 196 entrées sont vérifiés. Les boîtes et l'ordre des contraintes sont exactement ceux des phases parentes. Aucun ancien évaluateur primaire n'est relancé.

## Résultats

Les 9470 angles sont contrôlés sur chacune des 153 boîtes entières : **1448910 évaluations**, dont **1440051 positives**, **8859 indécises** et **aucun refus certain**. Le parcours indépendant dure 771,936 s ; ce n'est pas un benchmark CFD. Les comptes de chaque boîte sont exactement identiques aux comptes primaires PR237. Les 115 boîtes précédemment annoncées entièrement positives sont toutes confirmées ; les 38 autres gardent au moins une borne indécise.

Les deux témoins angulaires anciens PR236, hérités sur leurs feuilles exactes, passent également sur ces 115 boîtes : elles satisfont les **9472 prédicats angulaires variables**. En combinant uniquement les certificats cellulaires PR238 déjà relus indépendamment, **113 boîtes satisfont tous les prédicats variables nécessaires étudiés** : angles, déterminants, plans et volumes. Les deux dernières boîtes ont des angles positifs mais gardent chacune 256 déterminants indécis de fermeture basse. Aucune boîte n'est une solution admise ; les contraintes constantes restent dans leur périmètre de preuve, et les obligations géométriques/natives restent ouvertes.

Aucune nouvelle exclusion : la largeur exclue reste **3943/4096**, la largeur non exclue **153/4096**, dans la seule restriction `u=q_m`. Ce ne sont ni des probabilités ni une mesure du système à deux inconnues.

## Certificat et portée de la comparaison

Toutes les bornes individuelles nouvelles de D, Q et du résidu sont conservées dans `angular-bounds.jsonl.gz`, avec les deux entiers d'extrémité divisés par `2^192`. Voir `method.md` pour le format, les conventions d'orientation, la reconstruction et les limites. `records.json` conserve les comptes par boîte ; `order.json` les tuples ordonnés ; `boxes.json` les domaines exacts.

PR237 ne conservait pas ses bornes individuelles non excluantes : **aucune inclusion numérique dans ces anciennes bornes absentes n'est revendiquée**, ni une comparaison face par face des anciennes classifications dans les boîtes mixtes. La nouvelle reconstruction indépendante couvre chaque face et confirme intégralement les 115 boîtes entièrement positives. `read_certificate.py` relit ensuite toutes les lignes enregistrées, leur ordre et leurs signes, puis vérifie les comptes et les domaines de l'héritage. Cette relecture structurelle ne constitue pas une seconde reconstruction géométrique.

Aucune assertion refusée, aucun lecteur interrompu, aucune installation dans cette phase. Les représentations et dérivations antérieures ne sont pas refaites. Les noyaux et les sources anciennes restent immuables. Les tests du dépôt et leurs limites sont décrits dans `validation.md`.

Les gros encadrements et listes sont disponibles dans l'[archive complète](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-angular-independent-bounds-2026-10-13), avec tailles/SHA et relecture locale de tous les payloads. Les résultats synthétiques et les sources figurent dans ce dossier.

Partage exact, frontière, couverture orientée, non-intersection, planéité, bilan, branches natives et arrondis OpenFOAM, qualité native et repos global restent distincts. Les trois intervalles synthétiques ne qualifient ni toute la couronne ni les surfaces physiques. 084 reste incomplet et n'est pas relancé. Aucun débit, puissance ou calibration validé. Voir `next-scope.md`.
