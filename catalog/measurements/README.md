# Registre des mesures

Une fiche JSON peut enregistrer soit une séance de mesure physique, soit une
spécification quantitative publiée par un document de référence. Une séance
physique contient sujet, repères, instruments, lectures brutes et incertitude.
Une spécification documentaire contient sa source, sa page, son texte de valeur
et son statut d'extraction ; elle ne remplace pas une séance instrumentée.

Le registre ne remplace pas le plan de mesure
(`templates/measurement-plan.md`), elle en conserve le résultat sous une forme
vérifiable par machine.

Le validateur refuse notamment une valeur qui ne correspond pas à ses propres
échantillons, une incertitude plus fine que la résolution de l’instrument, une
lecture attribuée à un instrument non déclaré, et un niveau de preuve `A` sans
répétitions ni état d’étalonnage connu.

Créer une fiche depuis `templates/measurement-record.json`, ou la remplir
directement depuis l’instrument :

```bash
python3 scripts/capture_caliper.py --record catalog/measurements/meas-<pièce>.json \
    --dimension D01 --description "Alésage de l'œil" --port /dev/ttyUSB0 --repeats 3
```

Une valeur tapée à la main reste enregistrée comme telle : `manual_entry`, jamais
`instrument_stream`.

Le registre documentaire issu du manuel Porsche 993 est
[`MEAS-MANUAL-993-ALL.json`](MEAS-MANUAL-993-ALL.json). Il reprend 2 496 valeurs
avec page et provenance. Les valeurs `ocr_unreviewed` doivent être vérifiées
dans l'exemplaire autorisé avant de servir à une CAO ou une fabrication.

La campagne physique prête à être exécutée et son ordre de priorité sont décrits dans
[`docs/MEASUREMENT_CAMPAIGN.md`](../../docs/MEASUREMENT_CAMPAIGN.md). Tant qu'un
contributeur n'a pas fourni une pièce, un véhicule et les lectures brutes, le
registre des séances physiques reste vide : il vaut mieux zéro mesure
instrumentée vérifiable qu'une cote inventée.

Régénérer la fiche documentaire après une mise à jour du registre du manuel :

```bash
python3 scripts/import_manual_measurements.py
```
