# Crédits, origine et licences

Légende origine : **Humain** (réalisé par moi) · **IA** (généré, outil précisé) · **Tiers** (ressource externe).

| Élément | Origine | Outil / source | Licence | Usage commercial | Attribution requise | Lien |
|---|---|---|---|---|---|---|
| Conception, brief, choix techniques | Humain + IA | Claude Code (assistant) | — | — | non | — |
| Workflows n8n (JSON), scripts Python | IA, sous direction humaine | Claude Code | même licence que ce dépôt | — | non | [workflows/](../workflows/) |
| Textes des réponses simulées (mock), fiche produit, listes de contrôle | IA, sous direction humaine, à partir des faits des dépôts TENSIL | Claude Code | même licence que ce dépôt | — | non | nœuds `Réponse simulée (mock)`, `Préparer le prompt`, `Valider la réponse` |
| Gabarit visuel SVG (mise en page) | IA, sous direction humaine | Claude Code | même licence que ce dépôt | — | non | nœud `Construire les fichiers` |
| Couleurs du gabarit (papier, encre, signal) | projet website-redesign | jetons CSS de `src/styles/global.css` | œuvre du portfolio | oui | non | [website-redesign](https://github.com/elie-gordo/website-redesign) |
| Rendus intégrés aux visuels (`renders/web/01_hero`, `03_detail`, `wire_hero`, `colorways_test`, `04_lit`) | projet blender-studio-object (images de synthèse, Blender 5.2.2) | lus par l'API GitHub au commit `ec74096` | œuvre du portfolio | oui | non | [blender-studio-object](https://github.com/elie-gordo/blender-studio-object/tree/ec74096adb0c2fea723eedd12b1ea9f6c1a26699/renders/web) |
| Marque et produit « TENSIL » | fictifs (projet blender-studio-object) | — | — | aucune vente | — | — |
| API GitHub (lecture des rendus) | Tiers | GitHub | conditions d'utilisation GitHub ; accès anonyme limité à 60 requêtes/heure | — | non | https://docs.github.com/en/rest/repos/contents |
| n8n | Tiers | n8n GmbH | Sustainable Use License (source disponible, **pas open source**) ; fichiers `.ee.` sous licence Enterprise | usage interne, personnel ou non commercial ; pas de revente de n8n comme service | conserver les mentions de licence | https://github.com/n8n-io/n8n/blob/master/LICENSE.md |
| API OpenAI (mode live, optionnel) | Tiers | OpenAI | conditions d'utilisation OpenAI | oui, selon les conditions | non | https://openai.com/policies/ |
| Tailscale (accès privé de test) | Tiers | Tailscale Inc. | conditions du service | — | non | https://tailscale.com/terms |
| Polices des visuels | système | Archivo / Azeret Mono / Inter si installées, sinon Arial Narrow, Consolas, Arial ; appelées par nom, non embarquées | dépend du système qui affiche le SVG | — | — | — |

Les visuels sont des SVG qui intègrent le rendu WebP (base64) mais pas les polices. Le rendu du texte peut varier selon la machine.
