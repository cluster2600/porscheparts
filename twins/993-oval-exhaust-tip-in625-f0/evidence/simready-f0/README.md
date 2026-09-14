# SimReady F0 — embout ovale IN625

Le STEP parametrique a ete converti avec `usd-convert-cad 0.2.0`, traite par les Content Agents Material et Physics, puis conforme et valide avec la suite NVIDIA documentee.

La sortie du LLM n'a pas ete acceptee telle quelle. L'agent avait propose une identite « acier inox poli », des coefficients de frottement, une restitution et une scene de gravite sans source. Le script `sanitize_simready_asset.py` les retire et ne conserve que :

- un proxy visuel OpenPBR argent explicitement nomme IN625 ;
- la masse analytique `0,40638 kg` ;
- la densite de criblage `8 440 kg/m3` ;
- un materiau physique limite a cette densite, sans frottement ni restitution ;
- un corps rigide et un `convexHull` reserves a l'inspection du prop isole.

L'asset final passe Minimum OpenUSD, NVIDIA Asset Validator, Geometry, Physics et le profil `Prop-Robotics-Neutral 1.0.0`. `RB.MB.001` reste non bloquant car la source ne contient qu'un composant. Une ligne de prise a ete placee apres revue visuelle sur les deux parois externes opposees a mi-longueur ; elle ne constitue pas un essai de prehension robotique.

`oval-tip-in625-f0-ovrtx.png` est un rendu OVRTX du USD final sans lumiere ajoutee. `grasp-preview-overlay.png` conserve les quatre vues utilisees pour choisir la ligne de prise. `simready-validation-summary.json` lie les artefacts et rapports par SHA-256.

PhysicsNeMo `2.2.0` a passe un smoke test tensoriel CUDA. Aucun surrogate n'a ete entraine : les cas CFD et LPBF ne sont pas suffisamment converges et correles pour produire un modele de validation.

Le passage SimReady prouve la coherence d'un asset isole, pas le montage sur le silencieux, la compatibilite avec la jupe, le comportement thermique, la fabricabilite ou le fonctionnement sur vehicule.

Les rapports de service et USD intermediaires bruts restent hors Git sous `work/`.
