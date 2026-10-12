# OpenStreetMap data license

`osm-circuits.geojson` contains track outlines derived from
[OpenStreetMap](https://www.openstreetmap.org) data, © OpenStreetMap contributors.

It is **not** covered by the repository's MIT License. It is made available under the
[Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/), as
OpenStreetMap requires for databases derived from its data. See
[openstreetmap.org/copyright](https://www.openstreetmap.org/copyright).

What it contains: one outline each for Circuito de Jerez, Fuji Speedway and the Korean
International Circuit, the F1 circuits that the bacinger/f1-circuits dataset does not cover.
Each outline is the closed loop of OpenStreetMap race-track ways (`highway=raceway`) whose
length matches the official F1 layout, starting at the start/finish line and running in the
race direction. The source way IDs and the OpenStreetMap data timestamp are recorded in each
feature. `scripts/import_osm_circuits.py` rebuilds the file from the Overpass API.

If you reuse this file or a database adapted from it:

- credit "© OpenStreetMap contributors" and link to https://www.openstreetmap.org/copyright;
- keep it, and any adapted database you share, under the ODbL 1.0.

The SimGent app shows this credit on the track map whenever one of these outlines is displayed.
