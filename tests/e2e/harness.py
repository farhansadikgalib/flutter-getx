#!/usr/bin/env python3
"""End-to-end QA for the flutter-getx Claude Code plugin.

Runs each /flutter-getx:* command headless with `claude -p` in a fresh copy of
a fixture project, then checks the result with objective checks (files,
flutter analyze, flutter test) instead of trusting Claude's summary.

Prerequisites: Claude Code, Flutter, Python 3.9+, network access, and the
plugin installed, e.g. from a local clone:

    claude plugin marketplace add /path/to/flutter-getx
    claude plugin install flutter-getx@flutter-getx

Usage:
    python3 tests/e2e/harness.py [--work DIR] [--jobs 4] [case_id ...]

Results go to DIR/results.json; each case keeps its project in DIR/runs/<id>.
A full run takes about 30-40 minutes and costs roughly $10-15 in API usage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GETX = ROOT / "skills" / "flutter-getx" / "scripts" / "getx.py"
TOOLS = ["Bash", "Read", "Edit", "Write", "Glob", "Grep", "WebFetch"]
LEGACY_REPO = "https://github.com/farhansadikgalib/Flutter-GetX-with-Basic-Setup"


def sh(cmd: str, cwd: Path, timeout: int = 1200) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout + p.stderr


def read(p: Path) -> str:
    return p.read_text(errors="ignore") if p.exists() else ""


def tree_hash(root: Path) -> str:
    h = hashlib.md5()
    for p in sorted(root.rglob("*")):
        if (p.is_file() and not any(x in p.parts for x in (".dart_tool", "build", ".idea"))
                and p.name != "pubspec.lock" and not p.name.startswith(".qa_")):
            h.update(str(p.relative_to(root)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


# ---- checks: each takes the case dir and returns (ok, evidence) ------------
def exists(*rels):
    def c(d):
        miss = [r for r in rels if not (d / r).exists()]
        return not miss, ("missing: " + ", ".join(miss)) if miss else "all present"
    return c


def contains(rel, pattern, flags=0):
    def c(d):
        ok = bool(re.search(pattern, read(d / rel), flags))
        return ok, f"/{pattern}/ {'found' if ok else 'not found'} in {rel}"
    return c


def absent_in_lib(pattern):
    def c(d):
        hits = [str(p.relative_to(d)) for p in (d / "lib").rglob("*.dart") if re.search(pattern, read(p))]
        return not hits, f"hits: {hits[:4]}" if hits else "none"
    return c


def analyze(root=".", errors_only=False):
    def c(d):
        _, out = sh("flutter analyze", d / root)
        last = out.strip().splitlines()[-1] if out.strip() else ""
        if errors_only:
            errs = [l for l in out.splitlines() if l.strip().startswith("error")]
            return not errs, f"{len(errs)} errors; {last}"
        return "No issues found" in out, last
    return c


def tests(root="."):
    def c(d):
        code, out = sh("flutter test", d / root)
        return code == 0 and "All tests passed" in out, (out.strip().splitlines() or [""])[-1][-120:]
    return c


def mentions(pattern):
    def c(d):
        ok = bool(re.search(pattern, read(d / ".qa_result.txt"), re.I))
        return ok, f"/{pattern}/ {'in' if ok else 'not in'} Claude's reply"
    return c


def unchanged():
    def c(d):
        same = read(d / ".qa_hash").strip() == tree_hash(d)
        return same, "tree unchanged" if same else "files changed"
    return c


def no_new_dirs():
    def c(d):
        dirs = [p.name for p in d.iterdir() if p.is_dir()]
        return not dirs, f"dirs: {dirs}" if dirs else "nothing created"
    return c


def json_differs(rel, key, other):
    def c(d):
        a = json.loads(read(d / rel) or "{}").get(key)
        b = json.loads(read(d / other) or "{}").get(key)
        return bool(a) and a != b, f"{key}: {a!r} vs {b!r}"
    return c


# ---- cases -------------------------------------------------------------------
P = "/flutter-getx:"
CASES = [
    dict(id="create_project", fixture=None,
         prompt=f'{P}create project:demo_app --platforms android,ios --title "Demo App"',
         checks=[exists("demo_app/lib/app/core/base/base_controller.dart", "demo_app/assets/locales/ar_AR.json"),
                 contains("demo_app/lib/main.dart", r"title: 'Demo App'"),
                 contains("demo_app/pubspec.yaml", r"^  hive_ce:", re.M),
                 analyze("demo_app"), tests("demo_app")]),
    dict(id="create_no_args", fixture=None, prompt=f"{P}create", checks=[no_new_dirs()]),
    dict(id="create_typo", fixture="base_app", prompt=f"{P}create pag:cart", track=True,
         checks=[unchanged(), mentions(r"page:cart")]),
    dict(id="create_dry_run", fixture="base_app", prompt=f"{P}create page:cart --dry-run", track=True,
         checks=[unchanged(), mentions(r"cart")]),
    dict(id="create_page", fixture="base_app", prompt=f"{P}create page:settings",
         checks=[contains("lib/app/modules/settings/controllers/settings_controller.dart", r"extends BaseController"),
                 contains("lib/app/routes/app_routes.dart", r"SETTINGS = '/settings'"), analyze(), tests()]),
    dict(id="create_page_nested", fixture="base_app", prompt=f"{P}create page:reviews on home",
         checks=[exists("lib/app/modules/home/reviews/views/reviews_view.dart"),
                 contains("lib/app/routes/app_routes.dart", r"REVIEWS = _Paths\.HOME \+ _Paths\.REVIEWS"), analyze()]),
    dict(id="create_page_exists", fixture="base_app", prompt=f"{P}create page:home", track=True,
         checks=[unchanged(), mentions(r"already exists")]),
    dict(id="create_page_described", fixture="base_app",
         prompt=f"{P}create page:profile showing the saved user's name and email from MyHive, "
                "with a logout button that deletes the user and goes back home",
         checks=[contains("lib/app/modules/profile/controllers/profile_controller.dart", r"MyHive"),
                 contains("lib/app/modules/profile/controllers/profile_controller.dart", r"deleteCurrentUser"),
                 analyze(), tests()]),
    dict(id="create_controller", fixture="base_app", prompt=f"{P}create controller:edit on home",
         checks=[contains("lib/app/modules/home/controllers/edit_controller.dart", r"extends BaseController"),
                 contains("lib/app/modules/home/bindings/home_binding.dart", r"Get\.lazyPut<EditController>"),
                 analyze()]),
    dict(id="create_feature", fixture="base_app",
         prompt=f"{P}create feature:posts with https://jsonplaceholder.typicode.com/posts",
         checks=[exists("lib/app/data/models/post_model.dart", "lib/app/data/remote/post_remote_source.dart",
                        "test/posts_controller_test.dart"),
                 contains("lib/app/modules/posts/views/posts_view.dart", r"MyWidgetsAnimator"),
                 json_differs("assets/locales/ar_AR.json", "posts_title", "assets/locales/en_US.json"),
                 analyze(), tests()]),
    dict(id="create_string", fixture="base_app", prompt=f'{P}create string:welcome_back "Welcome back, @name"',
         checks=[json_differs("assets/locales/ar_AR.json", "welcome_back", "assets/locales/en_US.json"),
                 contains("assets/locales/ar_AR.json", r"@name"),
                 contains("lib/generated/locales.g.dart", r"welcome_back"), analyze()]),
    dict(id="generate_model_hive", fixture="base_app",
         prompt=f"{P}generate model:Customer with https://jsonplaceholder.typicode.com/users/1 --hive",
         checks=[exists("lib/app/data/models/customer_model.dart", "lib/app/data/models/customer_model.g.dart"),
                 contains("lib/app/data/models/customer_model.dart", r"class Address\b"),
                 contains("lib/app/data/models/customer_model.dart", r"@HiveType"),
                 contains("lib/main.dart", r"CustomerAdapter"), analyze(), tests()]),
    dict(id="init_plain", fixture="plain_app", prompt=f"{P}init",
         checks=[exists("lib/app/core/base/base_view.dart", "lib/generated/locales.g.dart"),
                 contains("lib/main.dart", r"GetMaterialApp"), analyze(), tests()]),
    dict(id="install_package", fixture="base_app", prompt=f"{P}install lottie",
         checks=[contains("pubspec.yaml", r"^  lottie: \^\d", re.M), analyze()]),
    dict(id="install_fcm", fixture="base_app", prompt=f"{P}install fcm",
         checks=[contains("pubspec.yaml", r"^  firebase_messaging:", re.M),
                 exists("lib/utils/fcm_helper.dart", "lib/firebase_options.dart"),
                 contains("lib/main.dart", r"FcmHelper\.initFcm"), contains("ios/Podfile", r"platform :ios, '15\.0'"),
                 mentions(r"flutterfire"), analyze(), tests()]),
    dict(id="upgrade_legacy", fixture="legacy_app", prompt=f"{P}upgrade",
         checks=[lambda d: (not re.search(r"^  (hive|hive_flutter|hive_generator):", read(d / "pubspec.yaml"), re.M),
                            "old hive deps removed"),
                 contains("pubspec.yaml", r"^  hive_ce:", re.M), absent_in_lib(r"MaterialStateProperty|\.withOpacity\("),
                 absent_in_lib(r"package:hive/|package:hive_flutter/"), analyze(errors_only=True), tests()]),
    dict(id="doctor_legacy", fixture="legacy_app", prompt=f"{P}doctor", track=True,
         checks=[unchanged(), mentions(r"hive"), mentions(r"getx upgrade|/flutter-getx:upgrade|upgrade")]),
    dict(id="natural_language", fixture=None,
         prompt="I need a new flutter app called notes_app using getx, with dark mode and arabic support. "
                "android and ios only.",
         checks=[exists("notes_app/lib/app/core/base/base_view.dart"), analyze("notes_app"), tests("notes_app")]),
]


# ---- fixtures and runner -----------------------------------------------------
def build_fixtures(fx: Path) -> None:
    fx.mkdir(parents=True, exist_ok=True)
    if not (fx / "base_app").exists():
        code, out = sh(f'python3 "{GETX}" create project:base_app --dir "{fx}"', fx, timeout=1800)
        if code:
            sys.exit(f"fixture base_app failed:\n{out[-2000:]}")
    if not (fx / "plain_app").exists():
        sh("flutter create --org com.example --platforms android,ios plain_app", fx)
    if not (fx / "legacy_app").exists():
        sh(f"git clone -q --depth 1 {LEGACY_REPO} legacy_app && rm -rf legacy_app/.git", fx)


def run_case(case: dict, work: Path) -> dict:
    d = work / "runs" / case["id"]
    shutil.rmtree(d, ignore_errors=True)
    if case.get("fixture"):
        shutil.copytree(work / "fixtures" / case["fixture"], d, symlinks=True)
    else:
        d.mkdir(parents=True)
    if case.get("track"):
        (d / ".qa_hash").write_text(tree_hash(d))
    t0 = time.time()
    cmd = ["claude", "-p", case["prompt"], "--output-format", "json", "--max-turns", "80",
           "--allowedTools", *TOOLS]
    try:
        p = subprocess.run(cmd, cwd=d, capture_output=True, text=True, timeout=1800, stdin=subprocess.DEVNULL)
        data = json.loads(p.stdout) if p.stdout.strip().startswith("{") else {}
    except subprocess.TimeoutExpired:
        data = {"result": "TIMEOUT"}
    (d / ".qa_result.txt").write_text(data.get("result") or "")
    checks = []
    for chk in case["checks"]:
        try:
            ok, ev = chk(d)
        except Exception as exc:  # noqa: BLE001
            ok, ev = False, f"check crashed: {exc}"
        checks.append({"ok": bool(ok), "evidence": ev})
    rec = {"id": case["id"], "prompt": case["prompt"], "seconds": round(time.time() - t0),
           "turns": data.get("num_turns"), "cost": data.get("total_cost_usd"), "checks": checks,
           "result": (data.get("result") or "")[:3000]}
    print(f"[{sum(c['ok'] for c in checks)}/{len(checks)}] {case['id']} ({rec['seconds']}s)", flush=True)
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cases", nargs="*")
    ap.add_argument("--work", default="/tmp/flutter-getx-e2e")
    ap.add_argument("--jobs", type=int, default=4)
    args = ap.parse_args()
    work = Path(args.work).resolve()
    build_fixtures(work / "fixtures")
    todo = [c for c in CASES if not args.cases or c["id"] in args.cases]
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        recs = list(ex.map(lambda c: run_case(c, work), todo))
    out = work / "results.json"
    old = json.loads(out.read_text()) if out.exists() else {}
    old.update({r["id"]: r for r in recs})
    out.write_text(json.dumps(old, indent=2, ensure_ascii=False))
    failed = [(r["id"], c["evidence"]) for r in recs for c in r["checks"] if not c["ok"]]
    cost = sum(r["cost"] or 0 for r in recs)
    print(f"\n{len(recs) - len({f[0] for f in failed})}/{len(recs)} cases passed all checks; cost ${cost:.2f}")
    for cid, ev in failed:
        print(f"  FAIL {cid}: {ev}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
