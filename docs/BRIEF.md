# Brief — Campagne TENSIL préparée avec n8n

> Statut : **réalisé**, livré le 2026-10-16.

## 1. Problème
Lancer un produit demande de publier chaque jour un message distinct, adapté à LinkedIn et à Instagram, et **fidèle au produit**. Une IA rédige vite, mais elle invente facilement des caractéristiques, des prix ou des promesses, et elle se répète. Personne ne veut qu'elle publie sans relecture.

## 2. Contexte de portfolio
TENSIL, lampe de bureau articulée **fictive**, est présentée sous plusieurs angles :

| Projet | Rôle | Ce que ce dépôt en reprend |
|---|---|---|
| [blender-studio-object](https://github.com/elie-gordo/blender-studio-object) | modèle 3D, rendus, animation | les rendus `renders/web/*.webp` (lus à un commit fixé) et les faits de construction |
| [website-redesign](https://github.com/elie-gordo/website-redesign) | boutique de démonstration | dimensions, matériaux, coloris, existence de la boutique |
| ce dépôt | préparation de la campagne de lancement | — |
| teaser vidéo | projet séparé | rien : ce workflow ne produit pas de film |

Les deux dépôts de contexte ne sont **pas modifiés**.

## 3. Principe
1 brief par semaine → 5 jours × (LinkedIn + Instagram + visuel 1080×1350), soit 10 textes et 5 visuels, tous validés par un humain. Publication **simulée** : aucune connexion à un vrai compte.

## 4. Données d'entrée (formulaire A)
| Champ | Obligatoire | Exemple | Règle |
|---|---|---|---|
| Semaine | oui | 2026-10-19 | un lundi |
| Thème | oui | Semaine de présentation de la lampe TENSIL | 10–120 caractères |
| Message clé | oui | Une lampe de bureau articulée, équilibrée par 2 ressorts par segment | 10–200 caractères |
| Produit ou coloris | non | TENSIL Graphite | ≤ 80 caractères |
| Ton | oui | sobre | sobre, technique, chaleureux, direct |
| Appel à l'action | non | Voir la boutique de démonstration | ≤ 40 caractères |

Pour tous les champs : pas de prix ni de promesse de vente, et aucun chiffre absent de la fiche produit.

## 5. Fiche produit (seuls faits autorisés)
- Marque fictive créée pour un portfolio ; la lampe n'est pas commercialisée.
- Bras en deux segments de 30 cm (portée de 60 cm), 2 ressorts équilibreurs par segment, sans molette à serrer.
- Principe des ressorts équilibreurs connu depuis les années 1930, réinterprété avec une silhouette propre.
- Base en disque lestée de 22 cm ; hauteur de 43 cm en position de travail ; abat-jour conique de 15 cm avec réflecteur interne.
- Matériaux représentés : acier laqué verni, laiton brossé (rotules), acier poli (ressorts), câble en caoutchouc.
- 4 coloris de laque : Graphite, Sauge, Oxyde, Crème.
- Images de synthèse : modèle construit par scripts Python dans Blender 5.2, rendu Cycles ; un film de 8 s (dépliement, allumage).
- Boutique de démonstration en ligne : vue 3D à 360°, coloris en direct, commande simulée, sans paiement ni vente.

**Exclu volontairement** : le prix fictif de 249 € et les formulations commerciales du site qu'on ne peut pas vérifier (« brossés à la main », « sans éblouissement »).

## 6. Les 5 angles
| Jour | Angle | Message | Visuel |
|---|---|---|---|
| Lun | Dévoilement | la lampe, le principe des ressorts | rendu héros |
| Mar | Anatomie | un chiffre de la fiche et le détail qu'il décrit | gros plan ressort et rotule, titre en grand chiffre |
| Mer | Coulisses | construction 3D par le code, images de synthèse | rendu en fil de fer |
| Jeu | Coloris | les 4 laques, question à la communauté | planche des 4 coloris |
| Ven | La boutique | vue 3D, coloris en direct, commande simulée, rien n'est vendu | lampe allumée |

## 7. Critères de réussite
1. Un brief valide crée 5 créneaux ; un brief invalide (date, ton, longueur, prix, chiffre) est refusé sans rien écrire.
2. Une semaine déjà planifiée est refusée.
3. En mode simulé, un jour produit 4 fichiers dans `output/`, avec le rendu Blender intégré au visuel.
4. Une promesse interdite déclenche un nouvel essai.
5. Une réponse invalide déclenche un nouvel essai, puis une erreur tracée.
6. Une accroche répétée est détectée et signalée (`needs_review`).
7. Approuver range le post dans `outbox/`, rejeter le range dans `rejected/` avec le motif.
8. Une panne imprévue est tracée par le workflow d'erreur.
9. Aucun secret dans les exports, les exemples ou les captures.
10. Le mode live, s'il est configuré, passe par la même validation que le mode simulé.

## 8. Inclus / exclus
| Inclus | Exclus |
|---|---|
| LinkedIn et Instagram, 5 angles, 1 visuel par jour | publication réelle, carrousels, stories, vidéo |
| mode simulé (0 €) et mode live optionnel | génération d'images par IA (seuls les rendus existants sont utilisés) |
| validation humaine par formulaire n8n | e-mail, Slack, Telegram ou toute messagerie |
| contrôles de fidélité au produit | statistiques d'engagement, promesses de conversion |
| export sans secrets, tests, documentation | modification des dépôts Blender et boutique |
