#!/usr/bin/env python3
"""Generate a null-safe Dart model (fromJson / toJson / copyWith) from a JSON sample.

Replaces `get generate model`, which crashes in get_cli 1.9.1 on Dart 3
projects ("Null check operator used on a null value" in nullSafeSupport).

Usage:
    python json_to_model.py <sample.json> <ClassName> [--project .] [--out lib/app/data/models]
                            [--nullable field1,field2] [--stdout]

Rules:
  * Nested objects become their own classes (named from the key, PascalCase).
  * Lists of objects become List<Child>; lists of primitives List<T>.
  * int vs double comes from the sample; numbers parse through `num` so an API
    sending 4 instead of 4.0 still works.
  * A field whose sample value is null, or that is listed in --nullable, is
    nullable. Everything else is required.
  * Keys are converted to lowerCamelCase field names; the original key is kept
    for JSON.
Only the Python standard library is used.
"""

from __future__ import annotations

import argparse
import json
import keyword
import re
import sys
from pathlib import Path

DART_RESERVED = {
    "abstract", "as", "assert", "async", "await", "break", "case", "catch", "class",
    "const", "continue", "default", "do", "dynamic", "else", "enum", "export", "extends",
    "external", "factory", "false", "final", "finally", "for", "get", "if", "implements",
    "import", "in", "is", "late", "library", "new", "null", "operator", "part", "required",
    "rethrow", "return", "set", "static", "super", "switch", "this", "throw", "true", "try",
    "typedef", "var", "void", "while", "with", "yield",
}


def camel(key: str) -> str:
    parts = [p for p in re.split(r"[^A-Za-z0-9]+|(?<=[a-z0-9])(?=[A-Z])", key) if p]
    if not parts:
        return "field"
    name = parts[0].lower() + "".join(p[:1].upper() + p[1:].lower() for p in parts[1:])
    if name[0].isdigit():
        name = "f" + name
    if name in DART_RESERVED or keyword.iskeyword(name):
        name += "Value"
    return name


def pascal(key: str) -> str:
    c = camel(key)
    return c[0].upper() + c[1:]


def singular(name: str) -> str:
    if name.endswith("ies"):
        return name[:-3] + "y"
    if name.endswith("s") and not name.endswith("ss"):
        return name[:-1]
    return name


class Field:
    def __init__(self, key: str, dart_type: str, nullable: bool, kind: str, child: str | None = None):
        self.key = key
        self.name = camel(key)
        self.type = dart_type
        self.nullable = nullable
        self.kind = kind  # prim | int | double | obj | list_prim | list_obj | dynamic
        self.child = child

    @property
    def full_type(self) -> str:
        if self.type == "dynamic":
            return "dynamic"
        return self.type + ("?" if self.nullable else "")


class Generator:
    def __init__(self, nullable: set[str]):
        self.classes: dict[str, list[Field]] = {}
        self.nullable = nullable

    def visit(self, class_name: str, data: dict) -> None:
        if class_name in self.classes:
            return
        self.classes[class_name] = []  # reserve name (handles recursion)
        fields: list[Field] = []
        for key, value in data.items():
            nullable = value is None or key in self.nullable
            fields.append(self.field_for(key, value, nullable))
        self.classes[class_name] = fields

    def field_for(self, key: str, value, nullable: bool) -> Field:
        if isinstance(value, bool):
            return Field(key, "bool", nullable, "prim")
        if isinstance(value, int):
            return Field(key, "int", nullable, "int")
        if isinstance(value, float):
            return Field(key, "double", nullable, "double")
        if isinstance(value, str):
            return Field(key, "String", nullable, "prim")
        if isinstance(value, dict):
            child = pascal(key)
            self.visit(child, value)
            return Field(key, child, nullable, "obj", child)
        if isinstance(value, list):
            first = next((v for v in value if v is not None), None)
            if isinstance(first, dict):
                child = pascal(singular(key))
                merged: dict = {}
                for item in value:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            merged.setdefault(k, v)
                self.visit(child, merged)
                return Field(key, f"List<{child}>", nullable, "list_obj", child)
            inner = {bool: "bool", int: "int", float: "double", str: "String"}.get(type(first), "dynamic")
            if inner == "int" and any(isinstance(v, float) for v in value):
                inner = "double"
            return Field(key, f"List<{inner}>", nullable, "list_prim", inner)
        return Field(key, "dynamic", True, "dynamic")

    # ------------------------------------------------------------------ #

    def from_json_expr(self, f: Field) -> str:
        src = f"json['{f.key}']"
        q = "?" if f.nullable else ""
        if f.kind == "int":
            return f"({src} as num{q}){q}.toInt()"
        if f.kind == "double":
            return f"({src} as num{q}){q}.toDouble()"
        if f.kind == "prim":
            return f"{src} as {f.full_type}"
        if f.kind == "obj":
            expr = f"{f.child}.fromJson({src} as Map<String, dynamic>)"
            return f"{src} == null ? null : {expr}" if f.nullable else expr
        if f.kind == "list_obj":
            expr = (f"({src} as List<dynamic>)\n            .map((e) => {f.child}.fromJson(e as Map<String, dynamic>))\n            .toList()")
            return f"{src} == null ? null : {expr}" if f.nullable else expr
        if f.kind == "list_prim":
            if f.child in ("int", "double"):
                conv = "toInt" if f.child == "int" else "toDouble"
                expr = f"({src} as List<dynamic>).map((e) => (e as num).{conv}()).toList()"
            elif f.child == "dynamic":
                expr = f"List<dynamic>.from({src} as List<dynamic>)"
            else:
                expr = f"List<{f.child}>.from({src} as List<dynamic>)"
            return f"{src} == null ? null : {expr}" if f.nullable else expr
        return src

    def to_json_expr(self, f: Field) -> str:
        q = "?" if f.nullable else ""
        if f.kind == "obj":
            return f"{f.name}{q}.toJson()"
        if f.kind == "list_obj":
            return f"{f.name}{q}.map((e) => e.toJson()).toList()"
        return f.name

    def render_class(self, name: str, fields: list[Field]) -> str:
        out = [f"class {name} {{"]
        for f in fields:
            out.append(f"  final {f.full_type} {f.name};")
        out.append("")
        if fields:
            out.append(f"  const {name}({{")
            for f in fields:
                out.append(f"    {'' if f.nullable else 'required '}this.{f.name},")
            out.append("  });")
        else:
            out.append(f"  const {name}();")
        out.append("")
        out.append(f"  factory {name}.fromJson(Map<String, dynamic> json) => {name}(")
        for f in fields:
            out.append(f"        {f.name}: {self.from_json_expr(f)},")
        out.append("      );")
        out.append("")
        out.append("  Map<String, dynamic> toJson() => {")
        for f in fields:
            out.append(f"        '{f.key}': {self.to_json_expr(f)},")
        out.append("      };")
        if fields:
            out.append("")
            out.append(f"  {name} copyWith({{")
            for f in fields:
                out.append(f"    {'dynamic' if f.type == 'dynamic' else f.type + '?'} {f.name},")
            out.append("  }) {")
            out.append(f"    return {name}(")
            for f in fields:
                out.append(f"      {f.name}: {f.name} ?? this.{f.name},")
            out.append("    );")
            out.append("  }")
        out.append("}")
        return "\n".join(out)

    def render(self) -> str:
        header = (
            "// Generated by flutter-getx skill scripts/json_to_model.py.\n"
            "// Edit freely; re-running the script overwrites this file only with --force.\n"
        )
        return header + "\n" + "\n\n".join(self.render_class(n, f) for n, f in self.classes.items()) + "\n"


def snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sample", help="JSON file with one representative object (or a list of them)")
    parser.add_argument("class_name", help="root class name, e.g. Product")
    parser.add_argument("--project", default=".", help="Flutter project root (default: cwd)")
    parser.add_argument("--out", default="lib/app/data/models", help="output dir relative to project")
    parser.add_argument("--nullable", default="", help="comma-separated JSON keys to force nullable")
    parser.add_argument("--stdout", action="store_true", help="print instead of writing a file")
    parser.add_argument("--force", action="store_true", help="overwrite an existing model file")
    args = parser.parse_args(argv)

    data = json.loads(Path(args.sample).read_text(encoding="utf-8"))
    if isinstance(data, list):
        merged: dict = {}
        for item in data:
            if isinstance(item, dict):
                for k, v in item.items():
                    merged.setdefault(k, v)
        data = merged
    if not isinstance(data, dict):
        sys.exit("error: sample must be a JSON object or a list of objects")

    root = pascal(args.class_name) if not re.fullmatch(r"[A-Z][A-Za-z0-9]*", args.class_name) else args.class_name
    gen = Generator({k.strip() for k in args.nullable.split(",") if k.strip()})
    gen.visit(root, data)
    code = gen.render()

    if args.stdout:
        sys.stdout.write(code)
        return 0

    base = snake(root)
    filename = base if base.endswith("_model") else f"{base}_model"
    dest = Path(args.project) / args.out / f"{filename}.dart"
    if dest.exists() and not args.force:
        print(f"error: {dest} exists; pass --force to overwrite", file=sys.stderr)
        return 1
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(code, encoding="utf-8")
    print(f"wrote {dest} ({len(gen.classes)} classes: {', '.join(gen.classes)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
