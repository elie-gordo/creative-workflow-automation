# Café Lumen — pipeline éditorial automatisé (n8n)

> Projet de démonstration pour portfolio. **Café Lumen est une marque fictive** ; toutes les données sont inventées. Aucune publication réelle n'est effectuée.

Une idée saisie le lundi devient, chaque jour ouvré, un post LinkedIn et un post Instagram avec visuel. Chaque post est contrôlé automatiquement, puis **validé par un humain** avant d'être déposé dans une boîte d'envoi simulée.

![Visuel généré pour le lundi de la semaine de démonstration](docs/img/2026-W43_1-lun_chiffre_instagram_1080x1350.png)

## Fonctionnement

| Workflow | Déclencheur | Rôle |
|---|---|---|
| `CL — A · Planifier la semaine` | formulaire n8n | valide le brief, refuse une semaine déjà planifiée, crée 5 créneaux (1 angle par jour) |
| `CL — B · Produire le jour` | planification lun–ven 8 h (désactivée par défaut) + webhook de test | génère, contrôle, crée les fichiers, attend la validation humaine, classe le résultat |
| `CL — E · Erreurs` | Error Trigger | écrit une trace pour toute exception non gérée (aucune notification) |
| `CL — T · Inspecter les sorties` | webhook GET | liste les fichiers produits (lecture seule), utile sans accès au disque |

```
[A] Formulaire ─► Valider ─► Semaine déjà planifiée ? ─► 5 créneaux (Data table cl_slots)
[B] 8 h / webhook ─► Créneau du jour ─► Historique ─► Prompt ─► IA (mock | OpenAI) ◄── 1 nouvel essai
        ─► Validation JSON + longueurs + anti-répétition ─► Visuel SVG ─► Fichiers ─► statut to_review
        ─► Formulaire de validation ─► approuvé : outbox/   rejeté : rejected/ + motif
        └► échec après nouvel essai : _errors/ + statut error
```

**Les 5 angles** : lundi chiffre clé, mardi astuce, mercredi coulisses, jeudi question, vendredi produit.

**Rôle de l'IA** : une seule étape. À partir du brief et de l'angle du jour, elle renvoie un JSON (accroche, texte LinkedIn, légende Instagram, hashtags, textes du visuel). Tout le reste est déterministe : validation, contrôle des longueurs, détection des répétitions, mise en page du visuel, classement des fichiers.

## Mode démo et mode réel

| | `mock` (par défaut) | `live` |
|---|---|---|
| Rédaction | réponses simulées intégrées au workflow | API OpenAI (`gpt-4o-mini`, via une credential n8n) |
| Coût | 0 € | ≈ 0,0005 $ par appel (voir [docs/COSTS.md](docs/COSTS.md)) |
| Compte requis | aucun | clé API OpenAI |
| Scénarios de test | `valid`, `invalid_once`, `invalid_json`, `repeat` | — |

Le mode simulé permet de démontrer le classement, la validation et les chemins d'erreur sans abonnement. Il ne démontre **pas** la qualité rédactionnelle d'un modèle.

## Installation

Prérequis : n8n **2.x** auto-hébergé (testé sur 2.43.6) avec Data tables.

1. **Data table** : créer une table `cl_slots` avec les colonnes listées dans `COLUMNS` de [scripts/build_workflows.py](scripts/build_workflows.py) (toutes en `string` sauf `day_index` en `number`).
2. **Dossiers de sortie** : n8n 2.x limite l'écriture de fichiers à `~/.n8n-files` et ne crée pas les dossiers. Il faut les créer une fois :
   ```bash
   docker exec <conteneur-n8n> mkdir -p /home/node/.n8n-files/cafe-lumen/{output,outbox,rejected,_errors}
   ```
   Pour conserver les fichiers après une mise à jour du conteneur, montez un volume sur `/home/node/.n8n-files`.
3. **Import** : importer les 4 fichiers de [workflows/](workflows/), puis :
   - dans chaque nœud Data table, sélectionner `cl_slots` (l'export contient `REPLACE_WITH_cl_slots_TABLE_ID`) ;
   - dans les paramètres de A et B, définir `CL — E · Erreurs` comme workflow d'erreur ;
   - activer A, B et T. La planification quotidienne de B reste désactivée tant qu'on ne l'active pas.
4. **URL publique** : `N8N_EDITOR_BASE_URL` et `WEBHOOK_URL` (ou `N8N_WEBHOOK_URL`) doivent pointer vers l'adresse réellement utilisée. Sinon, les liens de formulaire générés renvoient vers `localhost`.
5. **Mode live (optionnel)** : créer une credential n8n de type *OpenAI*, l'associer au nœud `OpenAI : générer`, puis passer `mode: 'live'` dans le nœud `Contexte` (ou envoyer `"mode": "live"` au webhook de test).

Alternative à l'import manuel : `scripts/build_workflows.py --deploy` crée la table et les workflows par l'API publique n8n (variables dans [.env.example](.env.example)).

## Utilisation

- **Formulaire de la semaine** : `https://<n8n>/form/cl-brief`
- **Produire un jour à date forcée (démo)** :
  ```bash
  curl -X POST https://<n8n>/webhook/cl-produire -H "Content-Type: application/json" \
       -d '{"date":"2026-10-19","mock_case":"valid"}'
  ```
- **Valider** : le lien du formulaire de validation est enregistré dans `cl_slots.review_url` et dans `*_meta.json`.
- **Voir les fichiers** : `https://<n8n>/webhook/cl-inspect`

Sorties dans `~/.n8n-files/cafe-lumen/`. Les noms de fichiers sont à plat : semaine, jour et angle sont dans le nom, car le nœud d'écriture de n8n ne crée pas de dossiers.
```
output/2026-W43_1-lun_chiffre_{linkedin.md, instagram_caption.md, instagram_1080x1350.svg, meta.json}
outbox/   …_decision.json + post approuvé        rejected/ …_decision.json + motif
_errors/  2026-W43_3-mer_<execution>.json
```
Un jeu complet de sorties réelles, issu des tests, se trouve dans [examples/](examples/).

## Vérifications

`scripts/e2e_tests.py` joue 10 scénarios contre une instance réelle, en mode simulé, et contrôle 7 fichiers produits. Dernier passage : **17/17 contrôles réussis** (n8n 2.43.6). Le détail des scénarios et ce qui n'a pas été vérifié sont dans [docs/VERIFICATION.md](docs/VERIFICATION.md).

## Limites

- Aucune publication réelle sur LinkedIn ou Instagram : il faudrait des comptes professionnels, une application déclarée et des autorisations d'API.
- Le mode live n'a pas encore été testé avec une vraie clé (voir [docs/VERIFICATION.md](docs/VERIFICATION.md)).
- Visuels en SVG. Une conversion en PNG demanderait une dépendance externe.
- L'anti-répétition compare les mots des accroches (similarité de Jaccard). Elle ne détecte pas les reformulations sémantiques.
- Le lien de validation n'est envoyé nulle part : il faut le récupérer dans la table ou le fichier `meta.json`.
- Licence n8n : *Sustainable Use License*, source disponible mais **pas open source** (voir [docs/CREDITS.md](docs/CREDITS.md)).

## Sécurité

- Aucun identifiant ni secret dans le dépôt ou dans les exports. La clé OpenAI reste dans une credential n8n.
- Les webhooks de démo n'ont pas d'authentification : l'instance de test n'est joignable que par réseau privé (Tailscale). Sur une instance publique, ajoutez une authentification par en-tête au webhook B et au webhook T.

## Documentation

- [Brief](docs/BRIEF.md) · [Architecture et faisabilité](docs/ARCHITECTURE.md) · [Vérifications](docs/VERIFICATION.md)
- [Coûts](docs/COSTS.md) · [Crédits & licences](docs/CREDITS.md) · [Contenu portfolio](docs/PORTFOLIO.md)
