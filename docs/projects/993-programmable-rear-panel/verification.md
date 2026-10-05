# Vérifications de livraison

Dossier préparé le 27 septembre 2026. Aucun essai matériel, montage, métrologie,
qualification radio/routière ou certification d'origine n'est obtenu.

## Schéma natif E0 — 2 octobre 2026

Base `0efe260` (`origin/main`), après fusion du travail E0 précédent. Nouvelle
branche `codex/993-e0-kicad`, dans le worktree isolé existant ; aucun changement
du répertoire principal incorporé. Ajout de trois feuilles KiCad A3 éditables,
du projet et de sa bibliothèque locale attribuée, d'un PDF et d'un test de netlist.
Documentation, RFQ non envoyée et backlog actualisés. Aucun achat ni fabrication.

| Contrôle | Résultat observé |
|---|---|
| KiCad 9.0.2, `sch erc --severity-all --exit-code-violations` | **0 erreur, 0 avertissement**, aucune exclusion ni règle désactivée |
| Test du schéma sur export `kicadxml` frais | **172 composants, 172 nets, 541 broches** : groupes de connexions complets, valeurs, rails, 128 cathodes, chaîne des drivers, IREF, BLANK, pad thermique et broches inutilisées conformes au contrat E0 |
| `python3 -m unittest discover -s tests -p 'test_993_rear_panel*.py' -v`, Linux avec KiCad | **17 tests réussis**, aucun ignoré |
| Même commande sur macOS sans KiCad | 17 tests exécutés, **OK, 1 ignoré** (le schéma) ; ne remplace pas le contrôle Linux |
| Export PDF KiCad | Trois pages A3 relues visuellement, champs lisibles, métadonnées auteur absentes ; aucun dessin de PCB |
| `make docs-links-check reports-index-check` | Réussi, 0 lien cassé sur 641 fichiers Markdown ; index des rapports à jour |
| `git diff --cached --check` | Réussi après suppression d'un espace final dans le texte de licence importé |
| `make check`, Linux natif | Suite de **3 250 tests, OK, 159 ignorés**, puis contrôles F32/F34/F37 franchis. Arrêt sur `917-manufacturing-f37-lpbf-audit-check`, `/bin/sh: 1: docker: not found`, Makefile ligne 1014, code global **2** ; cibles suivantes non exécutées |

Environnement : conteneur local Debian trixie arm64, image
`debian:trixie-slim@sha256:a99cfc517144bc59b1978475ec53b46ecabec7e43635402ee5b77cc54cd1b20a`,
KiCad `9.0.2+dfsg-1`, symboles `9.0.2-1`, Python 3.13.5, NumPy 2.2.4,
Pillow 11.1.0, Node 20.19.2. Dépendances installées dans ce conteneur uniquement.
Copie sur son système Linux, index Git local, UID/GID 1000, umask 022 ; réseau
déconnecté avant les tests, aucun secret ni socket Docker hôte monté. Les messages
de publication/cloud de la suite globale proviennent de simulations.

Corrections de préparation : premier fichier généré refusé par KiCad (parenthèse
de fermeture manquante par instance), corrigé avant validation ; premiers ERC
avec avertissements d'héritage de symbole et de bibliothèque locale non chargée,
corrigés par symboles locaux explicites et projet associé. Premier contrôle de
liens avant ajout des nouveaux fichiers à l'index Git : cinq liens signalés absents,
puis zéro après ajout. Aucun contrôle désactivé pour obtenir ces résultats.

Le schéma n'est **pas validé pour fabrication** : empreintes non attribuées,
aucun PCB/DRC, aucune simulation analogique ni mesure de courant, température,
extinction ou alimentation parasite. Revue indépendante puis routage et essais
E0 restent ouverts. Le calcul de puissance, les coûts et les limites du MCU
bloqué du 28 septembre restent des hypothèses inchangées. `make check` global
doit encore être exécuté dans un environnement disposant du moteur Docker et
des images imposées par le dépôt ; son résultat n'est pas annoncé réussi.

## Complément électronique E0 — 28 septembre 2026

Ajout du [circuit de principe E0](electronics/coupon.md), des BOM/connexions CSV,
de l'encodeur TLC5947 et du calcul de puissance. La fiche LED exacte remplace
la fiche d'exemple d'une autre référence. Sources S01 et S31–S34 relues.

| Contrôle | Résultat observé sur ce complément |
|---|---|
| `python3 -m unittest discover -s tests -p 'test_993_rear_panel*.py' -v` | **16 tests réussis** sur macOS/Python 3.10.11, dont 6 nouveaux : chaîne SPI simulée indépendamment sur chacun des 128 pixels, plafond/valeurs invalides, noir après défaut, coordonnées/broches, calculs et génération sans écrasement |
| `coupon_driver.py --output-dir /tmp/993-coupon-e0-20260928` et variante `--pitch-mm 4` | Deux cartes de 128 connexions, deux trames de 216 octets par variante, calculs JSON ; 2,46 mA nominal/canal et allocation coupon ≈2,114 W sous hypothèses, pas mesure |
| CSV et documentation | 19 lignes BOM, 34 lignes de connexions, colonnes cohérentes ; `make docs-links-check reports-index-check` réussi, 0 lien cassé sur 556 fichiers Markdown ; `git diff --check` réussi |
| `make check` sous Linux natif dans conteneur local | **3 062 tests, OK, 142 ignorés**, puis tests F32/F34/F37 franchis ; arrêt sur `917-manufacturing-f37-lpbf-audit-check`, `/bin/sh: 1: docker: not found`, code make 2. Les cibles suivantes restent non exécutées |

Même image locale que décrite ci-dessous, Python 3.11, NumPy 2.4.6, Pillow 12.3.0,
copie sur le système Linux du conteneur, UID/GID 1000, umask 022. Réseau déconnecté
avant l'exécution du dépôt ; aucun socket Docker hôte ni secret monté. Les tests
de fournisseurs cloud utilisent leurs simulations : aucune machine payante lancée.
Première copie rejetée par `validate_catalog.py` à cause de fichiers AppleDouble
`._*` ajoutés par l'archivage macOS (UnicodeDecodeError). L'archive a été recréée
avec `COPYFILE_DISABLE=1` et sans attributs étendus, puis la commande relancée ;
aucun fichier catalogue ni garde de validation modifié pour la faire passer.

À la livraison du 28 septembre, `kicad-cli` n'était pas disponible : aucun ERC/DRC exécuté,
et aucun fichier EDA natif ou export de fabrication annoncé. Les tests valident
uniquement les données et calculs hôtes. Revue électronique, schéma natif, routage,
alimentation automobile, watchdog matériel, mesures optiques/thermiques et portage
MCU/BLE restent ouverts. Le coupon E0 nécessite une surveillance humaine au banc.

Les résultats ci-dessous concernent la livraison initiale du 27 septembre.

## Révision et périmètre

Base distante : `967f40c`. Branche : `codex/993-programmable-rear-panel`.
20 fichiers de préparation sous `docs/projects/993-programmable-rear-panel/`
et un fichier de tests dédié. Les modifications préexistantes du répertoire
principal ne sont pas incorporées. Accès GitHub en lecture et droit ADMIN vérifiés.
Aucun achat, demande de devis envoyée ou déploiement commercial.

## Résultats reproductibles

| Contrôle | Résultat réellement observé |
|---|---|
| `python3 -m unittest discover -s tests -p 'test_993_rear_panel.py' -v` | **10 réussis**, macOS, Python 3.10.11, Pillow 11.3.0 ; dernière vérification ciblée après nettoyage import inutile |
| `python3 docs/projects/993-programmable-rear-panel/software/panel_simulator.py` | Démonstration deux trames ASCII, puis extinction ; pas de radio ni matériel |
| `python3 docs/projects/993-programmable-rear-panel/software/cost_model.py` | Fourchettes historiques et ventilations cohérentes ; cible 250 ; NRE partiel 21 230–64 980 ; origine illustrative 115/205=56,10 % |
| Variante `cost_model.py --rd-ch 20700 --units 1000` | 60,12 % illustratifs, aucune attestation ; hypothèses et sensibilité décrites dans budget.md |
| CSV et liens Markdown locaux | Colonnes cohérentes des quatre CSV ; toutes destinations locales existantes |
| `git diff --cached --check` | Réussi |
| `make docs-links-check reports-index-check` sous Linux | Réussi : 0 lien cassé sur 555 fichiers Markdown ; index des rapports à jour |
| Maquette HTML | Page servie uniquement sur loopback et vérifiée dans le navigateur : rendu bureau et avertissements visibles ; serveur arrêté. Pas de validation mobile, pas de test de compatibilité app |
| Suite globale, via `make check` dans Linux natif | **3 056 tests, OK, 142 ignorés**, Python 3.11.15, NumPy 2.4.6, Pillow 12.3.0 ; compte incluant les tests de ce projet |
| Cibles suivantes de `make check` | F32/F34 et tests F37 publiés franchis ; arrêt ensuite sur cible Docker décrite ci-dessous |

## Limite de `make check` — commande complète non réussie

Environnement : image locale `nikolaik/python-nodejs:python3.11-nodejs20` (arm64),
image ID `sha256:8f958bdc1b4a422bfafd97cab4f69836401f616ae985d4b57a53d254f5bcb038`,
copie sur système de fichiers Linux, utilisateur 1000:1000, umask 022, index Git
local initialisé. NumPy/Pillow installés uniquement dans le conteneur jetable ;
réseau déconnecté **avant** les tests. Aucun accès au moteur Docker hôte exposé au
conteneur. Aucune dépendance projet, image verrouillée ou règle du dépôt modifiée.

Après la suite globale réussie et des cibles supplémentaires réussies :

```text
/bin/sh: 1: docker: not found
make: *** [Makefile:1013: 917-manufacturing-f37-lpbf-audit-check] Error 127
```

La cible réclame `docker run` et une image mesh-cfd épinglée. Le `make` global
retourne **2** ; les cibles suivantes ne sont donc pas couvertes par cette exécution.
Il reste à relancer `make check` dans l'environnement Linux natif prévu par le
projet avec moteur Docker et images nécessaires disponibles. Ne pas cocher « make
check réussi » dans la PR. Les 142 tests ignorés portent sur des dépendances/
runtimes optionnels, notamment CAO/solveurs ; ils ne constituent pas des réussites.

## Tentatives antérieures consignées

1. Conteneur Linux natif minimal, archive sans index Git, utilisateur root et sans
   NumPy : 2 900 tests, 1 échec, 77 erreurs, 168 ignorés. Causes relevées : 18 erreurs
   NumPy, 54 refus de métadonnées propriétaire/permissions de modules de garde,
   5 appels `git ls-files` sans dépôt ; l'échec F58 refusait l'UID 0.
2. Image existante `3dprinting993-simready-workflow:f35`, amd64 en émulation :
   interrompue pour durée excessive avant résultat global, non comptée comme réussite.
3. Relance native corrigée ci-dessus : ces erreurs ne réapparaissent pas ; aucun
   code de garde ou test existant n'a été changé pour les contourner.

Les fichiers d'archive/logs de contrôle sont des artefacts locaux temporaires,
non committés. Les messages de publication imprimés par certains tests globaux
proviennent de simulations : le réseau du conteneur était coupé.

## Limites du produit restant ouvertes

Authentification BLE injectée par les tests, pas de chiffrement radio implémenté ;
DFU spécifiée, pas livrée ; compatibilité MCU/iOS/Android non testée. Aucun scan,
cote, PCB routé ou prototype réel. Pièce Anibis et coûts non vérifiés. Avis légal,
fonctions d'origine, transmission rouge, vieillissement, alimentation automobile,
CEM/RF, thermique, rendement et origine suisse à qualifier.

Les indisponibilités documentaires (portail Fedlex sans texte extrait, UNECE 403,
texte cybersécurité non extrait) sont recensées dans sources.md. Elles empêchent
une conclusion réglementaire définitive, pas la préparation des consultations.
