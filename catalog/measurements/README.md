# Registre des mesures

Une fiche JSON enregistre une séance de mesure : sujet, repères, instruments,
lectures brutes et incertitude. Elle ne remplace pas le plan de mesure
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
