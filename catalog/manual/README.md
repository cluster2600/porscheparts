# Registre quantitatif du manuel 993

`993-workshop-manual-measurements.json` regroupe les valeurs quantitatives
trouvées dans le manuel d'atelier Porsche 993 :

- les fiches `technical_data` déjà structurées par Porsche Fanatics ;
- les `torque_spec` des tableaux de couples ;
- les occurrences de cotes, jeux, limites, pressions, masses, angles et
  dimensions de filetage rencontrées dans les procédures OCR.

Le registre contient actuellement 2 496 enregistrements : 111 données
techniques, 195 couples et 2 190 occurrences quantitatives issues des 1 481
pages. Les occurrences peuvent se répéter lorsqu'une même valeur apparaît dans
une procédure ou dans plusieurs variantes ; elles portent toujours la page et
le contexte court qui permettent de revenir à la source.

Les pages 15, 19, 98, 108, 121, 137, 152–157, 177, 258 et 725–728 ont été
contrôlées visuellement dans le PDF local ; le reste est conservé comme
occurrence OCR à vérifier au moment où il sera utilisé.

Chaque ligne porte la page PDF. Les tableaux structurés sont des faits dérivés
et les occurrences OCR portent `ocr_unreviewed` : elles doivent être contrôlées
visuellement dans l'exemplaire autorisé avant d'être utilisées pour une CAO ou
une fabrication. Le registre n'est pas une copie du PDF et ne contient aucune
image ni le texte complet des procédures.

Régénérer depuis les données du projet Porsche Fanatics :

```bash
python3 scripts/extract_manual_measurements.py \
  --raw "/chemin/vers/porschefanatic.com/data/raw/993-manual/layout.txt" \
  --technical-data "/chemin/vers/porschefanatic.com/data/993-manual/technical-data.json" \
  --torque-specs "/chemin/vers/porschefanatic.com/data/993-manual/torque-specs.json" \
  --output catalog/manual/993-workshop-manual-measurements.json
```

La source de provenance est `SRC-PORSCHE-WORKSHOP-MANUAL-993`. Les valeurs du
manuel ne sont pas des mesures directes du projet : elles servent de références
constructeur et de critères pour une future campagne métrologique.
