"""All tunable parameters for the FLOWMIND simulation."""

SEED = 20260819
ZONES = ["A", "B", "C", "D"]
ZONE_AREA_M2 = 120.0
TOTAL_PASSENGERS = 700
TRAIN_ARRIVES_AT_SEC = 90.0
TICKS_PER_SEC = 10
RECORD_EVERY = 10          # record one animation frame every N ticks

DENSITY_WATCH = 1.5
DENSITY_WARNING = 2.5
DENSITY_CRITICAL = 3.5
TARGET_DENSITY = 2.0       # what the engine tries to pull crowded zones down to

# How likely passengers in each zone REALLY are to obey an announcement.
# The engine does not know these numbers - it has to learn them.
TRUE_COMPLIANCE = {"A": 0.34, "B": 0.46, "C": 0.52, "D": 0.44}

ALPHA = 0.3                # learning rate of the compliance estimator
C_HAT_START = 0.5          # engine's initial guess
C_HAT_MIN, C_HAT_MAX = 0.15, 0.95

MIN_HOLD_TICKS = 95        # dead band: no new recommendation for ~9.5 seconds
MIN_ACTION_SCORE = 0.4     # below this, do nothing
WALK_TICKS = 25            # how long a complying passenger takes to move zones

W_DENSITY = 1.0
W_DISTANCE = 0.35
W_DEST = 0.8
W_OSCILLATION = 0.6

# Boarding model (simplified, stated openly on the dashboard).
# Passenger flow through a door falls as platform density rises.
# base flow ~1.2 pax/door/s at free-flow, degrading above 1.0 pax/m2.
BASE_FLOW = 1.2
DOORS_PER_ZONE = 4
FLOW_FLOOR = 0.25
