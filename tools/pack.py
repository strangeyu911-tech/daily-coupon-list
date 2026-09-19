# -*- coding: utf-8 -*-
"""Validate a skill folder against the open-platform rules and zip it.

Usage: python pack.py <skill_dir> <version>
Root of the zip = <skill_dir>, i.e. entries look like `daily-coupon-list/SKILL.md`.
"""
import io
import os
import re
import sys
import zipfile

REQUIRED = [
    "name",
    "display_name",
    "display_name_en",
    "description",
    "description_zh",
    "description_en",
    "category",
    "version",
    "author",
]


def main():
    root = os.path.abspath(sys.argv[1])
    version = sys.argv[2]
    name = os.path.basename(root)

    skill = io.open(os.path.join(root, "SKILL.md"), encoding="utf-8").read()
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", skill, re.S)
    print("frontmatter:", "OK" if m else "MISSING")
    if not m:
        return 1

    problems = []
    seen = {}
    for ln in m.group(1).splitlines():
        if not ln.strip():
            continue
        if ":" not in ln:
            problems.append("no colon: " + ln)
            continue
        k, v = ln.split(":", 1)
        key = k.strip()
        val = v.strip()
        if not v.startswith(" "):
            problems.append("missing space after colon: " + key)
        if val.startswith('"') or val.startswith("'"):
            problems.append("plain scalar starts with a quote (must then be closed): " + key)
        # YAML plain-scalar hazards. The platform's parser reports these as
        # "mapping values are not allowed in this context" and refuses the zip.
        if ": " in val:
            problems.append("plain scalar contains ': ' which YAML reads as a mapping: " + key)
        if val.endswith(":"):
            problems.append("plain scalar ends with ':': " + key)
        if val and val[0] in "\"'[]{}#&*!|>%@`":
            problems.append("plain scalar starts with a YAML indicator: " + key)
        if " #" in val:
            problems.append("plain scalar contains ' #' which YAML reads as a comment: " + key)
        if "\t" in v:
            problems.append("contains tab: " + key)
        seen[key] = val

    for r in REQUIRED:
        if r not in seen:
            problems.append("missing field: " + r)

    print("fields:", ", ".join(seen.keys()))
    print("problems:", problems or "none")

    # Authoritative check: parse the frontmatter with a real YAML parser.
    # The platform runs the same kind of parser and rejects the whole zip with
    # "SKILL.md 格式错误 — frontmatter 无法解析" if this fails.
    try:
        import yaml

        try:
            doc = yaml.safe_load(m.group(1))
            if not isinstance(doc, dict):
                print("yaml parse: FAILED (top level is not a mapping)")
            else:
                bad = [k for k, v in doc.items() if not isinstance(v, str)]
                print("yaml parse: OK  (%d keys, %d non-string)" % (len(doc), len(bad)))
                if bad:
                    print("  non-string values:", bad)
        except Exception as exc:  # noqa: BLE001
            print("yaml parse: FAILED -> %s" % exc)
    except ImportError:
        print("yaml parse: SKIPPED (pyyaml not installed)")

    for k in ("description", "description_zh", "description_en"):
        if k in seen:
            print("  %s len=%d" % (k, len(seen[k])))

    print("\nfiles:")
    depth_max = 0
    for dp, dn, fn in os.walk(root):
        rel = os.path.relpath(dp, root)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        depth_max = max(depth_max, depth)
        for f in fn:
            r2 = os.path.join(rel, f) if rel != "." else f
            print("  depth=%d  %s" % (depth, r2.replace("\\", "/")))
    print("max depth:", depth_max, "(platform expects the SKILL.md at the zip root)")

    out = os.path.join(os.path.dirname(root), "%s-%s.zip" % (name, version))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for dp, dn, fn in os.walk(root):
            for f in fn:
                full = os.path.join(dp, f)
                arc = os.path.join(name, os.path.relpath(full, root)).replace("\\", "/")
                z.write(full, arc)
    print("\nzip: %s (%.1f KB, limit 3072 KB)" % (out, os.path.getsize(out) / 1024.0))
    with zipfile.ZipFile(out) as z:
        for i in z.infolist():
            print("   ", i.filename, i.file_size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
