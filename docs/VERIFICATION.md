# Vérifications

Instance : n8n **2.43.6** auto-hébergé (Docker), accessible par réseau privé Tailscale.
Méthode : `scripts/e2e_tests.py` pilote les vrais formulaires et webhooks, puis lit la Data table `cl_slots`, les exécutions (API publique n8n) et les fichiers produits (workflow T).
Mode : **mock** uniquement. Dernier passage : 2026-10-16, **17/17 contrôles réussis**.

## Scénarios réellement exécutés

| # | Scénario | Attendu | Résultat |
|---|---|---|---|
| 1 | Brief invalide (mardi, thème de 5 caractères, ton inconnu) | page « Brief refusé » listant 3 erreurs, aucune ligne créée | ✅ |
| 2 | Brief valide (semaine 2026-W43) | 5 créneaux `planned`, accents conservés | ✅ |
| 3 | Même semaine soumise une deuxième fois | refus « déjà planifiée », toujours 5 lignes | ✅ |
| 4 | Lundi, réponse IA valide | fichiers dans `output/`, statut `to_review`, lien de validation enregistré | ✅ |
| 5 | Mardi, réponse invalide puis valide (`invalid_once`) | 2e essai, puis `to_review` | ✅ (attempt = 2) |
| 6 | Mercredi, réponse toujours invalide (`invalid_json`) | 2 essais, statut `error`, trace dans `_errors/` | ✅ |
| 7 | Jeudi, accroche identique à celle du lundi (`repeat`) | répétition détectée, 2e essai, puis `needs_review` | ✅ |
| 8 | Vendredi rejeté avec motif via le formulaire de validation | statut `rejected`, motif enregistré, fichiers dans `rejected/` | ✅ |
| 9 | Lundi approuvé via le formulaire de validation | statut `approved`, fichiers + SVG dans `outbox/` | ✅ |
| 10 | Date sans créneau (samedi) | arrêt propre sur « Rien à produire » | ✅ |
| 11 | Présence de 7 fichiers clés (output, outbox, rejected, _errors) | fichiers listés par le workflow T | ✅ |

Les 4 visuels SVG produits ont été rendus en PNG (Chrome headless) et contrôlés visuellement : [docs/img/](img/).

## Recherche de secrets

Recherche dans tout le dépôt (hors `.git`) des motifs : jeton n8n (`eyJhbGci`), clé OpenAI (`sk-…`), nom d'hôte Tailscale (`*.ts.net`), signatures d'URL. **Aucune occurrence.** Dans `examples/`, les liens de validation ont été remplacés par `https://n8n.example.com/…?signature=REDACTED`. Les exports de workflows ne contiennent aucune credential ; l'identifiant de la Data table est remplacé par `REPLACE_WITH_cl_slots_TABLE_ID`.

## Non vérifié

| Élément | Raison |
|---|---|
| Mode `live` (OpenAI) | aucune credential configurée pour l'instant ; le nœud HTTP et le schéma JSON n'ont été qu'inspectés |
| Workflow E (exception non gérée) | aucune panne imprévue provoquée ; les erreurs prévues passent par le chemin d'erreur de B (testé) |
| Déclencheur planifié 8 h | volontairement désactivé ; testé uniquement par le webhook à date forcée |
| Rendu dans un vrai navigateur des formulaires | soumis par HTTP (multipart) ; seule la page de fin de A a été lue en HTML |
| Import manuel des JSON exportés dans une instance vierge | déploiement fait par l'API ; l'import par l'interface n'a pas été rejoué |
| Captures d'écran du canevas n8n | à faire (nécessite une session dans l'éditeur) |
