"""When does a plan need a person? One small rule, no model.

A plan can only ever be acted on without asking if it trades nothing off: no promise missed,
no job moved, a source that is safe to borrow from, a cost under the manager's limit, and a
plan the solver proved best. Anything else is listed as a reason, in plain words."""

SPEND_LIMIT = 50  # dollars the agent may spend on one part without asking


def _n(count, word):
    return f"{count} {word}{'s' if count != 1 else ''}"


def needs_a_person(option, source_safe, spend_limit=SPEND_LIMIT):
    """Reasons this plan must be approved by a person. An empty list means nothing is traded off."""
    reasons = []
    if option["missed_promises"]:
        reasons.append(f"{_n(option['missed_promises'], 'promise')} would be missed")
    if not source_safe:
        reasons.append("the source is unsafe to lend from")
    if option.get("bay_decision") == "roll_out":
        reasons.append("the car would be rolled out of its bay")
    if option["jobs_moved"]:
        reasons.append(f"{_n(option['jobs_moved'], 'job')} would move")
    if option["cost"] > spend_limit:
        reasons.append(f"it costs ${option['cost']:.0f}, above the ${spend_limit} limit")
    if not option["proven_best"]:
        reasons.append("the plan is not proven best")
    return reasons
