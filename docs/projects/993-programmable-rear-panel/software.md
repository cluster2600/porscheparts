# Logiciel, firmware et protocole BLE v0

**Contrat de prototype, non validé sur matériel.**
[panel_simulator.py](software/panel_simulator.py) est le squelette exécutable de la
machine d'états du firmware et du transfert. Il ne pilote ni MCU, ni LED, ni radio.
Le contexte `connect(authenticated=True)` est injecté par le test : **aucun
appairage, chiffrement, stockage de clés ou boot sécurisé n'est implémenté**.
Il ne faut jamais relier ce booléen à une commande reçue du téléphone.

Pour le coupon E0, [coupon_driver.py](software/coupon_driver.py) encode les trames
mono8 en données pour six TLC5947, sans accès matériel. Le [contrat E0](electronics/coupon.md)
définit câblage, ordre des bits et séquence BLANK/XLAT à vérifier sur cible.
Cette brique ne fournit pas le firmware, le transport SPI réel ou la sécurité BLE.

## Périmètre logiciel

Première version : texte rasterisé sur téléphone, dessin, animations simples et
GIF convertis hors MCU en trames bornées. Pas de cloud, de compte, de microphone,
de télémétrie ni de collecte d'identifiants personnels. App native iOS CoreBluetooth
et Android BLE à réaliser après validation coupon ; aucune application mobile
livrée ni compatibilité OS testée. Wireframes fonctionnels : connexion/appairage,
éditer/importer, aperçu à la résolution négociée, envoyer/progression, armer en
présence physique, arrêter. Afficher la limite d'usage, les erreurs et le nombre
réel de couleurs disponibles ; pas de bouton « homologué ».

## Contrat v0 et limites choisies pour le simulateur

- Coupon virtuel : 16×8 pixels mono8 (0–255). Limites générales du parseur :
  4 096 pixels/trame, 60 trames, 256 KiB de données décodées ; 100–10 000 ms/trame.
  Ce sont des limites de test, pas les capacités retenues pour le produit.
- Encodage document JSON de développement : `version=1`, `width`, `height`,
  `format="mono8"`, `frames=[{"duration_ms":100,"pixels":[…]}]`.
  Rangées de gauche à droite et haut en bas ; valeurs entières, booléens interdits.
  En produit, transporter les pixels binaires sans JSON pour économiser RAM/débit.
- Dans le transport v0, BEGIN annonce taille et SHA-256 des pixels concaténés
  (`frame0` puis `frame1`), dimensions et durées ; DATA fournit offset exact et
  octets. Max 128 octets applicatifs par fragment dans le modèle ; le transport
  réel devra réduire à MTU ATT−3−en-tête (MTU 23 doit rester fonctionnel).
- COMMIT vérifie longueur, SHA-256 et atomicité avant de remplacer le contenu actif.
  Le SHA-256 détecte une corruption, **n'authentifie pas un expéditeur**. Un transfert
  incomplet ou invalide ne remplace pas le précédent ; l'affichage reste éteint.
- Une connexion ne suffit pas à activer : PLAY exige un contenu valide et un
  armement local. Déconnexion, timeout ≥2 s, reset ou défaut : noir, transfert
  abandonné et désarmement. HEARTBEAT authentifié relance le délai ; reconnexion
  impose nouvel armement physique. Aucune reprise automatique après panne.

## GATT proposé pour le portage

Service de projet UUID `6d530001-0993-4e50-9b00-2b0a26000001` ; UUIDs caractéristiques
avec premier groupe `6d530002` capabilities (read), `6d530003` control (write with
response), `6d530004` data (write with response), `6d530005` status (notify).
UUIDs privés de projet, pas un service standard Bluetooth SIG.

| Commande | Charge utile | Réponse et règles |
|---|---|---|
| CAPABILITIES | aucune | version, formats, largeur/hauteur, octets max, cadence, chunk max ; lecture limitée sans lien authentifié |
| BEGIN | session ID, taille, SHA-256, dimensions, durées | READY ou erreur ; arrêt affichage, un transfert à la fois |
| DATA | session ID, offset, octets | prochain offset ; rejet doublon/hors ordre dans v0, reprise par nouveau BEGIN |
| COMMIT | session ID | STORED si complet, sinon erreur sans installation |
| PLAY / STOP | session ID | état ; PLAY conditionné à armement local |
| HEARTBEAT | session ID | état, compteur défaut ; expiration ferme la session |

Les IDs GATT/session et la sérialisation binaire sont une spécification de portage,
pas implémentés dans le simulateur. Le périphérique crée un nouvel ID aléatoire
à chaque session ; rejeter ID ancien, taille excessive et écritures non chiffrées.
Aucune commande OTA dans ce protocole de contenu.

## Sécurité du portage

BLE LE Secure Connections avec protection MITM : bouton local ouvrant une fenêtre
courte d'appairage, code à usage unique sur afficheur/service local ou mécanisme
OOB authentifié à valider avec iOS/Android. Refuser un repli silencieux vers
« Just Works ». L'appairage initial en atelier peut nécessiter un dispositif de
service tant que l'afficheur n'est pas prêt. Un seul propriétaire actif ; effacement
des bonds par geste local explicite, révocation documentée, temporisation contre
les tentatives répétées. Clés générées et conservées sur l'appareil, jamais dans
ce dépôt. Tester interception, rejeu, appareil non autorisé et perte du téléphone.

Firmware : acquisition capteurs, gestion puissance et watchdog indépendants du
transfert ; rendu borné et non bloquant ; double tampon. Driver LED derrière une
interface minimale `blank/render`, transport derrière authentification et limites.
Ne pas construire un framework avant sélection de la cible.

DFU futur : mécanisme éprouvé du SDK (MCUboot/chaîne sécurisée selon MCU [S09]),
images signées, clé publique provisionnée, version compatible et anti-retour à
version vulnérable, banque secondaire puis confirmation de boot ; coupure de
courant à chaque étape, récupération locale. Clé privée de signature hors dépôt.
L'authentification BLE seule ne remplace pas la signature. Écran noir pendant DFU ;
ne jamais exposer ici un chargeur qui accepterait un binaire arbitraire.

## Import GIF et démonstration

Avec Pillow déjà installé :

```sh
python3 docs/projects/993-programmable-rear-panel/software/panel_simulator.py --gif dessin.gif --output /tmp/panel-frames.json
python3 docs/projects/993-programmable-rear-panel/software/panel_simulator.py --input /tmp/panel-frames.json
```

Conversion locale : plafond fichier 5 MiB, dimensions source 1 mégapixel maximum,
60 trames maximum ; compositing GIF par Pillow puis fond noir, letterbox 16×8,
gris 8 bits, durée bornée 100–10 000 ms. Les images volumineuses/animations trop
longues sont rejetées, pas tronquées silencieusement. Pas de décodage GIF sur MCU.
Le rendu réel rouge utilisera une LUT/calibration mesurée ; RGB demanderait un
format versionné distinct. GIF tiers : vérifier droits avant usage et ne pas
committer de contenu reçu sans licence.

## Titre musical : étude séparée

| Origine | Piste réelle | Limite / essai à mener |
|---|---|---|
| iPhone | Accessoire client **Apple Media Service** [S10] : informations du lecteur iOS via BLE | Documentation archivée ; tester versions iOS et lecteurs choisis, notifications, écran verrouillé et coexistence BLE. Une app iOS ordinaire n'obtient pas automatiquement les titres de toutes les autres apps |
| Android | MediaSessionManager et MediaController [S11] | `MEDIA_CONTENT_CONTROL` ou listener de notifications autorisé par l'utilisateur ; respect du refus, variations lecteurs/OS, arrière-plan et permissions BLE |
| Autoradio | API documentée du modèle, ou rôle AVRCP approprié si disponible | Référence exacte et rôles Bluetooth à identifier ; BLE n'est pas AVRCP Bluetooth Classic. Un récepteur A2DP n'offre pas nécessairement un accès tiers aux métadonnées ; aucun démontage/bus inventé |

Accepter absence de titre et effacer les données à la déconnexion. Ne pas conserver
l'historique musical. RP-12 est un POC optionnel qui ne bloque ni le coupon ni les
messages manuels. Aucun titre réel de tiers, logo de service ou pochette n'est livré.
