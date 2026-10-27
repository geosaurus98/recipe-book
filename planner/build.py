"""Build the meal planner page from the recipe book.

Reads the chapter order and recipe files from main.tex, converts each
recipebox to plain data, and writes planner/index.html from
planner/template.html with the recipes inlined.

Usage (from the repo root): python3 planner/build.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingredients import parse as parse_ingredient  # noqa: E402
from nutrition import DEFAULT_GRAMS, NUTR, estimate, grams  # noqa: E402
from prices import PRICES  # noqa: E402

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
    "Bread Maker": "breadmaker",
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
    raw = path.read_text(encoding="utf-8")
    overrides = " ".join(re.findall(r"^\s*%\s*tags:\s*(.*)$", raw, re.M | re.I))
    src = strip_comments(raw)
    m = re.search(r"\\begin\{recipebox\}", src)
    (title, servings, time), j = args(src, m.end(), 3)
    end = src.rindex("\\end{recipebox}")
    intro, sections = parse_body(src[j:end])
    book = re.search(r"\\nutritiontable\{([\d.]+)\}\{([\d.]+)\}\{([\d.]+)\}", src)
    return {
        "texTitle": title,
        "tagOverrides": overrides,
        "bookNutrition": book and [float(x) for x in book.groups()],
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


OPTIONAL_GROUP = re.compile(r"serve|serving|\btop\b|garnish|optional", re.I)


def shop_items(recipe):
    """Ingredient lines as shopping-list entries, keeping 'To serve' groups optional."""
    out = []
    seen_steps = False
    for sec in recipe["sections"]:
        if sec["kind"] == "steps":
            seen_steps = True
        is_list = sec["kind"] == "ingredients" or (
            sec["kind"] == "list" and not seen_steps
            and not re.search(r"why|works|serving|storage|tip|note|option", sec.get("heading") or "", re.I))
        if not is_list:
            continue
        group_optional = bool(OPTIONAL_GROUP.search(sec.get("heading") or ""))
        for it in sec["items"]:
            if "group" in it:
                group_optional = bool(OPTIONAL_GROUP.search(it["group"]))
                continue
            for raw in [it["text"]] + it.get("sub", []):
                out.extend(split_and_parse(raw, group_optional))
    return out


# Words that describe preparation, not a separate ingredient ("..., sliced").
PREP_ONLY = re.compile(r"(finely |roughly |thinly )?(sliced|chopped|diced|grated|minced|crushed|halved|shredded|torn|to taste|optional|for serving|to serve|extra)", re.I)


def split_and_parse(raw, optional):
    """'Greek yoghurt, salsa, lettuce' -> three optional items; '1 onion, diced' -> one."""
    first = parse_ingredient(raw)
    if first is None:
        return []
    entries = [(raw, first)]
    plain = re.sub(r"\*\*", "", raw)
    if first["qty"] is None:
        parts = [p for p in re.split(r",|;| or | and |/", re.sub(r"^[^:]{0,40}:\s*", "", plain))
                 if p.strip() and not PREP_ONLY.fullmatch(p.strip())]
        parsed = [parse_ingredient(p) for p in parts]
        known = [x for x in parsed if x and x["aisle"]]
        if len(parts) > 1 and len(known) * 3 >= len(parts) * 2:
            entries = [(raw, x) for x in parsed if x]
            optional = True  # a list of serving options
    out = []
    for line, p in entries:
        p = dict(p, raw=re.sub(r"\*\*", "", line).strip())
        # A "To serve" group only makes items optional when they have no amount:
        # "1¼ cups dry rice, to serve" is still needed.
        p["optional"] = p["optional"] if p["qty"] is not None else (p["optional"] or optional)
        if p["qty"] is not None and re.search(r"\boptional\b", p["raw"], re.I):
            p["optional"] = True
        out.append(p)
    # The same ingredient named twice in one split line counts once.
    uniq = {}
    for p in out:
        uniq.setdefault(p["key"], p)
    return list(uniq.values())


def tags(recipe):
    text = " ".join(ingredient_lines(recipe)).lower() + " " + recipe["title"].lower()
    text = re.sub(r"(chicken|beef|pork)( or \w+)? (stock|broth)", "", text)
    found = [name for name, pat in PROTEIN_WORDS if re.search(pat, text)]
    if re.search(r"\bmince\b", text):
        found.append("mince")
    return found


# ─── Diet and meal-prep tags ────────────────────────────────────────────────

DIET_LABELS = {
    "freezes": "Freezer-friendly", "vegetarian": "Vegetarian", "dairy-free": "Dairy-free",
    "quick": "Under 30 min", "leftovers": "Uses leftovers",
}
NOT_VEGETARIAN = {"chicken-stock", "beef-stock", "fish-sauce", "oyster-sauce", "tuna", "prawns"}
DAIRY = {"milk", "cream", "sour-cream", "cream-cheese", "cottage-cheese", "greek-yoghurt", "yoghurt",
         "butter", "cheese", "mozzarella", "parmesan", "feta", "halloumi", "ricotta", "milk-powder",
         "protein-powder"}
# Dishes that freeze well even when the recipe doesn't say so
FREEZES_TITLE = re.compile(
    r"stew|curry|soup|chilli|bolognese|ragu|keema|congee|adobo|pulled|shredded|taco filling|"
    r"savoury mince|sloppy joe|freezer|meatloaf|muffin|scone|loaf|bread|bun|biscuit|brownie|"
    r"slice|cake|scroll|sausage roll|dumpling|pasta sauce|butter chicken|tikka|masala|biryani|"
    r"shepherd|cottage pie|pie bake|kofta|meatball", re.I)
SAYS_FREEZES = re.compile(r"\bfreez(e|es|ing)\b", re.I)  # not "from the freezer"
NO_FREEZE = re.compile(r"(not|n[’']t) (be )?freez|freezes? poorly|not suitable for freezing", re.I)
LEFTOVERS = re.compile(r"leftover|day-old|\bcooked (rice|chicken|pasta|quinoa|noodles|potato|kumara)|roast chicken", re.I)
STORAGE = re.compile(r"fridge|refrigerat|freez|airtight|keeps? (for|up|well)|storage|reheat", re.I)


def recipe_text(sections):
    """All the words in a recipe's sections, for searching."""
    out = []
    for s in sections:
        out += [s.get("heading") or "", s.get("text") or ""]
        for it in s.get("items", []):
            out += [it.get("text") or it.get("group") or ""] + it.get("sub", [])
        out.append(recipe_text(s.get("sections", [])))
    return " ".join(out)


def minutes(time):
    """Total time in minutes ('15 min prep + 10 min' -> 25), or None if not given.

    Ranges count at their top ('15–20 min' -> 20)."""
    total, found = 0, False
    for m in re.finditer(r"(\d+)(?:\s*[–-]\s*(\d+))?\s*(hr|hours?|h|min)\b", time):
        n = int(m.group(2) or m.group(1))
        total += n * 60 if m.group(3).startswith("h") else n
        found = True
    return total if found else None


def diet_tags(recipe, overrides):
    """Tags for the diet and meal-prep filters, plus `% tags: +x -y` corrections."""
    needed = [s for s in recipe["shop"] if not s["optional"]]
    keys = {s["key"] for s in needed}
    text = recipe_text(recipe["sections"]) + " " + recipe["intro"]
    found = set()
    if not any(s["aisle"] == "Meat & fish" for s in needed) and not keys & NOT_VEGETARIAN:
        found.add("vegetarian")
    if not keys & DAIRY:
        found.add("dairy-free")
    mins = minutes(recipe["time"])
    if mins is not None and mins <= 30:
        found.add("quick")
    if not NO_FREEZE.search(text) and (SAYS_FREEZES.search(text) or FREEZES_TITLE.search(recipe["title"])):
        found.add("freezes")
    if any(LEFTOVERS.search(s["raw"]) and not re.search(r"serve|serving", s["raw"], re.I) for s in needed):
        found.add("leftovers")
    for sign, tag in re.findall(r"([+-])\s*([\w-]+)", overrides):
        (found.add if sign == "+" else found.discard)(tag)
    return [t for t in DIET_LABELS if t in found]


SKIP_STORAGE = re.compile(r"advance prep|defrost|night before|straight from the freezer|frozen \w+ (can|work)", re.I)


def storage_notes(recipe):
    """Sentences about keeping, freezing and reheating, for the planner's Storage box."""
    sentences = []
    def take(text):
        for sent in re.split(r"(?<=[.!])\s+", re.sub(r"\*\*", "", text)):
            if STORAGE.search(sent) and not SKIP_STORAGE.search(sent):
                sentences.append(sent.strip())
    def walk(sections, in_storage):
        for s in sections:
            here = in_storage or bool(re.search(r"storage|storing|keeping|leftovers", s.get("heading") or "", re.I))
            if s.get("text"):
                take(s["text"]) if not here else sentences.append(s["text"])
            if s["kind"] not in ("ingredients", "steps"):
                for it in s.get("items", []):
                    t = it.get("text")
                    if t:
                        (sentences.append(re.sub(r"\*\*", "", t)) if here else take(t))
            walk(s.get("sections", []), here)
    walk(recipe["sections"], False)
    seen, out = set(), []
    for x in sentences:
        if x and x.lower() not in seen:
            seen.add(x.lower())
            out.append(x)
    return out[:4]


AHEAD_WHEN = re.compile(r"night before|overnight|the day before", re.I)
AHEAD_WHAT = re.compile(r"defrost|thaw|chop|\bcut\b|brown|dice|prep|marinat|soak", re.I)
AHEAD_LABEL = re.compile(r"^(advance prep(aration)?|make ahead|tip)\s*:\s*", re.I)


def ahead_notes(recipe):
    """Jobs to do the day before ('defrost the chicken in the fridge the night before')."""
    out = []
    def take(text):
        for sent in re.split(r"(?<=[.!])\s+", re.sub(r"\*\*", "", text)):
            if AHEAD_WHEN.search(sent) and AHEAD_WHAT.search(sent) and not re.search(r"reheat|to freeze", sent, re.I):
                sent = AHEAD_LABEL.sub("", sent.strip())
                out.append(sent[:1].upper() + sent[1:])
    def walk(sections):
        for s in sections:
            if s.get("text"):
                take(s["text"])
            for it in s.get("items", []):
                for t in [it.get("text") or ""] + it.get("sub", []):
                    take(t)
            walk(s.get("sections", []))
    walk(recipe["sections"])
    return list(dict.fromkeys(out))[:3]


def main_meat(recipe):
    """The first meat or fish the recipe needs, for 'take it out of the freezer' reminders."""
    for s in recipe["shop"]:
        if s["aisle"] == "Meat & fish" and not s["optional"]:
            return s["name"]
    return None


def nutrition(recipe, tex_title, book):
    """Per-serving estimate, using the recipe's own \\nutritiontable where it has one."""
    est = estimate(recipe["shop"], recipe["servings"])
    if not est:
        return None
    est.pop("missing")
    if book:
        est.update(kcal=round(book[0]), protein=round(book[1]), fat=round(book[2]))
    return est


def recipe_info_tex(rows):
    """recipe_info.tex: one \\recipeinfo{title}{lines} per recipe, read by the books."""
    out = ["% Written by planner/build.py from each recipe. Don't edit by hand."]
    for tex_title, n, diet in rows:
        lines = []
        if n:
            lines.append(
                f"Per {n['per']} (estimate): {n['kcal']} kcal"
                f" \\textbullet{{}} {n['protein']}\\,g protein \\textbullet{{}} {n['carbs']}\\,g carbs"
                f" \\textbullet{{}} {n['fat']}\\,g fat")
        if diet:
            lines.append(" \\textbullet{} ".join(DIET_LABELS[t] for t in diet))
        if lines:
            body = " \\newline ".join(lines)
            out.append(f"\\recipeinfo{{{tex_title}}}{{{body}}}")
    return "\n".join(out) + "\n"


# ─── Build ──────────────────────────────────────────────────────────────────


def main():
    main_tex = (ROOT / "main.tex").read_text(encoding="utf-8")
    recipes, info_rows = [], []
    chapter = group = None
    for line in main_tex.splitlines():
        cm = re.match(r"\\chapter\{(.*)\}", line)
        if cm:
            chapter = cm.group(1).replace("\\&", "&")
            group = None
            continue
        gm = re.match(r"\\recipegroup\{(.*)\}", line)
        if gm:
            group = gm.group(1).replace("\\&", "&")
            continue
        im = re.match(r"\\input\{(.*)\}", line)
        if im and chapter:
            path = ROOT / (im.group(1) + ".tex")
            r = parse_recipe(path)
            r["id"] = im.group(1).replace("/", "-")
            r["file"] = im.group(1) + ".tex"
            r["chapter"] = CHAPTER_KEYS[chapter]
            r["chapterName"] = chapter
            r["group"] = group
            r["ingredients"] = ingredient_lines(r)
            r["shop"] = shop_items(r)
            for item in r["shop"]:
                g = grams(item)
                if g is not None:
                    item["g"] = round(g, 1)
            r["tags"] = tags(r)
            tex_title, book = r.pop("texTitle"), r.pop("bookNutrition")
            r["nutrition"] = nutrition(r, tex_title, book)
            r["diet"] = diet_tags(r, r.pop("tagOverrides"))
            r["storage"] = storage_notes(r)
            r["minutes"] = minutes(r["time"])
            r["ahead"] = ahead_notes(r)
            r["meat"] = main_meat(r)
            info_rows.append((tex_title, r["nutrition"], r["diet"]))
            recipes.append(r)
    (ROOT / "recipe_info.tex").write_text(recipe_info_tex(info_rows), encoding="utf-8", newline="\n")
    data = json.dumps(recipes, ensure_ascii=False, separators=(",", ":"))
    (HERE / "recipes.json").write_text(json.dumps(recipes, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    template = (HERE / "template.html").read_text(encoding="utf-8")
    html = template.replace("/*RECIPES*/[]", data.replace("</", "<\\/"))
    # Firebase settings for sharing between people (see README). Without the
    # file the planner just saves on each device.
    html = html.replace("/*PRICES*/{}", json.dumps(PRICES))
    # Per-100 g values and unit weights, so recipes added in the planner get estimates too.
    html = html.replace("/*NUTR*/{}", json.dumps({"units": DEFAULT_GRAMS, "foods": {k: list(v) for k, v in NUTR.items()}}))
    sync = HERE / "sync-config.json"
    if sync.exists():
        html = html.replace("/*SYNC*/null", json.dumps(json.loads(sync.read_text(encoding="utf-8"))))
    (HERE / "index.html").write_text(html, encoding="utf-8", newline="\n")
    print(f"{len(recipes)} recipes -> planner/index.html ({len(html) // 1024} KB)")


if __name__ == "__main__":
    main()
