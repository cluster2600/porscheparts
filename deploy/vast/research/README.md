# Lecteurs documentaires M64 sur Vast

Ce profil exécute un LLM public pour analyser un corpus documentaire fourni.
Il ne lance ni CAO, ni solveur, ni fabrication ; les réponses ne sont jamais
publiées automatiquement. Voir le [dossier d'exécution](../../../docs/M64_RESEARCH_EXECUTION_20260912.md).

## Profil borné

- Image vLLM 0.19.0 épinglée au manifeste `linux/amd64` ; modèle public
  `Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8` à révision immuable dans le wrapper.
- Une L40S ou RTX 6000 Ada, au moins 45 000 MB de VRAM, 64 000 MB de RAM,
  12 CPU effectifs et 100 GB de disque ; offre vérifiée et relue avant création.
- Maximum 0,85 USD/h et 4 USD par tentative, transferts et réserve inclus dans
  l'estimation ; deadline absolue au plus deux heures, préparation comprise.
- API `127.0.0.1:8000`, tunnel SSH seulement ; aucun jeton HF/GitHub envoyé.
- `gpu_frac` est le rapport entre GPU loués et GPU du serveur, pas une fraction
  de carte ; un GPU et sa VRAM sont exigés et relus séparément.

La garde locale est armée **avant** l'appel payant. Elle utilise le moteur PicoGK
historique vérifié par SHA, surveille le label exact et détruit l'instance avant
l'échéance, puis vérifie son absence. Ce mécanisme ne remplace pas une limite de
facturation côté fournisseur : perte durable du poste/réseau ou indisponibilité
de Vast peuvent retarder la destruction. Le délai interne du serveur arrête
l'inférence mais ne termine pas, seul, la facturation.

Le délai d'inférence est calculé sur le contrôleur, pas avec l'horloge distante :
temps restant moins 900 secondes de démarrage, 300 de nettoyage et 60 de marge.
Un résultat inférieur à 60 secondes interdit la création. Le contrôle des
métadonnées peut attendre jusqu'à 900 secondes, toujours à l'intérieur de
l'échéance globale. Ces bornes incluent le chargement et ne garantissent pas
que le modèle sera prêt dans ce délai.

## Exécution contrôlée

Le manifeste local privé est validé par `research_load_manifest` : empreintes de
l'image, des poids, de leur qualification et de la garde ; chemin exact, label
unique, budget, horodatage et reçu de garde. Les valeurs sont préparées pour une
tentative précise : ne pas réutiliser un manifeste consommé.

1. Vérifier le crédit, `research-offers`, l'image publique et les poids sans les
   télécharger sur le Mac. Installer uniquement le wrapper testé, sans modifier
   l'identité OpenBao existante.
2. Exécuter `python3 /chemin/absolu/deadline_guard.py /chemin/absolu/manifest.json`
   et conserver le processus jusqu'à preuve de destruction.
3. Exécuter `openbao-vastai launch-research OFFER_ID /chemin/absolu/manifest.json`.
   Toute création incertaine est réconciliée, jamais rejouée.
4. Vérifier connexion SSH, GPU, modèle et API locale, puis ouvrir un tunnel.
   Un retour du provisionneur n'atteste pas ces étapes.
5. Exécuter quatre missions avec le répartiteur, relire les résultats avant le
   reste de la file, puis collecter et détruire exactement l'instance.

Exemple de commande documentaire, **une fois le tunnel et le corpus vérifiés** :

```sh
python3 twins/m64-cylinder-head/source/run_research_readers.py \
  --corpus /chemin/prive/corpus.json \
  --endpoint http://127.0.0.1:18000/v1 \
  --model Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 \
  --output /chemin/prive/nouveau-pilote \
  --limit 4
```

Chaque source contient `url`, `text`, `read_level`, `sha256` du texte UTF-8.
Le répartiteur transmet au plus 8 000 caractères par source et trois sources par
mission. Maximum : 24 missions, quatre simultanées, 1 600 tokens de réponse,
180 secondes par requête, 1 800 secondes globales. Aucune nouvelle tentative
automatique, navigation autonome, exécution de code ou accès aux secrets.

Les réponses JSON, citations et rapports bruts restent privés. URL et extrait
doivent correspondre au corpus réellement transmis ; cela ne prouve pas que la
conclusion découle correctement de l'extrait. Une revue conserve les limites
de lecture, élimine les contradictions et produit la synthèse publiable.

## Vérification

```sh
python3 -m unittest discover -s tests -p 'test_*research*.py' -v
```

Ces tests sont hors ligne. Ni leur succès ni une réponse LLM ne valident la
culasse. La modification du wrapper commun fait dériver certains fingerprints
de rapports historiques, notamment F46 : ne pas les régénérer pour annoncer à
tort que les anciens essais ont été réexécutés.

Source de sémantique des offres : [documentation officielle Vast](https://docs.vast.ai/cli/reference/search-instances).

## Mode d'essai des spécialistes CAO

Le champ optionnel du manifeste `execution_mode: "cad-specialists-v1"`
réutilise l'image et les garde-fous financiers, mais démarre seulement un
processus d'attente borné : aucun serveur Qwen, téléchargement de ses poids
ou port API. L'absence du champ conserve le profil documentaire historique.
`cad-specialist-offers` recherche les GPU explicitement admis de 24 Go ou plus,
avec 8 CPU effectifs et 32 Go de RAM au minimum. Le plafond de 0,85 USD/h,
les frais de transfert bornés et la garde de suppression restent inchangés.

`cad-specialist-offers OFFER_ID` fournit un diagnostic de relecture sans
création : nombres d'offres, identifiants entiers et empreinte de requête.
Une offre affichée n'est pas une réservation ; le lancement exige une nouvelle
correspondance exacte avant l'appel payant.

Les champs Qwen de qualification attestent uniquement le profil de base et
conservent une provision de téléchargement prudente. Le reçu spécialiste
indique `model: null`, `api_bind: null` et `specialist_weights_verified: false`.
Il faut donc vérifier séparément les révisions et l'inférence effectives de
cadrille et CAD-Recode, puis exécuter leur code généré dans un bac à sable
indépendant. Voir le [compte rendu spécialisé](../../../docs/M64_CAD_SPECIALISTS_20260912.md).
