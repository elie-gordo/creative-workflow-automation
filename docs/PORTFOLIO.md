# Contenu de la page projet (portfolio)

> Le portfolio n'est pas modifié depuis ce dépôt. Ce fichier fournit le texte et les visuels à intégrer.

## Titre
**Pipeline éditorial automatisé — n8n + IA**

## Description courte (≈ 300 caractères)
Un workflow n8n qui transforme une idée hebdomadaire en 5 jours de posts LinkedIn et Instagram, avec un visuel par jour. Une étape IA rédige, le workflow contrôle, classe et décline, et un humain valide chaque post. Démonstration sur une marque fictive, sans publication réelle.

## Problème
Un petit commerce veut publier régulièrement sur LinkedIn et Instagram, mais il manque de temps, tombe vite dans la répétition et doit adapter chaque message à chaque plateforme. Il ne veut pas non plus qu'une IA publie sans relecture.

## Solution
- **Lundi** : un formulaire reçoit l'idée de la semaine (thème, message clé, produit, ton). Le workflow la valide et planifie 5 créneaux, avec un angle par jour : chiffre clé, astuce, coulisses, question, produit.
- **Chaque jour ouvré** : une étape IA renvoie un JSON structuré. Le workflow vérifie le format, les longueurs et les limites des plateformes, détecte les accroches déjà utilisées, relance une fois si nécessaire, génère le visuel Instagram 1080×1350 et range les fichiers.
- **Validation** : un formulaire présente le post. S'il est approuvé, il va dans la boîte d'envoi ; s'il est rejeté, il est archivé avec le motif.
- **Erreurs** : en cas d'échec après le nouvel essai, le post passe au statut `error` et une trace est écrite. Un workflow d'erreur dédié capte les pannes imprévues.

## Automatisé / manuel
| Automatisé | Manuel |
|---|---|
| validation du brief, planification de la semaine | saisie de l'idée de la semaine |
| rédaction (IA), contrôle du format, nouvel essai | validation ou rejet de chaque post |
| anti-répétition, génération du visuel, classement des fichiers | publication réelle (hors périmètre) |
| suivi des statuts, traces d'erreur | — |

## Rôle de l'IA et limites
- **Une seule étape IA**, enfermée dans un schéma JSON strict. Tout le reste est déterministe et vérifiable.
- L'IA peut produire des textes génériques ou inexacts. Le prompt interdit d'inventer des chiffres absents du brief, et la validation humaine reste obligatoire.
- L'anti-répétition compare les mots des accroches. Elle ne détecte pas les reformulations sémantiques.
- **Mode démo sans IA** : des réponses simulées permettent de rejouer tous les scénarios, y compris les erreurs, gratuitement.

## Outils
n8n 2.x auto-hébergé (Docker), Data tables n8n, nœuds Code (JavaScript), API OpenAI en option (`gpt-4o-mini`), Tailscale pour l'accès privé, Python pour le déploiement par l'API n8n et les tests de bout en bout.

## Coûts et quotas
- **0 €** en mode démo, sur un serveur déjà en service, sans domaine ni cloud.
- Mode IA réel : environ **0,0005 $ par appel**, soit moins de 0,02 $ par mois au volume prévu (tarif OpenAI vérifié le 2026-10-16).
- Hébergement cloud et offres gratuites (Oracle, Google Cloud, n8n Cloud, Gemini, Groq, Mistral) comparés et documentés, mais non utilisés.

## Compétences démontrées
- Conception d'un workflow lisible : 3 workflows (planifier, produire, erreurs) et un outil d'inspection.
- Intégration raisonnée d'une étape IA : sortie structurée, validation, nouvel essai, humain dans la boucle.
- Organisation des fichiers et des déclinaisons : 2 plateformes, 5 angles, un visuel par jour.
- Gestion des erreurs, des paramètres (mode mock/live) et des secrets (credentials n8n, export nettoyé).
- Vérification réelle : 10 scénarios exécutés sur une instance, **17/17 contrôles réussis**.
- Documentation des limites, des coûts et des licences (n8n : source disponible, pas open source).

## Chiffres clés
- 3 workflows métier et 1 outil, 38 nœuds au total.
- 1 idée par semaine donne 10 posts et 5 visuels.
- 10 scénarios testés, 0 € dépensé.

## Visuels
- [x] Visuels générés : `docs/img/2026-W43_*_instagram_1080x1350.png`
- [x] Schéma du workflow : `docs/img/workflow-diagram.svg`
- [x] Captures du canevas n8n (sans secrets) :
  - `docs/img/canvas-A-planifier.png` : workflow A
  - `docs/img/canvas-B-vue-ensemble.png` : workflow B en entier
  - `docs/img/canvas-B-detail.png` : cœur de B (IA, contrôles, nouvel essai, erreurs)
  - `docs/img/canvas-E-erreurs.png` : workflow E
  - Le triangle rouge sur « OpenAI : générer » signale l'absence de credential : le mode live n'est pas configuré.

## Ordre suggéré des visuels sur la page
1. `workflow-diagram.png` : comprendre le flux en 10 secondes
2. `canvas-B-detail.png` : preuve que c'est un vrai workflow n8n
3. 2 ou 3 visuels générés (`2026-W43_*.png`) : le résultat concret
4. `canvas-A-planifier.png` et `canvas-E-erreurs.png` : en complément

## Liens
- Dépôt : https://github.com/elie-gordo/creative-workflow-automation
- Démo / vidéo : non réalisée

## Contrôle final (prévu vs produit)
| Livrable prévu (brief) | Produit ? | Remarque |
|---|---|---|
| Cas d'usage validé | ✅ | `docs/BRIEF.md` |
| Architecture documentée | ✅ | `docs/ARCHITECTURE.md` |
| Workflow n8n exportable sans secrets | ✅ | `workflows/`, contrôle des secrets fait |
| Données de démonstration fictives | ✅ | Café Lumen, `examples/` |
| Documentation de reproduction | ✅ | `README.md` |
| Vérifications correspondant au brief | ⚠️ | 8 critères sur 9 ; le critère 9 (mode live) n'est pas testé |
| Dépôt Git dédié | ✅ | — |
| Visuels et résumé portfolio | ✅ | schéma, captures, visuels générés |
| Relevé des coûts et limites | ✅ | `docs/COSTS.md`, README |
