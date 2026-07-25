#!/usr/bin/env python3
"""Verify the invariants in BRIEF.md. Run after every change; exits non-zero on failure."""
import pathlib
import re
import sys

SITE = pathlib.Path(__file__).parent / "site"
PAGES = ["index.html", "hours/index.html", "simple/index.html",
         "team/index.html", "crew/index.html"]
fails = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not ok:
        fails.append(name)


docs = {p: (SITE / p).read_text() for p in PAGES}

check(f"all {len(PAGES)} pages present", all((SITE / p).exists() for p in PAGES))
check("pure ASCII", all(all(ord(c) < 128 for c in d) for d in docs.values()))
check("viewport meta on every page", all('name="viewport"' in d for d in docs.values()))
check("noindex on every page", all("noindex" in d for d in docs.values()))
check("robots.txt disallows", "Disallow: /" in (SITE / "robots.txt").read_text())
check("no external assets",
      not any(re.search(r'(?:src|href)="https?://[^"]+\.(?:js|css|woff2?)', d) for d in docs.values()))
check("no absolute asset paths", not any(re.search(r'(?:src|srcset)="/', d) for d in docs.values()))
check("no source comments leaked",
      not any(re.search(r"/\*.*?\*/|<!--.*?-->", d, re.S) for d in docs.values()))
for p, d in docs.items():
    o, c = len(re.findall(r"<div\b", d)), len(re.findall(r"</div>", d))
    check(f"div tags balanced in {p}", o == c, f"{o} open / {c} close")

# every referenced image must exist on disk
for p, d in docs.items():
    for ref in set(re.findall(r'(?:src|srcset)="([^"]+\.png)"', d)):
        check(f"image exists: {ref} (from {p})", ((SITE / p).parent / ref).resolve().exists())

# the shared chrome must be identical, or the A/B/C test is comparing designs
def parts(d):
    return (d[d.index("<nav>"):d.index("</section>", d.index('<section id="how">'))],
            d[d.index("<footer>"):],
            d[d.index("<style>"):d.index("</style>")])


variants = PAGES[1:]
v = [parts(docs[p]) for p in variants]
for i, name in enumerate(("shared chrome (nav..how)", "footer", "stylesheet")):
    distinct = {x[i] for x in v}
    ok = len(distinct) == 1
    detail = ""
    if not ok:
        # name the odd one out rather than just failing
        groups = {}
        for pg, x in zip(variants, v):
            groups.setdefault(x[i], []).append(pg)
        detail = " | ".join(",".join(g) for g in groups.values())
    check(f"{name} identical across all {len(variants)} variants", ok, detail)

print(f"\n{len(fails)} failure(s)" + (": " + ", ".join(fails) if fails else ""))
sys.exit(1 if fails else 0)
