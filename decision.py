"""
decision.py - the DECISION-MAKING and DECISION-SUPPORT layer of AquaDoc.

The engine (engine.py) answers "WHAT is wrong?"  (inferencing + diagnosis).
This file answers "WHAT SHOULD WE DO, and in what order?":

    1. verdict()       - DECISION: overall status (EMERGENCY / ACTION NEEDED / MONITOR / HEALTHY)
    2. differential()  - DECISION: which disease most likely explains a symptom
    3. action_plan()   - SUPPORT:  prioritised plan (Now / 24 h / week), unsafe advice removed
    4. simulate()      - SUPPORT:  what-if analysis - change the facts, re-run the engine
"""
from engine import SEVERITY_RANK

URGENCY_ORDER = ["now", "24h", "week"]
URGENCY_LABEL = {"now": "🔴 Do now", "24h": "🟠 Within 24 hours", "week": "🔵 This week"}
# Root causes first: decisions, then tank/water problems, then fish diagnoses.
KIND_ORDER = {"decision": 0, "problem": 1, "diagnosis": 2}

VERDICTS = {   # verdict -> (icon, streamlit message style, explanation)
    "EMERGENCY": ("🚨", "error", "Act immediately - the fish are in danger."),
    "ACTION NEEDED": ("⚠️", "warning", "Problems found - follow the action plan today."),
    "MONITOR": ("👀", "info", "Minor issues only - fix them this week and keep testing."),
    "HEALTHY": ("✅", "success", "No problems found - keep up regular care and weekly tests."),
}
EMERGENCY_CF = 0.70   # a critical conclusion must be at least this certain to declare an emergency
UNEXPLAINED = ("Symptoms are present but no rule fully explains them - observe the fish closely, "
               "re-test the water within 24 hours, and consult an expert if they persist.")


def verdict(shown, conclusions, symptoms_present=False):
    """Decide the overall status. `shown` is the engine's sorted list of (name, cf).
    Returns (verdict, name of the conclusion that caused it).
    A tank is never called HEALTHY while the fish still show symptoms."""
    if not shown:
        return ("MONITOR", None) if symptoms_present else ("HEALTHY", None)
    for name, cf in shown:
        if conclusions[name]["severity"] == "critical" and cf >= EMERGENCY_CF:
            return "EMERGENCY", name
    for name, cf in shown:
        if conclusions[name]["urgency"] in ("now", "24h"):
            return "ACTION NEEDED", name
    return "MONITOR", shown[0][0]


def differential(shown, conclusions):
    """For every symptom group with 2+ competing diagnoses, rank them by confidence.
    Returns {group: [(name, cf), ...]} with the most likely first."""
    groups = {}
    for name, cf in shown:
        group = conclusions[name].get("differential")
        if group:
            groups.setdefault(group, []).append((name, cf))
    return {g: sorted(items, key=lambda i: -i[1]) for g, items in groups.items() if len(items) > 1}


def action_plan(shown, conclusions):
    """Merge the advice of all conclusions into one ordered, de-duplicated plan.
    Advice that another conclusion marks as unsafe ('cancels') is removed.
    Returns ({urgency: [(step, from_title)]}, [(removed_step, because_title)])."""
    present = {name for name, _ in shown}
    cancelled = {}
    for name in present:
        for step in conclusions[name]["cancels"]:
            cancelled[step] = conclusions[name]["title"]

    ordered = sorted(shown, key=lambda item: (
        KIND_ORDER[conclusions[item[0]]["kind"]],
        SEVERITY_RANK[conclusions[item[0]]["severity"]], -item[1]))
    plan, seen = {u: [] for u in URGENCY_ORDER}, set()
    for name, _ in ordered:
        info = conclusions[name]
        for step in info["advice"]:
            if step in seen or step in cancelled:
                continue
            seen.add(step)
            plan[info["urgency"]].append((step, info["title"]))
    removed = [(step, why) for step, why in cancelled.items()
               if any(step in conclusions[n]["advice"] for n in present)]
    return plan, removed


def simulate(facts, water_change_pct=0, aerate=False, ideal_temp=None, feed_less=False):
    """What-if analysis: return a COPY of the facts after the chosen actions,
    plus a list describing what was changed. The engine is then simply re-run."""
    new, changes = dict(facts), []
    if water_change_pct:
        keep = 1 - water_change_pct / 100
        for p in ("ammonia", "nitrite", "nitrate"):
            new[p] = round(facts[p] * keep, 2)
        new["water_change_days"] = 0
        changes.append(f"{water_change_pct}% water change: ammonia {facts['ammonia']} → {new['ammonia']}, "
                       f"nitrite {facts['nitrite']} → {new['nitrite']}, nitrate {facts['nitrate']} → {new['nitrate']}")
    if aerate:
        new["aerated"] = True
        if facts["mode"] == "pond":
            new["dissolved_oxygen"] = round(facts["dissolved_oxygen"] + 2.0, 1)
            changes.append(f"Aeration on: dissolved oxygen assumed to rise by 2 mg/L "
                           f"({facts['dissolved_oxygen']} → {new['dissolved_oxygen']})")
        else:
            changes.append("Air stone / surface movement turned on")
    if ideal_temp is not None:
        new["temp_c"] = ideal_temp
        changes.append(f"Temperature corrected: {facts['temp_c']} → {ideal_temp} °C")
    if feed_less:
        new["feedings_per_day"], new["uneaten_food"] = 1, False
        changes.append("Feeding reduced to once a day, leftovers removed")
    return new, changes
