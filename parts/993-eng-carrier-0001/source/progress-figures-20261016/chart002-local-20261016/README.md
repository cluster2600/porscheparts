# Correction locale de la peau 2 — 16 octobre 2026

Statut historique : **Cas local admis — région complète en cours**. Cette
planche explique un résultat local ; elle n'accorde aucune admission globale
à la région ou aux couches du support moteur.

Les trois JSON de `inputs/` sont des copies strictement identiques des entrées
et résultats réels du replay `full-repair-003`. Le renderer vérifie leurs SHA-256,
les polygones calculés et les cinq certificats de quadrilatères entièrement
contenus dans le domaine source. Les chemins historiques présents dans ces
reçus restent des métadonnées : le rendu ne les ouvre pas.

Depuis ce dossier, avec Python, Matplotlib **3.11.2** et Shapely **2.2.0** :

```sh
python render.py /tmp/993-chart002-replay-001
```

Le dossier de sortie doit être neuf. La commande exporte la même planche en
PNG, SVG et PDF, puis un reçu liant le script, les entrées locales et les trois
exports. Elle n'exécute aucun calcul `native_infill`, remapping ou génération
de supports. `reference/` conserve le rendu rejoué avec ce script et son reçu ;
le PNG est identique à la planche locale acceptée. Les dates internes des
exports vectoriels peuvent varier à la reproduction.

Le [reçu de portabilité](portable-validation.json) conserve le rejeu après
extraction, l'identité du PNG et le refus d'une sortie déjà existante.
