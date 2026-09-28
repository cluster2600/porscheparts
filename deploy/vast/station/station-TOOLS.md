# Station PicoGK : commandes OpenClaw sur Kali2

Ajouter ce bloc au `TOOLS.md` du workspace OpenClaw ; conserver les instructions
déjà présentes. Installer `openclaw-tools.py` sous `~/.local/bin/station-task`
avec le mode `0755`. Le CLI utilise Python 3 et `ssh` / `rsync` de Kali2.

Configuration fournie par l’opérateur dans
`~/.config/picogk-station/endpoint.json` :

```json
{"host": "ssh.example.invalid", "port": 22222}
```

Remplacer ces valeurs par l’endpoint SSH réellement attribué à la station.
L’utilisateur distant est toujours `station-worker` (UID 10002). La clé dédiée
est `~/.ssh/id_picogk_station_worker` ; sa partie publique doit être installée
pour ce compte et l’identité de l’hôte doit être vérifiée dans `known_hosts`.
Le CLI ne lit pas la clé : seul OpenSSH l’utilise. `StrictHostKeyChecking=yes`,
`BatchMode=yes` et l’absence de transfert d’agent sont imposés. Un échec
d’authentification reste bloquant ; ne pas essayer un autre compte ou secret.

## Utilisation

```sh
station-task status
station-task demo coupon-001 --span-mm 30 --voxel-mm 0.25
station-task status
station-task render coupon-001
station-task collect coupon-001
```

- Un identifiant commence par une lettre minuscule et contient au maximum
  48 caractères parmi `a-z`, `0-9`, `-`. Chaque démonstration exige un nouvel
  identifiant. Les tâches existantes ne sont pas écrasées.
- `demo` lance la chaîne existante `station-demo` : PicoGK **2.3.0**, **.NET
  9.0.317**, contrôles géométriques métal, cartes EOS M 290 / AlSi10Mg 30 µm et
  assemblage USD. `span-mm` est compris entre 20 et 80 ; `voxel-mm` entre 0,1
  et 0,5. Les autres opérations CAO restent celles du dépôt ; le CLI n’accepte
  aucun script, commande shell ou chemin arbitraire.
- `demo` et `render` renvoient immédiatement un accusé d’acceptation. Les tâches
  continuent après la déconnexion SSH, dans une file de calcul unique. Un
  accusé ne prouve pas la réussite : attendre `status: complete` dans `status`.
- `render` exige le fichier `completed.json` de la démonstration et appelle
  `station-render` sur le GPU 3. Le résultat est `render.png`. Chaque rendu
  exige un nom de fichier neuf ; un second rendu du même job est refusé.
- Chaque commande de calcul est limitée à 30 minutes après sa prise en charge.
  `failed` ou `interrupted_or_unknown` nécessite de lire le journal avant de
  proposer une nouvelle tâche. Ne pas relancer automatiquement une boucle.
- `collect` copie les résultats et journaux dans `~/stations/JOB/` sur Kali2,
  sans liens symboliques, fichiers spéciaux, suppression ni accès hors du job.

Les fichiers distants sont sous `/workspace/jobs/JOB/` : `demo.json`,
`demo.log`, `render.json`, `render.log`, `render.png`, et `output/` pour les
géométries, rapports, empreintes et `station-assembly.usda`.

L’impression n’est jamais autorisée par ces résultats numériques. Ne pas
présenter la pièce comme ajustée, imprimée, testée physiquement ou homologuée.
Le CLI ne loue, ne prolonge et ne détruit aucune instance Vast ; les limites de
coût et la garde externe restent contrôlées séparément.

## Calcul CPU sur Kali1

Kali1 dispose d'un runtime PicoGK extrait et vérifié depuis l'image station,
avec les sources C# conservées. Depuis Kali2, utiliser le lanceur natif :

```sh
kali1-picogk coupon-kali1-001 --span-mm 50 --voxel-mm 0.25
```

Le calcul bloque jusqu'à son résultat : témoin volume/offset/aller-retour STL,
puis témoin paramétrique et deux coupons. Il utilise au maximum **deux CPU,
2 Gio, zéro swap et 300 secondes**, avec priorité `nice 10`. Un verrou refuse
un deuxième calcul simultané sur Kali1 ; il n'y a pas de nouvelle file.
Chaque identifiant doit être neuf, avec les mêmes caractères autorisés que
`station-task`. Les paramètres restent bornés à 20–80 mm et 0,1–0,5 mm.

La commande utilise exclusivement SSH via `127.0.0.1:2221` sur Kali2,
`HostKeyAlias=kali1-cpu`, une identité dédiée utilisée par OpenSSH et aucun
transfert d'agent. Ce port est relié à Kali1 par le contrôleur Mac : le
contrôleur et son tunnel doivent rester disponibles. La liaison IP directe
Kali2 → Kali1 a expiré avant authentification ; ne pas désactiver la vérification
d'hôte ou rechercher un autre secret pour contourner un échec du tunnel.

Après le calcul, `rsync` copie seulement le job dans
`~/stations/kali1/JOB/` sur Kali2, sans liens, fichiers spéciaux ni suppression.
Le lanceur vérifie les huit empreintes du reçu `execution.json`. Les sources
et les trois premiers essais sont également conservés dans
`~/stations/kali1-compute-20260928-r8kj70sz/`.
Cette voie exécute la géométrie PicoGK CPU ; les contrôles métal, la CAO et USD
restent disponibles via la chaîne complète `station-task` sur Vast.
Ne pas redémarrer le gateway OpenClaw pour lancer ou collecter un calcul Kali1.
