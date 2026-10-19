"""Estimate calories and macros per serving from a recipe's shopping items.

Each shopping item (from ingredients.parse) has a standard key, a quantity
and a unit. NUTR gives that key's energy and macros per 100 g as bought
(meat raw, rice/pasta/lentils dry, beans drained) plus how many grams one
unit weighs. The totals are divided by the recipe's servings.

These are estimates for comparing recipes, not lab values: they land within
about 10-15% for most dishes. Items with no amount ("salt, to taste") and
optional serving extras are left out.
"""
import re

# Grams per unit when an ingredient gives no figure of its own.
DEFAULT_GRAMS = {
    "g": 1, "ml": 1, "tsp": 5, "tbsp": 15, "cup": 240, "can": 400, "jar": 500,
    "clove": 5, "slice": 30, "bunch": 250, "head": 500, "stalk": 40, "rasher": 30,
    "scoop": 30, "sheet": 160, "packet": 30, "block": 100, "bulb": 50, "box": 250,
    "handful": 30,
}


def n(kcal, protein, carbs, fat, **grams):
    """Per-100 g values, plus grams for units this ingredient uses differently.

    `each` is the weight of one with no unit ("2 onions")."""
    return (kcal, protein, carbs, fat, grams)


SPICE = n(300, 12, 50, 10, tsp=2.5, tbsp=7, each=1)
ZERO = n(0, 0, 0, 0)
OIL = n(884, 0, 0, 100, tsp=4.5, tbsp=13.5, cup=215, each=5)
SUGAR = n(400, 0, 100, 0, tsp=4, tbsp=13, cup=200)
FLOUR = n(355, 11, 73, 1.3, tsp=3, tbsp=9, cup=140)
RICE = n(355, 7, 79, 0.7, cup=185)
PASTA = n(355, 12.5, 71, 1.5, cup=100)
STOCK = n(5, 0.6, 0.3, 0.2, cup=250, each=250)
CHOC = n(510, 5, 60, 28, tbsp=12, cup=170)
SYRUP = n(320, 0, 80, 0, tsp=7, tbsp=21, cup=340)
HERB = n(30, 3, 5, 0.5, tsp=1, tbsp=2, each=20)
CITRUS_JUICE = n(25, 0.4, 8, 0.2, each=40)  # juice and zest only
BERRY = n(45, 1, 10, 0.3, cup=150)

NUTR = {
    # Meat and fish (raw)
    "beef-mince": n(190, 20, 0, 12), "pork-mince": n(220, 18, 0, 16),
    "mince": n(200, 19, 0, 13), "chicken": n(130, 21, 0, 5),
    "chicken-breast": n(110, 23, 0, 1.5, each=200),
    "chicken-thigh": n(150, 19, 0, 8, each=120),
    "chicken-drumstick": n(130, 13, 0, 8, each=120),  # weighed with the bone
    "pork-shoulder": n(230, 17, 0, 18), "pork-loin": n(145, 21, 0, 6),
    "stewing-beef": n(150, 21, 0, 7), "steak": n(140, 22, 0, 5),
    "schnitzel": n(120, 22, 0, 3, each=150), "sausages": n(260, 13, 5, 21, each=70),
    "bacon": n(270, 15, 1, 23, each=30), "ham": n(120, 18, 2, 4, slice=20),
    "chorizo": n(455, 24, 2, 38), "salmon": n(200, 20, 0, 13, each=150),
    "tuna": n(110, 25, 0, 1, can=150), "prawns": n(70, 16, 0, 1),
    # Cans and pulses (beans drained; lentils and split peas dry)
    "black-beans": n(115, 7.5, 16, 0.5, can=240, cup=170),
    "kidney-beans": n(105, 7, 14, 0.5, can=240, cup=170),
    "cannellini": n(95, 7, 13, 0.5, can=240, cup=170),
    "chickpeas": n(130, 7, 17, 2.5, can=240, cup=165),
    "baked-beans": n(85, 5, 12, 0.5, can=420, cup=260),
    "lentils": n(340, 24, 50, 1.5, cup=190),
    "lentils-canned": n(100, 8, 14, 0.5, can=240, cup=200),
    "red-lentils": n(345, 24, 52, 1.5, cup=190),
    "split-peas": n(340, 24, 52, 1.2, cup=200),
    "canned-tomatoes": n(22, 1, 3.5, 0.2, can=400, cup=240),
    "passata": n(30, 1.4, 5, 0.2, can=400, cup=250),
    "tomato-paste": n(85, 4.5, 15, 0.5, tsp=5, tbsp=16, can=140, each=140),
    "coconut-milk": n(170, 1.7, 3, 17, can=400, cup=240, each=400),
    "coconut-cream": n(230, 2, 4, 23, can=400, cup=240),
    "salsa": n(35, 1.5, 7, 0.2, jar=300, cup=250),
    "pasta-sauce": n(60, 1.7, 9, 2, jar=500, cup=250),
    "corn": n(85, 3, 16, 1.2, can=300, cup=160),
    "bamboo-shoots": n(20, 2, 3, 0.3, can=225),
    "water-chestnuts": n(50, 1, 12, 0.1, can=225),
    "edamame": n(120, 12, 9, 5, cup=155, can=240),
    "curry-roux": n(510, 6, 45, 34, block=100, packet=100),
    "doubanjiang": n(180, 9, 15, 9, tbsp=17),
    "capers": n(25, 2, 5, 0.9, tbsp=9, each=9),
    "olives": n(145, 1, 4, 15, tbsp=9, cup=135),
    "gherkins": n(15, 0.5, 3, 0.2, each=30),
    "jam": n(260, 0.4, 65, 0, tsp=7, tbsp=20, cup=320),
    # Grains, pasta and bread (dry)
    "rice": RICE, "basmati-rice": RICE, "jasmine-rice": RICE,
    "brown-rice": n(360, 7.5, 76, 2.7, cup=190),
    "pasta": PASTA, "macaroni": PASTA, "spaghetti": PASTA, "rigatoni": PASTA,
    "lasagne-sheets": n(355, 12.5, 71, 1.5, each=20, sheet=20),
    "gnocchi": n(155, 4, 33, 0.5),
    "noodles": n(360, 12, 70, 3, each=80, cup=100, packet=80),
    "rice-noodles": n(360, 6, 82, 0.6),
    "couscous": n(365, 12.5, 73, 1.5, cup=175),
    "quinoa": n(370, 14, 64, 6, cup=170),
    "barley": n(350, 10, 73, 1.2, cup=200),
    "oats": n(380, 13, 60, 8, tbsp=6, cup=90),
    "buckwheat": n(345, 13, 72, 3.4, cup=170),
    "polenta": n(365, 8, 77, 2, cup=160),
    "cornflakes": n(380, 7, 84, 0.9, cup=30),
    "popcorn": n(380, 12, 74, 4.5, tbsp=12, cup=200),
    "granola": n(450, 10, 60, 18, tbsp=8, cup=120),
    "dumpling-wrappers": n(290, 9, 58, 1.5, each=8),
    "taco-shells": n(470, 6, 62, 22, each=12),
    "tortillas": n(300, 8, 50, 7, each=40),
    "buns": n(270, 9, 49, 4, each=70),
    "bread": n(250, 9, 45, 3, each=35, slice=35, cup=110),
    "crackers": n(440, 9, 70, 13, each=5),
    "pita": n(275, 9, 55, 1.2, each=60),
    "rice-paper": n(340, 1, 83, 0.3, each=9),
    "rice-cakes": n(390, 8, 80, 3, each=9),
    "pastry": n(400, 6, 36, 25, sheet=160),
    "corn-chips": n(500, 7, 60, 25, each=150, cup=30),
    # Baking
    "flour": FLOUR, "sr-flour": FLOUR, "bread-flour": n(355, 12.5, 71, 1.5, tbsp=9, cup=140),
    "wholemeal-flour": n(340, 13, 62, 2.5, tbsp=8, cup=130),
    "cornflour": n(360, 0.3, 88, 0.1, tsp=3, tbsp=8, cup=125),
    "sugar": SUGAR, "caster-sugar": SUGAR,
    "brown-sugar": n(380, 0, 98, 0, tsp=4, tbsp=13, cup=200),
    "icing-sugar": n(400, 0, 100, 0, tsp=3, tbsp=8, cup=130),
    "cocoa": n(230, 20, 25, 14, tsp=2, tbsp=6, cup=100),
    "choc-chips": CHOC, "dark-choc": CHOC, "white-choc": n(540, 6, 59, 32, tbsp=12, cup=170),
    "coconut": n(660, 7, 24, 65, tbsp=5, cup=85),
    "golden-syrup": SYRUP, "treacle": SYRUP, "honey": SYRUP,
    "dates": n(280, 2.5, 75, 0.4, cup=150), "sultanas": n(300, 3, 79, 0.5, tbsp=10, cup=150),
    "dried-fruit": n(300, 3, 79, 0.5, cup=150),
    "walnuts": n(655, 15, 14, 65, cup=100), "almonds": n(600, 21, 22, 50, cup=140),
    "peanuts": n(590, 25, 16, 50, tbsp=9, cup=145),
    "seeds": n(560, 20, 30, 45, tbsp=9, cup=140), "chia": n(490, 17, 42, 31, tbsp=12),
    "sesame-seeds": n(570, 18, 23, 50, tsp=3, tbsp=9, each=3),
    "peanut-butter": n(600, 25, 20, 50, tsp=5, tbsp=16, cup=260),
    "tahini": n(600, 17, 21, 54, tbsp=15),
    "milk-powder": n(360, 36, 52, 1, tbsp=7, cup=100),
    "protein-powder": n(380, 75, 8, 6, scoop=30, tbsp=10),
    "baking-powder": ZERO, "baking-soda": ZERO, "yeast": ZERO, "surebake": ZERO,
    "vanilla": ZERO,
    # Dairy and chilled
    "milk": n(64, 3.4, 4.8, 3.3, tbsp=15, cup=250, can=375, each=250),
    "cream": n(340, 2, 3, 35, tbsp=15, cup=240),
    "sour-cream": n(200, 2.5, 4, 20, tbsp=15, cup=240),
    "cream-cheese": n(300, 6, 4, 30, tbsp=15),
    "cottage-cheese": n(95, 12, 4, 3.5, tbsp=15, cup=225),
    "greek-yoghurt": n(100, 9, 4, 5, tbsp=15, cup=250),
    "yoghurt": n(70, 4.5, 6, 3, tbsp=15, cup=250, each=150),
    "butter": n(740, 0.6, 0.5, 82, tsp=5, tbsp=14, cup=225),
    "cheese": n(400, 25, 0.5, 33, tbsp=7, cup=100, slice=20, each=20),
    "mozzarella": n(300, 22, 2, 22, cup=110, each=125),
    "parmesan": n(400, 35, 0, 28, tbsp=6, cup=90, each=20),
    "feta": n(270, 16, 1, 22, cup=150), "halloumi": n(320, 22, 2, 25),
    "ricotta": n(150, 10, 3, 11, cup=245),
    "eggs": n(140, 12.5, 0.7, 9.5, each=55),
    "tofu": n(120, 13, 2, 7, block=300),
    "hummus": n(300, 7, 14, 24, tbsp=15, cup=240, each=200),
    "mayonnaise": n(680, 1, 2, 75, tbsp=14, cup=220, each=14),
    # Oils, sauces and condiments
    "oil": OIL, "olive-oil": OIL, "sesame-oil": OIL,
    "soy-sauce": n(60, 8, 6, 0, tsp=6, tbsp=18, cup=270),
    "fish-sauce": n(35, 5, 4, 0, tsp=6, tbsp=18),
    "oyster-sauce": n(120, 2, 25, 0.3, tsp=6, tbsp=18),
    "hoisin": n(220, 3, 44, 3, tbsp=18),
    "worcestershire": n(80, 0, 20, 0, tsp=6, tbsp=17),
    "sweet-chilli": n(230, 0.5, 55, 0.2, tbsp=18),
    "bbq-sauce": n(170, 1, 40, 0.5, tbsp=17, cup=280),
    "tomato-sauce": n(110, 1.5, 25, 0.2, tbsp=17, cup=270),
    "teriyaki-sauce": n(90, 6, 16, 0, tbsp=18, cup=280),
    "sweet-sour-sauce": n(150, 0.5, 37, 0.2, tbsp=18, cup=280),
    "mustard": n(70, 4, 5, 4, tsp=5, tbsp=15),
    "curry-paste": n(150, 2, 12, 10, tsp=5, tbsp=15),
    "marmite": n(250, 34, 25, 0, tsp=3, tbsp=9),
    "chilli-oil": n(700, 2, 10, 70, tsp=5, tbsp=14),
    "hot-sauce": n(20, 1, 4, 0, tsp=5, tbsp=15),
    "vinegar": n(20, 0, 1, 0, tsp=5, tbsp=15, cup=240),
    "rice-vinegar": n(20, 0, 1, 0, tsp=5, tbsp=15),
    "cider-vinegar": n(20, 0, 1, 0, tsp=5, tbsp=15, cup=240),
    "wine": n(80, 0, 2.6, 0, tbsp=15, cup=240, each=150),
    "stock": STOCK, "chicken-stock": STOCK, "beef-stock": STOCK,
    "stock-powder": n(250, 10, 30, 10, tsp=3, tbsp=8),
    "taco-seasoning": n(320, 6, 60, 5, packet=30, tbsp=8),
    "salt": ZERO, "pepper": ZERO, "salt-pepper": ZERO, "white-pepper": ZERO,
    # Fresh fruit and veg (edible weight)
    "onion": n(40, 1.1, 9, 0.1, each=150, cup=160),
    "red-onion": n(40, 1.1, 9, 0.1, each=150, cup=160),
    "spring-onion": n(32, 1.8, 7, 0.2, each=15, cup=100, bunch=100),
    "garlic": n(150, 6, 33, 0.5, clove=5, tsp=3, tbsp=9, bulb=50),
    "ginger": n(80, 1.8, 18, 0.8, tsp=2, tbsp=6),
    "carrot": n(41, 0.9, 10, 0.2, each=120, cup=130),
    "kumara": n(86, 1.6, 20, 0.1, each=300, cup=135),
    "potato": n(77, 2, 17, 0.1, each=200, cup=150),
    "capsicum": n(30, 1, 6, 0.3, each=160, cup=150),
    "celery": n(16, 0.7, 3, 0.2, each=40, stalk=40, cup=100),
    "courgette": n(17, 1.2, 3, 0.3, each=200, cup=125),
    "eggplant": n(25, 1, 6, 0.2, each=350),
    "mushrooms": n(22, 3, 3, 0.3, each=50, cup=70),
    "bok-choy": n(13, 1.5, 2, 0.2, each=150, head=150),
    "cabbage": n(25, 1.3, 6, 0.1, each=900, cup=70),
    "spinach": n(23, 2.9, 3.6, 0.4, each=30, cup=30),
    "frozen-spinach": n(23, 2.9, 3.6, 0.4, each=100, cup=150),
    "broccoli": n(34, 2.8, 7, 0.4, each=350, head=350, bunch=350, cup=90),
    "cauliflower": n(25, 1.9, 5, 0.3, each=600, head=600, cup=100),
    "frozen-broccoli-cauli": n(30, 2.5, 5, 0.3, cup=100),
    "lettuce": n(15, 1.2, 3, 0.2, each=300, cup=50),
    "cucumber": n(15, 0.7, 3.6, 0.1, each=300, cup=120),
    "tomato": n(18, 0.9, 3.9, 0.2, each=120, cup=180, can=400),
    "avocado": n(160, 2, 9, 15, each=150),
    "bean-sprouts": n(30, 3, 6, 0.2, cup=100),
    "pumpkin": n(26, 1, 6.5, 0.1, cup=120),
    "asparagus": n(20, 2.2, 3.9, 0.1, bunch=250, each=20),
    "lemon": CITRUS_JUICE, "lime": CITRUS_JUICE,
    "orange": n(47, 0.9, 12, 0.1, each=150),
    "apple": n(52, 0.3, 14, 0.2, each=180, cup=125),
    "pineapple": n(60, 0.4, 15, 0.1, each=225, can=225, cup=180),  # canned in juice
    "banana": n(89, 1.1, 23, 0.3, each=120, cup=150),
    "feijoa": n(55, 1, 13, 0.4, each=50, cup=150),
    "passionfruit": n(97, 2.2, 23, 0.7, each=18, tbsp=15, cup=240),
    "mango": n(60, 0.8, 15, 0.4, each=200, cup=165),
    "kiwifruit": n(61, 1.1, 15, 0.5, each=75),
    "berries": BERRY, "strawberries": BERRY,
    "frozen-peas": n(80, 5.4, 14, 0.4, cup=140),
    "frozen-mixed-veg": n(60, 3, 11, 0.5, cup=135),
    "frozen-stir-fry": n(35, 2, 6, 0.3, cup=100, each=500),
    "green-beans": n(31, 1.8, 7, 0.2, cup=110),
    "coriander": HERB, "parsley": HERB, "mint": HERB, "basil": HERB,
    "chilli": n(40, 2, 9, 0.4, each=10, tsp=3, tbsp=9),
}

for _k in ("smoked-paprika paprika cumin ground-coriander curry-powder garam-masala turmeric "
           "cinnamon mixed-spice ground-ginger oregano thyme sage mixed-herbs rosemary "
           "fennel-seeds nutmeg chilli-flakes chilli-powder cayenne bay-leaves garlic-powder "
           "onion-powder mustard-powder allspice sichuan-pepper").split():
    NUTR[_k] = SPICE


def grams(item):
    """Weight in grams of one shopping item, or None if it can't be judged."""
    qty, unit, key = item["qty"], item["unit"], item["key"]
    if qty is None:
        return None
    if key == "lentils" and unit == "can":
        key = "lentils-canned"
    entry = NUTR.get(key)
    if entry is None:
        return None
    per = entry[4]
    if key in ("lettuce", "cabbage") and unit == "" and re.search(r"\bleaf|\bleaves", item["raw"], re.I):
        return qty * 15
    if unit in ("g", "ml"):
        return qty
    if unit == "":
        return qty * per["each"] if "each" in per else None
    if unit in per:
        return qty * per[unit]
    return qty * DEFAULT_GRAMS[unit] if unit in DEFAULT_GRAMS else None


def servings_count(text):
    """'4' -> (4, 'serving'); '3–4' -> 3.5; '1 loaf (10 slices)' -> (10, 'slice')."""
    if re.match(r"^\s*1\s+(large\s+)?(loaf|ring|focaccia)", text):
        m = re.search(r"\((\d+)(?:\s*[–-]\s*(\d+))?", text)
        return (mid(m) if m else 12), "slice"
    m = re.match(r"^\s*(\d+)(?:\s*[–-]\s*(\d+))?", text)
    return (mid(m), "serving") if m else (None, None)


def mid(m):
    """Middle of a matched range such as 3–4, or the single number."""
    lo = int(m.group(1))
    return (lo + int(m.group(2))) / 2 if m.group(2) else lo


def estimate(shop, servings_text):
    """Per-serving kcal, protein, carbs and fat for a recipe, or None.

    `missing` lists ingredients with an amount that couldn't be counted."""
    count, per = servings_count(servings_text)
    if not count:
        return None
    total = [0.0, 0.0, 0.0, 0.0]
    missing = []
    for item in shop:
        if item["optional"] or item["qty"] is None:
            continue
        g = grams(item)
        if g is None:
            missing.append(item["raw"])
            continue
        key = "lentils-canned" if item["key"] == "lentils" and item["unit"] == "can" else item["key"]
        for i, v in enumerate(NUTR[key][:4]):
            total[i] += v * g / 100
    kcal, protein, carbs, fat = (x / count for x in total)
    return {
        "kcal": round(kcal / 10) * 10, "protein": round(protein), "carbs": round(carbs),
        "fat": round(fat), "per": per, "count": count, "missing": missing,
    }
