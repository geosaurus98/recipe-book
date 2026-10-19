# recipe-book

LaTeX recipe books. Every recipe is its own file in a `recipebox`, so the same
recipe can appear in more than one book.

## Books

| File | What it is |
| --- | --- |
| `main.tex` | **George's Recipe Book** — everything, split into chapters by how it's cooked |
| `Palmer Recipe Book.tex` | **GP's Recipe Book** — the easier course recipes (Fakeaways, Italian) for the flat |
| `Preview.tex` | Quick preview of a handful of recipes |
| `To_Add.tex` | Checklist of recipe ideas for every chapter, built from each folder's `Ideas.tex` |

## Recipe folders

| Folder | Chapter in `main.tex` |
| --- | --- |
| `InstantPot/` | Instant Pot & Pressure Cooker |
| `SlowCooker/` | Slow Cooker |
| `Stovetop/` | Stovetop |
| `Oven/` | Oven |
| `Breakfast/`, `Snacks/`, `Shakes/`, `Desserts/`, `Baking/` | One chapter each |
| `Fakeaways/`, `Italian/` | Cooking-course recipes. Used by Palmer, and placed by method in `main.tex` |
| `Sides/` | Salads & Sides (new recipes go here; the course salad and asparagus stay in `Italian/`) |
| `BreadMaker/` | Bread Maker (Panasonic SD-2501 NZ recipes: machine loaves, doughs, and a tea bread) |

Each folder (except the course folders) also has an `Ideas.tex`: a checklist of
recipes that could go in that chapter. `To_Add.tex` shows them all in one PDF.
Tick an idea with `\done`, or delete its line once the recipe is in the book.

Recipes converted from earlier Claude-made books start with a `% From ...`
comment saying where they came from (those books have since been removed).
Those from `recipe_book.tex` have `--` for the time because the original
didn't give one.

## Adding a recipe made in Claude

1. Save it as `Folder/Recipe_Name.tex` (no spaces or `&` in the file name).
2. Add it to the right chapter in `main.tex`, which keeps chapters in title order:

   ```
   python3 tools/add_to_book.py "Slow Cooker" SlowCooker/Recipe_Name
   python3 tools/add_to_book.py "Salads \& Sides" --group "Rice & grains" Sides/Recipe_Name
   ```

   Salads & Sides is split into groups (`\recipegroup{...}` lines in
   `main.tex`), so new sides need `--group`: "Salads", "Rice & grains" or
   "Vegetables & potatoes". Other books still take a plain line:

   ```latex
   \newpage
   \input{InstantPot/Recipe_Name}
   ```

### Ingredient style

Write each ingredient as amount, unit, ingredient, then any preparation after
a comma:

```latex
\item 500\,g lean beef mince
\item 1 large onion, diced
\item 3 garlic cloves, crushed
\item 2 cans (400\,g) kidney beans, drained and rinsed
\item 1\nicefrac{1}{2} cups chicken stock
```

- Metric units with a thin space (`500\,g`, `250\,ml`, `1\,L`); spoons as
  `tbsp` and `tsp`; fractions with `\nicefrac`.
- NZ names: beef mince, chicken stock, capsicum, courgette, spring onions,
  plain flour, cornflour, yoghurt, coriander.

`python3 tools/standardise_ingredients.py` rewrites recipes into this style.
It's safe to run again after adding recipes from Claude; it only changes
lines that don't match yet.

Recipe files can use `recipebox`, `ingredients`, `method` (optionally
`\begin{method}[Rice (Rice Cooker)]` for a custom heading), `notes`,
`notelist`, `variationbox` and `\nutritiontable`.

## Meal planner

`planner/index.html` is a web page for planning the week: one slow cooker, one
pressure cooker and one quick meal, plus extras, with a combined shopping list
grouped by aisle. It's built from the recipe files, so after adding or
changing recipes, rebuild it:

```
python3 planner/build.py
```

This reads the chapters in `main.tex`, writes `planner/recipes.json` and
regenerates `planner/index.html` from `planner/template.html`.

### Nutrition estimates

The build also estimates calories, protein, carbs and fat per serving from
each recipe's ingredients (`planner/nutrition.py` holds the per-100 g values
and typical weights, such as one onion or a cup of flour). They show on every
recipe in the planner, power the "30 g+ protein" filter and the weekly totals,
and appear under Servings/Time in the PDF books via the generated
`recipe_info.tex`. A recipe's own `
utritiontable` takes priority. Estimates
are for comparing recipes, so expect them to be within about 10-15%. If a new
ingredient isn't in `nutrition.py` it's simply left out, so add it there when
you add recipes with something unusual.

### Tags and storage notes

Each recipe also gets tags for the planner's filters and the books:
**Freezer-friendly**, **Vegetarian**, **Dairy-free**, **Under 30 min** and
**Uses leftovers**. They're worked out automatically from the ingredients,
time and notes (see `diet_tags` in `planner/build.py`). To correct one, add a
comment line anywhere in the recipe file:

```latex
% tags: +freezes -vegetarian
```

The planner also shows a **Storage** box on each recipe, pulled from the
fridge, freezer and reheating advice in its notes.

## Website

Every push to `main` runs `.github/workflows/publish.yml`, which rebuilds the
planner, compiles `main.tex` and `Palmer Recipe Book.tex` to PDF, and publishes
them to GitHub Pages:

- Planner: <https://geosaurus98.github.io/recipe-book/>
- Books: [`books/main.pdf`](https://geosaurus98.github.io/recipe-book/books/main.pdf)
  and [`books/palmer.pdf`](https://geosaurus98.github.io/recipe-book/books/palmer.pdf)

So there's no need to run `build.py` before pushing, though it's handy for
checking changes locally. Progress and errors show on the repo's Actions tab.

The planner works as a home-screen app: open the planner link on your phone,
then use **Share → Add to Home Screen** (iPhone, in Safari) or **⋮ → Add to
Home screen** (Android, in Chrome). It opens full-screen and still works with
no signal. The icon is drawn by `tools/make_icons.py` (needs Pillow); the app
settings are in `planner/manifest.webmanifest` and `planner/sw.js`. If you
change `sw.js`, bump the `CACHE` name in it so phones pick up the new version.
