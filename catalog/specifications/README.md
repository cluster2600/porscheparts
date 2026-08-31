# Registre des spécifications documentaires

Ce registre conserve les valeurs publiées dans des sources documentaires :
dimensions générales, capacités, rapports de transmission, couples et angles de
serrage. Il reste distinct de `catalog/measurements/`, qui est réservé aux
séances instrumentées avec lectures brutes et incertitudes.

Une transcription OCR n'est pas une mesure validée. Les enregistrements importés
depuis PorscheFanatics conservent donc la chaîne source, la page et l'unité
brutes, avec l'état `ocr_transcription_unverified`. Ils peuvent guider un modèle
documentaire, mais ne doivent pas piloter une géométrie de fabrication avant
contrôle dans la source primaire ou mesure physique.

Régénérer les deux instantanés depuis un checkout PorscheFanatics :

```bash
python3 scripts/import_porschefanatics_specs.py \
  --technical-data /chemin/data/993-manual/technical-data.json \
  --torques /chemin/data/993-manual/torque-specs.json
```

