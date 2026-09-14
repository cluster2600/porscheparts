# CalculiX F0 — piston CP1

`calculix-thermomechanical-screen.json` est le résumé public de six calculs
réellement exécutés sur le X1 : statique froide et thermo-mécanique séquentielle
stationnaire pour trois maillages C3D10 du STEP F0 exact.

Les sorties brutes `.inp`, `.dat`, `.frd`, `.msh` et `.log` sont volumineuses et
restent hors Git. Le rapport conserve leur taille et leur SHA-256, ainsi que
l'identité de l'image locale. Il ne contient ni secret ni géométrie nouvelle.

Le solveur reçoit `5 kW` sur les nœuds extérieurs de calotte, un puits idéal à
`120 °C` sur la galerie, un puits idéal à `160 °C` sur la jupe et l'enveloppe
axiale synthétique pression plus inertie déjà définie dans le F0. Ces valeurs ne
sont pas des mesures M64/60. La fixation totale de l'alésage d'axe est une borne
conservatrice qui surcontraint la dilatation thermique.

Le contrôle reproductible du rapport est :

```bash
python3 twins/993-m64-60-piston-gallery-f0/source/verify_calculix_thermomechanical_report.py
```

Les portes numériques vérifient seulement la terminaison et la sensibilité de
maillage. Toutes les portes matériau à chaud, fatigue, fabrication et moteur
restent fermées.
