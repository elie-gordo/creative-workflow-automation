# Architecture et faisabilité gratuite (étape 3)

> Statut : **proposition — en attente de validation**. Rien n'est déployé, aucun compte créé.
> Vérifications faites le 2026-10-15 sur les sources officielles listées en bas. Les offres gratuites peuvent changer sans préavis.
> Légende : ✅ vérifié (source officielle) · ⚠️ vérifié mais ambigu / contradictoire · ❓ non vérifié

## 1. Constat clé

La démo du portfolio **n'a pas besoin d'un serveur allumé 24 h/24** pour être convaincante :
- le workflow est livré en **export JSON** importable dans n'importe quel n8n ;
- le déclencheur quotidien est démontrable avec un **déclenchement manuel à date forcée** ;
- les preuves (captures, sorties, éventuellement vidéo) sont dans le dépôt.

L'hébergement cloud permanent est donc un **plus**, pas une condition de réussite. Cela réduit fortement le risque lié aux offres gratuites.

## 2. Hébergement de n8n — comparaison

| Critère | Oracle Always Free (A1 Arm) | Google Cloud Free Tier (e2-micro) | n8n Cloud |
|---|---|---|---|
| Ressources | ✅ 2 OCPU, 12 Go RAM (total), 200 Go disque | ✅ 1 e2-micro (❓ RAM exacte non lue), 30 Go disque | géré |
| Durée | ✅ « Always Free », sans durée annoncée — pas une garantie à vie | ✅ Free Tier sans durée annoncée | ✅ essai : 1 000 exécutions, durée non indiquée |
| Carte bancaire | ✅ demandée pour la plupart des comptes, autorisation de 1 USD, pas de débit sans passage en payant | ✅ compte de facturation obligatoire | ✅ pas de carte pour l'essai |
| Disponibilité | ⚠️ erreurs « out of host capacity » possibles à la création | ✅ régions US uniquement | ✅ |
| Récupération pour inactivité | ⚠️ instance **récupérable si inactive 7 jours** : CPU p95 < 20 %, réseau < 20 % **et** mémoire < 20 % (A1). Un n8n peu sollicité peut entrer dans ces seuils. Compte inactif 30 jours : suspension possible | ❓ | — |
| Trafic sortant | ✅ 10 To/mois | ✅ 1 Go/mois (suffisant pour du texte) | — |
| Sauvegardes | ✅ 5 sauvegardes de volume gratuites | ❓ | gérées |
| HTTPS / webhooks | à configurer : reverse proxy + domaine, ou tunnel | idem | ✅ inclus |
| Modules npm dans le nœud Code | ✅ possible (auto-hébergé) | ✅ possible | ✅ non autorisé — sans impact ici (SVG pur) |
| Coût pérenne | 0 € tant que l'offre existe | 0 € tant que l'offre existe | ✅ Starter **20 €/mois facturé à l'année = 240 €/an** → dépasse le budget global |

**Recommandation 💡** : **Oracle A1** comme cible, à condition que tu acceptes la vérification par carte. Contre la récupération pour inactivité : surveiller les métriques après déploiement ; option possible : passer le compte en « Pay As You Go » (✅ les ressources Always Free restent gratuites ; ❓ effet exact sur la règle d'inactivité non confirmé). Google Cloud = solution de repli. n8n Cloud = uniquement pour tourner une vidéo de démo pendant l'essai, pas pour l'hébergement durable.

### HTTPS et accès public (nécessaire pour les formulaires n8n)

| Option | Domaine | Coût | Remarque |
|---|---|---|---|
| Reverse proxy (Caddy ou Traefik) + certificat Let's Encrypt | oui, pointé sur l'IP de la VM | domaine payant ❓ (≈ 10 €/an, à vérifier) ou sous-domaine gratuit ❓ | ports 80/443 à ouvrir dans le pare-feu Oracle (liste de sécurité + pare-feu de la VM) |
| Cloudflare Tunnel nommé | ✅ domaine géré chez Cloudflare requis | ✅ disponible sur tous les plans | aucun port entrant à ouvrir |
| Cloudflare Quick Tunnel | ✅ aucun compte ni domaine | 0 € | ✅ URL aléatoire et temporaire — dépannage seulement |

Opérations manuelles nécessaires (de ta part) : création du compte cloud, vérification carte/téléphone, éventuel domaine.

## 3. n8n — points vérifiés impactant la conception

- ✅ **Licence** : Sustainable Use License, **source disponible, pas open source**. Autorise l'usage « pour vos propres besoins internes » ou « non commercial ou personnel ». Redistribution permise seulement gratuitement et à des fins non commerciales. Les fichiers `.ee.` (fonctions Enterprise) nécessitent une licence Enterprise.
  - Démo portfolio auto-hébergée, données fictives : usage personnel/non commercial → **compatible**.
  - Vendre l'hébergement de n8n à des clients : **non couvert** par cette licence.
  - ❓ Le cas « je construis des workflows pour un client qui héberge son propre n8n » n'est pas tranché par le texte lu ; à vérifier avant toute mission réelle.
- ✅ **n8n v2** : les nœuds de lecture/écriture de fichiers n'accèdent par défaut qu'à `~/.n8n-files` (`N8N_RESTRICT_FILE_ACCESS_TO`) ; le nœud Execute Command est désactivé par défaut. → Sorties écrites sous `~/.n8n-files/`, aucune commande système utilisée.
- ✅ **Data tables** : stockage interne, limite par défaut 200 Mio (⚠️ ancienne doc : 50 Mo). Largement suffisant pour plan + historique. Le nœud Code ne lit pas une Data table directement → passer par le nœud Data Table.
- ✅ **Clé de chiffrement** (`N8N_ENCRYPTION_KEY`) : chiffre les credentials en base ; à sauvegarder hors du dépôt.
- ✅ **Mémoire** : 320 Mo – 2 Go selon les workflows.
- ⚠️ URL publique : `N8N_WEBHOOK_URL` à partir de n8n 2.30.0, `WEBHOOK_URL` avant.

## 4. Étape IA — comparaison

| Option | Coût | Limites | Données | Compatibilité |
|---|---|---|---|---|
| **Mock** (réponses fixes dans `fixtures/`) | 0 € | aucune | aucune donnée envoyée | — |
| Google Gemini (offre gratuite) | ✅ gratuit sur les modèles Flash / Flash-Lite | ⚠️ quotas visibles seulement dans AI Studio, « non garantis » | ⚠️ **en gratuit, le contenu sert à améliorer les produits Google** | ✅ point d'accès compatible OpenAI, sortie JSON structurée |
| Groq (offre gratuite) | ✅ gratuit | ⚠️ ex. `openai/gpt-oss-20b` : 30 req/min, 1 000 req/jour, 200 k tokens/jour (plan non explicitement indiqué dans le tableau) | ✅ pas de conservation des requêtes par défaut (journaux d'abus ≤ 30 jours) | ✅ compatible OpenAI (`https://api.groq.com/openai/v1`) |
| Mistral (mode gratuit) | ✅ gratuit, sans carte | ❓ chiffres visibles seulement en console | ⚠️ « pas d'entraînement sur les données API » — application au gratuit non confirmée | ❓ |

Besoin réel : 1 appel par jour (+1 en cas de nouvel essai), quelques centaines de tokens → **toutes les offres gratuites suffisent largement**.

**Recommandation 💡** : **mock par défaut** + **Groq** en mode live (gratuit, compatible OpenAI, pas de conservation par défaut). Gemini en alternative. Appel via un **nœud HTTP Request** au format OpenAI : changer de fournisseur = changer `LLM_BASE_URL` et `LLM_MODEL`. Clé stockée dans une credential n8n, jamais dans le dépôt.

## 5. Contraintes des plateformes (pour la validation par code)

| Règle | Valeur | Source |
|---|---|---|
| Post LinkedIn | ✅ 3 000 caractères max | aide LinkedIn |
| Légende Instagram | ✅ 2 200 caractères max | doc Graph API |
| Hashtags Instagram | ✅ 30 max | aide Instagram + Graph API |
| Format d'image Instagram | ✅ ratio entre 4:5 et 1,91:1, largeur 1080 px, hauteur jusqu'à 1350 px | aide Instagram |

→ Le visuel **1080 × 1350 (4:5)** prévu au brief est conforme. Les limites internes du workflow seront plus strictes (posts courts) ; ces maxima servent de garde-fou.

## 6. Architecture proposée

```
                 ┌──────────────── VM Oracle A1 (Docker Compose) ────────────────┐
 Navigateur ─HTTPS─► Reverse proxy ──► n8n ──► Data tables (plan, historique)    │
 (formulaires)   │                      ├──► ~/.n8n-files/output/… (posts, SVG)  │
                 │                      └──► HTTP Request ─► LLM (Groq) [live]   │
                 │                                 ou fixtures/ [mock]           │
                 └───────────────────────────────────────────────────────────────┘
```

Aucun déploiement sans ton accord.

## 7. Coûts

| Poste | Option gratuite | Type | Solution pérenne payante (estimation) |
|---|---|---|---|
| Hébergement n8n | Oracle Always Free : 0 € | mensuel | ❓ petite VM payante, quelques €/mois — à chiffrer si besoin ; n8n Cloud Starter 240 €/an (✅) |
| Domaine | Quick Tunnel / sous-domaine gratuit ❓ | annuel | ❓ ≈ 10 €/an selon l'extension, à vérifier |
| IA | mock ou offre gratuite : 0 € | à l'usage | ❓ quelques centimes/mois au volume prévu, à chiffrer si passage en payant |
| Certificat HTTPS | Let's Encrypt / Cloudflare : 0 € | — | — |
| **Total visé** | **0 €** | | |

Offres soumises à conditions : crédit d'essai Oracle (300 USD, 30 jours — non utilisé ici), essai n8n Cloud (1 000 exécutions), quotas gratuits IA révisables à tout moment.

## Sources officielles consultées

- n8n — licence : https://github.com/n8n-io/n8n/blob/master/LICENSE.md
- n8n — tarifs : https://n8n.io/pricing/
- n8n — changements v2.0 : https://docs.n8n.io/2-0-breaking-changes/
- n8n — nœud Read/Write Files : https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.readwritefile
- n8n — modules dans le nœud Code : https://docs.n8n.io/hosting/configuration/configuration-examples/modules-in-code-node/
- n8n — Data tables : https://docs.n8n.io/data/data-tables/
- n8n — Docker Compose : https://docs.n8n.io/hosting/installation/server-setups/docker-compose/
- Oracle — ressources Always Free : https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
- Oracle — FAQ Free Tier : https://www.oracle.com/cloud/free/faq/
- Oracle — inscription : https://docs.oracle.com/en-us/iaas/Content/GSG/Tasks/signingup_topic-Sign_Up_for_Free_Oracle_Cloud_Promotion.htm
- Google Cloud — Free Tier : https://docs.cloud.google.com/free/docs/free-cloud-features
- Gemini API — tarifs : https://ai.google.dev/gemini-api/docs/pricing
- Gemini API — quotas : https://ai.google.dev/gemini-api/docs/rate-limits
- Gemini API — compatibilité OpenAI : https://ai.google.dev/gemini-api/docs/openai
- Groq — quotas : https://console.groq.com/docs/rate-limits
- Groq — compatibilité OpenAI : https://console.groq.com/docs/openai
- Groq — données : https://console.groq.com/docs/your-data
- Mistral — limites : https://docs.mistral.ai/admin/user-management-finops/tier
- Mistral — inférence : https://mistral.ai/cloud/inference/
- Cloudflare Tunnel : https://developers.cloudflare.com/tunnel/
- Cloudflare Quick Tunnels : https://try.cloudflare.com/
- LinkedIn — publier : https://www.linkedin.com/help/linkedin/answer/a528176
- Instagram — résolution d'image : https://help.instagram.com/1631821640426723/
- Instagram Graph API — IG User Media : https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media
