# Relevé des coûts

Plafond global (5 projets) : 200 €. Budget consommé par ce projet : **0 €**.

## Coûts engagés
| Date | Service | Type | Montant | Justificatif |
|---|---|---|---|---|
| — | aucun | — | 0 € | n8n auto-hébergé sur un serveur existant, mode mock |

## Coûts de fonctionnement prévisibles
| Poste | Type | Montant estimé | Hypothèse / source |
|---|---|---|---|
| Hébergement n8n | mensuel | 0 € supplémentaire | serveur personnel déjà en service (électricité non comptée) |
| Accès réseau / HTTPS | — | 0 € | Tailscale + `tailscale serve`, pas de domaine |
| IA, mode mock | — | 0 € | aucune API appelée |
| IA, mode live (`gpt-4o-mini`) | à l'usage | ≈ 0,0005 $ par appel, < 0,02 $/mois | 0,15 $ / 1 M tokens en entrée, 0,60 $ / 1 M en sortie (tarif standard OpenAI consulté le 2026-10-16) ; ≈ 1 000 tokens en entrée et 600 en sortie par appel ; 5 à 10 appels par semaine avec les nouveaux essais |

Les tarifs OpenAI peuvent changer, et l'API est facturée à l'usage sur un compte prépayé ou avec carte. Une limite de dépense mensuelle est recommandée dans la console OpenAI.

## Options non retenues (pour mémoire)
| Option | Coût | Raison |
|---|---|---|
| n8n Cloud Starter | 20 €/mois facturé à l'année (240 €/an) | dépasse le budget global |
| Oracle Cloud Always Free | 0 € (carte de vérification) | serveur personnel déjà disponible |
| Domaine | ≈ 10 €/an (non vérifié) | inutile en réseau privé |
