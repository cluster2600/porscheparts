# Prescription finale avant application

Branche codex/bionic-turbo-native-face-tets-audit-20261013 depuis 8318891519d7271186115cca007d9e0b12eddcaa ; CI main exacte 38435448947 verte selon base-readback.json. Le brouillon historique et les sources extraites pendant la CI PR252 restent conservés.

Appliquer method.md avec check_face_tets.py puis verify_face_tets.py seulement après succès complet du primaire. Les références v2, l'audit des sources/parents et la compilation des deux parcours précèdent le gel before-application.json. Les sorties sont exclusives, afin de refuser un rejeu accidentel. Aucun conteneur actif au contrôle préalable ; préserver tous les conteneurs arrêtés et le volume source.

Les sources anciennes restent inchangées ; le primaire, le lecteur, les évaluateurs et cette prescription sont hachés avant application. En cas d'échec, garder le code et les journaux, produire une version distincte avant toute correction scientifique. Ne pas attribuer au programme échoué le résultat d'une version ultérieure.
