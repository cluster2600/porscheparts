# Endurance simultanée — troisième essai

**PASS**, du 28 septembre 2026 à **21:25:42,527 UTC** jusqu’à **21:55:42,702 UTC**,
soit **1 800,176 secondes**. Le [rapport intégral](report.json), les
[événements](events.jsonl) et le [résumé](summary.json) conservent les mesures.

- 30 lots de quatre requêtes Qwen simultanées : **120 succès**, 15 360 tokens de sortie.
- **53 chaînes PicoGK, contrôles métal, assemblage USD et rendu OVRTX** : 18 témoins de 20 mm, 18 de 30 mm et 17 de 40 mm.
- **121 mesures**, intervalle maximal de 15,412 s ; aucun OOM, aucune erreur et aucun redémarrage de Qwen ou Kit.
- VRAM maximale : GPU 0 **91,992 %**, GPU 1 **91,285 %**, GPU 2 **5,476 %**, GPU 3 **3,951 %** ; RAM disponible minimale **793,404 Go** (octets décimaux).
- Latence des requêtes : médiane **5,425 s**, P95 au rang supérieur **11,013 s**, maximum **19,507 s**. Débit moyen par requête **20,305 tokens/s** ; débit rapporté aux trente minutes, temps d’attente compris, **8,533 tokens/s**.

Les [empreintes vérifiées sur Vast](artifact-verification.json) couvrent
**1 113 artefacts**, 53 reçus de fin et 53 images PNG. Les **1 219 fichiers**
correspondent à la [copie persistante de Kali2](kali2-sync-verification.json),
ainsi que le rapport final et les événements. Le service de synchronisation
était actif ; ses quatre redémarrages précédents appartiennent au remplacement
de l’ancien mécanisme de copie et ne sont pas des redémarrages de Qwen ou Kit.

Le [deuxième essai](../soak-attempt-2/report.json) a été interrompu pour le
diagnostic du dashboard. Le [premier](../soak-attempt-1/report.json) conserve
l’échec du seuil mémoire avant fixation explicite de la limite Qwen à 0,90.

Les compteurs de requêtes ci-dessus appartiennent uniquement au test. Les
mesures de ressources incluent l’activité utilisateur éventuellement présente
sur la station. Quatre requêtes courtes ne valident pas quatre contextes pleins
de 262 144 tokens. Les contrôles métal restent des témoins logiciels ; aucune
fabrication physique ni simulation thermomécanique calibrée n’est qualifiée.
La machine reste allumée sur demande explicite de l’utilisateur.
