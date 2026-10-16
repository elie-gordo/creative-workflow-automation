// Offline checks of the Code nodes (no n8n needed): runs the real node JavaScript from scripts/out/*.json
// with stubbed n8n globals ($input, $, $execution, $now).
// Usage: python scripts/build_workflows.py && node scripts/offline_tests.mjs [--previews]
// --previews also writes the 5 Instagram SVGs to scripts/out/preview/ (renders read from ../blender-studio-object if present).
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, 'out');
const RENDERS = path.join(HERE, '..', '..', 'blender-studio-object');
const load = (k) => JSON.parse(fs.readFileSync(path.join(OUT, `${k}.json`), 'utf8'));
const A = load('A'), B = load('B');
const codeOf = (wf, name) => wf.nodes.find((n) => n.name === name).parameters.jsCode;
const AsyncFunction = Object.getPrototypeOf(async () => {}).constructor;

let pass = 0, fail = 0;
function check(label, cond, detail = '') {
  cond ? pass++ : fail++;
  console.log(`${cond ? 'PASS' : 'FAIL'} ${label}${detail ? `  [${detail}]` : ''}`);
}

async function run(wf, name, input, refs = {}) {
  const items = (Array.isArray(input) ? input : [input]).map((json) => ({ json }));
  const fn = new AsyncFunction('$input', '$', '$execution', '$now', codeOf(wf, name));
  const $ = (n) => ({ first: () => ({ json: refs[n] }) });
  const $now = { toISODate: () => '2026-10-19', toISO: () => '2026-10-19T08:00:00.000Z' };
  const $execution = { id: 'offline', resumeFormUrl: 'https://n8n.example.com/form-waiting/offline' };
  return fn({ first: () => items[0], all: () => items }, $, $execution, $now);
}

const BRIEF = {
  'Semaine (lundi)': '2026-10-19', 'Thème de la semaine': 'Semaine de présentation de la lampe TENSIL',
  'Message clé': 'Une lampe de bureau articulée, équilibrée par 2 ressorts par segment',
  'Produit ou coloris mis en avant (optionnel)': 'TENSIL Graphite', Ton: 'sobre',
  "Appel à l'action (optionnel)": 'Voir la boutique de démonstration',
};

// ---------------------------------------------------------------- A: brief validation and plan
const okBrief = (await run(A, 'Valider le brief', BRIEF))[0].json;
check('A · brief TENSIL valide', okBrief.valid && okBrief.week_id === '2026-W43', okBrief.errors.join(' | '));
const badBrief = (await run(A, 'Valider le brief', { ...BRIEF, 'Semaine (lundi)': '2026-10-20', Ton: 'bizarre',
  'Message clé': 'En vente à 249 € avec livraison offerte', 'Thème de la semaine': 'Court' }))[0].json;
const e = badBrief.errors.join(' | ');
check('A · brief invalide : lundi, ton, longueur', !badBrief.valid && /lundi/.test(e) && /Ton/.test(e) && /Thème/.test(e), e);
check('A · brief invalide : prix, vente, livraison, chiffre', /prix/.test(e) && /vente/.test(e) && /livraison/.test(e) && /249/.test(e));
const plan = (await run(A, 'Construire le plan', [{}], { 'Valider le brief': okBrief })).map((i) => i.json);
check('A · plan de 5 créneaux, un angle par jour',
  plan.length === 5 && plan.map((p) => p.angle).join() === 'devoilement,anatomie,coulisses,coloris,boutique'
  && plan[4].date === '2026-10-23' && plan.every((p) => p.status === 'planned'));
const dup = (await run(A, 'Construire le plan', [{ id: 1 }], { 'Valider le brief': okBrief }))[0].json;
check('A · semaine déjà planifiée refusée', dup.ok === false && /déjà planifiée/.test(dup.message));

// ---------------------------------------------------------------- B: generation loop per angle and mock case
const ctx = (await run(B, 'Contexte', { body: { date: '2026-10-19' } }))[0].json;
check('B · contexte mock par défaut', ctx.mode === 'mock' && ctx.mock_case === 'valid' && ctx.config.base_path.endsWith('/tensil'));

async function generate(slot, mock_case, history = []) {
  const c = { ...ctx, mock_case };
  let it = (await run(B, 'Préparer le prompt', history, { Contexte: c, 'Créneau du jour': slot }))[0].json;
  for (let i = 0; i < 4; i++) {
    const mocked = (await run(B, 'Réponse simulée (mock)', it))[0].json;
    it = (await run(B, 'Valider la réponse', mocked))[0].json;
    if (it.check !== 'retry') return it;
  }
  return it;
}

function assetResponse(p) {
  const file = path.join(RENDERS, p);
  if (!fs.existsSync(file)) return { encoding: 'base64', content: Buffer.alloc(200).toString('base64') };
  return { encoding: 'base64', content: fs.readFileSync(file).toString('base64') };
}

const results = {};
for (const slot of plan) {
  const s = { ...slot, id: slot.day_index };
  const v = await generate(s, 'valid');
  results[s.angle] = v;
  check(`B · ${s.angle} (valid) → ok au 1er essai`, v.check === 'ok' && v.attempt === 1, v.errors.join(' | '));
  check(`B · ${s.angle} : rendu ${v.asset.path}`, /^renders\/web\/.+\.webp$/.test(v.asset.path) && v.asset.ref.length === 40);
  check(`B · ${s.angle} : prompt contient la fiche produit`, /Fiche produit/.test(v.system_prompt) && /2 ressorts par segment/.test(v.system_prompt));
}
const mon = { ...plan[0], id: 1 }, tue = { ...plan[1], id: 2 }, thu = { ...plan[3], id: 4 };

const claim = await generate(tue, 'claim');
check('B · claim → promesse refusée puis nouvel essai propre', claim.check === 'ok' && claim.attempt === 2
  && /promesse interdite/.test(claim.attempts_log[0].errors.join()) && /249/.test(claim.attempts_log[0].errors.join()),
  claim.attempts_log[0].errors.join(' | '));
const once = await generate(tue, 'invalid_once');
check('B · invalid_once → nouvel essai puis ok', once.check === 'ok' && once.attempt === 2);
const broken = await generate(tue, 'invalid_json');
check('B · invalid_json → échec après 2 essais', broken.check === 'fail' && broken.attempt === 2 && broken.attempts_log.length === 2);
const history = [{ id: 1, hook: results.devoilement.post.hook, status: 'to_review' }];
const repeat = await generate(thu, 'repeat', history);
check('B · repeat → répétition détectée, needs_review', repeat.check === 'ok' && repeat.needs_review && repeat.similar_hook === history[0].hook);
const nextWeek = await generate({ ...mon, id: 9, week_id: '2026-W44' }, 'valid', history);
check("B · même angle la semaine suivante → accroche différente au 2e essai", nextWeek.check === 'ok' && nextWeek.attempt === 2
  && nextWeek.post.hook !== history[0].hook);

// Hand-written outputs that the checks must reject.
async function validateRaw(slot, post) {
  const it = (await run(B, 'Préparer le prompt', [], { Contexte: ctx, 'Créneau du jour': slot }))[0].json;
  return (await run(B, 'Valider la réponse', { ...it, raw_response: JSON.stringify(post) }))[0].json;
}
const good = results.devoilement.post;
const cases = [
  ['LED', { ...good, linkedin_text: good.linkedin_text + '\n\nAmpoule LED 8 W.' }, /caractéristique/],
  ['chiffre inventé', { ...good, instagram_caption: good.instagram_caption + ' Seulement 1,2 kg.' }, /chiffre absent/],
  ['fait main', { ...good, linkedin_text: good.linkedin_text + '\n\nRotules polies à la main.' }, /origine/],
  ['superlatif', { ...good, hook: 'La meilleure lampe de bureau du moment' }, /superlatif/],
  ['hashtag invalide', { ...good, hashtags: ['#TENSIL', 'design', '#Rendu3D'] }, /hashtags/],
  ['linkedin trop long', { ...good, linkedin_text: 'x'.repeat(1400) }, /linkedin_text/],
];
for (const [label, post, re] of cases) {
  const r = await validateRaw(mon, post);
  check(`B · rejet : ${label}`, r.check === 'retry' && re.test(r.errors.join(' | ')), r.errors.join(' | '));
}
const anatBad = await validateRaw({ ...tue }, { ...results.anatomie.post, visual: { title: 'Deux ressorts équilibreurs', subtitle: '' } });
check('B · rejet : titre anatomie sans chiffre', anatBad.check === 'retry' && /anatomie/.test(anatBad.errors.join()));

// ---------------------------------------------------------------- B: files, decision, error
const previews = process.argv.includes('--previews');
if (previews) fs.mkdirSync(path.join(OUT, 'preview'), { recursive: true });
for (const [angle, v] of Object.entries(results)) {
  const files = await run(B, 'Construire les fichiers', { ...v, ...assetResponse(v.asset.path) });
  const byExt = Object.fromEntries(files.map((f) => [f.json.path.split('_').pop(), f]));
  const text = (k) => Buffer.from(byExt[k].binary.data.data, 'base64').toString('utf8');
  const svg = text('1080x1350.svg'), meta = JSON.parse(text('meta.json'));
  check(`B · ${angle} : 4 fichiers, SVG avec rendu intégré`, files.length === 4 && svg.includes('data:image/webp;base64,')
    && /^<\?xml/.test(svg) && svg.includes('TENSIL'));
  check(`B · ${angle} : meta (brief, angle, statut, contrôles, provenance)`, meta.brief.theme === BRIEF['Thème de la semaine']
    && meta.slot.angle === angle && meta.status === 'to_review' && meta.published === false
    && meta.checks.length === 1 && meta.visual.render.embedded && /github\.com/.test(meta.visual.render.source));
  check(`B · ${angle} : mention marque fictive dans les .md`, /marque fictive/.test(text('linkedin.md')) && /marque fictive/.test(text('caption.md')));
  check(`B · ${angle} : chemins output/ à plat`, files.every((f) => /\/tensil\/output\/2026-W43_\d-(lun|mar|mer|jeu|ven)_/.test(f.json.path)));
  if (previews) fs.writeFileSync(path.join(OUT, 'preview', path.basename(byExt['1080x1350.svg'].json.path)), svg);
}
const noAsset = await run(B, 'Construire les fichiers', { ...results.boutique, error: { message: 'timeout' } });
check('B · rendu indisponible → needs_review, visuel sans image', noAsset[0].json.status === 'needs_review'
  && /indisponible/.test(noAsset[0].json.reason));

const built = (await run(B, 'Construire les fichiers', { ...results.devoilement, ...assetResponse(results.devoilement.asset.path) }))[0].json;
const approved = await run(B, 'Appliquer la décision', { Décision: 'Approuver' }, { 'Construire les fichiers': built });
check('B · approuvé → outbox/ avec SVG', approved.length === 4 && approved.every((f) => f.json.path.includes('/outbox/'))
  && JSON.parse(Buffer.from(approved[2].binary.data.data, 'base64')).published === false);
const rejected = await run(B, 'Appliquer la décision', { Décision: 'Rejeter', 'Motif (si rejet)': 'Accroche trop proche du site' },
  { 'Construire les fichiers': built });
const decision = JSON.parse(Buffer.from(rejected[2].binary.data.data, 'base64'));
check('B · rejeté → rejected/ avec motif, sans SVG', rejected.length === 3 && rejected.every((f) => f.json.path.includes('/rejected/'))
  && decision.reason === 'Accroche trop proche du site' && decision.status === 'rejected');
const errFile = (await run(B, "Préparer l'erreur", broken))[0];
const errJson = JSON.parse(Buffer.from(errFile.binary.data.data, 'base64'));
check("B · erreur → _errors/ avec brief et contrôles", errFile.json.path.includes('/_errors/2026-W43_2-mar_')
  && errJson.checks.length === 2 && errJson.brief.theme && errFile.json.reason === 'JSON invalide');

console.log(`\n${pass}/${pass + fail} PASS`);
process.exit(fail ? 1 : 0);
