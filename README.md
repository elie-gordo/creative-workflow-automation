# Projet 4 — Workflow de création automatisé

> Statut : **brief en validation** — aucun workflow construit.

## Concept
Pipeline éditorial hebdomadaire orchestré par **n8n** pour une marque **fictive** (Café Lumen) : une idée saisie le lundi devient chaque jour un post LinkedIn et un post Instagram (avec visuel SVG), validés par un humain avant d'être déposés dans une boîte d'envoi **simulée**. Aucune publication réelle. Détails : [docs/BRIEF.md](docs/BRIEF.md).

## Décisions
- [x] Concept : pipeline éditorial LinkedIn + Instagram, 5 angles, validation humaine
- [ ] Périmètre et livrables (brief à valider)
- [ ] Hébergement, fournisseur IA, licences et quotas vérifiés
- [ ] Budget alloué (sur plafond global 200 €)

## Structure
| Dossier | Contenu |
|---|---|
| `workflows/` | exports n8n (sans identifiants ni secrets) |
| `fixtures/` | données fictives et réponses IA simulées |
| `output/` | sorties générées (non versionnées) |
| `docs/` | brief, coûts, crédits/licences, contenu portfolio |

## Documentation
- [Brief](docs/BRIEF.md)
- [Coûts](docs/COSTS.md)
- [Crédits & licences](docs/CREDITS.md)
- [Intégration portfolio](docs/PORTFOLIO.md)
