"""Rough NZ supermarket prices, used to estimate what each recipe costs.

Every price is NZ$ per kg as bought (per litre for liquids), so it works with
the grams that nutrition.grams() gives each shopping item. They're ballpark
figures for comparing recipes, not live prices: change them in the planner
(Shopping > Prices) to match your supermarket, and the planner remembers them.
"""

SPICE = 60  # dried herbs and spices, bought in small jars

PRICES = {
    # Meat and fish
    "beef-mince": 15, "pork-mince": 13, "mince": 14, "chicken": 13,
    "chicken-breast": 14, "chicken-thigh": 12, "chicken-drumstick": 7,
    "pork-shoulder": 12, "pork-loin": 15, "pork-leg": 9, "stewing-beef": 18, "steak": 30,
    "schnitzel": 18, "sausages": 11, "bacon": 18, "ham": 20, "chorizo": 30,
    "salmon": 40, "tuna": 14, "prawns": 30,
    # Cans and pulses (per kg drained for beans; dry for lentils and split peas)
    "black-beans": 6, "kidney-beans": 6, "cannellini": 6, "chickpeas": 6,
    "baked-beans": 4.5, "lentils": 6, "red-lentils": 5, "split-peas": 4,
    "canned-tomatoes": 3.25, "passata": 4, "tomato-paste": 8.5,
    "coconut-milk": 5, "coconut-cream": 6, "salsa": 13, "pasta-sauce": 7,
    "corn": 5, "edamame": 10,
    # Pasta, rice and grains
    "rice": 3, "basmati-rice": 4, "jasmine-rice": 3.5, "brown-rice": 4,
    "pasta": 3, "spaghetti": 3, "noodles": 6, "oats": 4, "barley": 4, "couscous": 6,
    # Baking
    "flour": 2, "bread-flour": 3, "sr-flour": 3, "sugar": 2.5, "brown-sugar": 3.5,
    "caster-sugar": 3.5, "icing-sugar": 4, "cornflour": 6, "cocoa": 25,
    "choc-chips": 25, "baking-powder": 15, "surebake": 30, "milk-powder": 15,
    # Fruit and veg
    "onion": 3, "red-onion": 4, "garlic": 20, "carrot": 2.5, "potato": 2.5,
    "kumara": 5, "pumpkin": 3, "capsicum": 12, "tomato": 8, "spinach": 15,
    "lettuce": 6, "cabbage": 3, "celery": 4, "cucumber": 6, "courgette": 10,
    "broccoli": 8, "mushrooms": 14, "lemon": 8, "lime": 12, "ginger": 20,
    "spring-onion": 15, "coriander": 40, "parsley": 30, "basil": 50,
    "banana": 3.5, "apple": 4,
    # Dairy, eggs and chilled
    "butter": 14, "eggs": 12, "milk": 2.5, "cheese": 13, "parmesan": 35,
    "greek-yoghurt": 7, "yoghurt": 6, "sour-cream": 8, "cream": 9, "feta": 20,
    # Frozen
    "frozen-mixed-veg": 4, "frozen-peas": 4, "berries": 10,
    # Bread and wraps
    "bread": 6, "tortillas": 10,
    # Pantry
    "oil": 5, "olive-oil": 15, "sesame-oil": 25, "soy-sauce": 8,
    "chicken-stock": 3, "beef-stock": 3, "honey": 15, "worcestershire": 12,
    "peanut-butter": 10, "curry-paste": 25, "protein-powder": 40,
    "mayonnaise": 12, "tomato-sauce": 6, "mustard": 15, "wine": 15,
    "vanilla": 100, "salt": 2, "pepper": 60, "lemon-pepper": 60, "taco-seasoning": 40,
    "smoked-paprika": SPICE, "paprika": SPICE, "cumin": SPICE, "oregano": SPICE,
    "thyme": SPICE, "cinnamon": SPICE, "chilli-flakes": SPICE, "chilli-powder": SPICE,
    "mixed-herbs": SPICE, "garlic-powder": SPICE, "garam-masala": SPICE, "turmeric": SPICE,
    "rosemary": SPICE, "onion-powder": SPICE, "cayenne": SPICE, "curry-powder": SPICE,
    "ground-ginger": SPICE, "bay-leaves": SPICE, "white-pepper": SPICE,
    "mustard-powder": SPICE, "ground-coriander": SPICE, "fennel-seeds": SPICE,
    "oyster-sauce": 12, "fish-sauce": 10, "hoisin": 12, "teriyaki-sauce": 10,
    "sweet-chilli": 8, "vinegar": 4, "cider-vinegar": 6, "rice-vinegar": 8,
    "stock": 3, "stock-powder": 30, "baking-soda": 10, "chia": 15, "sesame-seeds": 15,
    "peanuts": 12, "dates": 10, "hummus": 15, "corn-chips": 15,
    # More of the above aisles
    "mozzarella": 15, "macaroni": 3, "rice-noodles": 8, "wholemeal-flour": 3,
    "buns": 8, "frozen-stir-fry": 5, "frozen-spinach": 6, "frozen-broccoli-cauli": 5,
    "cauliflower": 5, "bean-sprouts": 10, "feijoa": 8,
}
