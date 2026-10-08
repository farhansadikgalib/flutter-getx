#!/usr/bin/env python3
"""getx - get_cli-style commands for Flutter GetX projects.

    getx create project:my_shop
    getx create page:cart [on home]
    getx create controller:edit on profile
    getx create view:edit on profile
    getx create feature:products with https://fakestoreapi.com/products
    getx create string:checkout "Checkout" --ar "الدفع"
    getx generate model:Product with product.json [on shop]
    getx generate locales
    getx init
    getx install lottie | getx install mocktail --dev | getx install fcm
    getx upgrade
    getx doctor
    getx help [verb]

Global flags: --project DIR, --dry-run, --json, --yes, --offline, --no-get-cli.
Exit codes: 0 success, 1 the operation failed, 2 invalid usage.

Run `getx help` for every option. Only the Python standard library is used.
"""

from __future__ import annotations

import difflib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import reporter  # noqa: E402
from reporter import out  # noqa: E402

VERSION = "0.3.0"

# verb -> allowed targets (None: the verb takes no target)
VERBS: dict[str, list[str] | None] = {
    "create": ["project", "page", "controller", "view", "feature", "string"],
    "generate": ["model", "locales"],
    "init": None,
    "install": None,
    "upgrade": None,
    "doctor": None,
    "help": None,
    "version": None,
    "install-cli": None,
}
ALIASES = {"-v": "version", "--version": "version", "-h": "help", "--help": "help", "new": "create"}

# flags: name -> takes a value?
GLOBAL_FLAGS = {"--project": True, "--dry-run": False, "--json": False, "--yes": False, "-y": False,
                "--offline": False, "--no-get-cli": False}
OPTION_FLAGS = {"--org": True, "--platforms": True, "--title": True, "--design-size": True,
                "--nullable": True, "--force": False, "--dev": False, "--firebase": False,
                "--dir": True, "--hive": False}

HELP = {
    "create": """getx create <target>:<name> [on <module>] [with <source>] [options]

  project:<name>           new Flutter app with the GetX pattern, latest packages,
                           generated code; flutter analyze and test run at the end
                           --org com.acme  --platforms android,ios  --title "My App"
                           --design-size 375x812  --dir <parent folder>
  page:<name> [on <m>]     module with binding, controller, view and route
  controller:<name> on <m> controller in module <m>, registered in its binding
  view:<name> on <m>       extra view in module <m> (not routed)
  feature:<name> with <s>  API screen: model, data source, states, view, route, tests
                           <s> is an endpoint URL, a JSON file, or inline JSON
  string:<key> "<text>"    translated string in every locale; --ar "..." --fr "..."

examples:
  getx create project:my_shop --platforms android,ios
  getx create page:cart on home
  getx create controller:edit on profile
  getx create feature:products with https://fakestoreapi.com/products
  getx create string:checkout "Checkout" --ar "الدفع"
""",
    "generate": """getx generate <target> [...]

  model:<ClassName> with <s> [on <m>]   null-safe model (fromJson, toJson, copyWith);
                                        <s> is a JSON file, URL or inline JSON;
                                        on <m> writes it under that module
                                        --nullable a,b  --force
  locales                               lib/generated/locales.g.dart from assets/locales

examples:
  getx generate model:Product with assets/models/product.json
  getx generate model:Customer with https://jsonplaceholder.typicode.com/users/1
  getx generate locales
""",
    "init": """getx init [--title "My App"] [--design-size 375x812]

  Adds the GetX folder pattern to an existing Flutter project. Never overwrites
  edited files; untouched flutter-create starters are replaced.
""",
    "install": """getx install <package> [--dev] | getx install fcm

  <package>   adds the latest stable pub.dev version and runs flutter pub get
  fcm         Firebase Cloud Messaging add-on (packages, helpers, main.dart wiring,
              placeholder firebase_options.dart, iOS Podfile hooks)
""",
    "upgrade": """getx upgrade [--firebase]

  Latest packages, hive -> hive_ce, mechanical API fixes (WidgetStateProperty,
  withValues), build_runner, and an analyzer report of what is left.
""",
    "doctor": """getx doctor [--offline]

  Checks Flutter, Dart, Python, get_cli and pub.dev, then audits the project.
""",
    "install-cli": """getx install-cli [--dir ~/.local/bin]

  Puts a `getx` launcher on your PATH that runs this copy of the skill.
""",
}

USAGE = f"""getx {VERSION} - get_cli-style commands for Flutter GetX projects

usage: getx <verb> [<target>:<name>] [on <module>] [with <source>] [flags]

verbs:
  create     project | page | controller | view | feature | string
  generate   model | locales
  init       add the GetX pattern to an existing Flutter app
  install    <package> | fcm
  upgrade    latest packages and current Flutter APIs
  doctor     toolchain and project health check
  help       getx help <verb>
  install-cli  put `getx` on your PATH

global flags:
  --project <dir>  project root (default: current directory)
  --dry-run        show what would change, write nothing
  --json           print one JSON result object on stdout (progress on stderr)
  --yes, -y        never prompt (getx never needs input once arguments are given)
  --offline        use the dated package snapshot instead of pub.dev
  --no-get-cli     use bundled templates even if get_cli is installed

exit codes: 0 success, 1 operation failed, 2 invalid usage

examples:
  getx create project:my_shop
  getx create page:cart on home
  getx generate model:Product with product.json
  getx install fcm
"""


class UsageError(Exception):
    pass


# --------------------------------------------------------------------------- #
# parsing
# --------------------------------------------------------------------------- #

def snake(text: str) -> str:
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", text.strip())
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return re.sub(r"_+", "_", text)


def suggest(word: str, options: list[str]) -> str | None:
    m = difflib.get_close_matches(word, options, n=1, cutoff=0.6)
    return m[0] if m else None


def parse(argv: list[str]) -> dict:
    flags: dict[str, object] = {}
    lang: dict[str, str] = {}
    words: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in GLOBAL_FLAGS or a in OPTION_FLAGS:
            takes = GLOBAL_FLAGS.get(a, OPTION_FLAGS.get(a))
            if takes:
                if i + 1 >= len(argv):
                    raise UsageError(f"{a} needs a value")
                flags[a] = argv[i + 1]
                i += 2
            else:
                flags["--yes" if a == "-y" else a] = True
                i += 1
            continue
        if re.fullmatch(r"--[a-z]{2}", a):  # --ar "text", --fr "text"
            if i + 1 >= len(argv):
                raise UsageError(f"{a} needs a value")
            lang[a[2:]] = argv[i + 1]
            i += 2
            continue
        if a.startswith("--") and "=" in a:
            k, v = a.split("=", 1)
            if k in GLOBAL_FLAGS or k in OPTION_FLAGS:
                flags[k] = v
                i += 1
                continue
        if a.startswith("-") and a not in ALIASES:
            known = list(GLOBAL_FLAGS) + list(OPTION_FLAGS)
            hint = suggest(a, known)
            raise UsageError(f"unknown option {a}" + (f" (did you mean {hint}?)" if hint else ""))
        words.append(a)
        i += 1

    if not words:
        return {"verb": "help", "flags": flags, "lang": lang, "topic": None}
    verb = ALIASES.get(words[0], words[0])
    if verb not in VERBS:
        hint = suggest(verb, list(VERBS))
        rest = " ".join(shlex.quote(w) for w in words[1:])
        raise UsageError(f"unknown command '{verb}'"
                         + (f". Did you mean: getx {hint} {rest}".rstrip() if hint else ". Run: getx help"))
    cmd = {"verb": verb, "flags": flags, "lang": lang, "target": None, "name": None,
           "on": None, "with": None, "text": [], "topic": None}
    rest = words[1:]
    if verb == "help":
        cmd["topic"] = rest[0] if rest else None
        return cmd
    targets = VERBS[verb]
    if targets is not None:
        if not rest:
            raise UsageError(f"{verb} needs a target: {', '.join(t + ':<name>' for t in targets)}"
                             f" (e.g. getx {verb} {targets[0]}:<name>)")
        head = rest.pop(0)
        target, _, name = head.partition(":")
        if target not in targets:
            hint = suggest(target, targets)
            raise UsageError(f"'{target}' is not a {verb} target ({', '.join(targets)})"
                             + (f". Did you mean: getx {verb} {hint}:{name or '<name>'}" if hint else ""))
        cmd["target"], cmd["name"] = target, name.strip() or None
    # on / with keywords, then free text
    while rest:
        w = rest.pop(0)
        if w in ("on", "with") and rest and cmd[w] is None:
            cmd[w] = rest.pop(0)
        else:
            cmd["text"].append(w)
    return cmd


# --------------------------------------------------------------------------- #
# execution helpers
# --------------------------------------------------------------------------- #

def call(module_name: str, argv: list[str]) -> int:
    import operations
    module = __import__(module_name)
    return operations.call_script(module, argv)


def need_name(cmd: dict, example: str) -> str:
    if not cmd["name"]:
        raise UsageError(f"{cmd['target']} name required (e.g. getx {example})")
    return cmd["name"]


def project_dir(cmd: dict) -> Path:
    return Path(str(cmd["flags"].get("--project", "."))).expanduser().resolve()


def skill_location() -> Path:
    return SCRIPTS


def command_string(argv: list[str]) -> str:
    return "getx " + " ".join(shlex.quote(a) for a in argv if a not in ("--json",))


# --------------------------------------------------------------------------- #
# verbs
# --------------------------------------------------------------------------- #

def do_create(cmd: dict) -> int:
    f, target, project = cmd["flags"], cmd["target"], project_dir(cmd)
    dry = bool(f.get("--dry-run"))
    no_get = ["--no-get-cli"] if f.get("--no-get-cli") else []
    result = reporter.current()

    if target == "project":
        name = snake(need_name(cmd, "create project:my_shop"))
        if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
            raise UsageError(f"'{cmd['name']}' is not a valid Dart package name")
        parent = Path(str(f.get("--dir", project))).expanduser().resolve()
        dest = parent / name
        if dest.exists():
            result.fail(f"{dest} already exists; to add the pattern to it run: getx init --project {dest}")
            return 1
        args = [str(SCRIPTS / "new_project.sh"), name, "--dir", str(parent)]
        for flag in ("--org", "--platforms", "--title", "--design-size"):
            if f.get(flag):
                args += [flag, str(f[flag])]
        if dry:
            out("[dry-run] would run: bash " + " ".join(shlex.quote(a) for a in args))
            result.add_created(str(dest))
            result.data["dry_run"] = True
            return 0
        out(f"==> creating {dest}")
        stream = sys.stderr if reporter.json_mode() else sys.stdout
        p = subprocess.run(["bash", *args], stdout=stream, stderr=stream)
        if p.returncode != 0:
            result.fail("project creation failed; see the output above")
            return 1
        result.add_created(str(dest))
        result.data.update({"project": str(dest), "analyze": "passed", "tests": "passed"})
        result.add_next(f"cd {name}")
        result.add_next("getx create page:<name>")
        return 0

    if target in ("page", "controller", "view"):
        name = snake(need_name(cmd, f"create {target}:cart" + (" on home" if target != "page" else "")))
        args = [name, "--project", str(project), *no_get]
        if target != "page":
            if not cmd["on"]:
                raise UsageError(f"{target} needs a module: getx create {target}:{name} on <module>")
            args += ["--kind", target]
        if cmd["on"]:
            args += ["--on", snake(cmd["on"])]
        if dry:
            args.append("--dry-run")
        code = call("new_module", args)
        if cmd["text"]:
            result.data["note"] = " ".join(cmd["text"])
        return code

    if target == "feature":
        name = need_name(cmd, "create feature:products with https://api.example.com/products")
        if not cmd["with"]:
            raise UsageError(f"feature needs a data source: getx create feature:{snake(name)} with <url|file.json>")
        import operations
        code = operations.create_feature(project, name, cmd["with"], dry, bool(f.get("--no-get-cli")))
        if cmd["text"]:
            result.data["note"] = " ".join(cmd["text"])
        return code

    if target == "string":
        key = snake(need_name(cmd, 'create string:checkout "Checkout"'))
        if not cmd["text"]:
            raise UsageError(f'string needs its English text: getx create string:{key} "Text"')
        args = [key, " ".join(cmd["text"]), "--project", str(project)]
        for code_, text in cmd["lang"].items():
            args += [f"--{code_}", text]
        if dry:
            args.append("--dry-run")
        return call("add_string", args)

    raise UsageError(f"unsupported target {target}")


def do_generate(cmd: dict) -> int:
    f, project = cmd["flags"], project_dir(cmd)
    dry = bool(f.get("--dry-run"))
    result = reporter.current()
    if cmd["target"] == "locales":
        from add_string import find_get
        exe = None if f.get("--no-get-cli") else find_get()
        if exe and not dry:
            import operations
            code, output = operations.run([exe, "generate", "locales", "assets/locales"], project,
                                          "get generate locales assets/locales")
            if code == 0 and (project / "lib/generated/locales.g.dart").exists():
                result.add_modified("lib/generated/locales.g.dart")
                result.data["generator"] = "get_cli"
                return 0
            out("get_cli failed; using the bundled generator")
        result.data["generator"] = "bundled"
        return call("locales", ["--project", str(project)] + (["--dry-run"] if dry else []))

    # model
    cls = need_name(cmd, "generate model:Product with product.json")
    if not cmd["with"]:
        raise UsageError(f"model needs a JSON source: getx generate model:{cls} with <file.json|url>")
    cls = re.sub(r"[^A-Za-z0-9]", "", cls[:1].upper() + cls[1:]) if not re.fullmatch(r"[A-Z][A-Za-z0-9]*", cls) else cls
    import operations
    try:
        data = operations.fetch_json(cmd["with"], project)
    except Exception as exc:  # noqa: BLE001
        result.fail(f"could not load JSON from {cmd['with']}: {exc}")
        return 1
    sample_name = operations.snake(cls)
    sample_name = sample_name[:-6] if sample_name.endswith("_model") else sample_name
    sample = project / "assets/models" / f"{sample_name}.json"
    if not dry:
        sample.parent.mkdir(parents=True, exist_ok=True)
        existed = sample.exists()
        sample.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (result.add_modified if existed else result.add_created)(f"assets/models/{sample.name}")
    out_dir = f"lib/app/modules/{snake(cmd['on'])}/data/models" if cmd["on"] else "lib/app/data/models"
    if cmd["on"] and not (project / "lib/app/modules" / snake(cmd["on"])).exists():
        result.fail(f"module '{snake(cmd['on'])}' not found")
        return 1
    if dry:
        # json_to_model needs a file; use a scratch copy so nothing in the project changes
        import tempfile
        tmp = Path(tempfile.mkdtemp()) / sample.name
        tmp.write_text(json.dumps(data), encoding="utf-8")
        args = [str(tmp), cls, "--project", str(project), "--out", out_dir, "--dry-run"]
    else:
        args = [str(sample), cls, "--project", str(project), "--out", out_dir]
    if f.get("--nullable"):
        args += ["--nullable", str(f["--nullable"])]
    if f.get("--force"):
        args.append("--force")
    code = call("json_to_model", args)
    if code == 0 and f.get("--hive"):
        result.add_next("add @HiveType/@HiveField annotations and a part line, register the adapter in "
                        "main.dart, then run build_runner (references/local-storage.md)")
    return code


def do_install(cmd: dict) -> int:
    import operations
    f, project = cmd["flags"], project_dir(cmd)
    if not cmd["text"]:
        raise UsageError("install needs a package name or `fcm` (e.g. getx install lottie)")
    if len(cmd["text"]) > 1:
        raise UsageError("install takes one package at a time")
    pkg = cmd["text"][0]
    if pkg in ("fcm", "firebase", "push"):
        return operations.install_fcm(project, bool(f.get("--dry-run")), bool(f.get("--offline")))
    return operations.install_package(project, pkg, bool(f.get("--dev")), bool(f.get("--dry-run")),
                                      bool(f.get("--offline")))


def do_install_cli(cmd: dict) -> int:
    result = reporter.current()
    target_dir = Path(str(cmd["flags"].get("--dir", "~/.local/bin"))).expanduser()
    launcher = target_dir / "getx"
    script = (SCRIPTS / "getx.py").resolve()
    body = f'#!/bin/sh\n# getx launcher written by `getx install-cli`\nexec python3 "{script}" "$@"\n'
    if cmd["flags"].get("--dry-run"):
        out(f"[dry-run] would write {launcher} -> {script}")
        result.data["dry_run"] = True
        return 0
    target_dir.mkdir(parents=True, exist_ok=True)
    existed = launcher.exists()
    launcher.write_text(body)
    launcher.chmod(0o755)
    (result.add_modified if existed else result.add_created)(str(launcher))
    out(f"installed {launcher} -> {script}")
    on_path = str(target_dir) in os.environ.get("PATH", "").split(os.pathsep)
    result.data.update({"launcher": str(launcher), "on_path": on_path})
    if not on_path:
        line = f'export PATH="{target_dir}:$PATH"'
        out(f"{target_dir} is not on your PATH. Add this to your shell profile:\n  {line}")
        result.add_next(line)
    return 0


def run_command(cmd: dict, argv: list[str]) -> int:
    verb, f = cmd["verb"], cmd["flags"]
    if verb == "help":
        topic = cmd["topic"]
        topic = ALIASES.get(topic, topic) if topic else None
        if topic and topic not in HELP:
            hint = suggest(topic, list(HELP))
            raise UsageError(f"no help for '{topic}'" + (f"; did you mean `getx help {hint}`?" if hint else ""))
        text = HELP[topic] if topic else USAGE
        if reporter.json_mode():
            reporter.current().data["help"] = text
        else:
            print(text, end="")
        return 0
    if verb == "version":
        if reporter.json_mode():
            reporter.current().data["version"] = VERSION
        else:
            print(f"getx {VERSION} ({SCRIPTS.parent})")
        return 0
    if verb == "create":
        return do_create(cmd)
    if verb == "generate":
        return do_generate(cmd)
    if verb == "install":
        return do_install(cmd)
    if verb == "install-cli":
        return do_install_cli(cmd)
    import operations
    project = project_dir(cmd)
    if verb == "init":
        if cmd["text"]:
            project = Path(cmd["text"][0]).expanduser().resolve()
        return operations.init_project(project, f.get("--title"), f.get("--design-size"),
                                       bool(f.get("--dry-run")), bool(f.get("--offline")))
    if verb == "upgrade":
        return operations.upgrade_project(project, True if f.get("--firebase") else None,
                                          bool(f.get("--dry-run")), bool(f.get("--offline")))
    if verb == "doctor":
        return call("doctor", ["--project", str(project)] + (["--offline"] if f.get("--offline") else []))
    raise UsageError(f"unknown command {verb}")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    json_mode = "--json" in argv
    reporter.set_json(json_mode)
    result = reporter.reset()
    try:
        cmd = parse(argv)
        code = run_command(cmd, argv)
    except UsageError as exc:
        result.fail(str(exc))
        code = 2
        if not json_mode:
            print(f"getx: {exc}", file=sys.stderr)
    except KeyboardInterrupt:
        result.fail("interrupted")
        code = 1
    if code and result.ok:
        result.fail("operation failed; see the output above")
    if not code and not result.ok:
        code = 1
    if json_mode:
        payload = {"command": command_string(argv), **result.to_dict()}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif code == 1 and result.error and not result.error_printed \
            and not result.error.startswith("operation failed"):
        print(f"getx: {result.error}", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
