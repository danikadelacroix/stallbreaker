# 111 Act alone, or ask

**Status:** Rule 3 built; acting alone not planned · **Owner:** unassigned · **Depends on:** 003, 004

## Why

The use case asks for an agent. An agent that asks about everything is a form; one that never
asks is a risk. Ours acts alone only when there is nothing to trade off, and says so.

## Rules

1. A manager sets a policy: the most the agent may spend alone per part (default $50), and whether it may act alone at all.
2. The agent resolves a stall alone only if the plan misses no promise, moves no job, uses a safe source, is proven best, and costs no more than the limit.
3. Anything else waits for a person, with the reason shown ("needs you: 1 promise would be missed").
4. Everything done alone is in the decision log, marked as done by the agent, with the rule that allowed it.
5. With the policy off, nothing changes from today.

Built so far: rule 3. Every plan option carries `needs_you`, the list of reasons from `backend/policy.py`, and the card shows them; an approval logs `needed_a_person_because` and `decided_by`. Acting alone (rules 1, 2 and 4) is not planned: an order sent to a source cannot be taken back, so
every plan waits for a person and the card says why.

## Acceptance checks

| # | Check | Test |
|---|---|---|
| A1 | A stall with a free, safe, in-time fix is resolved alone and logged as such | to write |
| A2 | A stall that would miss a promise is never resolved alone | to write |
| A3 | A fix above the limit waits for a person | to write |
| A4 | Policy off: existing suite passes unchanged | existing suite |
