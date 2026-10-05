# D2 terminé à 1020 : comparaison encore inconclusive

La reprise unique autorisée a terminé **1001–1020**, depuis le checkpoint1000
natif vérifié, sans rejouer le témoin. La branche prolongée totalise donc
**40 + 20 itérations complètes** ; le témoin conserve ses60 itérations d'origine.
Géométrie, partitions, MRF, conditions limites, numérique et critères restent
inchangés. **La pression ne satisfait toujours pas les critères numériques et
de stationnarité.** Le lot est clos, ressources libérées, aucune suite1040.

[Retour à l'étude](README.md) · [Accueil](../../README.md) ·
[Lot D2 initial, preuves conservées](D2_EXECUTION.md) ·
[Préparation et protocole1000→1020](D2_COMPLETION_PREPARATION.md)

## Exécution et ressources

Le [préflight natif](results/runtime/D2-supervisor-native-input-verification.json)
contrôle les96 fichiers de la copie préparée, les16 fichiers de capsule, les12
entrées natives réutilisées et les sélections communes. Une première entrée
du superviseur s'est arrêtée avant création du conteneur : l'import Python
avait ajouté un cache dans la capsule vérifiée. La capsule finale et le
démarrage `python3 -B` corrigent ce point ; aucun solveur n'avait été lancé.
Le transfert initial comportant des fichiers auxiliaires macOS a aussi été
écarté avant lancement. Ces préparations ne modifient aucun état CFD.

Le [reçu d'exécution](results/runtime/D2-completion-execution-receipt.json)
contient exactement trois commandes, toutes terminées avec code0 :

| Commande native | Temps mesuré | Plafond de phase |
|---|---:|---:|
| Un seul `foamRun -parallel`, quatre rangs,1001–1020 | 67,007 s | 110 s |
| `reconstructPar -time 1000,1020` | 12,875 s | 25 s |
| Contrôle final et analyse des deux fenêtres/domaines | 16,724 s | 30 s |

Le [superviseur](source/launch_d2_completion.py) et le
[runner de branche unique](source/run_d2_completion.py) utilisent une seule
date limite monotone pour admission, copie, solveur, reconstruction, analyse,
archivage et libération. **Temps global réellement mesuré : 110,505 s sous
240 s**, [preuve native expurgée](results/runtime/D2-completion-launcher-receipt-sanitized.json).
CPU réel plafonné à4, cpuset de quatre cœurs physiques distincts, RAM+swap
**5 GiB**, réseau absent, sources/préparation/témoin/sélections en lecture seule.
Admission : 11 294 654 464 octets disponibles,12 CPU logiques, charge1,369.
Pic RSS d'enfant460 348 KiB : cette valeur n'est pas une mesure agrégée.

Le conteneur est libéré le4 octobre2026 à **21:26:53 UTC**. La
[confirmation indépendante à21:31:28 UTC](results/runtime/D2-completion-release-confirmation.json)
constate son absence et les services préexistants inchangés. Aucun service
tiers arrêté, accès persistant ajouté, installation, location ou dépense.
Aucune réservation Mac/Kali2 n'est maintenue.

## Validation du checkpoint et de la fenêtre

Le [certificat natif1020](results/runtime/D2-completion-native1020-verification.json)
vérifie32 fichiers : `p/U/k/omega/nut/phi/Uf` et `uniform/time` sur quatre rangs,
cardinalités correctes, valeurs finies, index/temps1020 concordants. Les
champs sériels reconstruits couvrent chacun680 596 cellules. Le log contient
exactement vingt pas complets1001–1020 et `End` ; chaque table finale possède
les vingt mesures consécutives requises. La fenêtre n'est plus manquante.

Le [résumé final natif](results/cfd/D2-extended1020-flow-summary.json) reste
**non admis** :

| Critère original sur1001–1020 | Mesure | Limite | État |
|---|---:|---:|---|
| Maximum du résidu initial p | 0,0106874 | 0,0001 | Rejet |
| Maximum du résidu initial d'une composante U | 0,00184464 | 0,00001 | Rejet |
| Maximum du résidu initial k | 0,00443590 | 0,0001 | Rejet |
| Maximum du résidu initial ω | 0,000003672 | 0,0001 | Passe |
| Déséquilibre de débit maximal | 0,0000340581 | 0,005 | Passe |
| CV du débit de frontière | 0,00115817 | 0,01 | Passe |
| CV du couple | 0,00115130 | 0,02 | Passe |

Les champs finis, les mesures finies et le sens de débit déclaré passent.
Le témoin réutilisé conserve ses dix critères originaux et ses sept contrôles
supplémentaires admis. La branche prolongée échoue encore quatre des sept
contrôles de stationnarité :

| Contrôle supplémentaire | Mesure | Limite |
|---|---:|---:|
| Écart-type pression commune, fenêtre1001–1020 | **6,1701 Pa** | 2 Pa |
| Écart des moyennes pression981–1000 /1001–1020 | **15,5991 Pa** | 2 Pa |
| RMS volumique pression du cœur1000→1020 | **10,3471 Pa** | 1 Pa |
| RMS volumique vitesse du cœur1000→1020 | **0,381724 m/s** | 0,1 m/s |

P99/max des variations locales du cœur :30,170 /195,111 Pa et1,337 /60,557 m/s.
Les variations des zones fixes et les écarts locaux entre domaines figurent
dans l'[analyse complète](results/cfd/D2-completed-pair-analysis.json).
Ces indicateurs restent des variations d'itérations SIMPLE stationnaires,
sans temps physique ; ils ne démontrent pas une oscillation réelle du moteur.

## Comparaison descriptive, sans admission

Sur les vingt mesures natives1001–1020 :

| Observable commune | Témoin réutilisé | Prolongé terminé |
|---|---:|---:|
| Débit orienté au plan commun | 1,152300435 m³/s | 1,153996582 m³/s |
| Pression statique moyenne de bande | 85,647426 Pa | 82,145799 Pa |
| Couple du fluide sur le rotor | −3,867106500 N·m | −3,822585586 N·m |
| Puissance mécanique du rotor, régime supposé6000 tr/min | 2429,7747 W | 2401,8014 W |

Écarts symétriques : débit0,14698 %, couple/puissance1,15127 %, pression
3,501627 Pa pour une bande descriptive5 Pa. **Les quatre bandes descriptives
passent, mais leurs prérequis numériques et de stationnarité échouent.**
Le statut demeure `inconclusive_domain_comparison` ; aucune sensibilité physique
stationnaire du domaine, indépendance générale ou amélioration airflow n'est
établie. La pression de bande n'est pas une hausse de pression entre ports.

À1020, reflux grossier : témoin0,123976 m³/s ; prolongé dans le plan commun
0,107130 m³/s ; prolongé à la frontière éloignée0,125093 m³/s. Le reflux
persiste à la frontière déplacée. L'écart RMS entre champs du cœur des deux
domaines est38,6723 Pa et1,49356 m/s ; ces snapshots non admis ne qualifient
pas un effet stationnaire du domaine. Vitesse locale maximale finale128,760 m/s,
soit Mach estimé0,3754 avec343 m/s : la compressibilité n'est pas qualifiée par
ce modèle incompressible MRF.

![Traces natives D2, reprise20 pas séparée](results/cfd/D2-completed-native-traces.png)

[Provenance du rendu](results/cfd/D2-completed-native-traces.json) : uniquement
les mesures et résidus des60 pas du témoin,40 pas initiaux prolongés et20 pas
repris. Aucune extrapolation ni image inventée. La séparation1000/1001 est
visible et les axes portent les unités.

## Conservation et reproduction

L'[archive privée transférée et vérifiée](results/runtime/D2-completion-native-archive-verification.json)
contient **181 fichiers**,352 214 760 octets compressés, SHA256
`5b2591992c93d92781f871fb6f69a86befb991938ae9807d0af83ecad67c3c6f`.
Tous les membres sont vérifiés nativement puis après transfert. Les champs
natifs de partitions1000 et1020, maillages, logs séparés, tables et capsule
exacte sont conservés ; le brut du scan n'est pas inclus. Aucun champ, maillage
ou table native brute n'est publié dans le dépôt.

L'[analyse composée](results/cfd/D2-completion-comparison-provenance.json)
déclare explicitement40 +20 pas. Les logs originaux restent distincts ; le
bloc1001 incomplet de l'ancien log n'est pas un pas complet. Seules trois
vues de tables dérivées assemblent les lignes natives, avec contrôle de la
mesure1000 dupliquée et SHA des deux sources. Elles ne sont pas présentées
comme un log natif unique. Le témoin est réutilisé sans solveur.

La [capsule réellement exécutée](parameters/D2-completion-executed-capsule-manifest.json)
est conservée avec ses sources et configs exactes. `make fan-program-check`
vérifie les identités, les preuves natives et les limites de qualification.
Les tests logiciels couvrent la branche unique, les limites240 s/4 CPU/5 GiB,
l'isolation avant solveur, l'arrêt du seul conteneur possédé, le timeout sans
relance, l'archivage partiel non qualifié et le démarrage sans cache Python.
Un test refuse explicitement de promouvoir ces résultats lorsque les bandes
descriptives passent mais que la pression reste non stationnaire.

**Arrêt final1020 respecté.** Identité935/993, unités du scan, dimensions et
interfaces installées, modèle compressible, parois, matériaux, fatigue,
simulation process LPBF qualifiée et jumeau NVIDIA physique validé restent
ouverts conformément aux autres étapes documentées. Aucun résultat présent
n'autorise la fabrication ou la mise en service.
