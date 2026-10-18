"""Rewrite recipe files so ingredients follow one house style.

House style for an ingredient line:
    amount, unit, ingredient, then preparation after a comma
    \\item 500\\,g lean beef mince
    \\item 1 large onion, diced
    \\item 3 garlic cloves, crushed
    \\item 2 cans (400\\,g) kidney beans, drained and rinsed

- Metric units with a thin space: g, kg, ml, L. Spoons as tbsp and tsp.
- Fractions with \\nicefrac.
- NZ names: beef mince, chicken stock, capsicum, courgette, spring onions,
  plain flour, cornflour, yoghurt, coriander.

Usage (from the repo root): python3 tools/standardise_ingredients.py [--dry]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOLDERS = ["InstantPot", "SlowCooker", "Stovetop", "Oven", "Fakeaways", "Italian",
           "Breakfast", "Snacks", "Shakes", "Desserts", "Baking", "Sides"]

UNICODE_FRACS = {"½": "1}{2", "¼": "1}{4", "¾": "3}{4", "⅓": "1}{3", "⅔": "2}{3", "⅛": "1}{8"}

# (pattern, replacement) applied to the whole recipe. Case of the first
# letter is kept, so "Yogurt" becomes "Yoghurt".
SYNONYMS = [
    (r"ground beef", "beef mince"),
    (r"minced beef", "beef mince"),
    (r"ground pork", "pork mince"),
    (r"ground chicken", "chicken mince"),
    (r"ground lamb", "lamb mince"),
    (r"chicken broth", "chicken stock"),
    (r"beef broth", "beef stock"),
    (r"\bbroth\b", "stock"),
    (r"bell peppers", "capsicums"),
    (r"bell pepper", "capsicum"),
    (r"scallions", "spring onions"),
    (r"scallion", "spring onion"),
    (r"green onions", "spring onions"),
    (r"all-purpose flour", "plain flour"),
    (r"standard grade flour", "plain flour"),
    (r"cornstarch", "cornflour"),
    (r"yogurt", "yoghurt"),
    (r"zucchinis", "courgettes"),
    (r"zucchini", "courgette"),
    (r"cilantro", "coriander"),
    (r"(\d) cloves garlic", r"\1 garlic cloves"),
    (r"(\d) clove garlic", r"\1 garlic clove"),
]

# Capitalised ingredient words copied from brand recipes ("1 cup White Sugar").
LOWERCASE = ["Self-Raising Flour", "Self Raising Flour", "Beef Stock", "Chicken Stock", "Plain flour", "White Sugar", "Brown Sugar", "Demerara Sugar", "Caster Sugar", "Icing Sugar",
             "Baking Powder", "Baking Soda", "Milk", "Butter", "Flour", "Plain Flour",
             "Self Raising Flour", "Self-Raising Flour", "Rolled Oats", "Cocoa"]

# Only after an amount, so method sentences ("roll tablespoons of mixture") read normally.
QTY_BEFORE = r"(?<=[\d}])\s*"
UNIT_WORDS = [
    (r"\bTbsp\b", "tbsp"), (QTY_BEFORE + r"\s[Tt]ablespoons?\b", " tbsp"),
    (QTY_BEFORE + r"\s[Tt]easpoons?\b", " tsp"), (r"\bTsp\b", "tsp"),
    (r"(?<=\d)\s*mL\b", r"\\,ml"), (r"\bmL\b", "ml"),
    (r"(?<=\d)\s*litres?\b", r"\\,L"), (r"(?<=\d) litre\b", r"\\,L"),
]


def keep_case(repl):
    def f(m):
        out = m.expand(repl)
        return out[0].upper() + out[1:] if m.group(0)[0].isupper() else out
    return f


def fix_text(s):
    """Changes that apply anywhere in a recipe (ingredients and method)."""
    # Fractions: $\tfrac{1}{4}$ / ½ / 3/4 -> \nicefrac{1}{4}
    s = re.sub(r"\$\\tfrac\{(\d)\}\{(\d)\}\$", r"\\nicefrac{\1}{\2}", s)
    for ch, f in UNICODE_FRACS.items():
        s = s.replace(ch, "\\nicefrac{" + f + "}")
    s = re.sub(r"(?<![\d/:])\b([1-9])/([2-8])\b(?![\d/])", r"\\nicefrac{\1}{\2}", s)
    s = re.sub(r"(\d) \\nicefrac", r"\1\\nicefrac", s)  # "1 \nicefrac{1}{2}" -> "1\nicefrac{1}{2}"
    for pat, repl in UNIT_WORDS:
        s = re.sub(pat, repl, s)
    for pat, repl in SYNONYMS:
        s = re.sub(pat, keep_case(repl), s, flags=re.I)
    # Thin space between a number and a metric unit: 500g / 500 g -> 500\,g
    s = re.sub(r"(\d|\})\s?(kg|g|ml|L)\b(?!\w)", r"\1\\,\2", s)
    s = s.replace("\\,\\,", "\\,")
    return s


AMOUNT = r"(?:[\d.]+(?:--[\d.]+)?(?:\\nicefrac\{\d\}\{\d\})?|\\nicefrac\{\d\}\{\d\}(?:--[\d.]+(?:\\nicefrac\{\d\}\{\d\})?)?)"


PROPER = {"Italian", "Greek", "Cajun", "Thai", "Dijon", "Worcestershire", "Parmesan", "Japanese",
          "Mexican", "Chinese", "Korean", "Sichuan", "American", "Edam", "BBQ"}


def lower_first(name):
    if name.split(" ")[0] in PROPER:
        return name
    if len(name) > 1 and name[0].isupper() and name[1].islower():
        return name[0].lower() + name[1:]
    return name


def amount_first(item):
    """'Onion --- 1 large, diced' (or with an em dash) -> '1 large onion, diced'."""
    if item.count("—") > 1:
        return item  # two amounts on one line; leave for a person to tidy
    m = re.match(r"^(?P<name>[A-Za-z][^—]*?)\s*(?:—|---)\s*(?P<rest>.+)$", item)
    if not m or not re.match(AMOUNT, m.group("rest")):
        if m and not re.match(r"\d", m.group("rest")):
            return f"{m.group('name')}, {m.group('rest')}"  # "Oil — for sautéing"
        return item
    name, rest = m.group("name").strip(), m.group("rest").strip()
    # Pull a bracketed note off the name: "Frozen mixed vegetables (peas, corn)"
    note = ""
    nm = re.match(r"^(.*?)\s*(\(.*\))$", name)
    if nm:
        name, note = nm.group(1), " " + nm.group(2)
    name = lower_first(name)
    am = re.match(rf"^(?P<amt>{AMOUNT})\s*(?P<unit>\$\\times\$\s*400\\,g|\\,?(?:kg|g|ml|L)\b|cups?\b|tbsp\b|tsp\b|cloves?\b|large\b|medium\b|small\b|cans?\b|stalks?\b)?(?P<tail>.*)$", rest)
    if not am:
        return item
    amt, unit, tail = am.group("amt"), (am.group("unit") or "").strip(), am.group("tail")
    if unit.startswith("$\\times$"):
        name = re.sub(r"^canned\s+", "", name, flags=re.I)
        core = f"{amt} {'can' if amt == '1' else 'cans'} (400\\,g) {name}"
    elif unit in ("clove", "cloves") and name.lower() == "garlic":
        core = f"{amt} garlic {unit}"
    elif unit:
        sep = "" if unit.startswith("\\,") else " "
        unit = unit if unit.startswith("\\,") or unit not in ("kg", "g", "ml", "L") else "\\," + unit
        core = f"{amt}{sep if not unit.startswith(chr(92)) else ''}{unit} {name}"
    else:
        core = f"{amt} {name}"
    tail = tail.strip()
    if tail.startswith(("(", "\\")):
        tail = " " + tail
    elif tail and not tail.startswith((",", "+")):
        tail = ", " + tail
    return core + note + tail


def fix_items(block):
    """Changes to \\item lines in an ingredient list."""
    def one(m):
        indent, label, text = m.group(1), m.group(2) or "", m.group(3)
        # Bold amounts: \textbf{1.1--1.2 kg} chicken -> 1.1--1.2 kg chicken
        text = re.sub(r"^\\textbf\{(" + AMOUNT + r"[^}]*)\}\s*", r"\1 ", text).replace(" ,", ",")
        # "2 $\times$ 400\,g cans lentils" -> "2 cans (400\,g) lentils"
        text = re.sub(r"^(" + AMOUNT + r")\s*\$\\times\$\s*(\d+)\\,(g|ml)\s+cans?\s+",
                      lambda m: f"{m.group(1)} {'can' if m.group(1) == '1' else 'cans'} ({m.group(2)}\\,{m.group(3)}) ", text)
        for pat, repl in SYNONYMS:
            text = re.sub(pat, keep_case(repl), text, flags=re.I)
        text = amount_first(text)
        text = re.sub(r"\bMeadow Fresh\s+", "", text)
        for w in LOWERCASE:
            text = re.sub(rf"(?<=\w )\b{w}\b", w.lower(), text)
        text = re.sub(r"\bstandard grade flour\b", "plain flour", text, flags=re.I)
        return f"{indent}\\item{label} {text}"
    return re.sub(r"^(\s*)\\item(\[[^\]]*\])? (.*)$", one, block, flags=re.M)


def standardise(src):
    out = fix_text(src)
    # Ingredient lists: everything before the first method/enumerate.
    cut = re.search(r"\\begin\{(method|enumerate)\}", out)
    head, tail = (out[: cut.start()], out[cut.start():]) if cut else (out, "")
    return fix_items(head) + tail


def main():
    dry = "--dry" in sys.argv
    changed = 0
    for folder in FOLDERS:
        for path in sorted((ROOT / folder).glob("*.tex")):
            if path.name == "Ideas.tex":
                continue
            src = path.read_text()
            new = standardise(src)
            if new != src:
                changed += 1
                if not dry:
                    path.write_text(new)
    print(f"{changed} files {'would change' if dry else 'changed'}")


if __name__ == "__main__":
    main()
