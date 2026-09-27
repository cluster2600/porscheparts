# Session Vast — résultats du 26 septembre 2026

**La stack fonctionne sur une fixture. La reconstruction de la culasse est rejetée.**

## Culasse 935, depuis le brut original

- Brut inchangé, SHA-256 contrôlé. Aucune ancienne géométrie, matière ou interface reprise.
- Trois générations GPU : un solide invalide, deux STEP valides au sens topologique.
- Candidat 2 : p95 scan → CAO 27,321 et CAO → scan 23,414, unités OBJ inconnues.
- Le rendu séparé montre la perte des ailettes, ouvertures et détails. La superposition initiale mélangeait ces erreurs avec le scan dans une seule couleur ; ce n'était pas une reconstruction réussie.
- [Scan seul](run/omniverse/raw-scan-only.png) · [Candidat rejeté](run/omniverse/candidate-only.png) · [Scène USD de comparaison](run/omniverse/comparison.usda).
- Les références de la scène sont relatives et survivent au rapatriement. Les échelles 0,001 sont des conventions visuelles issues du convertisseur, pas une mesure physique.

## Exécution réelle sur la VM

CAD-Recode GPU, Nemotron FP8 avec appel d'outil, OpenClaw avec lecture/écriture isolées, Qwen2.5-VL avec entrée image, OVRTX avec rendu PNG, Material puis Physics : exécutés. Les services restent sur loopback ou réseau Docker interne.

Le VLM a mal identifié une mire rouge 64 × 64, puis correctement identifié rouge et bleu en 256 × 256. La revue OpenClaw a inventé un dépassement de seuil avant correction. Material a initialement choisi du plastique pour le bloc en aluminium ; une consigne matière explicite a corrigé ce choix. Ces erreurs et les sorties antérieures sont conservées.

## Contrôle synthétique indépendant

Bloc choisi pour le test : 20 × 40 × 60 mm, aluminium, densité 2700 kg/m³. Après correction de la matière et normalisation des unités : volume 0,000048 m³, masse 0,1296 kg, gravité 9,81 m/s², un corps rigide et collision active. Le contrôle rejette l'ancienne version plastique et accepte la version corrigée.

Les validateurs USD, géométrie, physique et le profil Prop-Robotics-Neutral passent sur la fixture finale. Une ligne de préhension traverse ses deux faces opposées après inspection visuelle et prise en compte de l'échelle locale. Aucun essai réel de préhension n'est revendiqué. Ce test ne fournit aucune matière, charge ou validation de culasse.

## Limites et suite utile

Le passage global de cette culasse dans les 256 points de CAD-Recode ne donne pas une CAO utilisable. Pour continuer la reconstruction : définir les repères et l'échelle depuis des mesures, puis reconstruire séparément les surfaces et fonctions identifiées sur le brut. Aucune donnée manquante n'est remplacée par un résultat du LLM.

Les calculs thermiques/mécaniques de culasse restent bloqués par les entrées d'ingénierie manquantes. Les benchmarks analytiques CalculiX/OpenFOAM antérieurs qualifient des cas synthétiques, pas cette culasse. PhysicsNeMo n'a pas été entraîné.

Neuf tests ciblés passent ; les sept tests géométriques ont été rejoués après la correction des références USD. `make check` : 912 tests, trois skips, puis blocage sur le fichier PET préexistant absent `/tmp/kat517-993.txt`.

VM 52810563 : 1,924074 USD/h annoncé, transferts en supplément. Suppression programmée à **00:53:06 heure de Zurich le 27 septembre** par le garde local, qui nécessite que le Mac et OpenBao restent disponibles. L'extinction invitée est programmée séparément et ne suffit pas à arrêter la facturation du stockage. Les résultats sont sauvegardés localement.
