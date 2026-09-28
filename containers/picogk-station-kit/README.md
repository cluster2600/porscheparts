# Éditeur Kit de la station PicoGK

Kit Base Editor **110.2.0** vient du dépôt NVIDIA fixé au commit
`3f4b33387f58e5c6694b5479559c945fb80bb625`. Le générateur officiel produit
`station.editor.kit` ; notre couche ajoute la diffusion de l’éditeur complet.
L’application utilise le rendu RTX de Kit et tourne dans le conteneur Vast,
sans Docker imbriqué. Le navigateur reçoit une vidéo WebRTC.

## Construction et licence

La construction nécessite l’acceptation explicite du
[contrat NVIDIA](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-software-license-agreement/)
et des [conditions Omniverse](https://www.nvidia.com/en-us/agreements/enterprise-software/product-specific-terms-for-omniverse/).
`install.sh` refuse de continuer sans `NVIDIA_EULA_ACCEPTED=yes` ; cet argument
autorise la réponse « Yes » au générateur officiel. L’acceptation pour cette
station a été donnée dans la conversation du 28 septembre 2026. Elle ne donne
aucun droit supplémentaire de redistribution des logiciels NVIDIA.

Depuis la racine du dépôt, sur Linux x86-64 :

```sh
docker build -f containers/picogk-station-kit/Dockerfile \
  --build-arg NVIDIA_EULA_ACCEPTED=yes -t picogk-station:kit-source .
cd deploy/vast/station-client
npm ci --ignore-scripts --no-audit --no-fund
npm test
npm run build
```

Le runtime autonome est placé dans `/opt/station-kit-runtime`. Les liens vers
les caches de construction sont déréférencés. Le runtime inclut les licences
amont et le commit du modèle. L’image finale fournit son digest et les versions
réellement résolues des extensions.

## Réseau et GPU

Publier uniquement **UDP 47998** pour WebRTC. Garder **TCP 49100** non publié
sur Vast ; l’accès se fait par un tunnel SSH local. Le lanceur refuse une
configuration qui annonce `VAST_TCP_PORT_49100`. Kit ne documente pas de réglage
de liaison de la signalisation à loopback : l’isolation repose donc sur
l’absence de publication de ce port dans le réseau du conteneur.

`station-kit` utilise `PUBLIC_IPADDR` (ou `VAST_PUBLIC_IP`) et
`VAST_UDP_PORT_47998`. Il écrit les informations de connexion dans
`/workspace/station-runtime/webrtc-connection.json`. Le serveur écoute sur le
port UDP **interne 47998** ; le client utilise le port **externe mappé**.

`STATION_KIT_GPU=2` est l’ordinal par défaut. Avant de lancer Qwen en parallèle,
vérifier dans le tableau `gpu.foundation` que cet ordinal désigne bien le
troisième GPU physique réservé à Kit, en comparant l’identifiant PCI. Corriger
l’ordinal si nécessaire. Le lanceur impose `renderer.activeGpu`, désactive le
multi-GPU et retire `CUDA_VISIBLE_DEVICES` de son propre processus.

`STATION_SCENE` désigne un fichier USD de travail produit par la démonstration,
jamais une source utilisateur à préserver. Le lanceur ouvre cette scène ;
l’éditeur natif fournit sélection, déplacement, propriétés et sauvegarde.

## Client et preuves

Servir `deploy/vast/station-client/dist` sur `127.0.0.1:8088`, puis transférer
les ports 8088 et 49100 vers la machine du navigateur par SSH. Ouvrir
`http://127.0.0.1:8088`, saisir l’adresse IPv4 publique Vast et le port UDP
externe. Le client officiel `@nvidia/ov-web-rtc` **6.7.0** et son intégrité sont
fixés dans `package-lock.json`. Aucun CDN n’est utilisé à l’exécution.

La qualification exige une image non vide, le déplacement d'une pièce
sélectionnée, une sauvegarde du USD de travail, puis une reconnexion. Le bouton
« Exporter le diagnostic » enregistre les événements du client et les images
décodées. Compléter avec des captures visuelles, la preuve du transform avant /
après et les journaux Kit. Une signalisation réussie seule ne valide pas le
chemin média UDP. La validation GPU et WebRTC distante reste à exécuter tant
que ces preuves ne sont pas présentes.

## Repli média par SSH

La qualification du 28 septembre a constaté un mapping UDP public présent dans
l’API Vast, mais aucun des six datagrammes de test Mac/Kali2 n’a atteint le
serveur lié à `0.0.0.0:47998`. La sonde loopback a réussi. Le passage UDP public
reste donc **en échec sur cette instance**. Le repli ci-dessous a fourni de vraies images Kit
en 1920 × 1080, une sélection, un déplacement de 10 mm et une sauvegarde USD.
Une reconnexion a réussi après une reprise du client d’environ 34 secondes.
Un navigateur Chromium isolé exécuté sur Kali2 a ensuite reçu 132 images en
1920 × 1080 avec les fichiers du client final. Les services sont restés actifs
après fermeture de SSH et le relais s’est reconnecté automatiquement après
redémarrage du seul tunnel média.
Le fichier sauvegardé a également été rouvert par `File > Open`, après sélection
de `My Computer /` ; le transform X = 10 mm reste visible après rechargement.

`deploy/vast/station/media-relay.py` transporte les datagrammes opaques dans un
flux TCP à travers SSH. Il utilise uniquement la bibliothèque standard Python,
des cibles loopback fixes et un choix explicite de durée : `--deadline` dans les
six heures suivantes, ou `--persistent` après autorisation de maintien actif.
Il conserve les limites des datagrammes, gère les lectures partielles
et EOF, borne la file mémoire, le nombre de pairs et l’inactivité des fragments.
Il n’enregistre ni contenu média, ni SDP, ni paramètres d’authentification ICE.

Sur Vast, utiliser le deadline Unix du manifeste de la location courante :

```sh
station-media-relay server --deadline "$STATION_DEADLINE_EPOCH"
```

Cette commande écoute **TCP 127.0.0.1:47999** et ne peut transmettre qu’à
**UDP 127.0.0.1:47998**. Ajouter au tunnel SSH approuvé du poste client :

```sh
-L 127.0.0.1:47999:127.0.0.1:47999
```

Puis, sur le poste qui exécute le navigateur :

```sh
python3 ~/bin/station-media-relay client --deadline "$STATION_DEADLINE_EPOCH"
```

Ouvrir `http://127.0.0.1:8088/` et saisir **127.0.0.1**, port **47998** dans
les champs média. La signalisation reste dans le tunnel TCP 49100. Un seul
poste média doit être connecté à la fois ; déconnecter le navigateur précédent
avant de changer de poste.

Sur Kali2, les unités `picogk-station-media-tunnel.service` et
`picogk-station-media-relay.service` sont distinctes de
`qwen-vast-tunnel.service`. Elles utilisent `Restart=always`, une
`ExecCondition` comparant l’horloge au deadline du manifeste et un
`RuntimeMaxSec` borné. Ainsi, une fermeture TCP prématurée relance le client ;
l’échéance et un arrêt manuel empêchent une boucle de relance. Le programme
du tunnel recalcule aussi le temps restant avant chaque lancement de SSH sous
`timeout`, pour ne pas prolonger l’échéance lors d’une reprise. Le programme
Vast `media-relay` est ajouté seul au superviseur, sans redémarrer Kit ou Qwen.
Les fragments exacts propres à la location sont conservés dans ses preuves ;
aucun deadline de location n’est gravé dans l’image réutilisable.

L’utilisateur a ensuite demandé de conserver la station active, sans coupure.
Dans ce mode autorisé, les commandes deviennent `station-media-relay server
--persistent` sur Vast et `python3 ~/bin/station-media-relay client --persistent`
sur Kali2. Les unités média conservent `Restart=always`, mais n’ont plus
`ExecCondition`, `RuntimeMaxSec` ni enveloppe `timeout` ; le tunnel lance SSH
directement. Le service Qwen reste indépendant. Cette option ne modifie aucune
garde de location : le contrôleur doit enregistrer séparément l’autorisation
de prolongation et adapter sa politique de coût.

```sh
systemctl --user status picogk-station-media-tunnel picogk-station-media-relay
systemctl --user stop picogk-station-media-relay picogk-station-media-tunnel
```

Le transport TCP peut augmenter la latence et bloquer momentanément les images
lors d’une retransmission. Il permet le travail interactif observé, mais ne
valide pas le réseau UDP direct Vast et ne garantit pas une latence maximale.
Lors de la réouverture USD depuis le Mac, la file a atteint sa limite de 8 MiB
et le relais a fermé cette connexion. La reconnexion a rétabli l’image et le
transform sauvegardé, sans redémarrer Kit ni Qwen. Un chargement volumineux peut
donc nécessiter une reconnexion ; la limite mémoire reste active.

## Protocole de qualification native

Exécuter ces étapes après le précontrôle GPU et sous la garde de coût active.
Le dossier `ui-witness` doit être neuf. Sur Vast, le contrôleur root prépare
une copie de travail, en conservant le résultat original de la génération :

```sh
set -eu
test ! -e /workspace/jobs/ui-witness
install -d -o station-worker -g station-worker /workspace/jobs/ui-witness
runuser -u station-worker -- station-demo /workspace/jobs/ui-witness/output --span-mm 30 --voxel-mm 0.25
cp -p /workspace/jobs/ui-witness/output/station-assembly.usda /workspace/jobs/ui-witness/working.usda
sha256sum /workspace/jobs/ui-witness/output/station-assembly.usda /workspace/jobs/ui-witness/working.usda
```

Avant le **premier** lancement de `station-onstart`, exporter
`STATION_SCENE=/workspace/jobs/ui-witness/working.usda`. Si supervisord existe
déjà, l'environnement du shell de `supervisorctl` ne lui est pas transmis :
ajouter `STATION_SCENE="/workspace/jobs/ui-witness/working.usda"` au réglage
`environment` du seul programme `kit`, puis appliquer `reread` et `update`
avant `start kit`. Ce même réglage impose `STATION_KIT_GPU="2"` ; si le tableau
Vulkan révèle un autre ordinal pour le GPU physique réservé, le corriger ici.
Conserver Qwen arrêté durant cette vérification initiale du GPU.

1. Démarrer `kit` avec `supervisorctl -c /opt/station/supervisord.conf start kit`.
   Conserver `/workspace/logs/kit.log` et `kit.err.log`, le tableau
   `gpu.foundation` et `nvidia-smi --query-gpu=index,pci.bus_id,uuid --format=csv`.
   Vérifier qu'un seul GPU est actif dans Kit et que son PCI correspond au
   GPU physique 2 prévu. Relever le PID Kit.
2. Depuis le poste du navigateur, ouvrir un tunnel SSH avec
   `-L 127.0.0.1:8088:127.0.0.1:8088 -L 127.0.0.1:49100:127.0.0.1:49100`
   et `-o ExitOnForwardFailure=yes`. Conserver les options d'identité et de
   vérification de clé de la connexion approuvée. Le port UDP externe n'est
   pas un port du tunnel SSH.
3. Ouvrir `http://127.0.0.1:8088`, renseigner les champs à partir de
   `/workspace/station-runtime/webrtc-connection.json`, puis connecter.
   Une image doit montrer l'éditeur natif et l'assemblage ; capturer cet état.
4. Dans le panneau Stage de Kit, sélectionner **`/World/bracket_witness`**,
   son Xform parent. Capturer la sélection et son transform initial `(0,0,0)`.
   Dans les propriétés natives, double-cliquer la valeur Translate X et saisir
   **10 mm**, conserver Y et Z à zéro, puis quitter le champ pour valider.
   Constater le déplacement dans la vue et capturer.
5. Enregistrer `working.usda` depuis File → Save. Sur la station, relire le
   fichier avec USD pour vérifier `xformOp:translate == (10,0,0)` :

   ```sh
   /opt/geometry-qa/bin/python -c 'from pxr import Usd; s=Usd.Stage.Open("/workspace/jobs/ui-witness/working.usda"); v=s.GetPrimAtPath("/World/bracket_witness").GetAttribute("xformOp:translate").Get(); print(tuple(v)); assert tuple(v)==(10.0,0.0,0.0)'
   sha256sum /workspace/jobs/ui-witness/output/station-assembly.usda /workspace/jobs/ui-witness/working.usda
   ```

6. Cliquer Déconnecter puis Connecter. Vérifier une nouvelle image décodée,
   le même PID Kit et le transform conservé. Rouvrir `working.usda` via le
   menu natif File → Open pour confirmer également la lecture du fichier
   sauvegardé. Capturer l'état et exporter le diagnostic du client : au moins
   deux connexions, des images décodées et des dimensions vidéo non nulles.
7. Produire le rendu séparé avec
   `runuser -u station-worker -- station-render /workspace/jobs/ui-witness/working.usda /workspace/jobs/ui-witness/render-after.png`.
   Vérifier le journal, le PNG non vide et l'activité du GPU 3. Cette commande
   utilise `/opt/ovrtx-runtime` ; elle ne remplace pas la preuve d'interaction Kit.

Collecter le dossier avec `station-task collect ui-witness`, les captures,
le diagnostic WebRTC et les logs Kit. Le transform relu sur disque et les
images réelles sont les preuves ; aucun résultat ne doit être déclaré réussi
si une étape n'a pas pu être observée.

Sources : [diffusion Kit](https://docs.omniverse.nvidia.com/kit/docs/kit-app-template/latest/docs/streaming.html),
[réglages des flux](https://docs.omniverse.nvidia.com/kit/docs/omni.kit.livestream.app/latest/Overview.html),
[sélection des GPU](https://docs.omniverse.nvidia.com/kit/docs/kit-manual/107.3.0/guide/linux_troubleshooting.html).
