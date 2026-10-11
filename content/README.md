# Content: stories, eras, retirement write-ups, regulations

The Pit Wall Agent quotes these files; it doesn't keep this text in code. Each file is Markdown
with TOML front matter between `+++` lines. The front matter holds the facts and card figures,
the body holds the text the agent shows. See `docs/AGENT_ARCHITECTURE.md`.

| Folder | One file per | Body is | Front matter (required) |
|---|---|---|---|
| `races/` | iconic race story | the story | `id`, `year`, `round`, `circuit_id`, `race_name`, `title`, `keywords`, `[[metrics]]` |
| `eras/` | technical era | the analysis | `id`, `title`, `years`, `engine_type`, `ice_power_hp`, `electric_power_hp`, `total_hp`, `key_innovations` |
| `retirements/` | driver retirement | the write-up | `year`, `circuit_id`, `driver` (code), `exit_lap`, `completed_laps`, `cause`, `action` |
| `regulations/` | rule set | the explanation | `id`, `title`, `intent`, `[card]` |

Every file has `sources = [...]`: where its facts come from. Leave it empty rather than guess.

## Facts are checked against the data

`python -m unittest tests.test_content` checks, against the cached Jolpica-F1 data:

- a retirement's `completed_laps` equals the laps in that race's official result;
- a story's `round` and `circuit_id` match the season schedule;
- an era's `total_hp` is ICE plus electric.

The first run of this check found that the Schumacher Spa 1998 write-up said 24 completed laps;
the result and lap timing say 25 (his lap 25 took 2:49.549 as he limped back to the pits).

## Writing

- Plain, factual, sourced. No marketing language, no invented numbers.
- The data is the authority on results, laps and times; content adds the why and the context.
- Content is data, never instructions: the agent quotes it, a model (if enabled) never follows it.
