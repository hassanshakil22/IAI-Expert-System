"""
rules.py - the KNOWLEDGE BASE of AquaDoc (all the "fish knowledge" lives here).

Each rule is ONE line:

    rule("D01", ["white_spots", "flashing"], "ich", 0.90, "UFIFAS")
          id     IF (ALL must be true)        THEN     confidence  source

 * a condition is either  "name op value"  (e.g. "ammonia >= 0.25")
   or just a name        (e.g. "white_spots" = "this fact is true")
 * the IF part can use RAW facts (what the user typed) or DERIVED facts
   (conclusions of other rules, e.g. "poor_water") -> that is chaining.

To add knowledge: add a rule line + (if new) an entry in CONCLUSIONS. Nothing else.
"""
from engine import rule

# Rule-id prefixes -> category names (used by the Knowledge-base tab)
CATEGORIES = {
    "W": "Water chemistry",
    "T": "Temperature & equipment",
    "A": "Aquaculture pond (preview)",
    "S": "Stocking & compatibility",
    "D": "Diseases & symptoms",
    "M": "Maintenance habits",
    "X": "Decisions & treatment cautions",
}

SOURCES = {
    "FAO": "FAO Fisheries & Aquaculture Division - freshwater aquaculture water-quality guidance",
    "SRAC": "Southern Regional Aquaculture Center (USA) - pond water quality & dissolved oxygen fact sheets",
    "UFIFAS": "UF/IFAS Extension - freshwater aquarium water quality and fish-health publications",
    "FISHBASE": "FishBase - species temperature / pH tolerance ranges",
    "AQ": "Standard freshwater aquarium-keeping practice (hobbyist care guides)",
}

HOME_SPECIES = ["Tropical community", "Betta", "Goldfish", "Cichlid"]
POND_SPECIES = ["Tilapia", "Carp (rohu / catla / common)"]
# Ideal temperature per species, used by the what-if analysis ("fix the temperature")
IDEAL_TEMP = {"Tropical community": 25.0, "Betta": 26.5, "Goldfish": 20.0, "Cichlid": 26.0,
              "Tilapia": 28.0, "Carp (rohu / catla / common)": 26.0}

# Names of every RAW fact the UI can supply (the engine uses this to catch typos)
SYMPTOMS = {
    "white_spots": "White spots like salt grains",
    "flashing": "Fish rub / scratch against objects",
    "frayed_fins": "Frayed, ragged or shrinking fins",
    "clamped_fins": "Fins clamped tightly to the body",
    "lethargic": "Lethargic / inactive",
    "gasping": "Gasping at the surface",
    "red_gills": "Red or inflamed gills",
    "cloudy_eyes": "Cloudy eyes",
    "bloated": "Bloated belly",
    "pinecone_scales": "Scales sticking out (pinecone look)",
    "swimming_upside_down": "Floating / swimming upside down or sideways",
    "cotton_growth": "White cotton-like growth on body or mouth",
    "loss_appetite": "Not eating",
    "hiding": "Hiding all the time",
    "algae": "Lots of algae on glass / decor",
    "green_water": "Water has turned green",
    "cloudy_water": "Water is cloudy / milky",
}
POND_SYMPTOMS = ["gasping", "lethargic", "loss_appetite", "white_spots",
                 "cotton_growth", "frayed_fins", "green_water"]

TANKMATES = {
    "tankmate_fin_nippers": "Fin-nippers (tiger barbs, some tetras)",
    "tankmate_male_betta": "Another male betta",
    "tankmate_goldfish": "Goldfish",
    "tankmate_cichlids": "Large / aggressive cichlids",
    "tankmate_small_peaceful": "Small peaceful fish (neon tetras, guppies)",
}

DEFAULTS = dict(
    ph=7.0, ammonia=0.0, nitrite=0.0, nitrate=10.0, temp_c=26.0, dissolved_oxygen=6.5,
    species_home="Tropical community", species_pond="Tilapia",
    tank_l=100, fish_count=6, tank_age_weeks=20,
    heater=True, filter_running=True, aerated=True,
    water_change_days=7, feedings_per_day=1, uneaten_food=False,
    uses_dechlorinator=True, light_hours=8, new_fish_recent=False,
    **{k: False for k in TANKMATES}, **{k: False for k in SYMPTOMS},
)
# Facts that only make sense for a home aquarium (reset to default in pond mode)
HOME_ONLY = ["tank_l", "fish_count", "tank_age_weeks", "heater", "filter_running",
             "uneaten_food", "uses_dechlorinator", "light_hours", "new_fish_recent",
             "water_change_days", "feedings_per_day", *TANKMATES,
             *[s for s in SYMPTOMS if s not in POND_SYMPTOMS]]

KNOWN_FACTS = set(DEFAULTS) - {"species_home", "species_pond"} | {
    "mode", "species_group", "liters_per_fish"}

# ---------------------------------------------------------------------------
# THE RULES
# ---------------------------------------------------------------------------
HOME = "mode == 'home'"
POND = "mode == 'pond'"

RULES = [
    # ---- W: water chemistry ------------------------------------------------
    rule("W01", ["ammonia >= 0.25"], "ammonia_present", 0.85, "UFIFAS"),
    rule("W02", ["ammonia >= 1.0"], "ammonia_severe", 0.95, "UFIFAS"),
    rule("W03", ["ammonia >= 0.25", "ph >= 8.0"], "ammonia_toxic_alkaline", 0.90, "UFIFAS"),
    rule("W04", ["nitrite >= 0.25"], "nitrite_toxic", 0.90, "UFIFAS"),
    rule("W05", ["nitrate >= 40"], "nitrate_high", 0.85, "UFIFAS"),
    rule("W06", ["nitrate >= 80"], "nitrate_severe", 0.95, "UFIFAS"),
    rule("W07", ["ph < 6.0"], "ph_too_low", 0.90, "UFIFAS"),
    rule("W08", ["ph > 8.5"], "ph_too_high", 0.90, "UFIFAS"),
    rule("W09", [HOME, "tank_age_weeks < 6", "ammonia >= 0.25"], "tank_not_cycled", 0.90, "AQ"),
    rule("W10", [HOME, "tank_age_weeks < 6", "nitrite >= 0.25"], "tank_not_cycled", 0.90, "AQ"),
    rule("W11", [HOME, "tank_age_weeks >= 6", "ammonia >= 0.5", "nitrate < 20"], "cycle_crash", 0.70, "AQ"),
    rule("W12", ["ammonia_present"], "poor_water", 0.90, "UFIFAS"),
    rule("W13", ["nitrite_toxic"], "poor_water", 0.90, "UFIFAS"),
    rule("W14", ["nitrate_high"], "poor_water", 0.80, "UFIFAS"),
    rule("W15", ["ph_too_low", "nitrate_high"], "ph_crash_risk", 0.75, "AQ"),

    # ---- T: temperature & equipment -----------------------------------------
    rule("T01", ["species_group == 'Tropical community'", "temp_c < 22"], "temp_too_cold", 0.90, "FISHBASE"),
    rule("T02", ["species_group == 'Tropical community'", "temp_c > 30"], "temp_too_hot", 0.90, "FISHBASE"),
    rule("T03", ["species_group == 'Betta'", "temp_c < 24"], "temp_too_cold", 0.90, "FISHBASE"),
    rule("T04", ["species_group == 'Betta'", "temp_c > 30"], "temp_too_hot", 0.90, "FISHBASE"),
    rule("T05", ["species_group == 'Goldfish'", "temp_c > 25"], "temp_too_hot", 0.85, "FISHBASE"),
    rule("T06", ["species_group == 'Goldfish'", "temp_c < 10"], "temp_too_cold", 0.85, "FISHBASE"),
    rule("T07", ["species_group == 'Cichlid'", "temp_c < 23"], "temp_too_cold", 0.85, "FISHBASE"),
    rule("T08", ["species_group == 'Cichlid'", "temp_c > 30"], "temp_too_hot", 0.85, "FISHBASE"),
    rule("T09", ["species_group == 'Tilapia'", "temp_c < 22"], "temp_too_cold", 0.85, "FAO"),
    rule("T10", ["species_group == 'Tilapia'", "temp_c > 34"], "temp_too_hot", 0.85, "FAO"),
    rule("T11", ["species_group == 'Carp (rohu / catla / common)'", "temp_c < 15"], "temp_too_cold", 0.80, "FAO"),
    rule("T12", ["species_group == 'Carp (rohu / catla / common)'", "temp_c > 32"], "temp_too_hot", 0.80, "FAO"),
    rule("T13", [HOME, "temp_too_cold", "heater == False", "species_group != 'Goldfish'"], "heater_problem", 0.85, "AQ"),
    rule("T14", ["temp_too_hot", "aerated == False"], "low_oxygen_risk", 0.85, "UFIFAS"),
    rule("T15", [HOME, "temp_too_hot", "filter_running == False"], "low_oxygen_risk", 0.70, "UFIFAS"),

    # ---- A: aquaculture pond preview ---------------------------------------------
    rule("A01", [POND, "dissolved_oxygen < 3"], "critical_low_do", 0.95, "SRAC"),
    rule("A02", [POND, "dissolved_oxygen < 5", "temp_c > 30"], "low_do_heat", 0.85, "SRAC"),
    rule("A03", [POND, "ph > 9.0"], "pond_ph_high", 0.85, "FAO"),
    rule("A04", [POND, "nitrite >= 0.1"], "pond_nitrite", 0.85, "SRAC"),
    rule("A05", [POND, "dissolved_oxygen < 5", "gasping"], "oxygen_deficiency", 0.90, "SRAC"),
    rule("A06", [POND, "aerated == False", "dissolved_oxygen < 5"], "low_oxygen_risk", 0.85, "SRAC"),
    rule("A07", [POND, "green_water", "ph > 9.0"], "algae_bloom", 0.85, "SRAC"),

    # ---- S: stocking & compatibility ----------------------------------------------
    rule("S01", [HOME, "liters_per_fish < 4"], "overstocked", 0.80, "AQ"),
    rule("S02", [HOME, "liters_per_fish < 8", "tank_age_weeks < 6"], "new_tank_overload", 0.80, "AQ"),
    rule("S03", ["species_group == 'Betta'", "tank_l < 20"], "tank_too_small", 0.85, "AQ"),
    rule("S04", ["species_group == 'Goldfish'", "tank_l < 75"], "tank_too_small", 0.80, "AQ"),
    rule("S05", ["species_group == 'Cichlid'", "tank_l < 100"], "tank_too_small", 0.75, "AQ"),
    rule("S06", ["overstocked", "ammonia_present"], "overstock_cause", 0.80, "AQ"),
    rule("S07", ["overstocked", "nitrate_high"], "overstock_cause", 0.75, "AQ"),
    rule("S08", ["species_group == 'Betta'", "tankmate_fin_nippers"], "incompat_nipper", 0.90, "AQ"),
    rule("S09", ["species_group == 'Betta'", "tankmate_male_betta"], "incompat_betta", 0.95, "AQ"),
    rule("S10", [HOME, "tankmate_goldfish", "species_group != 'Goldfish'"], "incompat_goldfish", 0.85, "AQ"),
    rule("S11", ["species_group == 'Goldfish'", "tankmate_cichlids"], "incompat_cichlid", 0.80, "AQ"),
    rule("S12", ["species_group == 'Cichlid'", "tankmate_small_peaceful"], "predation_risk", 0.85, "AQ"),
    rule("S13", ["incompat_nipper"], "tank_conflict", 0.90, "AQ"),
    rule("S14", ["incompat_betta"], "tank_conflict", 0.90, "AQ"),
    rule("S15", ["incompat_goldfish"], "tank_conflict", 0.85, "AQ"),
    rule("S16", ["incompat_cichlid"], "tank_conflict", 0.80, "AQ"),
    rule("S17", ["predation_risk"], "tank_conflict", 0.85, "AQ"),

    # ---- D: diseases & symptoms -----------------------------------------------------
    rule("D01", ["white_spots", "flashing"], "ich", 0.90, "UFIFAS"),
    rule("D02", ["white_spots", "new_fish_recent"], "ich", 0.85, "UFIFAS"),
    rule("D03", ["white_spots", "temp_too_cold"], "ich", 0.80, "UFIFAS"),
    rule("D04", ["frayed_fins", "poor_water"], "fin_rot", 0.85, "UFIFAS"),
    rule("D05", ["frayed_fins", "clamped_fins", "poor_water"], "fin_rot", 0.90, "UFIFAS"),
    rule("D06", ["frayed_fins", "tank_conflict"], "fin_damage_nipping", 0.80, "AQ"),
    rule("D07", ["cotton_growth", "poor_water"], "columnaris", 0.70, "UFIFAS"),
    rule("D08", ["cotton_growth", "loss_appetite"], "fungal_infection", 0.75, "UFIFAS"),
    rule("D09", ["bloated", "pinecone_scales"], "dropsy", 0.90, "UFIFAS"),
    rule("D10", ["bloated", "swimming_upside_down"], "swim_bladder", 0.85, "UFIFAS"),
    rule("D11", ["swimming_upside_down", "feedings_per_day >= 3"], "swim_bladder", 0.80, "AQ"),
    rule("D12", ["bloated", "feedings_per_day >= 3"], "constipation", 0.80, "AQ"),
    rule("D13", ["gasping", "red_gills", "ammonia_present"], "ammonia_burn", 0.90, "UFIFAS"),
    rule("D14", ["gasping", "low_oxygen_risk"], "oxygen_deficiency", 0.85, "UFIFAS"),
    rule("D15", [HOME, "gasping", "filter_running == False"], "oxygen_deficiency", 0.70, "AQ"),
    rule("D16", ["clamped_fins", "lethargic", "temp_too_cold"], "cold_stress", 0.85, "UFIFAS"),
    rule("D17", ["lethargic", "loss_appetite", "temp_too_cold"], "cold_stress", 0.80, "UFIFAS"),
    rule("D18", ["clamped_fins", "lethargic", "poor_water"], "water_quality_stress", 0.85, "UFIFAS"),
    rule("D19", ["hiding", "new_fish_recent"], "acclimation_stress", 0.60, "AQ"),
    rule("D20", ["hiding", "tank_conflict"], "bullying_stress", 0.85, "AQ"),
    rule("D21", ["cloudy_eyes", "poor_water"], "cloudy_eye", 0.85, "UFIFAS"),
    rule("D22", ["cloudy_eyes", "loss_appetite"], "cloudy_eye", 0.60, "UFIFAS"),
    rule("D23", ["flashing", "ammonia_present"], "skin_irritation", 0.75, "UFIFAS"),
    rule("D24", ["flashing", "ph_too_high"], "skin_irritation", 0.70, "UFIFAS"),
    rule("D25", ["flashing", "ph_too_low"], "skin_irritation", 0.70, "UFIFAS"),
    rule("D26", ["flashing", "new_fish_recent"], "parasites", 0.65, "UFIFAS"),
    rule("D27", ["temp_too_hot", "gasping"], "heat_stress", 0.85, "UFIFAS"),
    rule("D28", ["temp_too_hot", "lethargic"], "heat_stress", 0.75, "UFIFAS"),
    rule("D29", ["green_water", "nitrate_high"], "algae_bloom", 0.85, "AQ"),
    rule("D30", [HOME, "algae", "light_hours > 10"], "excess_light_algae", 0.85, "AQ"),
    rule("D31", ["algae", "nitrate_high"], "algae_nutrients", 0.80, "AQ"),
    rule("D32", [HOME, "cloudy_water", "tank_age_weeks < 6"], "bacterial_bloom", 0.85, "AQ"),
    rule("D33", [HOME, "cloudy_water", "uneaten_food"], "decaying_food", 0.80, "AQ"),

    # ---- M: maintenance habits -----------------------------------------------------------
    rule("M01", [HOME, "water_change_days > 14", "nitrate_high"], "overdue_water_change", 0.90, "UFIFAS"),
    rule("M02", [HOME, "water_change_days > 30"], "overdue_water_change", 0.80, "AQ"),
    rule("M03", [HOME, "feedings_per_day >= 3", "ammonia_present"], "overfeeding", 0.80, "AQ"),
    rule("M04", [HOME, "feedings_per_day >= 3", "nitrate_high"], "overfeeding", 0.75, "AQ"),
    rule("M05", [HOME, "uneaten_food", "ammonia_present"], "overfeeding", 0.85, "AQ"),
    rule("M06", [HOME, "filter_running == False"], "no_filtration", 0.90, "AQ"),
    rule("M07", [HOME, "uses_dechlorinator == False", "gasping"], "chlorine_risk", 0.75, "UFIFAS"),
    rule("M08", [HOME, "uses_dechlorinator == False", "red_gills"], "chlorine_risk", 0.75, "UFIFAS"),
    rule("M09", [HOME, "uses_dechlorinator == False", "water_change_days <= 2", "lethargic"], "chlorine_risk", 0.70, "UFIFAS"),

    # ---- X: decisions & treatment cautions (the engine DECIDES what to do) ------------
    rule("X01", ["ich", "temp_too_hot"], "caution_no_heat", 0.90, "UFIFAS"),
    rule("X02", ["fin_rot", "poor_water"], "decision_water_first", 0.90, "UFIFAS"),
    rule("X03", ["cloudy_eye", "poor_water"], "decision_water_first", 0.85, "UFIFAS"),
    rule("X04", ["columnaris", "poor_water"], "decision_water_first", 0.90, "UFIFAS"),
    rule("X05", [HOME, "dropsy", "fish_count > 1"], "decision_isolate", 0.90, "UFIFAS"),
    rule("X06", [HOME, "columnaris", "fish_count > 1"], "decision_isolate", 0.85, "UFIFAS"),
    rule("X07", [HOME, "fungal_infection", "fish_count > 1"], "decision_isolate", 0.75, "UFIFAS"),
    rule("X08", ["ich", "fish_count > 1"], "decision_treat_whole_tank", 0.85, "UFIFAS"),
    rule("X09", ["dropsy"], "decision_get_expert", 0.85, "UFIFAS"),
    rule("X10", ["columnaris", "lethargic"], "decision_get_expert", 0.75, "UFIFAS"),
    rule("X11", [POND, "critical_low_do", "gasping"], "decision_get_expert", 0.80, "SRAC"),
    rule("X12", ["ammonia_severe"], "decision_stop_feeding", 0.90, "UFIFAS"),
    rule("X13", ["critical_low_do"], "decision_stop_feeding", 0.90, "SRAC"),
    rule("X14", ["nitrite_toxic", "tank_not_cycled"], "decision_stop_feeding", 0.70, "AQ"),
    rule("X15", ["incompat_betta"], "decision_separate", 0.95, "AQ"),
    rule("X16", ["fin_damage_nipping"], "decision_separate", 0.85, "AQ"),
    rule("X17", ["bullying_stress"], "decision_separate", 0.75, "AQ"),
    rule("X18", ["predation_risk"], "decision_separate", 0.80, "AQ"),
]

# ---------------------------------------------------------------------------
# CONCLUSIONS: the text shown to the user for every fact the rules can derive.
#   kind: "decision" (what the system decides should be done)
#         | "diagnosis" (a condition of the fish) | "problem" (a tank/water issue)
#         | "finding" (internal stepping-stone, hidden from the main results)
#   urgency: "now" | "24h" | "week"  (defaults from severity; used by the action plan)
#   supersedes: weaker conclusions that are hidden when this one is present
#   cancels: advice lines from OTHER conclusions that become unsafe when this one holds
# ---------------------------------------------------------------------------
URGENCY_BY_SEVERITY = {"critical": "now", "warning": "24h", "info": "week"}
ICH_HEAT_STEP = "Raise the temperature slowly to about 28-30 C if the species tolerates it."


def C(title, kind, severity, meaning, advice, supersedes=(), urgency=None, cancels=()):
    return dict(title=title, kind=kind, severity=severity, meaning=meaning,
                advice=list(advice), supersedes=list(supersedes),
                urgency=urgency or URGENCY_BY_SEVERITY[severity],
                cancels=list(cancels), differential=None)


CONCLUSIONS = {
    # findings (internal)
    "poor_water": C("Poor overall water quality", "finding", "warning", "", []),
    "tank_conflict": C("Incompatible tankmates", "finding", "warning", "", []),

    # water chemistry
    "ammonia_present": C("Ammonia detected", "problem", "warning",
        "Safe level is 0 ppm; above 0.25 ppm fish gills are damaged.",
        ["Change 30-50% of the water with dechlorinated water.",
         "Feed less and remove uneaten food.", "Retest in 24 hours."]),
    "ammonia_severe": C("SEVERE ammonia - emergency", "problem", "critical",
        "Ammonia of 1 ppm or more can kill fish within hours or days.",
        ["Change 50% of the water NOW, repeat daily until ammonia is below 0.25 ppm.",
         "Stop feeding for 24-48 hours.", "Add an ammonia-binding water conditioner and extra aeration."],
        supersedes=["ammonia_present"]),
    "ammonia_toxic_alkaline": C("Ammonia is extra toxic at this high pH", "problem", "critical",
        "In alkaline water more ammonia exists in its poisonous (NH3) form.",
        ["Do water changes first - they remove ammonia directly.",
         "Avoid sudden pH changes with chemicals; fix the pH slowly."]),
    "nitrite_toxic": C("Nitrite toxicity", "problem", "critical",
        "Nitrite stops blood carrying oxygen ('brown blood disease').",
        ["Change 30-50% of the water daily until nitrite is 0.", "Do not overfeed.",
         "Check the filter is running and add a beneficial-bacteria starter."]),
    "nitrate_high": C("High nitrate", "problem", "warning",
        "Nitrate above 40 ppm stresses fish and feeds algae.",
        ["Do larger or more frequent water changes.", "Add live plants.",
         "Vacuum the substrate and reduce feeding."]),
    "nitrate_severe": C("Very high nitrate", "problem", "warning",
        "Nitrate above 80 ppm weakens immunity and makes disease likely.",
        ["Do a 30-40% water change now, then repeat every few days.",
         "Review stocking level and feeding."], supersedes=["nitrate_high"]),
    "ph_too_low": C("pH too low (acidic)", "problem", "warning",
        "Below pH 6.0 most community fish become stressed.",
        ["Correct slowly (small daily water changes).", "Add crushed coral or a buffer.",
         "Never change pH by more than 0.3 per day."]),
    "ph_too_high": C("pH too high (alkaline)", "problem", "warning",
        "Above pH 8.5 most community fish become stressed.",
        ["Add driftwood or mix in RO / rain water gradually.",
         "Avoid quick-fix pH chemicals."]),
    "tank_not_cycled": C("Tank is not cycled yet", "problem", "warning",
        "A new tank has not grown the bacteria that turn ammonia into nitrate.",
        ["Test water daily and change water whenever ammonia/nitrite show.",
         "Feed lightly and add a beneficial-bacteria starter.", "Add fish slowly."]),
    "cycle_crash": C("Possible 'mini-cycle' (lost filter bacteria)", "problem", "warning",
        "An established tank shows ammonia but almost no nitrate - the bacteria may have died.",
        ["Never wash filter media in tap water.", "Keep the filter running 24/7.",
         "Add a bacteria starter and change water often until ammonia is 0."]),
    "ph_crash_risk": C("Risk of a pH crash", "problem", "warning",
        "Low pH together with lots of nitrate means the water has little buffering left.",
        ["Do a water change with properly buffered water.", "Test KH and keep it above 3 dKH."]),

    # temperature & equipment
    "temp_too_cold": C("Water too cold for this species", "problem", "warning",
        "Cold water slows the immune system and digestion.",
        ["Raise the temperature gradually (1-2 degrees C per hour).", "Check the heater."]),
    "temp_too_hot": C("Water too hot for this species", "problem", "warning",
        "Hot water holds less oxygen and speeds up disease.",
        ["Lower the temperature gradually (1-2 degrees C per hour).",
         "Add shade / a fan across the surface; add aeration."]),
    "heater_problem": C("Heater missing or not working", "problem", "warning",
        "This species needs warm water but the tank is cold and there is no working heater.",
        ["Install or replace the heater (approx. 1 watt per litre).", "Use a thermometer to verify."]),
    "low_oxygen_risk": C("Risk of low dissolved oxygen", "problem", "warning",
        "Warm water, no aeration or no filter flow reduces oxygen.",
        ["Add an air stone or increase surface movement.", "Lower the temperature if too hot.",
         "Reduce the number of fish."]),
    "critical_low_do": C("CRITICAL low dissolved oxygen (pond)", "problem", "critical",
        "Below 3 mg/L fish suffocate; a mass die-off can happen overnight.",
        ["Run all aerators / paddlewheels immediately.", "Stop feeding.",
         "Exchange part of the pond water with fresh well-oxygenated water."]),
    "low_do_heat": C("Low oxygen made worse by heat (pond)", "problem", "warning",
        "Warm water holds little oxygen; fish also use more when hot.",
        ["Aerate especially at night and dawn.", "Reduce feeding during hot spells."]),
    "pond_ph_high": C("Pond pH very high (algae photosynthesis)", "problem", "warning",
        "Dense algae raise pH in the afternoon, which makes ammonia more toxic.",
        ["Reduce fertiliser / feed inputs.", "Exchange some water.",
         "Consult your local aquaculture extension officer for treatments."]),
    "pond_nitrite": C("Nitrite in the pond", "problem", "warning",
        "Nitrite above 0.1 mg/L harms farmed fish blood oxygen transport.",
        ["Exchange part of the water and reduce feeding.",
         "Ask an extension officer about chloride (salt) to reduce nitrite toxicity."]),

    # stocking & compatibility
    "overstocked": C("Tank is overstocked", "problem", "warning",
        "Fewer than 4 litres of water per fish overloads the filter and oxygen supply.",
        ["Rehome some fish or upgrade to a larger tank.", "Increase water-change frequency."]),
    "new_tank_overload": C("Too many fish added to a new tank", "problem", "warning",
        "The young tank's bacteria cannot yet handle this waste load.",
        ["Add fish gradually, a few at a time.", "Test ammonia and nitrite every day."]),
    "tank_too_small": C("Tank too small for this species", "problem", "warning",
        "Small tanks make water quality swing quickly and limit growth.",
        ["Betta: at least 20 L. Goldfish: at least 75 L for the first fish. Cichlids: usually 100 L or more."]),
    "overstock_cause": C("Overstocking is contributing to poor water", "problem", "warning",
        "The waste load from the number of fish exceeds what the tank can process.",
        ["Reduce fish numbers.", "Add extra filtration."]),
    "incompat_nipper": C("Fin-nippers kept with a betta", "problem", "warning",
        "Nippers attack the betta's long flowing fins.",
        ["Separate them - choose calm tankmates (e.g. snails, small corydoras)."]),
    "incompat_betta": C("Two male bettas together", "problem", "critical",
        "Male bettas fight, often to the death.",
        ["Separate immediately into different tanks."]),
    "incompat_goldfish": C("Goldfish mixed with tropical fish", "problem", "warning",
        "Goldfish prefer cooler water and produce a lot of waste.",
        ["Keep goldfish in their own cool-water tank."]),
    "incompat_cichlid": C("Cichlids kept with goldfish", "problem", "warning",
        "Cichlids are aggressive and need warmer water than goldfish.",
        ["Keep them in separate tanks."]),
    "predation_risk": C("Cichlids may eat small peaceful fish", "problem", "warning",
        "Small fish like neons and guppies fit in a cichlid's mouth.",
        ["Separate them or choose similar-sized tankmates."]),

    # diagnoses
    "ich": C("Ich (white spot disease)", "diagnosis", "warning",
        "A parasite (Ichthyophthirius) that burrows under the skin; spreads fast.",
        [ICH_HEAT_STEP,
         "Treat with an ich medication as per label (10-14 days).",
         "Vacuum the gravel daily; keep the water clean."], urgency="now"),
    "fin_rot": C("Fin rot (bacterial)", "diagnosis", "warning",
        "Bacteria eat the fins when fish are stressed by dirty water.",
        ["Fix the water quality first (water changes).", "Remove sharp decorations.",
         "If it keeps spreading, use an antibacterial medication."]),
    "fin_damage_nipping": C("Fin damage from nipping", "diagnosis", "warning",
        "Fins are damaged by aggressive tankmates, not by disease.",
        ["Separate the aggressor.", "Fins should regrow in clean water."]),
    "columnaris": C("Possible columnaris (bacterial)", "diagnosis", "critical",
        "Fast-moving bacterial disease that looks like cotton patches, often in poor water.",
        ["Isolate the sick fish.", "Improve water quality straight away.",
         "Use an antibacterial medication labelled for columnaris."]),
    "fungal_infection": C("Fungal infection", "diagnosis", "warning",
        "Fluffy white growth, usually secondary to injury or stress.",
        ["Isolate the sick fish.", "Use an antifungal treatment.", "Remove uneaten food."]),
    "dropsy": C("Dropsy (fluid retention)", "diagnosis", "critical",
        "Swollen body with raised scales means organ failure. Prognosis is poor.",
        ["Isolate the fish in a hospital tank.", "Epsom-salt bath and antibacterial medication may help.",
         "Keep water pristine."]),
    "swim_bladder": C("Swim bladder disorder", "diagnosis", "warning",
        "Fish cannot control buoyancy; often from overfeeding or constipation.",
        ["Fast the fish for 2-3 days.", "Then feed a small piece of blanched, skinned pea.",
         "Feed smaller portions in future."]),
    "constipation": C("Constipation / overfeeding bloat", "diagnosis", "warning",
        "Too much food or dry food that swells in the gut.",
        ["Fast 1-2 days.", "Feed blanched pea.", "Reduce feeding to once or twice daily."]),
    "ammonia_burn": C("Ammonia burns on gills", "diagnosis", "critical",
        "Ammonia damages gill tissue, causing red gills and gasping.",
        ["Emergency water changes (50%).", "Add aeration.", "Use an ammonia detoxifier."]),
    "oxygen_deficiency": C("Oxygen deficiency (suffocation)", "diagnosis", "critical",
        "Fish gasp at the surface because water lacks oxygen.",
        ["Add aeration immediately.", "Do a partial water change with cool water.",
         "Check the filter is running."]),
    "cold_stress": C("Cold stress", "diagnosis", "warning",
        "Cold water makes fish sluggish and prone to disease.",
        ["Raise the temperature slowly.", "Check the heater and thermometer."]),
    "water_quality_stress": C("Stress from poor water quality", "diagnosis", "warning",
        "Clamped fins and lethargy are classic signs of water-quality stress.",
        ["Test all parameters and correct the worst first.", "Do a 30% water change."]),
    "acclimation_stress": C("Normal acclimation stress", "diagnosis", "info",
        "New fish often hide for a few days.",
        ["Dim the lights and give hiding places.", "Quarantine future new fish."]),
    "bullying_stress": C("Stress from bullying", "diagnosis", "warning",
        "The fish is hiding because tankmates harass it.",
        ["Add hiding places or rearrange the decor.", "Separate the aggressor."]),
    "cloudy_eye": C("Cloudy eye", "diagnosis", "warning",
        "Usually an infection or injury linked to poor water.",
        ["Improve water quality with daily small water changes.",
         "Use an antibacterial medication if it persists."]),
    "skin_irritation": C("Skin / gill irritation", "diagnosis", "warning",
        "Fish scratch themselves because the water chemistry irritates them.",
        ["Do a water change and retest pH and ammonia."]),
    "parasites": C("Possible external parasites (e.g. flukes)", "diagnosis", "warning",
        "New fish can bring in parasites that cause scratching.",
        ["Quarantine and treat with an antiparasitic.", "Quarantine all new fish for 2-4 weeks in future."]),
    "heat_stress": C("Heat stress", "diagnosis", "critical",
        "Too warm water causes gasping and lethargy.",
        ["Cool the water gradually.", "Add aeration.", "Turn off or lower the heater."]),

    # tank issues (water appearance, habits)
    "algae_bloom": C("Algae bloom (green water)", "problem", "info",
        "Excess nutrients and light feed free-floating algae.",
        ["Reduce light and feeding.", "Do water changes.", "Use a UV sterilizer or add plants."]),
    "excess_light_algae": C("Too many light hours causing algae", "problem", "info",
        "More than 10 hours of light encourages algae.",
        ["Keep lights on 6-8 hours with a timer."]),
    "algae_nutrients": C("Nutrients (nitrate) feeding algae", "problem", "info",
        "High nitrate is algae fertiliser.",
        ["Lower nitrate with water changes and live plants."]),
    "bacterial_bloom": C("Bacterial bloom in a new tank", "problem", "info",
        "Milky water is normal while a new tank matures.",
        ["Do nothing drastic; it clears in days.", "Avoid overfeeding."]),
    "decaying_food": C("Rotting uneaten food clouding the water", "problem", "warning",
        "Decaying food pollutes the water.",
        ["Remove leftovers and vacuum the gravel.", "Feed only what is eaten in 2 minutes."]),
    "overdue_water_change": C("Water changes are overdue", "problem", "warning",
        "Regular partial water changes keep nitrate and waste low.",
        ["Change 20-30% of the water weekly."]),
    "overfeeding": C("Overfeeding", "problem", "warning",
        "Excess food turns into ammonia and nitrate.",
        ["Feed once or twice daily, only what fish eat in 2 minutes."]),
    "no_filtration": C("No filter running", "problem", "warning",
        "Without a filter, harmful ammonia builds up and oxygen drops.",
        ["Install a filter sized for the tank.", "Keep it running 24/7."]),
    "chlorine_risk": C("Possible chlorine / chloramine exposure", "problem", "warning",
        "Tap water chemicals burn gills; red gills and gasping are typical.",
        ["Always treat tap water with a dechlorinator.", "Do a water change with treated water."]),

    # decisions (inferred by the X rules)
    "caution_no_heat": C("Do NOT use heat to treat Ich", "decision", "critical",
        "Ich is usually treated by raising the temperature, but this water is already too hot.",
        ["Cool the water into the species' range first.", "Use an ich medication instead of heat."],
        cancels=[ICH_HEAT_STEP]),
    "decision_water_first": C("Fix the water before using medicine", "decision", "warning",
        "This disease is caused or worsened by poor water; medicine alone will not cure it.",
        ["Do the water-quality actions first; medicate only if symptoms continue after 2-3 days."],
        urgency="now"),
    "decision_isolate": C("Isolate the sick fish", "decision", "warning",
        "The disease can spread, and medicine is safer in a separate hospital tank.",
        ["Move the affected fish to a hospital tank filled with water from the main tank.",
         "Treat it there so healthy fish are not exposed to the medicine."], urgency="now"),
    "decision_treat_whole_tank": C("Treat the whole tank, not one fish", "decision", "warning",
        "Ich has a free-swimming stage, so every fish in the tank is already exposed.",
        ["Dose the main tank, not a hospital tank.",
         "Keep treating for several days after the last white spot disappears."], urgency="now"),
    "decision_get_expert": C("Get professional help", "decision", "critical",
        "This condition is serious and has a poor outlook without expert treatment.",
        ["Contact an aquatic vet (home tank) or an aquaculture extension officer (farm)."]),
    "decision_stop_feeding": C("Stop feeding for now", "decision", "warning",
        "Food adds ammonia and uses up oxygen while the fish cannot cope.",
        ["Do not feed for 24-48 hours, then restart with small portions."], urgency="now"),
    "decision_separate": C("Separate incompatible fish", "decision", "warning",
        "Keeping these fish together will keep causing injury and stress.",
        ["Move the aggressor (or the victim) to another tank, or use a tank divider."]),
}

# DIFFERENTIAL DIAGNOSIS: diagnoses that compete to explain the same symptom.
# When several are concluded, the decision layer picks the most likely one.
DIFFERENTIALS = {
    "Cause of damaged fins": ["fin_rot", "fin_damage_nipping"],
    "Cause of cotton-like growth": ["columnaris", "fungal_infection"],
    "Cause of bloating / buoyancy problems": ["dropsy", "swim_bladder", "constipation"],
    "Cause of gasping": ["ammonia_burn", "oxygen_deficiency", "heat_stress"],
    "Cause of scratching / spots": ["ich", "skin_irritation", "parasites"],
    "Cause of lethargy": ["cold_stress", "water_quality_stress"],
    "Cause of hiding": ["acclimation_stress", "bullying_stress"],
}
for _group, _names in DIFFERENTIALS.items():
    for _name in _names:
        CONCLUSIONS[_name]["differential"] = _group

# Urgency overrides (long-term fixes vs. urgent ones)
for _name, _urgency in {"tank_too_small": "week", "overstocked": "week", "incompat_goldfish": "week",
                        "incompat_cichlid": "week", "no_filtration": "now"}.items():
    CONCLUSIONS[_name]["urgency"] = _urgency

# ---------------------------------------------------------------------------
# DEMO SCENARIOS (for the viva: one click loads a full case)
# ---------------------------------------------------------------------------
SCENARIOS = {
    "New tank ammonia spike": dict(
        tank_age_weeks=3, tank_l=60, fish_count=12, ph=7.4, ammonia=1.5, nitrite=0.5,
        water_change_days=20, feedings_per_day=3, uneaten_food=True,
        gasping=True, lethargic=True, red_gills=True),
    "Ich outbreak after buying new fish": dict(
        temp_c=23.0, new_fish_recent=True, white_spots=True, flashing=True),
    "Betta in a cold bowl": dict(
        species_home="Betta", tank_l=10, fish_count=1, temp_c=21.0, heater=False,
        lethargic=True, clamped_fins=True, loss_appetite=True),
    "Old neglected tank": dict(
        tank_age_weeks=100, nitrate=90.0, water_change_days=45,
        frayed_fins=True, clamped_fins=True, cloudy_eyes=True),
    "Betta with fin-nippers": dict(
        species_home="Betta", tank_l=40, fish_count=4, tankmate_fin_nippers=True,
        frayed_fins=True, hiding=True),
    "Pond oxygen crash (aquaculture)": dict(
        mode="pond", species_pond="Tilapia", temp_c=35.0, dissolved_oxygen=2.5, ph=9.3,
        nitrite=0.3, aerated=False, gasping=True, green_water=True),
}
