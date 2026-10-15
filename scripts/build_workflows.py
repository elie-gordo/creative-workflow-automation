"""Generate CL workflows (A plan, B produce, E errors) and deploy them via n8n public API.

Usage: N8N_BASE_URL=... N8N_API_KEY=... python build.py [--deploy]
Writes JSON to ./out/. With --deploy: creates/updates data table + workflows on the instance.
"""
import json, os, sys, uuid, urllib.request, urllib.error

BASE_URL = os.environ.get("N8N_BASE_URL", "").rstrip("/")  # e.g. https://my-n8n.example.ts.net
URL = BASE_URL + "/api/v1"
KEY = os.environ.get("N8N_API_KEY", "")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
STATE = os.path.join(HERE, ".n8n-state.json")
BASE_PATH = "/home/node/.n8n-files/cafe-lumen"
TABLE = "cl_slots"
COLUMNS = [
    ("week_id", "string"), ("date", "string"), ("day_index", "number"), ("angle", "string"),
    ("theme", "string"), ("key_message", "string"), ("product", "string"), ("tone", "string"),
    ("cta", "string"), ("status", "string"), ("hook", "string"), ("linkedin_text", "string"),
    ("instagram_caption", "string"), ("hashtags", "string"), ("visual_title", "string"),
    ("visual_subtitle", "string"), ("review_url", "string"), ("reason", "string"),
    ("mode", "string"), ("updated_at", "string"),
]

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
         "position": pos, "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "cl-" + name))}
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
const ANGLES = ['chiffre', 'astuce', 'coulisses', 'question', 'produit'];
const DAYS = ['', 'lun', 'mar', 'mer', 'jeu', 'ven'];
"""

JS_FILES = r"""
const BRAND = { navy: '#1B3A4B', amber: '#F2A541', cream: '#F6EFE6', name: 'CAFÉ LUMEN' };
const LABELS = { chiffre: 'LE CHIFFRE', astuce: 'ASTUCE', coulisses: 'COULISSES', question: 'ET VOUS ?', produit: 'NOUVEAUTÉ' };

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

function renderSvg(angle, visual) {
  const W = 1080, H = 1350;
  const big = angle === 'chiffre';
  const size = big ? 170 : 88;
  const lh = Math.round(size * 1.12);
  const tLines = wrap(visual.title, big ? 9 : 17).slice(0, 4);
  const sLines = wrap(visual.subtitle, 32).slice(0, 3);
  const y0 = big ? 640 : 560;
  const title = tLines.map((l, i) =>
    `<text x="96" y="${y0 + i * lh}" font-family="Georgia, 'Times New Roman', serif" font-size="${size}" font-weight="700" fill="${BRAND.cream}">${esc(l)}</text>`).join('\n');
  const sy = y0 + tLines.length * lh + 40;
  const sub = sLines.map((l, i) =>
    `<text x="96" y="${sy + i * 58}" font-family="Helvetica, Arial, sans-serif" font-size="44" fill="${BRAND.cream}" fill-opacity="0.85">${esc(l)}</text>`).join('\n');
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
<rect width="${W}" height="${H}" fill="${BRAND.navy}"/>
<circle cx="${W - 60}" cy="140" r="260" fill="${BRAND.amber}" fill-opacity="0.12"/>
<rect x="96" y="200" width="120" height="12" fill="${BRAND.amber}"/>
<text x="96" y="300" font-family="Helvetica, Arial, sans-serif" font-size="40" font-weight="700" letter-spacing="8" fill="${BRAND.amber}">${esc(LABELS[angle] || '')}</text>
${title}
${sub}
<rect x="0" y="${H - 150}" width="${W}" height="150" fill="${BRAND.amber}"/>
<text x="96" y="${H - 62}" font-family="Helvetica, Arial, sans-serif" font-size="44" font-weight="700" letter-spacing="6" fill="${BRAND.navy}">${BRAND.name}</text>
<text x="${W - 96}" y="${H - 66}" text-anchor="end" font-family="Helvetica, Arial, sans-serif" font-size="26" fill="${BRAND.navy}">Marque fictive · démo</text>
</svg>`;
}

function fileItem(path, content, mimeType, json = {}) {
  const fileName = path.split('/').pop();
  return { json: { ...json, path }, binary: { data: { data: Buffer.from(content, 'utf8').toString('base64'), mimeType, fileName } } };
}

function linkedinMd(s, c) {
  return `# LinkedIn — ${s.date} (${s.angle})\n\n${c.linkedin_text}\n`;
}

function instagramMd(s, c) {
  return `# Instagram — ${s.date} (${s.angle})\n\n${c.instagram_caption}\n\n${(c.hashtags || []).join(' ')}\n`;
}

// Flat layout: n8n's file node does not create folders, so week/day/angle go in the file name.
function slotPrefix(s) {
  return `${s.week_id}_${s.day_index}-${DAYS[s.day_index]}_${s.angle}`;
}
"""

# ---------------------------------------------------------------- Workflow A
JS_A_VALIDATE = JS_COMMON + r"""
// Normalise the form submission and validate it against the brief rules.
const TONES = ['chaleureux', 'direct', 'expert', 'ludique'];
const f = $input.first().json;
const pick = (...keys) => {
  for (const k of keys) if (f[k] !== undefined && f[k] !== null) return String(f[k]).trim();
  return '';
};
const brief = {
  week_start: pick('Semaine (lundi)', 'week_start'),
  theme: pick('Thème de la semaine', 'theme'),
  key_message: pick('Message clé', 'key_message'),
  product: pick('Produit mis en avant (optionnel)', 'product'),
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
        {"fieldLabel": "Thème de la semaine", "placeholder": "Lancement du cold brew d'automne", "requiredField": True},
        {"fieldLabel": "Message clé", "fieldType": "textarea", "placeholder": "Infusé 18 h, sans sucre ajouté", "requiredField": True},
        {"fieldLabel": "Produit mis en avant (optionnel)", "placeholder": "Cold Brew Lumen 25 cl"},
        {"fieldLabel": "Ton", "fieldType": "dropdown", "requiredField": True,
         "fieldOptions": {"values": [{"option": t} for t in ["chaleureux", "direct", "expert", "ludique"]]}},
        {"fieldLabel": "Appel à l'action (optionnel)", "placeholder": "Disponible en boutique"},
    ]
    nodes.append(node("Formulaire : idée de la semaine", "n8n-nodes-base.formTrigger", 2.2, {
        "formTitle": "Café Lumen — idée de la semaine",
        "formDescription": "Démo portfolio, marque fictive. Une idée → 5 jours de posts LinkedIn + Instagram à valider.",
        "formFields": {"values": fields}, "responseMode": "lastNode", "options": {"path": "cl-brief"}},
        [0, 300], webhookId=str(uuid.uuid5(uuid.NAMESPACE_DNS, "cl-brief"))))
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
        "completionMessage": "=5 créneaux planifiés pour la semaine {{ $('Construire le plan').first().json.week_id }}. Les posts seront produits chaque jour ouvré et soumis à validation.",
        "options": {}}, [1320, 200], executeOnce=True))
    nodes.append(node("Page : brief refusé", "n8n-nodes-base.form", 1, {
        "operation": "completion", "completionTitle": "Brief refusé",
        "completionMessage": "={{ $json.message }}", "options": {}}, [1100, 420]))
    connect(conns, "Formulaire : idée de la semaine", "Valider le brief")
    connect(conns, "Valider le brief", "Semaine déjà planifiée ?")
    connect(conns, "Semaine déjà planifiée ?", "Construire le plan")
    connect(conns, "Construire le plan", "Plan valide ?")
    connect(conns, "Plan valide ?", "Enregistrer les créneaux", 0)
    connect(conns, "Plan valide ?", "Page : brief refusé", 1)
    connect(conns, "Enregistrer les créneaux", "Page : plan créé")
    return {"name": "CL — A · Planifier la semaine", "nodes": nodes, "connections": conns}

# ---------------------------------------------------------------- Workflow B
JS_B_CONTEXT = r"""
// Configuration (no secrets here) + test overrides from the webhook body.
const CONFIG = {
  mode: 'mock',              // 'mock' (default, free) or 'live' (OpenAI, needs the credential)
  llm_model: 'gpt-4o-mini', // live mode only
  base_path: '__BASE_PATH__',
  max_attempts: 2,
  similarity_threshold: 0.6,
};
const MOCK_CASES = ['valid', 'invalid_once', 'invalid_json', 'repeat'];
const input = $input.first().json;
const body = input.body || {};
const date = /^\d{4}-\d{2}-\d{2}$/.test(body.date || '') ? body.date : $now.toISODate();
const mode = ['mock', 'live'].includes(body.mode) ? body.mode : CONFIG.mode;
const mock_case = MOCK_CASES.includes(body.mock_case) ? body.mock_case : 'valid';
return [{ json: { config: CONFIG, date, mode, mock_case, trigger: input.body ? 'webhook' : 'schedule' } }];
""".replace("__BASE_PATH__", BASE_PATH)

JS_B_PROMPT = r"""
// Build the prompt for the day's slot, with the hooks already used (anti-repetition).
const ctx = $('Contexte').first().json;
const slot = $('Créneau du jour').first().json;
const history_hooks = $input.all().map((i) => i.json)
  .filter((r) => r.id && r.id !== slot.id && r.hook && ['to_review', 'needs_review', 'approved'].includes(r.status))
  .map((r) => r.hook).slice(-30);

const ANGLE_GUIDE = {
  chiffre: 'Mettre en avant UN chiffre tiré du brief (ne pas en inventer). visual.title = le chiffre seul.',
  astuce: 'Donner une astuce pratique en 3 points liée au thème.',
  coulisses: "Raconter un court moment de coulisses de l'atelier de torréfaction.",
  question: 'Poser une question ouverte à la communauté, liée au thème.',
  produit: "Présenter le produit mis en avant et finir par l'appel à l'action.",
};
const system_prompt = [
  'Tu es rédacteur social media pour Café Lumen, une torréfaction artisanale FICTIVE (démo portfolio).',
  'Réponds uniquement avec un objet JSON conforme au schéma fourni.',
  "N'invente aucun chiffre, prix, label ou promesse absent du brief. Maximum 2 emojis par texte.",
].join('\n');
const user_prompt = [
  `Date : ${slot.date} — angle du jour : ${slot.angle}. ${ANGLE_GUIDE[slot.angle]}`,
  `Thème : ${slot.theme}`, `Message clé : ${slot.key_message}`,
  `Produit : ${slot.product || '(aucun)'}`, `Ton : ${slot.tone}`, `Appel à l'action : ${slot.cta || '(aucun)'}`,
  'Contraintes : hook ≤ 90 caractères ; linkedin_text 300–1300 caractères, ton professionnel, paragraphes courts ;',
  'instagram_caption 80–600 caractères sans hashtags ; hashtags : 3 à 8, format #MotSansEspace ;',
  'visual.title ≤ 40 caractères ; visual.subtitle ≤ 80 caractères.',
  history_hooks.length ? `Accroches déjà utilisées, à ne pas reprendre : ${history_hooks.map((h) => `"${h}"`).join(' ; ')}` : '',
].filter(Boolean).join('\n');

return [{ json: { ...ctx, slot, history_hooks, attempt: 1, retry_hint: '', system_prompt, user_prompt } }];
"""

JS_B_MOCK = r"""
// Simulated AI response (no API call). mock_case drives the test scenarios.
const it = $input.first().json;
const s = it.slot;
const num = ((/\d+[.,]?\d*\s*(h|heures?|%|g|cl|°)?/i.exec(s.key_message) || [])[0] || '1').trim();
const product = s.product || 'notre café';
const cta = s.cta || 'Passez nous voir en boutique';
const variant = it.attempt > 1 ? ' (autrement dit)' : '';
const TEMPLATES = {
  chiffre: () => ({
    hook: `${num} : le chiffre clé de la semaine chez Café Lumen${variant}`.slice(0, 90),
    visual: { title: num, subtitle: s.key_message.slice(0, 80) },
  }),
  astuce: () => ({
    hook: `3 astuces pour profiter de ${product}${variant}`.slice(0, 90),
    visual: { title: '3 astuces maison', subtitle: `Pour profiter de ${product}`.slice(0, 80) },
  }),
  coulisses: () => ({
    hook: `Dans l'atelier : comment naît ${product}${variant}`.slice(0, 90),
    visual: { title: "Dans l'atelier", subtitle: s.key_message.slice(0, 80) },
  }),
  question: () => ({
    hook: `Et vous, comment aimez-vous votre café en ce moment ?${variant}`.slice(0, 90),
    visual: { title: 'Et vous ?', subtitle: 'Racontez-nous en commentaire' },
  }),
  produit: () => ({
    hook: `${product} arrive chez Café Lumen${variant}`.slice(0, 90),
    visual: { title: product.slice(0, 40), subtitle: cta.slice(0, 80) },
  }),
};
const base = TEMPLATES[s.angle]();
const content = {
  hook: base.hook,
  linkedin_text: `${base.hook}\n\nCette semaine chez Café Lumen : ${s.theme}.\n\n${s.key_message}.\n\n` +
    `Chaque lot est torréfié en petite quantité dans notre atelier, et nous ajustons chaque profil à la main.\n\n${cta}.`,
  instagram_caption: `${base.hook}\n\n${s.key_message}. ${cta}.`,
  hashtags: ['#CafeLumen', '#CafeDeSpecialite', '#Torrefaction', `#${s.angle.charAt(0).toUpperCase()}${s.angle.slice(1)}DuJour`],
  visual: base.visual,
};

let raw;
if (it.mock_case === 'invalid_json' || (it.mock_case === 'invalid_once' && it.attempt === 1)) {
  raw = '{"hook": "Réponse tronquée par le fournisseur...';
} else {
  if (it.mock_case === 'repeat' && it.history_hooks.length) content.hook = it.history_hooks[0];
  raw = JSON.stringify(content);
}
return [{ json: { ...it, raw_response: raw } }];
"""

JS_B_VALIDATE = r"""
// Validate the AI output (schema, lengths, platform limits) and check repetition.
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
}

const norm = (s) => String(s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
  .replace(/[^a-z0-9 ]/g, ' ').split(/\s+/).filter((w) => w.length > 2);
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
  retry_hint = `Ta réponse précédente était invalide (${errors.join(' ; ')}). Respecte strictement le schéma et les longueurs.`;
} else if (similar_hook) {
  if (canRetry) { check = 'retry'; retry_hint = `L'accroche « ${similar_hook} » est déjà utilisée : propose une accroche nettement différente.`; }
  else needs_review = true;
}

return [{ json: {
  config: cfg, date: it.date, mode: it.mode, mock_case: it.mock_case, slot: it.slot,
  history_hooks: it.history_hooks, system_prompt: it.system_prompt, user_prompt: it.user_prompt,
  attempt: check === 'retry' ? it.attempt + 1 : it.attempt,
  check, errors, retry_hint, needs_review, similar_hook, content: errors.length ? null : data,
} }];
"""

JS_B_FILES = JS_COMMON + JS_FILES + r"""
// Write the day's deliverables + meta, status to_review (or needs_review).
const it = $input.first().json;
const s = it.slot, c = it.content;
const dir = `${it.config.base_path}/output/${slotPrefix(s)}`;
const status = it.needs_review ? 'needs_review' : 'to_review';
const svg = renderSvg(s.angle, c.visual);
const review_url = $execution.resumeFormUrl;
const meta = {
  brand: 'Café Lumen (fictive)', week_id: s.week_id, date: s.date, angle: s.angle, status, mode: it.mode,
  attempts: it.attempt, similar_hook: it.similar_hook || null, review_url,
  execution_id: $execution.id, generated_at: new Date().toISOString(), prompt_version: 'v1',
};
const shared = { slot_id: s.id, slot: s, content: c, status, svg, review_url, mode: it.mode,
  similar_hook: it.similar_hook, base_path: it.config.base_path };
return [
  fileItem(`${dir}_linkedin.md`, linkedinMd(s, c), 'text/markdown', shared),
  fileItem(`${dir}_instagram_caption.md`, instagramMd(s, c), 'text/markdown'),
  fileItem(`${dir}_instagram_1080x1350.svg`, svg, 'image/svg+xml'),
  fileItem(`${dir}_meta.json`, JSON.stringify(meta, null, 2), 'application/json'),
];
"""

JS_B_DECISION = JS_COMMON + JS_FILES + r"""
// Apply the human decision: approved -> outbox/, rejected -> rejected/ with the reason.
const f = $('Construire les fichiers').first().json;
const answer = $input.first().json;
const s = f.slot, c = f.content;
const approved = String(answer['Décision'] || '').toLowerCase().startsWith('approuv');
const reason = String(answer['Motif (si rejet)'] || '').trim() || (approved ? '' : '(non précisé)');
const status = approved ? 'approved' : 'rejected';
const dir = `${f.base_path}/${approved ? 'outbox' : 'rejected'}/${slotPrefix(s)}`;
const decision = { status, reason: reason || null, decided_at: new Date().toISOString(), execution_id: $execution.id };
const items = [
  fileItem(`${dir}_linkedin.md`, linkedinMd(s, c), 'text/markdown', { slot_id: s.id, status, reason }),
  fileItem(`${dir}_instagram_caption.md`, instagramMd(s, c), 'text/markdown'),
  fileItem(`${dir}_decision.json`, JSON.stringify(decision, null, 2), 'application/json'),
];
if (approved) items.push(fileItem(`${dir}_instagram_1080x1350.svg`, f.svg, 'image/svg+xml'));
return items;
"""

JS_B_ERROR = JS_COMMON + JS_FILES + r"""
// Generation failed after retries: keep a trace in _errors/.
const it = $input.first().json;
const s = it.slot;
const err = { week_id: s.week_id, date: s.date, angle: s.angle, mode: it.mode, attempts: it.attempt,
  errors: it.errors, execution_id: $execution.id, at: new Date().toISOString() };
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
                      {"httpMethod": "POST", "path": "cl-produire", "responseMode": "onReceived", "options": {}},
                      [0, 400], webhookId=str(uuid.uuid5(uuid.NAMESPACE_DNS, "cl-produire"))))
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
    nodes.append(code("Construire les fichiers", JS_B_FILES, [2420, 100]))
    nodes.append(write_file("Écrire les fichiers", [2640, 100]))
    nodes.append(dt_write("Statut : à valider", "update", table_id, {
        "status": "={{ %s.status }}" % fb, "hook": "={{ %s.content.hook }}" % fb,
        "linkedin_text": "={{ %s.content.linkedin_text }}" % fb,
        "instagram_caption": "={{ %s.content.instagram_caption }}" % fb,
        "hashtags": "={{ %s.content.hashtags.join(' ') }}" % fb,
        "visual_title": "={{ %s.content.visual.title }}" % fb,
        "visual_subtitle": "={{ %s.content.visual.subtitle }}" % fb,
        "review_url": "={{ %s.review_url }}" % fb, "mode": "={{ %s.mode }}" % fb,
        "updated_at": "={{ $now.toISO() }}"},
        [2860, 100], filters=dt_filters(("id", "={{ %s.slot_id }}" % fb)), executeOnce=True))
    nodes.append(node("Validation humaine", "n8n-nodes-base.wait", 1.1, {
        "resume": "form",
        "formTitle": "=Café Lumen — post du {{ %s.slot.date }}" % fb,
        "formDescription": ("=Angle : {{ F.slot.angle }}{{ F.status === 'needs_review' ? ' — ⚠ accroche proche de : ' + F.similar_hook : '' }}"
                            "\n\nLINKEDIN\n{{ F.content.linkedin_text }}\n\nINSTAGRAM\n{{ F.content.instagram_caption }}\n{{ F.content.hashtags.join(' ') }}").replace("F.", fb + "."),
        "formFields": {"values": [
            {"fieldLabel": "Décision", "fieldType": "dropdown", "requiredField": True,
             "fieldOptions": {"values": [{"option": "Approuver"}, {"option": "Rejeter"}]}},
            {"fieldLabel": "Motif (si rejet)", "fieldType": "textarea"}]},
        "options": {}}, [3080, 100], webhookId=str(uuid.uuid5(uuid.NAMESPACE_DNS, "cl-review"))))
    nodes.append(code("Appliquer la décision", JS_B_DECISION, [3300, 100]))
    nodes.append(write_file("Écrire la décision", [3520, 100]))
    dec = "$('Appliquer la décision').first().json"
    nodes.append(dt_write("Statut final", "update", table_id, {
        "status": "={{ %s.status }}" % dec, "reason": "={{ %s.reason }}" % dec, "updated_at": "={{ $now.toISO() }}"},
        [3740, 100], filters=dt_filters(("id", "={{ %s.slot_id }}" % dec)), executeOnce=True))
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
    connect(conns, "Résultat", "Construire les fichiers", 0)
    connect(conns, "Résultat", "Mode live ?", 1)
    connect(conns, "Résultat", "Préparer l'erreur", 2)
    connect(conns, "Construire les fichiers", "Écrire les fichiers")
    connect(conns, "Écrire les fichiers", "Statut : à valider")
    connect(conns, "Statut : à valider", "Validation humaine")
    connect(conns, "Validation humaine", "Appliquer la décision")
    connect(conns, "Appliquer la décision", "Écrire la décision")
    connect(conns, "Écrire la décision", "Statut final")
    connect(conns, "Préparer l'erreur", "Écrire l'erreur")
    connect(conns, "Écrire l'erreur", "Statut : erreur")
    return {"name": "CL — B · Produire le jour", "nodes": nodes, "connections": conns}

# ---------------------------------------------------------------- Workflow E
JS_E = r"""
// Unhandled failure in a CL workflow: write a trace (no notification is sent).
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
    nodes.append(node("Erreur dans un workflow CL", "n8n-nodes-base.errorTrigger", 1, {}, [0, 300]))
    nodes.append(code("Préparer la trace", JS_E, [220, 300]))
    nodes.append(write_file("Écrire la trace", [440, 300]))
    connect(conns, "Erreur dans un workflow CL", "Préparer la trace")
    connect(conns, "Préparer la trace", "Écrire la trace")
    return {"name": "CL — E · Erreurs", "nodes": nodes, "connections": conns}

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
                      {"httpMethod": "GET", "path": "cl-inspect", "responseMode": "lastNode", "options": {}},
                      [0, 300], webhookId=str(uuid.uuid5(uuid.NAMESPACE_DNS, "cl-inspect"))))
    nodes.append(node("Lire les sorties", "n8n-nodes-base.readWriteFile", 1,
                      {"operation": "read", "fileSelector": BASE_PATH + "/**/*", "options": {}},
                      [220, 300], alwaysOutputData=True))
    nodes.append(code("Lister", JS_T, [440, 300]))
    connect(conns, "Webhook : inspecter", "Lire les sorties")
    connect(conns, "Lire les sorties", "Lister")
    return {"name": "CL — T · Inspecter les sorties (lecture seule)", "nodes": nodes, "connections": conns}

# ---------------------------------------------------------------- deploy
def ensure_table(state):
    for t in api("GET", "/data-tables?limit=100").get("data", []):
        if t["name"] == TABLE:
            state["table_id"] = t["id"]
            return t["id"]
    t = api("POST", "/data-tables", {"name": TABLE, "columns": [{"name": n, "type": ty} for n, ty in COLUMNS]})
    state["table_id"] = t["id"]
    return t["id"]

def upsert_workflow(state, key, wf, settings):
    body = {"name": wf["name"], "nodes": wf["nodes"], "connections": wf["connections"], "settings": settings}
    wid = state.get(key)
    if wid:
        api("PUT", f"/workflows/{wid}", body)
    else:
        wid = api("POST", "/workflows", body)["id"]
        state[key] = wid
        save_state(state)
    return wid

def main():
    os.makedirs(OUT, exist_ok=True)
    deploy = "--deploy" in sys.argv
    state = load_state()
    table_id = ensure_table(state) if deploy else "TABLE_ID"
    save_state(state) if deploy else None
    wfs = {"E": workflow_e(), "A": workflow_a(table_id), "B": workflow_b(table_id), "T": workflow_t()}
    for k, wf in wfs.items():
        json.dump(wf, open(os.path.join(OUT, f"{k}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    if not deploy:
        print("built", list(wfs))
        return
    e_id = upsert_workflow(state, "wf_E", wfs["E"], {"executionOrder": "v1"})
    for k in ("A", "B", "T"):
        upsert_workflow(state, "wf_" + k, wfs[k], {"executionOrder": "v1", "errorWorkflow": e_id})
    save_state(state)
    print(json.dumps(state, indent=2))

if __name__ == "__main__":
    main()
