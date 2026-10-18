# recipe-book

LaTeX recipe books. Every recipe is its own file in a `recipebox`, so the same
recipe can appear in more than one book.

## Books

| File | What it is |
| --- | --- |
| `main.tex` | **George's Recipe Book** — everything, split into chapters by how it's cooked |
| `Palmer Recipe Book.tex` | **GP's Recipe Book** — the easier course recipes (Fakeaways, Italian) for the flat |
| `Preview.tex` | Quick preview of a handful of recipes |
| `To_Add.tex` | Checklist of recipes to add next and ideas that could be added |

## Recipe folders

| Folder | Chapter in `main.tex` |
| --- | --- |
| `InstantPot/` | Instant Pot & Pressure Cooker |
| `SlowCooker/` | Slow Cooker |
| `Stovetop/` | Stovetop |
| `Oven/` | Oven |
| `Breakfast/`, `Snacks/`, `Shakes/`, `Desserts/`, `Baking/` | One chapter each |
| `Fakeaways/`, `Italian/` | Cooking-course recipes. Used by Palmer, and placed by method in `main.tex` |

Recipes converted from earlier Claude-made books start with a `% From ...`
comment saying where they came from (those books have since been removed).
Those from `recipe_book.tex` have `--` for the time because the original
didn't give one.

## Adding a recipe made in Claude

1. Save it as `Folder/Recipe_Name.tex` (no spaces or `&` in the file name).
2. Add a line to the right chapter in `main.tex` (and any other book):

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
