"""End-to-end scenarios against the TENSIL workflows on an n8n instance (mock mode, fictive data).

Usage: N8N_BASE_URL=... N8N_API_KEY=... python scripts/e2e_tests.py [--save-examples]
Requires workflows deployed with scripts/build_workflows.py --deploy (reads scripts/.n8n-state.json).
WARNING: deletes and recreates the rows of weeks 2026-W43 and 2026-W44 in the tensil_slots data table.
Also creates, runs and deletes a temporary workflow to check that the error workflow E writes its trace.
--save-examples replaces examples/ with the files produced by this run (review links redacted).
"""
import json, os, re, shutil, sys, time, uuid, urllib.parse, urllib.request, urllib.error

HOST = os.environ["N8N_BASE_URL"].rstrip("/")
API = HOST + "/api/v1"
KEY = os.environ["N8N_API_KEY"]
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STATE = json.load(open(os.path.join(HERE, ".n8n-state.json")))
TABLE, WF_B, WF_E = STATE["table_id"], STATE["wf_B"], STATE["wf_E"]
WEEKS = ("2026-W43", "2026-W44")
RESULTS = []
sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252

def http(method, url, body=None, headers=None, raw=False):
    h = {"Accept": "text/html,application/json", "User-Agent": "Mozilla/5.0 (tensil-tests)"}
    h.update(headers or {})
    req = urllib.request.Request(url, method=method, data=body, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        data = e.read()
    return data if raw else (json.loads(data) if data.strip().startswith((b"{", b"[")) else data.decode("utf-8", "replace"))

def api(method, path, body=None):
    return http(method, API + path, json.dumps(body).encode() if body is not None else None,
                {"X-N8N-API-KEY": KEY, "Content-Type": "application/json"})

def multipart(url, fields):
    b = uuid.uuid4().hex
    parts = b"".join(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode("utf-8") for k, v in fields.items())
    return http("POST", url, parts + f"--{b}--\r\n".encode(), {"Content-Type": f"multipart/form-data; boundary={b}"})

def rows():
    return [r for r in api("GET", f"/data-tables/{TABLE}/rows?limit=100").get("data", []) if r["week_id"] in WEEKS]

def row(date):
    return next((r for r in rows() if r["date"] == date), None)

def delete_weeks():
    for w in WEEKS:
        f = urllib.parse.quote(json.dumps({"type": "and", "filters": [{"columnName": "week_id", "condition": "eq", "value": w}]}))
        api("DELETE", f"/data-tables/{TABLE}/rows/delete?filter={f}")

def last_exec(wf):
    data = api("GET", f"/executions?workflowId={wf}&limit=1")["data"]
    return data[0] if data else {"id": "0", "status": "none"}

def wait_exec(wf, after_id, statuses=("success", "error", "waiting", "crashed")):
    for _ in range(60):
        e = last_exec(wf)
        if int(e["id"]) > int(after_id) and e["status"] in statuses:
            return api("GET", f"/executions/{e['id']}?includeData=true")
        time.sleep(1)
    raise SystemExit("timeout waiting execution")

def node_out(ex, name):
    rd = ex["data"]["resultData"]["runData"].get(name)
    return None if not rd else rd[-1]["data"]["main"][0][0]["json"] if rd[-1]["data"]["main"][0] else {}

def check(label, cond, detail=""):
    RESULTS.append((label, bool(cond)))
    print(("PASS " if cond else "FAIL ") + label + (f"  [{detail}]" if detail else ""))

def submit_brief(fields):
    r = multipart(HOST + "/form/tensil-brief", fields)
    url = r.get("formWaitingUrl") if isinstance(r, dict) else None
    if not url:
        return str(r)
    for _ in range(4):
        time.sleep(1.5)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=8) as x:
                return x.read().decode("utf-8", "replace")
        except Exception:
            continue
    return ""

def produce(date, mock_case="valid"):
    before = last_exec(WF_B)["id"]
    http("POST", HOST + "/webhook/tensil-produire", json.dumps({"date": date, "mock_case": mock_case}).encode(),
         {"Content-Type": "application/json"})
    return wait_exec(WF_B, before)

def review(date, decision, reason=""):
    multipart(row(date)["review_url"], {"field-0": decision, "field-1": reason})
    for _ in range(30):
        r = row(date)
        if r["status"] in ("approved", "rejected"):
            return r
        time.sleep(1)
    return row(date)

def inspect():
    r = http("GET", HOST + "/webhook/tensil-inspect")
    return r.get("files", []) if isinstance(r, dict) else []

def file(files, suffix):
    """Most recent file whose path ends with suffix (traces carry an execution id, the highest is the latest)."""
    found = [f for f in files if re.search(suffix + "$", f["path"])]
    return sorted(found, key=lambda f: [int(n) for n in re.findall(r"\d+", f["path"])])[-1] if found else None

def check_error_workflow():
    """Temporary workflow that always throws, with E as error workflow: E must write _errors/workflow_<id>.json."""
    wf = api("POST", "/workflows", {"name": "TENSIL — X · Test du workflow d'erreur (temporaire)", "settings": {
        "executionOrder": "v1", "errorWorkflow": WF_E}, "connections": {
        "Webhook": {"main": [[{"node": "Panne simulée", "type": "main", "index": 0}]]}}, "nodes": [
        {"parameters": {"httpMethod": "POST", "path": "tensil-test-erreur", "responseMode": "onReceived", "options": {}},
         "name": "Webhook", "type": "n8n-nodes-base.webhook", "typeVersion": 2, "position": [0, 0],
         "webhookId": str(uuid.uuid4())},
        {"parameters": {"jsCode": "throw new Error('Panne simulée pour tester le workflow E');"},
         "name": "Panne simulée", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [220, 0]}]})
    try:
        api("POST", f"/workflows/{wf['id']}/activate")
        before_e = last_exec(WF_E)["id"]
        for _ in range(15):  # the production webhook is registered a moment after activation
            r = http("POST", HOST + "/webhook/tensil-test-erreur", b"{}", {"Content-Type": "application/json"})
            if not (isinstance(r, dict) and r.get("code") == 404):
                break
            time.sleep(1)
        failed = wait_exec(wf["id"], 0)
        traced = wait_exec(WF_E, before_e)
        return failed["id"], traced["status"]
    finally:
        api("POST", f"/workflows/{wf['id']}/deactivate")
        api("DELETE", f"/workflows/{wf['id']}")

REDACT = [(re.compile(r"https?://[^/\"\s]+(/form-waiting/)"), r"https://n8n.example.com\1"),
          (re.compile(r"signature=[^\"&\s]+"), "signature=REDACTED")]

def save_examples(files):
    target = os.path.join(ROOT, "examples")
    shutil.rmtree(target, ignore_errors=True)
    wanted = [rf"/output/2026-W43_[1245]-\w+_\w+_(linkedin\.md|instagram_caption\.md|instagram_1080x1350\.svg|meta\.json)",
              r"/outbox/2026-W43_1-lun_devoilement_\w+\.(md|svg|json)", r"/rejected/2026-W43_5-ven_boutique_\w+\.(md|json)"]
    keep = [f for f in files if any(re.search(w + "$", f["path"]) for w in wanted)]
    keep += [f for f in (file(files, r"/_errors/2026-W43_3-mer_\d+\.json"), file(files, r"/_errors/workflow_\d+\.json")) if f]
    for f in keep:
        rel = f["path"].split("/tensil/", 1)[1]
        text = f["content"]
        for pattern, repl in REDACT:
            text = pattern.sub(repl, text)
        os.makedirs(os.path.dirname(os.path.join(target, rel)), exist_ok=True)
        with open(os.path.join(target, rel), "w", encoding="utf-8", newline="\n") as out:
            out.write(text)
    print(f"examples/: {len(keep)} fichiers")

BRIEF = {"field-0": "2026-10-19", "field-1": "Semaine de présentation de la lampe TENSIL",
         "field-2": "Une lampe de bureau articulée, équilibrée par 2 ressorts par segment", "field-3": "TENSIL Graphite",
         "field-4": "sobre", "field-5": "Voir la boutique de démonstration"}

def main():
    delete_weeks()
    page = submit_brief({"field-0": "2026-10-20", "field-1": "Court", "field-2": "En vente à 249 € avec livraison offerte",
                         "field-4": "bizarre"})
    check("Brief invalide refusé (lundi, ton, prix, vente, chiffre), rien écrit",
          "lundi" in page and "Promesse non vérifiable" in page and "249" in page and not rows())
    submit_brief(BRIEF)
    rs = [r for r in rows() if r["week_id"] == "2026-W43"]
    check("Brief valide → 5 créneaux planned, un angle par jour",
          len(rs) == 5 and all(r["status"] == "planned" for r in rs)
          and sorted(r["angle"] for r in rs) == sorted(["devoilement", "anatomie", "coulisses", "coloris", "boutique"])
          and rs[0]["key_message"] == BRIEF["field-2"], f"{len(rs)} lignes")
    page = submit_brief(BRIEF)
    check("Semaine déjà planifiée refusée", "déjà planifiée" in page and len(rows()) == 5)

    ex = produce("2026-10-19")
    r = row("2026-10-19")
    check("Lundi dévoilement (valid) → to_review + lien de validation",
          ex["status"] == "waiting" and r["status"] == "to_review" and r["review_url"], r["hook"])
    ex = produce("2026-10-20", "claim")
    v = node_out(ex, "Valider la réponse") or {}
    log = v.get("attempts_log") or [{}]
    check("Mardi anatomie (claim) → promesse refusée, nouvel essai, to_review",
          row("2026-10-20")["status"] == "to_review" and v.get("attempt") == 2 and "249" in " ".join(log[0].get("errors", [])),
          " | ".join(log[0].get("errors", [])))
    ex = produce("2026-10-21", "invalid_json")
    r = row("2026-10-21")
    check("Mercredi coulisses (invalid_json) → 2 essais puis statut error", ex["status"] == "success" and r["status"] == "error", r["reason"])
    ex = produce("2026-10-22", "repeat")
    v = node_out(ex, "Valider la réponse") or {}
    check("Jeudi coloris (repeat) → répétition détectée, needs_review",
          row("2026-10-22")["status"] == "needs_review" and v.get("similar_hook"), v.get("similar_hook"))
    produce("2026-10-23")
    r = review("2026-10-23", "Rejeter", "Accroche trop proche de la page d'accueil du site")
    check("Vendredi boutique rejeté avec motif", r["status"] == "rejected" and "proche" in (r["reason"] or ""), r["reason"])
    r = review("2026-10-19", "Approuver")
    check("Lundi approuvé", r["status"] == "approved")
    ex = produce("2026-10-24")
    check("Samedi sans créneau → arrêt propre", ex["status"] == "success" and "Rien à produire" in ex["data"]["resultData"]["runData"])

    submit_brief({**BRIEF, "field-0": "2026-10-26"})
    ex = produce("2026-10-26", "invalid_once")
    v = node_out(ex, "Valider la réponse") or {}
    r = row("2026-10-26")
    check("Semaine suivante, lundi (invalid_once) → nouvel essai, accroche différente de la semaine 43",
          r["status"] == "to_review" and v.get("attempt") == 2 and r["hook"] != row("2026-10-19")["hook"], r["hook"])

    failed_id, e_status = check_error_workflow()
    files = inspect()
    paths = [f["path"] for f in files]
    check("Workflow E : exception non gérée → trace _errors/workflow_<id>.json",
          e_status == "success" and any(p.endswith(f"/_errors/workflow_{failed_id}.json") for p in paths), f"exécution {failed_id}")

    need = ["output/2026-W43_1-lun_devoilement_linkedin.md", "output/2026-W43_1-lun_devoilement_instagram_caption.md",
            "output/2026-W43_1-lun_devoilement_instagram_1080x1350.svg", "output/2026-W43_1-lun_devoilement_meta.json",
            "outbox/2026-W43_1-lun_devoilement_decision.json", "outbox/2026-W43_1-lun_devoilement_instagram_1080x1350.svg",
            "rejected/2026-W43_5-ven_boutique_decision.json"]
    for n in need:
        check(f"fichier {n}", any(p.endswith(n) for p in paths))
    check("trace _errors/ pour mercredi", file(files, r"/_errors/2026-W43_3-mer_\d+\.json") is not None)
    svgs = [f for f in files if re.search(r"/output/2026-W43_\d-\w+_instagram_1080x1350\.svg$", f["path"])]
    check("4 visuels avec le rendu Blender intégré", len(svgs) == 4 and all("data:image/webp;base64," in f["content"] for f in svgs),
          f"{len(svgs)} SVG")
    meta = json.loads(file(files, "/output/2026-W43_2-mar_anatomie_meta.json")["content"])
    check("meta mardi : brief, contrôles des 2 essais, rendu épinglé, non publié",
          meta["brief"]["theme"] == BRIEF["field-1"] and len(meta["checks"]) == 2 and meta["visual"]["render"]["embedded"]
          and meta["published"] is False)
    md = file(files, "/outbox/2026-W43_1-lun_devoilement_linkedin.md")["content"]
    check("post approuvé : mention marque fictive, aucune promesse", "marque fictive" in md and "€" not in md)

    print(f"\n{sum(1 for _, c in RESULTS if c)}/{len(RESULTS)} PASS")
    if "--save-examples" in sys.argv:
        save_examples(files)

if __name__ == "__main__":
    main()
