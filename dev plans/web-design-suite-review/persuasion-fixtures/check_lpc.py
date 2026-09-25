"""Review helper: verify documented claims in landing-page-conversion against the shipped CSS."""
import re, pathlib, sys

wd = pathlib.Path(__file__).parent
ps = (wd / "landing-page-conversion/assets/page-sections.css").read_text(encoding="utf-8")
tokens = (wd / "web-design-studio/assets/starter/styles/tokens.css").read_text(encoding="utf-8")
layout = (wd / "web-design-studio/assets/starter/styles/layout.css").read_text(encoding="utf-8")
base = (wd / "web-design-studio/assets/starter/styles/base.css").read_text(encoding="utf-8")

def strip_comments(s):
    return re.sub(r"/\*.*?\*/", "", s, flags=re.S)

ps_nc = strip_comments(ps)
used = set(re.findall(r"var\(\s*(--[\w-]+)", ps_nc))
declared_tokens = set(re.findall(r"(--[\w-]+)\s*:", strip_comments(tokens)))
declared_local = set(re.findall(r"(--[\w-]+)\s*:", ps_nc))
declared_layout = set(re.findall(r"(--[\w-]+)\s*:", strip_comments(layout)))

from_tokens = sorted(u for u in used if u in declared_tokens)
local = sorted(u for u in used if u in declared_local and u not in declared_tokens)
missing = sorted(u for u in used if u not in declared_tokens and u not in declared_local)
print("unique var() names used:", len(used))
print("resolved in tokens.css:", len(from_tokens))
print("declared locally (sockets):", len(local), "| local declarations total:", len(declared_local))
print("missing:", missing, "(in layout.css:", [m for m in missing if m in declared_layout], ")")

# classes named in SKILL.md / worked-example / page-architecture
docs = ""
for f in ["landing-page-conversion/SKILL.md",
          "landing-page-conversion/references/worked-example.md",
          "landing-page-conversion/references/page-architecture.md",
          "landing-page-conversion/references/copy-patterns.md",
          "landing-page-conversion/references/conversion-audit.md"]:
    docs += (wd / f).read_text(encoding="utf-8")
names = set(re.findall(r"`\.([a-z][\w-]*(?:\.[a-z][\w-]*)*)`", docs))
names |= set(re.findall(r'class="([^"]+)"', docs))
classes = set()
for n in names:
    for c in re.split(r"[.\s]+", n):
        if c:
            classes.add(c)
all_css = strip_comments(layout) + strip_comments(ps) + strip_comments(base)
defined = set(re.findall(r"\.([a-zA-Z][\w-]*)", all_css))
undef = sorted(c for c in classes if c not in defined)
print("classes named in docs:", len(classes), "| not defined in layout/page-sections/base:", undef)
