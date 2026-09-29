# Bandeau arrière programmable — Porsche 993

**Dossier de préparation, 27 septembre 2026. Aucun matériel fabriqué, mesuré,
essayé ou homologué. Aucun achat, devis envoyé, publication commerciale ou commande.**

## Décision proposée

Commencer par un **coupon monochrome rouge à pas de 2,5 à 4 mm**, comparé à une
matrice RGB du commerce derrière les mêmes échantillons de façade. Une LED de
1 × 0,5 mm existe ; cela ne définit ni le pas ni la résolution finale.
Conserver le RGB comme option à décider après essais optiques et devis.

Le produit visé remplace le bandeau d'origine, avec les mêmes contours,
fixations et interfaces, **sans modification de la voiture**. C'est un objectif,
pas un résultat démontré. Ni dimension extérieure ni référence de variante ne
sont fixées. L'alimentation devra elle aussi être réversible : aucun perçage,
épissure ou prélèvement de puissance non qualifié sur un circuit d'éclairage.

Le porteur du projet assure toute la CAO mécanique et l'assemblage final des
premières séries. Un spécialiste externe accompagne l'électronique. Un renfort
étudiant EPFL est une possibilité future, sans accord institutionnel ni recrutement
engagé. Les noms et coordonnées personnels restent hors de ce dépôt.

La pièce repérée sur Anibis à **180 CHF** est une information fournie par le
porteur ; achat, disponibilité, référence, état et droits de scan restent à
confirmer. Elle n'est ni acquise ni mesurée. Une pièce déformée ne suffit pas à
établir la géométrie nominale d'origine.

## Livrables et ordre de lecture

1. [Feuille de route et backlog](roadmap.md) : dépendances, responsables et portes de décision.
2. [Mécanique, scan et optique](mechanical-optical.md) et [fiche de mesures](measurements.csv).
3. [Architecture électronique et prototype](electronics.md), [BOM préliminaire](bom.csv),
   [coupon E0 : circuit, câblage, BOM et mise au point](electronics/coupon.md).
4. [Logiciel et BLE](software.md), [simulateur](software/panel_simulator.py).
5. [Budget](budget.md), [coûts modifiables](budget.csv), [registre Swissness](swissness.csv).
6. [Prestataires](suppliers.md), [demandes de devis non envoyées](rfqs.md).
7. [Conformité et origine](compliance.md), [validation](validation.md).
8. [Commercialisation](commercial.md), [maquette locale](product-preview.html).
9. [Sources et limites de recherche](sources.md), [résultats des contrôles](verification.md).

## Exécuter localement

Depuis la racine du dépôt, Python 3.10+ ; aucune dépendance pour les deux premières commandes :

```sh
python3 docs/projects/993-programmable-rear-panel/software/panel_simulator.py
python3 docs/projects/993-programmable-rear-panel/software/cost_model.py
python3 -m unittest discover -s tests -p 'test_993_rear_panel*.py' -v
```

Le simulateur affiche deux trames ASCII d'un **coupon virtuel 16 × 8 pixels**.
Ce format ne constitue pas une dimension ni une résolution de la pièce 993.
L'import GIF optionnel utilise Pillow, seulement s'il est déjà installé ; voir
[le contrat logiciel](software.md). Le modèle de coûts est lisible dans un
terminal et ses CSV s'ouvrent dans un tableur. Aucune configuration matérielle,
connexion radio ou mise à jour d'un appareil n'est effectuée.

Le [travail électronique E0](electronics/coupon.md) ajoute un encodeur de référence
TLC5947, une carte des 128 canaux et un calcul de puissance à hypothèses explicites.
Il s'exécute sans matériel ; les résultats ne valident pas un circuit physique.

## Ce qui est réutilisé / ce qui manque

Le dépôt distant `cluster2600/porscheparts` a été vérifié ; la base de travail est
`967f40c` (`origin/main` au début de cette préparation). La recherche ciblée dans
les chemins du dépôt, l'historique local et les PR portant « rear panel » n'a pas
retrouvé de dossier, budget ou patch dédié. Cette recherche n'est pas un audit de
toutes les branches distantes, messages ou archives privées. Les trois fourchettes
historiques du brief sont conservées dans le budget, avec leur statut non vérifié.

Le travail est isolé sur `codex/993-programmable-rear-panel` ; les modifications
préexistantes du répertoire principal ne sont pas incorporées. Aucun enregistrement
de pièce validée n'est ajouté à `catalog/parts/`. Ce dossier constitue une étude,
pas une extension du catalogue faisant foi. La documentation reste en français,
conformément à la demande explicite, malgré la migration générale du dépôt vers
l'anglais. `RTK.md` n'a pas été trouvé aux chemins d'instructions consultés.
