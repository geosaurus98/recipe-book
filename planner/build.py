"""Build the meal planner page from the recipe book.

Reads the chapter order and recipe files from main.tex, converts each
recipebox to plain data, and writes planner/index.html from
planner/template.html with the recipes inlined.

Usage (from the repo root): python3 planner/build.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent

CHAPTER_KEYS = {
    "Instant Pot & Pressure Cooker": "pressure",
    "Slow Cooker": "slow",
    "Stovetop": "stovetop",
    "Oven": "oven",
    "Salads & Sides": "sides",
    "Breakfast": "breakfast",
    "Snacks": "snacks",
    "Protein Shakes": "shakes",
    "Desserts": "desserts",
    "Baking & Breads": "baking",
}

# ─── LaTeX → plain text ─────────────────────────────────────────────────────

FRACTIONS = {"1/2": "½", "1/3": "⅓", "2/3": "⅔", "1/4": "¼", "3/4": "¾", "1/8": "⅛"}


def frac(a, b):
    return FRACTIONS.get(f"{a}/{b}", f"{a}/{b}")


def match_brace(s, i):
    """Index just past the brace group starting at s[i] == '{'."""
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return j + 1
    raise ValueError("unbalanced braces")


def args(s, i, n):
    """Read n brace arguments starting at s[i]; return (list, end)."""
    out = []
    for _ in range(n):
        while s[i].isspace():
            i += 1
        j = match_brace(s, i)
        out.append(s[i + 1 : j - 1])
        i = j
    return out, i


def strip_comments(s):
    return re.sub(r"(?<!\\)%.*", "", s)


def tex(s):
    """Convert inline LaTeX to plain text, keeping **bold** markers."""
    s = re.sub(r"\\nicefrac\{(\d+)\}\{(\d+)\}", lambda m: frac(*m.groups()), s)
    s = re.sub(r"\$?\\tfrac\{(\d+)\}\{(\d+)\}\$?", lambda m: frac(*m.groups()), s)
    s = re.sub(r"(\d)\$?(\d)\\tfrac", r"\1\2", s)
    s = re.sub(r"\$\s*(\d+)\^\{\\circ\}\s*\$", r"\1°", s)
    for a, b in [
        ("\\textonehalf{}", "½"), ("\\textonehalf", "½"),
        ("\\textonequarter{}", "¼"), ("\\textonequarter", "¼"),
        ("\\textdegree", "°"), ("\\degree", "°"), ("\\textasciitilde", "~"),
        ("$\\times$", "×"), ("$\\rightarrow$", "→"), ("$\\sim$", "~"),
        ("---", "—"), ("--", "–"), ("``", "“"), ("''", "”"),
        ("\\&", "&"), ("\\$", "$"), ("\\%", "%"), ("\\,", " "), ("~", " "),
        ("\\approx", "≈"), ("\\(", ""), ("\\)", ""), ("\\columnbreak", ""),
        ("\\'e", "é"), ("\\'{e}", "é"), ("\\ ", " "), ("\\\\", " "),
    ]:
        s = s.replace(a, b)
    s = re.sub(r"\\textbf\{([^{}]*)\}", r"**\1**", s)
    for cmd in ("emph", "textit", "textsc", "text", "mbox"):
        s = re.sub(r"\\%s\{([^{}]*)\}" % cmd, r"\1", s)
    s = re.sub(r"\\(vspace|hspace)\*?\{[^}]*\}", "", s)
    s = re.sub(r"\\(medskip|smallskip|bigskip|newline|noindent|par|centering)\b", "", s)
    s = re.sub(r"\\[a-zA-Z]+\*?", "", s)
    s = s.replace("{", "").replace("}", "").replace("$", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s.replace("° C", "°C")


# ─── Recipe body parsing ────────────────────────────────────────────────────

ENV_RE = re.compile(r"\\begin\{(\w+)\}")


def env_end(s, name, start):
    """Given s[start:] just after \\begin{name}, return (inner_end, after)."""
    depth = 1
    pat = re.compile(r"\\(begin|end)\{%s\}" % re.escape(name))
    for m in pat.finditer(s, start):
        depth += 1 if m.group(1) == "begin" else -1
        if depth == 0:
            return m.start(), m.end()
    raise ValueError(f"unclosed {name}")


def split_items(body):
    """Split list body on top-level \\item; return list of (label, text)."""
    items, depth, cur, label = [], 0, None, None
    i = 0
    tokens = re.compile(r"\\begin\{\w+\}|\\end\{\w+\}|\\item(\[[^\]]*\])?")
    last = 0
    for m in tokens.finditer(body):
        t = m.group(0)
        if t.startswith("\\begin"):
            depth += 1
        elif t.startswith("\\end"):
            depth -= 1
        elif depth == 0:
            if cur is not None:
                items.append((label, body[last : m.start()]))
            cur, label, last = True, m.group(1), m.end()
    if cur is not None:
        items.append((label, body[last:]))
    return items


def parse_list(body):
    """List body → [{text, sub?, group?}]."""
    body = re.sub(r"\\(begin|end)\{multicols\}(\{\d+\})?", "", body)
    out = []
    for label, raw in split_items(body):
        sub = []
        m = re.search(r"\\begin\{(itemize|enumerate)\}(\[[^\]]*\])?", raw)
        if m:
            inner_end, after = env_end(raw, m.group(1), m.end())
            sub = [x["text"] for x in parse_list(raw[m.end() : inner_end])]
            raw = raw[: m.start()] + raw[after:]
        text = tex(raw)
        if label is not None and label != "[]":
            text = (tex(label[1:-1]) + " " + text).strip()
        if not text and not sub:
            continue
        item = {"text": text}
        is_header = (label == "[]" or re.fullmatch(r"\*\*[^*]+\*\*:?", text)) and not sub
        if is_header and re.fullmatch(r"\*\*[^*]+\*\*:?", text):
            item = {"group": text.strip("*: ").rstrip(":*")}
        elif label == "[]" and text and not sub:
            item = {"group": re.sub(r"\*\*", "", text).rstrip(":")}
        if sub:
            item["sub"] = sub
        out.append(item)
    return out


def parse_body(body):
    """Body of a recipebox → (intro paragraphs, sections)."""
    sections, intro = [], []
    pending_heading = None
    i = 0
    seen_env = False

    def add_text(t):
        t = tex(t)
        if not t:
            return
        if not seen_env and not sections:
            intro.append(t)
        elif sections and sections[-1]["kind"] == "text" and sections[-1].get("heading") == pending_heading:
            sections[-1]["text"] += " " + t
        else:
            sections.append({"kind": "text", "heading": pending_heading, "text": t})

    token = re.compile(
        r"\\begin\{(\w+)\}(\[[^\]]*\])?|\\(sub)*section\*\{|\\nutritiontable\{|\\paragraph\*?\{"
    )
    while True:
        m = token.search(body, i)
        if not m:
            for para in re.split(r"\n\s*\n", body[i:]):
                add_text(para)
            break
        for para in re.split(r"\n\s*\n", body[i : m.start()]):
            add_text(para)
        t = m.group(0)
        if t.startswith("\\begin"):
            name, opt = m.group(1), m.group(2)
            inner_end, after = env_end(body, name, m.end())
            inner = body[m.end() : inner_end]
            seen_env = True
            if name == "ingredients":
                sections.append({"kind": "ingredients", "heading": "Ingredients", "items": parse_list(inner)})
            elif name == "method":
                head = tex(opt[1:-1]) if opt else "Method"
                sections.append({"kind": "steps", "heading": head, "items": parse_list(inner)})
            elif name in ("itemize", "enumerate"):
                kind = "steps" if name == "enumerate" else "list"
                sections.append({"kind": kind, "heading": pending_heading, "items": parse_list(inner)})
            elif name == "notelist":
                sections.append({"kind": "notes", "heading": "Notes", "items": parse_list(inner)})
            elif name == "notes":
                paras = [tex(p) for p in re.split(r"\n\s*\n", inner) if tex(p)]
                sections.append({"kind": "notes", "heading": "Notes", "items": [{"text": p} for p in paras]})
            elif name == "variationbox":
                vm = re.match(r"\s*\{", inner)
                vt, rest = args(inner, inner.index("{"), 1) if vm else ([""], 0)
                v_intro, v_sections = parse_body(inner[rest:])
                sections.append({"kind": "variation", "heading": tex(vt[0]), "text": " ".join(v_intro), "sections": v_sections})
            else:
                add_text(inner)
            pending_heading = None
            i = after
        elif t.startswith("\\nutritiontable"):
            vals, j = args(body, m.end() - 1, 4)
            sections.append({
                "kind": "notes", "heading": "Nutrition (per serve)",
                "items": [{"text": f"{vals[0]} kcal · {vals[1]} g protein · {vals[2]} g fat · {vals[3]} g saturated fat"}],
            })
            i = j
        else:
            (head,), j = args(body, m.end() - 1, 1)
            pending_heading = tex(head)
            i = j
            # A heading directly followed by text (no list) becomes a text section later.
    return intro, sections


def parse_recipe(path):
    src = strip_comments(path.read_text())
    m = re.search(r"\\begin\{recipebox\}", src)
    (title, servings, time), j = args(src, m.end(), 3)
    end = src.rindex("\\end{recipebox}")
    intro, sections = parse_body(src[j:end])
    return {
        "title": tex(title),
        "servings": tex(servings),
        "time": tex(time),
        "intro": " ".join(intro),
        "sections": sections,
    }


# ─── Tags for filtering ─────────────────────────────────────────────────────

PROTEIN_WORDS = [
    ("beef", r"\bbeef\b|steak|schnitzel"),
    ("pork", r"\bpork\b|bacon|\bham\b|sausage|chorizo"),
    ("chicken", r"chicken"),
    ("fish", r"salmon|tuna|fish|prawn"),
    ("lamb", r"\blamb\b"),
]


def ingredient_lines(recipe):
    lines = []
    seen_steps = False
    for sec in recipe["sections"]:
        if sec["kind"] == "steps":
            seen_steps = True
        if sec["kind"] == "ingredients" or (
            sec["kind"] == "list" and not seen_steps
            and not re.search(r"why|works|serving|storage|tip|note|option", sec.get("heading") or "", re.I)
        ):
            for it in sec["items"]:
                if "text" in it:
                    lines.append(it["text"])
                lines.extend(it.get("sub", []))
    return lines


def tags(recipe):
    text = " ".join(ingredient_lines(recipe)).lower() + " " + recipe["title"].lower()
    text = re.sub(r"(chicken|beef|pork) (stock|broth)", "", text)
    found = [name for name, pat in PROTEIN_WORDS if re.search(pat, text)]
    if re.search(r"\bmince\b", text):
        found.append("mince")
    return found


# ─── Build ──────────────────────────────────────────────────────────────────


def main():
    main_tex = (ROOT / "main.tex").read_text()
    recipes = []
    chapter = None
    for line in main_tex.splitlines():
        cm = re.match(r"\\chapter\{(.*)\}", line)
        if cm:
            chapter = cm.group(1).replace("\\&", "&")
            continue
        im = re.match(r"\\input\{(.*)\}", line)
        if im and chapter:
            path = ROOT / (im.group(1) + ".tex")
            r = parse_recipe(path)
            r["id"] = im.group(1).replace("/", "-")
            r["file"] = im.group(1) + ".tex"
            r["chapter"] = CHAPTER_KEYS[chapter]
            r["chapterName"] = chapter
            r["ingredients"] = ingredient_lines(r)
            r["tags"] = tags(r)
            recipes.append(r)
    data = json.dumps(recipes, ensure_ascii=False, separators=(",", ":"))
    (HERE / "recipes.json").write_text(json.dumps(recipes, ensure_ascii=False, indent=1))
    template = (HERE / "template.html").read_text()
    html = template.replace("/*RECIPES*/[]", data.replace("</", "<\\/"))
    (HERE / "index.html").write_text(html)
    print(f"{len(recipes)} recipes → planner/index.html ({len(html) // 1024} KB)")


if __name__ == "__main__":
    main()
