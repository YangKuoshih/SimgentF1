#!/usr/bin/env python3
"""
SimGent Model Context Protocol (MCP) Server
Exposes Grand Prix Race Intelligence, Incident Investigation, Telemetry, and Regulations to external AI agents.
Compatible with Claude Desktop, Cursor, Zed, Antigravity, and autonomous agent frameworks.
Operates 100% locally with zero external API dependencies and $0 billing risk.
"""

import sys
import json
import logging
from typing import Any, Dict, List, Optional

from app.tools import race_agent, race_replay
from app.tools.f1_telemetry import simulate_undercut, F1_REGULATIONS_ERAS, TRACK_BLUEPRINTS
from app.tools.guardrails import evaluate_all_guardrails, sanitize_input

logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s [F1-MCP] %(message)s")

TOOLS = [
    {
        "name": "query_race_engineer",
        "description": "Natural language pit wall race engineering copilot. Resolves driver telemetry, incident investigations, pit strategies, championship standings, and 2026 regulations across seasons 1950-2026.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language question (e.g., 'Why did Hamilton retire in Australia 2024?', 'Explain Verstappen pit strategy', '2026 active aero rules')."
                },
                "year": {
                    "type": "integer",
                    "description": "Season year (e.g. 2024, 2026). Default is 2024.",
                    "default": 2024
                },
                "round": {
                    "type": "integer",
                    "description": "Round number in season calendar. Default is 1.",
                    "default": 1
                },
                "session": {
                    "type": "string",
                    "description": "Session type: 'race', 'qualifying', or 'sprint'. Default is 'race'.",
                    "default": "race"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "investigate_incident",
        "description": "Investigate verified telemetry and steward debriefs for race retirements, crashes, and technical failures (e.g., Hamilton Australia 2024, Verstappen Silverstone 2021, Schumacher Spa 1998).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "driver": {
                    "type": "string",
                    "description": "Driver surname, code or identifier (e.g. 'hamilton', 'VER', 'senna')."
                },
                "year": {
                    "type": "integer",
                    "description": "Championship season year."
                },
                "circuit_or_race": {
                    "type": "string",
                    "description": "Circuit name or Grand Prix locality (e.g. 'australia', 'silverstone', 'monza')."
                }
            },
            "required": ["driver", "year"]
        }
    },
    {
        "name": "get_session_telemetry",
        "description": "Retrieve official lap-by-lap timing, finishing classification, intervals, pit stops, and sector geometry for an F1 session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": "Championship year (1950-2026)."
                },
                "round": {
                    "type": "integer",
                    "description": "Championship round number."
                },
                "session": {
                    "type": "string",
                    "description": "'race', 'qualifying', or 'sprint'.",
                    "default": "race"
                }
            },
            "required": ["year", "round"]
        }
    },
    {
        "name": "simulate_pit_strategy",
        "description": "Simulate an undercut or overcut pit stop window against a rival driver, calculating pit loss time, traffic corridors, and delta advantage.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "year": {"type": "integer", "description": "Season year (optional)"},
                "round": {"type": "integer", "description": "Round number (optional)"},
                "target_driver": {"type": "string", "description": "Attacking driver code or name (e.g. 'VER', 'HAM', 'NOR')", "default": "VER"},
                "rival_driver": {"type": "string", "description": "Target rival or race leader to leapfrog (e.g. 'NOR', 'LEC')"},
                "pit_lap": {"type": "integer", "description": "Target lap to box for fresh tyres"},
                "compound": {"type": "string", "description": "Tyre compound: 'soft', 'medium', or 'hard' (or 'S', 'M', 'H')", "default": "hard"},
                "circuit_name": {"type": "string", "description": "Circuit name (e.g. 'Bahrain', 'Silverstone', 'Monza')"},
                "disruption": {"type": "string", "description": "Race condition: 'Normal', 'Virtual Safety Car', or 'Full Safety Car'", "default": "Normal"},
                "total_laps": {"type": "integer", "description": "Total race laps (e.g. 55)"}
            },
            "required": ["pit_lap"]
        }
    },
    {
        "name": "lookup_fia_regulations",
        "description": "Look up FIA Formula 1 Technical and Sporting Regulations (e.g., 2026 50/50 hybrid power split, active aero X/Z-mode, Manual Overtake Mode, DRS rules).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Regulation topic (e.g. '2026 engine', 'active aero', 'drs', 'penalties')."
                }
            },
            "required": ["topic"]
        }
    },
    {
        "name": "get_championship_standings",
        "description": "Retrieve official FIA Formula 1 World Drivers' and Constructors' Championship standings.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": "Championship season year (e.g. 2024, 2026)."
                }
            },
            "required": ["year"]
        }
    }
]

RESOURCES = [
    {
        "uri": "f1://standings/2026",
        "name": "2026 World Championship Standings",
        "description": "Current official FIA Formula 1 World Drivers' and Constructors' Championship standings.",
        "mimeType": "application/json"
    },
    {
        "uri": "f1://standings/2024",
        "name": "2024 World Championship Standings",
        "description": "Historical final 2024 FIA Formula 1 World Drivers' and Constructors' Championship standings.",
        "mimeType": "application/json"
    },
    {
        "uri": "f1://regulations/2026",
        "name": "2026 FIA Technical Regulations",
        "description": "2026 Technical Regulations specification: Active Aerodynamics (X-mode/Z-mode), 50/50 Hybrid power unit split, and Manual Overtake Mode (MOM).",
        "mimeType": "application/json"
    },
    {
        "uri": "f1://circuits",
        "name": "Formula 1 Circuit Blueprints",
        "description": "Track blueprints, corner counts, lap records, and tyre stress ratings for all 24 circuits.",
        "mimeType": "application/json"
    }
]

PROMPTS = [
    {
        "name": "race_incident_investigation",
        "description": "Investigate a driver retirement, crash, or mechanical failure with verified telemetry debrief.",
        "arguments": [
            {"name": "driver", "description": "Driver surname or code (e.g. 'hamilton', 'VER')", "required": True},
            {"name": "year", "description": "Season year (e.g. 2024, 2026)", "required": True},
            {"name": "race", "description": "Grand Prix locality or circuit name (e.g. 'Australia', 'Monza')", "required": False}
        ]
    },
    {
        "name": "pit_undercut_analysis",
        "description": "Perform an undercut tactical evaluation against a target rival to project leapfrog delta and clean air window.",
        "arguments": [
            {"name": "target_driver", "description": "Attacking driver code (e.g. 'VER', 'NOR')", "required": True},
            {"name": "rival_driver", "description": "Defending rival driver code (e.g. 'LEC', 'HAM')", "required": False},
            {"name": "pit_lap", "description": "Target lap to box for tyres (e.g. 18, 35)", "required": True},
            {"name": "compound", "description": "Target compound ('soft', 'medium', 'hard')", "required": False}
        ]
    }
]


def handle_tool_call(name: str, args: Dict[str, Any]) -> Any:
    if name == "query_race_engineer":
        raw_query = args.get("query", "")
        clean_query = sanitize_input(raw_query, max_chars=500)
        ctx = {
            "year": args.get("year", 2024),
            "round": args.get("round", 1),
            "session_type": args.get("session", "race")
        }
        blocked, guardrail_resp = evaluate_all_guardrails(clean_query, ctx)
        if blocked and guardrail_resp:
            return {
                "response": guardrail_resp.get("text", ""),
                "tool_invoked": guardrail_resp.get("tool"),
                "intent": "guardrail_intercept",
                "card": guardrail_resp.get("a2ui_card")
            }
        res = race_agent.answer_race_engineer_query(clean_query, ctx)
        return {
            "response": res.get("text", ""),
            "tool_invoked": res.get("tool"),
            "intent": res.get("intent"),
            "card": res.get("a2ui_card")
        }

    elif name == "investigate_incident":
        query = f"Why did {args['driver']} retire in {args.get('circuit_or_race', '')} {args['year']}?"
        res = race_agent.answer_race_engineer_query(query, {"year": args["year"]})
        return {
            "debrief": res.get("text", ""),
            "tool": res.get("tool"),
            "card": res.get("a2ui_card")
        }

    elif name == "get_session_telemetry":
        model = race_replay.build_replay(args["year"], args["round"], session_type=args.get("session", "race"))
        if not model:
            return {"error": f"Session model unavailable for {args['year']} Round {args['round']}"}
        drivers = [
            {
                "pos": d["finish"],
                "name": d["name"],
                "code": d["code"],
                "team": d["team"],
                "grid": d["grid"],
                "status": d["status"],
                "laps": d["laps"],
                "pits": d["pits"]
            }
            for d in model["drivers"]
        ]
        return {
            "meta": model["meta"],
            "drivers": drivers,
            "events": model.get("events", [])
        }

    elif name == "simulate_pit_strategy":
        raw_comp = str(args.get("compound", "H")).strip().upper()
        comp_code = raw_comp[0] if raw_comp else "H"
        res = simulate_undercut(
            pit_lap=args["pit_lap"],
            target_compound=comp_code,
            disruption=args.get("disruption", "Normal"),
            target_driver=args.get("target_driver", "VER"),
            rival_driver=args.get("rival_driver"),
            circuit_name=args.get("circuit_name"),
            total_laps=args.get("total_laps")
        )
        return res

    elif name == "lookup_fia_regulations":
        res = race_agent.answer_race_engineer_query(args["topic"])
        return {"regulations": res.get("text", "")}

    elif name == "get_championship_standings":
        st = race_replay.standings(args["year"])
        return st

    else:
        raise ValueError(f"Unknown tool: {name}")


def handle_resource_read(uri: str) -> Dict[str, Any]:
    if uri == "f1://standings/2026":
        return race_replay.standings(2026)
    elif uri == "f1://standings/2024":
        return race_replay.standings(2024)
    elif uri == "f1://regulations/2026":
        era = next((e for e in F1_REGULATIONS_ERAS if e.get("era_id") == "2026_active_aero"), F1_REGULATIONS_ERAS[0])
        return era
    elif uri == "f1://circuits":
        return TRACK_BLUEPRINTS
    else:
        raise ValueError(f"Unknown resource URI: {uri}")


def handle_prompt_get(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if name == "race_incident_investigation":
        driver = arguments.get("driver", "Driver")
        year = arguments.get("year", 2024)
        race = arguments.get("race", "Grand Prix")
        return {
            "description": f"Incident debrief for {driver} in {race} {year}",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"Please conduct a comprehensive incident investigation for {driver} during the {year} {race}. Provide official retirement lap, telemetry indicators, mechanical or collision root cause, and steward findings."
                    }
                }
            ]
        }
    elif name == "pit_undercut_analysis":
        target = arguments.get("target_driver", "VER")
        rival = arguments.get("rival_driver", "Leader")
        lap = arguments.get("pit_lap", 30)
        compound = arguments.get("compound", "hard")
        return {
            "description": f"Pit stop undercut simulation for {target} vs {rival}",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"Simulate an aggressive undercut pit window for {target} pitting on Lap {lap} onto {compound} tyres against {rival}. Calculate out-lap fresh rubber delta, projected traffic corridor, and net track position leapfrog probability."
                    }
                }
            ]
        }
    else:
        raise ValueError(f"Unknown prompt name: {name}")


def main():
    """Stdio JSON-RPC 2.0 loop compliant with Model Context Protocol specification."""
    logging.info("SimGent MCP server started on stdio.")
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            msg = json.loads(line)
            req_id = msg.get("id")
            method = msg.get("method")
            params = msg.get("params", {})

            if method == "initialize":
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {
                            "name": "f1-simgent-mcp",
                            "version": "1.2.0"
                        },
                        "capabilities": {
                            "tools": {},
                            "resources": {},
                            "prompts": {}
                        }
                    }
                }
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()

            elif method == "notifications/initialized":
                # Client acknowledge
                pass

            elif method == "tools/list":
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": TOOLS
                    }
                }
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()

            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                try:
                    result = handle_tool_call(tool_name, tool_args)
                    resp = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(result, indent=2) if isinstance(result, (dict, list)) else str(result)
                                }
                            ]
                        }
                    }
                except Exception as ex:
                    resp = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "isError": True,
                        "result": {
                            "content": [{"type": "text", "text": f"Error executing {tool_name}: {str(ex)}"}]
                        }
                    }
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()

            elif method == "resources/list":
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "resources": RESOURCES
                    }
                }
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()

            elif method == "resources/read":
                uri = params.get("uri", "")
                try:
                    data = handle_resource_read(uri)
                    resp = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "contents": [
                                {
                                    "uri": uri,
                                    "mimeType": "application/json",
                                    "text": json.dumps(data, indent=2)
                                }
                            ]
                        }
                    }
                except Exception as ex:
                    resp = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "isError": True,
                        "result": {
                            "content": [{"type": "text", "text": f"Error reading resource {uri}: {str(ex)}"}]
                        }
                    }
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()

            elif method == "prompts/list":
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "prompts": PROMPTS
                    }
                }
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()

            elif method == "prompts/get":
                prompt_name = params.get("name", "")
                prompt_args = params.get("arguments", {})
                try:
                    p_res = handle_prompt_get(prompt_name, prompt_args)
                    resp = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": p_res
                    }
                except Exception as ex:
                    resp = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "isError": True,
                        "result": {
                            "content": [{"type": "text", "text": f"Error resolving prompt {prompt_name}: {str(ex)}"}]
                        }
                    }
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()

            elif method == "ping":
                resp = {"jsonrpc": "2.0", "id": req_id, "result": {}}
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()

            else:
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method '{method}' not found"
                    }
                }
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()

        except Exception as e:
            logging.error(f"Error processing message: {e}")


if __name__ == "__main__":
    main()
