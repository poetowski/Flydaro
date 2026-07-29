"""Landing/takeoff detection thresholds and lifecycle timers.

These are reasonable starting guesses, NOT validated against real OpenSky
data for the actual starter airports -- flagged as an open risk in the plan.
Expect to tune these from real poller logs once the worker has been running
against live traffic for a while. Keeping them as named constants here (one
place) makes that tuning a one-line change instead of a hunt through the code.
"""

# Takeoff detection: how "airborne, close to the airport, still climbing" is defined.
TAKEOFF_MAX_ALTITUDE_M = 1500.0  # ~5000 ft
TAKEOFF_MIN_VERTICAL_RATE_MS = 3.0
TAKEOFF_MAX_DISTANCE_KM = 15.0

# Betting window: how long AIRBORNE_OPEN stays open before locking.
BETTING_WINDOW_MINUTES = 5.0

# Landing detection: on_ground=True is the strong signal; these are the
# fallback low-altitude/low-speed/near-zero-climb criteria when on_ground is
# stale or missing.
LANDING_MAX_ALTITUDE_M = 150.0  # ~500 ft
LANDING_MAX_VELOCITY_MS = 40.0
LANDING_MAX_ABS_VERTICAL_RATE_MS = 2.0

# Grace period between LANDING_SUSPECTED and confirmed RESOLVED_LANDED, to
# rule out a momentary ADS-B blip or a touch-and-go/go-around.
LANDING_GRACE_PERIOD_MINUTES = 5.0

# Ceilings that guarantee every tracked flight eventually resolves even if
# OpenSky coverage drops the aircraft entirely.
MAX_FLIGHT_DURATION_CEILING_MINUTES = 12 * 60.0  # single global ceiling for phase 1
LOST_SIGNAL_CEILING_MINUTES = 25.0
