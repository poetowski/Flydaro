"""Landing/takeoff detection thresholds and lifecycle timers.

These are reasonable starting guesses, NOT validated against real OpenSky
data for the actual starter airports -- flagged as an open risk in the plan.
Expect to tune these from real poller logs once the worker has been running
against live traffic for a while. Keeping them as named constants here (one
place) makes that tuning a one-line change instead of a hunt through the code.
"""

# Takeoff detection: how "airborne, close to the airport, still climbing" is defined.
# Deliberately wide: at a 60s poll interval, a narrower window (previously
# 1500m/15km) left too few samples per real departure to reliably land one
# with non-null baro_altitude/vertical_rate before the aircraft climbed past
# the ceiling. ~3000m covers most of the climb-out phase for most aircraft
# types, several minutes rather than ~60-120s.
TAKEOFF_MAX_ALTITUDE_M = 3000.0  # ~10,000 ft
# Only a reading BELOW this rejects a candidate (clearly not climbing); a
# null vertical_rate is treated as "unknown", not "not climbing", since
# OpenSky frequently omits it during climb-out. Looser than requiring proof
# of a >=3 m/s climb -- see thresholds discussion in the project plan for
# the false-positive trade-off this accepts.
TAKEOFF_VERTICAL_RATE_REJECT_BELOW_MS = 0.0
TAKEOFF_MAX_DISTANCE_KM = 50.0  # matches ground track covered over the wider altitude window

# Rental window: how long AIRBORNE_OPEN stays open (capacity rentable) before locking.
CAPACITY_WINDOW_MINUTES = 5.0

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

# On-demand landing confirmation (app/services/flight_status_service.py):
# triggered when a player checks their rentals, not on a fixed schedule, so
# it needs its own throttle rather than relying on poll cadence.
STATUS_CHECK_MIN_INTERVAL_SECONDS = 30.0

# Ad-hoc board discovery (app/services/flight_discovery_service.py): throttles
# how often any single airport gets a fresh adsb.fi query, so N concurrent
# users all loading the board with the same unlocked airport don't turn into
# N adsb.fi calls (on top of the client's own global pacing, see
# adsb_client.MIN_REQUEST_INTERVAL_SECONDS).
AIRPORT_POLL_MIN_INTERVAL_SECONDS = 45.0

# Query radius passed to adsb.fi's lat/lon/dist endpoint, replacing the old
# OpenSky-era bounding-box query. Must stay >= TAKEOFF_MAX_DISTANCE_KM (in
# nautical miles: 50km / 1.852 ~= 27nm) or a real candidate could fall
# outside the query itself before the distance check above ever runs;
# rounded up for a comfortable margin.
AIRPORT_QUERY_RADIUS_NM = 30.0
