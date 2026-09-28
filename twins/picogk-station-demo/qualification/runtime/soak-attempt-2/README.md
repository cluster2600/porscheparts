# Deuxième essai interrompu

Le [rapport brut](report.json) porte le statut `FAIL` après **168,669 s**,
avec les seules erreurs `interrupted by signal 15` et `qualification interrupted`.
L’opérateur a interrompu le contrôleur pour diagnostiquer l’absence de réponse
dans le dashboard ; ce résultat ne prouve pas une panne de ressources.

Les [événements](events.jsonl) conservent 12 requêtes réussies, 1 536 tokens de
sortie et cinq chaînes terminées. La VRAM maximale atteignait 91,026 % et la
RAM disponible restait supérieure à 794,304 Go. Cet essai ne constitue pas une
qualification de trente minutes ; le [troisième essai](../soak/README.md) la réalise.
