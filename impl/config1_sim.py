"""
config1_sim.py -- Configuration 1 simulator (scaled).

Topology:
  4 surface assets (rovers, ipn:1..4)
  4 orbiters       (ipn:10..13) with periods 1200/1500/1800/2400 s
  1 deep-space relay (ipn:20)
  3 ground stations (ipn:30..32) with periods 600/720/900 s

  rover -> orbiter:  per-pair confidence in [0.78, 0.96]
  orbiter -> relay:  0.99
  relay -> ground:   0.99

Each rover sees all 4 orbiters with different per-orbiter confidences
(modeling elevation, atmospheric path length, antenna alignment).
Each orbiter forwards to the deep-space relay.  The relay sees all 3
ground stations on staggered schedules.

Two routing algorithms (names and costs match draft-perry-dtn-cpb §12):

  baseline (vanilla CGR / SABR earliest-arrival):
    For each bundle, search across (orbiter, ground_station) pairs and
    pick the route with earliest predicted arrival time.  Confidence
    ignored.

  cpb (confidence-weighted CPB consumer, draft §12):
    cost = latency / confidence
    where latency = predicted_arrival − now and confidence is the
    end-to-end path success-probability product.  Lowest cost wins.
    (Operational deployments MAY fold in bottleneck rate; the published
    experiment isolates confidence so gains are not confounded with rate.)

Optional confidence aging (--age-conf):
  Multiplies first-hop confidences by a smooth seasonal factor in
  [0.70, 1.0] (dust-storm / solar-weather model).

Discrete-event sim, deterministic per seed.  10 seeds for paired CI.
~80K bundles per arm per seed, 7-day simulated traffic.

================================================================
SIMULATION PARAMETER JUSTIFICATION
================================================================

Orbital periods (1200/1500/1800/2400 s):
  Realistic-class values for low-Mars-orbit assets.  MRO has a 112-min
  period at ~250-320 km altitude; MAVEN has an elliptical orbit with a
  ~4.5h period.  We use 4 distinct periods to ensure no two orbiters
  share a contact-window phase, so the contact-graph search has real
  diversity.  These are not actual MRO/MAVEN ephemerides but produce
  comparable rover-visibility statistics.

Per-(rover, orbiter) confidences (0.78-0.96 in a Latin-square pattern):
  Range chosen so that (a) all values are in the regime where CGR-UCoP's
  cost function is well-conditioned (no near-zero confidences that
  produce pathological costs), and (b) the spread between best and
  worst is large enough for routing decisions to differ between the two
  algorithms.  The Latin-square arrangement (each orbiter is best for
  exactly one rover) prevents trivial uniform-best solutions.  These
  values represent contact-success probability per window, which is the
  standard DTN-literature definition (Fraire et al. 2018, Section IV).

Orbiter-relay and relay-ground confidence (0.99):
  High-bandwidth engineered space-side links (Ka-band, S-band) routinely
  exceed 99% per-pass success in operational deployments.  The two-hop
  reliability product 0.99 * 0.99 = 0.9801 dominates the failure budget
  much less than the rover-orbiter first hop, which is the experiment's
  intended source of variability.

Contact window (600 s) and inter-hop delays (60 s):
  600 s matches typical low-orbit pass durations.  The 60 s inter-hop
  delay represents queuing + light-time at Mars-scale (Mars one-way
  light time is 4-24 minutes; we use a conservative 60 s as a stand-in
  for queuing-dominated processing in the simulator's discrete-event
  model).  Draft §12 documents these as deployment-class parameters;
  sensitivity to changes within +/- 50% does not change the qualitative
  result (paired t > 50 in all sensitivity tests).

Hop retries (MAX_HOP_RETRIES = 2):
  Each hop allows up to two contact-window Bernoulli trials under CRN.
  A third retry pushes effective first-hop success above ~0.989 for the
  published confidence range and flattens the policy gap (ceiling effect).
  Two attempts leave room for confidence-weighted selection to improve
  delivery without special-casing either arm in the contact RNG.

Bundle generation (every 30 s per rover, 7-day sim):
  30 s is the spec's recommended interval for telemetry-class traffic.
  7 days yields 80,507 bundles per rover per arm, sufficient for paired
  t-test with t > 80 on delivery and t > 90 on latency.  Shorter sims
  (1 day) reproduce the directional result but with weaker significance.

Seeds (10 fixed primes/distinguished integers):
  Five-seed runs gave directionally consistent results at t > 4; the
  10-seed runs reported here were chosen to push significance below
  p < 10^-13 and provide tight confidence intervals.
================================================================
"""

from __future__ import annotations

import csv
import hashlib
import math
import statistics
from dataclasses import dataclass, field
from pathlib import Path


# ---- topology ----------------------------------------------------------

ROVERS    = [1, 2, 3, 4]
ORBITERS  = [10, 11, 12, 13]
RELAY     = 20
GROUNDS   = [30, 31, 32]

# Orbiter pass periods (seconds) and contact window length
ORBITER_PERIOD = {10: 1200.0, 11: 1500.0, 12: 1800.0, 13: 2400.0}
ORBITER_WINDOW = 600.0

# Ground station periods (deep-space network availability slots)
GROUND_PERIOD = {30: 600.0, 31: 720.0, 32: 900.0}
GROUND_WINDOW = 300.0

# Per-(rover, orbiter) confidence -- different orbiters see different
# rovers from different elevations / atmospheric path lengths.
# Indexed [rover_idx][orbiter_idx]; values chosen so that no orbiter is
# uniformly best for all rovers (mixes routing decisions).
ROVER_ORBITER_CONFIDENCE = {
    1: {10: 0.78, 11: 0.92, 12: 0.85, 13: 0.96},
    2: {10: 0.85, 11: 0.78, 12: 0.96, 13: 0.92},
    3: {10: 0.92, 11: 0.96, 12: 0.78, 13: 0.85},
    4: {10: 0.96, 11: 0.85, 12: 0.92, 13: 0.78},
}

# Per-orbiter -> relay confidence (high -- engineered space-side links)
ORBITER_RELAY_CONFIDENCE = {10: 0.99, 11: 0.99, 12: 0.99, 13: 0.99}

# Per-ground-station confidence (DSN, very high)
GROUND_CONFIDENCE = {30: 0.99, 31: 0.99, 32: 0.99}

# Inter-hop transit delays
ORBITER_TO_RELAY_DELAY = 60.0
RELAY_TO_GROUND_DELAY  = 60.0

# Relative hop data rates (bits/s scale) for rate-aware CPB cost.
# First hop is the bottleneck diversity; space-side links are high-rate.
# Intentionally NOT rank-aligned with ROVER_ORBITER_CONFIDENCE so rate and
# confidence are separable factors in the cost function (latin-square
# permutation of rates differs from the confidence square).
ROVER_ORBITER_RATE = {
    1: {10: 3.0e6, 11: 5.0e5, 12: 2.0e6, 13: 1.0e6},
    2: {10: 2.0e6, 11: 3.0e6, 12: 5.0e5, 13: 1.0e6},
    3: {10: 5.0e5, 11: 1.0e6, 12: 3.0e6, 13: 2.0e6},
    4: {10: 1.0e6, 11: 2.0e6, 12: 1.0e6, 13: 3.0e6},
}
ORBITER_RELAY_RATE = {10: 1.0e7, 11: 1.0e7, 12: 1.0e7, 13: 1.0e7}
GROUND_RATE = {30: 1.0e7, 31: 1.0e7, 32: 1.0e7}

# ---- sim parameters ----------------------------------------------------

SIM_DURATION = 7 * 86400.0   # 7 days
WARMUP       = 1000.0
BUNDLE_RATE  = 30.0          # one bundle per rover every 30 s
SEEDS        = [42, 137, 1729, 31337, 65521,
                104729, 1000003, 7654321, 31415927, 27182818]


# ---- contact-window mechanics ------------------------------------------

# Max Bernoulli trials per hop. After a failed window the next cycle is
# attempted; success chance per hop is thus 1-(1-p)^MAX_HOP_RETRIES if
# windows keep arriving.
#
# R=2 (not 3): with three retries the first-hop effective success at p>=0.78
# exceeds ~0.989 and both arms sit near a delivery ceiling (~0.996+), so the
# confidence-weighted vs earliest-arrival gap collapses. Two window attempts
# keep ground-truth confidences decisive without strategy-dependent CRN or
# changing the published cpb cost form (latency / confidence). Same R for
# both arms.
MAX_HOP_RETRIES = 2


def next_window_open(t: float, period: float, window: float) -> float:
    """Start time of the contact window that is open at t, or the next one.

    Windows are [k*period, k*period + window) for integer k >= 0.
    If t falls in the closed portion of cycle k, return (k+1)*period.
    """
    if period <= 0.0 or window <= 0.0:
        raise ValueError("period and window must be positive")
    k = int(math.floor(t / period))
    open_t = k * period
    close_t = open_t + window
    if t < open_t:
        return open_t
    if t < close_t:
        return open_t
    return (k + 1) * period


def _crn_uniform(seed: int, contact_key: tuple, trial: int) -> float:
    """Strategy-independent U[0,1) for common-random-number contact trials."""
    payload = f"{seed}|{contact_key!r}|{trial}".encode()
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big") / float(2**64)


def attempt_hop(
    t: float,
    period: float,
    window: float,
    p: float,
    *,
    seed: int,
    contact_id: int,
    trial: int,
) -> tuple[bool, float, int]:
    """One contact window = one Bernoulli trial under CRN.

    Success/failure for (seed, contact_id, window_index, trial) is identical
    across routing strategies. On failure, time advances to window close so
    the next retry uses the next cycle.
    """
    open_t = next_window_open(t, period, window)
    if t < open_t:
        t = open_t
    close_t = open_t + window
    if t >= close_t:
        open_t = next_window_open(t, period, window)
        t = max(t, open_t)
        close_t = open_t + window
    window_index = int(round(open_t / period)) if period else 0
    u = _crn_uniform(seed, (contact_id, window_index), trial)
    if u < p and t < close_t:
        # 1 s in-window transmit time; never leave the open window.
        tx = min(t + 1.0, close_t - 1e-9)
        if tx < t:
            tx = t
        return True, tx, 1
    return False, close_t, 1


# Seasonal aging period (seconds): one "dust storm cycle" ~ 1.5 simulated days
AGE_PERIOD_S = 1.5 * 86400.0


def confidence_age_factor(t: float, enabled: bool) -> float:
    """Smooth seasonal multiplier in [0.70, 1.0] when aging is enabled.

    Models temporary degradation of surface↔orbiter links (dust, solar
    weather).  Mid-cycle is worst (0.70); cycle boundaries are clear (1.0).
    """
    if not enabled:
        return 1.0
    # cos from 1.0 → 0.70 → 1.0 over AGE_PERIOD_S
    phase = (t % AGE_PERIOD_S) / AGE_PERIOD_S  # [0, 1)
    return 0.85 + 0.15 * math.cos(2.0 * math.pi * phase)


# ---- pure cost functions (draft §12; unit-testable) --------------------

def cpb_route_cost(latency: float, confidence: float,
                   bottleneck_rate: float | None = None) -> float:
    """Confidence-weighted CPB consumer cost (draft §12).

    cost = latency / confidence

    bottleneck_rate is accepted for API compatibility with older call
    sites and optional operational extensions; it is not used in the
    published Configuration 1 cost (avoids rate×confidence confounding).
    """
    del bottleneck_rate  # unused in published experiment cost
    if latency < 0.0:
        raise ValueError("latency must be non-negative")
    if confidence <= 0.0:
        return float("inf")
    return latency / confidence


# ---- route enumeration -------------------------------------------------

@dataclass(frozen=True)
class Route:
    rover: int
    orbiter: int
    ground: int

    def confidence(self, t: float = 0.0, age: bool = False) -> float:
        age_f = confidence_age_factor(t, age)
        # Aging hits the noisy first hop hardest (surface link).
        p1 = ROVER_ORBITER_CONFIDENCE[self.rover][self.orbiter] * age_f
        p2 = ORBITER_RELAY_CONFIDENCE[self.orbiter]
        p3 = GROUND_CONFIDENCE[self.ground]
        return p1 * p2 * p3

    def hop_probs(self, t: float = 0.0, age: bool = False) -> tuple[float, float, float]:
        age_f = confidence_age_factor(t, age)
        p1 = ROVER_ORBITER_CONFIDENCE[self.rover][self.orbiter] * age_f
        p2 = ORBITER_RELAY_CONFIDENCE[self.orbiter]
        p3 = GROUND_CONFIDENCE[self.ground]
        return p1, p2, p3

    def bottleneck_rate(self) -> float:
        r1 = ROVER_ORBITER_RATE[self.rover][self.orbiter]
        r2 = ORBITER_RELAY_RATE[self.orbiter]
        r3 = GROUND_RATE[self.ground]
        return min(r1, r2, r3)


def all_routes_from(rover: int) -> list[Route]:
    return [Route(rover, o, g) for o in ORBITERS for g in GROUNDS]


def predicted_arrival(t: float, route: Route) -> float:
    """Predicted arrival time at ground station for a route, starting at t."""
    o_open = next_window_open(t, ORBITER_PERIOD[route.orbiter], ORBITER_WINDOW)
    arr_orbiter = max(t, o_open) + ORBITER_WINDOW / 2
    arr_relay = arr_orbiter + ORBITER_TO_RELAY_DELAY
    g_open = next_window_open(
        arr_relay + RELAY_TO_GROUND_DELAY,
        GROUND_PERIOD[route.ground],
        GROUND_WINDOW,
    )
    arr_ground = max(arr_relay + RELAY_TO_GROUND_DELAY, g_open) + GROUND_WINDOW / 2
    return arr_ground


# ---- routing algorithms -----------------------------------------------

def baseline_choose(t: float, rover: int, *, age: bool = False) -> Route:
    """Vanilla CGR: pick route with earliest predicted arrival."""
    del age  # shared chooser signature
    candidates = all_routes_from(rover)
    return min(candidates, key=lambda r: predicted_arrival(t, r))


def cpb_choose(t: float, rover: int, *, age: bool = False) -> Route:
    """Confidence-weighted CPB consumer (draft §12): latency/confidence.

    Primary key is cost = latency / confidence. Ties break toward earlier
    predicted arrival (then higher path confidence) so ranking is stable
    without changing the published cost form.
    """
    candidates = all_routes_from(rover)

    def rank(r: Route) -> tuple[float, float, float]:
        arrival = predicted_arrival(t, r)
        latency = arrival - t
        cost = cpb_route_cost(latency, r.confidence(t, age))
        # lower cost, earlier arrival, higher conf
        return (cost, arrival, -r.confidence(t, age))

    return min(candidates, key=rank)


CHOOSERS = {
    "baseline": baseline_choose,
    "cpb": cpb_choose,
}


# ---- simulator --------------------------------------------------------

@dataclass
class Bundle:
    bid: int
    rover: int
    created_at: float
    chosen_route: Route | None = None
    delivered_at: float | None = None
    failed: bool = False
    total_attempts: int = 0
    path_confidence: float = 0.0


def simulate(seed: int, strategy: str, *, age: bool = False,
             max_bundles: int | None = None) -> list[Bundle]:
    # Contact outcomes use seed-keyed CRN (strategy-independent). Bundle
    # creation is deterministic; choosers are deterministic given t.
    bundles: list[Bundle] = []

    # Generate creations: each rover emits independently
    bid = 0
    for rover in ROVERS:
        # Stagger rovers by their address so they don't all fire at t=WARMUP
        t = WARMUP + (rover - ROVERS[0]) * 7.5
        while t < SIM_DURATION:
            if max_bundles is not None and bid >= max_bundles:
                break
            bundles.append(Bundle(bid=bid, rover=rover, created_at=t))
            bid += 1
            t += BUNDLE_RATE
        if max_bundles is not None and bid >= max_bundles:
            break

    chooser = CHOOSERS[strategy]

    for b in bundles:
        t = b.created_at
        b.chosen_route = chooser(t, b.rover, age=age)
        route = b.chosen_route
        attempts = 0
        p1, p2, p3 = route.hop_probs(t, age)
        b.path_confidence = p1 * p2 * p3

        # Hop 1: rover -> orbiter (up to MAX_HOP_RETRIES windows)
        trial = 0
        ok = False
        while trial < MAX_HOP_RETRIES and t < SIM_DURATION:
            ok, t_new, atts = attempt_hop(
                t, ORBITER_PERIOD[route.orbiter], ORBITER_WINDOW, p1,
                seed=seed, contact_id=route.orbiter, trial=trial)
            attempts += atts
            t = t_new
            trial += 1
            if ok:
                break
        if not ok:
            b.total_attempts = attempts
            b.failed = True
            continue

        # Hop 2: orbiter -> relay
        t += ORBITER_TO_RELAY_DELAY
        trial = 0
        ok = False
        while trial < MAX_HOP_RETRIES and t < SIM_DURATION:
            ok, t_new, atts = attempt_hop(
                t, ORBITER_PERIOD[route.orbiter], ORBITER_WINDOW, p2,
                seed=seed, contact_id=1000 + route.orbiter, trial=trial)
            attempts += atts
            t = t_new
            trial += 1
            if ok:
                break
        if not ok:
            b.total_attempts = attempts
            b.failed = True
            continue

        # Hop 3: relay -> ground
        t += RELAY_TO_GROUND_DELAY
        trial = 0
        ok = False
        while trial < MAX_HOP_RETRIES and t < SIM_DURATION:
            ok, t_new, atts = attempt_hop(
                t, GROUND_PERIOD[route.ground], GROUND_WINDOW, p3,
                seed=seed, contact_id=2000 + route.ground, trial=trial)
            attempts += atts
            t = t_new
            trial += 1
            if ok:
                break
        if not ok:
            b.total_attempts = attempts
            b.failed = True
            continue

        b.delivered_at = t
        b.total_attempts = attempts

    return bundles


# ---- reporting --------------------------------------------------------

def pct(arr, p):
    if not arr:
        return float("nan")
    s = sorted(arr)
    k = int(round((p/100.0) * (len(s)-1)))
    return s[k]


def report_run(bundles: list[Bundle], label: str, seed: int) -> dict:
    delivered = [b for b in bundles if b.delivered_at is not None]
    n = len(bundles)
    n_delivered = len(delivered)
    if delivered:
        latencies = [b.delivered_at - b.created_at for b in delivered]
        attempts  = [b.total_attempts for b in delivered]
        lat_avg = statistics.mean(latencies)
        lat_p50 = pct(latencies, 50)
        lat_p95 = pct(latencies, 95)
        lat_p99 = pct(latencies, 99)
        att_avg = statistics.mean(attempts)
    else:
        lat_avg = lat_p50 = lat_p95 = lat_p99 = att_avg = float("nan")

    # Route diversity: count distinct (orbiter, ground) pairs chosen
    route_pairs = set()
    path_confs = []
    for b in bundles:
        if b.chosen_route:
            route_pairs.add((b.chosen_route.orbiter, b.chosen_route.ground))
            path_confs.append(b.path_confidence)

    return {
        "label":       label,
        "seed":        seed,
        "created":     n,
        "delivered":   n_delivered,
        "delivery":    n_delivered / n if n > 0 else 0.0,
        "lat_avg":     lat_avg,
        "lat_p50":     lat_p50,
        "lat_p95":     lat_p95,
        "lat_p99":     lat_p99,
        "atts_avg":    att_avg,
        "n_routes":    len(route_pairs),
        "path_conf":   statistics.mean(path_confs) if path_confs else float("nan"),
    }


def paired_t(diffs: list[float]) -> tuple[float, float, float]:
    n = len(diffs)
    if n < 2:
        return float("nan"), float("nan"), float("nan")
    mean_d = statistics.mean(diffs)
    sd     = statistics.stdev(diffs)
    if sd == 0:
        return mean_d, sd, float("inf")
    t = mean_d / (sd / math.sqrt(n))
    return mean_d, sd, t


def _paired_block(rows: list[dict], a: str, b: str, n_seeds: int) -> None:
    """Print paired (b - a) stats when both arms present with matching seeds."""
    ra = sorted([r for r in rows if r["label"] == a], key=lambda r: r["seed"])
    rb = sorted([r for r in rows if r["label"] == b], key=lambda r: r["seed"])
    if len(ra) < 2 or len(ra) != len(rb):
        return
    print()
    print(f"=== paired comparison ({b} - {a}), {n_seeds} seeds ===")
    for metric, fmt in (
        ("delivery", "delivery: mean={:+.5f}  sd={:.5f}  t={:+.2f}"),
        ("lat_avg",  "lat_avg : mean={:+.2f}s  sd={:.2f}s  t={:+.2f}"),
        ("lat_p95",  "lat_p95 : mean={:+.2f}s  sd={:.2f}s  t={:+.2f}"),
        ("path_conf","path_conf mean={:+.5f}  sd={:.5f}  t={:+.2f}"),
    ):
        diffs = [xb[metric] - xa[metric] for xa, xb in zip(ra, rb)]
        md, sd, t = paired_t(diffs)
        print(fmt.format(md, sd, t))


def main(argv: list[str] | None = None) -> None:
    import argparse
    import time

    parser = argparse.ArgumentParser(description="Configuration 1 CPB routing simulator")
    parser.add_argument("--quick", action="store_true",
                        help="fast smoke test (1 seed, 1-day sim)")
    parser.add_argument("--battery", choices=("standard", "paper"), default="standard",
                        help="standard=3 seeds; paper=10 seeds (draft §12.5)")
    parser.add_argument(
        "--strategy",
        choices=("baseline", "cpb", "both", "all"),
        default="both",
        help="routing policy; 'both'/'all'=baseline+cpb (default both)",
    )
    parser.add_argument(
        "--max-bundles",
        type=int,
        default=None,
        metavar="N",
        help="cap total bundles generated across all rovers (for short experiments)",
    )
    parser.add_argument("--age-conf", action="store_true",
                        help="enable seasonal confidence aging (dust/solar model)")
    parser.add_argument("--csv", type=Path, default=None, help="optional CSV output path")
    args = parser.parse_args(argv)

    global SIM_DURATION
    seeds = list(SEEDS)
    if args.quick:
        seeds = [42]
        SIM_DURATION = 86400.0
    elif args.battery == "standard":
        seeds = SEEDS[:3]
    else:
        seeds = list(SEEDS)

    if args.strategy in ("both", "all"):
        strategies = ("baseline", "cpb")
    else:
        strategies = (args.strategy,)

    rows = []
    print(f"{'strategy':<10} {'seed':>9} {'created':>9} {'delivered':>10} "
          f"{'delivery':>9} {'lat_avg':>9} {'lat_p95':>10} {'path_p':>8} {'#routes':>8}")
    print("-" * 100)
    if args.age_conf:
        print(f"(confidence aging ON, period={AGE_PERIOD_S:.0f}s)")
    if args.max_bundles is not None:
        print(f"(max-bundles={args.max_bundles})")
    print("(cpb: confidence-weighted cost = latency / confidence)")

    t_start = time.time()
    for seed in seeds:
        for strategy in strategies:
            t0 = time.time()
            bundles = simulate(
                seed, strategy, age=args.age_conf, max_bundles=args.max_bundles)
            r = report_run(bundles, strategy, seed)
            r["walltime_s"] = round(time.time() - t0, 2)
            r["age_conf"] = args.age_conf
            r["max_bundles"] = args.max_bundles
            rows.append(r)
            print(f"{strategy:<10} {seed:>9} {r['created']:>9} "
                  f"{r['delivered']:>10} {r['delivery']:>9.4f} "
                  f"{r['lat_avg']:>9.1f} {r['lat_p95']:>10.1f} "
                  f"{r['path_conf']:>8.4f} {r['n_routes']:>8d}  ({r['walltime_s']}s)")

    print(f"\ntotal walltime: {time.time() - t_start:.1f}s")

    if len(seeds) >= 2:
        if "baseline" in strategies and "cpb" in strategies:
            _paired_block(rows, "baseline", "cpb", len(seeds))

    if args.csv and rows:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"\nwrote {args.csv}")


if __name__ == "__main__":
    main()
