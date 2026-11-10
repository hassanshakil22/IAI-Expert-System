# AquaDoc - Aquarium Expert System & Decision Support System

A rule-based expert system (Python + Streamlit) that **diagnoses** water-quality problems and
fish diseases through **inferencing**, **makes decisions** (verdict, isolate / stop feeding / fix
water first, differential diagnosis) and **supports** the keeper with a prioritised action plan
and what-if analysis.

## Files
| File | Purpose |
|---|---|
| `rules.py`    | Knowledge base: 114 IF-THEN rules (240 conditions), advice text, demo scenarios |
| `engine.py`   | Inference engine: forward chaining, certainty factors, conflict resolution |
| `decision.py` | Decision layer: verdict, differential diagnosis, action plan, what-if simulation |
| `app.py`      | Streamlit user interface |
| `test_engine.py`, `test_ui.py` | Automated tests |

## Run locally
```
pip install -r requirements.txt
streamlit run app.py
```

## Deploy (public link)
1. Push this folder to a public GitHub repository.
2. Go to https://share.streamlit.io, sign in with GitHub, choose the repo and `app.py`.
3. Click Deploy - you get a public URL.
