---
workflow: general-video
flow: automation
storyboard: no
message: "Montrer le principe de fonctionnement de la culasse Porsche 917 F39 à quatre soupapes, son refroidissement air/huile et les limites exactes de sa validation numérique."
destination: desktop-engineering-review
aspect: 1920x1080
language: fr
audience: ingénieurs mécaniciens et fabricant LPBF
length: 26s
angle: animation technique en coupe
narration: no
---

## Intent

Vidéo technique courte montrant l'enveloppe analytique F39 issue du seul scan,
le mouvement d'écran des quatre soupapes, les phases admission/fermeture/
échappement, puis l'évacuation de chaleur par huile locale et air forcé entre
les ailettes. Les chiffres visibles proviennent des rapports F39.

## Assets

- `assets/f39-exterior.png` — rendu du B-Rep analytique F39.
- `assets/f39-section.png` — vue de coupe du volume reconstruit.
- `assets/f39-cutaway-*.png` — écrans cinématiques analytiques réutilisés de F38.
- `assets/f39-cooling.png` — optimisation thermique F39.
- `assets/f39-lpbf.png` — audit fabricabilité du scan F39.

## Customizations

- Cycle visuel admission → fermeture/charge thermique → échappement.
- Mouvement synchronisé de deux soupapes d'admission puis deux d'échappement.
- Air forcé animé en bleu, transfert d'huile local en vert et charge thermique en orange.

## Notes

- Silence volontaire pour une revue technique.
- La levée affichée est un écran géométrique de 12 mm; le profil de came réel n'est pas mesuré.
- Les méthodes F39 sont des modèles de présélection, pas une CHT complète ni une corrélation de banc.
- La vidéo ne donne aucune autorisation d'impression métal ou de démarrage moteur.
