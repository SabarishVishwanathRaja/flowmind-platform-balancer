"""FLOWMIND - Platform Balancer.  Entry point.

Usage:  python main.py
Output: dashboard.html
"""

from backend.simulation import run, sweep
from frontend.build import build


def main():
    print("Running FLOWMIND simulation (3 passes)...")
    data = {
        "on":     run(intervention_enabled=True,  loop_enabled=True),
        "noloop": run(intervention_enabled=True,  loop_enabled=False),
        "off":    run(intervention_enabled=False, loop_enabled=False),
    }
    for k, v in data.items():
        print("  %-7s boarding=%5.1fs  peak=%.2f pax/m2  final=%s"
              % (k, v["boarding"], v["peak"], v["final_density"]))

    base, cur = data["off"]["boarding"], data["on"]["boarding"]
    print("\n  Boarding time reduction vs baseline: %.0f%%"
          % ((base - cur) / base * 100))

    print()
    sweep_data = sweep()

    out = build(data, sweep_data)
    print("\nWrote %s  -  open it in your browser." % out)


if __name__ == "__main__":
    main()
