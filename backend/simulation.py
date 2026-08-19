"""The FLOWMIND control loop.

Observe -> Predict -> Decide -> Intervene -> Measure -> Adapt

Everything here is deterministic given SEED. The engine is never told the
true passenger compliance rate; it estimates it online from observed movement.
"""

import random

from .config import *
from .boarding import ZONE_INDEX, zone_distance, flow_rate, zone_boarding_time
from .passenger import Passenger


def run(intervention_enabled, loop_enabled, record=True, compliance=None):
    truec = dict(TRUE_COMPLIANCE)
    if compliance is not None:
        truec = {z: compliance for z in ZONES}
    rng = random.Random(SEED)
    total_ticks = int(TRAIN_ARRIVES_AT_SEC * TICKS_PER_SEC)

    passengers = []
    # Arrival schedule: heavily skewed toward Zone A (the staircase).
    arrival_ticks = sorted(
        rng.randint(0, int(total_ticks * 0.75)) for _ in range(TOTAL_PASSENGERS)
    )
    arrival_zones = []
    for _ in range(TOTAL_PASSENGERS):
        r = rng.random()
        if r < 0.58:
            arrival_zones.append("A")
        elif r < 0.80:
            arrival_zones.append("B")
        elif r < 0.93:
            arrival_zones.append("C")
        else:
            arrival_zones.append("D")

    next_arrival = 0
    history = {z: [] for z in ZONES}          # density history for prediction
    c_hat = {z: C_HAT_START for z in ZONES}
    state = {z: "normal" for z in ZONES}
    state_held = {z: 0 for z in ZONES}

    current_rec = None
    last_rec_tick = -10 ** 9
    last_source = None
    rec_counter = 0
    frames = []
    events = []
    pred10 = []
    last_fb = None
    pending = None      # recommendation awaiting measurement

    peak_density = 0.0
    pred_errors = []

    for tick in range(total_ticks + 1):
        # --- arrivals -------------------------------------------------
        while next_arrival < TOTAL_PASSENGERS and arrival_ticks[next_arrival] <= tick:
            passengers.append(Passenger(arrival_zones[next_arrival], rng))
            next_arrival += 1

        # --- move passengers who are relocating -----------------------
        for p in passengers:
            if p.moving_to is not None:
                p.move_ticks -= 1
                tx = 0.5
                p.x += (tx - p.x) * 0.12
                p.y += (rng.uniform(0.15, 0.85) - p.y) * 0.06
                if p.move_ticks <= 0:
                    p.zone = p.moving_to
                    p.moving_to = None
                    p.x = rng.uniform(0.08, 0.92)
                    p.y = rng.uniform(0.12, 0.88)
            else:
                p.x += rng.uniform(-0.004, 0.004)
                p.y += rng.uniform(-0.004, 0.004)
                p.x = min(0.95, max(0.05, p.x))
                p.y = min(0.92, max(0.08, p.y))

        # --- OBSERVE: counts and density ------------------------------
        counts = {z: 0 for z in ZONES}
        for p in passengers:
            counts[p.zone] += 1
        density = {z: counts[z] / ZONE_AREA_M2 for z in ZONES}
        peak_density = max(peak_density, max(density.values()))

        for z in ZONES:
            history[z].append(density[z])

        # --- hysteresis on state --------------------------------------
        for z in ZONES:
            d = density[z]
            if d >= DENSITY_CRITICAL:
                raw = "critical"
            elif d >= DENSITY_WARNING:
                raw = "warning"
            elif d >= DENSITY_WATCH:
                raw = "watch"
            else:
                raw = "normal"
            if raw != state[z]:
                state_held[z] += 1
                if state_held[z] >= 8:      # must persist 0.8s to flip
                    state[z] = raw
                    state_held[z] = 0
            else:
                state_held[z] = 0

        # --- PREDICT: trend to train arrival --------------------------
        eta = max(0.0, TRAIN_ARRIVES_AT_SEC - tick / TICKS_PER_SEC)
        predicted = {}
        slopes = {}
        window = 30
        for z in ZONES:
            h = history[z][-window:]
            if len(h) >= 5:
                slope = (h[-1] - h[0]) / (len(h) / TICKS_PER_SEC)
            else:
                slope = 0.0
            slopes[z] = slope
            predicted[z] = max(0.0, density[z] + slope * eta * 0.75)

        # --- MEASURE: did the last recommendation work? ---------------
        feedback = None
        if pending is not None and tick >= pending["measure_at"]:
            actual = pending["actual"]
            expected = max(1, pending["expected"])
            eff = actual / expected
            before = c_hat[pending["from_zone"]]
            if loop_enabled:
                after = before + ALPHA * (eff * before / max(0.05, before) - before)
                # observed compliance is actual / offered, not actual / expected
                observed_c = pending["actual"] / max(1, pending["offered"])
                after = before + ALPHA * (observed_c - before)
                after = min(C_HAT_MAX, max(C_HAT_MIN, after))
                c_hat[pending["from_zone"]] = after
            else:
                after = before
            feedback = {
                "rec": pending["id"],
                "expected": pending["expected"],
                "actual": actual,
                "eff": round(eff, 2),
                "cb": round(before, 2),
                "ca": round(after, 2),
                "zone": pending["from_zone"],
            }
            events.append({"t": tick, "text":
                           "Measured %s: expected %d moved, %d actually moved (%d%%). "
                           "Compliance estimate for Zone %s %.2f to %.2f."
                           % (pending["id"], pending["expected"], actual,
                              round(eff * 100), pending["from_zone"], before, after)})
            last_fb = feedback
            pending = None

        # --- DECIDE ---------------------------------------------------
        if intervention_enabled and pending is None and tick - last_rec_tick >= MIN_HOLD_TICKS and eta > 12:
            src = max(ZONES, key=lambda z: predicted[z])
            if predicted[src] > TARGET_DENSITY and counts[src] > 40:
                raw_need = int((predicted[src] - TARGET_DENSITY) * ZONE_AREA_M2)
                raw_need = min(raw_need, counts[src])
                best = None
                for dst in ZONES:
                    if dst == src:
                        continue
                    # score against the destination's PREDICTED post-move density
                    post = predicted[dst] + raw_need / ZONE_AREA_M2
                    gain = predicted[src] - (predicted[src] - raw_need / ZONE_AREA_M2)
                    dist = zone_distance(src, dst)
                    osc = 1.0 if (last_source is not None and dst == last_source) else 0.0
                    score = (W_DENSITY * gain
                             - W_DISTANCE * dist
                             - W_DEST * max(0.0, post - TARGET_DENSITY)
                             - W_OSCILLATION * osc)
                    if best is None or score > best[1]:
                        best = (dst, score, post)
                dst, score, post = best
                if score >= MIN_ACTION_SCORE:
                    c = c_hat[src] if loop_enabled else 1.0
                    target = int(min(counts[src], raw_need / max(0.15, c)))
                    rec_counter += 1
                    rid = "REC-%03d" % rec_counter
                    # --- INTERVENE: passengers decide individually ----
                    pool = [p for p in passengers if p.zone == src and p.moving_to is None]
                    rng.shuffle(pool)
                    offered = min(target, len(pool))
                    moved = 0
                    for p in pool[:offered]:
                        if rng.random() < truec[src]:
                            p.moving_to = dst
                            p.move_ticks = WALK_TICKS + rng.randint(0, 12)
                            moved += 1
                    current_rec = {
                        "id": rid, "src": src, "dst": dst,
                        "target": target, "raw": raw_need,
                        "score": round(score, 2),
                        "gain": round(gain, 2),
                        "dist": dist,
                        "post": round(post, 2),
                        "chat": round(c, 2),
                        "text": ("Redirect %d passengers from Zone %s toward Zone %s "
                                 "- Zone %s is predicted to reach %.1f pax/m2 by train "
                                 "arrival. Monitoring response and will adjust."
                                 % (target, src, dst, src, predicted[src])),
                    }
                    pending = {"id": rid, "from_zone": src, "expected": target,
                               "offered": offered, "actual": moved,
                               "measure_at": tick + WALK_TICKS + 15}
                    events.append({"t": tick, "text":
                                   "%s issued: move %d from Zone %s to Zone %s "
                                   "(need %d, compliance estimate %.2f)."
                                   % (rid, target, src, dst, raw_need, c)})
                    last_rec_tick = tick
                    last_source = src

        # --- prediction accuracy: 10-second-ahead forecast ------------
        pred10.append({z: max(0.0, density[z] + slopes[z] * 10.0) for z in ZONES})
        if tick >= 100:
            old = pred10[tick - 100]
            for z in ZONES:
                pred_errors.append(abs(old[z] - density[z]))

        # --- record a frame -------------------------------------------
        if record and tick % RECORD_EVERY == 0:
            frames.append({
                "t": round(tick / TICKS_PER_SEC, 1),
                "eta": round(eta, 1),
                "zc": [counts[z] for z in ZONES],
                "zd": [round(density[z] * 100) for z in ZONES],
                "zp": [round(predicted[z] * 100) for z in ZONES],
                "zs": [state[z] for z in ZONES],
                "ch": [round(c_hat[z] * 100) for z in ZONES],
                "rec": current_rec,
                "fb": last_fb,
                "p": [[round(p.x * 100), round(p.y * 100), ZONE_INDEX[p.zone]]
                      for p in passengers],
            })

    # --- train arrives: boarding time -------------------------------
    counts = {z: 0 for z in ZONES}
    for p in passengers:
        counts[p.zone] += 1
    density = {z: counts[z] / ZONE_AREA_M2 for z in ZONES}
    boarding = max(zone_boarding_time(counts[z], density[z]) for z in ZONES)

    mae = sum(pred_errors) / len(pred_errors) if pred_errors else 0.0

    return {
        "frames": frames,
        "events": events,
        "boarding": round(boarding, 1),
        "peak": round(peak_density, 2),
        "final_density": {z: round(density[z], 2) for z in ZONES},
        "mae": round(mae, 3),
        "chat_final": round(c_hat["A"], 3),
    }


def sweep():
    """Run the whole system across a range of TRUE compliance rates.
    The engine is never told the true rate - it must estimate it online."""
    print("Running compliance sweep (13 x 3 passes)...")
    out = {"c": [], "on": [], "noloop": [], "off": [], "chat": []}
    for k in range(13):
        c = round(0.15 + k * (0.70 / 12), 3)
        a = run(True, True, record=False, compliance=c)
        b = run(True, False, record=False, compliance=c)
        z = run(False, False, record=False, compliance=c)
        out["c"].append(c)
        out["on"].append(a["boarding"])
        out["noloop"].append(b["boarding"])
        out["off"].append(z["boarding"])
        out["chat"].append(a["chat_final"])
        print("  true compliance %.2f -> estimated %.2f | boarding %.1fs (loop) "
              "%.1fs (no loop) %.1fs (baseline)"
              % (c, a["chat_final"], a["boarding"], b["boarding"], z["boarding"]))
    return out
