# Intégrer une recherche

[Dossier documentaire](README.md) · [Registre](dossier.json)

1. Ajouter une source avec identifiant stable, éditeur/auteur, URL directe,
   langue, édition/date et statut d'accès. Distinguer lecture directe, extrait,
   résumé, copie et résultat de recherche. Indiquer la page PDF et imprimée,
   figure ou message/date. Ne pas stocker de justificatif personnel.
2. Relier les reprises à leur origine avec `origin_source_id`. Noter les limites
   d'indépendance et garder `independent_of_project=false` pour les productions
   du projet, PorscheFanatics et leurs dérivés. Ne pas compter les copies comme
   de nouvelles confirmations.
3. Ajouter chaque proposition comme `claim` avec variante et portée. Une source
   absente produit une question de recherche ; une source inaccessible conserve
   un statut de lecture non vérifiée. Ne pas annoncer une équivalence 935/993
   sur une photo ou un nom commercial.
4. Ajouter un paramètre numérique avec unité, variante, conditions, locator et
   incertitude. Écrire `null` si inconnu. Distinguer diamètre extérieur, diamètre
   carter et jeu radial ; vitesse vilebrequin, ventilateur et alternateur ;
   pression statique/totale et débit volumique/massique. Une valeur dérivée doit
   garder sa formule et ses entrées dans `conditions`.
5. Ouvrir une contradiction en pointant les records concernés. Documenter une
   résolution avec son évidence sans effacer la valeur d'origine. Séparer
   variantes et montages avant de supposer une erreur de source.
6. Compléter la couverture avec langues réellement lues, requêtes et dates,
   sites/forums, pages retenues/rejetées et blocages d'accès. Une recherche
   terminée dans son périmètre ne prouve pas l'exhaustivité du Web.
7. Réviser la synthèse du dossier, exécuter les contrôles puis publier sur la
   branche de la PR brouillon. Conserver les sources de géométrie et le scan
   privés tant que leur licence de réutilisation/publication n'est pas établie.

Les champs `engineering_validation` et `engineering_use_approved` restent faux
dans ce registre. Une donnée OEM documentée peut servir d'entrée proposée pour
une étude ; accepter un modèle fonctionnel demande toujours les preuves du
[plan de validation](../VALIDATION_PLAN.md), les interfaces mesurées et la revue
d'ingénierie. Une modification de catalogue se traite séparément avec ces
preuves, sans convertir une synthèse bibliographique en pièce libérée.
