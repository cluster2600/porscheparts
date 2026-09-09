---
format: 1920x1080
duration: 24s
message: "La F38 conserve enfin la morphologie du scan, mais les écrans actuels refusent encore la simulation structurelle, l'impression et le démarrage."
arc: Géométrie → Fonctionnement → Refroidissement et résistance → Verdict industriel
audience: ingénieurs et fabricant LPBF
mode: autonomous
---

## Frame 1 — Peau conforme au scan

- status: outline
- src: compositions/frames/01-brep.html
- duration: 5s
- transition_in: cut
- poster: 3.0s
- scene: Rotation lente de la culasse F38 reconstruite, avec enveloppe du scan en filaire et trois critères géométriques.

Ouvrir sur la peau F38 issue du scan. Les badges affichent l'épaisseur minimale, le volume piégé et la fraction de supports issus du rapport F38. Blueprint `camera-journey`; règle `multi-phase-camera`.

## Frame 2 — Coupe fonctionnelle

- status: outline
- src: compositions/frames/02-cutaway.html
- duration: 7s
- transition_in: cut
- poster: 4.0s
- scene: Vue de coupe animée montrant quatre soupapes, culbuteurs, galeries d'huile et trajet d'air entre ailettes.

Faire de la coupe le cœur explicatif : les quatre soupapes se déplacent par paires, les axes et culbuteurs restent visibles, l'huile est codée cyan et le refroidissement externe bleu. Les trajets se dessinent seulement sur les géométries correspondantes. Blueprint `camera-journey`; règles `svg-path-draw` et `multi-phase-camera`.

## Frame 3 — Double validation

- status: outline
- src: compositions/frames/03-validation.html
- duration: 7s
- transition_in: cut
- poster: 4.2s
- scene: Comparaison OpenFOAM contre corrélation analytique, puis structure et fabrication LPBF.

Les valeurs proviennent des rapports F38 : coefficient d'échange, température projetée et échec du maillage structurel. Les barres comparent les deux méthodes sans masquer leur écart de perte de charge; un encart sépare résultats numériques et essais physiques manquants. Blueprint `dataviz-countup`; règles `stat-bars-and-fills` et `svg-path-draw`.

## Frame 4 — Décision fabricabilité

- status: outline
- src: compositions/frames/04-verdict.html
- duration: 5s
- transition_in: cut
- poster: 3.0s
- scene: Culasse en orientation d'impression avec matrice de coupons et verdict conditionnel.

Terminer sur la pièce orientée LPBF, ses surfaces à usiner et le nombre de coupons à chaud. Montrer clairement deux colonnes : preuves numériques obtenues et portes physiques encore fermées. Le dernier plan ne dit jamais « validée moteur » tant que l'échelle et les interfaces 917 ne sont pas mesurées. Règle `stat-bars-and-fills`.
