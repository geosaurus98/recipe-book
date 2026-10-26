// Browser tests for the meal planner. run_planner_tests.py opens the built
// planner with this file added at the end of the page (after a snippet that
// clears saved data and records errors), then collects the results. It
// drives the real page: every recipe, every tab, cooking mode, scaling, the
// shopping list and the day-by-day plan.
const results = { passed: 0, failed: [] };
const w = window;
const run = src => (0, eval)(src);  // global eval reaches the planner's own let/const variables
function check(name, ok, detail) {
  if (ok) results.passed++;
  else results.failed.push(detail === undefined ? name : `${name}: ${typeof detail === "string" ? detail : JSON.stringify(detail)}`);
}
function eq(name, got, want) { check(name, JSON.stringify(got) === JSON.stringify(want), { got, want }); }
function test(name, fn) {
  try { fn(); } catch (e) { results.failed.push(`${name}: threw ${e && e.stack || e}`); }
}
const wait = ms => new Promise(r => setTimeout(r, ms));
const $ = sel => document.querySelector(sel);
const click = el => el.dispatchEvent(new MouseEvent("click", { bubbles: true }));
const pageErrors = window.__errors;

async function main() {
  await wait(300);

  test("page loads", () => {
    check("week tab rendered", /Week of/.test($("#app").textContent), $("#app").textContent.slice(0, 200));
    check("recipes are embedded", run("RECIPES.length") > 150, run("RECIPES.length"));
    check("example week shown", run("state.example") === true);
  });

  test("example week uses recipes that exist", () => {
    for (const id of run("Object.values(EXAMPLE.slots).concat(Object.keys(EXAMPLE.days))"))
      check(`example recipe ${id}`, run(`!!BY_ID[${JSON.stringify(id)}]`));
  });

  test("tabs render", () => {
    for (const tab of ["recipes", "shop", "track", "week"]) {
      click(document.querySelector(`[data-tab="${tab}"]`));
      check(`${tab} tab has content`, $("#app").textContent.trim().length > 50);
    }
    click(document.querySelector('[data-tab="recipes"]'));
    check("every recipe has a card", document.querySelectorAll(".card").length === run("RECIPES.length"));
    click(document.querySelector('[data-tab="week"]'));
  });

  test("every recipe opens", () => {
    for (const id of run("RECIPES.map(r => r.id)")) {
      try {
        run(`ui.open = ${JSON.stringify(id)}; renderSheet();`);
        check(`sheet ${id}`, $("#sheet-title") && $("#sheet-title").textContent.trim().length > 0);
      } catch (e) { results.failed.push(`sheet ${id}: ${e}`); }
    }
    run("ui.open = null; renderSheet();");
  });

  test("cooking mode steps through every recipe", () => {
    for (const id of run("RECIPES.filter(r => cookSteps(r).length).map(r => r.id)")) {
      try {
        const n = run(`ui.cook = { id: ${JSON.stringify(id)}, step: 0, have: {} }; cookSteps(BY_ID[${JSON.stringify(id)}]).length`);
        for (let i = 0; i <= n; i++) run(`ui.cook.step = ${i}; cookView()`);
        check(`cook ${id}`, true);
      } catch (e) { results.failed.push(`cook ${id}: ${e}`); }
    }
    run("ui.cook = null; renderSheet();");
  });

  test("scaling", () => {
    eq("1½ cups x2", run(`scaleText("1½ cups stock", 2)`), "3 cups stock");
    eq("range x2", run(`scaleText("2–3 garlic cloves", 2)`), "4–6 garlic cloves");
    eq("can size kept", run(`scaleText("1 can (400 g) chopped tomatoes", 2)`), "2 can (400 g) chopped tomatoes");
    eq("half", run(`scaleText("**500 g** beef mince", 0.5)`), "**250 g** beef mince");
    eq("servings", run(`scaleServings("4 (8 burritos)", 2)`), "8 (16 burritos)");
    eq("portion size kept", run(`scaleServings("6 (about ½ cup each)", 2)`), "12 (about ½ cup each)");
  });

  test("adding up amounts", () => {
    eq("grams", run(`amountText([{qty:600,unit:"g"},{qty:500,unit:"g"}], "x")`), "1.1 kg");
    eq("spoons", run(`amountText([{qty:1,unit:"tbsp"},{qty:3,unit:"tsp"}], "x")`), "2 tbsp");
    eq("cans", run(`amountText([{qty:1,unit:"can"},{qty:2,unit:"can"}], "x")`), "3 cans");
  });

  test("sync sends only what changed", () => {
    eq("one tick", run(`diffState({checked:{a:true}, week:"w"}, {checked:{a:true,b:true}, week:"w"})`), [[["checked", "b"], true]]);
    eq("untick", run(`diffState({checked:{a:true}}, {checked:{}})`), [[["checked", "a"], null]]);
    eq("days sync per meal", run(`diffState({days:{x:1}}, {days:{x:2}})`), [[["days", "x"], 2]]);
  });

  // A real plan from here on.
  const slow = run(`RECIPES.find(r => r.chapter === "slow" && r.minutes && r.ahead.length).id`);
  const quick = run(`RECIPES.find(r => r.chapter === "stovetop" && r.minutes && r.meat && !r.ahead.length).id`);
  const pressure = run(`RECIPES.find(r => r.chapter === "pressure" && r.minutes).id`);
  run(`commit(s => { s.slots = { slow: ${JSON.stringify(slow)}, pressure: ${JSON.stringify(pressure)}, quick: ${JSON.stringify(quick)} };
    s.days = { [${JSON.stringify(slow)}]: 2, [${JSON.stringify(quick)}]: 0 }; s.dinner = "18:30"; })`);

  test("day by day", () => {
    const r = run(`BY_ID[${JSON.stringify(slow)}]`);
    eq("slow cooker start time", run(`startAt(BY_ID[${JSON.stringify(slow)}])`), Math.floor((18.5 * 60 - r.minutes) / 5) * 5);
    const tasks = run("dayTasks()");
    check("start reminder on its night", (tasks[2] || []).some(t => t.start && t.id === slow), tasks[2]);
    check("advance prep the night before", (tasks[1] || []).some(t => t.text.startsWith(r.ahead[0].replace(/\.$/, ""))), tasks[1]);
    check("Monday's defrost reminder lands on Sunday", (tasks[-1] || []).some(t => t.id === quick && /freezer|fridge/.test(t.text)), tasks[-1]);
    check("unscheduled meal has no reminders", !Object.values(tasks).flat().some(t => t.id === pressure));
    eq("time format", run("fmtTime(615)"), "10:15 am");
    run("commit(fillDays)");
    check("spread over the week gives the pressure meal a free night", [4, 6].includes(run(`state.days[${JSON.stringify(pressure)}]`)), run("state.days"));
    check("day section rendered", /Day by day/.test($("#app").textContent));
  });

  test("swapping a meal keeps its night", () => {
    click(document.querySelector('[data-act="shuffle-slot"][data-slot="slow"]'));
    const now = run("state.slots.slow");
    check("swapped", now !== slow);
    eq("night moved to the new meal", run(`state.days[${JSON.stringify(now)}]`), 2);
    check("old meal lost its night", run(`state.days[${JSON.stringify(slow)}]`) === undefined);
  });

  test("calendar file", () => {
    const ics = run("icsText()");
    const n = run("Object.values(dayTasks()).flat().length");
    eq("one event per reminder", (ics.match(/BEGIN:VEVENT/g) || []).length, n);
    check("lines are short enough", ics.split("\r\n").every(l => l.length <= 75));
    check("has alarms", /BEGIN:VALARM/.test(ics));
  });

  test("shopping list", () => {
    const groups = run("shoppingList()");
    const items = Object.values(groups).flat();
    check("has items", items.length > 10, items.length);
    const key = items.find(x => !x.optional).key;
    run(`commit(s => { s.pantry[${JSON.stringify(key)}] = true; })`);
    const name = items.find(x => x.key === key).name;
    check("at-home item left out of the copied list", !run("listText()").split("\n").some(l => l === `- ${name}` || l.startsWith(`- ${name} `)));
    click(document.querySelector('[data-tab="shop"]'));
    check("at home section shown", !!$(".at-home"));
    run("commit(s => { s.scale[s.slots.quick] = 2; })");
    check("scaled list still renders", document.querySelectorAll(".aisle").length > 0);
  });

  test("buttons on the week tab", () => {
    click(document.querySelector('[data-tab="week"]'));
    click($('[data-act="shuffle-all"]'));
    check("trio filled", run("Object.values(state.slots).every(Boolean)"));
    click($('[data-act="new-week"]'));
    check("new week clears the plan and nights", run("plannedIds().length === 0 && Object.keys(state.days).length === 0"));
  });

  test("food log", () => {
    eq("targets from profile", run(`calcTargets({ sex: "male", age: 27, height: 180, weight: 80, activity: "moderate", goal: "maintain" })`),
      { kcal: 2780, protein: 128, carbs: 394, fat: 77 });
    check("cut is lower than maintenance", run(`calcTargets({ sex: "female", age: 30, height: 165, weight: 65, activity: "light", goal: "lose" }).kcal`) <
      run(`calcTargets({ sex: "female", age: 30, height: 165, weight: 65, activity: "light", goal: "maintain" }).kcal`));
    eq("bad profile gives no targets", run(`calcTargets({ sex: "male", age: "", height: 180, weight: 80 })`), null);
    click(document.querySelector('[data-tab="track"]'));
    check("food log tab rendered", /Food log/.test($("#app").textContent));
    $("#tp-age").value = "27"; $("#tp-height").value = "180"; $("#tp-weight").value = "80";
    click($('[data-act="track-calc"]'));
    eq("targets saved", run("tracker.targets.protein"), 128);
    const id = run(`RECIPES.find(r => r.nutrition && r.nutrition.per === "serving").id`);
    const n = run(`BY_ID[${JSON.stringify(id)}].nutrition`);
    click($('[data-act="track-qty"][data-v="2"]'));
    run(`trackClick("track-recipe", { dataset: { id: ${JSON.stringify(id)} } })`);
    eq("two serves logged", run("Math.round(dayTotals(todayISO()).kcal)"), Math.round(n.kcal * 2));
    $("#qa-name").value = "Protein bar"; $("#qa-kcal").value = "200"; $("#qa-protein").value = "20";
    click($('[data-act="track-quick"]'));
    eq("quick add counted", run("Math.round(dayTotals(todayISO()).protein)"), Math.round(n.protein * 2) + 20);
    check("recent foods offered", document.querySelectorAll('[data-act="track-again"]').length === 2);
    click($('[data-act="track-del"]'));
    eq("entry removed", run("dayEntries(todayISO()).length"), 1);
    check("log is not part of the shared plan", run("!('days' in state && JSON.stringify(state).includes('Protein bar'))"));
    run(`ui.open = ${JSON.stringify(id)}; renderSheet();`);
    click($('[data-act="track-log"]'));
    eq("logged from the recipe", run("dayEntries(todayISO()).length"), 2);
    run("ui.open = null; renderSheet();");
    click($('[data-act="track-day"]'));
    check("previous day is empty", /Nothing logged/.test($("#app").textContent));
    run("ui.trackDay = null; ui.trackQty = 1;");
    click(document.querySelector('[data-tab="week"]'));
  });

  test("cost estimates", () => {
    const id = run(`RECIPES.find(r => r.id === "InstantPot-Beef_Lentil_Bolognese").id`);
    const c = run(`recipeCost(BY_ID[${JSON.stringify(id)}])`);
    check("costed", c && c.perServe > 1 && c.perServe < 10, c);
    run(`commit(s => { s.prices["beef-mince"] = 30; })`);
    const c2 = run(`recipeCost(BY_ID[${JSON.stringify(id)}])`);
    check("your price changes the cost", c2.total > c.total + 8, [c.total, c2.total]);
    run(`commit(s => { delete s.prices["beef-mince"]; })`);
    const costed = run("RECIPES.filter(r => recipeCost(r)).length");
    check("most recipes have a cost", costed > 190, costed);
    click(document.querySelector('[data-tab="recipes"]'));
    click($('[data-act="sort-cheap"]'));
    const costs = run("filteredRecipes().slice(0, 20).map(r => recipeCost(r)?.perServe ?? 99)");
    check("cheapest first", costs.every((v, i) => !i || v >= costs[i - 1]), costs);
    click($('[data-act="cheap"]'));
    check("cheap filter", run(`filteredRecipes().every(r => recipeCost(r).perServe <= CHEAP)`) && run("filteredRecipes().length") > 5);
    click($('[data-act="cheap"]')); click($('[data-act="sort-cheap"]'));
  });

  test("leftovers", () => {
    const slow = run(`RECIPES.find(r => r.chapter === "slow" && r.nutrition && r.nutrition.count === 4).id`);
    run(`commit(s => { s.slots.slow = ${JSON.stringify(slow)}; s.cooked = {}; s.leftovers = {}; s.eaters = 2; s.scale = {}; })`);
    click(document.querySelector('[data-tab="week"]'));
    const box = document.querySelector(`[data-act="cooked"][data-id="${slow}"]`);
    box.checked = true; box.dispatchEvent(new Event("change", { bubbles: true }));
    const lid = run(`Object.keys(state.leftovers)[0]`);
    eq("spare portions added", run(`state.leftovers[${JSON.stringify(lid)}].n`), 2);
    check("leftovers section shown", !!$(".leftover"));
    const before = run("dayEntries(todayISO()).length");
    click($(`[data-act="lo-eat"][data-lid="${lid}"]`));
    eq("one eaten", run(`state.leftovers[${JSON.stringify(lid)}].n`), 1);
    eq("logged in the food log", run("dayEntries(todayISO()).length"), before + 1);
    click($(`[data-act="lo-move"][data-lid="${lid}"]`));
    const frozen = run(`Object.entries(state.leftovers).find(([, l]) => l.where === "freezer")`);
    check("moved to the freezer", frozen && frozen[1].n === 1, run("state.leftovers"));
    eq("freezer keeps 90 days", run(`useBy(state.leftovers[${JSON.stringify(frozen[0])}])`), run(`isoAdd(todayISO(), 90)`));
    click($(`[data-act="lo-eat"][data-lid="${frozen[0]}"]`));
    eq("frozen portion must thaw first", run(`state.leftovers[${JSON.stringify(frozen[0])}].n`), 1);
    run(`commit(s => { s.leftovers = {}; })`);
    box.checked = false; document.querySelector(`[data-act="cooked"][data-id="${slow}"]`).dispatchEvent(new Event("change", { bubbles: true }));
    const b2 = document.querySelector(`[data-act="cooked"][data-id="${slow}"]`);
    b2.checked = true; b2.dispatchEvent(new Event("change", { bubbles: true }));
    document.querySelector(`[data-act="cooked"][data-id="${slow}"]`).checked = false;
    document.querySelector(`[data-act="cooked"][data-id="${slow}"]`).dispatchEvent(new Event("change", { bubbles: true }));
    eq("unticking takes today's leftovers back", run("Object.keys(state.leftovers).length"), 0);
    eq("sync sends one leftover at a time", run(`diffState({leftovers:{a:{n:1}}}, {leftovers:{a:{n:1},b:{n:2}}})`), [[["leftovers", "b"], { n: 2 }]]);
  });

  test("what can I make", () => {
    click(document.querySelector('[data-tab="recipes"]'));
    click($('[data-act="make-toggle"]'));
    check("make view shown", !!$(".make"));
    click($('[data-act="have-toggle"][data-key="beef-mince"]'));
    click($('[data-act="have-toggle"][data-key="frozen-mixed-veg"]'));
    const res = run("makeable().map(x => [x.r.id, x.score, x.r.shop.some(i => i.key === 'beef-mince' || i.key === 'frozen-mixed-veg')])");
    check("results use what you have", res.length > 3 && res.every(x => x[2]), res.slice(0, 5));
    check("best matches first", res.every((x, i) => !i || x[1] >= res[i - 1][1]), res.map(x => x[1]));
    check("your meat comes first", run("makeable()[0].r.shop.some(i => i.key === 'beef-mince')"));
    check("cards rendered", document.querySelectorAll(".make ~ .list .card").length === res.length);
    click($('[data-act="have-clear"]'));
    click($('[data-act="make-toggle"]'));
  });

  test("reading ingredient lines", () => {
    const p = t => run(`(() => { const x = parseIngredient(${JSON.stringify(t)}); return [x.key, x.qty, x.unit, x.optional]; })()`);
    eq("grams", p("500 g lean beef mince"), ["beef-mince", 500, "g", false]);
    eq("fraction", p("1/2 cup red lentils, rinsed"), ["red-lentils", 0.5, "cup", false]);
    eq("mixed number", p("1 1/2 cups jasmine rice"), ["jasmine-rice", 1.5, "cup", false]);
    eq("unicode fraction", p("1½ tbsp soy sauce"), ["soy-sauce", 1.5, "tbsp", false]);
    eq("cans", p("2 cans (400 g) black beans, drained"), ["black-beans", 2, "can", false]);
    eq("each", p("2 onions, diced"), ["onion", 2, "", false]);
    eq("to taste", p("Salt, to taste"), ["salt", null, "", true]);
    eq("kg", p("1.2 kg chicken thighs"), ["chicken-thigh", 1200, "g", false]);
    check("unknown ingredient still listed", p("3 tbsp gochujang")[0].startsWith("custom-") || p("3 tbsp gochujang")[0] === "gochujang");
  });

  test("adding a recipe in the planner", () => {
    w.confirm = () => true;
    click(document.querySelector('[data-tab="recipes"]'));
    click($('[data-act="custom-new"]'));
    $("#cf-title").value = "Test Pork & Bean Chilli";
    $("#cf-chapter").value = "slow";
    $("#cf-servings").value = "4";
    $("#cf-time").value = "15 min prep + 8 hr";
    $("#cf-ingredients").value = "Base:\n500 g pork mince\n1 onion, diced\n2 cans (400 g) kidney beans, drained\n1 can (400 g) chopped tomatoes\n2 tsp smoked paprika\nSalt, to taste";
    $("#cf-method").value = "Brown the mince.\nPut everything in the slow cooker.\nCook on low for 8 hours.";
    click($('[data-act="custom-save"]'));
    const id = run(`Object.keys(state.custom)[0]`);
    check("saved", !!id && run(`!!BY_ID[${JSON.stringify(id)}]`));
    const r = run(`BY_ID[${JSON.stringify(id)}]`);
    eq("minutes", r.minutes, 495);
    check("nutrition estimated", r.nutrition && r.nutrition.protein > 25 && r.nutrition.protein < 60, r.nutrition);
    check("costed", run(`recipeCost(BY_ID[${JSON.stringify(id)}]).perServe`) > 1);
    check("tagged pork and mince", r.tags.includes("pork") && r.tags.includes("mince"), r.tags);
    check("sheet open after saving", /Test Pork/.test($("#sheet-title").textContent));
    check("book export", /\\begin\{recipebox\}\{Test Pork \\& Bean Chilli\}\{4\}/.test(run(`customTex(${JSON.stringify(id)})`)) && /SlowCooker\/Test_Pork_and_Bean_Chilli/.test(run(`customTex(${JSON.stringify(id)})`)));
    run(`commit(s => { s.slots.slow = ${JSON.stringify(id)}; })`);
    check("on the shopping list", run(`Object.values(shoppingList()).flat().some(x => x.key === "item:kidney-beans")`));
    check("survives reloading", run(`sanitize(clone(state)).slots.slow`) === id);
    run(`ui.cook = { id: ${JSON.stringify(id)}, step: 0, have: {} }; cookView(); ui.cook = null; renderSheet();`);
    run(`ui.edit = ${JSON.stringify(id)}; ui.open = null; ui.editing = true; renderSheet();`);
    eq("edit form filled in", $("#cf-title").value, "Test Pork & Bean Chilli");
    click($('[data-act="custom-delete"]'));
    check("deleted", run(`!BY_ID[${JSON.stringify(id)}] && !state.custom[${JSON.stringify(id)}] && state.slots.slow === null`));
  });

  await (async () => {
    const realFetch = w.fetch;
    try {
      w.fetch = async url => ({ json: async () => /9415767012345/.test(url)
        ? { status: 1, product: { product_name: "Greek Yoghurt", brands: "Test Dairy", serving_quantity: 150, serving_size: "150 g", nutriments: { "energy-kcal_100g": 80, proteins_100g: 9, carbohydrates_100g: 5, fat_100g: 2.5 } } }
        : { status: 0 } });
      click(document.querySelector('[data-tab="track"]'));
      run("ui.trackMeal = 'snacks'");
      click($('[data-act="scan-open"]'));
      check("scanner opens", !!$("#scan-code"));
      $("#scan-code").value = "9415767012345";
      click($('[data-act="scan-lookup"]'));
      await wait(50);
      eq("product found", run("ui.scan && ui.scan.stage"), "found");
      eq("serving size suggested", $("#scan-grams").value, "150");
      const n = run("dayEntries(todayISO()).length");
      click($('[data-act="scan-add"]'));
      const e = run("dayEntries(todayISO()).slice(-1)[0]");
      eq("logged from the barcode", [e.name, e.kcal, e.protein, e.meal], ["Test Dairy Greek Yoghurt", 120, 14, "snacks"]);
      eq("one more entry", run("dayEntries(todayISO()).length"), n + 1);
      check("product remembered", run("!!tracker.foods['9415767012345']"));
      click($('[data-act="scan-open"]'));
      $("#scan-code").value = "9400000000001";
      click($('[data-act="scan-lookup"]'));
      await wait(50);
      eq("unknown product", run("ui.scan.stage"), "missing");
      click($('[data-act="close"]'));
      check("scanner closed", !run("ui.scan") && !$("#scan-code"));
    } catch (err) { results.failed.push("barcode: threw " + (err && err.stack || err)); }
    finally { w.fetch = realFetch; }
  })();

  test("weight and charts", () => {
    const t = run("todayISO()");
    run(`trackCommit(tr => {
      tr.weights = {};
      for (let i = 0; i < 30; i += 3) tr.weights[isoAdd(${JSON.stringify(t)}, -i)] = 84 - i * 0.05;
      for (let i = 1; i < 20; i++) tr.days[isoAdd(${JSON.stringify(t)}, -i)] = [{ name: "x", meal: i % 2 ? "lunch" : "dinner", kcal: 2000 + i * 20, protein: 120 + i, carbs: 200, fat: 60 }];
    })`);
    check("trend", Math.abs(run(`weightTrend(${JSON.stringify(t)})`) - 83.9) < 0.2, run(`weightTrend(${JSON.stringify(t)})`));
    click(document.querySelector('[data-tab="track"]'));
    check("weight chart", !!document.querySelector(".chart .trend"));
    check("calorie and protein charts", document.querySelectorAll(".chart .bar-mark").length >= 38);
    check("target line", !!document.querySelector(".chart .target"));
    check("no NaN in charts", !/NaN|undefined/.test([...document.querySelectorAll(".chart")].map(c => c.outerHTML).join("")));
    check("protein per meal", document.querySelectorAll(".per-meal li").length >= 2);
    check("suggests new targets", /Update my targets/.test($("#app").textContent), run("tracker.profile.weight"));
    click($('[data-act="weigh-retarget"]'));
    check("targets follow the trend", Math.abs(Number(run("tracker.profile.weight")) - 83.9) < 0.2);
    $("#weigh-kg").value = "83.5";
    click($('[data-act="weigh-save"]'));
    eq("weigh-in saved", run(`tracker.weights[${JSON.stringify(t)}]`), 83.5);
    click(document.querySelector('[data-tab="week"]'));
  });

  await wait(700);  // let any async errors surface
  check("no errors on the page", pageErrors.length === 0, pageErrors);
  try { localStorage.clear(); } catch {}
  report();
}
function report() {
  if (report.sent) return;
  report.sent = true;
  fetch(window.__report, { method: "POST", body: JSON.stringify(results) }).catch(() => {});
}
main().catch(e => { results.failed.push("harness: " + (e && e.stack || e)); report(); });
setTimeout(() => { results.failed.push("harness: timed out after 2 minutes"); report(); }, 120000);
