# Vérifications

Deux niveaux de tests, tous deux exécutés le 2026-10-16.

## 1. Tests hors ligne : 57/57
`python scripts/build_workflows.py && node scripts/offline_tests.mjs`

Le script exécute le **JavaScript réel** des nœuds Code (extrait des workflows générés) avec des variables n8n simulées (`$input`, `$`, `$execution`, `$now`). Aucune instance n8n n'est nécessaire.

| Domaine | Ce qui est vérifié |
|---|---|
| Brief (A) | brief TENSIL accepté ; refus d'une date hors lundi, d'un ton inconnu, d'un thème trop court, d'un prix, d'une vente, d'une livraison, d'un chiffre hors fiche ; plan de 5 créneaux ; semaine en double refusée |
| Génération (B) | les 5 angles passent au 1er essai, avec le bon rendu et la fiche produit dans le prompt ; scénarios `claim`, `invalid_once`, `invalid_json`, `repeat` ; même angle la semaine suivante → nouvelle accroche |
| Rejets | LED, chiffre inventé (« 1,2 kg »), « à la main », superlatif, hashtag invalide, texte trop long, titre d'anatomie sans chiffre |
| Fichiers | 4 fichiers par jour, SVG avec le rendu intégré, `meta.json` complet, mention « marque fictive », chemins à plat ; rendu indisponible → `needs_review` |
| Décision et erreur | approuvé → `outbox/` avec SVG ; rejeté → `rejected/` avec motif ; échec → `_errors/` avec brief et contrôles |

Ce test a révélé un défaut, corrigé avant le déploiement : les nombres décimaux étaient découpés (« 1,2 » lu comme « 1 » et « 2 », deux nombres autorisés).

## 2. Tests de bout en bout : 23/23
`python scripts/e2e_tests.py` sur n8n **2.43.6** auto-hébergé (Docker), joignable par réseau privé Tailscale, en mode **mock**. Le script pilote les vrais formulaires et webhooks, puis lit la Data table, les exécutions (API n8n) et les fichiers (workflow T).

| # | Scénario | Attendu | Résultat |
|---|---|---|---|
| 1 | Brief invalide (mardi, thème de 5 caractères, ton inconnu, « En vente à 249 € avec livraison offerte ») | page « Brief refusé » listant les erreurs, aucune ligne créée | ✅ |
| 2 | Brief TENSIL valide (2026-W43) | 5 créneaux `planned`, un angle par jour, accents conservés | ✅ |
| 3 | Même semaine soumise à nouveau | refus « déjà planifiée » | ✅ |
| 4 | Lundi dévoilement, réponse valide | `to_review`, lien de validation enregistré | ✅ |
| 5 | Mardi anatomie, `claim` (promesse « disponible à 249 € ») | 3 motifs relevés au 1er essai (prix, vente, chiffre), 2e essai propre, `to_review` | ✅ |
| 6 | Mercredi coulisses, `invalid_json` | 2 essais, statut `error`, trace dans `_errors/` | ✅ |
| 7 | Jeudi coloris, `repeat` (accroche du lundi) | répétition détectée, `needs_review` | ✅ |
| 8 | Vendredi boutique rejeté avec motif | `rejected`, motif enregistré, fichiers dans `rejected/` | ✅ |
| 9 | Lundi approuvé | `approved`, textes et visuel dans `outbox/` | ✅ |
| 10 | Samedi, aucun créneau | arrêt propre sur « Rien à produire » | ✅ |
| 11 | Semaine 2026-W44, lundi `invalid_once` | 2e essai, accroche différente de la semaine 43 | ✅ |
| 12 | Workflow temporaire qui lève une exception, avec E comme workflow d'erreur | E écrit `_errors/workflow_<id>.json`, puis le workflow temporaire est supprimé | ✅ |
| 13 | Fichiers clés (output, outbox, rejected, _errors), 4 visuels avec le rendu intégré, `meta.json` du mardi (2 contrôles, rendu épinglé, `published: false`), post approuvé sans « € » et avec la mention « marque fictive » | présents et conformes | ✅ (11 contrôles) |

Les fichiers de ce passage sont dans [examples/](../examples/). Les visuels produits ont été convertis en PNG (Chrome headless) et contrôlés à l'œil : [docs/img/](img/). Le visuel du mercredi (coulisses) provient d'une production réelle sur la semaine 2026-W44, le mercredi de la semaine 43 servant au scénario d'erreur.

### Fait établi pendant les tests
Dans n8n 2.43.6, un workflow d'erreur **non publié** ne se déclenche pas : l'exécution en panne 581 n'a produit aucune exécution de E. Une fois E publié, l'exécution 582 a déclenché E (583, succès). Le déploiement publie donc E.

## Recherche de secrets
Recherche dans le dépôt (hors `.git` et `.env`) des motifs : jeton n8n (`eyJhbGci`), clé OpenAI (`sk-…`), nom d'hôte Tailscale (`*.ts.net`), signatures d'URL, identifiants de table et de workflows de l'instance. **Aucune occurrence**, en dehors d'un exemple générique d'URL en commentaire et du motif de masquage lui-même. Dans `examples/`, les liens de validation sont remplacés par `https://n8n.example.com/…?signature=REDACTED`. Les exports ne contiennent aucune credential ; l'identifiant de la Data table est remplacé par `REPLACE_WITH_tensil_slots_TABLE_ID`.
