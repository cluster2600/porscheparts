# Pilote pièce entière — sorties natives en double précision

Cette capsule conserve le véritable calcul CCX à quatre états de la pièce entière et permet de **rejouer son analyse sans exécuter CCX**. Le cas est une sensibilité sous déformation propre équivalente imposée et bridage provisoire. Il ne simule ni dépôt LPBF, ni cycle thermique, ni libération des sept supports physiques.

Le calcul natif a terminé RC0, puis l’analyse native64 a passé les contrôles numériques. Le même DAT mécanique est byte-identique à l’ancien résultat : seules les sorties de déplacement sont lues dans le FRD binaire double. Le refus historique lié aux sept chiffres du DAT n’est pas réétiqueté ; ses reçus et son diagnostic sont conservés dans les payloads historiques.

## Contenu exact

Les sources `assess.py`, `prepare.py`, `read_double_frd.py`, `run.py` et les trois helpers FIELDS/GRADIENTS/EDGES sont conservés byte-identiques. La restauration recrée leurs chemins `work/...` et `parts/...` sous un nouveau ROOT ; les expressions ROOT des sources restent inchangées. Les cartes INP, le maillage complet, le champ de température équivalent, les quatre champs natifs, le DAT complet et les vrais reçus sont inclus. Le NPZ d’origine des groupes de perçages est aussi conservé.

Les textes INP/INC et le FRD sont gzip à date zéro, sans nom de fichier embarqué ; le DAT est XZ/CRC64 déterministe, sans date. Tous les flux décompressés doivent reproduire leurs SHA256 et tailles d’origine. Gzip, XZ, JSON et SHA256 sont traités uniquement par la bibliothèque standard Python. Aucun binaire de décompression, solveur ou image Docker n’est livré ou requis pour la réanalyse.

`manifest.json` décrit les payloads exacts et les utilitaires ; `archive.json` ferme aussi la notice et les reçus de vérification. Le `bundle.json` et le plan natifs sont conservés **comme reçus historiques intacts** : leurs chemins absolus décrivent l’exécution d’origine et leur inventaire ne signifie pas que les 56 fichiers du dossier de travail ont tous été dupliqués. Les exécutables, caches, deuxième DAT identique et sorties de smoke inutiles à la réanalyse sont omis.

## Vérifier, restaurer, réanalyser

Python 3.12.14 et NumPy 2.3.5 sont les versions du véritable rejeu. La vérification et la restauration seules n’importent aucune dépendance scientifique. Choisir deux chemins absolus et une racine de restauration inexistante :

```sh
CARRIER_CAPSULE=/chemin/wholepart-native64-20261017
CARRIER_PRIMARY_PYTHON=/chemin/python3
CARRIER_RESTORED=/chemin/restauration-neuve
CARRIER_MANIFEST_SHA=d7c4e32f905b0e607aca6a5a3f196659530fb0cc4c25e563dd9bfdcb48dcaeb5

"$CARRIER_PRIMARY_PYTHON" -I -B "$CARRIER_CAPSULE/restore.py" verify --manifest-sha256 "$CARRIER_MANIFEST_SHA"
"$CARRIER_PRIMARY_PYTHON" -I -B "$CARRIER_CAPSULE/restore.py" restore "$CARRIER_RESTORED" --manifest-sha256 "$CARRIER_MANIFEST_SHA"
"$CARRIER_PRIMARY_PYTHON" -I -B "$CARRIER_CAPSULE/replay_analysis.py" "$CARRIER_RESTORED" --manifest-sha256 "$CARRIER_MANIFEST_SHA"
```

Le dernier appel lance uniquement le même `assess.py`, avec un seul thread et un timeout de 60 secondes, depuis `/`. Il refuse d’écraser une analyse et exige l’identité byte-à-byte du JSON entier des contrôles et mesures, SHA256 `9982186046f1e975f38a5189e69bc923897372c7705892e842832ed90f7c591d`. Il vérifie les entrées restaurées avant et après. Les sorties et le vrai code retour de cette **nouvelle réanalyse**, distincte du calcul natif historique, se trouvent dans `reanalysis-001/`.

Une sortie de restauration existante, un lien symbolique pendant ou un chemin parent symbolique sont refusés avant création. Les six petits tests stdlib couvrent la restauration gzip/XZ exacte, les refus de destination, de SHA modifié, de flux d’origine modifié et de chemin sortant de la capsule. Ils n’ont pas le statut d’un calcul mécanique.

## Résultats et portée

Le jeu est le maillage actuel de 103 534 nœuds et 54 149 C3D10. Les quatre états sont : zéro, contraction uniforme libre, champ quadratique avec plan inférieur provisoirement fixé, puis même champ libéré vers six jauges de corps rigide. Le contrôle uniforme respecte exactement ces jauges analytiques ; son erreur de déformation vaut 1,2434497875801753×10⁻¹⁴ sous le seuil inchangé de 10⁻⁷. Le zéro est exact, les équilibres force/moment et detF positif passent sur les quatre états.

Pour le champ quadratique déclaré : déplacement maximal libéré 58,090 µm, incrément maximal de débridage 57,471 µm, variation d’entraxe principal −13,187 µm. La masse EF lagrangienne reste 1,2614835044 kg (ρ₀V₀) ; le volume déformé est un diagnostic et ne sert pas à redéfinir cette masse. Les cotes utilisent les mêmes groupes nodaux et leurs cercles projetés ; elles ne constituent pas une nouvelle métrologie des alésages.

Le binaire et l’image CCX d’origine sont identifiés dans les reçus, sans être copiés. `run.py` est une source historique ; son plan figé reste lié au contexte d’origine. Cette capsule rend la **restauration et la réanalyse** portables, sans prétendre installer ou rejouer le solveur. L’identité byte-à-byte de l’analyse est testée avec le runtime déclaré ; un autre environnement numérique doit repasser ce contrôle. Aucune validation physique ou admission globale d’impression n’est revendiquée.

## Vérification réelle de cette capsule

La copie relocalisée a été restaurée depuis `/` avec RC0 (15,261 s), puis réanalysée avec RC0 (25,420 s, dont l’appel assessor limité à 60 s). Le JSON complet des contrôles et mesures est byte-identique à celui du calcul natif. Les 59 pins du plan d’origine sont encore inchangés après cette opération. Les reçus se trouvent dans `verification/`. Les 48 payloads comprimés représentent 47 345 141 octets ; la cible pratique de 40 Mo est dépassée pour conserver le cas complet, sans nouvel outil de compression.
