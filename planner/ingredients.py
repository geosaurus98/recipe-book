"""Turn a recipe ingredient line into something a shopping list can add up.

parse("2 large onions, diced") ->
    {"key": "onion", "name": "Onions", "aisle": "Fruit & veg",
     "qty": 2, "unit": "", "optional": False}

Each line gets a quantity, a unit and one standard ingredient name, so
"1 onion, diced" and "2 onions" land on the same shopping-list row.
"""
import re

FRACS = {"½": 0.5, "¼": 0.25, "¾": 0.75, "⅓": 1 / 3, "⅔": 2 / 3, "⅛": 0.125}

UNITS = {
    "g": "g", "gram": "g", "grams": "g", "kg": "kg",
    "ml": "ml", "l": "l", "litre": "l", "litres": "l", "liter": "l",
    "cup": "cup", "cups": "cup",
    "tbsp": "tbsp", "tablespoon": "tbsp", "tablespoons": "tbsp",
    "tsp": "tsp", "teaspoon": "tsp", "teaspoons": "tsp",
    "can": "can", "cans": "can", "tin": "can", "tins": "can",
    "jar": "jar", "jars": "jar", "packet": "packet", "packets": "packet", "pkt": "packet",
    "sheet": "sheet", "sheets": "sheet", "clove": "clove", "cloves": "clove",
    "bunch": "bunch", "bunches": "bunch", "head": "head", "heads": "head",
    "stalk": "stalk", "stalks": "stalk", "rasher": "rasher", "rashers": "rasher",
    "slice": "slice", "slices": "slice", "scoop": "scoop", "scoops": "scoop",
    "handful": "handful", "handfuls": "handful", "block": "block", "blocks": "block",
    "box": "box", "lb": "lb", "oz": "oz",
    "bulb": "bulb", "bulbs": "bulb",
}

MEAT, VEG, DAIRY, FROZEN, CANS, GRAINS, BREAD, BAKING, PANTRY = (
    "Meat & fish", "Fruit & veg", "Dairy, eggs & chilled", "Frozen",
    "Cans, jars & pulses", "Pasta, rice & grains", "Bread & wraps", "Baking",
    "Pantry: check first",
)

# (pattern, key, display name, aisle). First match wins, so specific names
# come before general ones ("spring onion" before "onion").
CANON = [
    # Stock and sauces first so "chicken stock" never reads as chicken.
    (r"stock powder", "stock-powder", "Stock powder", PANTRY),
    (r"chicken stock|chicken broth", "chicken-stock", "Chicken stock", PANTRY),
    (r"beef stock|beef broth", "beef-stock", "Beef stock", PANTRY),
    (r"\bstock\b", "stock", "Stock", PANTRY),
    (r"tahini", "tahini", "Tahini", PANTRY),
    (r"peanut butter", "peanut-butter", "Peanut butter", PANTRY),
    (r"marmite|vegemite", "marmite", "Marmite", PANTRY),
    (r"soy sauce", "soy-sauce", "Soy sauce", PANTRY),
    (r"fish sauce", "fish-sauce", "Fish sauce", PANTRY),
    (r"oyster sauce", "oyster-sauce", "Oyster sauce", PANTRY),
    (r"hoisin", "hoisin", "Hoisin sauce", PANTRY),
    (r"worcestershire", "worcestershire", "Worcestershire sauce", PANTRY),
    (r"sweet chilli sauce", "sweet-chilli", "Sweet chilli sauce", PANTRY),
    (r"bbq sauce|barbecue sauce", "bbq-sauce", "BBQ sauce", PANTRY),
    (r"tomato sauce|ketchup", "tomato-sauce", "Tomato sauce", PANTRY),
    (r"marinara|pasta sauce", "pasta-sauce", "Pasta sauce (jar)", CANS),
    (r"teriyaki", "teriyaki-sauce", "Teriyaki sauce", PANTRY),
    (r"sweet (and|&) sour", "sweet-sour-sauce", "Sweet & sour sauce", PANTRY),
    (r"mayo", "mayonnaise", "Mayonnaise", PANTRY),
    (r"hot sauce|sriracha|tabasco", "hot-sauce", "Hot sauce", PANTRY),
    (r"red wine|white wine|\bwine\b", "wine", "Wine (for cooking)", PANTRY),
    (r"chilli oil|chilli crisp", "chilli-oil", "Chilli oil or crisp", PANTRY),
    (r"sesame oil", "sesame-oil", "Sesame oil", PANTRY),
    (r"olive oil", "olive-oil", "Olive oil", PANTRY),
    (r"\boil\b", "oil", "Cooking oil", PANTRY),
    (r"rice vinegar", "rice-vinegar", "Rice vinegar", PANTRY),
    (r"cider vinegar", "cider-vinegar", "Apple cider vinegar", PANTRY),
    (r"vinegar", "vinegar", "Vinegar", PANTRY),
    (r"curry roux", "curry-roux", "Japanese curry roux", CANS),
    (r"curry paste|masala paste|tikka paste", "curry-paste", "Curry paste", PANTRY),
    (r"chilli bean paste|doubanjiang", "doubanjiang", "Chilli bean paste", CANS),
    (r"tomato paste", "tomato-paste", "Tomato paste", CANS),
    (r"passata|tomato pur[ée]e", "passata", "Passata", CANS),
    (r"(crushed|diced|chopped|whole|tinned|canned) tomato|tomatoes \(canned\)|cans? (of )?tomato", "canned-tomatoes", "Canned tomatoes", CANS),
    # Spices and dried herbs
    (r"smoked paprika", "smoked-paprika", "Smoked paprika", PANTRY),
    (r"paprika", "paprika", "Paprika", PANTRY),
    (r"cumin", "cumin", "Ground cumin", PANTRY),
    (r"ground coriander|coriander, ground", "ground-coriander", "Ground coriander", PANTRY),
    (r"curry powder", "curry-powder", "Curry powder", PANTRY),
    (r"garam masala", "garam-masala", "Garam masala", PANTRY),
    (r"turmeric", "turmeric", "Turmeric", PANTRY),
    (r"cinnamon", "cinnamon", "Ground cinnamon", PANTRY),
    (r"mixed spice", "mixed-spice", "Mixed spice", PANTRY),
    (r"ground ginger", "ground-ginger", "Ground ginger", PANTRY),
    (r"oregano", "oregano", "Dried oregano", PANTRY),
    (r"thyme", "thyme", "Dried thyme", PANTRY),
    (r"\bsage\b", "sage", "Dried sage", PANTRY),
    (r"mixed herbs|italian herbs|italian seasoning", "mixed-herbs", "Mixed herbs", PANTRY),
    (r"rosemary", "rosemary", "Rosemary", PANTRY),
    (r"fennel seed", "fennel-seeds", "Fennel seeds", PANTRY),
    (r"nutmeg", "nutmeg", "Nutmeg", PANTRY),
    (r"capers", "capers", "Capers", CANS),
    (r"olives", "olives", "Olives", CANS),
    (r"bamboo shoots", "bamboo-shoots", "Bamboo shoots", CANS),
    (r"water chestnut", "water-chestnuts", "Water chestnuts", CANS),
    (r"corn chips|tortilla chips", "corn-chips", "Corn chips", BREAD),
    (r"granola", "granola", "Granola", GRAINS),
    (r"almonds", "almonds", "Almonds", PANTRY),
    (r"chilli flakes|chili flakes|red pepper flakes|crushed red pepper", "chilli-flakes", "Chilli flakes", PANTRY),
    (r"chilli powder|chili powder", "chilli-powder", "Chilli powder", PANTRY),
    (r"cayenne", "cayenne", "Cayenne pepper", PANTRY),
    (r"bay lea", "bay-leaves", "Bay leaves", PANTRY),
    (r"garlic powder", "garlic-powder", "Garlic powder", PANTRY),
    (r"onion powder", "onion-powder", "Onion powder", PANTRY),
    (r"mustard powder|dry mustard", "mustard-powder", "Mustard powder", PANTRY),
    (r"allspice", "allspice", "Allspice", PANTRY),
    (r"sichuan pepper", "sichuan-pepper", "Sichuan pepper", PANTRY),
    (r"white pepper", "white-pepper", "White pepper", PANTRY),
    (r"taco seasoning", "taco-seasoning", "Taco seasoning", PANTRY),
    (r"salt and (black )?pepper|salt & pepper", "salt-pepper", "Salt and pepper", PANTRY),
    (r"\bsalt\b", "salt", "Salt", PANTRY),
    (r"black pepper|\bpepper\b(?!s)", "pepper", "Black pepper", PANTRY),
    (r"mustard", "mustard", "Mustard", PANTRY),
    (r"golden syrup", "golden-syrup", "Golden syrup", PANTRY),
    (r"treacle", "treacle", "Treacle", PANTRY),
    (r"honey", "honey", "Honey", PANTRY),
    (r"protein powder", "protein-powder", "Protein powder", PANTRY),
    (r"vanilla", "vanilla", "Vanilla essence", BAKING),
    (r"sesame seeds|sesame or poppy|poppy seeds", "sesame-seeds", "Sesame or poppy seeds", PANTRY),
    # Meat and fish
    (r"chicken breast|chicken tenderloin|chicken breasts", "chicken-breast", "Chicken breast or tenderloins", MEAT),
    (r"chicken thigh", "chicken-thigh", "Chicken thighs", MEAT),
    (r"drumstick", "chicken-drumstick", "Chicken drumsticks", MEAT),
    (r"pork mince|minced pork|ground pork", "pork-mince", "Pork mince", MEAT),
    (r"beef mince|minced beef|ground beef", "beef-mince", "Beef mince", MEAT),
    (r"\bmince\b", "mince", "Mince (beef or pork)", MEAT),
    (r"pork shoulder", "pork-shoulder", "Pork shoulder", MEAT),
    (r"pork loin", "pork-loin", "Pork loin", MEAT),
    (r"stewing beef|beef chuck|diced beef|chuck steak|gravy beef", "stewing-beef", "Stewing beef", MEAT),
    (r"rump steak|steak|topside|\brump\b", "steak", "Beef steak (rump or topside)", MEAT),
    (r"schnitzel", "schnitzel", "Beef schnitzel", MEAT),
    (r"sausage", "sausages", "Sausages", MEAT),
    (r"bacon|guanciale", "bacon", "Bacon", MEAT),
    (r"\bham\b", "ham", "Ham", MEAT),
    (r"chorizo", "chorizo", "Chorizo", MEAT),
    (r"salmon", "salmon", "Salmon", MEAT),
    (r"tuna", "tuna", "Tuna", CANS),
    (r"prawn", "prawns", "Prawns", MEAT),
    (r"\bchicken\b", "chicken", "Chicken", MEAT),
    # Frozen (before fresh veg so "frozen spinach" stays frozen)
    (r"frozen (green )?peas|\bpeas\b(?! *\w*split)", "frozen-peas", "Frozen peas", FROZEN),
    (r"edamame", "edamame", "Frozen edamame", FROZEN),
    (r"frozen spinach", "frozen-spinach", "Frozen spinach", FROZEN),
    (r"stir[- ]fry veg", "frozen-stir-fry", "Frozen stir-fry vegetables", FROZEN),
    (r"frozen broccoli", "frozen-broccoli-cauli", "Frozen broccoli & cauliflower", FROZEN),
    (r"frozen (mixed )?veg|mixed vegetables|mixed veg\b", "frozen-mixed-veg", "Frozen mixed vegetables", FROZEN),
    (r"popcorn", "popcorn", "Popcorn kernels", GRAINS),
    (r"frozen corn|corn kernels|whole kernel corn|\bcorn\b(?! ?(flour|flakes|chips|starch|muffin))", "corn", "Corn (frozen or canned)", FROZEN),
    (r"frozen (green )?beans|green beans", "green-beans", "Green beans", FROZEN),
    (r"frozen (mixed )?berr|berries", "berries", "Berries", FROZEN),
    # Cans and pulses
    (r"coconut milk", "coconut-milk", "Coconut milk", CANS),
    (r"coconut cream", "coconut-cream", "Coconut cream", CANS),
    (r"black beans", "black-beans", "Black beans", CANS),
    (r"kidney beans", "kidney-beans", "Kidney beans", CANS),
    (r"cannellini|butter beans|white beans", "cannellini", "Cannellini or butter beans", CANS),
    (r"baked beans", "baked-beans", "Baked beans", CANS),
    (r"chickpea", "chickpeas", "Chickpeas", CANS),
    (r"red lentils|split red lentils", "red-lentils", "Red lentils (dry)", CANS),
    (r"lentils", "lentils", "Lentils", CANS),
    (r"split peas", "split-peas", "Yellow split peas", CANS),
    (r"salsa", "salsa", "Salsa", CANS),
    (r"gherkin|pickle", "gherkins", "Gherkins", CANS),
    (r"raspberry jam|\bjam\b", "jam", "Raspberry jam", CANS),
    # Grains and pasta
    (r"pearl barley|barley", "barley", "Pearl barley", GRAINS),
    (r"basmati", "basmati-rice", "Basmati rice", GRAINS),
    (r"jasmine", "jasmine-rice", "Jasmine rice", GRAINS),
    (r"brown rice", "brown-rice", "Brown rice", GRAINS),
    (r"rice noodle|vermicelli", "rice-noodles", "Rice noodles", GRAINS),
    (r"rice paper", "rice-paper", "Rice paper sheets", GRAINS),
    (r"rice cakes?", "rice-cakes", "Rice cakes", BREAD),
    (r"\brice\b", "rice", "Rice", GRAINS),
    (r"macaroni", "macaroni", "Macaroni", GRAINS),
    (r"spaghetti", "spaghetti", "Spaghetti", GRAINS),
    (r"rigatoni", "rigatoni", "Rigatoni", GRAINS),
    (r"lasagne sheets|lasagne", "lasagne-sheets", "Lasagne sheets", GRAINS),
    (r"gnocchi", "gnocchi", "Gnocchi", GRAINS),
    (r"noodle", "noodles", "Noodles", GRAINS),
    (r"couscous", "couscous", "Couscous", GRAINS),
    (r"quinoa", "quinoa", "Quinoa", GRAINS),
    (r"\bpasta\b|penne|fusilli|spirals", "pasta", "Pasta", GRAINS),
    (r"rolled oats|\boats\b|oatmeal", "oats", "Rolled oats", GRAINS),
    (r"buckwheat", "buckwheat", "Buckwheat groats", GRAINS),
    (r"cornmeal|polenta", "polenta", "Cornmeal (polenta)", GRAINS),
    (r"cornflakes", "cornflakes", "Cornflakes", GRAINS),
    (r"dumpling|gyoza|wonton", "dumpling-wrappers", "Dumpling wrappers", DAIRY),
    (r"taco shells?", "taco-shells", "Taco shells", BREAD),
    (r"tortilla|\bwraps?\b", "tortillas", "Tortillas or wraps", BREAD),
    (r"burger buns?|\bbuns?\b|bread rolls?", "buns", "Burger buns or rolls", BREAD),
    (r"crackers", "crackers", "Crackers", BREAD),
    (r"\bpitas?\b|pita bread", "pita", "Pita bread", BREAD),
    (r"bread|loaf|baguette", "bread", "Bread", BREAD),
    (r"puff pastry|filo|pastry", "pastry", "Pastry", DAIRY),
    # Baking
    (r"self[- ]raising flour", "sr-flour", "Self-raising flour", BAKING),
    (r"high[- ]grade|bread flour", "bread-flour", "High-grade flour", BAKING),
    (r"wholemeal flour|whole ?wheat flour", "wholemeal-flour", "Wholemeal flour", BAKING),
    (r"cornflour|cornstarch", "cornflour", "Cornflour", BAKING),
    (r"flour", "flour", "Plain flour", BAKING),
    (r"baking powder", "baking-powder", "Baking powder", BAKING),
    (r"baking soda|bicarbonate", "baking-soda", "Baking soda", BAKING),
    (r"cocoa", "cocoa", "Cocoa powder", BAKING),
    (r"icing sugar", "icing-sugar", "Icing sugar", BAKING),
    (r"brown sugar|soft brown", "brown-sugar", "Brown sugar", BAKING),
    (r"caster sugar", "caster-sugar", "Caster sugar", BAKING),
    (r"\bsugar\b", "sugar", "White sugar", BAKING),
    (r"chocolate chips|choc chips", "choc-chips", "Chocolate chips", BAKING),
    (r"white chocolate", "white-choc", "White chocolate chips", BAKING),
    (r"dark chocolate", "dark-choc", "Dark chocolate", BAKING),
    (r"desiccated coconut|long-thread coconut|\bcoconut\b", "coconut", "Desiccated coconut", BAKING),
    (r"surebake", "surebake", "Surebake yeast", BAKING),
    (r"\byeast\b", "yeast", "Instant dried yeast", BAKING),
    (r"\bdates\b", "dates", "Pitted dates", BAKING),
    (r"sultanas?|raisins", "sultanas", "Sultanas", BAKING),
    (r"mixed dried fruit|dried fruit", "dried-fruit", "Mixed dried fruit", BAKING),
    (r"linseed|sunflower seeds|pumpkin seeds", "seeds", "Seeds (linseed, sunflower)", PANTRY),
    (r"walnut", "walnuts", "Walnuts", BAKING),
    (r"peanuts", "peanuts", "Peanuts", PANTRY),
    (r"chia", "chia", "Chia seeds", PANTRY),
    # Dairy and chilled
    (r"cream cheese", "cream-cheese", "Cream cheese", DAIRY),
    (r"sour cream", "sour-cream", "Sour cream", DAIRY),
    (r"cottage cheese", "cottage-cheese", "Cottage cheese", DAIRY),
    (r"greek yo", "greek-yoghurt", "Greek yoghurt", DAIRY),
    (r"yoghurt|yogurt", "yoghurt", "Plain yoghurt", DAIRY),
    (r"milk powder|powdered milk", "milk-powder", "Milk powder", BAKING),
    (r"\bmilk\b", "milk", "Milk", DAIRY),
    (r"\bcream\b", "cream", "Cream", DAIRY),
    (r"butter", "butter", "Butter", DAIRY),
    (r"mozzarella", "mozzarella", "Mozzarella", DAIRY),
    (r"parmesan|pecorino", "parmesan", "Parmesan", DAIRY),
    (r"feta", "feta", "Feta", DAIRY),
    (r"halloumi", "halloumi", "Halloumi", DAIRY),
    (r"ricotta", "ricotta", "Ricotta", DAIRY),
    (r"cheddar|tasty cheese|grated cheese|\bcheese\b", "cheese", "Tasty cheese", DAIRY),
    (r"\beggs?\b|egg yolks?|egg whites?", "eggs", "Eggs", DAIRY),
    (r"tofu", "tofu", "Tofu", DAIRY),
    (r"hummus", "hummus", "Hummus", DAIRY),
    # Fresh fruit and veg
    (r"spring onion|scallion|green onion", "spring-onion", "Spring onions", VEG),
    (r"red onion", "red-onion", "Red onion", VEG),
    (r"onion", "onion", "Onions", VEG),
    (r"garlic", "garlic", "Garlic", VEG),
    (r"ginger", "ginger", "Fresh ginger", VEG),
    (r"carrot", "carrot", "Carrots", VEG),
    (r"sweet potato|kumara", "kumara", "Kumara", VEG),
    (r"potato", "potato", "Potatoes", VEG),
    (r"capsicum|bell pepper", "capsicum", "Capsicums", VEG),
    (r"celery", "celery", "Celery", VEG),
    (r"courgette|zucchini", "courgette", "Courgettes", VEG),
    (r"eggplant|aubergine", "eggplant", "Eggplant", VEG),
    (r"mushroom", "mushrooms", "Mushrooms", VEG),
    (r"bok choy|pak choi", "bok-choy", "Bok choy", VEG),
    (r"cabbage|slaw", "cabbage", "Cabbage", VEG),
    (r"spinach", "spinach", "Baby spinach", VEG),
    (r"broccoli", "broccoli", "Broccoli", VEG),
    (r"cauliflower", "cauliflower", "Cauliflower", VEG),
    (r"lettuce|salad mix|salad leaves|rocket", "lettuce", "Lettuce or salad leaves", VEG),
    (r"cucumber", "cucumber", "Cucumber", VEG),
    (r"cherry tomato|tomato", "tomato", "Tomatoes", VEG),
    (r"avocado", "avocado", "Avocado", VEG),
    (r"bean sprouts|sprouts", "bean-sprouts", "Bean sprouts", VEG),
    (r"pumpkin", "pumpkin", "Pumpkin", VEG),
    (r"asparagus", "asparagus", "Asparagus", VEG),
    (r"lemon", "lemon", "Lemons", VEG),
    (r"orange", "orange", "Oranges", VEG),
    (r"\blimes?\b", "lime", "Limes", VEG),
    (r"apple", "apple", "Apples", VEG),
    (r"banana", "banana", "Bananas", VEG),
    (r"feijoa", "feijoa", "Feijoas", VEG),
    (r"passionfruit", "passionfruit", "Passionfruit", VEG),
    (r"mango", "mango", "Mango", VEG),
    (r"kiwifruit", "kiwifruit", "Kiwifruit", VEG),
    (r"strawberr", "strawberries", "Strawberries", VEG),
    (r"coriander|cilantro", "coriander", "Fresh coriander", VEG),
    (r"parsley", "parsley", "Fresh parsley", VEG),
    (r"\bmint\b", "mint", "Fresh mint", VEG),
    (r"basil", "basil", "Fresh basil", VEG),
    (r"chilli|chili", "chilli", "Fresh chilli", VEG),
]
CANON_RE = [(re.compile(p, re.I), k, n, a) for p, k, n, a in CANON]

# Ingredients bought by the can: weights convert to cans of about 400 g.
CANNED = {"canned-tomatoes", "black-beans", "kidney-beans", "cannellini", "chickpeas",
          "coconut-milk", "coconut-cream", "baked-beans", "lentils", "tuna"}

SKIP = re.compile(r"^(boiling |cold |warm |hot |lukewarm )?water\b|^ice\b|ice cubes|baking paper|toothpick|frypan|frying pan", re.I)


def num(s):
    """'1½' -> 1.5, '3/4' -> 0.75, '½' -> 0.5, '1.5' -> 1.5."""
    s = s.strip()
    m = re.fullmatch(r"(\d+)\s*/\s*(\d+)", s)
    if m:
        return int(m.group(1)) / int(m.group(2))
    m = re.fullmatch(r"(\d+(?:[.,]\d+)?)?\s*([½¼¾⅓⅔⅛])?", s)
    if not m or not (m.group(1) or m.group(2)):
        return None
    whole = float(m.group(1).replace(",", ".")) if m.group(1) else 0
    return whole + (FRACS[m.group(2)] if m.group(2) else 0)


NUM = r"(?:\d+(?:[.,]\d+)?\s*[½¼¾⅓⅔⅛]?|[½¼¾⅓⅔⅛]|\d+\s*/\s*\d+)"
QTY_RE = re.compile(rf"^({NUM})(?:\s*(?:–|-|to)\s*({NUM}))?\s*")
UNIT_RE = re.compile(r"^(" + "|".join(sorted(map(re.escape, UNITS), key=len, reverse=True)) + r")\b\.?\s*", re.I)


def parse(raw):
    text = re.sub(r"\*\*", "", raw).strip()
    optional = bool(re.search(r"optional|to serve|to garnish|for serving|to top|to decorate", text, re.I))
    if SKIP.search(text):
        return None

    # "Chicken breast — 1.1 kg, diced" (Meal Prep style): put the amount first.
    m = re.match(r"^([A-Za-z][^—\d]*?)\s+—\s+(.+)$", text)
    if m and re.match(NUM, m.group(2)):
        rest = m.group(2)
        amt = re.match(rf"({NUM}(?:\s*(?:–|-)\s*{NUM})?\s*(?:[×x]\s*\d+\s*\w+|\w+)?)(.*)", rest)
        text = f"{amt.group(1)} {m.group(1)}{amt.group(2)}" if amt else f"{rest} {m.group(1)}"

    # Drop a leading label such as "To serve:" or "For creaminess + volume:".
    text = re.sub(r"^[A-Za-z][^:\d]{0,40}:\s*", "", text)
    # "Juice of 2 limes", "Zest and juice of 2 lemons"
    text = re.sub(r"^(?:zest and )?juice of\s+", "", text, flags=re.I)
    text = re.sub(r"^about\s+", "", text, flags=re.I)
    text = re.sub(r"^(a )?(pinch|squeeze|splash|dash|drizzle|handful|few drops|little|sprinkle) of\s+", "", text, flags=re.I)

    qty, unit = None, ""
    # "2 × 400 g cans lentils" -> 2 cans
    m = re.match(rf"^({NUM})\s*[×x]\s*\d+\s*(?:g|ml)\s*(cans?|tins?)?\s*", text)
    if m:
        qty, unit, text = num(m.group(1)), "can", text[m.end():]
    else:
        m = QTY_RE.match(text)
        if m:
            qty = num(m.group(2) or m.group(1))  # ranges: buy for the top of the range
            text = text[m.end():]
            u = UNIT_RE.match(text)
            if u:
                unit, text = UNITS[u.group(1).lower()], text[u.end():]
            # "1 can (400 g) ...": drop the size note after a can
            text = re.sub(r"^\(\s*[\d.]+\s*(g|ml|oz|ml|mL)\b[^)]*\)\s*", "", text, flags=re.I)

    # Name: up to the first comma / bracket / dash note.
    name = re.split(r",|\(|;| – | - |—", text)[0]
    name = re.sub(r"^(of|x|about)\s+", "", name.strip(), flags=re.I)
    full = text.lower()
    if not name.strip() or SKIP.search(name.strip()):
        return None

    if unit in ("kg",):
        qty, unit = qty * 1000 if qty else qty, "g"
    if unit == "l":
        qty, unit = qty * 1000 if qty else qty, "ml"
    if unit == "lb":
        qty, unit = qty * 454 if qty else qty, "g"
    if unit == "oz":
        qty, unit = qty * 28 if qty else qty, "g"

    for rx, key, disp, aisle in CANON_RE:
        if rx.search(name) or (not name.strip() and rx.search(full)):
            break
    else:
        for rx, key, disp, aisle in CANON_RE:
            if rx.search(full):
                break
        else:
            key = re.sub(r"[^a-z]+", "-", name.lower()).strip("-") or "other"
            disp = name.strip().capitalize() or text.strip().capitalize()
            aisle = None

    if key == "garlic" and unit in ("", "clove") and qty:
        unit = "clove"
    if key == "corn" and unit == "g" and qty and re.search(r"\bcans?\b|\btins?\b|tinned|canned", full):
        qty, unit = round(qty / 400 * 2) / 2 or 0.5, "can"
    if key in CANNED and unit == "g" and qty:
        qty, unit = round(qty / 400 * 2) / 2 or 0.5, "can"
    if key in CANNED and unit == "ml" and qty:
        qty, unit = round(qty / 400 * 2) / 2 or 0.5, "can"

    # Cooked rice is about three times the dry amount you buy.
    if key.endswith("rice") and unit == "cup" and qty and re.search(r"\bcooked\b", name, re.I) and not re.search(r"uncooked", name, re.I):
        qty = round(qty / 3 * 4) / 4
    # Grated rind in spoons -> one orange or lemon is plenty.
    if key in ("orange", "lemon") and unit in ("tsp", "tbsp") and qty and re.search(r"rind|zest", full):
        qty, unit = 1, ""
    # Citrus juice in spoons -> whole fruit (a lemon or lime gives about 2 tbsp).
    if key in ("lemon", "lime") and unit in ("tsp", "tbsp", "cup") and qty:
        tsp = qty * {"tsp": 1, "tbsp": 3, "cup": 48}[unit]
        qty, unit = max(0.5, -(-tsp // 3) / 2), ""

    return {"key": key, "name": disp, "aisle": aisle, "qty": qty, "unit": unit, "optional": optional}


if __name__ == "__main__":
    import sys
    for line in sys.argv[1:]:
        print(line, "->", parse(line))
