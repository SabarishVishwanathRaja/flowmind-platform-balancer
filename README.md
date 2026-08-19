# FLOWMIND — Platform Balancer

**PromptWars × NEXUS — Next-Gen Commuter & Transit Intelligence**

> Existing transit systems monitor *where passengers are*. FLOWMIND predicts
> where congestion will form on a platform **before it happens**, recommends a
> redistribution, measures whether passengers actually followed it, and adapts.

⚠️ **All results are from simulation.** This is not a real deployment and the
numbers are not field measurements.

---

## The problem

Platform crowding is rarely a capacity problem — it is a **distribution**
problem. Passengers cluster near staircases and familiar boarding spots, so one
section of a platform reaches 90%+ density while another sits near 30%, even
though the train has room. The result is longer dwell time, slower boarding, and
cascading network delay.

Detecting this is already solved in several metros. What is not solved is
**closing the loop between a recommendation and actual passenger behaviour.**

## The control loop

```
Observe  →  Predict  →  Decide  →  Intervene  →  Measure  →  Adapt
   ↑                                                            │
   └────────────────────────────────────────────────────────────┘
```

| Stage | What happens |
|---|---|
| **Observe** | Zone-level density only. No identity, no individual tracking. |
| **Predict** | Trend extrapolation of per-zone density to train-arrival time. |
| **Decide** | Weighted multi-objective scoring with an oscillation dead band. |
| **Intervene** | Each passenger independently chooses whether to comply. |
| **Measure** | Expected movement vs. actual movement. |
| **Adapt** | Damped online update of the per-zone compliance estimate. |

## The research gap this addresses

Crowd-guidance systems in the literature almost universally **assume**
passengers comply with announcements. Reliable compliance figures barely exist,
and the real rate varies by station, time of day, and crowd composition.

FLOWMIND does not assume a compliance rate. **It estimates it online** from
observed movement:

```
ĉ ← ĉ + α (observed / offered − ĉ)          α = 0.3, ĉ clamped to [0.15, 0.95]
target_movers = raw_need / ĉ
```

Damping is deliberate: aggressive updating causes the system to overshoot and
oscillate, which is worse for passengers than doing nothing.

## Results (simulated)

| Mode | Boarding time | Peak density |
|---|---|---|
| Baseline — no intervention | 152.0 s | 3.42 pax/m² |
| Intervention, feedback loop disabled | 58.8 s | 1.95 pax/m² |
| **Full FLOWMIND** | **56.0 s** | **1.88 pax/m²** |

**63% boarding-time reduction vs. baseline.** Same seed, same 700 passengers,
same arrival sequence — a true counterfactual, not two separate runs.

10-second-ahead density forecast error (MAE): **0.228 pax/m²**

### Robustness sweep

The system is re-run at 13 true compliance rates from 15% to 85%. Boarding time
stays between 44 s and 77 s across the entire range — the result does not depend
on a favourable compliance assumption.

## Running it

Requires Python 3.8+. No third-party packages.

```bash
python main.py
```

This runs 45 simulations (3 demo modes + 13 × 3 sweep runs) and writes a
self-contained `dashboard.html`. Open it in any browser — no server, no network.

## Repository layout

```
flowmind/
├── main.py                  entry point
├── backend/
│   ├── config.py            all tunable parameters
│   ├── passenger.py         agent model
│   ├── boarding.py          platform geometry + door-flow boarding model
│   └── simulation.py        the control loop and the compliance sweep
└── frontend/
    ├── template.html        dashboard UI (vanilla JS + canvas)
    └── build.py             bakes results into a standalone HTML file
```

## Design decisions and what was deliberately cut

| Cut | Why |
|---|---|
| Reinforcement learning | Cannot be trained to convergence or defended in a hackathon window. Explicit weighted scoring is transparent and auditable. |
| Deep-learning forecaster | At this data volume, trend extrapolation is both more accurate and fully explainable. |
| Live LLM explanation call | A network failure during a demo is an unnecessary risk. Explanations are generated deterministically. |
| CV / YOLO as primary input | Would make the pipeline look real while adding no verifiable evidence. Simulation is labelled as simulation. |
| LoRa / IoT sensor network | Adds nothing to the boarding-time story. |
| Accessibility-differentiated routing | Right instinct long-term, but undemonstrable without real user categories and reintroduces the privacy problem. |

## Known limitations

- The boarding-time model uses illustrative constants, not field-calibrated data.
- Compliance is a simulation parameter; the estimator's convergence is shown, but the true rate has no empirical grounding.
- The compliance estimator undershoots at high true rates, receiving only 4–6 observations per run.
- Zone-to-door mapping and real coach occupancy are unsolved without live camera and train data.
- Redirecting crowds can relocate congestion rather than remove it; the simulation models this explicitly rather than assuming it away.

## Privacy

Zone-level counts only. No facial recognition, no re-identification, no
persistence of any individual across runs.
