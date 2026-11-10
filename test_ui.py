"""UI smoke test (no browser needed). Run with:  python test_ui.py"""
from streamlit.testing.v1 import AppTest
from rules import SCENARIOS

EXPECTED_VERDICT = {
    "New tank ammonia spike": "EMERGENCY",
    "Ich outbreak after buying new fish": "ACTION NEEDED",
    "Betta in a cold bowl": "ACTION NEEDED",
    "Old neglected tank": "ACTION NEEDED",
    "Betta with fin-nippers": "ACTION NEEDED",
    "Pond oxygen crash (aquaculture)": "EMERGENCY",
}


def banner_text(at):
    return " ".join(m.value for group in (at.error, at.warning, at.info, at.success) for m in group)


at = AppTest.from_file("app.py", default_timeout=30).run()
assert not at.exception, at.exception
assert "HEALTHY" in banner_text(at), "default tank should be HEALTHY"
print("PASS  app loads, default tank -> HEALTHY")

for name in SCENARIOS:
    at.selectbox(key="scenario").set_value(name).run()
    assert not at.exception, (name, at.exception)
    assert EXPECTED_VERDICT[name] in banner_text(at), (name, banner_text(at)[:200])
    # what-if: simulate a 60% water change + aeration
    at.slider(key="wi_water").set_value(60).run()
    at.checkbox(key="wi_aerate").check().run()
    assert not at.exception, (name, "what-if", at.exception)
    after = [m for m in at.metric if m.label == "Decision after these actions"][0].value
    print(f"PASS  {name}: {EXPECTED_VERDICT[name]}  |  what-if 60% change + aeration -> {after}")
    at.slider(key="wi_water").set_value(0).run()
    at.checkbox(key="wi_aerate").uncheck().run()
print("UI TESTS PASSED")
