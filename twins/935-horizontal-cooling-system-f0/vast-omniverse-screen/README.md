# Écran Vast / Omniverse du rotor horizontal 935

Cette campagne envoie un **modèle paramétrique de présélection**, pas le scan privé. Il reprend seulement l'enveloppe annulaire de `226,94` unités issue de l'inférence d'échelle, provisoirement utilisée comme `226,94 mm`, et dix pales visuelles. L'alésage de 34 mm, l'encastrement et tous les autres détails sont des hypothèses de modèle déclarées dans `scenario.json`.

Le calcul sur Vast produit un solide CAD de proxy, le maillage tétraédrique et dix résolutions CalculiX centrifuges à 8 500 tr/min ; un calcul modal non précontraint AlSi10Mg avec mise à l'échelle élastique des autres cartes ; masse, inertie, vitesse de pointe, énergie et extrapolations élastiques ; un indicateur de conduction radiale à 1 W par pale ; et un USD avec une variante par carte matière.

Le jeu couvre dix familles LPBF de `materials.json`. La liste mondiale des alliages imprimables reste ouverte. Les valeurs sont des comparateurs de cartes matière, jamais des admissibles de conception. WE43 conserve sa limite élastique à `null`.

Aucun résultat ne prouve le débit, la pression, la tenue en rotation, la fatigue, l'équilibrage, les jeux, les interfaces, la matière de l'original, la conformité à la 935 ou l'aptitude à fabriquer. Les cotes d'interface, les chargements, les coupons du procédé retenu, les équilibrages et les essais restent requis. Pour le titane, le dossier de fabrication devra documenter nuance, machine, orientation, traitement, usinage, inspection, fatigue et isolation galvanique.
