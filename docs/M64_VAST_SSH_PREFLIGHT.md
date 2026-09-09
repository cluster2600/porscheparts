# Prévol SSH Vast — 7 septembre 2026

Le wrapper `outils/deploy/openbao/openbao-vastai` sépare désormais trois preuves :

1. **Paire locale utilisable**, avant enregistrement et création payante :
   validation des métadonnées du fichier privé approuvé, puis OpenSSH
   `ssh-keygen -y` dérive sa seule identité publique. La comparaison ignore
   les commentaires. L'opération est bornée à 10 secondes, sans saisie,
   agent ou variable d'authentification héritée. Ni clé privée, ni sortie
   publique, ni erreur brute de cette commande ne sont affichées.
2. **Clé listée pour l'instance exacte** : lecture de son endpoint SSH,
   attachement de la seule clé approuvée si absente, accusé strict `true`,
   puis relecture (trois tentatives au maximum). Un attachement POST n'est
   jamais rejoué automatiquement. Un reçu JSON fixe conserve l'ID, le label
   unique et les booléens de preuve, sans clés ni commentaires.
3. **Authentification et service effectifs** : la vérification SSH BatchMode
   et du marqueur READY demeure obligatoire. La preuve des étapes 1 et 2
   **ne prouve pas** l'injection de `authorized_keys` dans le conteneur.

En cas d'échec SSH terminal, le reçu conserve l'hôte/port réellement utilisés,
le code de retour et des indicateurs dérivés (`permission_denied`,
`key_load_failed`, `bad_key_permissions`). Aucun stdout/stderr brut n'est
journalisé. La suppression avec preuve d'absence demeure obligatoire sur
échec après création ; ces diagnostics ne désactivent aucun contrôle de clé
d'hôte, d'identité ou de disponibilité.

Les tests utilisent des clés et réponses synthétiques. Ils ne prouvent ni
une connexion réelle sur Vast, ni un calcul sur la culasse.

La commande en lecture seule `ssh-endpoints <id>` expose séparément la paire
`ssh_host` / `ssh_port` et la paire `public_ipaddr` / `ports[22/tcp][0].HostPort`.
Elle refuse un ID retourné différent et masque une paire incomplète ou invalide.
Elle ne change pas le choix courant du wrapper, n'essaie pas de connexion et ne
présente pas ces métadonnées comme une preuve d'accessibilité.

Le sélecteur existant normalise aussi le `HostPort` direct en entier : Vast
peut le retourner sous forme de chaîne décimale. Les formats non décimaux,
booléens et valeurs hors de 1 à 65535 sont refusés. La priorité de la paire
proxy complète reste inchangée ; aucune adresse proxy n'est combinée avec
le port direct, et aucun contrôle d'authentification n'est assoupli.

Références du fournisseur :
[SSH](https://docs.vast.ai/guides/instances/connect/ssh),
[attachement SSH](https://docs.vast.ai/api-reference/instances/attach-ssh-key).
