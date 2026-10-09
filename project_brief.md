# Project Brief: F1 Simgent — Agentic Race Telemetry, Circuit Replay & Technical Regulations Engine

## 1. Executive Summary
**F1 Simgent** is an agent-first Formula 1 telemetry, race replay, and historical analytics web application. It transforms raw Formula 1 timing, GPS telemetry, and official Race Control event streams into an interactive pit-wall command center. 

Users can:
1. Track every race across modern and historical seasons with dynamic circuit layouts.
2. Observe micro-scale 2D F1 car models moving across real circuit geometry in authentic team brand liveries.
3. Control replay playback at variable speeds (0.25x slow-mo to 10x time-lapse) with real-time **Race Control event tracking** (Safety Cars, Virtual Safety Cars, Red Flags, Yellow Flags, and Retirements/DNFs).
4. Track **Drivers' (WDC) and Constructors' (WCC) Championship standings** across the season.
5. Explore an **F1 Technical Regulations & Engine Era Primer** comparing power units, downforce concepts, and energy balances (e.g., 2026 50/50 electric split vs. 2024 Ground Effect vs. 2004 V10 screamer vs. 1960s Classic) through on-screen AI analysis.
6. Collaborate with an on-screen **AI Race Strategist Copilot** powered by Google Cloud Vertex AI and A2UI.

---

## 2. Target Audience & Core Value Proposition
- **Formula 1 Fans & Analysts**: Want genuine race data (lap times, sector deltas, tire wear curves, telemetry traces, safety car disruptions) beyond basic TV broadcast graphics.
- **Sim Racers & Engineers**: Want to study cornering speeds, apex trajectories, and braking markers across actual race weekends.
- **Motorsport Historians & Technical Geeks**: Want to understand how different eras of technical regulations (engine power, hybrid energy deployment, aero philosophies) fundamentally shifted race outcomes.
- **Core Value**: Combines authentic physics/GPS telemetry with an intuitive, uncluttered UI and a proactive AI Race Engineer that interprets complex data on demand.

---

## 3. UI/UX Principles (High-End Motorsport Design — Anti-Slop)
1. **Calibrated Information Density**: Avoid sensory overload. Vital data is structured with strict tabular alignment, monospace numerals (`JetBrains Mono`), and clear typographic hierarchy (`Space Grotesk` headers, `Inter` prose).
2. **Unified Design System ("Aerodynamic Telemetry Cockpit")**:
   - **Chassis Background**: Deep Monocoque Carbon `#0B0F19` and `#0F131D`.
   - **Glass Surfaces**: Container obsidian decks (`#111827` @ 85% opacity, backdrop blur 16px) with 1px slate borders (`rgba(255, 255, 255, 0.07)`).
   - **Signal Colors**: Formula 1 Racing Red `#E10600` (primary triggers, heavy braking, red flags), Telemetry Cyan `#00F5D4` (speed traces, active DRS), Sector Purple `#A855F7` (fastest laps), Warning Amber `#FFB703` (pit windows, yellow flags, VSC).
3. **Purposeful Interactivity**:
   - Selecting any Grand Prix or season immediately re-skins the entire cockpit with the exact circuit layout, race results, and driver grid.
   - Scrubbing the race timeline automatically syncs the track map, timing tower, telemetry traces, flag alerts, and copilot context.
   - Hovering over cars reveals concise micro-tooltips rather than screen-blocking modals.

---

## 4. Key Application Features

### A. Authentic Track Ribbon & Real GPS Coordinate Mapping
- Accurate 2D vector circuit geometry rendered from over 30,000+ real \((x, y, z)\) GPS coordinates per car per session via the free **OpenF1 API** and **FastF1**.
- Supports 40+ Grand Prix circuits: Silverstone, Monaco, Spa-Francorchamps, Monza, Suzuka, Miami, Austin COTA, Interlagos, Zandvoort, Spielberg, Bahrain, Jeddah, etc.
- Detailed circuit features: asphalt texture, apex rumble kerbs, DRS detection lines, DRS activation zones, pit lane entry/exit, and labeled corner apexes.

### B. Miniature F1 Car Models with Official Team Liveries
- Top-down vector micro-car chassis models:
  - Aerodynamic silhouette: front wing, nosecone, halo cockpit, sculpted sidepods, 4 exposed black wheels, and rear wing.
  - **Authentic Brand Liveries**: Red Bull (#3671C6 navy / yellow nose), McLaren (#FF8000 papaya), Ferrari (#E80020 rosso corsa), Mercedes (#27F4D2 cyan / silver), Aston Martin (#229971 British racing green), Alpine (#FF87BC pink / blue), Kick Sauber (#52E252 neon green), Williams (#64C4FF cyan), Haas, RB.
  - **Dynamic Heading Rotation**: Chassis rotates smoothly to match real GPS velocity vectors \(\theta = \arctan2(\Delta y, \Delta x)\).
  - **Pirelli Tyre Compound Rings**: Color-coded tire rings (Red = Soft, Yellow = Medium, White = Hard, Green = Inters, Blue = Wets).
  - **Active DRS Wing**: Rear wing flap illuminates or animates open when DRS is active.

### C. Live Race Control, Safety Cars, Flags & Incident Tracking
- Full ingestion of OpenF1 `/race_control` events:
  - **Safety Car (SC)** & **Virtual Safety Car (VSC)** deployments with exact laps and timestamps.
  - **Flag Tracking**: GREEN, YELLOW (Sector 1, 2, 3), DOUBLE YELLOW, and RED FLAGS.
  - **Incidents & Retirements (DNF)**: Collisions, track limit deletions, mechanical retirements.
- Dynamic timeline scrubber annotations marking exact moments where Safety Cars or crashes flipped the race outcome.
- Dynamic track status banner turning Yellow, Red, or VSC and slowing cars down to safety car delta speed.

### D. Season Championship & Constructors' Cup Standings
- Tracks **World Drivers' Championship (WDC)** and **World Constructors' Championship (WCC)** standings after every round.
- Displays championship leader points, win tallies, podium finishes, and constructor battle margins.

### E. F1 Technical Regulations & Power Unit Era Matrix
- Historical and futuristic technical primer comparing how engine architecture, downforce, and electrical deployment shaped racing across eras:
  - **2026 Era**: Active Aero (X-mode straight / Z-mode corner), 50% Internal Combustion + 50% 350kW Electric MGU-K, 100% Sustainable Fuels, Manual Overtake Mode (MOM), elimination of MGU-H.
  - **2022–2025 Ground Effect Era**: Venturi tunnels underfloor, 1.6L V6 Turbo Hybrid (160kW MGU-K + MGU-H, ~1000 hp), 18-inch low profile tires.
  - **2014–2021 Turbo Hybrid Era**: 1.6L V6 Turbo with complex ERS (>50% thermal efficiency), wide high-downforce regulations (2017–2020).
  - **2006–2013 V8 Era**: 2.4L Naturally Aspirated V8 (18,000 RPM, ~750 hp), KERS battery boost (2009), DRS introduction (2011).
  - **1995–2005 V10 Era**: 3.0L V10 screaming at 20,000 RPM (~950 hp), in-race refueling sprint strategies, traction control.
  - **1980s Turbo Era**: 1.5L Turbo qualifying engines producing over 1,400 hp at 5.5 bar boost.
  - **1960s Classic Era**: Cigar-shaped chassis, 1.5L / 3.0L atmospheric engines (Cosworth DFV), zero wings.
- AI Copilot analyzes how regulation changes alter race dynamics and strategy on demand.

### F. Multi-Channel Telemetry Oscilloscope
- Synchronized telemetry comparison (Speed km/h, Throttle %, Brake pressure %, Gear, DRS) between any two drivers.
- Micro-sector speed trap analysis and corner entry/exit delta graphs.

### G. On-Screen AI Race Engineer (GCP Vertex AI Copilot)
- Context-aware conversational agent positioned as your pit-wall race strategist.
- **Proactive Insights**: Explains tactical consequences of Safety Cars, undercut windows, rain transitions, and technical regulation impacts.
- **Interactive A2UI Cards**:
  - *Undercut Strategy Simulation*: Pit loss delta, target re-entry traffic window, tire life delta.
  - *Race Turning Points & Incident Debrief*: Chronological safety car and crash breakdown.
  - *Regulation Era Comparison Card*: Power output, battery capacity, downforce philosophy.
  - *Action Buttons*: "Simulate VSC Pit Window", "Compare NOR vs VER Speed", "Analyze 2026 Engine Impact".

---

## 5. Google Cloud (GCP) Architecture & Services

| GCP Component | Role in F1 Simgent | Implementation Details |
| :--- | :--- | :--- |
| **Vertex AI Agent Platform / ADK** | Brain & Agentic Runtime | Python agent in `app/agent.py` orchestrating deterministic tools, session state, and Gemini reasoning. |
| **Vertex AI Memory Bank** | Cross-Session User Memory | Remembers user preferences: favorite teams/drivers, home Grand Prix, preferred units (km/h vs mph), favorite regulation eras. |
| **Cloud Firestore** | Structured Real-Time DB | Stores season calendars, driver profiles, cached race results, session bookmarks, WDC/WCC standings, and race control events. |
| **Cloud Storage (GCS)** | High-Volume Blob Storage | Public bucket storing normalized circuit coordinate GeoJSON/SVG files, cached telemetry slices, and generated strategy cards. |
| **Vertex AI Serverless RAG Engine** | Knowledge Grounding | Vector corpus indexing FIA Formula 1 Sporting Regulations (SC/VSC rules, DRS rules, tire allocation) and 2026 vs 2024 Technical Regulations. |
| **Code Execution Sandbox** | Safe Mathematical Modeling | Runs Python scripts via `AgentEngineSandboxCodeExecutor` to calculate quadratic tire decay, undercut probabilities, and energy deployment limits. |
| **Gemini Multimodal (`gemini-3.1-flash-lite-image`)** | Generative Visual Assets | Generates circuit weather radar overlays, race infographic banners, and event posters. |
| **A2UI (Agent-to-UI)** | Rich Interactive Responses | Structures agent responses into UI cards, timing tables, and clickable action chips using `a2ui_utils.py` and `A2uiSchemaManager`. |
| **Cloud Run** | Web App & Proxy Hosting | Houses the FastAPI proxy backend and serves the high-performance HTML5 Canvas / Tailwind frontend, authenticating via ADC. |

---

## 6. Stitch Screen Matrix (Strict Unified Design System)

All screens share the unified `Aerodynamic Telemetry Cockpit` design system (`assets/30b619bafd584750b103188f1b246588`), adhering to 44pt minimum touch targets, dark carbon palette, Space Grotesk headers, and JetBrains Mono telemetry metrics:

1. **Screen 1 — Race Center & Replay Cockpit** (`ac564f37a5da46baa6881f4f88ca215b`): Live race command center with real-time Safety Car & Flag status banners, 2D vector track map with miniature livery-accurate F1 cars, timing tower, replay scrubber with incident markers, and AI copilot drawer.
2. **Screen 2 — Precision Circuit & Car Visualizer** (`83402bf2e1874ee8a58359cd1f70c0c4`): Zoomed-in track ribbon with high-detail micro F1 cars in authentic liveries, dynamic velocity tags, and Stowe apex battle camera.
3. **Screen 3 — Season Archives, Circuits & Championship Standings** (`51997ee0f20b4a9ebc386cfc5daf0bf1`): Multi-year season browser, WDC / WCC points tables, circuit technical blueprints, lap records, turn breakdowns, session selectors (FP1–Race), and AI race debriefs.
4. **Screen 4 — AI Strategy Simulator & Regulations Workbench** (`865e38f80b57420ba637170ce0e03b9a`): Tactical workbench with pit stop slider, tire degradation curves, pit exit traffic corridor, Monte Carlo simulations, and **F1 Engine & Regulations Era Primer**.
