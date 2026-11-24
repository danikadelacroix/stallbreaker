# When rolling the car out pays (200 seeded days per setting)

12 repair orders, 4 technicians, 1 flat bay; stalls where the car can be made movable.
Averages per stall: always hold the bay, then let the engine choose. All data is synthetic.

| Lift bays | Part at least | Stalls | Rolled out | Promises missed | Late minutes | Bay blocked (min) |
|---|---|---|---|---|---|---|
| 3 | as generated | 84 | 0 | 0.08 to 0.08 | 2.6 to 2.6 | 76 to 76 |
| 3 | 2 h away | 84 | 1 | 0.37 to 0.37 | 15.6 to 15.4 | 125 to 123 |
| 3 | 4 h away | 84 | 2 | 1.04 to 1.01 | 105.1 to 103.9 | 240 to 234 |
| 3 | 6 h away | 84 | 4 | 1.07 to 1.01 | 230.7 to 224.3 | 360 to 343 |
| 2 | as generated | 89 | 19 | 0.57 to 0.42 | 29.2 to 30.4 | 70 to 54 |
| 2 | 2 h away | 89 | 33 | 0.98 to 0.64 | 71.7 to 55.5 | 123 to 78 |
| 2 | 4 h away | 89 | 44 | 1.61 to 1.07 | 206.5 to 149.6 | 240 to 121 |
| 2 | 6 h away | 89 | 46 | 1.70 to 1.07 | 360.7 to 267.1 | 360 to 174 |

Reading: with three lift bays the next car nearly always finds another bay, so holding costs little and the
engine almost never rolls a car out. With two lift bays, or when the part is hours away, rolling out keeps
promises that holding the bay would lose. The roll-out and set-up minutes are assumptions (see shopgen.MOVABLE).
