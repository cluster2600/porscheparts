# Vérifications de livraison

Dossier préparé le 27 septembre 2026. Aucun essai matériel, montage, métrologie,
qualification radio/routière ou certification d'origine n'est obtenu.

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
