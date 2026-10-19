"""Add recipes to a chapter of main.tex and keep every chapter in title order.

Usage (from the repo root):
    python3 tools/add_to_book.py "Chapter name" Folder/File [Folder/File ...]
    python3 tools/add_to_book.py "Salads \\& Sides" --group "Rice & grains" Sides/Coconut_Rice

A chapter can be split into groups with \\recipegroup{Name} lines. Recipes are
sorted within their group, and groups keep their order. --group says which
group the new recipes go in (needed when the chapter has groups).
With no files, it just re-sorts every chapter.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "main.tex"


def sort_key(path):
    m = re.search(r"\\begin\{recipebox\}\{(.*?)\}\{", (ROOT / (path + ".tex")).read_text(encoding="utf-8"))
    return re.sub(r"\\[a-z]+|[{}\\&’']", "", m.group(1)).lower()


def parse_chapter(body):
    """Chapter body -> [(group or None, [inputs])]."""
    groups = [(None, [])]
    for line in body.splitlines():
        g = re.match(r"\\recipegroup\{(.*)\}", line)
        if g:
            groups.append((g.group(1), []))
            continue
        i = re.match(r"\\input\{(.*)\}", line)
        if i:
            groups[-1][1].append(i.group(1))
    return [(g, items) for g, items in groups if g is not None or items]


def render_chapter(name, groups):
    out = f"\\chapter{{{name}}}\n\\minitoc\n"
    for group, items in groups:
        for n, path in enumerate(sorted(items, key=sort_key)):
            out += "\\newpage\n"
            if n == 0 and group is not None:
                out += f"\\recipegroup{{{group}}}\n"
            out += f"\\input{{{path}}}\n"
    return out + "\n"


def main(argv):
    chapter = argv[0] if argv else None
    rest = argv[1:]
    group = None
    if rest[:1] == ["--group"]:
        group, rest = rest[1].replace("&", "\\&").replace("\\\\&", "\\&"), rest[2:]
    files = rest
    s = MAIN.read_text(encoding="utf-8")

    def fix(m):
        name, body = m.group(1), m.group(2)
        groups = parse_chapter(body)
        if name == chapter and files:
            names = [g for g, _ in groups]
            if group is None and any(names):
                raise SystemExit(f"{name} has groups {names}; pass --group")
            target = next((items for g, items in groups if g == group), None)
            if target is None:
                groups.append((group, []))
                target = groups[-1][1]
            target.extend(files)
        every = [p for _, items in groups for p in items]
        if len(set(every)) != len(every):
            raise SystemExit(f"duplicate recipe in {name}")
        for p in every:
            if not (ROOT / (p + ".tex")).exists():
                raise SystemExit(f"missing file {p}.tex")
        return render_chapter(name, groups)

    if chapter and chapter not in s:
        raise SystemExit(f"no chapter called {chapter}")
    new = re.sub(r"\\chapter\{(.*?)\}\n\\minitoc\n(.*?)\n(?=\\chapter|\\end\{document\})", fix, s, flags=re.S)
    MAIN.write_text(new, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main(sys.argv[1:])
