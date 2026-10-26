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
