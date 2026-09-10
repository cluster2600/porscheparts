# M64 — gestion bornée des HTTP 429 Vast

Date : 2026-09-07. Vérification **hors ligne** du correctif, puis déploiement
du même diff sur le wrapper installé, vérifié identique par `cmp`.
Les permissions, identités et chemins OpenBao ne sont pas modifiés. Aucune
location ni requête fournisseur n'a été effectuée par les tests unitaires.
L'essai réel ultérieur est documenté séparément dans
`M64_VAST_EXECUTION_20260907.md`.

## Diagnostic et correction

Avant correction, `vast_request` propageait immédiatement tout `SafeHttpError`,
y compris une limitation temporaire HTTP 429 sur une lecture GET. Le scénario
est reproduit par un mock levant cette exception : pas par un nouvel appel
payant ou une récupération de secret.

Le wrapper retente désormais uniquement les **GET Vast avec HTTP 429** : trois
attentes de 20, 40 et 60 secondes, soit quatre tentatives au maximum. Les
messages indiquent uniquement le service, le numéro de tentative et le délai :
ni clé, ni URL, ni corps d'erreur fournisseur. Après épuisement, une erreur 429
reste levée ; aucune réponse artificiellement vide ni succès n'est retourné.

POST, PUT, DELETE, PATCH, autres statuts HTTP et indisponibilité réseau ne sont
pas rejoués. La connexion OpenBao et la lecture du secret restent hors de cette
boucle, dans leurs fonctions existantes.

Le polling de disponibilité SSH/READY de **SimReady seulement** passe de 2 à
15 secondes, toujours borné par son délai restant. La constante des autres
workflows reste à 2 secondes. Les vérifications d'image, coût, unicité et
nettoyage ne sont pas assouplies.

Une lecture fortement limitée peut prendre jusqu'à 120 secondes d'attente
supplémentaire, en plus des timeouts réseau existants. Un délai externe vérifié
entre deux appels peut donc être dépassé pendant l'appel bloquant : cette
correction ne constitue pas une nouvelle garantie de deadline temps réel.

## Vérifications

Commande :

```sh
python3 -m unittest discover -s tests -p test_openbao_vastai_wrapper.py -q
```

Résultat : **87 tests réussis**, dont cinq nouveaux tests couvrant la reprise
GET, l'épuisement fail-closed, l'absence de rejeu des mutations, les autres
erreurs/offline et la séparation de cadence SimReady. Les attentes des nouveaux
tests sont mockées : aucun sommeil réel ni accès réseau. Les logs de location
affichés par d'autres tests de cette suite sont des fixtures synthétiques.

Ce correctif ne démontre ni la disponibilité actuelle d'une offre Vast, ni le
succès d'une location, ni l'état d'Omniverse, ni une simulation de culasse.

## Diagnostic complémentaire : appariement SSH

Après signalement d'un échec `ssh_authentication_failed`, une lecture hors
ligne du code révèle un autre défaut : `safe_instance` conservait `ssh_host`
(potentiellement proxy), mais prenait le port direct `ports[22/tcp].HostPort`
si `ssh_port` était absent. Une paire hybride pouvait donc être transmise à
`verify_simready_ssh_ready`.

Correction dans le dépôt, puis déployée identiquement (`cmp`) : conserver la paire proxy complète si elle
existe ; sinon utiliser ensemble `public_ipaddr` et le port direct mappé ; sinon
laisser les deux valeurs absentes. Les contrôles de format/port et d'identité
SSH existants restent actifs. Aucun basculement automatique après échec
d'authentification, aucune clé supplémentaire, aucun relâchement de host key.

Trois tests supplémentaires couvrent paire proxy complète, port proxy absent
ou null, et paires incomplètes. **90 tests wrapper réussis** après correction.
Le snapshot normalisé de l'essai échoué ne conserve pas la provenance du port :
ce défaut est reproduit synthétiquement, mais **n'est pas établi comme cause de
l'échec payé**. Aucun nouvel appel live ni location pendant ce diagnostic.
