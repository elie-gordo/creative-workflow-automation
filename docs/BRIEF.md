# Brief — Pipeline éditorial hebdomadaire LinkedIn + Instagram

> Statut : **validé le 2026-10-15**. Rien n'est construit.
> Légende : ✅ décidé · 💡 proposition · ❓ inconnu / à vérifier (étape 3)

## 1. Problème

Un petit commerce veut publier régulièrement sur LinkedIn et Instagram, mais :
- manque de temps pour écrire chaque jour ;
- tombe vite dans la répétition (mêmes accroches, mêmes sujets) ;
- doit adapter chaque message à chaque plateforme (ton, longueur, visuel) ;
- ne veut pas qu'une IA publie quoi que ce soit sans relecture.

## 2. Utilisateur fictif

✅ **Café Lumen** — torréfaction artisanale **fictive** (aucun lien avec une entreprise réelle).
Persona : la gérante, seule à gérer la communication, 15 min par jour disponibles.
Besoin : donner **une idée le lundi** et recevoir **chaque matin** des posts prêts à valider.

## 3. Principe

✅ 1 idée par semaine → 5 jours × 2 plateformes = **10 posts**, dont 5 visuels Instagram, tous validés par un humain avant d'être déposés dans la boîte d'envoi.
✅ Publication **simulée** : aucune connexion à un vrai compte LinkedIn / Instagram.

## 4. Données d'entrée

Formulaire n8n « Idée de la semaine » :

| Champ | Obligatoire | Exemple fictif | Règle |
|---|---|---|---|
| `week_start` | oui | 2026-10-19 | date, un lundi |
| `theme` | oui | Lancement du cold brew d'automne | 10–120 car. |
| `key_message` | oui | Infusé 18 h, sans sucre ajouté | 10–200 car. |
| `product` | non | Cold Brew Lumen 25 cl | ≤ 80 car. |
| `tone` | oui | chaleureux, direct | liste fermée |
| `cta` | non | Disponible en boutique | ≤ 40 car. |

Données de référence (fichiers fictifs dans `fixtures/`) : charte de marque (couleurs, typo, ton), 5 angles, réponses IA simulées.

## 5. Les 5 angles (rotation fixe) 💡

| Jour | Angle | LinkedIn | Instagram |
|---|---|---|---|
| Lun | Chiffre clé | post développé autour d'un chiffre | visuel « gros chiffre » + légende |
| Mar | Astuce | liste de 3 conseils | visuel titre + légende |
| Mer | Coulisses | court récit | visuel citation + légende |
| Jeu | Question | question ouverte à la communauté | visuel question + légende |
| Ven | Produit | mise en avant + CTA | visuel produit (texte) + légende |

La variété vient d'abord de la **structure** (angles), ensuite de l'IA.

## 6. Étapes du workflow 💡

**Workflow A — Planifier la semaine** (déclenché par le formulaire)
1. Réception du formulaire.
2. Validation des champs → si invalide : réponse listant les erreurs, rien n'est créé.
3. Construction du plan : 5 créneaux (jour × angle) avec statut `planned`.
4. Enregistrement du plan (stockage ❓ : Data Table n8n ou fichier JSON — tranché étape 4).

**Workflow B — Produire le jour** (planifié chaque jour ouvré + déclenchement manuel avec date forcée pour la démo)
1. Lecture du créneau du jour → aucun créneau : arrêt propre.
2. Construction du prompt (brief + angle + charte + accroches déjà utilisées).
3. **Étape IA** (unique) : renvoie un JSON avec le texte LinkedIn, la légende Instagram, les hashtags et le texte du visuel.
   Mode `mock` (fichier fixe) ou `live` (API réelle), choisi par variable.
4. Validation de la réponse (JSON, champs, longueurs, nombre de hashtags) → 1 nouvel essai, sinon erreur.
5. Anti-répétition : comparaison de l'accroche avec l'historique (code, pas IA) → 1 nouvel essai, sinon signalé « à revoir ».
6. Génération du visuel Instagram (gabarit SVG selon l'angle, couleurs de la charte).
7. Écriture des fichiers + statut `to_review`.
8. **Validation humaine** (formulaire n8n) : approuver / rejeter (+ motif).
9. Approuvé → copie dans `outbox/` ; rejeté → `rejected/` avec motif. Journal mis à jour.

**Workflow d'erreur** : toute exception non gérée → dossier `_errors/` + entrée de journal.

## 7. Résultat attendu

> Écart à la réalisation : le nœud d'écriture de n8n ne crée pas de dossiers. Les sorties sont donc rangées dans 4 dossiers fixes, avec la semaine, le jour et l'angle dans le nom de fichier (ex. `output/2026-W43_1-lun_chiffre_linkedin.md`). Les réponses simulées sont intégrées au workflow plutôt que dans `fixtures/`.

```
output/
└── 2026-W43_cafe-lumen/
    ├── plan.json
    ├── 1-lun_chiffre/
    │   ├── linkedin.md
    │   ├── instagram_caption.md
    │   ├── instagram_1080x1350.svg
    │   └── meta.json          # statut, mode mock/live, version du prompt, horodatage, erreurs
    ├── 2-mar_astuce/ …
    ├── outbox/                # posts approuvés, prêts à publier
    ├── rejected/
    └── _errors/
```

## 8. Inclus / exclus

| Inclus ✅ | Exclus ✅ |
|---|---|
| 2 plateformes : LinkedIn, Instagram | publication réelle sur un compte |
| 5 angles, 5 jours, 1 visuel par jour | carrousels, vidéo, stories |
| mode mock (0 €) + mode live optionnel | génération d'images par IA |
| validation humaine via formulaire n8n | e-mail, Slack, Telegram ou toute messagerie réelle |
| gestion d'erreurs + journal | statistiques d'engagement |
| visuels SVG | PNG (amélioration possible, dépendance externe) |
| export du workflow sans secrets, README, `.env.example` | modification du portfolio |

## 9. Outils et intégrations 💡

| Outil | Rôle | Coût / condition |
|---|---|---|
| n8n (auto-hébergé) | orchestration, formulaires, planification | ❓ licence Sustainable Use (source disponible, pas open source) — usage à vérifier |
| Hébergement cloud | faire tourner n8n en continu (déclencheur quotidien) | ❓ Oracle Always Free vs alternatives — étape 3 |
| API LLM (optionnelle) | rédaction des posts en mode live | ❓ fournisseur avec offre gratuite à comparer — étape 3 |
| Gabarits SVG | visuels | 0 €, fichiers du dépôt |

Aucune API LinkedIn / Instagram utilisée.

## 10. Risques, limites, coûts

- **Hébergement** ❓ : le déclencheur quotidien exige un n8n allumé en permanence. Oracle Always Free : disponibilité des instances, carte bancaire demandée, risque de récupération des instances inactives — à vérifier.
- **Offre gratuite LLM** ❓ : quotas, conditions d'utilisation des données, pérennité non garantis. Le mode mock garantit une démo fonctionnelle sans API.
- **Qualité IA** : textes parfois génériques ou inexacts → atténué par les angles, les contraintes, la validation humaine.
- **Limites des plateformes** ❓ (longueur des posts, nombre de hashtags) : à revérifier avant de les coder.
- **Publication réelle** : nécessiterait des comptes professionnels, une application déclarée et des autorisations — documenté, non réalisé.
- **Coût cible** : 0 € en mode mock. Estimation du mode live et de l'hébergement pérenne : étape 3.

## 11. Critères de réussite de la démo

1. Un formulaire valide crée un plan de 5 créneaux.
2. Un formulaire invalide est refusé avec la liste des erreurs, sans fichier créé.
3. En mode mock, la production d'un jour génère les 4 fichiers attendus dans le bon dossier.
4. Une réponse IA invalide (fixture volontairement cassée) déclenche un nouvel essai puis une erreur tracée.
5. Une accroche répétée (fixture) est détectée et signalée.
6. Approuver déplace le post dans `outbox/` ; rejeter le place dans `rejected/` avec le motif.
7. Une semaine complète (5 jours forcés manuellement) produit 10 posts et 5 visuels.
8. Aucun secret dans les exports, journaux ou captures (vérification par recherche dans le dépôt).
9. Le mode live, s'il est configuré, produit un JSON accepté par la même validation.
