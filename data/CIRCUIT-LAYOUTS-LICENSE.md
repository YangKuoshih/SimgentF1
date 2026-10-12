# Circuit layouts: sources and licenses

`circuit-layouts.json` records, for every World Championship Grand Prix, the circuit layout
raced and its figures, plus an outline for every layout. It is built by
`scripts/build_circuit_layouts.py` from:

- **F1DB** (https://github.com/f1db/f1db), release recorded in the file, licensed under
  [Creative Commons Attribution 4.0 (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
  Used: each race's circuit layout, direction, course length, turns, laps, distance and
  fastest lap. Changes: reduced to these fields; the Indianapolis 500 oval races (1950-60)
  are recorded as anticlockwise (F1DB gives the circuit's clockwise direction to both
  Indianapolis layouts).
- **f1-circuits-svg** (https://github.com/MisterSix2295/f1-circuits-svg), commit recorded in
  the file, MIT License, Copyright (c) 2024-2025 ROY Jules. See `f1-circuits-svg.LICENSE`.
  Used: one outline per layout, scaled to F1DB's length, turned to the race direction and,
  where the venue has a geographic outline, to its map orientation.

Layouts that match one of our geographic outlines (`f1-circuits.geojson`, MIT, bacinger;
`osm-circuits.geojson`, ODbL, OpenStreetMap contributors) use that outline instead.

The start/finish line of an outline drawn from f1-circuits-svg is estimated: taken from the
venue's geographic outline when the two share that stretch of track, otherwise placed at the
middle of the longest straight.

If you reuse this file, credit F1DB (CC BY 4.0) and keep the f1-circuits-svg MIT notice.
