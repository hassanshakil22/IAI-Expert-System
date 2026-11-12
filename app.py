"""
app.py - the Streamlit USER INTERFACE of AquaDoc.
Run with:  streamlit run app.py

The UI only: (1) collects facts, (2) calls the engine (inferencing + diagnosis)
and the decision layer (decision making + decision support), (3) shows the answer.
"""
import zlib

import pandas as pd
import streamlit as st

from decision import (UNEXPLAINED, URGENCY_LABEL, URGENCY_ORDER, VERDICTS, action_plan, differential,
                      simulate, verdict)
from engine import Engine
from rules import (CATEGORIES, CONCLUSIONS, DEFAULTS, HOME_ONLY, HOME_SPECIES, IDEAL_TEMP, KNOWN_FACTS,
                   POND_SPECIES, POND_SYMPTOMS, RULES, SCENARIOS, SOURCES, SYMPTOMS, TANKMATES)

st.set_page_config(page_title="AquaDoc - Expert & Decision Support System", page_icon="🐟", layout="wide")


# Built on every run (it takes milliseconds), so edits to rules.py show up immediately.
engine = Engine(RULES, CONCLUSIONS, KNOWN_FACTS)
HOME_LABEL, POND_LABEL = "🏠 Home aquarium", "🌾 Aquaculture pond (preview)"
SEVERITY_ICON = {"critical": "🔴", "warning": "🟠", "info": "🔵"}
KIND_ICON = {"decision": "🧭", "problem": "💧", "diagnosis": "🩺"}

# Every input gets its value from session state (so demo cases can fill them in)
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)
st.session_state.setdefault("mode_label", HOME_LABEL)
st.session_state.setdefault("scenario", "- choose a demo case -")


def load_scenario():
    """Callback: fill every input from the chosen demo scenario."""
    name = st.session_state["scenario"]
    if name not in SCENARIOS:
        return
    preset = SCENARIOS[name]
    for key, value in DEFAULTS.items():
        st.session_state[key] = preset.get(key, value)
    st.session_state["mode_label"] = POND_LABEL if preset.get("mode") == "pond" else HOME_LABEL


# A link such as  ...?demo=Old neglected tank  opens straight into that demo case (once)
_demo = st.query_params.get("demo")
if _demo in SCENARIOS and not st.session_state.get("_demo_applied"):
    st.session_state["scenario"] = _demo
    load_scenario()
    st.session_state["_demo_applied"] = True


def title_cf(name, cf):
    return f"{CONCLUSIONS[name]['title']} ({cf:.0%})"


# ----------------------------------------------------------------------------- sidebar
with st.sidebar:
    st.title("🐟 AquaDoc")
    st.caption("Expert system & decision support system for aquarium and fish-farm diagnosis")
    st.radio("Mode", [HOME_LABEL, POND_LABEL], key="mode_label",
             help="The same engine works for both modes - only the rules that apply change. "
                  "This is how the system scales to fish farms.")
    st.selectbox("Load a demo case", ["- choose a demo case -", *SCENARIOS], key="scenario",
                 on_change=load_scenario)
    min_cf = st.slider("Show conclusions above confidence", 0, 100, 50, 5, format="%d%%") / 100
    st.divider()
    total_conditions = sum(len(r.conditions) for r in RULES)
    st.metric("Rules in knowledge base", len(RULES))
    st.metric("Total conditions", total_conditions)
    st.caption("Advice is educational and based on published guidelines. "
               "For valuable stock consult an aquatic vet.")

mode = "home" if st.session_state["mode_label"] == HOME_LABEL else "pond"
S = st.session_state

tab_diag, tab_whatif, tab_how, tab_kb, tab_about = st.tabs(
    ["🩺 Diagnose & decide", "🧪 What-if analysis", "🔍 How? (rule trace)", "📚 Knowledge base", "ℹ️ About"])

# ============================================================================= INPUT
with tab_diag:
    st.header("1. Describe your " + ("tank" if mode == "home" else "pond"))
    c1, c2, c3 = st.columns(3)

    with c1:
        st.subheader("💧 Water test")
        st.slider("pH", 4.0, 10.0, step=0.1, key="ph",
                  help="Why we ask: pH decides how toxic ammonia is and which species are comfortable.")
        st.number_input("Ammonia (ppm / mg/L)", 0.0, 10.0, step=0.05, format="%.2f", key="ammonia",
                        help="Why we ask: ammonia is the #1 killer of aquarium fish.")
        st.number_input("Nitrite (ppm / mg/L)", 0.0, 10.0, step=0.05, format="%.2f", key="nitrite",
                        help="Why we ask: nitrite shows whether the filter bacteria are working.")
        st.number_input("Nitrate (ppm / mg/L)", 0.0, 500.0, step=5.0, key="nitrate",
                        help="Why we ask: nitrate builds up between water changes.")
        st.number_input("Temperature (°C)", 0.0, 45.0, step=0.5, key="temp_c",
                        help="Why we ask: every species has a comfortable temperature range.")
        if mode == "pond":
            st.number_input("Dissolved oxygen (mg/L)", 0.0, 20.0, step=0.5, key="dissolved_oxygen",
                            help="Why we ask: low oxygen is the main cause of fish kills in ponds.")

    with c2:
        st.subheader("🐠 Fish & equipment")
        if mode == "home":
            st.selectbox("Main fish type", HOME_SPECIES, key="species_home")
            st.number_input("Tank size (litres)", 5, 5000, step=5, key="tank_l",
                            help="Why we ask: small tanks cannot dilute waste.")
            st.number_input("Number of fish", 1, 500, key="fish_count",
                            help="Why we ask: stocking level, and whether sick fish should be isolated.")
            st.number_input("Tank age (weeks)", 0, 520, key="tank_age_weeks",
                            help="Why we ask: tanks under ~6 weeks are usually not cycled.")
            st.checkbox("Heater installed and working", key="heater")
            st.checkbox("Filter running", key="filter_running")
            st.checkbox("Air stone / surface movement", key="aerated")
        else:
            st.selectbox("Farmed species", POND_SPECIES, key="species_pond")
            st.checkbox("Aerator / paddlewheel running", key="aerated")

    with c3:
        if mode == "home":
            st.subheader("🧹 Care routine")
            st.number_input("Days since last water change", 0, 365, key="water_change_days")
            st.number_input("Feedings per day", 0, 10, key="feedings_per_day")
            st.number_input("Light hours per day", 0, 24, key="light_hours")
            st.checkbox("Uneaten food left in tank", key="uneaten_food")
            st.checkbox("Use a tap-water dechlorinator", key="uses_dechlorinator")
            st.checkbox("New fish added in last 2 weeks", key="new_fish_recent")
        else:
            st.subheader("🌾 Pond mode")
            st.info("A small preview showing how the same engine extends to aquaculture "
                    "with extra rules and species.")

    symptom_keys = list(SYMPTOMS) if mode == "home" else POND_SYMPTOMS
    with st.expander("🩺 Symptoms and what you see", expanded=True):
        cols = st.columns(3)
        for i, key in enumerate(symptom_keys):
            cols[i % 3].checkbox(SYMPTOMS[key], key=key)
    if mode == "home":
        with st.expander("🐟 Tankmates present"):
            cols = st.columns(3)
            for i, (key, label) in enumerate(TANKMATES.items()):
                cols[i % 3].checkbox(label, key=key)

# ---- build the fact base and run the engine -------------------------------------
facts = {k: S[k] for k in DEFAULTS if k not in ("species_home", "species_pond")}
if mode == "pond":
    facts.update({k: DEFAULTS[k] for k in HOME_ONLY if k not in POND_SYMPTOMS})
facts["mode"] = mode
facts["species_group"] = S["species_home"] if mode == "home" else S["species_pond"]
facts["liters_per_fish"] = facts["tank_l"] / max(facts["fish_count"], 1)

symptoms_present = any(facts[s] for s in SYMPTOMS)
result = engine.run(facts)                      # INFERENCING + DIAGNOSIS
shown = result.visible(min_cf)
status, reason = verdict(shown, CONCLUSIONS, symptoms_present)    # DECISION MAKING
plan, removed = action_plan(shown, CONCLUSIONS)  # DECISION SUPPORT
diffs = differential(shown, CONCLUSIONS)
cf_of = dict(shown)

# ============================================================================= RESULTS
with tab_diag:
    st.divider()
    st.header("2. Decision")
    icon, style, explanation = VERDICTS[status]
    message = f"### {icon} {status}\n{explanation}"
    if reason:
        message += f"\n\n**Main reason:** {title_cf(reason, cf_of[reason])}"
    elif status == "MONITOR":
        message += f"\n\n{UNEXPLAINED}"
    getattr(st, style)(message)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Problems & diagnoses", sum(1 for n, _ in shown if CONCLUSIONS[n]["kind"] != "decision"))
    m2.metric("Decisions made", sum(1 for n, _ in shown if CONCLUSIONS[n]["kind"] == "decision"))
    m3.metric("Rules fired", len(result.fired))
    m4.metric("Inference cycles", result.cycles)

    decisions = [(n, cf) for n, cf in shown if CONCLUSIONS[n]["kind"] == "decision"]
    if decisions:
        st.subheader("🧭 Decisions made by the system")
        for name, cf in decisions:
            info = CONCLUSIONS[name]
            st.markdown(f"- {SEVERITY_ICON[info['severity']]} **{info['title']}** ({cf:.0%}) - {info['meaning']}")

    if diffs:
        st.subheader("🔎 Most likely cause (differential diagnosis)")
        for group, items in diffs.items():
            (best, best_cf), others = items[0], items[1:]
            st.markdown(f"- **{group}:** {title_cf(best, best_cf)} - less likely: "
                        + ", ".join(title_cf(n, cf) for n, cf in others))

    if shown:
        st.header("3. Action plan")
        st.caption("Ordered by urgency, fixing root causes (water) before symptoms. "
                   "Tick actions as you complete them - the final decision stays with you.")
        for urgency in URGENCY_ORDER:
            if plan[urgency]:
                st.markdown(f"**{URGENCY_LABEL[urgency]}**")
                for step, source in plan[urgency]:
                    st.checkbox(f"{step} - *{source}*", key=f"plan_{zlib.crc32(step.encode())}")
        for step, because in removed:
            st.warning(f"Removed from the plan: *\"{step}\"* - unsafe because: **{because}**.")

        st.header("4. Detailed findings")
        for name, cf in shown:
            info = CONCLUSIONS[name]
            if info["kind"] == "decision":
                continue
            with st.container(border=True):
                top, bar = st.columns([4, 1])
                top.markdown(f"**{SEVERITY_ICON[info['severity']]} {KIND_ICON[info['kind']]} {info['title']}**")
                bar.progress(cf, text=f"Confidence {cf:.0%}")
                top.caption(f"{info['kind'].capitalize()} - {info['meaning']}")
                st.caption("Based on rules: " + ", ".join(f.rule.id for f in result.why(name)))

# ============================================================================= WHAT-IF
with tab_whatif:
    st.header("What-if analysis")
    st.write("Try an action **before** doing it: the system changes the facts, runs the inference "
             "engine again and shows how its decision would change.")
    w1, w2 = st.columns(2)
    label = "Water change (%)" if mode == "home" else "Pond water exchange (%)"
    wc = w1.slider(label, 0, 90, 0, 10, key="wi_water")
    aerate = w1.checkbox("Turn on aeration" if mode == "home" else "Run aerators", key="wi_aerate")
    ideal = IDEAL_TEMP[facts["species_group"]]
    fix_temp = w2.checkbox(f"Correct temperature to {ideal} °C (ideal for {facts['species_group']})",
                           key="wi_temp")
    feed_less = (w2.checkbox("Feed once a day and remove leftovers", key="wi_feed")
                 if mode == "home" else False)

    new_facts, changes = simulate(facts, wc, aerate, ideal if fix_temp else None, feed_less)
    after = engine.run(new_facts).visible(min_cf)
    status_after, _ = verdict(after, CONCLUSIONS, symptoms_present)

    b1, b2 = st.columns(2)
    change = len(after) - len(shown)
    b1.metric("Decision now", f"{VERDICTS[status][0]} {status}")
    b1.caption(f"{len(shown)} conclusions")
    b2.metric("Decision after these actions", f"{VERDICTS[status_after][0]} {status_after}",
              f"{change:+d} conclusions" if change else None, delta_color="inverse")
    b2.caption(f"{len(after)} conclusions")
    if not changes:
        st.info("Choose one or more actions above to see their effect.")
    else:
        st.markdown("**Simulated changes:** " + "; ".join(changes))
        before_set, after_set = {n for n, _ in shown}, {n for n, _ in after}
        r1, r2, r3 = st.columns(3)
        r1.markdown("**✅ Resolved**\n" + "".join(f"\n- {CONCLUSIONS[n]['title']}" for n in before_set - after_set))
        r2.markdown("**⏳ Still present**\n" + "".join(f"\n- {CONCLUSIONS[n]['title']}" for n in before_set & after_set))
        r3.markdown("**🆕 New**\n" + "".join(f"\n- {CONCLUSIONS[n]['title']}" for n in after_set - before_set))
        st.caption("Symptoms you ticked (e.g. white spots) stay the same in the simulation - fish take days "
                   "to recover, so diagnoses based on symptoms remain until they do.")

# ============================================================================= HOW?
with tab_how:
    st.header("How did the system reach its conclusions?")
    st.write("**Forward chaining:** in every cycle the engine finds all rules whose IF part is true and "
             "fires them. New conclusions can trigger more rules in the next cycle (e.g. *poor water* → "
             "*fin rot* → *fix the water before medicating*) until nothing new is learned.")
    if result.fired:
        st.dataframe(pd.DataFrame([{
            "Cycle": f.cycle, "Rule": f.rule.id,
            "IF (evidence)": " AND ".join(f.evidence),
            "THEN": CONCLUSIONS[f.rule.conclusion]["title"],
            "Confidence": f"{f.cf:.0%}", "Source": f.rule.source} for f in result.fired]),
            width="stretch", hide_index=True)

        st.subheader("Explain one conclusion")
        pick = st.selectbox("Conclusion", list(result.derived),
                            format_func=lambda n: title_cf(n, result.derived[n]))

        def explain(name, depth=0):
            for f in result.why(name):
                st.markdown("&nbsp;" * 6 * depth + f"**{f.rule.id}**: IF " + " AND ".join(f.evidence) +
                            f" → **{CONCLUSIONS[name]['title']}** (rule confidence {f.rule.cf:.0%})")
                for cond in f.rule.conditions:
                    if cond.fact in CONCLUSIONS:
                        explain(cond.fact, depth + 1)
        explain(pick)

        st.subheader("How confidence is calculated")
        st.markdown(
            "- Each rule has a **certainty factor (CF)**, e.g. 0.90.\n"
            "- A rule's result = rule CF × the weakest confidence among its conditions.\n"
            "- If several rules support the same conclusion they reinforce each other: "
            "`CF = CF1 + CF2 × (1 − CF1)` (MYCIN formula).")
    else:
        st.info("No rules fired for the current inputs.")

# ============================================================================= KNOWLEDGE BASE
with tab_kb:
    st.header("Knowledge base")
    st.write(f"**{len(RULES)} rules** and **{total_conditions} conditions**, each linked to a source. "
             "Rules live in `rules.py`, reasoning in `engine.py`, decisions in `decision.py`.")
    f1, f2 = st.columns([1, 2])
    cat = f1.selectbox("Category", ["All", *CATEGORIES.values()])
    query = f2.text_input("Search", placeholder="e.g. ammonia, ich, betta")
    rows = []
    for r in RULES:
        category = CATEGORIES[r.id[0]]
        if cat != "All" and category != cat:
            continue
        row = {"ID": r.id, "Category": category, "IF": " AND ".join(c.text for c in r.conditions),
               "THEN": CONCLUSIONS[r.conclusion]["title"], "CF": r.cf, "Source": r.source}
        if query and query.lower() not in " ".join(str(v) for v in row.values()).lower():
            continue
        rows.append(row)
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

# ============================================================================= ABOUT
with tab_about:
    st.header("About AquaDoc")
    st.markdown("""
**AquaDoc** is a rule-based **expert system and decision support system** that diagnoses water-quality
problems and fish diseases in freshwater aquariums, decides what must be done, and helps the keeper plan
the treatment. A preview mode applies the same engine to aquaculture ponds.

### How AquaDoc meets the project requirements
| Requirement | How AquaDoc does it | Where |
|---|---|---|
| **Inferencing** | Forward-chaining engine over IF-THEN rules, with rule chaining, certainty factors and conflict resolution | `engine.py`, *How?* tab |
| **Diagnosis** | Detects water/tank problems and fish diseases; **differential diagnosis** picks the most likely of competing diseases | `rules.py` (W, T, S, D, M, A rules) |
| **Decision making** | Decision rules (X) infer actions such as *isolate*, *stop feeding*, *fix water first*, *get a vet*; an overall **verdict** (Emergency → Healthy); unsafe advice is **cancelled** | `rules.py` (X rules), `decision.py` |
| **Decision support system** | Prioritised **action plan** (Now / 24 h / week), **what-if analysis** that re-runs the engine on simulated actions, alternatives shown - the keeper makes the final choice | `decision.py`, *What-if* tab |

### Architecture
| Part | File | Role |
|---|---|---|
| Knowledge base | `rules.py` | IF-THEN rules, advice text, differential groups (data, not code) |
| Inference engine | `engine.py` | Forward chaining, certainty factors, conflict resolution, explanation |
| Decision layer | `decision.py` | Verdict, differential diagnosis, action plan, what-if simulation |
| User interface | `app.py` | Streamlit front end |

### Expert-system techniques used
- **Forward chaining** - data-driven reasoning over multiple recognise-act cycles.
- **Chained rules** - derived facts (e.g. *poor water*) trigger disease rules, which trigger decision rules.
- **Certainty factors** - MYCIN-style confidence for every conclusion.
- **Conflict resolution** - most specific rule first, then most severe; weaker conclusions are superseded
  (e.g. *severe ammonia* hides *ammonia detected*); contradictory advice is removed.
- **Explanation facility** - *How?* tab shows every fired rule; the *?* tooltips answer *Why do you ask?*

### Scalability
The knowledge base is separate from the engine, so new domains (ponds, fish farms, hatcheries, rivers)
are added by writing new rules - no engine changes. Future work: IoT sensor input, more species,
SMS alerts, and validation by aquatic veterinarians.

### Limitations
Rules are based on published general guidelines and have not been validated by an aquatic vet.
AquaDoc supports the keeper's decision; it does not replace expert care.
""")
    st.subheader("References")
    for key, text in SOURCES.items():
        st.markdown(f"- **{key}** - {text}")
