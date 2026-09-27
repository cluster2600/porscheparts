# Mission : reconstruire la culasse 935 depuis le brut

Tu pilotes une R&D non commerciale. Aucun modèle 993 ou ancien résultat de
culasse ne doit servir d'entrée. Ne déduis pas les millimètres des dimensions
attendues. Le scan ne prouve pas les galeries cachées, les matériaux ou les charges.

Lis `results/intake/intake.json` et les propositions CAD-Recode placées par
l'opérateur dans ce workspace. Produis un script CadQuery `candidate-1.py`
contenant le résultat dans `r`. Les coordonnées de ce script sont celles de
CAD-Recode : nuage normalisé multiplié par 100 ; le worker annule ce facteur.

Pour demander une exécution, écris `requests/export-1.json` :
`{"stage":"export","attempt":1}`. Le dispatcher extérieur exécute seulement
ce contrat. Lis `results/export-1/execution.json`, puis demande l'évaluation
avec `requests/evaluate-1.json` : `{"stage":"evaluate","attempt":1}`.
Lis le rapport `results/evaluate-1/report/deviation.json`.

Maximum trois propositions (1, 2, 3). Ne remplace pas une proposition déjà
exécutée. Corrige la syntaxe à partir des erreurs ; ne prétends pas améliorer
une géométrie que tu n'as pas mesurée. Ne réécris aucun résultat, seuil, empreinte
ou donnée source. Arrête après trois échecs et explique les défauts persistants.

Un STEP valide est seulement une reconstruction candidate. Les écarts restent
en unités OBJ. Toute promotion dimensionnelle, propriété physique, fabrication
ou compatibilité 993 exige des preuves et une revue humaine. Aucun achat,
aucune API payante, aucun accès aux secrets ou aux anciennes géométries.
