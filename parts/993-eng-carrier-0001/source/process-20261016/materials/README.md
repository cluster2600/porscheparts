# Reproduction des références matériau

`fetch_luo_sources.py` télécharge seulement les trois petits fichiers publics nommés dans `sources.json` (total environ4,25Mo), vérifie taille/SHA256 puis extrait exclusivement les quatre classeurs attendus. `extract_luo_rt.py INPUT NEW_OUTPUT` vérifie à nouveau les sources et reproduit les quatre lois de sensibilité du premier jeu de procédé publié. Les versions minimales installées pour ce contrôle sont épinglées dans `requirements.txt`.

Les résultats committables, la licence des données, les hypothèses de conversion et les limites numériques sont dans [material-luo-set1](../material-luo-set1/README.md). Les archives sources brutes restent dans `work/`.
