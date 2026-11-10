"""Run with:  python test_engine.py   (no extra libraries needed)"""
from decision import action_plan, differential, simulate, verdict
from engine import Engine
from rules import (CONCLUSIONS, DEFAULTS, HOME_ONLY, KNOWN_FACTS, POND_SYMPTOMS, RULES, SCENARIOS,
                   ICH_HEAT_STEP)

engine = Engine(RULES, CONCLUSIONS, KNOWN_FACTS)   # also validates every rule


def make_facts(scenario=None, **extra):
    preset = {**(SCENARIOS.get(scenario, {}) if scenario else {}), **extra}
    s = {k: preset.get(k, v) for k, v in DEFAULTS.items()}
    mode = preset.get("mode", "home")
    facts = {k: v for k, v in s.items() if k not in ("species_home", "species_pond")}
    if mode == "pond":
        facts.update({k: DEFAULTS[k] for k in HOME_ONLY if k not in POND_SYMPTOMS})
    facts["mode"] = mode
    facts["species_group"] = s["species_home"] if mode == "home" else s["species_pond"]
    facts["liters_per_fish"] = facts["tank_l"] / max(facts["fish_count"], 1)
    return facts


def shown_for(facts):
    return engine.run(facts).visible(0.5)


# scenario -> (must appear, must NOT appear, expected verdict)
EXPECTED = {
    None: ([], ["ich", "ammonia_present", "fin_rot"], "HEALTHY"),
    "New tank ammonia spike": (["ammonia_severe", "tank_not_cycled", "ammonia_burn", "overfeeding",
                                "decision_stop_feeding"], ["ich"], "EMERGENCY"),
    "Ich outbreak after buying new fish": (["ich", "parasites", "decision_treat_whole_tank"],
                                           ["ammonia_present"], "ACTION NEEDED"),
    "Betta in a cold bowl": (["temp_too_cold", "heater_problem", "cold_stress", "tank_too_small"],
                             ["ich"], "ACTION NEEDED"),
    "Old neglected tank": (["nitrate_severe", "fin_rot", "cloudy_eye", "overdue_water_change",
                            "decision_water_first"], ["ich"], "ACTION NEEDED"),
    "Betta with fin-nippers": (["incompat_nipper", "fin_damage_nipping", "bullying_stress",
                                "decision_separate"], ["fin_rot"], "ACTION NEEDED"),
    "Pond oxygen crash (aquaculture)": (["critical_low_do", "heat_stress", "oxygen_deficiency", "pond_ph_high",
                                         "decision_stop_feeding", "decision_get_expert"], ["ich"], "EMERGENCY"),
}

failures = 0
for name, (must, must_not, want_verdict) in EXPECTED.items():
    result = engine.run(make_facts(name))
    shown = result.visible(0.5)
    names = {n for n, _ in shown}
    got_verdict, _ = verdict(shown, CONCLUSIONS)
    missing = [m for m in must if m not in names]
    wrong = [m for m in must_not if m in names]
    ok = not missing and not wrong and got_verdict == want_verdict
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {name or 'Healthy default tank'}: verdict {got_verdict}, "
          f"{len(result.fired)} rules fired, {result.cycles} cycles")
    if missing:
        print("      missing:", missing)
    if wrong:
        print("      should NOT appear:", wrong)
    if got_verdict != want_verdict:
        print(f"      verdict should be {want_verdict}")


def check(label, condition):
    global failures
    failures += not condition
    print(f"{'PASS' if condition else 'FAIL'}  {label}")


# conflict resolution: severe ammonia hides plain ammonia
check("supersedes: severe ammonia hides 'ammonia detected'",
      "ammonia_present" not in {n for n, _ in shown_for(make_facts("New tank ammonia spike"))})
# certainty factors: two supporting rules give more than either alone
ich_cf = engine.run(make_facts("Ich outbreak after buying new fish")).derived["ich"]
check(f"CF combination: ich supported by 2 rules = {ich_cf:.2f} (> 0.90)", ich_cf > 0.90)
# differential diagnosis: competing causes of scratching are ranked
diffs = differential(shown_for(make_facts("Ich outbreak after buying new fish")), CONCLUSIONS)
check("differential: Ich ranked as most likely cause of scratching",
      diffs.get("Cause of scratching / spots", [("", 0)])[0][0] == "ich")
# decision: ich in hot water -> heat treatment removed from plan
hot_ich = shown_for(make_facts(white_spots=True, flashing=True, temp_c=32.0))
plan, removed = action_plan(hot_ich, CONCLUSIONS)
plan_steps = [s for steps in plan.values() for s, _ in steps]
check("decision: 'do not heat' cancels the Ich heat step",
      "caution_no_heat" in {n for n, _ in hot_ich} and ICH_HEAT_STEP not in plan_steps and removed)
# what-if: a 60% water change takes the ammonia-spike tank out of 'severe ammonia'
spike = make_facts("New tank ammonia spike")
after_facts, _ = simulate(spike, water_change_pct=60, aerate=True, feed_less=True)
after = {n for n, _ in shown_for(after_facts)}
check("what-if: 60% water change resolves severe ammonia",
      "ammonia_severe" not in after and "ammonia_severe" in {n for n, _ in shown_for(spike)})
# decision: symptoms with no explanation are never called HEALTHY
lonely = shown_for(make_facts(hiding=True))
check("verdict: unexplained symptom -> MONITOR (not HEALTHY)",
      verdict(lonely, CONCLUSIONS, symptoms_present=True)[0] == "MONITOR")
old = make_facts("Old neglected tank")
old_after, _ = simulate(old, water_change_pct=60)
check("what-if: old tank after water change -> MONITOR (fins/eyes still unhealthy)",
      verdict(shown_for(old_after), CONCLUSIONS, symptoms_present=True)[0] == "MONITOR")
# what-if: aerating the crashed pond lifts it out of critical oxygen
pond = make_facts("Pond oxygen crash (aquaculture)")
pond_after, _ = simulate(pond, aerate=True)
check("what-if: aeration resolves critical pond oxygen",
      "critical_low_do" not in {n for n, _ in shown_for(pond_after)})

print(f"\nRules: {len(RULES)}, conditions: {sum(len(r.conditions) for r in RULES)}")
print("ALL TESTS PASSED" if not failures else f"{failures} TEST(S) FAILED")
raise SystemExit(1 if failures else 0)
