# Contenu de la page projet (portfolio)

> Le portfolio n'est pas modifié depuis ce dépôt. Ce fichier fournit le texte et les visuels à intégrer.

## Titre
**TENSIL — préparer une campagne de lancement avec n8n et l'IA**

## Description courte (≈ 300 caractères)
Un workflow n8n qui transforme un brief en 5 jours de posts LinkedIn et Instagram pour TENSIL, une lampe fictive modélisée dans Blender. Une étape IA rédige, le code vérifie la fidélité au produit et met en page le visuel à partir des vrais rendus, un humain valide chaque post. Rien n'est publié.

## Place dans le portfolio
TENSIL est présentée sous plusieurs angles : le modèle 3D (Blender), la boutique de démonstration (site), cette campagne préparée avec n8n, et un teaser vidéo séparé. Ce projet relie les deux premiers : ses textes s'appuient sur les faits des dépôts, ses visuels sur les rendus Blender.

## Problème
Un lancement exige un message distinct chaque jour, adapté à chaque plateforme et fidèle au produit. Une IA rédige vite, mais elle invente facilement des prix, des caractéristiques ou des promesses. Pour une marque fictive qui ne vend rien, toute promesse commerciale serait fausse.

## Solution
- **Brief** : un formulaire reçoit le thème, le message clé, le coloris, le ton et l'appel à l'action. Le workflow refuse un prix, une promesse de vente ou un chiffre absent de la fiche produit, puis planifie 5 angles : dévoilement, anatomie, coulisses 3D, coloris, boutique.
- **Chaque jour** : l'IA rédige à partir d'une fiche produit limitée aux faits confirmés. Le code vérifie le format, les longueurs, les promesses interdites, les chiffres et les répétitions, puis relance une fois si nécessaire. Il compose ensuite le visuel 1080×1350 avec le rendu Blender de l'angle.
- **Validation** : un formulaire présente le post. Approuvé, il va dans la boîte d'envoi simulée ; rejeté, il est archivé avec le motif.
- **Erreurs** : en cas d'échec après le nouvel essai, une trace est écrite. Un workflow dédié capte les pannes imprévues.

## Automatisé / manuel
| Automatisé | Manuel |
|---|---|
| validation du brief, planification des 5 angles | rédaction du brief |
| rédaction (IA), contrôles de fidélité, nouvel essai | validation ou rejet de chaque post |
| visuel à partir des rendus existants, classement des fichiers | publication réelle (hors périmètre) |
| statuts, traces d'erreur | — |

## Rôle de l'IA et limites
- **Une seule étape IA**, contrainte par un schéma JSON et une fiche produit. Tout le reste est déterministe et testé.
- Les garde-fous (promesses, chiffres) reposent sur des listes : ils réduisent le risque sans le supprimer. La validation humaine reste obligatoire.
- **Mode démo sans IA** : des réponses simulées, écrites à partir de la fiche produit, rejouent tous les scénarios gratuitement. Le mode avec un vrai modèle (OpenAI) s'active avec une clé API.

## Outils
n8n 2.43.6 auto-hébergé (Docker), Data tables, nœuds Code (JavaScript), API GitHub (lecture des rendus), API OpenAI en option, Tailscale pour l'accès privé. Python pour le déploiement et les tests de bout en bout, Node.js pour les tests hors ligne.

## Coûts
**0 €** : serveur personnel déjà en service, mode démo, aucune génération d'image. Le mode avec un vrai modèle coûterait environ 0,0005 $ par appel.

## Compétences démontrées
- Conception d'un workflow lisible : 4 workflows (planifier, produire, erreurs, inspecter), 40 nœuds.
- Intégration raisonnée de l'IA : sortie structurée, fiche produit, contrôles de fidélité, nouvel essai, humain dans la boucle.
- Cohérence de marque entre projets : faits, rendus et direction artistique repris des projets Blender et boutique.
- Gestion des erreurs, des secrets (credentials n8n, export nettoyé) et de la provenance des visuels (commit épinglé).
- Tests réels : 57 contrôles hors ligne sur le code des nœuds, 23 contrôles de bout en bout sur une instance.
- Documentation honnête des limites.

## Chiffres clés
- 1 brief → 10 textes et 5 visuels, tous validés par un humain.
- 6 contrôles automatiques par post, 1 nouvel essai au maximum.
- 12 scénarios de bout en bout, 23/23 ; 57/57 hors ligne ; 0 € dépensé.

## Visuels
| Ordre | Fichier | Montre |
|---|---|---|
| 1 | `docs/img/campagne-tensil.png` | les 5 visuels de la campagne, tels que produits par le workflow |
| 2 | `docs/img/workflow-diagram.png` | le flux complet en 10 secondes |
| 3 | `docs/img/canvas-B-detail.png` | le cœur de B dans n8n : IA, contrôles, nouvel essai, rendu, erreurs |
| 4 | `docs/img/2026-W43_2-mar_anatomie_instagram_1080x1350.png` | un visuel seul, en grand |
| 5 | `docs/img/canvas-A-planifier.png`, `canvas-B-vue-ensemble.png`, `canvas-E-erreurs.png` | les autres workflows |

Captures du canevas prises sur l'instance de test le 2026-10-16, sans secret visible. Le triangle rouge sur « OpenAI : générer » et le point rouge du bouton « Publish » de B signalent qu'aucune clé OpenAI n'est enregistrée sur l'instance de démonstration, qui tourne en mode simulé. B est publié dans sa dernière version.

Extrait à citer (`examples/output/2026-W43_2-mar_anatomie_meta.json`) : au 1er essai, la réponse promettait « disponible à 249 € ». Le workflow l'a refusée pour 3 motifs (prix, vente, chiffre hors fiche), et le 2e essai est passé.

## Liens
- Dépôt : https://github.com/elie-gordo/creative-workflow-automation
- Projets liés : https://github.com/elie-gordo/blender-studio-object · https://github.com/elie-gordo/website-redesign

## Contrôle final (prévu vs produit)
| Livrable prévu | Produit ? | Remarque |
|---|---|---|
| Scénario TENSIL cohérent avec les dépôts | ✅ | fiche produit sourcée, `docs/BRIEF.md` |
| Workflows n8n exportables sans secrets | ✅ | `workflows/`, contrôle des secrets fait |
| Visuels issus des rendus existants | ✅ | rendus lus à un commit fixé, aucune génération |
| Exemples approuvé, rejeté, erreur, à revoir | ✅ | `examples/` |
| Tests adaptés | ✅ | 57/57 hors ligne, 23/23 de bout en bout |
| Documentation | ✅ | README, brief, architecture, vérifications, coûts, crédits |
