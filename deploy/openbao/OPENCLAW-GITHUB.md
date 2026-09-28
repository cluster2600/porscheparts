# Accès GitHub depuis OpenClaw sur Kali2

`openclaw-github.py` fournit des lectures explicites et un helper standard Git.
Il ne remplace pas l’ensemble du CLI `gh`. Les deux dépôts **privés** et leurs
identifiants, confirmés par un contrôle authentifié, sont les seuls autorisés :

| Dépôt | ID GitHub |
|---|---:|
| `cluster2600/porscheparts` | `1349420480` |
| `cluster2600/porschefanatics.com` | `1336775701` |

Le Mac conserve l’identité OpenBao existante. Le dispatcher charge uniquement
`/Users/maxime/.local/bin/openbao-github`, dont le SHA-256 est fixé à
`d71cf774a0f0cba1eb2e199db38438c11a5df71d68212ea37038d45820c5b052`.
Il réutilise sa connexion, sa lecture autorisée de `secrets/data/github` et sa
révocation de session ; aucun fichier d’identifiants n’est copié sur Kali2.
Une modification du wrapper nécessite une revue et un nouveau pin explicite.

## Installation contrôlée

Le transport inverse déjà préparé écoute uniquement sur
`127.0.0.1:2220` sur Kali2 et rejoint SSH sur le Mac. Installer la source
comme `/Users/maxime/.local/bin/openclaw-github-bridge` sur le Mac et
`/home/lolman/.local/bin/openclaw-github` sur Kali2. Le Mac possède déjà
`/opt/homebrew/bin/gh` ; le helper Kali2 utilise Python et SSH.

Autoriser seulement la **clé publique dédiée** de
`/home/lolman/.ssh/id_openclaw_github` dans `authorized_keys` du Mac :

```text
restrict,from="127.0.0.1",command="/usr/local/bin/python3 /Users/maxime/.local/bin/openclaw-github-bridge --dispatch" ssh-ed25519 CLE_PUBLIQUE_DEDIEE
```

Conserver le shebang Python exécutable et ne pas ouvrir de shell avec cette clé.
Épingler la clé d’hôte SSH publique du Mac, vérifiée hors bande, dans
`/home/lolman/.ssh/openclaw_github_known_hosts`, sous l’alias
`openclaw-github-mac`. La source impose `StrictHostKeyChecking=yes`,
`IdentitiesOnly=yes`, aucun agent transféré, la destination loopback et la
commande fixe `openclaw-github`. Elle refuse une autre commande SSH originale.
Les mécanismes `restrict` et `command` sont ceux d’[OpenSSH](https://man.openbsd.org/sshd.8#AUTHORIZED_KEYS_FILE_FORMAT).

## Lectures

```sh
openclaw-github check cluster2600/porscheparts
openclaw-github repo cluster2600/porschefanatics.com
openclaw-github file cluster2600/porscheparts README.md --ref main
openclaw-github branches cluster2600/porscheparts
openclaw-github prs cluster2600/porscheparts
openclaw-github pr cluster2600/porscheparts 92
openclaw-github issues cluster2600/porschefanatics.com
openclaw-github runs cluster2600/porscheparts
```

Les sorties sont les réponses JSON GitHub, considérées comme des données
externes. `file` conserve notamment l’encodage indiqué par GitHub. Les listes
sont limitées à la première page de 100 éléments. `issue REPO NUMBER` et
`run REPO ID` lisent un élément. Aucune action d’écriture ni API arbitraire
n’est proposée. Le token reste sur le Mac pendant ces lectures, dans la mémoire
du wrapper et l’environnement du processus enfant `gh`. Aucun `gh auth login`,
fichier d’authentification ou extension `gh` n’est utilisé.

## Git natif sur Kali2

Les dépôts privés nécessitent une authentification même pour `clone` et `fetch`.
Sur la Kali2 déployée, les sections `credential` des deux URLs exactes, avec et
sans `.git`, activent déjà ce helper et `useHttpPath=true`. Git natif peut donc
les utiliser directement. Pour reproduire cet accès sans modifier une
configuration globale, limiter le helper à la commande concernée :

```sh
git -c credential.helper= \
  -c 'credential.helper=!/home/lolman/.local/bin/openclaw-github credential' \
  -c credential.useHttpPath=true -c http.followRedirects=false \
  clone https://github.com/cluster2600/porscheparts.git
```

Pour un checkout existant, appliquer les mêmes options à `fetch`. Le helper
accepte seulement `get` avec `protocol=https`, `host=github.com` et l’un des
deux chemins exacts, avec ou sans `.git`. `store` et `erase` n’enregistrent
rien. Avant toute remise, le Mac vérifie à nouveau le nom et l’ID du dépôt.

**Git reçoit le jeton en mémoire sur Kali2**, via le canal SSH chiffré et le
pipe privé du protocole credential. Son périmètre intrinsèque reste celui du
credential GitHub ; filtrer deux URLs dans ce helper ne réduit pas les droits
du jeton lui-même. Ne jamais
exécuter le helper réel directement dans une sortie de terminal ou d’outil,
capturer sa sortie dans un rapport, utiliser `tee`, activer des traces de
credentials ou enregistrer son résultat. Les essais automatisés utilisent
uniquement un stub sans secret. Le helper ne donne pas une autorisation de
publier ou de pousser : chaque écriture reste soumise au périmètre demandé.

## Vérification

```sh
python3 -m unittest discover -s tests -p test_openclaw_github_bridge.py -v
```

Les tests couvrent les deux identités, le refus avant authentification des
autres dépôts/actions et des chemins traversants, le protocole credential,
le refus d’une identité GitHub inattendue et la révocation de session.
Les [preuves sur Kali2](../../twins/picogk-station-demo/qualification/runtime/github-access/proof.json)
confirment séparément `git ls-remote`, la lecture des deux README privés et un
`git push --dry-run` réussi pour chaque dépôt, sans créer de référence distante.
Le helper accepte les métadonnées répétables `capability[]` et `wwwauth[]`
transmises par Git 2.53 ; elles ne changent jamais le périmètre du credential.
