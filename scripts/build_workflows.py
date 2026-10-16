"""Generate the TENSIL workflows (A plan, B produce, E errors, T inspect) and deploy them via the n8n public API.

Usage (variables from .env, see .env.example):
  python scripts/build_workflows.py                     # writes JSON to scripts/out/
  python scripts/build_workflows.py --deploy            # creates/updates the data table + workflows, activates A, B, T
  python scripts/build_workflows.py --deploy --export   # same, then writes the cleaned exports to workflows/
"""
import json, os, sys, uuid, urllib.request, urllib.error

BASE_URL = os.environ.get("N8N_BASE_URL", "").rstrip("/")  # e.g. https://my-n8n.example.ts.net
URL = BASE_URL + "/api/v1"
KEY = os.environ.get("N8N_API_KEY", "")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "out")
STATE = os.path.join(HERE, ".n8n-state.json")
BASE_PATH = "/home/node/.n8n-files/tensil"
TABLE = "tensil_slots"
TABLE_PLACEHOLDER = "REPLACE_WITH_tensil_slots_TABLE_ID"
PREFIX = "TENSIL —"
# Renders come from the public Blender repository, pinned to a commit so the visuals never change silently.
ASSET_REPO = "elie-gordo/blender-studio-object"
ASSET_REF = "ec74096adb0c2fea723eedd12b1ea9f6c1a26699"
COLUMNS = [
    ("week_id", "string"), ("date", "string"), ("day_index", "number"), ("angle", "string"),
    ("theme", "string"), ("key_message", "string"), ("product", "string"), ("tone", "string"),
    ("cta", "string"), ("status", "string"), ("hook", "string"), ("linkedin_text", "string"),
    ("instagram_caption", "string"), ("hashtags", "string"), ("visual_title", "string"),
    ("visual_subtitle", "string"), ("review_url", "string"), ("reason", "string"),
    ("mode", "string"), ("updated_at", "string"),
]
EXPORT_FILES = {"A": "A_planifier_la_semaine.json", "B": "B_produire_le_jour.json",
                "E": "E_erreurs.json", "T": "T_inspecter_les_sorties.json"}
EXPORT_NOTE = ("Demo portfolio TENSIL (fictive brand, nothing is sold or published). No credentials included. "
               "Set the data table ID and the error workflow after import.")

# ---------------------------------------------------------------- API helpers
def api(method, path, body=None):
    req = urllib.request.Request(URL + path, method=method,
                                 headers={"X-N8N-API-KEY": KEY, "Content-Type": "application/json"},
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {path} -> {e.code}: {e.read().decode()[:800]}")

def load_state():
    return json.load(open(STATE)) if os.path.exists(STATE) else {}

def save_state(s):
    json.dump(s, open(STATE, "w"), indent=2)

# ---------------------------------------------------------------- node helpers
def node(name, ntype, version, params, pos, **extra):
    n = {"parameters": params, "name": name, "type": ntype, "typeVersion": version,
         "position": pos, "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "tensil-" + name))}
    n.update(extra)
    return n

def code(name, js, pos, **extra):
    return node(name, "n8n-nodes-base.code", 2, {"jsCode": js.strip()}, pos, **extra)

def cond_bool(expr):
    return {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                           "conditions": [{"id": str(uuid.uuid5(uuid.NAMESPACE_DNS, expr)), "leftValue": expr, "rightValue": "",
                                           "operator": {"type": "boolean", "operation": "true", "singleValue": True}}],
                           "combinator": "and"}, "options": {}}

def dt_filters(*conds):
    return {"conditions": [{"keyName": k, "condition": "eq", "keyValue": v} for k, v in conds]}

def dt_schema(names):
    return [{"id": n, "displayName": n, "type": dict(COLUMNS)[n], "display": True,
             "canBeUsedToMatch": True, "required": False, "defaultMatch": False, "removed": False} for n in names]

def dt_get(name, table_id, pos, filters=None, return_all=True, limit=1):
    p = {"resource": "row", "operation": "get", "dataTableId": {"mode": "id", "value": table_id},
         "matchType": "allConditions", "filters": filters or {"conditions": []}, "returnAll": return_all}
    if not return_all:
        p["limit"] = limit
    return node(name, "n8n-nodes-base.dataTable", 1.1, p, pos, alwaysOutputData=True)

def dt_write(name, op, table_id, values, pos, filters=None, **extra):
    p = {"resource": "row", "operation": op, "dataTableId": {"mode": "id", "value": table_id},
         "columns": {"mappingMode": "defineBelow", "value": values, "matchingColumns": [],
                     "schema": dt_schema(list(values.keys())), "attemptToConvertTypes": False,
                     "convertFieldsToString": False}, "options": {}}
    if filters:
        p["matchType"] = "allConditions"
        p["filters"] = filters
    return node(name, "n8n-nodes-base.dataTable", 1.1, p, pos, **extra)

def write_file(name, pos, **extra):
    return node(name, "n8n-nodes-base.readWriteFile", 1,
                {"operation": "write", "fileName": "={{ $json.path }}", "dataPropertyName": "data", "options": {}},
                pos, **extra)

def connect(conns, src, dst, out=0, inp=0):
    c = conns.setdefault(src, {"main": []})["main"]
    while len(c) <= out:
        c.append([])
    c[out].append({"node": dst, "type": "main", "index": inp})

# ---------------------------------------------------------------- shared JS
JS_COMMON = r"""
const ANGLES = ['devoilement', 'anatomie', 'coulisses', 'coloris', 'boutique'];
const ANGLE_LABELS = { devoilement: 'Dévoilement', anatomie: 'Anatomie', coulisses: 'Coulisses', coloris: 'Coloris', boutique: 'La boutique' };
const DAYS = ['', 'lun', 'mar', 'mer', 'jeu', 'ven'];
"""

# Product facts confirmed by the blender-studio-object and website-redesign repositories. Nothing else may be claimed.
JS_FACTS = r"""
const PRODUCT_FACTS = [
  "TENSIL est une marque fictive, créée pour un projet de portfolio. La lampe n'est pas commercialisée.",
  'Lampe de bureau articulée : bras en deux segments de 30 cm, soit 60 cm de portée.',
  'Ressorts équilibreurs : 2 ressorts par segment compensent le poids du bras, sans molette à serrer.',
  'Le principe des ressorts équilibreurs est connu depuis les années 1930 ; TENSIL le réinterprète avec une silhouette propre.',
  'Base en disque lestée de 22 cm de diamètre ; hauteur de 43 cm en position de travail.',
  'Abat-jour conique de 15 cm de diamètre, avec réflecteur interne.',
  'Matériaux représentés : acier laqué verni (bras, base, abat-jour), laiton brossé (rotules), acier poli (ressorts), câble en caoutchouc.',
  '4 coloris de laque : Graphite (presque noir), Sauge (vert gris doux), Oxyde (rouge brique), Crème (blanc cassé).',
  'Toutes les images sont des images de synthèse : modèle 3D construit par scripts Python dans Blender 5.2, sans modélisation manuelle, rendu avec Cycles.',
  "Un film de 8 s montre la lampe qui se déplie puis s'allume.",
  'Une boutique de démonstration est en ligne : vue 3D à 360°, changement de coloris en direct, parcours de commande simulé, sans paiement ni vente.',
];

// Claims a fictive, unsold product cannot make. Checked on the brief (A) and on every AI output (B). Not exhaustive.
const CLAIMS = [
  ['prix', /€|\bprix\b|\beuros?\b|\btarif/],
  ['vente', /\ben vente\b|\bachetez\b|\bcommandez\b|\bprecommand|\ben stock\b|\bdisponibles?\b|\bpromo|\bsoldes?\b/],
  ['livraison', /\blivraison/],
  ['caractéristique non documentée', /\bled\b|\blumens?\b|\bkelvins?\b|\bwatts?\b|\bdimmable|\bvariateur|\bbatterie|\busb\b|\bsans fil\b|\bcapteur/],
  ['garantie', /\bgaranti|\brembours|\bcertifi|\bnormes?\b/],
  ['origine ou engagement non vérifié', /\bfait main\b|\ba la main\b|\bartisan|\bfabriquee? en\b|\bmade in\b|\becolog|\beco-?respons|\brecycl|\bdurable/],
  ['superlatif', /\bn°\s?1\b|\bnumero un\b|\bmeilleure?s?\b|\brevolutionnaire|\bincomparable|\bunique au monde/],
  ['confort visuel non vérifié', /\beblou|\bfatigue visuelle/],
];
const normText = (s) => String(s ?? '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
const findClaims = (text) => CLAIMS
  .map(([label, re]) => { const m = normText(text).match(re); return m ? `${label} (« ${m[0]} »)` : null; })
  .filter(Boolean);

// Every number written must come from the product facts (0 and 1 are always allowed). Decimals are one number (1,2 ≠ 1 and 2).
const numbersIn = (text) => (String(text ?? '').match(/\d+(?:[.,]\d+)?/g) || []).map((n) => n.replace(',', '.'));
const FACT_NUMBERS = new Set(['0', '1', ...numbersIn(PRODUCT_FACTS.join(' '))]);
const unverifiedNumbers = (text) => [...new Set(numbersIn(text).filter((n) => !FACT_NUMBERS.has(n)))];
"""

JS_FILES = r"""
const BRAND = { paper: '#efebe4', sunk: '#e6e1d8', ink: '#171614', soft: '#57534c', signal: '#a8432a', name: 'TENSIL' };
const DISPLAY = "'Archivo Narrow', Archivo, 'Arial Narrow', 'Helvetica Neue', Arial, sans-serif";
const MONO = "'Azeret Mono', Consolas, 'Courier New', monospace";
const DISCLAIMER = 'Démo portfolio · TENSIL est une marque fictive · contenu préparé pour validation humaine, jamais publié.';

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' }[c]));
}

function wrap(text, max) {
  const lines = [];
  let cur = '';
  for (const w of String(text ?? '').split(/\s+/).filter(Boolean)) {
    if ((cur + ' ' + w).trim().length > max && cur) { lines.push(cur); cur = w; }
    else cur = (cur + ' ' + w).trim();
  }
  if (cur) lines.push(cur);
  return lines;
}

// Same number of lines as wrap(), but with lengths evened out (no single word left on the last line).
function balance(text, max) {
  const n = wrap(text, max).length;
  for (let m = Math.ceil(String(text ?? '').length / n); m < max; m++) {
    const lines = wrap(text, m);
    if (lines.length === n) return lines;
  }
  return wrap(text, max);
}

// 1080x1350 (4:5): Blender render on top (16:9), text block below, in the TENSIL store art direction.
function renderSvg(slot, visual, image, assetName) {
  const W = 1080, H = 1350, IMG_H = 680, X = 96, BOTTOM = 1176;
  const big = slot.angle === 'anatomie';
  const size = big ? 132 : 84;
  const lh = Math.round(size * 1.04);
  const tLines = balance(visual.title, big ? 14 : 22).slice(0, big ? 2 : 3);
  const sLines = balance(visual.subtitle, 50).slice(0, 2);
  // Text block anchored to the bottom, above the footer rule.
  const sy = BOTTOM - (sLines.length - 1) * 50;
  const yLast = sLines.length ? sy - 72 : BOTTOM;
  const y0 = yLast - (tLines.length - 1) * lh;
  const labelY = y0 - Math.round(size * 0.85) - 56;
  const title = tLines.map((l, i) =>
    `<text x="${X}" y="${y0 + i * lh}" font-family="${DISPLAY}" font-stretch="condensed" font-size="${size}" font-weight="700" fill="${BRAND.ink}">${esc(l)}</text>`).join('\n');
  const sub = sLines.map((l, i) =>
    `<text x="${X}" y="${sy + i * 50}" font-family="${DISPLAY}" font-size="38" fill="${BRAND.soft}">${esc(l)}</text>`).join('\n');
  const picture = image
    ? `<image href="${image}" x="0" y="0" width="${W}" height="${IMG_H}" preserveAspectRatio="xMidYMid slice"/>`
    : `<rect width="${W}" height="${IMG_H}" fill="${BRAND.sunk}"/>
<text x="${W / 2}" y="${IMG_H / 2}" text-anchor="middle" font-family="${MONO}" font-size="28" fill="${BRAND.soft}">Rendu indisponible</text>`;
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
<rect width="${W}" height="${H}" fill="${BRAND.paper}"/>
${picture}
<text x="${W - X}" y="${IMG_H + 36}" text-anchor="end" font-family="${MONO}" font-size="20" fill="${BRAND.soft}">Image de synthèse · Blender · ${esc(assetName)}</text>
<line x1="${X}" y1="${labelY - 8}" x2="${X + 56}" y2="${labelY - 8}" stroke="${BRAND.ink}" stroke-width="2"/>
<text x="${X + 76}" y="${labelY}" font-family="${MONO}" font-size="26" fill="${BRAND.ink}"><tspan fill="${BRAND.signal}">0${slot.day_index}</tspan>  ${esc(ANGLE_LABELS[slot.angle] || '')}</text>
${title}
${sub}
<line x1="${X}" y1="1232" x2="${W - X}" y2="1232" stroke="${BRAND.ink}" stroke-opacity="0.32" stroke-width="2"/>
<text x="${X}" y="1292" font-family="'Inter', Arial, sans-serif" font-size="40" font-weight="600" letter-spacing="10" fill="${BRAND.ink}">${BRAND.name}</text>
<text x="${W - X}" y="1288" text-anchor="end" font-family="${MONO}" font-size="20" fill="${BRAND.soft}">Marque fictive · démo portfolio</text>
</svg>`;
}

function fileItem(path, content, mimeType, json = {}) {
  const fileName = path.split('/').pop();
  return { json: { ...json, path }, binary: { data: { data: Buffer.from(content, 'utf8').toString('base64'), mimeType, fileName } } };
}

function linkedinMd(s, p) {
  return `# LinkedIn — ${s.date} · ${ANGLE_LABELS[s.angle]} (TENSIL)\n\n${p.linkedin_text}\n\n---\n${DISCLAIMER}\n`;
}

function instagramMd(s, p) {
  return `# Instagram — ${s.date} · ${ANGLE_LABELS[s.angle]} (TENSIL)\n\n${p.instagram_caption}\n\n${(p.hashtags || []).join(' ')}\n\n---\n${DISCLAIMER}\n`;
}

function briefOf(s) {
  return { week_id: s.week_id, theme: s.theme, key_message: s.key_message, product: s.product || null, tone: s.tone, cta: s.cta || null };
}

// Flat layout: n8n's file node does not create folders, so week/day/angle go in the file name.
function slotPrefix(s) {
  return `${s.week_id}_${s.day_index}-${DAYS[s.day_index]}_${s.angle}`;
}
"""

# ---------------------------------------------------------------- Workflow A
JS_A_VALIDATE = JS_COMMON + JS_FACTS + r"""
// Normalise the form submission and validate it against the brief rules and the product facts.
const TONES = ['sobre', 'technique', 'chaleureux', 'direct'];
const f = $input.first().json;
const pick = (...keys) => {
  for (const k of keys) if (f[k] !== undefined && f[k] !== null) return String(f[k]).trim();
  return '';
};
const brief = {
  week_start: pick('Semaine (lundi)', 'week_start'),
  theme: pick('Thème de la semaine', 'theme'),
  key_message: pick('Message clé', 'key_message'),
  product: pick('Produit ou coloris mis en avant (optionnel)', 'product'),
  tone: pick('Ton', 'tone').toLowerCase(),
  cta: pick("Appel à l'action (optionnel)", 'cta'),
};

const errors = [];
const checkLength = (value, min, max, label, required) => {
  if (!value) { if (required) errors.push(`${label} : obligatoire`); return; }
  if (value.length < min || value.length > max) errors.push(`${label} : ${min} à ${max} caractères (actuel : ${value.length})`);
};

function isoWeek(d) {
  const t = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
  const day = t.getUTCDay() || 7;
  t.setUTCDate(t.getUTCDate() + 4 - day);
  const y0 = new Date(Date.UTC(t.getUTCFullYear(), 0, 1));
  const w = Math.ceil(((t - y0) / 86400000 + 1) / 7);
  return `${t.getUTCFullYear()}-W${String(w).padStart(2, '0')}`;
}

let weekId = '';
const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(brief.week_start);
if (!m) {
  errors.push('Semaine : date au format AAAA-MM-JJ obligatoire');
} else {
  const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  if (isNaN(d) || d.getUTCDay() !== 1) errors.push('Semaine : la date doit être un lundi');
  else { brief.week_start = d.toISOString().slice(0, 10); weekId = isoWeek(d); }
}
checkLength(brief.theme, 10, 120, 'Thème', true);
checkLength(brief.key_message, 10, 200, 'Message clé', true);
checkLength(brief.product, 0, 80, 'Produit', false);
checkLength(brief.cta, 0, 40, "Appel à l'action", false);
if (!TONES.includes(brief.tone)) errors.push(`Ton : valeur attendue parmi ${TONES.join(', ')}`);

const text = [brief.theme, brief.key_message, brief.product, brief.cta].join(' ');
for (const c of findClaims(text)) errors.push(`Promesse non vérifiable pour un produit fictif : ${c}`);
const nums = unverifiedNumbers(text);
if (nums.length) errors.push(`Chiffre absent de la fiche produit : ${nums.join(', ')}`);

return [{ json: { valid: errors.length === 0, errors, brief, week_id: weekId } }];
"""

JS_A_PLAN = JS_COMMON + r"""
// Refuse an already-planned week, otherwise build the 5 daily slots (one angle per day).
const v = $('Valider le brief').first().json;
const existing = $input.all().filter((i) => i.json && i.json.id);
const errors = [...v.errors];
if (v.valid && existing.length) errors.push(`Semaine ${v.week_id} déjà planifiée (${existing.length} créneaux)`);
if (errors.length) return [{ json: { ok: false, errors, message: errors.map((e) => '• ' + e).join('\n') } }];

const start = new Date(v.brief.week_start + 'T00:00:00Z');
const now = new Date().toISOString();
return ANGLES.map((angle, i) => {
  const d = new Date(start);
  d.setUTCDate(d.getUTCDate() + i);
  return { json: { ok: true, week_id: v.week_id, date: d.toISOString().slice(0, 10), day_index: i + 1, angle,
    ...v.brief, status: 'planned', updated_at: now } };
});
"""

def workflow_a(table_id):
    nodes, conns = [], {}
    fields = [
        {"fieldLabel": "Semaine (lundi)", "fieldType": "date", "requiredField": True},
        {"fieldLabel": "Thème de la semaine", "placeholder": "Semaine de présentation de la lampe TENSIL", "requiredField": True},
        {"fieldLabel": "Message clé", "fieldType": "textarea",
         "placeholder": "Une lampe de bureau articulée, équilibrée par 2 ressorts par segment", "requiredField": True},
        {"fieldLabel": "Produit ou coloris mis en avant (optionnel)", "placeholder": "TENSIL Graphite"},
        {"fieldLabel": "Ton", "fieldType": "dropdown", "requiredField": True,
         "fieldOptions": {"values": [{"option": t} for t in ["sobre", "technique", "chaleureux", "direct"]]}},
        {"fieldLabel": "Appel à l'action (optionnel)", "placeholder": "Voir la boutique de démonstration"},
    ]
    nodes.append(node("Formulaire : brief de la semaine", "n8n-nodes-base.formTrigger", 2.2, {
        "formTitle": "TENSIL — brief de campagne",
        "formDescription": ("Démo portfolio : TENSIL est une marque fictive, rien n'est vendu ni publié. "
                            "Un brief → 5 jours de posts LinkedIn + Instagram, chacun validé par un humain. "
                            "Prix, promesses de vente et chiffres absents de la fiche produit sont refusés."),
        "formFields": {"values": fields}, "responseMode": "lastNode", "options": {"path": "tensil-brief"}},
        [0, 300], webhookId=str(uuid.uuid5(uuid.NAMESPACE_DNS, "tensil-brief"))))
    nodes.append(code("Valider le brief", JS_A_VALIDATE, [220, 300]))
    nodes.append(dt_get("Semaine déjà planifiée ?", table_id, [440, 300],
                        filters=dt_filters(("week_id", "={{ $json.week_id || '__none__' }}"))))
    nodes.append(code("Construire le plan", JS_A_PLAN, [660, 300]))
    nodes.append(node("Plan valide ?", "n8n-nodes-base.if", 2.2, cond_bool("={{ $json.ok }}"), [880, 300]))
    cols = ["week_id", "date", "day_index", "angle", "theme", "key_message", "product", "tone", "cta", "status", "updated_at"]
    nodes.append(dt_write("Enregistrer les créneaux", "insert", table_id,
                          {c: "={{ $json.%s }}" % c for c in cols}, [1100, 200]))
    nodes.append(node("Page : plan créé", "n8n-nodes-base.form", 1, {
        "operation": "completion", "completionTitle": "Plan créé",
        "completionMessage": ("=5 créneaux planifiés pour la semaine {{ $('Construire le plan').first().json.week_id }} : "
                              "dévoilement, anatomie, coulisses, coloris, boutique. Chaque jour ouvré produit un post LinkedIn "
                              "et un post Instagram soumis à validation. Rien n'est publié."),
        "options": {}}, [1320, 200], executeOnce=True))
    nodes.append(node("Page : brief refusé", "n8n-nodes-base.form", 1, {
        "operation": "completion", "completionTitle": "Brief refusé",
        "completionMessage": "={{ $json.message }}", "options": {}}, [1100, 420]))
    connect(conns, "Formulaire : brief de la semaine", "Valider le brief")
    connect(conns, "Valider le brief", "Semaine déjà planifiée ?")
    connect(conns, "Semaine déjà planifiée ?", "Construire le plan")
    connect(conns, "Construire le plan", "Plan valide ?")
    connect(conns, "Plan valide ?", "Enregistrer les créneaux", 0)
    connect(conns, "Plan valide ?", "Page : brief refusé", 1)
    connect(conns, "Enregistrer les créneaux", "Page : plan créé")
    return {"name": f"{PREFIX} A · Planifier la semaine", "nodes": nodes, "connections": conns}

# ---------------------------------------------------------------- Workflow B
JS_B_CONTEXT = r"""
// Configuration (no secrets here) + test overrides from the webhook body.
const CONFIG = {
  mode: 'mock',              // 'mock' (default, free) or 'live' (OpenAI, needs the credential)
  llm_model: 'gpt-4o-mini', // live mode only
  base_path: '__BASE_PATH__',
  max_attempts: 2,
  similarity_threshold: 0.6,
  prompt_version: 'tensil-v1',
};
const MOCK_CASES = ['valid', 'invalid_once', 'invalid_json', 'repeat', 'claim'];
const input = $input.first().json;
const body = input.body || {};
const date = /^\d{4}-\d{2}-\d{2}$/.test(body.date || '') ? body.date : $now.toISODate();
const mode = ['mock', 'live'].includes(body.mode) ? body.mode : CONFIG.mode;
const mock_case = MOCK_CASES.includes(body.mock_case) ? body.mock_case : 'valid';
return [{ json: { config: CONFIG, date, mode, mock_case, trigger: input.body ? 'webhook' : 'schedule' } }];
""".replace("__BASE_PATH__", BASE_PATH)

JS_B_PROMPT = JS_COMMON + JS_FACTS + r"""
// Build the prompt for the day's slot: product facts, angle, brief, hooks already used (anti-repetition).
const ctx = $('Contexte').first().json;
const slot = $('Créneau du jour').first().json;
const history_hooks = $input.all().map((i) => i.json)
  .filter((r) => r.id && r.id !== slot.id && r.hook && ['to_review', 'needs_review', 'approved'].includes(r.status))
  .map((r) => r.hook).slice(-30);

// One existing Blender render per angle (blender-studio-object, renders/web, 1600x900 WebP).
const ASSETS = {
  devoilement: 'renders/web/01_hero.webp',
  anatomie: 'renders/web/03_detail.webp',
  coulisses: 'renders/web/wire_hero.webp',
  coloris: 'renders/web/colorways_test.webp',
  boutique: 'renders/web/04_lit.webp',
};
const asset = { repo: '__ASSET_REPO__', ref: '__ASSET_REF__', path: ASSETS[slot.angle] };

const ANGLE_GUIDE = {
  devoilement: 'Présenter TENSIL dans son ensemble et le principe des ressorts équilibreurs. visual.title = une phrase courte qui décrit la lampe.',
  anatomie: "Mettre en avant UN chiffre de la fiche produit et le détail qu'il décrit (ressorts, rotules, base, abat-jour). visual.title = ce chiffre avec son unité ou son objet, 14 caractères maximum (ex. « 2 ressorts », « 22 cm »).",
  coulisses: "Raconter comment la lampe a été construite en 3D : scripts Python dans Blender, maquette grise, maillage, matériaux, rendu. Dire clairement qu'il s'agit d'images de synthèse.",
  coloris: 'Présenter les 4 coloris de laque et poser UNE question ouverte : lequel choisiriez-vous ?',
  boutique: "Présenter la boutique de démonstration (vue 3D à 360°, coloris en direct, commande simulée) en rappelant que rien n'est vendu. Finir par l'appel à l'action.",
};
const system_prompt = [
  "Tu es rédacteur social media pour TENSIL, une marque FICTIVE de lampe de bureau articulée créée pour un projet de portfolio.",
  "La lampe n'est pas commercialisée : aucun prix, aucune vente, aucune livraison, aucune disponibilité.",
  "N'utilise que les faits de la fiche produit. N'invente aucun chiffre, matériau, fonction, label ou promesse.",
  'Les images sont des images de synthèse : ne les présente jamais comme des photos.',
  'Style : phrases courtes, vocabulaire précis (mécanique, matière, lumière), pas de superlatifs. Maximum 2 emojis par texte.',
  'Réponds uniquement avec un objet JSON conforme au schéma fourni.',
  '', 'Fiche produit :', ...PRODUCT_FACTS.map((f) => '- ' + f),
].join('\n');
const user_prompt = [
  `Date : ${slot.date} — jour ${slot.day_index} sur 5 — angle : ${ANGLE_LABELS[slot.angle]}. ${ANGLE_GUIDE[slot.angle]}`,
  `Thème : ${slot.theme}`, `Message clé : ${slot.key_message}`,
  `Produit ou coloris : ${slot.product || '(aucun)'}`, `Ton : ${slot.tone}`, `Appel à l'action : ${slot.cta || '(aucun)'}`,
  'Contraintes : hook ≤ 90 caractères ; linkedin_text 300–1300 caractères, paragraphes courts ;',
  'instagram_caption 80–600 caractères sans hashtags ; hashtags : 3 à 8, format #MotSansEspace, dont #TENSIL ;',
  'visual.title ≤ 40 caractères ; visual.subtitle ≤ 80 caractères.',
  history_hooks.length ? `Accroches déjà utilisées, à ne pas reprendre : ${history_hooks.map((h) => `"${h}"`).join(' ; ')}` : '',
].filter(Boolean).join('\n');

return [{ json: { ...ctx, slot, asset, history_hooks, attempt: 1, attempts_log: [], retry_hint: '', system_prompt, user_prompt } }];
""".replace("__ASSET_REPO__", ASSET_REPO).replace("__ASSET_REF__", ASSET_REF)

JS_B_MOCK = r"""
// Simulated AI response (no API call), written from the product facts. mock_case drives the test scenarios.
const it = $input.first().json;
const s = it.slot;
const alt = it.attempt > 1 ? 1 : 0;
const cta = s.cta || 'Voir la boutique de démonstration';
const ANAT = {
  '2': ['2 ressorts', 'par segment, pour équilibrer le poids du bras'],
  '60': ['60 cm', 'de portée, en deux segments de 30 cm'],
  '22': ['22 cm', 'de diamètre pour la base lestée'],
  '43': ['43 cm', 'de hauteur en position de travail'],
  '15': ['15 cm', "de diamètre pour l'abat-jour conique"],
};
const anat = ANAT[(s.key_message.match(/\d+/g) || []).find((n) => ANAT[n]) || '2'];
const TEMPLATES = {
  devoilement: () => ({
    hooks: ['TENSIL : une lampe de bureau qui équilibre son propre bras', 'Voici TENSIL, la lampe articulée tenue par ses ressorts'],
    body: "TENSIL est une lampe de bureau articulée, imaginée pour un projet de portfolio. Son bras en deux segments est équilibré par des ressorts : pas de molette à serrer.\n\n" +
      `${s.key_message}.\n\nCette semaine, nous la présentons sous plusieurs angles : son anatomie, sa construction en 3D, ses coloris et sa boutique de démonstration.\n\n${cta}.`,
    caption: `Lampe de bureau articulée, bras en deux segments, ressorts équilibreurs. ${cta}.`,
    hashtags: ['#TENSIL', '#DesignProduit', '#LampeDeBureau', '#Rendu3D'],
    visual: { title: 'Une lampe qui équilibre son bras', subtitle: 'Lampe de bureau articulée à ressorts' },
  }),
  anatomie: () => ({
    hooks: [`${anat[0]} : ce qui tient le bras de TENSIL`, 'Anatomie de TENSIL, rotule après rotule'],
    body: 'Gros plan sur la mécanique de TENSIL.\n\n' +
      '• Ressorts équilibreurs : 2 par segment, ils compensent le poids du bras.\n• Rotules en laiton : elles articulent les segments.\n' +
      '• Base lestée : un disque de 22 cm de diamètre.\n• Abat-jour conique : 15 cm de diamètre, avec réflecteur interne.\n\n' +
      `${s.key_message}.\n\n${cta}.`,
    caption: `Ressorts équilibreurs, rotules en laiton, base lestée, abat-jour conique : la mécanique de TENSIL en un gros plan. ${cta}.`,
    hashtags: ['#TENSIL', '#Anatomie', '#DesignIndustriel', '#Rendu3D'],
    visual: { title: anat[0], subtitle: anat[1] },
  }),
  coulisses: () => ({
    hooks: ['Dans les coulisses : TENSIL est née de scripts Python', 'Pas un seul clic de modélisation : TENSIL vient du code'],
    body: "Chaque image de TENSIL est une image de synthèse. La lampe a été construite par des scripts Python exécutés dans Blender 5.2, puis rendue avec Cycles.\n\n" +
      "Les étapes : une maquette grise pour les volumes, le maillage détaillé avec les ressorts et les rotules, les matériaux, l'éclairage studio, puis les rendus finaux.\n\n" +
      `${s.key_message}.\n\n${cta}.`,
    caption: `Maquette grise, maillage, matériaux, lumière : TENSIL est une image de synthèse, construite étape par étape dans Blender. ${cta}.`,
    hashtags: ['#TENSIL', '#Blender', '#Coulisses', '#Modelisation3D'],
    visual: { title: 'Construite par le code', subtitle: 'Maillage du modèle 3D, scripts Python et Blender' },
  }),
  coloris: () => ({
    hooks: ['Graphite, Sauge, Oxyde ou Crème : laquelle pour votre bureau ?', 'Quatre laques pour une même lampe : votre choix ?'],
    body: 'TENSIL existe en 4 coloris de laque :\n• Graphite, presque noir ;\n• Sauge, un vert gris doux ;\n• Oxyde, un rouge brique ;\n• Crème, un blanc cassé.\n\n' +
      `Les rotules restent en laiton sur chaque coloris.\n\n${s.key_message}.\n\nDites-nous en commentaire quel coloris vous placeriez sur votre bureau.`,
    caption: '4 laques, les mêmes rotules en laiton. Graphite, Sauge, Oxyde ou Crème ? Répondez en commentaire.',
    hashtags: ['#TENSIL', '#Coloris', '#DesignProduit', '#VotreAvis'],
    visual: { title: 'Laquelle choisiriez-vous ?', subtitle: 'Graphite, Sauge, Oxyde, Crème' },
  }),
  boutique: () => ({
    hooks: ['La boutique de démonstration TENSIL est en ligne', 'TENSIL se manipule à 360° dans sa boutique de démo'],
    body: 'On peut y faire tourner la lampe en 3D à 360°, changer de coloris en direct et suivre un parcours de commande complet.\n\n' +
      "Ce parcours est simulé : TENSIL est une marque fictive, aucun paiement n'est demandé et aucune commande n'est réelle.\n\n" +
      `${s.key_message}.\n\n${cta}.`,
    caption: `Vue 3D à 360°, 4 coloris, commande simulée : rien n'est vendu, tout se manipule. ${cta}.`,
    hashtags: ['#TENSIL', '#Ecommerce', '#WebGL', '#Boutique3D'],
    visual: { title: 'À voir sous tous les angles', subtitle: 'Boutique de démonstration · vue 3D à 360°' },
  }),
};
const t = TEMPLATES[s.angle]();
const hook = it.mock_case === 'repeat' && it.history_hooks.length ? it.history_hooks[0] : t.hooks[alt];
const post = {
  hook,
  linkedin_text: `${hook}\n\n${t.body}`,
  instagram_caption: `${hook}\n\n${t.caption}`,
  hashtags: t.hashtags,
  visual: t.visual,
};
// 'claim': first answer promises a price and availability (forbidden for a fictive product), the retry is clean.
if (it.mock_case === 'claim' && it.attempt === 1) post.linkedin_text += '\n\nDisponible dès maintenant à 249 €.';

let raw;
if (it.mock_case === 'invalid_json' || (it.mock_case === 'invalid_once' && it.attempt === 1)) {
  raw = '{"hook": "Réponse tronquée par le fournisseur...';
} else {
  raw = JSON.stringify(post);
}
return [{ json: { ...it, raw_response: raw } }];
"""

JS_B_VALIDATE = JS_COMMON + JS_FACTS + r"""
// Validate the AI output: schema, lengths, platform limits, forbidden claims, unverified numbers, repetition.
// check = ok | retry | fail
const it = $input.first().json;
const cfg = it.config;
const errors = [];
let data = null;

if (it.mode === 'live') {
  if (it.error) errors.push('API : ' + String(it.error.message || JSON.stringify(it.error)).slice(0, 200));
  else {
    try { data = JSON.parse(it.choices?.[0]?.message?.content ?? ''); } catch (e) { errors.push('JSON invalide'); }
  }
} else {
  try { data = JSON.parse(it.raw_response); } catch (e) { errors.push('JSON invalide'); }
}

const str = (v, min, max, label) => {
  if (typeof v !== 'string') return errors.push(`${label} manquant`);
  if (v.length < min || v.length > max) errors.push(`${label} : ${v.length} caractères (attendu ${min}–${max})`);
};
if (data) {
  str(data.hook, 10, 90, 'hook');
  str(data.linkedin_text, 100, 1300, 'linkedin_text');           // LinkedIn max 3000
  str(data.instagram_caption, 50, 600, 'instagram_caption');     // Instagram max 2200
  str(data.visual?.title, 1, 40, 'visual.title');
  str(data.visual?.subtitle ?? '', 0, 80, 'visual.subtitle');
  const tags = data.hashtags;
  if (!Array.isArray(tags) || tags.length < 3 || tags.length > 8) errors.push('hashtags : 3 à 8 attendus'); // Instagram max 30
  else if (tags.some((t) => !/^#[\p{L}\p{N}_]+$/u.test(t))) errors.push('hashtags : format #MotSansEspace');
  if (it.slot.angle === 'anatomie' && typeof data.visual?.title === 'string' && (data.visual.title.length > 14 || !/\d/.test(data.visual.title)))
    errors.push('visual.title (anatomie) : un chiffre, 14 caractères maximum');
  if (!errors.length) {
    const all = [data.hook, data.linkedin_text, data.instagram_caption, data.hashtags.join(' '), data.visual.title, data.visual.subtitle].join('\n');
    for (const c of findClaims(all)) errors.push(`promesse interdite : ${c}`);
    const nums = unverifiedNumbers(all);
    if (nums.length) errors.push(`chiffre absent de la fiche produit : ${nums.join(', ')}`);
  }
}

const norm = (s) => normText(s).replace(/[^a-z0-9 ]/g, ' ').split(/\s+/).filter((w) => w.length > 2);
const jaccard = (a, b) => {
  const A = new Set(norm(a)), B = new Set(norm(b));
  if (!A.size || !B.size) return 0;
  const inter = [...A].filter((x) => B.has(x)).length;
  return inter / (A.size + B.size - inter);
};
let similar_hook = '';
if (!errors.length) {
  for (const h of it.history_hooks) {
    if (jaccard(data.hook, h) >= cfg.similarity_threshold) { similar_hook = h; break; }
  }
}

const canRetry = it.attempt < cfg.max_attempts;
let check = 'ok', retry_hint = '', needs_review = false;
if (errors.length) {
  check = canRetry ? 'retry' : 'fail';
  retry_hint = `Ta réponse précédente a été refusée (${errors.join(' ; ')}). Respecte strictement le schéma, les longueurs et la fiche produit.`;
} else if (similar_hook) {
  if (canRetry) { check = 'retry'; retry_hint = `L'accroche « ${similar_hook} » est déjà utilisée : propose une accroche nettement différente.`; }
  else needs_review = true;
}
const attempts_log = [...(it.attempts_log || []), { attempt: it.attempt, result: check, errors, similar_hook: similar_hook || null }];

return [{ json: {
  config: cfg, date: it.date, mode: it.mode, mock_case: it.mock_case, slot: it.slot, asset: it.asset,
  history_hooks: it.history_hooks, system_prompt: it.system_prompt, user_prompt: it.user_prompt,
  attempt: check === 'retry' ? it.attempt + 1 : it.attempt, attempts_log,
  check, errors, retry_hint, needs_review, similar_hook, post: errors.length ? null : data,
} }];
"""

JS_B_FILES = JS_COMMON + JS_FILES + r"""
// Write the day's deliverables + meta. Status to_review, or needs_review when something needs a closer look.
const it = $input.first().json;   // validated post merged with the GitHub contents API response for the render
const s = it.slot, p = it.post;
const dir = `${it.config.base_path}/output/${slotPrefix(s)}`;
const assetName = it.asset.path.split('/').pop();
const hasImage = it.encoding === 'base64' && typeof it.content === 'string' && it.content.length > 100;
const image = hasImage ? `data:image/webp;base64,${it.content.replace(/\s/g, '')}` : '';
const review_notes = [];
if (it.needs_review) review_notes.push(`accroche proche de : « ${it.similar_hook} »`);
if (!hasImage) review_notes.push(`rendu ${assetName} indisponible : visuel sans image`);
const status = review_notes.length ? 'needs_review' : 'to_review';
const svg = renderSvg(s, p.visual, image, assetName);
const review_url = $execution.resumeFormUrl;
const meta = {
  brand: 'TENSIL (marque fictive, démo portfolio)',
  brief: briefOf(s),
  slot: { date: s.date, day: DAYS[s.day_index], angle: s.angle, angle_label: ANGLE_LABELS[s.angle] },
  status, review_notes, mode: it.mode, prompt_version: it.config.prompt_version,
  attempts: it.attempt, checks: it.attempts_log,
  visual: {
    file: `${slotPrefix(s)}_instagram_1080x1350.svg`, title: p.visual.title, subtitle: p.visual.subtitle,
    render: { repo: it.asset.repo, ref: it.asset.ref, path: it.asset.path, embedded: hasImage,
      source: `https://github.com/${it.asset.repo}/blob/${it.asset.ref}/${it.asset.path}` },
  },
  review_url, published: false, execution_id: $execution.id, generated_at: new Date().toISOString(),
};
const shared = { slot_id: s.id, slot: s, post: p, status, reason: review_notes.join(' ; '), svg, review_url,
  mode: it.mode, review_notes, base_path: it.config.base_path };
return [
  fileItem(`${dir}_linkedin.md`, linkedinMd(s, p), 'text/markdown', shared),
  fileItem(`${dir}_instagram_caption.md`, instagramMd(s, p), 'text/markdown'),
  fileItem(`${dir}_instagram_1080x1350.svg`, svg, 'image/svg+xml'),
  fileItem(`${dir}_meta.json`, JSON.stringify(meta, null, 2), 'application/json'),
];
"""

JS_B_DECISION = JS_COMMON + JS_FILES + r"""
// Apply the human decision: approved -> outbox/, rejected -> rejected/ with the reason. Nothing is published.
const f = $('Construire les fichiers').first().json;
const answer = $input.first().json;
const s = f.slot, p = f.post;
const approved = String(answer['Décision'] || '').toLowerCase().startsWith('approuv');
const reason = String(answer['Motif (si rejet)'] || '').trim() || (approved ? '' : '(non précisé)');
const status = approved ? 'approved' : 'rejected';
const dir = `${f.base_path}/${approved ? 'outbox' : 'rejected'}/${slotPrefix(s)}`;
const decision = {
  brand: 'TENSIL (marque fictive, démo portfolio)', brief: briefOf(s), date: s.date, angle: s.angle,
  status, reason: reason || null, review_notes: f.review_notes, decided_at: new Date().toISOString(),
  execution_id: $execution.id, published: false,
  note: 'Publication simulée : aucun envoi vers LinkedIn ou Instagram.',
};
const items = [
  fileItem(`${dir}_linkedin.md`, linkedinMd(s, p), 'text/markdown', { slot_id: s.id, status, reason }),
  fileItem(`${dir}_instagram_caption.md`, instagramMd(s, p), 'text/markdown'),
  fileItem(`${dir}_decision.json`, JSON.stringify(decision, null, 2), 'application/json'),
];
if (approved) items.push(fileItem(`${dir}_instagram_1080x1350.svg`, f.svg, 'image/svg+xml'));
return items;
"""

JS_B_ERROR = JS_COMMON + JS_FILES + r"""
// Generation failed after retries: keep a trace in _errors/.
const it = $input.first().json;
const s = it.slot;
const err = { brand: 'TENSIL (marque fictive, démo portfolio)', brief: briefOf(s), date: s.date, angle: s.angle,
  mode: it.mode, attempts: it.attempt, errors: it.errors, checks: it.attempts_log, execution_id: $execution.id,
  at: new Date().toISOString() };
return [fileItem(`${it.config.base_path}/_errors/${s.week_id}_${s.day_index}-${DAYS[s.day_index]}_${$execution.id}.json`,
  JSON.stringify(err, null, 2), 'application/json', { slot_id: s.id, mode: it.mode, reason: it.errors.join(' ; ') })];
"""

OPENAI_BODY = r"""={{ JSON.stringify({
  model: $json.config.llm_model,
  temperature: 0.8,
  messages: [
    { role: 'system', content: $json.system_prompt },
    { role: 'user', content: $json.user_prompt + ($json.retry_hint ? '\n\n' + $json.retry_hint : '') }
  ],
  response_format: { type: 'json_schema', json_schema: { name: 'daily_posts', strict: true, schema: {
    type: 'object', additionalProperties: false,
    required: ['hook', 'linkedin_text', 'instagram_caption', 'hashtags', 'visual'],
    properties: {
      hook: { type: 'string' }, linkedin_text: { type: 'string' }, instagram_caption: { type: 'string' },
      hashtags: { type: 'array', items: { type: 'string' } },
      visual: { type: 'object', additionalProperties: false, required: ['title', 'subtitle'],
        properties: { title: { type: 'string' }, subtitle: { type: 'string' } } }
    } } } }
}) }}"""

def switch_rules(key, outputs):
    return {"rules": {"values": [{
        "conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                       "conditions": [{"id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "sw-" + o)), "leftValue": key, "rightValue": o,
                                       "operator": {"type": "string", "operation": "equals"}}],
                       "combinator": "and"},
        "renameOutput": True, "outputKey": o} for o in outputs]}, "options": {}}

def workflow_b(table_id):
    nodes, conns = [], {}
    fb = "$('Construire les fichiers').first().json"
    nodes.append(node("Chaque jour ouvré 8 h", "n8n-nodes-base.scheduleTrigger", 1.2,
                      {"rule": {"interval": [{"field": "cronExpression", "expression": "0 8 * * 1-5"}]}},
                      [0, 200], disabled=True))
    nodes.append(node("Webhook : test / date forcée", "n8n-nodes-base.webhook", 2,
                      {"httpMethod": "POST", "path": "tensil-produire", "responseMode": "onReceived", "options": {}},
                      [0, 400], webhookId=str(uuid.uuid5(uuid.NAMESPACE_DNS, "tensil-produire"))))
    nodes.append(code("Contexte", JS_B_CONTEXT, [220, 300]))
    nodes.append(dt_get("Créneau du jour", table_id, [440, 300], return_all=False,
                        filters=dt_filters(("date", "={{ $json.date }}"), ("status", "planned"))))
    nodes.append(node("Créneau trouvé ?", "n8n-nodes-base.if", 2.2, cond_bool("={{ !!$json.id }}"), [660, 300]))
    nodes.append(node("Rien à produire", "n8n-nodes-base.noOp", 1, {}, [880, 460]))
    nodes.append(dt_get("Historique des accroches", table_id, [880, 220]))
    nodes.append(code("Préparer le prompt", JS_B_PROMPT, [1100, 220]))
    nodes.append(node("Mode live ?", "n8n-nodes-base.if", 2.2, cond_bool("={{ $json.mode === 'live' }}"), [1320, 220]))
    nodes.append(node("OpenAI : générer", "n8n-nodes-base.httpRequest", 4.2, {
        "method": "POST", "url": "https://api.openai.com/v1/chat/completions",
        "authentication": "predefinedCredentialType", "nodeCredentialType": "openAiApi",
        "sendBody": True, "specifyBody": "json", "jsonBody": OPENAI_BODY,
        "options": {"timeout": 30000}}, [1540, 80], onError="continueRegularOutput"))
    nodes.append(node("Réunir contexte + réponse", "n8n-nodes-base.merge", 3,
                      {"mode": "combine", "combineBy": "combineByPosition", "options": {}}, [1760, 120]))
    nodes.append(code("Réponse simulée (mock)", JS_B_MOCK, [1540, 340]))
    nodes.append(code("Valider la réponse", JS_B_VALIDATE, [1980, 220]))
    nodes.append(node("Résultat", "n8n-nodes-base.switch", 3.2,
                      switch_rules("={{ $json.check }}", ["ok", "retry", "fail"]), [2200, 220]))
    nodes.append(node("Lire le rendu (GitHub)", "n8n-nodes-base.httpRequest", 4.2, {
        "method": "GET",
        "url": "=https://api.github.com/repos/{{ $json.asset.repo }}/contents/{{ $json.asset.path }}?ref={{ $json.asset.ref }}",
        "sendHeaders": True, "headerParameters": {"parameters": [
            {"name": "Accept", "value": "application/vnd.github+json"},
            {"name": "User-Agent", "value": "n8n-tensil-demo"}]},
        "options": {"timeout": 15000}}, [2420, 0], onError="continueRegularOutput"))
    nodes.append(node("Réunir texte + rendu", "n8n-nodes-base.merge", 3,
                      {"mode": "combine", "combineBy": "combineByPosition", "options": {}}, [2640, 100]))
    nodes.append(code("Construire les fichiers", JS_B_FILES, [2860, 100]))
    nodes.append(write_file("Écrire les fichiers", [3080, 100]))
    nodes.append(dt_write("Statut : à valider", "update", table_id, {
        "status": "={{ %s.status }}" % fb, "hook": "={{ %s.post.hook }}" % fb,
        "linkedin_text": "={{ %s.post.linkedin_text }}" % fb,
        "instagram_caption": "={{ %s.post.instagram_caption }}" % fb,
        "hashtags": "={{ %s.post.hashtags.join(' ') }}" % fb,
        "visual_title": "={{ %s.post.visual.title }}" % fb,
        "visual_subtitle": "={{ %s.post.visual.subtitle }}" % fb,
        "review_url": "={{ %s.review_url }}" % fb, "reason": "={{ %s.reason }}" % fb,
        "mode": "={{ %s.mode }}" % fb, "updated_at": "={{ $now.toISO() }}"},
        [3300, 100], filters=dt_filters(("id", "={{ %s.slot_id }}" % fb)), executeOnce=True))
    nodes.append(node("Validation humaine", "n8n-nodes-base.wait", 1.1, {
        "resume": "form",
        "formTitle": "=TENSIL — post du {{ %s.slot.date }}" % fb,
        "formDescription": ("=Angle : {{ F.slot.angle }}{{ F.review_notes.length ? ' — ⚠ à vérifier : ' + F.review_notes.join(' ; ') : '' }}"
                            "\n\nLINKEDIN\n{{ F.post.linkedin_text }}\n\nINSTAGRAM\n{{ F.post.instagram_caption }}\n{{ F.post.hashtags.join(' ') }}"
                            "\n\nVISUEL : {{ F.post.visual.title }} — fichier SVG dans output/ (workflow T pour le consulter)."
                            "\nTENSIL est une marque fictive : approuver range le post dans outbox/, rien n'est publié.").replace("F.", fb + "."),
        "formFields": {"values": [
            {"fieldLabel": "Décision", "fieldType": "dropdown", "requiredField": True,
             "fieldOptions": {"values": [{"option": "Approuver"}, {"option": "Rejeter"}]}},
            {"fieldLabel": "Motif (si rejet)", "fieldType": "textarea"}]},
        "options": {}}, [3520, 100], webhookId=str(uuid.uuid5(uuid.NAMESPACE_DNS, "tensil-review"))))
    nodes.append(code("Appliquer la décision", JS_B_DECISION, [3740, 100]))
    nodes.append(write_file("Écrire la décision", [3960, 100]))
    dec = "$('Appliquer la décision').first().json"
    nodes.append(dt_write("Statut final", "update", table_id, {
        "status": "={{ %s.status }}" % dec, "reason": "={{ %s.reason }}" % dec, "updated_at": "={{ $now.toISO() }}"},
        [4180, 100], filters=dt_filters(("id", "={{ %s.slot_id }}" % dec)), executeOnce=True))
    nodes.append(code("Préparer l'erreur", JS_B_ERROR, [2420, 420]))
    nodes.append(write_file("Écrire l'erreur", [2640, 420]))
    err = "$('Préparer l\\'erreur').first().json"
    nodes.append(dt_write("Statut : erreur", "update", table_id, {
        "status": "error", "reason": "={{ %s.reason }}" % err, "mode": "={{ %s.mode }}" % err,
        "updated_at": "={{ $now.toISO() }}"},
        [2860, 420], filters=dt_filters(("id", "={{ %s.slot_id }}" % err))))

    connect(conns, "Chaque jour ouvré 8 h", "Contexte")
    connect(conns, "Webhook : test / date forcée", "Contexte")
    connect(conns, "Contexte", "Créneau du jour")
    connect(conns, "Créneau du jour", "Créneau trouvé ?")
    connect(conns, "Créneau trouvé ?", "Historique des accroches", 0)
    connect(conns, "Créneau trouvé ?", "Rien à produire", 1)
    connect(conns, "Historique des accroches", "Préparer le prompt")
    connect(conns, "Préparer le prompt", "Mode live ?")
    connect(conns, "Mode live ?", "OpenAI : générer", 0)
    connect(conns, "Mode live ?", "Réunir contexte + réponse", 0, 0)
    connect(conns, "Mode live ?", "Réponse simulée (mock)", 1)
    connect(conns, "OpenAI : générer", "Réunir contexte + réponse", 0, 1)
    connect(conns, "Réunir contexte + réponse", "Valider la réponse")
    connect(conns, "Réponse simulée (mock)", "Valider la réponse")
    connect(conns, "Valider la réponse", "Résultat")
    connect(conns, "Résultat", "Lire le rendu (GitHub)", 0)
    connect(conns, "Résultat", "Réunir texte + rendu", 0, 0)
    connect(conns, "Lire le rendu (GitHub)", "Réunir texte + rendu", 0, 1)
    connect(conns, "Résultat", "Mode live ?", 1)
    connect(conns, "Résultat", "Préparer l'erreur", 2)
    connect(conns, "Réunir texte + rendu", "Construire les fichiers")
    connect(conns, "Construire les fichiers", "Écrire les fichiers")
    connect(conns, "Écrire les fichiers", "Statut : à valider")
    connect(conns, "Statut : à valider", "Validation humaine")
    connect(conns, "Validation humaine", "Appliquer la décision")
    connect(conns, "Appliquer la décision", "Écrire la décision")
    connect(conns, "Écrire la décision", "Statut final")
    connect(conns, "Préparer l'erreur", "Écrire l'erreur")
    connect(conns, "Écrire l'erreur", "Statut : erreur")
    return {"name": f"{PREFIX} B · Produire le jour", "nodes": nodes, "connections": conns}

# ---------------------------------------------------------------- Workflow E
JS_E = r"""
// Unhandled failure in a TENSIL workflow: write a trace (no notification is sent).
const e = $input.first().json;
const id = e.execution?.id || 'unknown';
const trace = {
  workflow: e.workflow?.name, execution_id: id, last_node: e.execution?.lastNodeExecuted,
  message: e.execution?.error?.message, at: new Date().toISOString(),
};
const path = `__BASE_PATH__/_errors/workflow_${id}.json`;
return [{ json: { path, ...trace }, binary: { data: {
  data: Buffer.from(JSON.stringify(trace, null, 2), 'utf8').toString('base64'),
  mimeType: 'application/json', fileName: path.split('/').pop() } } }];
""".replace("__BASE_PATH__", BASE_PATH)

def workflow_e():
    nodes, conns = [], {}
    nodes.append(node("Erreur dans un workflow TENSIL", "n8n-nodes-base.errorTrigger", 1, {}, [0, 300]))
    nodes.append(code("Préparer la trace", JS_E, [220, 300]))
    nodes.append(write_file("Écrire la trace", [440, 300]))
    connect(conns, "Erreur dans un workflow TENSIL", "Préparer la trace")
    connect(conns, "Préparer la trace", "Écrire la trace")
    return {"name": f"{PREFIX} E · Erreurs", "nodes": nodes, "connections": conns}

# ---------------------------------------------------------------- Workflow T (read-only inspector)
JS_T = r"""
// List generated files (read-only) so outputs can be checked without disk access.
const files = [];
for (let i = 0; i < $input.all().length; i++) {
  const item = $input.all()[i];
  const b = item.binary?.data;
  if (!b) continue;
  const buf = await this.helpers.getBinaryDataBuffer(i, 'data');
  const text = buf.toString('utf8');
  files.push({ path: `${b.directory || ''}/${b.fileName}`, bytes: buf.length,
    content: /svg|json|markdown|text/.test(b.mimeType || b.fileName) ? text : null });
}
files.sort((a, b) => a.path.localeCompare(b.path));
return [{ json: { count: files.length, files } }];
"""

def workflow_t():
    nodes, conns = [], {}
    nodes.append(node("Webhook : inspecter", "n8n-nodes-base.webhook", 2,
                      {"httpMethod": "GET", "path": "tensil-inspect", "responseMode": "lastNode", "options": {}},
                      [0, 300], webhookId=str(uuid.uuid5(uuid.NAMESPACE_DNS, "tensil-inspect"))))
    nodes.append(node("Lire les sorties", "n8n-nodes-base.readWriteFile", 1,
                      {"operation": "read", "fileSelector": BASE_PATH + "/**/*", "options": {}},
                      [220, 300], alwaysOutputData=True))
    nodes.append(code("Lister", JS_T, [440, 300]))
    connect(conns, "Webhook : inspecter", "Lire les sorties")
    connect(conns, "Lire les sorties", "Lister")
    return {"name": f"{PREFIX} T · Inspecter les sorties (lecture seule)", "nodes": nodes, "connections": conns}

def build_all(table_id):
    return {"E": workflow_e(), "A": workflow_a(table_id), "B": workflow_b(table_id), "T": workflow_t()}

# ---------------------------------------------------------------- deploy
def ensure_table(state):
    for t in api("GET", "/data-tables?limit=100").get("data", []):
        if t["name"] == TABLE:
            state["table_id"] = t["id"]
            return t["id"]
    t = api("POST", "/data-tables", {"name": TABLE, "columns": [{"name": n, "type": ty} for n, ty in COLUMNS]})
    state["table_id"] = t["id"]
    return t["id"]

def find_workflow(name):
    for w in api("GET", "/workflows?limit=250").get("data", []):
        if w["name"] == name:
            return w["id"]
    return None

def upsert_workflow(state, key, wf, settings):
    body = {"name": wf["name"], "nodes": wf["nodes"], "connections": wf["connections"], "settings": settings}
    wid = state.get(key) or find_workflow(wf["name"])
    if wid:
        api("PUT", f"/workflows/{wid}", body)
    else:
        wid = api("POST", "/workflows", body)["id"]
    state[key] = wid
    save_state(state)
    return wid

def export(state):
    """Write the deployed workflows to workflows/, without credentials or instance-specific IDs."""
    for k, fname in EXPORT_FILES.items():
        wf = api("GET", f"/workflows/{state['wf_' + k]}")
        for n in wf["nodes"]:
            n.pop("credentials", None)
        clean = {"name": wf["name"], "nodes": wf["nodes"], "connections": wf["connections"],
                 "settings": {"executionOrder": "v1"}, "meta": {"note": EXPORT_NOTE}}
        text = json.dumps(clean, ensure_ascii=False, indent=2).replace(state["table_id"], TABLE_PLACEHOLDER)
        with open(os.path.join(ROOT, "workflows", fname), "w", encoding="utf-8", newline="\n") as f:
            f.write(text + "\n")
    print("exported", list(EXPORT_FILES.values()))

def main():
    os.makedirs(OUT, exist_ok=True)
    deploy = "--deploy" in sys.argv
    if deploy and not (BASE_URL and KEY):
        raise SystemExit("N8N_BASE_URL and N8N_API_KEY are required for --deploy (see .env.example)")
    state = load_state()
    table_id = ensure_table(state) if deploy else TABLE_PLACEHOLDER
    wfs = build_all(table_id)
    for k, wf in wfs.items():
        json.dump(wf, open(os.path.join(OUT, f"{k}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    if not deploy:
        print("built", list(wfs))
        return
    save_state(state)
    e_id = upsert_workflow(state, "wf_E", wfs["E"], {"executionOrder": "v1"})
    api("POST", f"/workflows/{e_id}/activate")  # n8n 2.x only runs a published error workflow (checked 2.43.6)
    for k in ("A", "B", "T"):
        wid = upsert_workflow(state, "wf_" + k, wfs[k], {"executionOrder": "v1", "errorWorkflow": e_id})
        api("POST", f"/workflows/{wid}/activate")
    print(json.dumps(state, indent=2))
    if "--export" in sys.argv:
        export(state)

if __name__ == "__main__":
    main()
