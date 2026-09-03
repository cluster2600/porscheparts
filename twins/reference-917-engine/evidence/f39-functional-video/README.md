# Vidéo de fonctionnement F39

`917-head-f39-how-it-works.mp4` est une animation technique silencieuse de
26 secondes en 1920×1080 à 30 images/s. Elle montre l'enveloppe analytique, le
mouvement d'écran des quatre soupapes, le cycle admission/fermeture/échappement
et les chemins d'évacuation de chaleur par air forcé et huile locale.

La vidéo est une explication cinématique liée aux rapports F39. Elle n'est ni
une simulation transitoire de combustion, ni une CHT complète, ni une preuve
de distribution réelle, de fatigue, d'impression LPBF ou de banc moteur. Le
profil de came et les interfaces Porsche 917 ne sont pas mesurés.

Fichiers de contrôle :

- `917-head-f39-how-it-works-contact-sheet.png` : quatre images extraites du MP4;
- `917-head-f39-how-it-works-poster.png` : image de la phase fermeture;
- `publication.json` : codec, durée, dimensions, empreintes et portes fermées.

Le projet HyperFrames reproductible est sous
`videos/917-head-f39-function`. Exécuter `npm run check` puis `npm run render`.
