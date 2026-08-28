# Workflow d’une pièce

## 1. Qualification du besoin

Créer une issue et préciser : référence, fonction, variantes, disponibilité,
symptôme de défaillance, environnement, prix ou difficulté d’approvisionnement.

Sortie : candidat accepté ou refusé avec justification.

## 2. Provenance

Recenser les documents officiels, mesures directes, photographies et modèles
tiers. Toute source reçoit une URL, une date et une licence.

Sortie : aucune donnée d’origine inconnue dans le modèle publiable.

## 3. Mesure et acquisition

Choisir le moyen minimal donnant la précision nécessaire : pied à coulisse,
micromètre, jauge, gabarit, photogrammétrie ou scan structuré. Utiliser le modèle
de `templates/measurement-plan.md` pour préparer la séance.

Enregistrer ensuite le résultat sous forme vérifiable, dans
`catalog/measurements/`. Quand l’instrument a une sortie données, capturer
directement plutôt que recopier :

```bash
python3 scripts/capture_caliper.py --record catalog/measurements/meas-<pièce>.json \
    --dimension D01 --description "Alésage de l'œil" --port /dev/ttyUSB0 --repeats 3
```

Pour un jeu photogrammétrique, `scripts/capture_photoset.py` écrit un manifeste
et exige la référence d’échelle : sans elle, la reconstruction reste une forme,
pas une mesure.

Sortie : repères, unités, incertitudes et mesures critiques documentés, et une
fiche de mesure qui passe `make check`.

## 4. Reconstruction

- Importer le scan comme référence, jamais comme vérité absolue.
- Reconstruire plans, axes, cylindres, trous et interfaces en CAO paramétrique.
- Séparer les dimensions mesurées des dimensions supposées.
- Exporter un STEP et un 3MF de prototype.

Sortie : modèle maître éditable et fiche au statut `dimensionally_reviewed` au
maximum.

## 5. Prototype polymère

Imprimer rapidement, contrôler le montage, noter les jeux et photographier les
interfaces. Corriger le modèle maître plutôt que le maillage exporté.

Sortie : statut `prototype_fitted` seulement si la preuve est enregistrée.

## 6. Choix du procédé final

Comparer au minimum : polymère final, CNC, tôle, fonderie et fabrication additive
métal. Le titane est retenu seulement si masse, corrosion, géométrie ou petite
série justifient son coût.

Sortie : matrice de choix et devis comparables.

## 7. Calcul et DfAM

Définir cas de charge, contacts, précharges, température, vibration et durée de
vie. Adapter les surfaces, rayons, épaisseurs, évacuations de poudre, supports et
surépaisseurs d’usinage.

Sortie : modèle et demande de fabrication revus.

## 8. Fabrication et post-traitement

Conserver certificats, lot matière, traitement thermique, HIP éventuel, retrait
des supports, usinage et finition.

Sortie : pièce identifiée et reliée à une version précise de la CAO.

## 9. Contrôle et essais

Contrôle dimensionnel, inspection non destructive si nécessaire, montage statique,
essai progressif puis surveillance. Un essai réussi sur un véhicule ne prouve pas
la compatibilité universelle.

## 10. Publication

Mettre à jour la fiche, les limites connues et les preuves. La PR doit passer
`make check` et une revue humaine.
