# Reproduction

Restaurer les archives parentes PR229, PR231, PR232 et PR233 avec leurs manifestes sous work/. Copier les sources de cette phase dans un NOUVEAU répertoire de travail, sans exécuter directement dans evidence/ épinglé ni écraser un résultat publié.

polynomials.py construit les polynômes et contrôle les identités exactes. verify_models.py reconstruit séparément les aires natives et le Gram. Le reçu preliminary-publication.json atteste leurs versions publiées avant le calcul des boîtes. refine_bounds.py vérifie ces empreintes puis traite les seules feuilles indécises PR233. verify_refinement.py relit le résultat par Casteljau et le lecteur indépendant d'angles PR233 épinglé ; compare_bounds.py ne fait que comparer les bornes et réunir les statuts contigus.

Aucun de ces scripts ne crée ou lance de maillage natif ou de solveur CFD. Aucun ratio ponctuel nouveau n'est évalué. Les anciennes archives ne sont pas recopiées dans celle-ci ; les chemins et SHA parents sont conservés. Les sorties se placent près des copies des scripts : ne pas lancer sur les preuves originales.
