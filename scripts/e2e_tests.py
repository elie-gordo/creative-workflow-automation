"""End-to-end scenarios against the CL workflows on an n8n instance (mock mode, fictive data).

Usage: N8N_BASE_URL=... N8N_API_KEY=... python scripts/e2e_tests.py
Requires workflows deployed with scripts/build_workflows.py --deploy (reads scripts/.n8n-state.json).
WARNING: deletes and recreates the rows of week 2026-W43 in the cl_slots data table.
"""
import json, os, sys, time, uuid, urllib.parse, urllib.request, urllib.error

HOST = os.environ["N8N_BASE_URL"].rstrip("/")
API = HOST + "/api/v1"
KEY = os.environ["N8N_API_KEY"]
STATE = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".n8n-state.json")))
TABLE, WF_B = STATE["table_id"], STATE["wf_B"]
WEEK = "2026-W43"
RESULTS = []

def http(method, url, body=None, headers=None, raw=False):
    h = {"Accept": "text/html,application/json", "User-Agent": "Mozilla/5.0 (cl-tests)"}
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
    return api("GET", f"/data-tables/{TABLE}/rows?limit=100").get("data", [])

def row(date):
    return next((r for r in rows() if r["date"] == date), None)

def delete_week():
    f = urllib.parse.quote(json.dumps({"type": "and", "filters": [{"columnName": "week_id", "condition": "eq", "value": WEEK}]}))
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
    r = multipart(HOST + "/form/cl-brief", fields)
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
    http("POST", HOST + "/webhook/cl-produire", json.dumps({"date": date, "mock_case": mock_case}).encode(),
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
    return http("GET", HOST + "/webhook/cl-inspect")

BRIEF = {"field-0": "2026-10-19", "field-1": "Lancement du cold brew d'automne",
         "field-2": "Infusé 18 h, sans sucre ajouté", "field-3": "Cold Brew Lumen 25 cl",
         "field-4": "chaleureux", "field-5": "Disponible en boutique"}

def main():
    delete_week()
    page = submit_brief({"field-0": "2026-10-20", "field-1": "Court", "field-2": "Infusé 18 h, sans sucre ajouté", "field-4": "bizarre"})
    check("Brief invalide refusé, rien écrit", "lundi" in page and not rows())
    submit_brief(BRIEF)
    rs = [r for r in rows() if r["week_id"] == WEEK]
    check("Brief valide → 5 créneaux planned", len(rs) == 5 and all(r["status"] == "planned" for r in rs)
          and rs[0]["key_message"] == "Infusé 18 h, sans sucre ajouté", f"{len(rs)} lignes")
    page = submit_brief(BRIEF)
    check("Semaine déjà planifiée refusée", "déjà planifiée" in page and len(rows()) == 5)

    ex = produce("2026-10-19")
    r = row("2026-10-19")
    check("Lundi (valid) → to_review + lien de validation", ex["status"] == "waiting" and r["status"] == "to_review" and r["review_url"], r["hook"])
    ex = produce("2026-10-20", "invalid_once")
    v = node_out(ex, "Valider la réponse") or {}
    check("Mardi (invalid_once) → nouvel essai puis to_review", row("2026-10-20")["status"] == "to_review" and v.get("attempt") == 2, f"attempt={v.get('attempt')}")
    ex = produce("2026-10-21", "invalid_json")
    r = row("2026-10-21")
    check("Mercredi (invalid_json) → 2 essais puis statut error", ex["status"] == "success" and r["status"] == "error", r["reason"])
    ex = produce("2026-10-22", "repeat")
    v = node_out(ex, "Valider la réponse") or {}
    check("Jeudi (repeat) → répétition détectée, needs_review", row("2026-10-22")["status"] == "needs_review" and v.get("similar_hook"), v.get("similar_hook"))
    produce("2026-10-23")
    r = review("2026-10-23", "Rejeter", "Ton trop commercial pour un vendredi")
    check("Vendredi rejeté avec motif", r["status"] == "rejected" and "commercial" in (r["reason"] or ""), r["reason"])
    r = review("2026-10-19", "Approuver")
    check("Lundi approuvé", r["status"] == "approved")
    ex = produce("2026-10-24")
    check("Samedi sans créneau → arrêt propre", ex["status"] == "success" and "Rien à produire" in ex["data"]["resultData"]["runData"])

    ins = inspect()
    paths = [f["path"] for f in ins.get("files", [])] if isinstance(ins, dict) else []
    print("\n".join(paths) or str(ins)[:500])
    need = ["output/2026-W43_1-lun_chiffre_linkedin.md", "output/2026-W43_1-lun_chiffre_instagram_1080x1350.svg",
            "output/2026-W43_1-lun_chiffre_meta.json", "outbox/2026-W43_1-lun_chiffre_decision.json",
            "outbox/2026-W43_1-lun_chiffre_instagram_1080x1350.svg", "rejected/2026-W43_5-ven_produit_decision.json"]
    for n in need:
        check(f"fichier {n}", any(p.endswith(n) for p in paths))
    check("trace _errors/ pour mercredi", any("/_errors/2026-W43_3-mer_" in p for p in paths))
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"), exist_ok=True)
    json.dump(ins, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out/inspect.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n{sum(1 for _, c in RESULTS if c)}/{len(RESULTS)} PASS")

if __name__ == "__main__":
    main()
