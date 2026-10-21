# Contacts dans le domaine libre et dans la matière

Cette extension conserve les auditeurs et prédicats historiques gelés. Elle
traite une interface source projetée dont une partie sort du domaine libre
déplié : le contact conservé est exactement
`interface_source ∩ domaine_libre ∩ matière_générée`.

`exact_contacts_both.py` réunit les paramètres rationnels d'intersection avec
les contours des **deux** polygones avant de vérifier chaque intervalle. Les
trous sont conservés. Les coordonnées sont encodées une seule fois, après le
clipping exact ; aucun tampon ou seuil géométrique n'est introduit. Un
intervalle exact non nul qui s'effondre en float64 reste refusé.

L'API est :

```python
clip_contacts_in_both(material, domain, interfaces_raw)  # segments Fraction
round_contacts_in_both(material, domain, interfaces_raw)  # encodage final
contact_encoding_check_in_both(material, domain, interfaces_raw, recorded)
```

Chaque contact et chaque groupe de faces porte les mêmes
`free_domain_geometry_wkb_hex`, `free_domain_geometry_sha256` et
`contact_clip_scope`. Ce dernier vaut
`source_interface_intersect_material_intersect_free_domain_exact_before_single_float64_encoding`.
Les interfaces sources restent brutes ; les traces de contact contiennent
seulement l'encodage final de l'intersection dans les deux domaines.

## Audit complet

```sh
"$AM_PYTHON" parts/993-eng-carrier-0001/source/process-scanpath-audit-20261016/audit_complete_supports_both.py \
  PROCESS OUTPUT --source-stl SOURCE_STL --part-cache PART_CACHE
```

`audit_support_scanpaths_both.py` valide les WKB et leur SHA au contact et au
groupe. Il charge une instance isolée de l'auditeur complet historique dont
il vérifie le SHA, puis remplace uniquement ses deux prédicats de contacts.
Un même couple matière/interfaces associé à deux domaines distincts est
refusé, sans dépendre de l'ordre des groupes. La boucle complète de couches,
les coupes indépendantes des triangles, les graphes chronologiques et la
vérification de contact réel avec la pièce/plaque sont conservés.

Le wrapper complet exige encore une exposition réelle de **chaque** groupe.
Le contrat de reçu reste `assessment.json`, `scanpaths/assessment.json` et
`group-exposure-coverage.json`, avec leurs empreintes et le même SHA du
rapport de procédé. Le reçu principal exige également
`every_material_group_exposed=true`.

## Vérifications conservées

Les [résultats compacts](both-contact-results.json) lient les sources, quatorze
tests ciblés et le [cas réel de carte225](both-contact-evidence/chart225-assessment.json).
Ses [entrées](both-contact-evidence/chart225-inputs.json) sont conservées avec
leurs coordonnées d'origine. Le calcul certifie cinq segments hauts et deux
bas dans les deux domaines ; les erreurs du seul encodage final restent
inférieures ou égales à une demi-ULP.

Les négatifs couvrent un pont au-dessus d'un trou, une altération d'une ULP,
une identité WKB incohérente, un champ de portée absent, un domaine ambigu et
un groupe matériel situé entre les plans d'exposition. Ce témoin ne constitue
pas un audit complet des supports du carrier : celui-ci attend le procédé
complet corrigé.
