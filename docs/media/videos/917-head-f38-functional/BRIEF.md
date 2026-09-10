---
workflow: general-video
flow: automation
storyboard: no
message: "Montrer comment la culasse Porsche 917 F38 quatre soupapes fonctionne, se refroidit et se fabrique, avec ses résultats de validation visibles."
destination: desktop-engineering-review
aspect: 1920x1080
language: fr
audience: ingénieurs et fabricant LPBF
length: 24s
angle: démonstration technique avec vue de coupe
narration: no
---

## Intent

Film technique court du checkpoint F38 : vue extérieure conforme au scan,
écran cinématique des quatre soupapes et culbuteurs, recalcul du canal d'air,
puis verdict thermique et LPBF. Le rendu doit montrer les échecs mesurés et
ne jamais présenter le B-Rep facetté comme une CAO de production.

## Assets

- `assets/` — images et séquences calculées depuis la géométrie F38, adoptées localement avec leur provenance.

## Customizations

- Rotation lente de la pièce, ouverture en coupe et animation synchronisée des quatre soupapes.
- Superposition des champs thermiques, des flux d'air/huile et des critères LPBF.

## Notes

- Format horizontal 1920×1080 pour revue d'ingénierie sur ordinateur.
- Silence volontaire : aucune musique ni voix ne doit masquer le caractère technique.
- Toute métrique reste conditionnelle à l'échelle du scan tant qu'aucune référence physique n'est disponible.
- Les portes de qualification matériau, d'ajustement 917 et d'essais physiques restent séparées des validations virtuelles.
