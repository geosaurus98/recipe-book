"""Checks on the recipe files and what planner/build.py makes from them.

Run with:  python -m unittest discover tests
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "planner"))

import build  # noqa: E402

AISLES = {"Meat & fish", "Fruit & veg", "Dairy, eggs & chilled", "Frozen", "Bread & wraps",
          "Pasta, rice & grains", "Cans, jars & pulses", "Baking", "Pantry: check first", None}


def book_inputs(name):
    return re.findall(r"^\s*\\input\{(.*)\}", (ROOT / name).read_text(encoding="utf-8"), re.M)


class Recipes(unittest.TestCase):
    """Every recipe in main.tex, parsed the same way the build does."""

    @classmethod
    def setUpClass(cls):
        cls.recipes = []
        for inp in book_inputs("main.tex"):
            path = ROOT / (inp + ".tex")
            if not path.exists() or "\\begin{recipebox}" not in path.read_text(encoding="utf-8"):
                continue
            r = build.parse_recipe(path)
            r["file"] = inp
            r["shop"] = build.shop_items(r)
            cls.recipes.append(r)

    def test_books_only_include_files_that_exist(self):
        for book in ("main.tex", "Palmer Recipe Book.tex"):
            for inp in book_inputs(book):
                with self.subTest(book=book, file=inp):
                    self.assertTrue((ROOT / (inp + ".tex")).exists() or (ROOT / inp).exists())

    def test_every_recipe_has_a_title_ingredients_and_steps(self):
        self.assertGreater(len(self.recipes), 150)
        for r in self.recipes:
            with self.subTest(r["file"]):
                self.assertTrue(r["title"].strip())
                self.assertTrue(r["servings"].strip())
                self.assertTrue(r["shop"], "no ingredients found")
                self.assertTrue(any(s["kind"] == "steps" for s in r["sections"]), "no method steps found")

    def test_titles_have_no_leftover_latex(self):
        for r in self.recipes:
            with self.subTest(r["file"]):
                self.assertNotRegex(r["title"], r"\\[a-zA-Z]|[{}]")

    def test_ingredients_go_in_known_aisles(self):
        for r in self.recipes:
            for s in r["shop"]:
                with self.subTest(r["file"], item=s["raw"]):
                    self.assertIn(s["aisle"], AISLES)
                    self.assertRegex(s["key"], r"^[a-z0-9-]+$")

    def test_nutrition_estimates_are_sensible(self):
        for r in self.recipes:
            n = build.estimate(r["shop"], r["servings"])
            if not n:
                continue
            with self.subTest(r["file"], kcal=n["kcal"], per=n["per"]):
                self.assertGreater(n["kcal"], 20)
                self.assertLess(n["kcal"], 1700 if n["per"] == "serving" else 900)
                # Calories should roughly match 4/4/9 kcal per gram of protein, carbs and fat.
                macros = n["protein"] * 4 + n["carbs"] * 4 + n["fat"] * 9
                self.assertLess(abs(macros - n["kcal"]), max(40, n["kcal"] * 0.3))


class Helpers(unittest.TestCase):
    def test_minutes(self):
        self.assertEqual(build.minutes("15 min prep + 10 min"), 25)
        self.assertEqual(build.minutes("15 min prep + 7–8 hr (low)"), 495)
        self.assertEqual(build.minutes("Prep 15 min, Cook 45 min"), 60)
        self.assertEqual(build.minutes("20–25 min"), 25)
        self.assertIsNone(build.minutes("–"))

    def test_ahead_notes_find_the_night_before_jobs(self):
        r = {"sections": [{"kind": "text", "text": "**Advance prep:** defrost the pork in the fridge the night before. The edamame goes in from frozen."},
                          {"kind": "list", "items": [{"text": "Thaw overnight in the fridge and reheat until steaming."}]}]}
        self.assertEqual(build.ahead_notes(r), ["Defrost the pork in the fridge the night before."])

    def test_freezer_tag_can_be_turned_off_by_a_comment(self):
        jerky = ROOT / "Snacks" / "Oven_Beef_Jerky.tex"
        r = build.parse_recipe(jerky)
        r["shop"] = build.shop_items(r)
        self.assertNotIn("freezes", build.diet_tags(r, r["tagOverrides"]))


if __name__ == "__main__":
    unittest.main()


class Ingredients(unittest.TestCase):
    def test_split_peas_are_not_frozen_peas(self):
        import ingredients
        self.assertEqual(ingredients.parse("1 cup dry yellow split peas, rinsed")["key"], "split-peas")
        self.assertEqual(ingredients.parse("1 cup frozen peas")["key"], "frozen-peas")
        self.assertEqual(ingredients.parse("1 cup peas")["key"], "frozen-peas")

    def test_prices_are_sensible(self):
        from prices import PRICES
        for key, price in PRICES.items():
            self.assertTrue(0 < price < 200, f"{key}: ${price}/kg")
