# Région 008 — deux bandes déjà contenues dans la matière

Cette planche représente uniquement le chart 152 réellement rejoué. Les deux WKB retenus décrivent le domaine source D et la matière générée R. Les deux quads orange sont les bandes déjà incluses dans D selon les certificats rationnels conservés. Le renderer lit ces preuves et leurs liaisons SHA ; il ne les recalcule pas.

Le rôle source « upper » reste inchangé ; aucune interface « lower » n’est inventée. Le reçu conserve `generated_component_contact_flags = [false]`. Le périmètre est de 88 faces source et 24 triangles remappés, sans admission régionale ou globale. L’image ne remplace aucun contrôle de contacts ou d’exposition.

La vue entière échange seulement les axes d’affichage (Z horizontal, t vertical), à échelle égale. Le zoom conserve les coordonnées t/Z et montre les dimensions issues des coordonnées IEEE stockées, arrondies pour l’affichage. Les barres 5 mm et 0,2 mm sont contrôlées par les transformations réelles des axes.

Sources : [assessment](data/assessment.json), [chart authentique](data/authentic-chart.json), [liaisons](inputs.json), [plan](plan.json), [renderer](render.py). Le runtime de dessin existant est utilisé sans installation ; aucun module AM n’est importé.

Le premier lancement avec `-I` a refusé avant le rendu, car cette option exclut le site utilisateur où Matplotlib était déjà installé ; ce refus est conservé. Le second lancement a utilisé le même runtime de dessin que les planches existantes, sans installation, et a terminé avec le vrai code retour 0 en 34,120 s.

Exports réels : [PNG](render-002/source008-chart152-bandes-deja-contenues.png), [SVG](render-002/source008-chart152-bandes-deja-contenues.svg), [PDF](render-002/source008-chart152-bandes-deja-contenues.pdf). Le PDF contient une page ; le PNG et le PDF ont été inspectés. Les deux barres passent le contrôle de projection. Voir le [reçu de rendu](render-002/render-receipt.json), le [reçu d’exécution](execution-render-002.json) et la [revue locale](visual-qa.json). La publication reste en attente de la revue visuelle de root.

Le dossier `mpl-cache/` est un cache local incidental, exclu du manifeste de livraison. Le manifeste lie tous les petits fichiers de source, données, refus, exports et contrôles. Aucune géométrie ni preuve source n’a été modifiée.
