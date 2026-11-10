"""
engine.py - the INFERENCE ENGINE of AquaDoc.

The engine knows NOTHING about fish. It only knows how to reason:
    1. Read the rules (from rules.py) and the facts (user input).
    2. Forward chaining: keep firing every rule whose IF part is true,
       adding the THEN part as a new fact, until nothing new can be derived.
    3. Certainty factors: every conclusion carries a confidence (0 to 1).
    4. Conflict resolution: decide order of firing + hide weaker conclusions.
    5. Explanation: remember WHICH rules fired and WHY (the "How?" facility).
"""
import ast
import operator
import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# 1. Rules and conditions
# ---------------------------------------------------------------------------
OPERATORS = {
    ">=": operator.ge, "<=": operator.le, ">": operator.gt, "<": operator.lt,
    "==": operator.eq, "!=": operator.ne, "in": lambda a, b: a in b,
}
# "ammonia >= 0.25"  ->  name, operator, value      |      "poor_water" -> bare name
CONDITION_PATTERN = re.compile(r"^\s*(\w+)\s*(>=|<=|==|!=|>|<|in)\s*(.+?)\s*$")
SEVERITY_RANK = {"critical": 0, "warning": 1, "info": 2}


@dataclass(frozen=True)
class Condition:
    fact: str            # name of the fact, e.g. "ammonia"
    op: str              # ">=", "==", ... or "is" for a bare name (fact is true)
    value: object        # value to compare with
    text: str            # original text, used in explanations


@dataclass(frozen=True)
class Rule:
    id: str
    conditions: tuple    # IF part: ALL conditions must hold (AND)
    conclusion: str      # THEN part: name of the fact to derive
    cf: float            # rule confidence, 0..1
    source: str          # where the rule's knowledge comes from


def parse_condition(text):
    if re.fullmatch(r"\s*\w+\s*", text):          # bare name: "this fact is true"
        return Condition(text.strip(), "is", True, text.strip())
    match = CONDITION_PATTERN.match(text)
    if match:
        name, op, raw = match.groups()
        return Condition(name, op, ast.literal_eval(raw), text.strip())
    raise ValueError(f"Cannot understand condition: {text!r}")


def rule(rule_id, if_conditions, then_conclusion, cf, source):
    """Helper so rules.py can stay one readable line per rule."""
    return Rule(rule_id, tuple(parse_condition(c) for c in if_conditions),
                then_conclusion, cf, source)


# ---------------------------------------------------------------------------
# 2. Results (what the engine hands back to the UI)
# ---------------------------------------------------------------------------
@dataclass
class Fired:
    rule: Rule
    cycle: int           # in which recognise-act cycle it first fired
    cf: float            # confidence it contributed
    evidence: list       # human-readable proof of each condition


@dataclass
class Result:
    derived: dict                       # conclusion -> combined confidence
    fired: list                         # list[Fired] in firing order
    cycles: int
    conclusions: dict = field(repr=False)

    def visible(self, min_cf=0.5):
        """Conclusions to show the user, after conflict resolution."""
        superseded = set()
        for name in self.derived:
            superseded.update(self.conclusions[name].get("supersedes", []))
        shown = [
            (name, cf) for name, cf in self.derived.items()
            if self.conclusions[name]["kind"] != "finding"
            and name not in superseded and cf >= min_cf
        ]
        shown.sort(key=lambda item: (
            SEVERITY_RANK[self.conclusions[item[0]]["severity"]], -item[1]))
        return shown

    def why(self, conclusion):
        """All fired rules that support a conclusion (the 'How?' facility)."""
        return [f for f in self.fired if f.rule.conclusion == conclusion]


# ---------------------------------------------------------------------------
# 3. The engine
# ---------------------------------------------------------------------------
def combine(old_cf, new_cf):
    """Combine two positive certainty factors (MYCIN formula).
    Two independent pieces of evidence reinforce each other, never exceed 1."""
    return old_cf + new_cf * (1 - old_cf)


class Engine:
    MAX_CYCLES = 20

    def __init__(self, rules, conclusions, known_facts):
        self.rules = list(rules)
        self.conclusions = conclusions
        self.known_facts = set(known_facts)
        self._validate()

    def _validate(self):
        """Catch typos in rules.py early (very handy while writing rules)."""
        ids = [r.id for r in self.rules]
        assert len(ids) == len(set(ids)), "Duplicate rule ids"
        for r in self.rules:
            assert r.conclusion in self.conclusions, f"{r.id}: unknown conclusion {r.conclusion}"
            for c in r.conditions:
                is_derived = c.fact in self.conclusions
                assert is_derived or c.fact in self.known_facts, f"{r.id}: unknown fact {c.fact}"
                # Negating a derived fact would make results depend on firing order.
                assert not (is_derived and c.op != "is"), f"{r.id}: only bare names allowed for derived fact {c.fact}"

    def _match(self, rule_, facts, derived):
        """Check one rule. Returns (matched?, confidence of the IF part, evidence)."""
        confidences, evidence = [], []
        for c in rule_.conditions:
            if c.fact in self.conclusions:                    # a derived fact
                if c.fact not in derived:
                    return False, 0.0, []
                confidences.append(derived[c.fact])
                evidence.append(f"{c.fact} was concluded (confidence {derived[c.fact]:.0%})")
            else:                                             # a raw fact from the user
                actual = facts.get(c.fact)
                if actual is None:
                    return False, 0.0, []
                ok = bool(actual) if c.op == "is" else OPERATORS[c.op](actual, c.value)
                if not ok:
                    return False, 0.0, []
                shown = "yes" if c.op == "is" else f"actual: {actual}"
                evidence.append(f"{c.text}  ({shown})")
        # The IF part is only as certain as its weakest condition.
        return True, min(confidences, default=1.0), evidence

    def run(self, facts):
        derived, fired = {}, {}
        cycle = 0
        for cycle in range(1, self.MAX_CYCLES + 1):
            # MATCH: build the agenda of all rules whose IF part is true
            agenda = []
            for r in self.rules:
                ok, cf_in, evidence = self._match(r, facts, derived)
                if ok:
                    agenda.append((r, cf_in, evidence))
            # CONFLICT RESOLUTION: most specific rule first (most conditions),
            # then the most severe conclusion.
            agenda.sort(key=lambda a: (
                -len(a[0].conditions),
                SEVERITY_RANK[self.conclusions[a[0].conclusion]["severity"]]))
            # ACT: fire every rule on the agenda
            new_derived = {}
            for r, cf_in, evidence in agenda:
                cf = r.cf * cf_in
                new_derived[r.conclusion] = combine(new_derived.get(r.conclusion, 0.0), cf)
                if r.id in fired:
                    fired[r.id].cf, fired[r.id].evidence = cf, evidence
                else:
                    fired[r.id] = Fired(r, cycle, cf, evidence)
            stable = (set(new_derived) == set(derived) and all(
                abs(new_derived[k] - derived[k]) < 1e-9 for k in new_derived))
            derived = new_derived
            if stable:      # nothing new learned -> forward chaining is finished
                break
        return Result(derived, list(fired.values()), cycle, self.conclusions)
