"""
security_tests.py
=================

Objective 3 evaluation, security part: a repeatable set of test cases for the
four properties the study means by a "secure" pipeline -

    A. credential confidentiality   secrets stay out of the code and its history
    B. protected transport          data moves over encrypted connections only
    C. controlled write access      only an authorised account, for its own city
    D. data integrity               bad or hostile input cannot corrupt the store
    E. traceability                 every import and every pipeline run is recorded

Each case states what is expected, does the thing for real against the running
code (the Flask app through its test client, the local database, the git
repository), and reports what actually happened.

It creates three temporary accounts (zz_sec_*) and one temporary yield row, and
removes them again at the end, whatever happens. It refuses to run against a
database that is not on this machine.

Output: printed table, also saved to db/security_test_report.txt.

Usage
    python backend/scripts/security_tests.py
    python backend/scripts/security_tests.py --include-prod   # ST-02/03 also search for the
                                                              # production secrets in .env.prod
"""
import base64
import json
import os
import re
import secrets
import subprocess
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.abspath(os.path.join(HERE, ".."))
REPO = os.path.abspath(os.path.join(BACKEND, ".."))
REPORT_PATH = os.path.join(BACKEND, "db", "security_test_report.txt")
sys.path.insert(0, BACKEND)

from sqlalchemy import text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

import config  # noqa: E402
from app import app  # noqa: E402
from extensions import db  # noqa: E402

TEST_YEAR = 2000          # a season no real record uses
MARK = "zz_security_test"  # source tag on the one row the tests really write
CITY_A, CITY_B = "City of Calamba", "City of Cabuyao"
OLD_PUBLIC_SECRET = "dev-only-change-me"  # the fallback this repository used to ship


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


INCLUDE_PROD = False  # --include-prod: also search for the production secrets in .env.prod


def secret_values():
    """Real secret values from backend/.env (and .env.prod) - held in memory, never printed."""
    vals = {}
    for name in ((".env", ".env.prod") if INCLUDE_PROD else (".env",)):
        path = os.path.join(BACKEND, name)
        if not os.path.exists(path):
            continue
        for line in open(path, encoding="utf-8", errors="replace"):
            m = re.match(r"\s*([A-Z_]+)\s*=\s*(.*?)\s*$", line)
            if not m:
                continue
            key, val = m.group(1), m.group(2).strip('"').strip("'")
            if key in ("CDSE_CLIENT_ID", "CDSE_CLIENT_SECRET", "JWT_SECRET_KEY", "RESEND_API_KEY") and len(val) >= 8:
                vals[f"{name}:{key}"] = val
            if key in ("DATABASE_URL", "PROD_DATABASE_URL"):
                try:
                    pw = make_url(val.replace("postgres://", "postgresql://", 1)).password
                except Exception:  # noqa: BLE001
                    pw = None
                if pw and len(pw) >= 8:
                    vals[f"{name}:{key} password"] = pw
    return vals


class Ctx:
    """Shared fixtures: test client, temporary accounts, their tokens."""

    def __init__(self):
        self.client = app.test_client()
        self.users, self.tokens, self.ids = {}, {}, {}

    def q(self, sql, **p):
        return db.session.execute(text(sql), p).scalar()

    def setup(self):
        role = {r.role_name: r.role_id for r in db.session.execute(text("SELECT role_id, role_name FROM roles"))}
        self.muni = {r.municipality_name: r.municipality_id for r in db.session.execute(
            text("SELECT municipality_id, municipality_name FROM municipalities"))}
        plan = {
            "zz_sec_admin": ("administrator", None),
            "zz_sec_tech": ("rice_technician", CITY_A),
            "zz_sec_nocity": ("agriculturist", None),
        }
        for uname, (r, city) in plan.items():
            pw = secrets.token_urlsafe(18)
            db.session.execute(text("DELETE FROM users WHERE username = :u"), {"u": uname})
            uid = db.session.execute(text(
                "INSERT INTO users (username, password_hash, full_name, status, role_id, municipality_id) "
                "VALUES (:u, :h, 'Security test account', 'Active', :r, :m) RETURNING user_id"),
                {"u": uname, "h": generate_password_hash(pw), "r": role[r],
                 "m": self.muni[city] if city else None}).scalar()
            self.users[uname], self.ids[uname] = pw, uid
        db.session.commit()
        for uname, pw in self.users.items():
            r = self.client.post("/api/auth/login", json={"username": uname, "password": pw})
            self.tokens[uname] = r.get_json()["token"]

    def teardown(self):
        db.session.rollback()
        ids = list(self.ids.values())
        db.session.execute(text(
            "DELETE FROM municipality_yield_records WHERE source = :s"), {"s": MARK})
        db.session.execute(text(
            "DELETE FROM seasons s WHERE s.year = :y "
            "AND NOT EXISTS (SELECT 1 FROM municipality_yield_records r WHERE r.season_id = s.season_id) "
            "AND NOT EXISTS (SELECT 1 FROM municipality_predictions p WHERE p.season_id = s.season_id) "
            "AND NOT EXISTS (SELECT 1 FROM barangay_yield b WHERE b.season_id = s.season_id) "
            "AND NOT EXISTS (SELECT 1 FROM predictions p WHERE p.season_id = s.season_id) "
            "AND NOT EXISTS (SELECT 1 FROM yield_records y WHERE y.season_id = s.season_id)"),
            {"y": TEST_YEAR})
        if ids:
            db.session.execute(text("DELETE FROM yield_import_log WHERE user_id = ANY(:ids)"), {"ids": ids})
            db.session.execute(text("DELETE FROM users WHERE user_id = ANY(:ids)"), {"ids": ids})
        db.session.commit()

    def imp(self, user, csv_text, dry_run=True, token=None, source="security test"):
        headers = {}
        tok = token if token is not None else (self.tokens[user] if user else None)
        if tok:
            headers["Authorization"] = f"Bearer {tok}"
        r = self.client.post("/api/yield/import", headers=headers,
                             json={"csv": csv_text, "level": "municipality",
                                   "dry_run": dry_run, "source": source})
        return r.status_code, (r.get_json(silent=True) or {})

    def counts(self):
        return tuple(self.q(f"SELECT COUNT(*) FROM {t}") for t in
                     ("users", "seasons", "municipality_yield_records", "barangay_yield", "municipalities"))


HEAD = "municipality,year,season,yield\n"


# ------------------------------------------------------------------ the cases
def a1(c):
    tracked = set(git("ls-files").stdout.split())
    bad = [f for f in tracked if os.path.basename(f) in (".env", ".env.prod", ".env.local")]
    ignored = all(git("check-ignore", "-q", p).returncode == 0 for p in ("backend/.env", "backend/.env.prod"))
    return (not bad and ignored,
            f"{len(bad)} credential files tracked; backend/.env and .env.prod ignored: {ignored}")


def a2(c):
    vals = secret_values()
    hits = []
    for label, val in vals.items():
        if git("grep", "-q", "-F", "-e", val).returncode == 0:
            hits.append(label)
    return (bool(vals) and not hits,
            f"{len(vals)} live secret values searched for in every tracked file: {len(hits)} found")


def a3(c):
    vals = secret_values()
    hits = []
    for label, val in vals.items():
        if git("log", "--all", "--oneline", "-S", val).stdout.strip():
            hits.append(label)
    added = git("log", "--all", "--diff-filter=A", "--format=%h", "--",
                "backend/.env", "backend/.env.prod", ".env").stdout.strip()
    n = git("rev-list", "--all", "--count").stdout.strip()
    return (bool(vals) and not hits and not added,
            f"{n} commits on all branches: {len(hits)} of {len(vals)} secret values ever committed; "
            f".env files ever committed: {'yes' if added else 'none'}")


def _start_with(secret):
    env = dict(os.environ, JWT_SECRET_KEY=secret)
    return subprocess.run([sys.executable, "-c", "import app"], cwd=BACKEND, env=env,
                          capture_output=True, text=True)


def a4(c):
    r = _start_with("")
    return (r.returncode != 0 and "JWT_SECRET_KEY is not set" in r.stderr,
            "application refused to start (RuntimeError: JWT_SECRET_KEY is not set)"
            if r.returncode != 0 else "application started")


def a5(c):
    r = _start_with(OLD_PUBLIC_SECRET)
    return (r.returncode != 0, "application refused to start" if r.returncode != 0 else "application started")


def b1(c):
    urls = set()
    for root in (BACKEND, HERE):
        for f in os.listdir(root):
            if f.endswith(".py") and f != os.path.basename(__file__):
                urls |= set(re.findall(r"https?://[^\s\"'<>)]+", open(os.path.join(root, f), encoding="utf-8").read()))
    plain = sorted(u for u in urls if u.startswith("http://") and "localhost" not in u and "127.0.0.1" not in u)
    apis = sorted(u for u in urls if "open-meteo" in u or "copernicus" in u)
    return (not plain and all(u.startswith("https://") for u in apis),
            f"{len(urls)} URLs in backend code; non-local plain-http URLs: {len(plain)}; "
            f"Open-Meteo and Copernicus endpoints all https: {all(u.startswith('https://') for u in apis)}")


def b2(c):
    remote = config._engine_options("postgresql+psycopg://u:p@db.example.supabase.com:5432/postgres")
    ok = remote.get("connect_args", {}).get("sslmode") == "require"
    return ok, f"remote database URL -> connection options {remote.get('connect_args')}"


def c1(c):
    code, body = c.imp(None, HEAD + f"{CITY_A},{TEST_YEAR},Dry,4.2\n")
    return code == 401, f"HTTP {code}; nothing imported"


def c2(c):
    # Change the payload (claim to be user 1, an administrator) but keep the signature.
    h, p, s = c.tokens["zz_sec_tech"].split(".")
    claims = json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))
    claims.update(sub=str(c.ids["zz_sec_admin"]), role="administrator", municipality=None)
    p2 = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    code, _ = c.imp(None, HEAD + f"{CITY_B},{TEST_YEAR},Dry,4.2\n", token=f"{h}.{p2}.{s}")
    return code in (401, 422), f"HTTP {code}; token rejected (signature does not match)"


def c3(c):
    import warnings
    import jwt as pyjwt
    claims = pyjwt.decode(c.tokens["zz_sec_admin"], options={"verify_signature": False})
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # PyJWT warns that this old secret is too short - it is
        forged = pyjwt.encode(claims, OLD_PUBLIC_SECRET, algorithm="HS256")
    code, _ = c.imp(None, HEAD + f"{CITY_B},{TEST_YEAR},Dry,4.2\n", token=forged)
    return code in (401, 422), f"HTTP {code}; token rejected"


def c4(c):
    code, body = c.imp("zz_sec_tech", HEAD + f"{CITY_B},{TEST_YEAR},Dry,4.2\n")
    err = (body.get("errors") or [{}])[0].get("error", "")
    return (code == 200 and body.get("inserted") == 0 and body.get("skipped") == 1 and "only import" in err,
            f"HTTP {code}; inserted {body.get('inserted')}, skipped {body.get('skipped')}: \"{err}\"")


def c5(c):
    code, body = c.imp("zz_sec_tech", HEAD + f"{CITY_A},{TEST_YEAR},Dry,4.2\n")
    return (code == 200 and body.get("inserted") == 1 and body.get("skipped") == 0,
            f"HTTP {code}; row accepted (inserted {body.get('inserted')}, skipped {body.get('skipped')}, dry run)")


def c6(c):
    # Token was issued while assigned to CITY_A; reassign the account, reuse the old token.
    db.session.execute(text("UPDATE users SET municipality_id = :m WHERE user_id = :u"),
                       {"m": c.muni[CITY_B], "u": c.ids["zz_sec_tech"]})
    db.session.commit()
    try:
        code, body = c.imp("zz_sec_tech", HEAD + f"{CITY_A},{TEST_YEAR},Dry,4.2\n")
    finally:
        db.session.rollback()
        db.session.execute(text("UPDATE users SET municipality_id = :m WHERE user_id = :u"),
                           {"m": c.muni[CITY_A], "u": c.ids["zz_sec_tech"]})
        db.session.commit()
    return (code == 200 and body.get("inserted") == 0 and body.get("skipped") == 1,
            f"HTTP {code}; inserted {body.get('inserted')}, skipped {body.get('skipped')} "
            "(city read from the database, not from the token)")


def c7(c):
    code, body = c.imp("zz_sec_nocity", HEAD + f"{CITY_A},{TEST_YEAR},Dry,4.2\n")
    return code == 403, f"HTTP {code}: \"{body.get('error', '')[:60]}\""


def c8(c):
    uid = c.ids["zz_sec_nocity"]
    db.session.execute(text("DELETE FROM users WHERE user_id = :u"), {"u": uid})
    db.session.commit()
    code, body = c.imp("zz_sec_nocity", HEAD + f"{CITY_A},{TEST_YEAR},Dry,4.2\n")
    return code == 401, f"HTTP {code}: \"{body.get('error', '')}\""


def d1(c):
    bad = [
        (f"{CITY_A},{TEST_YEAR},Dry,abc", "yield is not a number"),
        (f"{CITY_A},{TEST_YEAR},Dry,-3", "negative yield"),
        (f"{CITY_A},{TEST_YEAR},Dry,0", "zero yield"),
        (f"{CITY_A},{TEST_YEAR},Dry,250", "yield above 20 mt/ha"),
        (f"{CITY_A},1850,Dry,4.2", "year out of range"),
        (f"{CITY_A},{TEST_YEAR},Summer,4.2", "unknown season"),
        (f"Atlantis,{TEST_YEAR},Dry,4.2", "unknown municipality"),
        (f"{CITY_A},,Dry,4.2", "missing year"),
    ]
    before = c.counts()
    code, body = c.imp("zz_sec_admin", HEAD + "\n".join(r for r, _ in bad) + "\n", dry_run=False,
                       source=MARK)
    same = c.counts() == before
    return (code == 200 and body.get("inserted") == 0 and body.get("updated") == 0
            and body.get("skipped") == len(bad) and same,
            f"{body.get('skipped')} of {len(bad)} bad rows rejected with a reason each; "
            f"{body.get('inserted')} written; table row counts unchanged: {same}")


def d2(c):
    hostile = [
        f"\"{CITY_A}'; DROP TABLE municipality_yield_records; --\",{TEST_YEAR},Dry,4.2",
        f"{CITY_A},\"{TEST_YEAR}; DELETE FROM users\",Dry,4.2",
        f"{CITY_A},{TEST_YEAR},\"Dry' OR '1'='1\",4.2",
        f"{CITY_A},{TEST_YEAR},Dry,\"4.2); UPDATE users SET role_id = 1; --\"",
    ]
    before = c.counts()
    code, body = c.imp("zz_sec_admin", HEAD + "\n".join(hostile) + "\n", dry_run=False, source=MARK)
    same = c.counts() == before
    return (code == 200 and body.get("inserted") == 0 and body.get("skipped") == len(hostile) and same,
            f"{body.get('skipped')} of {len(hostile)} injection rows treated as invalid data and rejected; "
            f"all tables intact, row counts unchanged: {same}")


def d3(c):
    r = c.client.post("/api/auth/login", json={"username": "' OR '1'='1' --", "password": "' OR '1'='1"})
    return r.status_code == 401, f"HTTP {r.status_code}; no token issued"


def d4(c):
    before = c.counts()
    r1 = c.client.get("/api/yield/municipalities", query_string={"year": "2025", "season": "Dry' OR '1'='1"})
    r2 = c.client.get("/api/features/municipalities",
                      query_string={"metric": "ndvi_mean; DROP TABLE users", "year": "2025", "season": "Dry"})
    n1 = len((r1.get_json(silent=True) or {}).get("records", []))
    same = c.counts() == before
    return (n1 == 0 and r2.status_code == 400 and same,
            f"yield query returned {n1} records (HTTP {r1.status_code}); metric not on the allowed list "
            f"-> HTTP {r2.status_code}; tables intact: {same}")


def d5(c):
    row = HEAD + f"{CITY_A},{TEST_YEAR},Dry,4.2\n"
    _, first = c.imp("zz_sec_tech", row, dry_run=False, source=MARK)
    _, second = c.imp("zz_sec_tech", row, dry_run=False, source=MARK)
    n = c.q("SELECT COUNT(*) FROM municipality_yield_records r JOIN seasons s ON s.season_id = r.season_id "
            "WHERE s.year = :y AND r.municipality_id = :m", y=TEST_YEAR, m=c.muni[CITY_A])
    return (first.get("inserted") == 1 and second.get("inserted") == 0 and second.get("updated") == 1 and n == 1,
            f"first upload inserted {first.get('inserted')}; second inserted {second.get('inserted')}, "
            f"updated {second.get('updated')}; rows stored for that city-season: {n}")


def d6(c):
    dups = sum(c.q(f"SELECT COUNT(*) FROM (SELECT 1 FROM {t} GROUP BY {key}, year, month "
                   "HAVING COUNT(*) > 1) x")
               for t, key in (("weather_monthly", "municipality_id"), ("satellite_monthly", "municipality_id"),
                              ("weather_monthly_barangay", "barangay_id"),
                              ("satellite_monthly_barangay", "barangay_id")))
    runs = c.q("SELECT COUNT(*) FROM pipeline_runs WHERE status = 'ok' AND mode = 'incremental'")
    muni = c.q("SELECT COUNT(*) FROM weather_monthly") + c.q("SELECT COUNT(*) FROM satellite_monthly")
    brgy = (c.q("SELECT COUNT(*) FROM weather_monthly_barangay")
            + c.q("SELECT COUNT(*) FROM satellite_monthly_barangay"))
    return (dups == 0 and runs >= 2,
            f"after {runs} incremental runs: {muni} municipality and {brgy} barangay feature rows, "
            f"{dups} duplicated area-months")


def e1(c):
    rows = db.session.execute(text(
        "SELECT username, role, municipality_scope, level, rows_inserted, rows_updated, rows_skipped "
        "FROM yield_import_log WHERE user_id = :u ORDER BY import_id"), {"u": c.ids["zz_sec_tech"]}).all()
    ok = (len(rows) == 2 and rows[0].username == "zz_sec_tech" and rows[0].role == "rice_technician"
          and rows[0].municipality_scope == CITY_A and rows[0].rows_inserted == 1 and rows[1].rows_updated == 1)
    return ok, (f"{len(rows)} log rows for the 2 uploads: user {rows[0].username}, role {rows[0].role}, "
                f"scope {rows[0].municipality_scope}, with timestamp and row counts" if rows else "no log rows")


def e2(c):
    before = c.q("SELECT COUNT(*) FROM yield_import_log")
    n_before = c.counts()
    c.imp("zz_sec_tech", HEAD + f"{CITY_A},{TEST_YEAR + 1},Dry,4.2\n", dry_run=True)
    same = c.counts() == n_before and c.q("SELECT COUNT(*) FROM yield_import_log") == before
    return same, f"preview stored nothing and logged nothing: {same}"


def e3(c):
    r = db.session.execute(text(
        "SELECT run_id, triggered_by, mode, status, finished_at, stages, processing_units, db_encrypted "
        "FROM pipeline_runs ORDER BY run_id DESC LIMIT 1")).first()
    total = c.q("SELECT COUNT(*) FROM pipeline_runs")
    ok = bool(r and r.finished_at and r.stages and r.status in ("ok", "partial", "failed"))
    return ok, (f"{total} runs on record; latest: run #{r.run_id}, {r.mode}, started by {r.triggered_by}, "
                f"status {r.status}, {len(r.stages)} stages timed, "
                + (f"{r.processing_units} processing units" if r.processing_units is not None
                   else "no data fetched")
                if r else "no runs on record")


CASES = [
    ("A. Credential confidentiality", [
        ("ST-01", "Credential files are kept out of version control",
         "No .env file tracked; both are git-ignored", a1),
        ("ST-02", "Search every tracked file for the live secret values",
         "No live secret appears in any file", a2),
        ("ST-03", "Search the whole commit history for the live secret values",
         "No live secret was ever committed", a3),
        ("ST-04", "Start the API with no token-signing secret",
         "The API refuses to start", a4),
        ("ST-05", "Start the API with the old published placeholder secret",
         "The API refuses to start", a5),
    ]),
    ("B. Protected transport", [
        ("ST-06", "Inspect every external address the pipeline and API call",
         "All use HTTPS", b1),
        ("ST-07", "Configure a database that is not on the local machine",
         "Connection requires TLS (sslmode=require)", b2),
    ]),
    ("C. Controlled write access", [
        ("ST-08", "Upload yields without logging in", "Rejected (401)", c1),
        ("ST-09", "Edit a technician's token to claim administrator", "Rejected (signature check)", c2),
        ("ST-10", "Forge an administrator token signed with the old published secret",
         "Rejected", c3),
        ("ST-11", f"Technician of {CITY_A} uploads a row for {CITY_B}",
         "Row skipped with a reason; nothing written", c4),
        ("ST-12", f"Technician of {CITY_A} uploads a row for {CITY_A}",
         "Row accepted", c5),
        ("ST-13", "Reassign the technician to another city, reuse the old token",
         "Old city refused (scope read from the database)", c6),
        ("ST-14", "Non-administrator account with no assigned city uploads", "Rejected (403)", c7),
        ("ST-15", "Delete an account, reuse its still-valid token", "Rejected (401)", c8),
    ]),
    ("D. Data integrity", [
        ("ST-16", "Upload eight malformed or out-of-range rows",
         "Every row rejected with a reason; nothing written", d1),
        ("ST-17", "Upload rows carrying SQL injection text in each column",
         "Treated as invalid data; no table altered", d2),
        ("ST-18", "Log in with SQL injection text as the username", "Rejected (401)", d3),
        ("ST-19", "Send SQL injection text in public query parameters",
         "No extra data returned; no table altered", d4),
        ("ST-20", "Upload the same row twice", "Stored once (second upload updates)", d5),
        ("ST-21", "Re-run the pipeline over months already loaded",
         "No duplicated area-month, municipality or barangay", d6),
    ]),
    ("E. Traceability", [
        ("ST-22", "Check the import log after the two uploads of ST-20",
         "Each upload logged with user, role, city and counts", e1),
        ("ST-23", "Preview an upload (dry run)", "Nothing stored, nothing logged", e2),
        ("ST-24", "Check the pipeline run log", "Each run logged with trigger, stages and result", e3),
    ]),
]


def main():
    global INCLUDE_PROD
    INCLUDE_PROD = "--include-prod" in sys.argv[1:]
    host = make_url(app.config["SQLALCHEMY_DATABASE_URI"]).host or ""
    if host not in ("localhost", "127.0.0.1", "::1", ""):
        sys.exit(f"ERROR: the database is on {host}. These tests only run against a local database.")

    lines = []

    def p(s=""):
        lines.append(s)
        print(s)

    p("=" * 78)
    p(" AgriKA-GIS DATA PIPELINE - SECURITY TEST REPORT")
    p(f" run {datetime.now().isoformat(timespec='seconds')} | local database | commit "
      f"{git('rev-parse', '--short', 'HEAD').stdout.strip()}")
    p("=" * 78)

    passed = total = 0
    with app.app_context():
        ctx = Ctx()
        try:
            ctx.setup()
            for group, cases in CASES:
                p(f"\n{group}")
                for cid, title, expected, fn in cases:
                    try:
                        ok, actual = fn(ctx)
                    except Exception as e:  # noqa: BLE001
                        db.session.rollback()
                        ok, actual = False, f"ERROR {type(e).__name__}: {e}"
                    total += 1
                    passed += bool(ok)
                    p(f"  {cid}  {'PASS' if ok else 'FAIL'}  {title}")
                    p(f"         expected: {expected}")
                    p(f"         actual:   {actual}")
        finally:
            ctx.teardown()
            left = ctx.q("SELECT COUNT(*) FROM users WHERE username LIKE 'zz_sec_%'")
            p(f"\ncleanup: temporary accounts remaining: {left}; "
              f"test rows remaining: {ctx.q('SELECT COUNT(*) FROM municipality_yield_records WHERE source = :s', s=MARK)}")

    p("\n" + "=" * 78)
    p(f" RESULT: {passed}/{total} passed")
    p("=" * 78)
    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"\nsaved -> {REPORT_PATH}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
