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

### Scaling

Open any recipe in the planner and pick ½×, 1×, 1½×, 2× or 3× under
**Make**. The ingredient amounts and servings update, and for planned meals
the shopping list and weekly totals follow. Only the leading amount on each
ingredient line changes (so "2 cans (400 g)" becomes "4 cans (400 g)");
cooking times aren't adjusted.

### Favourites, ratings and history

Star recipes as favourites and rate them 1-5 in the planner. Ticking
**Cooked** on a planned meal logs the date (shown as "Cooked 3 times · last on
12 Oct") and asks for a rating. **Pick for me** and **Shuffle the trio** favour
favourites (3×) and well-rated recipes (4★ 2×, 5★ 3×), rarely pick 1-2★ ones,
and skip anything cooked in the last 28 days or planned in the last four
weeks.

### Cooking mode

**Start cooking** on any recipe opens a full-screen view: a "Get ready"
ingredient checklist, then one step at a time in large text with the
ingredients that step uses (at the chosen scale). Swipe, tap Next/Back or use
the arrow keys. Steps that mention a time get a one-tap timer that beeps and
vibrates, and the screen stays on while cooking mode is open (on browsers that
support it). Timers stop if the app is closed.

### Pantry

Tap **Have it** on a shopping-list item you always keep at home and it moves
to a collapsed **At home** section, off the list and out of the shared/copied
text, for every future week. **Spices & staples are at home** does the whole
"Pantry: check first" aisle at once. Ran out? Tap the item under **At home** to
put it back. The pantry syncs with the rest of the planner when sharing.

### Day by day

Under **Day by day** on the week tab, pick a night for each meal (or tap
**Spread over the week**). Set your dinner time, and the planner uses each
recipe's cooking time to say when to start: "Get the slow cooker going:
11:15 am". The night before, it reminds you of the recipe's advance prep, or
to move the meat from the freezer to the fridge. Today's jobs show in a box at
the top of the planner. **Add to calendar** downloads a calendar file with an
alert for each reminder. Swapping a meal keeps its night, and the nights sync
when sharing. Recipes with no time in the book use a typical time (8 hr slow
cooker, 50 min pressure cooker, 30–45 min quick) and say it's a guess.

### Food log

The **Food log** tab tracks calories, protein, carbs and fat for each day
against your own targets. Under **Your targets**, enter sex, age, height,
weight, activity and goal and tap **Work them out**: calories come from the
Mifflin-St Jeor formula (about 20% below maintenance to lose weight, 300 kcal
above to build muscle), protein is 1.6-2 g per kg of body weight, fat is 25%
of calories and carbs are the rest. Every number can then be changed by hand.

Add food by searching your recipes (½, 1, 1½ or 2 serves, using each recipe's
estimate), tapping a meal planned for that night, re-adding something from
**Recent**, or **Quick add** for anything else (type its calories and
macros). **Log a serve** on any recipe adds one serve to today. Entries are
grouped into breakfast, lunch, dinner and snacks, and **Last 7 days** shows
daily calories and protein with a tick for days on target.

The log is private to each device: it's stored separately from the meal
plan, so it isn't shared with your household or synced between devices.

**Scan a barcode** opens the camera (or type the number under the barcode)
and looks the product up in [Open Food Facts](https://world.openfoodfacts.org),
a free shared database; enter how many grams you had. Products you've found
are remembered on the device. Scanning uses the browser's barcode reader
where there is one (Chrome on Android) and otherwise loads ZXing from
jsDelivr, so the first scan needs a signal.

**Weight** logs a weigh-in for the day and charts the last 12 weeks, with a
line for the 7-day average. If that trend is 2 kg or more away from the
weight your targets use, it offers to update them. **Last 4 weeks** charts
daily calories and protein against your targets and shows your average
protein at each meal.

### Leftovers and freezer

Ticking **Cooked** on a planned meal puts the spare portions in
**Leftovers** on the week tab (servings, times the scale, minus the number of
people eating each meal, which you can set there). Each lot shows where it is
and when to eat it by: 3 days in the fridge, about 3 months frozen. **Eat
one** takes a portion and logs it in your food log; **Freeze** and **Thaw in
fridge** move it and restart the clock. Fridge leftovers also appear in the
food log's Add food. Leftovers are shared with your household. Unticking
Cooked the same day takes them back off.

### Costs

Every recipe shows a rough cost per serve, the week tab and shopping list
show what the week's ingredients cost, and the recipe filters include
**Under $3 a serve** and **Cheapest first**. Costs are worked out from the
weight of each ingredient (the same weights the nutrition estimates use) and
rough NZ prices per kg in `planner/prices.py`. They count what the recipe
uses, not whole packets. Change any price under **Shopping > Prices**; your
prices are saved and shared with your household. Add a line to `prices.py`
for an ingredient that isn't priced yet.

### What can I make?

On the Recipes tab, **What can I make?** lists the main ingredients from your
recipes to tick off. Recipes that use them are ranked by how few other things
they need, with ones using your meat first. Spices, oils, sauces, stock and
anything in your pantry count as had unless you untick that.

### Adding recipes in the planner

**Add a recipe** on the Recipes tab saves a recipe in the planner itself:
name, chapter, servings, time, ingredients (one per line, amount first) and
method. It's shared with your household and works like any other recipe:
planning, the shopping list, cooking mode, costs and the food log. Nutrition
is estimated from the ingredients unless you type it in. To put it in the
PDF, open it and tap **Copy for the book**: that copies the recipe as LaTeX
with the file name and `add_to_book.py` command at the top. Save it in that
folder, run the command, and delete the planner copy once the book version
is published.

### George's and GP's planners

**Planning for** at the top switches between George's planner and GP's. GP's
planner only shows basic recipes: everything in GP's Recipe Book, plus
recipes that take 45 minutes or less with 14 ingredients or fewer and don't
use the slow cooker or Instant Pot (about 77 recipes). Its week is three easy
dinners instead of the slow cooker / pressure cooker / quick trio. Each
planner has its own week, shopping list, favourites, leftovers, prices, added
recipes and food log, saved separately on the device and, when sharing, in
its own copy of the household. The share link opens whichever planner you
shared from (it ends in `&as=gp` for GP's), and a link ending in `#as=gp`
opens GP's planner directly. The limits are `BASIC_MINUTES` and
`BASIC_INGREDIENTS` in `planner/template.html`.

### Sharing between people

With Firebase set up, a **Share** button appears in the planner's header. It
creates a household link; everyone who opens it sees the same week, shopping
list ticks, scales, favourites and ratings, live. Changes are sent as small
updates, so two people ticking items at once don't overwrite each other, and
each device keeps its own copy for offline use. **Stop sharing on this
device** leaves the household.

One-time setup (free Firebase Spark plan):

1. At <https://console.firebase.google.com>, add a project (Analytics off).
2. **Build > Firestore Database > Create database**, production mode, a nearby
   location (e.g. `australia-southeast1`).
3. On its **Rules** tab, paste `firestore.rules` from this repo and publish.
4. **Project settings > Your apps > Web (`</>`)**, register an app, and copy
   the `firebaseConfig` values into `planner/sync-config.json`:

   ```json
   { "apiKey": "...", "authDomain": "...", "projectId": "...",
     "storageBucket": "...", "messagingSenderId": "...", "appId": "..." }
   ```

These values identify the project rather than grant access, so they're safe
to commit; the rules are what protect the data. Households can only be read
or changed by someone with their link.

## Website

Every push to `main` runs `.github/workflows/publish.yml`, which rebuilds the
planner, compiles `main.tex` and `Palmer Recipe Book.tex` to PDF, and publishes
them to GitHub Pages:

- Planner: <https://geosaurus98.github.io/recipe-book/>
- Books: [`books/main.pdf`](https://geosaurus98.github.io/recipe-book/books/main.pdf)
  and [`books/palmer.pdf`](https://geosaurus98.github.io/recipe-book/books/palmer.pdf)

So there's no need to run `build.py` before pushing, though it's handy for
checking changes locally. Progress and errors show on the repo's Actions tab.

Before publishing, the workflow runs two sets of checks, and a failure stops
the site from updating (the Actions tab shows what broke):

- `python -m unittest discover tests` checks every recipe file parses, has
  ingredients and steps, uses known aisles and gets a sensible nutrition
  estimate, and that both books only include files that exist.
- `python tests/run_planner_tests.py` opens the built planner in headless
  Chrome (or Edge) and works through it: every recipe and cooking-mode step,
  scaling, the shopping list and pantry, sync updates, the day-by-day plan and
  calendar file. Run `python planner/build.py` first when running it locally.

The planner works as a home-screen app: open the planner link on your phone,
then use **Share → Add to Home Screen** (iPhone, in Safari) or **⋮ → Add to
Home screen** (Android, in Chrome). It opens full-screen and still works with
no signal. The icon is drawn by `tools/make_icons.py` (needs Pillow); the app
settings are in `planner/manifest.webmanifest` and `planner/sw.js`. If you
change `sw.js`, bump the `CACHE` name in it so phones pick up the new version.
