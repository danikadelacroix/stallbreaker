"""Seeded synthetic service-shop days. Every number here is invented and documented;
nothing comes from a real dealership."""
import random

from shopcore import Bay, Job, Shop, Source, Stall, Tech, initial_plan

L, F = ("lift",), ("flat",)
# (description, minutes, skill, bay kinds, relative frequency)
OPS = [
    ("Oil service", 45, "general", L + F, 5),
    ("Diagnostic scan", 40, "electrical", L + F, 3),
    ("Wheel alignment", 60, "alignment", F, 3),
    ("Battery and charging check", 75, "electrical", L + F, 2),
    ("AC service", 80, "general", L + F, 2),
    ("Front brake pads", 90, "brakes", L, 4),
    ("Suspension arm", 110, "general", L, 2),
    ("Rotors and brake fluid", 120, "brakes", L, 2),
    ("Timing belt", 150, "engine", L, 2),
    ("Water pump replacement", 180, "engine", L, 2),
]
SKILLSETS = [
    {"engine", "brakes", "general"},
    {"brakes", "general", "electrical"},
    {"general", "electrical", "alignment"},
    {"engine", "general", "alignment"},
    {"brakes", "electrical", "general"},
]
NAMES = ["Meera", "Kavya", "Riya", "Ananya", "Diya"]


def make_shop(n_tech=4, n_lift=3, n_flat=1):
    techs = tuple(Tech(NAMES[i], frozenset(SKILLSETS[i])) for i in range(n_tech))
    bays = tuple(Bay(f"Bay {i + 1}", "lift") for i in range(n_lift)) + \
        tuple(Bay(f"Bay {n_lift + i + 1}", "flat") for i in range(n_flat))
    return Shop(techs, bays)


def make_jobs(rng, n=12, first_id=101):
    jobs = []
    weights = [o[4] for o in OPS]
    for i in range(n):
        desc, dur, skill, kinds, _ = rng.choices(OPS, weights)[0]
        release = 0 if i < n // 3 else rng.randrange(0, 301, 15)
        slack = rng.randrange(60, 241, 15)
        jobs.append(Job(f"RO-{first_id + i}", desc, dur, skill, kinds, due=release + dur + slack, release=release))
    return jobs


def make_sources(rng):
    def src(i, name, lo, hi, cost, risk):
        return Source(i, name, eta=rng.randrange(lo, hi + 1, 5), cost=cost, risk=round(risk, 2), safe=risk <= 0.30)
    return (
        src("sisterA", "Sister store A", 30, 60, 15, rng.uniform(0, 0.8)),
        src("vendor", "Local vendor courier", 45, 90, rng.randrange(60, 121, 5), 0.0),
        src("sisterB", "Sister store B", 80, 140, 15, rng.uniform(0, 0.5)),
        src("oem", "OEM depot truck", 180, 300, 0, 0.0),
    )


def make_day(seed, n_jobs=12, **shop_kw):
    """A shop, its jobs and a morning plan. Same seed gives the same day."""
    rng = random.Random(seed)
    shop = make_shop(**shop_kw)
    jobs = make_jobs(rng, n_jobs)
    base = initial_plan(shop, jobs, time_limit=1.5, deterministic=True)
    return rng, shop, jobs, base


def make_stall(rng, jobs, base):
    """Pick a moment and a job in progress whose part turns out to be missing."""
    for _ in range(40):
        now = rng.randrange(60, 361, 15)
        cands = [j for j in jobs if base.assign[j.id].start + 20 <= now <= base.assign[j.id].end - 20]
        if cands:
            j = rng.choice(sorted(cands, key=lambda j: j.id))
            return now, Stall(j.id, "part", make_sources(rng))
    return None, None
