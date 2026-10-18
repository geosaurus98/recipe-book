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
| `recipe_book.tex`, `weightloss.tex`, `Meal Prep.tex` | Original Claude-made books, kept for reference. Their recipes have been copied into the folders below. |

## Recipe folders

| Folder | Chapter in `main.tex` |
| --- | --- |
| `InstantPot/` | Instant Pot & Pressure Cooker |
| `SlowCooker/` | Slow Cooker |
| `Stovetop/` | Stovetop |
| `Oven/` | Oven |
| `Breakfast/`, `Snacks/`, `Shakes/`, `Desserts/`, `Baking/` | One chapter each |
| `Fakeaways/`, `Italian/` | Cooking-course recipes. Used by Palmer, and placed by method in `main.tex` |

Recipes converted from the Claude-made books start with a `% From ...` comment
saying where they came from. Those from `recipe_book.tex` have `--` for the time
because the original didn't give one.

## Adding a recipe made in Claude

1. Save it as `Folder/Recipe_Name.tex` (no spaces or `&` in the file name).
2. Add a line to the right chapter in `main.tex` (and any other book):

   ```latex
   \newpage
   \input{InstantPot/Recipe_Name}
   ```

Recipe files can use `recipebox`, `ingredients`, `method` (optionally
`\begin{method}[Rice (Rice Cooker)]` for a custom heading), `notes`,
`notelist`, `variationbox` and `\nutritiontable`.
