# Architecture

## Vue d'ensemble

```
                ┌──────────── serveur personnel (Docker, n8n 2.43.6) ─────────────┐
 Navigateur ─Tailscale─► n8n ──► Data table tensil_slots (plan, statuts, textes)    │
 (formulaires,  │         ├──► ~/.n8n-files/tensil/{output,outbox,rejected,_errors} │
  validation)   │         ├──► api.github.com ─► rendus Blender (commit épinglé)   │
                │         └──► api.openai.com [live] ou mock intégré               │
                └─────────────────────────────────────────────────────────────────┘
 Poste de travail ─API n8n─► scripts/build_workflows.py (déploiement, export)
                           └► scripts/e2e_tests.py (scénarios de bout en bout)
```

- **Hébergement** : n8n auto-hébergé sur un serveur personnel (Docker), accessible uniquement par réseau privé **Tailscale**, HTTPS fourni par `tailscale serve`. Pas de domaine, pas de cloud public.
- **IA** : mode **mock** par défaut ; mode **live** via l'API **OpenAI** (`gpt-4o-mini`) avec une credential n8n.
- **Stockage** : Data table `tensil_slots` et fichiers sous `~/.n8n-files/tensil/`.
- **Visuels** : rendus Blender existants, lus par l'API GitHub publique à un commit fixé, intégrés en base64 dans le SVG. Aucune génération d'image.

## Workflows

| Workflow | Nœuds | Déclencheur | Rôle |
|---|---|---|---|
| A · Planifier la semaine | 8 | formulaire `tensil-brief` | valide le brief (règles, promesses, chiffres), refuse une semaine en double, crée 5 créneaux |
| B · Produire le jour | 26 | 8 h en semaine (désactivé) + webhook `tensil-produire` | prompt avec fiche produit → IA (mock ou OpenAI) → contrôles → nouvel essai → rendu GitHub → fichiers → validation humaine → classement |
| E · Erreurs | 3 | Error Trigger (publié : n8n 2.x l'exige) | trace JSON dans `_errors/` |
| T · Inspecter | 3 | webhook GET `tensil-inspect` | liste des fichiers, lecture seule |

## Choix et compromis
- **Le code n8n est généré** par `scripts/build_workflows.py`, une seule source pour le déploiement et l'export. Les nœuds Code sont testés hors ligne (`scripts/offline_tests.mjs`).
- **Fiche produit dans le code** : les faits sont recopiés des dépôts [blender-studio-object](https://github.com/elie-gordo/blender-studio-object) et [website-redesign](https://github.com/elie-gordo/website-redesign). S'ils évoluent, `PRODUCT_FACTS` est à mettre à jour.
- **Rendus lus sur GitHub** plutôt que copiés sur le serveur : aucun fichier à installer, provenance traçable dans `meta.json` ; en contrepartie, une dépendance réseau et la limite anonyme de 60 requêtes par heure.
- **Une seule étape IA**, isolée derrière un schéma JSON : changer de fournisseur compatible OpenAI revient à changer l'URL et le modèle du nœud HTTP.
- **Deux nœuds de fusion par position** : un pour la réponse OpenAI (mode live), un pour le rendu.

## Contraintes n8n prises en compte
- **Licence** : Sustainable Use License, **source disponible, pas open source**. Usage interne, personnel ou non commercial autorisé ; revendre l'hébergement de n8n n'est pas couvert. Une démo portfolio auto-hébergée sur données fictives est compatible.
- **Fichiers** : en v2, les nœuds de lecture/écriture n'accèdent par défaut qu'à `~/.n8n-files` (`N8N_RESTRICT_FILE_ACCESS_TO`) et ne créent pas de dossiers ; Execute Command est désactivé. D'où les dossiers créés à l'installation et les noms de fichiers à plat.
- **Data tables** : stockage interne (limite par défaut 200 Mio), lu et écrit par le nœud Data Table, pas par le nœud Code.
- **Workflow d'erreur** : ne se déclenche que s'il est publié.
- **Clé de chiffrement** (`N8N_ENCRYPTION_KEY`) : chiffre les credentials en base ; à sauvegarder hors du dépôt.
- **URL publique** : `N8N_WEBHOOK_URL` à partir de n8n 2.30.0, `WEBHOOK_URL` avant.

## Contraintes des plateformes
| Règle | Valeur | Limite interne du workflow |
|---|---|---|
| Post LinkedIn | 3 000 caractères max | 100–1 300 |
| Légende Instagram | 2 200 caractères max | 50–600 |
| Hashtags Instagram | 30 max | 3–8 |
| Format d'image Instagram | ratio entre 4:5 et 1,91:1, largeur 1080 px, hauteur jusqu'à 1350 px | 1080 × 1350 (4:5) |

## Sources
- n8n — licence : https://github.com/n8n-io/n8n/blob/master/LICENSE.md
- n8n — changements v2.0 : https://docs.n8n.io/2-0-breaking-changes/
- n8n — nœud Read/Write Files : https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.readwritefile
- n8n — Data tables : https://docs.n8n.io/data/data-tables/
- GitHub — API Contents : https://docs.github.com/en/rest/repos/contents
- LinkedIn — publier : https://www.linkedin.com/help/linkedin/answer/a528176
- Instagram — résolution d'image : https://help.instagram.com/1631821640426723/
- Instagram Graph API — IG User Media : https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media
