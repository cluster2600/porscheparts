# ADR 0003 — Jumeau numérique fédéré par zones fonctionnelles

## Statut

Accepté le 29 août 2026.

## Contexte

Le projet doit tester numériquement les pièces dans leur environnement avant
impression. Un maillage complet de voiture, même visuellement convaincant, ne
donne ni les interfaces, ni les jeux, ni l'incertitude nécessaires à un contrôle
de montage.

## Décision

Le jumeau 993 sera une fédération de sous-jumeaux fonctionnels. Chaque zone
contient la pièce candidate, la géométrie hôte, les pièces voisines utiles et
des règles d'acceptation calculables.

Les niveaux de fidélité sont cumulatifs :

| Niveau | Contenu | Usage autorisé |
|---|---|---|
| `F0_reference` | forme visuelle, échelle ou provenance incomplète | orientation seulement |
| `F1_envelope` | enveloppe à l'échelle et repère documenté | encombrement grossier |
| `F2_interface` | interfaces mesurées, tolérances et incertitudes | montage, jeu, collision |
| `F3_engineering` | matériaux, contacts, charges et conditions aux limites | FEA/CFD exploratoire |
| `F4_correlated` | résultats corrélés à des mesures ou essais physiques | décision documentée dans le domaine validé |

Le repère véhicule global suit la convention du projet : origine sur le plan de
symétrie, à la verticale du centre d'essieu avant sur le plan de sol nominal ;
`X` vers l'avant, `Y` vers la gauche et `Z` vers le haut. Un sous-jumeau peut
avoir un repère local, mais sa transformation vers le repère véhicule doit être
documentée avant intégration au jumeau global.

La géométrie dimensionnelle maîtresse reste en CAO solide ouverte et révisable :
scripts build123d/CadQuery, FreeCAD et STEP. FreeCAD Assembly sert à la revue des
contraintes et des mouvements. Une scène OpenUSD pourra fédérer les zones pour
la navigation et les variantes ; elle n'est jamais la source des cotes.

Chaque test utilise une marge au pire cas incluant les incertitudes de mesure.
Un sous-jumeau ne peut atteindre `digitally_checked` si une interface requise est
absente ou si la précision de sa géométrie est inconnue.

## Conséquences

- La première cible est le logement de cache d'interrupteur du tableau de bord.
- Le véhicule complet se construit progressivement à partir des zones utiles.
- Un scan public sans échelle peut habiller la scène au niveau `F0`, jamais
  qualifier une pièce.
- Neural Concept reste une couche ultérieure de substitution FEA/CFD ; il faut
  d'abord un corpus de géométries, paramètres et résultats cohérents.

