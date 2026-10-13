"""
SimGent - Comprehensive Formula 1 History & Career Knowledge Base (1950–2026)
Provides authoritative data, fuzzy driver matching, career timelines, technical eras,
championship rosters, all-time records, and legendary rivalries for motorsport research and analysis.
"""

import difflib
import functools
import os
import re
from functools import lru_cache
import json
from typing import Any, Dict, List, Optional, Tuple
from app.agent import content as _content

# =============================================================================
# 1. HISTORICAL DRIVER ENCYCLOPEDIA (WORLD CHAMPIONS & LEGENDS 1950–2026)
# =============================================================================

HISTORICAL_DRIVERS: Dict[str, Dict[str, Any]] = {
    "michael_schumacher": {
        "id": "michael_schumacher",
        "name": "Michael Schumacher",
        "code": "MSC",
        "nationality": "German",
        "born": "1969-01-03",
        "active_years": "1991–2006, 2010–2012 (19 seasons)",
        "seasons_count": 19,
        "debut": "1991 Belgian GP (Jordan-Ford)",
        "final_race": "2012 Brazilian GP (Mercedes)",
        "primary_eras": [
            "3.5L Naturally Aspirated Era (1991–1994)",
            "3.0L V10 Golden Era (1995–2005)",
            "2.4L V8 Screamer Era (2006, 2010–2012)"
        ],
        "primary_era_summary": "3.0L V10 Golden Era (1995–2005) & 3.5L Atmo Era (1991–1994)",
        "championships": [1994, 1995, 2000, 2001, 2002, 2003, 2004],
        "titles_count": 7,
        "starts": 306,
        "wins": 91,
        "podiums": 155,
        "poles": 68,
        "fastest_laps": 77,
        "career_points": 1566.0,
        "teams": [
            {"team": "Jordan", "years": "1991"},
            {"team": "Benetton", "years": "1991–1995"},
            {"team": "Ferrari", "years": "1996–2006"},
            {"team": "Mercedes", "years": "2010–2012"}
        ],
        "iconic_car": "Ferrari F2004 (3.0L V10, 15 wins in 18 races)",
        "landmark_race": {
            "year": 1998,
            "round": 13,
            "race_name": "Belgian Grand Prix (Spa-Francorchamps)",
            "circuit_id": "spa",
            "driver": "MSC",
            "lap": 24,
            "button_text": "EXPLORE 1998 SCHUMACHER REPLAY"
        },
        "highlights": (
            "Won back-to-back titles with Benetton (1994–1995) before orchestrating Ferrari's golden renaissance, "
            "clinching 5 consecutive World Championships (2000–2004). Known as the 'Regenmeister' (Rain Master) "
            "for masterclasses such as the 1996 Spanish GP. Held the all-time wins record (91) for 14 years."
        ),
        "aliases": [
            "schumacher", "michael", "schumi", "michael schumacher", "msc", "schuey", "shumacher",
            "schmacur", "shumaker", "micheal schumacher", "micheal", "schumaker"
        ]
    },
    "ayrton_senna": {
        "id": "ayrton_senna",
        "name": "Ayrton Senna",
        "code": "SEN",
        "nationality": "Brazilian",
        "born": "1960-03-21",
        "active_years": "1984–1994 (11 seasons)",
        "seasons_count": 11,
        "debut": "1984 Brazilian GP (Toleman)",
        "final_race": "1994 San Marino GP (Williams)",
        "primary_eras": [
            "1.5L Turbo Monster Era (1984–1988)",
            "3.5L Naturally Aspirated Era (1989–1994)"
        ],
        "primary_era_summary": "1,400hp Turbo Monster Era (1984–1988) & 3.5L Atmo Era (1989–1994)",
        "championships": [1988, 1990, 1991],
        "titles_count": 3,
        "starts": 161,
        "wins": 41,
        "podiums": 80,
        "poles": 65,
        "fastest_laps": 19,
        "career_points": 614.0,
        "teams": [
            {"team": "Toleman", "years": "1984"},
            {"team": "Lotus", "years": "1985–1987"},
            {"team": "McLaren", "years": "1988–1993"},
            {"team": "Williams", "years": "1994"}
        ],
        "iconic_car": "McLaren MP4/4 (1.5L Turbo V6 Honda, 15/16 wins in 1988)",
        "landmark_race": {
            "year": 1988,
            "round": 12,
            "race_name": "Italian Grand Prix (Monza)",
            "circuit_id": "monza",
            "driver": "SEN",
            "lap": 49,
            "button_text": "EXPLORE 1988 SENNA REPLAY"
        },
        "highlights": (
            "Renowned for supernatural qualifying pace (65 poles) and wet-weather brilliance (Donington 1993 'Lap of the Gods', "
            "Monaco 1984). Won 3 World Championships with McLaren-Honda in iconic battles against Alain Prost."
        ),
        "aliases": ["senna", "ayrton", "ayrton senna", "sen", "sena", "ayrton sena"]
    },
    "alain_prost": {
        "id": "alain_prost",
        "name": "Alain Prost",
        "code": "PRO",
        "nationality": "French",
        "born": "1955-02-24",
        "active_years": "1980–1991, 1993 (13 seasons)",
        "seasons_count": 13,
        "debut": "1980 Argentine GP (McLaren)",
        "final_race": "1993 Australian GP (Williams)",
        "primary_eras": [
            "1.5L Turbo Monster Era (1980–1988)",
            "3.5L Naturally Aspirated Era (1989–1993)"
        ],
        "primary_era_summary": "Turbo Monster Era (1980–1988) & 3.5L V10 Era (1989–1993)",
        "championships": [1985, 1986, 1989, 1993],
        "titles_count": 4,
        "starts": 199,
        "wins": 51,
        "podiums": 106,
        "poles": 33,
        "fastest_laps": 41,
        "career_points": 798.5,
        "teams": [
            {"team": "McLaren", "years": "1980, 1984–1989"},
            {"team": "Renault", "years": "1981–1983"},
            {"team": "Ferrari", "years": "1990–1991"},
            {"team": "Williams", "years": "1993"}
        ],
        "iconic_car": "Williams FW15C (3.5L Renault V10, active suspension)",
        "landmark_race": {
            "year": 1988,
            "round": 12,
            "race_name": "Italian Grand Prix (Monza)",
            "circuit_id": "monza",
            "driver": "PRO",
            "lap": 34,
            "button_text": "EXPLORE 1988 PROST REPLAY"
        },
        "highlights": (
            "Nicknamed 'The Professor' for meticulous racecraft, tyre conservation, and strategic calculation. "
            "Won 4 World Championships across McLaren and Williams, holding the all-time victory record (51) until 2001."
        ),
        "aliases": ["prost", "alain", "alain prost", "pro", "the professor", "prostt", "prosst"]
    },
    "lewis_hamilton": {
        "id": "hamilton",
        "name": "Lewis Hamilton",
        "code": "HAM",
        "nationality": "British",
        "born": "1985-01-07",
        "active_years": "2007–Present (19+ seasons)",
        "seasons_count": 19,
        "debut": "2007 Australian GP (McLaren)",
        "final_race": "Active (Ferrari 2025+)",
        "primary_eras": [
            "2.4L V8 Screamer Era (2007–2013)",
            "1.6L V6 Turbo-Hybrid Era (2014–2021)",
            "Ground Effect Venturi Floor Era (2022–2025)",
            "2026 Active Aero & 50/50 Hybrid Era (2026+)"
        ],
        "primary_era_summary": "1.6L V6 Turbo-Hybrid Dominance Era (2014–2021) & 2.4L V8 Era (2007–2013)",
        "championships": [2008, 2014, 2015, 2017, 2018, 2019, 2020],
        "titles_count": 7,
        "starts": 353,
        "wins": 105,
        "podiums": 201,
        "poles": 104,
        "fastest_laps": 67,
        "career_points": 4829.5,
        "teams": [
            {"team": "McLaren", "years": "2007–2012"},
            {"team": "Mercedes", "years": "2013–2024"},
            {"team": "Ferrari", "years": "2025–Present"}
        ],
        "iconic_car": "Mercedes-AMG F1 W11 EQ Performance (2020 all-time track record holder)",
        "landmark_race": {
            "year": 2021,
            "round": 22,
            "race_name": "Abu Dhabi Grand Prix (Yas Marina)",
            "circuit_id": "yas_marina",
            "driver": "HAM",
            "lap": 58,
            "button_text": "EXPLORE 2021 HAMILTON REPLAY"
        },
        "highlights": (
            "All-time record holder for most Grand Prix victories (105), pole positions (104), and podiums (201). "
            "Tied with Michael Schumacher for the record of 7 World Drivers' Championships. Famous for wet-weather mastery, "
            "relentless race pace, and historic championship battles against Alonso, Massa, Rosberg, and Verstappen."
        ),
        "aliases": ["hamilton", "lewis", "lewis hamilton", "ham", "#44", "hamiltonn", "hamiltun"]
    },
    "max_verstappen": {
        "id": "max_verstappen",
        "name": "Max Verstappen",
        "code": "VER",
        "nationality": "Dutch",
        "born": "1997-09-30",
        "active_years": "2015–Present (11+ seasons)",
        "seasons_count": 11,
        "debut": "2015 Australian GP (Toro Rosso, aged 17y 166d)",
        "final_race": "Active (Red Bull Racing)",
        "primary_eras": [
            "1.6L V6 Turbo-Hybrid Era (2015–2021)",
            "Ground Effect Venturi Floor Era (2022–2025)",
            "2026 Active Aero Era (2026+)"
        ],
        "primary_era_summary": "Ground Effect Venturi Floor Era (2022–2025) & Turbo-Hybrid Era (2015–2021)",
        "championships": [2021, 2022, 2023, 2024],
        "titles_count": 4,
        "starts": 206,
        "wins": 64,
        "podiums": 111,
        "poles": 40,
        "fastest_laps": 33,
        "career_points": 3014.5,
        "teams": [
            {"team": "Toro Rosso", "years": "2015–2016"},
            {"team": "Red Bull Racing", "years": "2016–Present"}
        ],
        "iconic_car": "Red Bull RB19 (21 wins from 22 races in 2023, most dominant car in F1 history)",
        "landmark_race": {
            "year": 2021,
            "round": 22,
            "race_name": "Abu Dhabi Grand Prix (Yas Marina)",
            "circuit_id": "yas_marina",
            "driver": "VER",
            "lap": 58,
            "button_text": "EXPLORE 2021 VERSTAPPEN REPLAY"
        },
        "highlights": (
            "Youngest Grand Prix starter (17y 166d) and youngest race winner (18y 228d at 2016 Spanish GP). "
            "Set the all-time record of 10 consecutive Grand Prix wins in 2023 and won 19 of 22 races in a single season. "
            "Clinched 4 consecutive World Championships (2021, 2022, 2023, 2024)."
        ),
        "aliases": ["verstappen", "max", "max verstappen", "ver", "#1", "#33", "versappen", "verstaping"]
    },
    "sebastian_vettel": {
        "id": "vettel",
        "name": "Sebastian Vettel",
        "code": "VET",
        "nationality": "German",
        "born": "1987-07-03",
        "active_years": "2007–2022 (16 seasons)",
        "seasons_count": 16,
        "debut": "2007 US GP (BMW Sauber)",
        "final_race": "2022 Abu Dhabi GP (Aston Martin)",
        "primary_eras": [
            "2.4L V8 Screamer & Blown Diffuser Era (2007–2013)",
            "1.6L V6 Turbo-Hybrid Era (2014–2021)",
            "Ground Effect Era (2022)"
        ],
        "primary_era_summary": "2.4L V8 Screamer & Blown Diffuser Era (2007–2013)",
        "championships": [2010, 2011, 2012, 2013],
        "titles_count": 4,
        "starts": 299,
        "wins": 53,
        "podiums": 122,
        "poles": 57,
        "fastest_laps": 38,
        "career_points": 3098.0,
        "teams": [
            {"team": "BMW Sauber", "years": "2007"},
            {"team": "Toro Rosso", "years": "2007–2008"},
            {"team": "Red Bull Racing", "years": "2009–2014"},
            {"team": "Ferrari", "years": "2015–2020"},
            {"team": "Aston Martin", "years": "2021–2022"}
        ],
        "iconic_car": "Red Bull RB9 (2013, 9 consecutive wins, 13 season wins)",
        "landmark_race": {
            "year": 2011,
            "round": 1,
            "race_name": "Australian Grand Prix (Melbourne)",
            "circuit_id": "albert_park",
            "driver": "VET",
            "lap": 58,
            "button_text": "EXPLORE 2011 VETTEL REPLAY"
        },
        "highlights": (
            "Youngest World Champion in Formula 1 history (23 years, 134 days in 2010). Won 4 consecutive "
            "World Championships with Red Bull (2010–2013). Won 9 consecutive races in 2013 and ranks 4th all-time "
            "with 53 Grand Prix victories."
        ),
        "aliases": ["vettel", "sebastian", "sebastian vettel", "vet", "#5", "vetel"]
    },
    "fernando_alonso": {
        "id": "alonso",
        "name": "Fernando Alonso",
        "code": "ALO",
        "nationality": "Spanish",
        "born": "1981-07-29",
        "active_years": "2001, 2003–2018, 2021–Present (22+ seasons)",
        "seasons_count": 22,
        "debut": "2001 Australian GP (Minardi)",
        "final_race": "Active (Aston Martin)",
        "primary_eras": [
            "3.0L V10 Golden Era (2001, 2003–2005)",
            "2.4L V8 Screamer Era (2006–2013)",
            "1.6L Turbo-Hybrid Era (2014–2018, 2021)",
            "Ground Effect Era (2022–2025)",
            "2026 Active Aero Era (2026+)"
        ],
        "primary_era_summary": "3.0L V10 & 2.4L V8 Eras (2003–2013)",
        "championships": [2005, 2006],
        "titles_count": 2,
        "starts": 401,
        "wins": 32,
        "podiums": 106,
        "poles": 22,
        "fastest_laps": 26,
        "career_points": 2329.0,
        "teams": [
            {"team": "Minardi", "years": "2001"},
            {"team": "Renault", "years": "2003–2006, 2008–2009"},
            {"team": "McLaren", "years": "2007, 2015–2018"},
            {"team": "Ferrari", "years": "2010–2014"},
            {"team": "Alpine", "years": "2021–2022"},
            {"team": "Aston Martin", "years": "2023–Present"}
        ],
        "iconic_car": "Renault R25 (3.0L V10, 2005 championship winner)",
        "landmark_race": {
            "year": 2023,
            "round": 10,
            "race_name": "British Grand Prix (Silverstone)",
            "circuit_id": "silverstone",
            "driver": "ALO",
            "lap": 52,
            "button_text": "EXPLORE 2023 ALONSO REPLAY"
        },
        "highlights": (
            "Dethroned Michael Schumacher in 2005 to become the youngest champion at the time. "
            "All-time record holder for most Grand Prix starts (400+). Won back-to-back championships with Renault (2005, 2006) "
            "and mounted heroic championship challenges with Ferrari in 2010 and 2012."
        ),
        "aliases": ["alonso", "fernando", "fernando alonso", "alo", "#14", "allonso", "alonzo"]
    },
    "kimi_raikkonen": {
        "id": "raikkonen",
        "name": "Kimi Räikkönen",
        "code": "RAI",
        "nationality": "Finnish",
        "born": "1979-10-17",
        "active_years": "2001–2009, 2012–2021 (19 seasons)",
        "seasons_count": 19,
        "debut": "2001 Australian GP (Sauber)",
        "final_race": "2021 Abu Dhabi GP (Alfa Romeo)",
        "primary_eras": [
            "3.0L V10 Golden Era (2001–2005)",
            "2.4L V8 Screamer Era (2006–2009, 2012–2013)",
            "1.6L Turbo-Hybrid Era (2014–2021)"
        ],
        "primary_era_summary": "3.0L V10 (2001–2005) & 2.4L V8 Screamer Era (2006–2009)",
        "championships": [2007],
        "titles_count": 1,
        "starts": 349,
        "wins": 21,
        "podiums": 103,
        "poles": 18,
        "fastest_laps": 46,
        "career_points": 1873.0,
        "teams": [
            {"team": "Sauber", "years": "2001"},
            {"team": "McLaren", "years": "2002–2006"},
            {"team": "Ferrari", "years": "2007–2009, 2014–2018"},
            {"team": "Lotus", "years": "2012–2013"},
            {"team": "Alfa Romeo", "years": "2019–2021"}
        ],
        "iconic_car": "Ferrari F2007 (2007 World Championship winning car)",
        "landmark_race": {
            "year": 2018,
            "round": 1,
            "race_name": "Australian Grand Prix (Melbourne)",
            "circuit_id": "albert_park",
            "driver": "RAI",
            "lap": 58,
            "button_text": "EXPLORE 2018 RAIKKONEN REPLAY"
        },
        "highlights": (
            "Nicknamed 'The Iceman'. Clinched the 2007 World Championship for Ferrari by a single point over Hamilton "
            "and Alonso after winning the season finale in Brazil. Third all-time in fastest laps (46)."
        ),
        "aliases": ["raikkonen", "räikkönen", "kimi", "kimi raikkonen", "rai", "#7", "iceman", "raikonen"]
    },
    "niki_lauda": {
        "id": "lauda",
        "name": "Niki Lauda",
        "code": "LAU",
        "nationality": "Austrian",
        "born": "1949-02-22",
        "active_years": "1971–1979, 1982–1985 (13 seasons)",
        "seasons_count": 13,
        "debut": "1971 Austrian GP (March)",
        "final_race": "1985 Australian GP (McLaren)",
        "primary_eras": [
            "Cosworth DFV & 3.0L Flat-12 Era (1971–1979)",
            "1.5L Turbo Monster Era (1982–1985)"
        ],
        "primary_era_summary": "3.0L Boxer/DFV Era (1974–1979) & Turbo Era (1982–1985)",
        "championships": [1975, 1977, 1984],
        "titles_count": 3,
        "starts": 171,
        "wins": 25,
        "podiums": 54,
        "poles": 24,
        "fastest_laps": 24,
        "career_points": 420.5,
        "teams": [
            {"team": "March", "years": "1971–1972"},
            {"team": "BRM", "years": "1973"},
            {"team": "Ferrari", "years": "1974–1977"},
            {"team": "Brabham", "years": "1978–1979"},
            {"team": "McLaren", "years": "1982–1985"}
        ],
        "iconic_car": "Ferrari 312T (1975) & McLaren MP4/2 TAG-Porsche (1984)",
        "landmark_race": {
            "year": 1976,
            "round": 16,
            "race_name": "Japanese Grand Prix (Fuji Speedway)",
            "circuit_id": "fuji",
            "driver": "LAU",
            "lap": 2,
            "button_text": "EXPLORE 1976 LAUDA REPLAY"
        },
        "highlights": (
            "Survived a catastrophic fiery crash at the Nürburgring Nordschleife in 1976, returning just 6 weeks later at Monza. "
            "Won two titles with Ferrari (1975, 1977) and returned from retirement to win the 1984 title with McLaren by 0.5 points."
        ),
        "aliases": ["lauda", "niki", "niki lauda", "lau", "louda", "nicky lauda"]
    },
    "juan_manuel_fangio": {
        "id": "fangio",
        "name": "Juan Manuel Fangio",
        "code": "FAN",
        "nationality": "Argentine",
        "born": "1911-06-24",
        "active_years": "1950–1951, 1953–1958 (8 seasons)",
        "seasons_count": 8,
        "debut": "1950 British GP (Alfa Romeo)",
        "final_race": "1958 French GP (Maserati)",
        "primary_eras": [
            "1950s Front-Engine Birth Era (1950–1958)"
        ],
        "primary_era_summary": "1950s Front-Engine Birth Era (1950–1958)",
        "championships": [1951, 1954, 1955, 1956, 1957],
        "titles_count": 5,
        "starts": 51,
        "wins": 24,
        "podiums": 35,
        "poles": 29,
        "fastest_laps": 23,
        "career_points": 277.6,
        "teams": [
            {"team": "Alfa Romeo", "years": "1950–1951"},
            {"team": "Maserati", "years": "1953–1954, 1957–1958"},
            {"team": "Mercedes-Benz", "years": "1954–1955"},
            {"team": "Ferrari", "years": "1956"}
        ],
        "iconic_car": "Maserati 250F & Mercedes W196 Streamliner",
        "landmark_race": {
            "year": 1956,
            "round": 1,
            "race_name": "Argentine Grand Prix (Buenos Aires)",
            "circuit_id": "buenos_aires",
            "driver": "FAN",
            "lap": 98,
            "button_text": "EXPLORE 1956 FANGIO REPLAY"
        },
        "highlights": (
            "Nicknamed 'El Maestro'. Won 5 World Championships across 4 different manufacturers (Alfa Romeo, Maserati, "
            "Mercedes, Ferrari) — a record that still stands today. Holds the highest win percentage in F1 history (46.15%)."
        ),
        "aliases": ["fangio", "juan manuel fangio", "el maestro", "fangyo", "fango"]
    },
    "mika_hakkinen": {
        "id": "hakkinen",
        "name": "Mika Häkkinen",
        "code": "HAK",
        "nationality": "Finnish",
        "born": "1968-09-28",
        "active_years": "1991–2001 (11 seasons)",
        "seasons_count": 11,
        "debut": "1991 US GP (Lotus)",
        "final_race": "2001 Japanese GP (McLaren)",
        "primary_eras": [
            "3.5L Era (1991–1994)",
            "3.0L V10 Golden Era (1995–2001)"
        ],
        "primary_era_summary": "3.0L V10 Golden Era (1995–2001)",
        "championships": [1998, 1999],
        "titles_count": 2,
        "starts": 161,
        "wins": 20,
        "podiums": 51,
        "poles": 26,
        "fastest_laps": 25,
        "career_points": 420.0,
        "teams": [
            {"team": "Lotus", "years": "1991–1992"},
            {"team": "McLaren", "years": "1993–2001"}
        ],
        "iconic_car": "McLaren MP4/13 (Mercedes 3.0L V10, 1998 championship winner)",
        "landmark_race": {
            "year": 1998,
            "round": 16,
            "race_name": "Japanese Grand Prix (Suzuka)",
            "circuit_id": "suzuka",
            "driver": "HAK",
            "lap": 51,
            "button_text": "EXPLORE 1998 HAKKINEN REPLAY"
        },
        "highlights": (
            "Nicknamed 'The Flying Finn'. Michael Schumacher cited Häkkinen as the rival he respected and feared most. "
            "Famous for his legendary 300+ km/h overtake on Schumacher at Spa 2000 through Ricardo Zonta."
        ),
        "aliases": ["hakkinen", "häkkinen", "mika", "mika hakkinen", "hak", "the flying finn", "hakinen"]
    },
    "jim_clark": {
        "id": "clark",
        "name": "Jim Clark",
        "code": "CLA",
        "nationality": "British (Scottish)",
        "born": "1936-03-04",
        "active_years": "1960–1968 (9 seasons)",
        "seasons_count": 9,
        "debut": "1960 Dutch GP (Lotus)",
        "final_race": "1968 South African GP (Lotus)",
        "primary_eras": ["1960s 1.5L & 3.0L DFV Era (1960–1968)"],
        "primary_era_summary": "1960s Classic DFV Monocoque Era",
        "championships": [1963, 1965],
        "titles_count": 2,
        "starts": 72,
        "wins": 25,
        "podiums": 32,
        "poles": 33,
        "fastest_laps": 28,
        "career_points": 274.0,
        "teams": [{"team": "Lotus", "years": "1960–1968"}],
        "iconic_car": "Lotus 25 & Lotus 49 (Cosworth DFV)",
        "landmark_race": {
            "year": 1968,
            "round": 1,
            "race_name": "South African Grand Prix (Kyalami)",
            "circuit_id": "kyalami",
            "driver": "CLA",
            "lap": 80,
            "button_text": "EXPLORE 1968 CLARK REPLAY"
        },
        "highlights": (
            "Widely considered one of the purest driving talents in motorsport history. Won the 1963 and 1965 World Championships "
            "and also won the Indianapolis 500 in 1965. Holds the record for 8 'Grand Chelems' (pole, win, fastest lap, led every lap)."
        ),
        "aliases": ["clark", "jim clark", "jimmy clark"]
    },
    "jackie_stewart": {
        "id": "stewart",
        "name": "Sir Jackie Stewart",
        "code": "STE",
        "nationality": "British (Scottish)",
        "born": "1939-06-11",
        "active_years": "1965–1973 (9 seasons)",
        "seasons_count": 9,
        "debut": "1965 South African GP (BRM)",
        "final_race": "1973 Italian GP (Tyrrell)",
        "primary_eras": ["1960s–1970s Cosworth DFV Era"],
        "primary_era_summary": "Late 1960s & Early 1970s Tyrrell-Cosworth Era",
        "championships": [1969, 1971, 1973],
        "titles_count": 3,
        "starts": 99,
        "wins": 27,
        "podiums": 43,
        "poles": 17,
        "fastest_laps": 15,
        "career_points": 360.0,
        "teams": [
            {"team": "BRM", "years": "1965–1967"},
            {"team": "Matra", "years": "1968–1969"},
            {"team": "March", "years": "1970"},
            {"team": "Tyrrell", "years": "1970–1973"}
        ],
        "iconic_car": "Tyrrell 003 (Ford Cosworth DFV)",
        "landmark_race": {
            "year": 1971,
            "round": 1,
            "race_name": "South African Grand Prix (Kyalami)",
            "circuit_id": "kyalami",
            "driver": "STE",
            "lap": 79,
            "button_text": "EXPLORE 1971 STEWART REPLAY"
        },
        "highlights": (
            "Triple World Champion (1969, 1971, 1973). Pioneered modern motorsport safety protocols, demanding mandatory "
            "seatbelts, full-face helmets, barrier protection, and on-track medical teams. Won 27 of 99 races."
        ),
        "aliases": ["stewart", "jackie stewart", "sir jackie stewart"]
    },
    "nelson_piquet": {
        "id": "piquet",
        "name": "Nelson Piquet",
        "code": "PIQ",
        "nationality": "Brazilian",
        "born": "1952-08-17",
        "active_years": "1978–1991 (14 seasons)",
        "seasons_count": 14,
        "debut": "1978 German GP (Ensign)",
        "final_race": "1991 Australian GP (Benetton)",
        "primary_eras": ["Ground Effect & 1.5L Turbo Monster Era (1978–1988)"],
        "primary_era_summary": "Ground Effect & Turbo Era (1981–1987)",
        "championships": [1981, 1983, 1987],
        "titles_count": 3,
        "starts": 204,
        "wins": 23,
        "podiums": 60,
        "poles": 24,
        "fastest_laps": 23,
        "career_points": 485.5,
        "teams": [
            {"team": "Brabham", "years": "1978–1985"},
            {"team": "Williams", "years": "1986–1987"},
            {"team": "Lotus", "years": "1988–1989"},
            {"team": "Benetton", "years": "1990–1991"}
        ],
        "iconic_car": "Brabham BT52 (BMW Turbo, 1983) & Williams FW11B (Honda Turbo, 1987)",
        "landmark_race": {
            "year": 1988,
            "round": 12,
            "race_name": "Italian Grand Prix (Monza)",
            "circuit_id": "monza",
            "driver": "PIQ",
            "lap": 51,
            "button_text": "EXPLORE 1988 PIQUET REPLAY"
        },
        "highlights": (
            "First driver to win a World Championship with turbocharged power (Brabham BMW in 1983). "
            "Won three World Championships (1981, 1983, 1987) during an intensely competitive era featuring Prost, Senna, and Mansell."
        ),
        "aliases": ["piquet", "nelson", "nelson piquet", "piquete"]
    },
    "nigel_mansell": {
        "id": "mansell",
        "name": "Nigel Mansell",
        "code": "MAN",
        "nationality": "British",
        "born": "1953-08-08",
        "active_years": "1980–1992, 1994–1995 (15 seasons)",
        "seasons_count": 15,
        "debut": "1980 Austrian GP (Lotus)",
        "final_race": "1995 Spanish GP (McLaren)",
        "primary_eras": ["1.5L Turbo Era & 3.5L Active Suspension Era"],
        "primary_era_summary": "Turbo Monster Era (1985–1988) & 3.5L Williams Tech Era (1991–1992)",
        "championships": [1992],
        "titles_count": 1,
        "starts": 187,
        "wins": 31,
        "podiums": 59,
        "poles": 32,
        "fastest_laps": 30,
        "career_points": 482.0,
        "teams": [
            {"team": "Lotus", "years": "1980–1984"},
            {"team": "Williams", "years": "1985–1988, 1991–1992, 1994"},
            {"team": "Ferrari", "years": "1989–1990"},
            {"team": "McLaren", "years": "1995"}
        ],
        "iconic_car": "Williams FW14B ('Red 5', active suspension, 1992 champion)",
        "landmark_race": {
            "year": 1988,
            "round": 12,
            "race_name": "Italian Grand Prix (Monza)",
            "circuit_id": "monza",
            "driver": "MAN",
            "lap": 15,
            "button_text": "EXPLORE 1988 MANSELL REPLAY"
        },
        "highlights": (
            "Nicknamed 'Il Leone' (The Lion) by Ferrari tifosi for aggressive wheel-to-wheel tenacity. "
            "Dominated the 1992 season with Williams FW14B, winning 9 races and clinching the title by Hungary in August. "
            "Only driver in history to hold both the F1 World Championship and IndyCar title simultaneously."
        ),
        "aliases": ["mansell", "nigel", "nigel mansell", "red 5", "il leone"]
    },
    "damon_hill": {
        "id": "damon_hill",
        "name": "Damon Hill",
        "code": "HIL",
        "nationality": "British",
        "born": "1960-09-17",
        "active_years": "1992–1999 (8 seasons)",
        "seasons_count": 8,
        "debut": "1992 British GP (Brabham)",
        "final_race": "1999 Japanese GP (Jordan)",
        "primary_eras": ["3.5L Naturally Aspirated Era (1992–1994)", "3.0L V10 Era (1995–1999)"],
        "primary_era_summary": "1990s Williams-Renault V10 Era",
        "championships": [1996],
        "titles_count": 1,
        "starts": 115,
        "wins": 22,
        "podiums": 42,
        "poles": 20,
        "fastest_laps": 19,
        "career_points": 360.0,
        "teams": [
            {"team": "Brabham", "years": "1992"},
            {"team": "Williams", "years": "1993–1996"},
            {"team": "Arrows", "years": "1997"},
            {"team": "Jordan", "years": "1998–1999"}
        ],
        "iconic_car": "Williams FW18 (Renault V10, 1996 champion)",
        "landmark_race": {
            "year": 1998,
            "round": 13,
            "race_name": "Belgian Grand Prix (Spa-Francorchamps)",
            "circuit_id": "spa",
            "driver": "HIL",
            "lap": 44,
            "button_text": "EXPLORE 1998 HILL REPLAY"
        },
        "highlights": (
            "Son of two-time champion Graham Hill, making them the first father-son World Champions. "
            "Won the 1996 World Championship with Williams-Renault and led Jordan Grand Prix to their historic maiden 1-2 victory at Spa 1998."
        ),
        "aliases": ["damon hill", "hill", "damon"]
    },
    "jenson_button": {
        "id": "jenson_button",
        "name": "Jenson Button",
        "code": "BUT",
        "nationality": "British",
        "born": "1980-01-19",
        "active_years": "2000–2017 (18 seasons)",
        "seasons_count": 18,
        "debut": "2000 Australian GP (Williams)",
        "final_race": "2017 Monaco GP (McLaren)",
        "primary_eras": ["3.0L V10 Era (2000–2005)", "2.4L V8 Screamer Era (2006–2013)", "1.6L Turbo Hybrid (2014–2017)"],
        "primary_era_summary": "2.4L V8 Screamer & Brawn GP Era (2006–2013)",
        "championships": [2009],
        "titles_count": 1,
        "starts": 306,
        "wins": 15,
        "podiums": 50,
        "poles": 8,
        "fastest_laps": 8,
        "career_points": 1235.0,
        "teams": [
            {"team": "Williams", "years": "2000"},
            {"team": "Benetton/Renault", "years": "2001–2002"},
            {"team": "BAR/Honda", "years": "2003–2008"},
            {"team": "Brawn GP", "years": "2009"},
            {"team": "McLaren", "years": "2010–2017"}
        ],
        "iconic_car": "Brawn BGP 001 (Mercedes V8, double diffuser, 2009 champion)",
        "landmark_race": {
            "year": 2011,
            "round": 7,
            "race_name": "Canadian Grand Prix (Montreal)",
            "circuit_id": "villeneuve",
            "driver": "BUT",
            "lap": 70,
            "button_text": "EXPLORE 2011 BUTTON REPLAY"
        },
        "highlights": (
            "Master of mixed and wet conditions with supreme tyre management. Clinched the fairy-tale 2009 World Championship "
            "with Brawn GP. Won the longest race in F1 history (Canada 2011) after 6 pit stops and a last-lap pass on Sebastian Vettel."
        ),
        "aliases": ["jenson button", "button", "jenson"]
    },
    "charles_leclerc": {
        "id": "charles_leclerc",
        "name": "Charles Leclerc",
        "code": "LEC",
        "nationality": "Monegasque",
        "born": "1997-10-16",
        "active_years": "2018–Present (9 seasons)",
        "seasons_count": 9,
        "debut": "2018 Australian GP (Sauber)",
        "final_race": "Active (Ferrari)",
        "primary_eras": ["1.6L V6 Turbo Hybrid Era (2018–Present)", "2022+ Ground Effect Era"],
        "primary_era_summary": "Modern Ground Effect & Hybrid Era (Ferrari)",
        "championships": [],
        "titles_count": 0,
        "starts": 146,
        "wins": 8,
        "podiums": 43,
        "poles": 26,
        "fastest_laps": 10,
        "career_points": 1390.0,
        "teams": [
            {"team": "Sauber", "years": "2018"},
            {"team": "Ferrari", "years": "2019–Present"}
        ],
        "iconic_car": "Ferrari SF-24 / F1-75",
        "landmark_race": {
            "year": 2024,
            "round": 8,
            "race_name": "Monaco Grand Prix (Monte Carlo)",
            "circuit_id": "monaco",
            "driver": "LEC",
            "lap": 78,
            "button_text": "EXPLORE 2024 LECLERC REPLAY"
        },
        "highlights": (
            "Regarded as the fastest one-lap qualifying driver of his generation (26 poles). Emotional home victory at the 2024 Monaco GP "
            "and Monza 2019/2024 victories for Ferrari."
        ),
        "aliases": ["charles leclerc", "leclerc", "charles", "lec", "#16"]
    },
    "lando_norris": {
        "id": "lando_norris",
        "name": "Lando Norris",
        "code": "NOR",
        "nationality": "British",
        "born": "1999-11-13",
        "active_years": "2019–Present (8 seasons)",
        "seasons_count": 8,
        "debut": "2019 Australian GP (McLaren)",
        "final_race": "Active (McLaren)",
        "primary_eras": ["1.6L V6 Turbo Hybrid Era (2019–Present)", "2022+ Ground Effect Era"],
        "primary_era_summary": "McLaren Ground Effect Resurgence (2022–2026)",
        "championships": [],
        "titles_count": 0,
        "starts": 128,
        "wins": 4,
        "podiums": 28,
        "poles": 8,
        "fastest_laps": 12,
        "career_points": 990.0,
        "teams": [
            {"team": "McLaren", "years": "2019–Present"}
        ],
        "iconic_car": "McLaren MCL38 (2024 Constructors' Champion)",
        "landmark_race": {
            "year": 2024,
            "round": 6,
            "race_name": "Miami Grand Prix",
            "circuit_id": "miami",
            "driver": "NOR",
            "lap": 57,
            "button_text": "EXPLORE 2024 NORRIS REPLAY"
        },
        "highlights": (
            "Leader of McLaren's modern renaissance, scoring maiden victory at Miami 2024 and spearheading McLaren's fight "
            "for the 2024 World Constructors' Championship."
        ),
        "aliases": ["lando norris", "norris", "lando", "nor", "#4"]
    },
    "daniel_ricciardo": {
        "id": "daniel_ricciardo",
        "name": "Daniel Ricciardo",
        "code": "RIC",
        "nationality": "Australian",
        "born": "1989-07-01",
        "active_years": "2011–2024 (14 seasons)",
        "seasons_count": 14,
        "debut": "2011 British GP (HRT)",
        "final_race": "2024 Singapore GP (RB)",
        "primary_eras": ["2.4L V8 Screamer Era (2011–2013)", "1.6L V6 Turbo Hybrid Era (2014–2024)"],
        "primary_era_summary": "Red Bull Racing Turbo Hybrid Era (2014–2018)",
        "championships": [],
        "titles_count": 0,
        "starts": 257,
        "wins": 8,
        "podiums": 32,
        "poles": 3,
        "fastest_laps": 17,
        "career_points": 1329.0,
        "teams": [
            {"team": "HRT", "years": "2011"},
            {"team": "Toro Rosso", "years": "2012–2013"},
            {"team": "Red Bull", "years": "2014–2018"},
            {"team": "Renault", "years": "2019–2020"},
            {"team": "McLaren", "years": "2021–2022"},
            {"team": "AlphaTauri/RB", "years": "2023–2024"}
        ],
        "iconic_car": "Red Bull RB10 / McLaren MCL35M",
        "landmark_race": {
            "year": 2018,
            "round": 6,
            "race_name": "Monaco Grand Prix",
            "circuit_id": "monaco",
            "driver": "RIC",
            "lap": 78,
            "button_text": "EXPLORE 2018 RICCIARDO REPLAY"
        },
        "highlights": (
            "Known as 'The Honey Badger' for legendary late-braking divebomb overtakes. Won 7 races with Red Bull including Monaco 2018 "
            "with a crippled MGU-K, and delivered McLaren's first win in nine years at Monza 2021."
        ),
        "aliases": ["daniel ricciardo", "ricciardo", "daniel", "ric", "honey badger", "#3"]
    }
}

# Add common name mappings for fuzzy search
DRIVER_NAME_LOOKUP: Dict[str, str] = {}
for did, profile in HISTORICAL_DRIVERS.items():
    DRIVER_NAME_LOOKUP[did] = did
    DRIVER_NAME_LOOKUP[profile["name"].lower()] = did
    for alias in profile.get("aliases", []):
        DRIVER_NAME_LOOKUP[alias.lower()] = did


# =============================================================================
# 2. F1 REGULATORY & TECHNICAL ERAS (1950–2026+)
# =============================================================================

# Eras live in content/eras/*.md (figures in front matter; analysis in the body).
HISTORICAL_ERAS: Dict[str, Dict[str, Any]] = _content.eras()
ERA_SEARCH_MIN_SCORE = 0.45  # below this, a generic era question gets the V10 overview


# =============================================================================
# 3. ALL-TIME F1 RECORDS & LEADERBOARDS
# =============================================================================

ALL_TIME_RECORDS: Dict[str, Dict[str, Any]] = {
    "championships": {
        "title": "Most Formula 1 World Drivers' Championships",
        "metric_label": "World Titles",
        "leaders": [
            {"name": "Michael Schumacher", "value": "7 Titles (1994, 1995, 2000, 2001, 2002, 2003, 2004)", "color": "#FFB703"},
            {"name": "Lewis Hamilton", "value": "7 Titles (2008, 2014, 2015, 2017, 2018, 2019, 2020)", "color": "#00F5D4"},
            {"name": "Juan Manuel Fangio", "value": "5 Titles (1951, 1954, 1955, 1956, 1957)", "color": "#FFFFFF"},
            {"name": "Alain Prost", "value": "4 Titles (1985, 1986, 1989, 1993)", "color": "#E10600"},
            {"name": "Sebastian Vettel", "value": "4 Titles (2010, 2011, 2012, 2013)", "color": "#3B82F6"},
            {"name": "Max Verstappen", "value": "4 Titles (2021, 2022, 2023, 2024)", "color": "#F59E0B"}
        ]
    },
    "wins": {
        "title": "Most Formula 1 Grand Prix Victories",
        "metric_label": "Career Wins",
        "leaders": [
            {"name": "Lewis Hamilton", "value": "105 Wins (201 Podiums)", "color": "#00F5D4"},
            {"name": "Michael Schumacher", "value": "91 Wins (155 Podiums)", "color": "#FFB703"},
            {"name": "Max Verstappen", "value": "64 Wins (111 Podiums)", "color": "#F59E0B"},
            {"name": "Sebastian Vettel", "value": "53 Wins (122 Podiums)", "color": "#3B82F6"},
            {"name": "Alain Prost", "value": "51 Wins (106 Podiums)", "color": "#E10600"},
            {"name": "Ayrton Senna", "value": "41 Wins (80 Podiums)", "color": "#10B981"},
            {"name": "Fernando Alonso", "value": "32 Wins (106 Podiums)", "color": "#06B6D4"},
            {"name": "Nigel Mansell", "value": "31 Wins (59 Podiums)", "color": "#A855F7"}
        ]
    },
    "poles": {
        "title": "Most Formula 1 Pole Positions",
        "metric_label": "Career Poles",
        "leaders": [
            {"name": "Lewis Hamilton", "value": "104 Pole Positions", "color": "#00F5D4"},
            {"name": "Michael Schumacher", "value": "68 Pole Positions", "color": "#FFB703"},
            {"name": "Ayrton Senna", "value": "65 Pole Positions", "color": "#10B981"},
            {"name": "Sebastian Vettel", "value": "57 Pole Positions", "color": "#3B82F6"},
            {"name": "Max Verstappen", "value": "40 Pole Positions", "color": "#F59E0B"},
            {"name": "Jim Clark", "value": "33 Pole Positions", "color": "#FFFFFF"},
            {"name": "Alain Prost", "value": "33 Pole Positions", "color": "#E10600"}
        ]
    },
    "constructors": {
        "title": "Most Formula 1 Constructors' Championships",
        "metric_label": "Constructors' Titles",
        "leaders": [
            {"name": "Scuderia Ferrari", "value": "16 WCC Titles (1961–2008)", "color": "#E80020"},
            {"name": "McLaren", "value": "10 WCC Titles (1974–2025)", "color": "#FF8000"},
            {"name": "Williams Racing", "value": "9 WCC Titles (1980–1997)", "color": "#005AFF"},
            {"name": "Mercedes-AMG", "value": "8 WCC Titles (2014–2021)", "color": "#27F4D2"},
            {"name": "Team Lotus", "value": "7 WCC Titles (1963–1978)", "color": "#FFB703"},
            {"name": "Red Bull Racing", "value": "6 WCC Titles (2010–2023)", "color": "#3671C6"}
        ]
    },
    "youngest_champion": {
        "title": "Youngest Formula 1 World Champions",
        "metric_label": "Age at Clinch",
        "leaders": [
            {"name": "Sebastian Vettel", "value": "23y 134d (2010 Abu Dhabi GP)", "color": "#FFB703"},
            {"name": "Lewis Hamilton", "value": "23y 300d (2008 Brazilian GP)", "color": "#00F5D4"},
            {"name": "Fernando Alonso", "value": "24y 58d (2005 Brazilian GP)", "color": "#06B6D4"},
            {"name": "Max Verstappen", "value": "24y 73d (2021 Abu Dhabi GP)", "color": "#F59E0B"},
            {"name": "Emerson Fittipaldi", "value": "25y 273d (1972 Italian GP)", "color": "#10B981"}
        ]
    }
}


# =============================================================================
# 4. WORLD CHAMPIONS BY YEAR ROSTER (1950–2025)
# =============================================================================

WORLD_CHAMPIONS_BY_YEAR: Dict[int, Dict[str, Any]] = {
    1950: {"driver": "Giuseppe Farina", "team": "Alfa Romeo", "runner_up": "Juan Manuel Fangio", "wins": 3, "points": 30.0},
    1951: {"driver": "Juan Manuel Fangio", "team": "Alfa Romeo", "runner_up": "Alberto Ascari", "wins": 3, "points": 31.0},
    1952: {"driver": "Alberto Ascari", "team": "Ferrari", "runner_up": "Nino Farina", "wins": 6, "points": 36.0},
    1953: {"driver": "Alberto Ascari", "team": "Ferrari", "runner_up": "Juan Manuel Fangio", "wins": 5, "points": 34.5},
    1954: {"driver": "Juan Manuel Fangio", "team": "Maserati / Mercedes", "runner_up": "José Froilán González", "wins": 6, "points": 42.0},
    1955: {"driver": "Juan Manuel Fangio", "team": "Mercedes-Benz", "runner_up": "Stirling Moss", "wins": 4, "points": 40.0},
    1956: {"driver": "Juan Manuel Fangio", "team": "Ferrari", "runner_up": "Stirling Moss", "wins": 3, "points": 30.0},
    1957: {"driver": "Juan Manuel Fangio", "team": "Maserati", "runner_up": "Stirling Moss", "wins": 4, "points": 40.0},
    1958: {"driver": "Mike Hawthorn", "team": "Ferrari", "runner_up": "Stirling Moss", "wins": 1, "points": 42.0},
    1959: {"driver": "Jack Brabham", "team": "Cooper-Climax", "runner_up": "Tony Brooks", "wins": 2, "points": 31.0},
    1960: {"driver": "Jack Brabham", "team": "Cooper-Climax", "runner_up": "Bruce McLaren", "wins": 5, "points": 43.0},
    1961: {"driver": "Phil Hill", "team": "Ferrari", "runner_up": "Wolfgang von Trips", "wins": 2, "points": 34.0},
    1962: {"driver": "Graham Hill", "team": "BRM", "runner_up": "Jim Clark", "wins": 4, "points": 42.0},
    1963: {"driver": "Jim Clark", "team": "Lotus-Climax", "runner_up": "Graham Hill", "wins": 7, "points": 54.0},
    1964: {"driver": "John Surtees", "team": "Ferrari", "runner_up": "Graham Hill", "wins": 2, "points": 40.0},
    1965: {"driver": "Jim Clark", "team": "Lotus-Climax", "runner_up": "Graham Hill", "wins": 6, "points": 54.0},
    1966: {"driver": "Jack Brabham", "team": "Brabham-Repco", "runner_up": "John Surtees", "wins": 4, "points": 42.0},
    1967: {"driver": "Denny Hulme", "team": "Brabham-Repco", "runner_up": "Jack Brabham", "wins": 2, "points": 51.0},
    1968: {"driver": "Graham Hill", "team": "Lotus-Ford", "runner_up": "Jackie Stewart", "wins": 3, "points": 48.0},
    1969: {"driver": "Jackie Stewart", "team": "Matra-Ford", "runner_up": "Jacky Ickx", "wins": 6, "points": 63.0},
    1970: {"driver": "Jochen Rindt", "team": "Lotus-Ford", "runner_up": "Jacky Ickx", "wins": 5, "points": 45.0},
    1971: {"driver": "Jackie Stewart", "team": "Tyrrell-Ford", "runner_up": "Ronnie Peterson", "wins": 6, "points": 62.0},
    1972: {"driver": "Emerson Fittipaldi", "team": "Lotus-Ford", "runner_up": "Jackie Stewart", "wins": 5, "points": 61.0},
    1973: {"driver": "Jackie Stewart", "team": "Tyrrell-Ford", "runner_up": "Emerson Fittipaldi", "wins": 5, "points": 71.0},
    1974: {"driver": "Emerson Fittipaldi", "team": "McLaren-Ford", "runner_up": "Clay Regazzoni", "wins": 3, "points": 55.0},
    1975: {"driver": "Niki Lauda", "team": "Ferrari", "runner_up": "Emerson Fittipaldi", "wins": 5, "points": 64.5},
    1976: {"driver": "James Hunt", "team": "McLaren-Ford", "runner_up": "Niki Lauda", "wins": 6, "points": 69.0},
    1977: {"driver": "Niki Lauda", "team": "Ferrari", "runner_up": "Jody Scheckter", "wins": 3, "points": 72.0},
    1978: {"driver": "Mario Andretti", "team": "Lotus-Ford", "runner_up": "Ronnie Peterson", "wins": 6, "points": 64.0},
    1979: {"driver": "Jody Scheckter", "team": "Ferrari", "runner_up": "Gilles Villeneuve", "wins": 3, "points": 51.0},
    1980: {"driver": "Alan Jones", "team": "Williams-Ford", "runner_up": "Nelson Piquet", "wins": 5, "points": 67.0},
    1981: {"driver": "Nelson Piquet", "team": "Brabham-Ford", "runner_up": "Carlos Reutemann", "wins": 3, "points": 50.0},
    1982: {"driver": "Keke Rosberg", "team": "Williams-Ford", "runner_up": "Didier Pironi", "wins": 1, "points": 44.0},
    1983: {"driver": "Nelson Piquet", "team": "Brabham-BMW", "runner_up": "Alain Prost", "wins": 3, "points": 59.0},
    1984: {"driver": "Niki Lauda", "team": "McLaren-TAG", "runner_up": "Alain Prost", "wins": 5, "points": 72.0},
    1985: {"driver": "Alain Prost", "team": "McLaren-TAG", "runner_up": "Michele Alboreto", "wins": 5, "points": 73.0},
    1986: {"driver": "Alain Prost", "team": "McLaren-TAG", "runner_up": "Nigel Mansell", "wins": 4, "points": 72.0},
    1987: {"driver": "Nelson Piquet", "team": "Williams-Honda", "runner_up": "Nigel Mansell", "wins": 3, "points": 73.0},
    1988: {"driver": "Ayrton Senna", "team": "McLaren-Honda", "runner_up": "Alain Prost", "wins": 8, "points": 90.0},
    1989: {"driver": "Alain Prost", "team": "McLaren-Honda", "runner_up": "Ayrton Senna", "wins": 4, "points": 76.0},
    1990: {"driver": "Ayrton Senna", "team": "McLaren-Honda", "runner_up": "Alain Prost", "wins": 6, "points": 78.0},
    1991: {"driver": "Ayrton Senna", "team": "McLaren-Honda", "runner_up": "Nigel Mansell", "wins": 7, "points": 96.0},
    1992: {"driver": "Nigel Mansell", "team": "Williams-Renault", "runner_up": "Riccardo Patrese", "wins": 9, "points": 108.0},
    1993: {"driver": "Alain Prost", "team": "Williams-Renault", "runner_up": "Ayrton Senna", "wins": 7, "points": 99.0},
    1994: {"driver": "Michael Schumacher", "team": "Benetton-Ford", "runner_up": "Damon Hill", "wins": 8, "points": 92.0},
    1995: {"driver": "Michael Schumacher", "team": "Benetton-Renault", "runner_up": "Damon Hill", "wins": 9, "points": 102.0},
    1996: {"driver": "Damon Hill", "team": "Williams-Renault", "runner_up": "Jacques Villeneuve", "wins": 8, "points": 97.0},
    1997: {"driver": "Jacques Villeneuve", "team": "Williams-Renault", "runner_up": "Heinz-Harald Frentzen", "wins": 7, "points": 81.0},
    1998: {"driver": "Mika Häkkinen", "team": "McLaren-Mercedes", "runner_up": "Michael Schumacher", "wins": 8, "points": 100.0},
    1999: {"driver": "Mika Häkkinen", "team": "McLaren-Mercedes", "runner_up": "Eddie Irvine", "wins": 5, "points": 76.0},
    2000: {"driver": "Michael Schumacher", "team": "Ferrari", "runner_up": "Mika Häkkinen", "wins": 9, "points": 108.0},
    2001: {"driver": "Michael Schumacher", "team": "Ferrari", "runner_up": "David Coulthard", "wins": 9, "points": 123.0},
    2002: {"driver": "Michael Schumacher", "team": "Ferrari", "runner_up": "Rubens Barrichello", "wins": 11, "points": 144.0},
    2003: {"driver": "Michael Schumacher", "team": "Ferrari", "runner_up": "Kimi Räikkönen", "wins": 6, "points": 93.0},
    2004: {"driver": "Michael Schumacher", "team": "Ferrari", "runner_up": "Rubens Barrichello", "wins": 13, "points": 148.0},
    2005: {"driver": "Fernando Alonso", "team": "Renault", "runner_up": "Kimi Räikkönen", "wins": 7, "points": 133.0},
    2006: {"driver": "Fernando Alonso", "team": "Renault", "runner_up": "Michael Schumacher", "wins": 7, "points": 134.0},
    2007: {"driver": "Kimi Räikkönen", "team": "Ferrari", "runner_up": "Lewis Hamilton", "wins": 6, "points": 110.0},
    2008: {"driver": "Lewis Hamilton", "team": "McLaren-Mercedes", "runner_up": "Felipe Massa", "wins": 5, "points": 98.0},
    2009: {"driver": "Jenson Button", "team": "Brawn-Mercedes", "runner_up": "Sebastian Vettel", "wins": 6, "points": 95.0},
    2010: {"driver": "Sebastian Vettel", "team": "Red Bull-Renault", "runner_up": "Fernando Alonso", "wins": 5, "points": 256.0},
    2011: {"driver": "Sebastian Vettel", "team": "Red Bull-Renault", "runner_up": "Jenson Button", "wins": 11, "points": 392.0},
    2012: {"driver": "Sebastian Vettel", "team": "Red Bull-Renault", "runner_up": "Fernando Alonso", "wins": 5, "points": 281.0},
    2013: {"driver": "Sebastian Vettel", "team": "Red Bull-Renault", "runner_up": "Fernando Alonso", "wins": 13, "points": 397.0},
    2014: {"driver": "Lewis Hamilton", "team": "Mercedes", "runner_up": "Nico Rosberg", "wins": 11, "points": 384.0},
    2015: {"driver": "Lewis Hamilton", "team": "Mercedes", "runner_up": "Nico Rosberg", "wins": 10, "points": 381.0},
    2016: {"driver": "Nico Rosberg", "team": "Mercedes", "runner_up": "Lewis Hamilton", "wins": 9, "points": 385.0},
    2017: {"driver": "Lewis Hamilton", "team": "Mercedes", "runner_up": "Sebastian Vettel", "wins": 9, "points": 363.0},
    2018: {"driver": "Lewis Hamilton", "team": "Mercedes", "runner_up": "Sebastian Vettel", "wins": 11, "points": 408.0},
    2019: {"driver": "Lewis Hamilton", "team": "Mercedes", "runner_up": "Valtteri Bottas", "wins": 11, "points": 413.0},
    2020: {"driver": "Lewis Hamilton", "team": "Mercedes", "runner_up": "Valtteri Bottas", "wins": 11, "points": 347.0},
    2021: {"driver": "Max Verstappen", "team": "Red Bull-Honda", "runner_up": "Lewis Hamilton", "wins": 10, "points": 395.5},
    2022: {"driver": "Max Verstappen", "team": "Red Bull-RBPT", "runner_up": "Charles Leclerc", "wins": 15, "points": 454.0},
    2023: {"driver": "Max Verstappen", "team": "Red Bull-Honda RBPT", "runner_up": "Sergio Pérez", "wins": 19, "points": 575.0},
    2024: {"driver": "Max Verstappen", "team": "Red Bull-Honda RBPT", "runner_up": "Lando Norris", "wins": 9, "points": 437.0},
    2025: {"driver": "Lando Norris", "team": "McLaren-Mercedes", "runner_up": "Max Verstappen", "wins": 7, "points": 423.0}
}


# =============================================================================
# 5. FUZZY DRIVER RESOLUTION & RESEARCH ENGINE
# =============================================================================

@functools.lru_cache(maxsize=1)
def _english_words() -> frozenset:
    """Whole words in the router model's WordPiece vocabulary (about 20,000 common English
    words), or a short list of question verbs when the model isn't downloaded."""
    try:
        from app.agent.embedding import MODEL_DIR, WordPiece
        vocab = WordPiece.from_tokenizer_json(os.path.join(MODEL_DIR, "tokenizer.json")).vocab
        return frozenset(w for w in vocab if w.isalpha() and not w.startswith("##"))
    except (OSError, ValueError):
        return frozenset({"started", "starting", "finished", "finishing", "stopped", "retired", "crashed",
                          "pitted", "qualified", "overtook", "passed", "leading", "behind", "ahead"})


@lru_cache(maxsize=1)
def _notable_first_names() -> Dict[str, set]:
    """Last name -> first names of drivers with 20+ starts (F1DB, data/f1db_facts.json)."""
    import unicodedata as _ud
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "f1db_facts.json")
    out: Dict[str, set] = {}
    try:
        with open(path, encoding="utf-8") as f:
            pairs = json.load(f).get("notable_drivers", [])
    except (OSError, ValueError):
        return out
    fold = lambda t: "".join(c for c in _ud.normalize("NFD", t.lower()) if _ud.category(c) != "Mn")
    for first, last in pairs:
        out.setdefault(fold(last), set()).add(fold(first).split()[0])
    return out


def _names_another_driver(q: str, alias: str, did: str) -> bool:
    """'Graham Hill' must not resolve to Damon Hill through the bare alias 'hill'."""
    firsts = _notable_first_names().get(alias)
    if not firsts or len(firsts) < 2:
        return False
    own = (HISTORICAL_DRIVERS.get(did, {}).get("name", "").lower().split() or [""])[0]
    for m in re.finditer(rf"\b([a-z]+)\s+{re.escape(alias)}\b", q):
        if m.group(1) in firsts and m.group(1) != own:
            return True
    return False


def resolve_historical_driver(query: str) -> Optional[Dict[str, Any]]:
    """
    Resolves driver queries even with heavy typos (e.g. 'schmacur', 'shumacher', 'sena', 'versappen').
    Uses exact lookup, token matching, and difflib similarity against canonical names and aliases.
    """
    q = query.lower().strip()
    words = set(re.findall(r'[#\w]+', q))
    STOP_WORDS = {
        "when", "what", "which", "where", "driver", "drivers", "race", "raced", "racing",
        "driving", "year", "years", "time", "times", "title", "titles", "about", "most", "wins", "win",
        "poles", "pole", "points", "point", "podium", "podiums", "start", "starts", "fastest",
        "first", "last", "best", "greatest", "team", "teams", "car", "cars", "champion",
        "champions", "championship", "championships", "world", "youngest", "oldest", "ever",
        "history", "all-time", "grand", "prix", "season", "seasons", "career", "careers",
        "this", "that", "these", "those", "have", "has", "had", "will", "would", "could",
        "should", "with", "from", "into", "over", "under", "more", "less", "many", "much", "lead"
    }

    # 1. Exact alias or substring match in whole query
    for alias, did in sorted(DRIVER_NAME_LOOKUP.items(), key=lambda x: -len(x[0])):
        if len(alias) <= 3:
            # 3-letter codes/aliases must be exact whole words
            if alias in words:
                return HISTORICAL_DRIVERS.get(did)
            continue

        if " " in alias:
            if alias in q:
                return HISTORICAL_DRIVERS.get(did)
        else:
            if alias in words and not _names_another_driver(q, alias, did):
                return HISTORICAL_DRIVERS.get(did)

    # 2. Token-level close match with difflib across all driver aliases, for misspellings only:
    # a real English word ("started", "finished") is never a misspelled name ("started" scored
    # 0.71 against "stewart"). Real names were matched exactly in step 1.
    candidates = [k for k in DRIVER_NAME_LOOKUP.keys() if len(k) >= 4 and k not in STOP_WORDS]
    english = _english_words()
    for word in words:
        if len(word) < 5 or word in STOP_WORDS or word in english:
            continue
        matches = difflib.get_close_matches(word, candidates, n=1, cutoff=0.70)
        if matches:
            matched_did = DRIVER_NAME_LOOKUP[matches[0]]
            return HISTORICAL_DRIVERS.get(matched_did)

    return None


def lookup_driver_career(driver_id: str) -> Optional[Dict[str, Any]]:
    """Returns the full historical profile and formatted A2UI card for a driver."""
    profile = HISTORICAL_DRIVERS.get(driver_id)
    if not profile and driver_id:
        # Current-driver ids are short ("hamilton"); career profiles are keyed in full ("lewis_hamilton").
        profile = next((p for k, p in HISTORICAL_DRIVERS.items() if k.endswith("_" + driver_id)), None)
    if not profile:
        return None

    titles_str = f"{profile['titles_count']} Championship{'s' if profile['titles_count'] != 1 else ''}"
    if profile["championships"]:
        titles_str += f" ({', '.join(str(y) for y in profile['championships'])})"

    teams_str = ", ".join(f"{t['team']} ({t['years']})" for t in profile["teams"])
    eras_str = "\n".join(f"• **{era}**" for era in profile["primary_eras"])

    text = (
        f"**F1 Career Profile: {profile['name']} ({profile['nationality']})**\n\n"
        f"• **Active Racing Years**: {profile['active_years']}\n"
        f"• **World Championships**: **{titles_str}**\n"
        f"• **Primary Era(s)**:\n{eras_str}\n"
        f"• **Constructors & Teams**: {teams_str}\n"
        f"• **Career Statistics**: **{profile['wins']} Wins**, {profile['poles']} Poles, {profile['podiums']} Podiums, {profile['starts']} Starts ({profile['career_points']:.1f} pts)\n\n"
        f"> *Historical Analysis*: {profile['highlights']}"
    )

    landmark = profile.get("landmark_race") or {
        "year": 1998,
        "round": 13,
        "circuit_id": "spa",
        "race_name": "Belgian Grand Prix",
        "driver": profile.get("code", "MSC"),
        "lap": 1,
        "button_text": f"EXPLORE {profile['name'].upper()} REPLAY"
    }

    card = {
        "type": "driver_career_card",
        "title": f"F1 Career Profile — {profile['name']}",
        "metrics": [
            {"label": "World Titles", "value": f"{profile['titles_count']} Championships", "color": "#FFB703"},
            {"label": "Career Wins", "value": f"{profile['wins']} Wins ({profile['podiums']} Podiums)", "color": "#00F5D4"},
            {"label": "Active Seasons", "value": profile['active_years'].split("(")[0].strip(), "color": "#FFFFFF"},
            {"label": "Primary Era", "value": profile.get("primary_era_summary", "Historical Era")[:26], "color": "#E10600"}
        ],
        "action": landmark.get("button_text", f"EXPLORE {profile['name'].upper()} REPLAY"),
        "target": {
            "action_type": "jump_to_replay",
            "year": landmark.get("year", 1998),
            "round": landmark.get("round", 13),
            "session": "race",
            "lap": landmark.get("lap", 1),
            "driver": landmark.get("driver", profile.get("code")),
            "race_name": landmark.get("race_name", "Grand Prix")
        }
    }

    return {
        "profile": profile,
        "text": text,
        "card": card
    }


def lookup_f1_era(query: str) -> Optional[Dict[str, Any]]:
    """Resolves questions about F1 technical and regulatory eras (1950–2026+)."""
    q = query.lower()
    matched_era = None

    if any(k in q for k in ["2026", "active aero", "z-mode", "x-mode", "manual overtake", "sustainable fuel"]):
        matched_era = HISTORICAL_ERAS["2026"]
    elif any(k in q for k in ["2022", "2023", "2024", "2025", "ground effect", "venturi", "porpoising"]):
        matched_era = HISTORICAL_ERAS["2022_2025"]
    elif any(k in q for k in ["turbo hybrid", "v6 turbo", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "mgu-h", "mgu-k"]):
        matched_era = HISTORICAL_ERAS["2014_2021"]
    elif any(k in q for k in ["v8 era", "2006", "2007", "2008", "2009", "2010", "2011", "2012", "2013", "blown diffuser", "kers"]):
        matched_era = HISTORICAL_ERAS["2006_2013"]
    elif any(k in q for k in ["v10 era", "v10", "1995", "1996", "1997", "1998", "1999", "2000", "2001", "2002", "2003", "2004", "2005", "grooved"]):
        matched_era = HISTORICAL_ERAS["1995_2005"]
    elif any(k in q for k in ["3.5l", "active suspension", "fw14b", "1989", "1990", "1991", "1992", "1993", "1994"]):
        matched_era = HISTORICAL_ERAS["1990s_atmo"]
    elif any(k in q for k in ["turbo era", "1400hp", "1980s", "1977", "1978", "1979", "1981", "1982", "1983", "1984", "1985", "1986", "1987", "1988"]):
        matched_era = HISTORICAL_ERAS["1980s"]
    elif any(k in q for k in ["1970s", "dfv", "flat-12", "1971", "1972", "1973", "1974", "1975", "1976"]):
        matched_era = HISTORICAL_ERAS["1970s"]
    elif any(k in q for k in ["1960s", "lotus 25", "lotus 49", "1960", "1961", "1962", "1963", "1964", "1965", "1966", "1967", "1968", "1969"]):
        matched_era = HISTORICAL_ERAS["1960s"]
    elif any(k in q for k in ["1950s", "birth", "front engine", "alfetta", "1950", "1951", "1952", "1953", "1954", "1955", "1956", "1957", "1958", "1959"]):
        matched_era = HISTORICAL_ERAS["1950s"]
    elif "era" in q or "eras" in q:
        # No era keyword: semantic search over content/eras/, or the V10 overview when unsure
        hit = _content.search(q, "eras", 1)
        matched_era = HISTORICAL_ERAS[hit[0][0]["id"]] if hit and hit[0][1] >= ERA_SEARCH_MIN_SCORE else HISTORICAL_ERAS["1995_2005"]

    if not matched_era:
        return None

    innovations_str = "\n".join(f"• {x}" for x in matched_era["key_innovations"])
    text = (
        f"**FIA Technical Era Profile: {matched_era['title']}**\n\n"
        f"• **Engine Architecture**: {matched_era['engine_type']}\n"
        f"• **Power Output**: **{matched_era['total_hp']} HP** ({matched_era['ice_power_hp']} hp ICE"
        + (f" + {matched_era['electric_power_hp']} hp Electric)" if matched_era['electric_power_hp'] > 0 else ")")
        + f"\n• **Aerodynamics Concept**: {matched_era['downforce_concept']}\n"
        f"• **Dominant Champions**: {matched_era['dominant_champions']}\n"
        f"• **Dominant Constructors**: {matched_era['dominant_teams']}\n\n"
        f"**Key Innovations & Technical Milestones**:\n{innovations_str}\n\n"
        f"> *Pit Wall Historical Debrief*: {matched_era['ai_analysis']}"
    )

    card = {
        "type": "regulations_card",
        "title": f"F1 Era Technical Blueprint — {matched_era['years']}",
        "metrics": [
            {"label": "Total Power", "value": f"{matched_era['total_hp']} HP", "color": "#00F5D4"},
            {"label": "Engine Spec", "value": matched_era['engine_type'][:22], "color": "#FFB703"},
            {"label": "Aero Concept", "value": matched_era['downforce_concept'][:22], "color": "#FFFFFF"},
            {"label": "Era Status", "value": matched_era['years'], "color": "#E10600"}
        ],
        "action": "VIEW REGULATIONS TAB",
        "target": {
            "action_type": "open_regulations"
        }
    }

    return {
        "era_id": matched_era["id"],
        "era": matched_era,
        "text": text,
        "card": card
    }


def lookup_all_time_records(query: str) -> Optional[Dict[str, Any]]:
    """Resolves queries regarding all-time F1 records, leaderboards, and historical milestones."""
    q = query.lower()
    rec_key = None

    # Team questions first: "most constructors' titles" also contains "title".
    if any(k in q for k in ["constructor", "team", "wcc"]):
        rec_key = "constructors"
    elif any(k in q for k in ["championship", "title", "most championships", "most titles", "greatest", "goat"]):
        rec_key = "championships"
    elif any(k in q for k in ["win", "wins", "most wins", "most victories", "winner"]):
        rec_key = "wins"
    elif any(k in q for k in ["pole", "poles", "qualifying record"]):
        rec_key = "poles"
    elif any(k in q for k in ["constructor", "team", "most constructor"]):
        rec_key = "constructors"
    elif any(k in q for k in ["youngest", "youngest champion", "youngest winner"]):
        rec_key = "youngest_champion"
    else:
        rec_key = "wins"

    rec = ALL_TIME_RECORDS[rec_key]
    lines = [f"• **{i+1}. {item['name']}**: {item['value']}" for i, item in enumerate(rec["leaders"])]
    leaderboard_str = "\n".join(lines)

    text = (
        f"**Grand Prix Historical Leaderboard — {rec['title']}**\n\n"
        f"{leaderboard_str}\n\n"
        f"> *All records verified against Jolpica / Ergast Historical Classifications (1950–Present).* "
    )

    top_leader = rec["leaders"][0]
    p2_leader = rec["leaders"][1] if len(rec["leaders"]) > 1 else None

    card = {
        "type": "records_card",
        "title": rec["title"],
        "metrics": [
            {"label": "All-Time #1", "value": top_leader["name"][:20], "color": "#FFB703"},
            {"label": "Top Mark", "value": top_leader["value"].split("(")[0].strip()[:20], "color": "#00F5D4"},
            {"label": "All-Time #2", "value": p2_leader["name"][:20] if p2_leader else "—", "color": "#FFFFFF"},
            {"label": "Archive Span", "value": "1950–Present", "color": "#64748B"}
        ],
        "action": "OPEN STANDINGS TAB",
        "target": {
            "action_type": "open_standings",
            "year": 2026
        }
    }

    return {
        "record": rec,
        "text": text,
        "card": card
    }


def lookup_season_champion(year: int) -> Optional[Dict[str, Any]]:
    """Returns the World Championship winner, runner up, and stats for any year from 1950 to 2025."""
    info = WORLD_CHAMPIONS_BY_YEAR.get(year)
    if not info:
        return None

    text = (
        f"**{year} FIA Formula 1 World Championship Summary**:\n\n"
        f"• **World Drivers' Champion**: **{info['driver']}** driving for **{info['team']}**\n"
        f"• **Championship Record**: **{info['wins']} Grand Prix victories**, scoring **{info['points']:.1f} points**\n"
        f"• **Runner-Up**: {info['runner_up']}\n\n"
        f"> *Source: SimGent's season records.*"
    )

    card = {
        "type": "championship_card",
        "title": f"{year} World Championship Classification",
        "metrics": [
            {"label": "World Champion", "value": info["driver"][:20], "color": "#FFB703"},
            {"label": "Winning Team", "value": info["team"][:20], "color": "#00F5D4"},
            {"label": "Season Wins", "value": f"{info['wins']} Victories", "color": "#FFFFFF"},
            {"label": "Runner-Up", "value": info["runner_up"][:20], "color": "#64748B"}
        ],
        "action": f"VIEW {year} STANDINGS",
        "target": {
            "action_type": "open_standings",
            "year": year
        }
    }

    return {
        "year": year,
        "info": info,
        "text": text,
        "card": card
    }


# =============================================================================
# 5. HEAD-TO-HEAD DRIVER COMPARISON ENGINE
# =============================================================================

def compare_drivers_head_to_head(d1_query: str, d2_query: str) -> Optional[Dict[str, Any]]:
    """Compares two Formula 1 drivers head-to-head across titles, wins, poles, podiums, and eras."""
    d1 = resolve_historical_driver(d1_query)
    d2 = resolve_historical_driver(d2_query)
    if not d1 or not d2:
        return None
    if d1["id"] == d2["id"]:
        return None

    # Check famous direct teammate pairings
    pair = {d1["id"], d2["id"]}
    teammate_note = ""
    if pair == {"ayrton_senna", "alain_prost"}:
        teammate_note = "Teammates at McLaren-Honda (1988–1989): Senna 14 wins, Prost 11 wins; 1 title each (Senna '88, Prost '89). Infamous title collisions at Suzuka 1989 & 1990."
    elif pair == {"lewis_hamilton", "fernando_alonso"}:
        teammate_note = "Teammates at McLaren-Mercedes (2007): Tied on 109 points with 4 wins each in a legendary rookie vs reigning double-champion rivalry."
    elif pair == {"michael_schumacher", "nico_rosberg"}:
        teammate_note = "Teammates at Mercedes (2010–2012): Nico Rosberg outscored Schumacher across three developmental seasons before Hamilton joined."
    elif pair == {"sebastian_vettel", "kimi_raikkonen"}:
        teammate_note = "Teammates at Ferrari (2015–2018): Vettel won 13 races, Räikkönen won 1 race (Austin 2018)."
    elif pair == {"lewis_hamilton", "nico_rosberg"}:
        teammate_note = "Teammates at Mercedes (2013–2016): Hamilton won 32 races and 2 titles ('14, '15); Rosberg won 22 races and 1 title ('16)."

    text = (
        f"**F1 Head-to-Head Comparison: {d1['name']} vs {d2['name']}**\n\n"
        f"• **World Championships**: **{d1['titles_count']}** ({d1['name']}) vs **{d2['titles_count']}** ({d2['name']})\n"
        f"• **Grand Prix Wins**: **{d1['wins']}** vs **{d2['wins']}**\n"
        f"• **Pole Positions**: **{d1['poles']}** vs **{d2['poles']}**\n"
        f"• **Podium Finishes**: **{d1['podiums']}** vs **{d2['podiums']}**\n"
        f"• **Career Starts**: {d1['starts']} vs {d2['starts']}\n"
        f"• **Eras**: {d1.get('primary_era_summary', '')} vs {d2.get('primary_era_summary', '')}"
    )
    if teammate_note:
        text += f"\n\n• **Direct Teammate Dynamics**: {teammate_note}"

    card = {
        "type": "driver_comparison_card",
        "title": f"Head-to-Head — {d1['name']} vs {d2['name']}",
        "metrics": [
            {"label": "Titles (WDC)", "value": f"{d1['titles_count']} vs {d2['titles_count']}", "color": "#FFB703"},
            {"label": "Race Wins", "value": f"{d1['wins']} vs {d2['wins']}", "color": "#00F5D4"},
            {"label": "Pole Positions", "value": f"{d1['poles']} vs {d2['poles']}", "color": "#A855F7"},
            {"label": "Podiums", "value": f"{d1['podiums']} vs {d2['podiums']}", "color": "#FFFFFF"}
        ],
        "action": f"VIEW {d1['code']} PROFILE",
        "target": {
            "action_type": "open_driver_profile",
            "driver_id": d1["id"]
        }
    }
    return {
        "d1": d1,
        "d2": d2,
        "text": text,
        "card": card
    }


# =============================================================================
# 6. DRIVER CAREER MILESTONES & SPECIFIC METRIC LOOKUP
# =============================================================================

@lru_cache(maxsize=1)
def _f1db_facts() -> Dict[str, Any]:
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "f1db_facts.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _fold(text: str) -> str:
    import unicodedata as _ud
    return " ".join("".join(c for c in _ud.normalize("NFD", (text or "").lower()) if _ud.category(c) != "Mn").replace("-", " ").split())


def _f1db_driver(query: str) -> Optional[Dict[str, Any]]:
    """The driver a question names, from F1DB career totals: full name first, then the curated
    aliases (nicknames, typos), then a last name only one driver with 20+ starts has."""
    drivers = _f1db_facts().get("drivers") or []
    if not drivers:
        return None
    q = " " + " ".join(re.findall(r"[a-z0-9]+", _fold(query))) + " "
    full = [d for d in drivers if f" {_fold(d['first'] + ' ' + d['last'])} " in q]
    if full:
        return max(full, key=lambda d: len(d["first"]) + len(d["last"]))
    roster = resolve_historical_driver(query)
    if roster:
        name = _fold(roster["name"])
        hit = [d for d in drivers if _fold(f"{d['first']} {d['last']}") == name]
        if hit:
            return hit[0]
    by_last = [d for d in drivers if d["starts"] >= 20 and f" {_fold(d['last'])} " in q]
    return by_last[0] if len(by_last) == 1 else None


METRICS = [  # (question words, F1DB field, label)
    (("podium", "podiums"), "podiums", "podiums"),
    (("win", "wins", "victories", "victory", "won"), "wins", "Grand Prix wins"),
    (("pole", "poles", "pole position", "pole positions"), "poles", "pole positions"),
    (("championship", "championships", "title", "titles", "wdc"), "titles", "World Championships"),
    (("fastest lap", "fastest laps"), "fastest_laps", "fastest laps"),
    (("start", "starts", "races", "entries"), "starts", "Grand Prix starts"),
]


def lookup_driver_metric(query: str) -> Optional[Dict[str, Any]]:
    """'How many podiums does Fernando Alonso have?', 'How many wins did Graham Hill have?':
    career totals from F1DB for every driver, ranked against all of them. (Numbers used to be
    typed into the driver roster, for a few dozen drivers, and went out of date.)"""
    d = _f1db_driver(query)
    if not d:
        return None
    q_low = query.lower()
    metric = next(((field, label) for words, field, label in METRICS
                   if any(re.search(rf"\b{re.escape(w)}\b", q_low) for w in words)), None)
    if not metric:
        return None
    field, label = metric
    facts = _f1db_facts()
    val = d[field]
    better = sum(1 for x in facts["drivers"] if x[field] > val)
    tied = sum(1 for x in facts["drivers"] if x[field] == val) > 1
    rank = f"{'=' if tied else ''}#{better + 1} all-time" if val else "none"
    name = f"{d['first']} {d['last']}"
    years = [y for y, c in sorted(facts.get("champions", {}).items()) if _fold(c["first"]) == _fold(d["first"]) and _fold(c["last"]) == _fold(d["last"])]
    seasons = f"{d['seasons'][0]}–{d['seasons'][1]}" if d.get("seasons") else ""
    through = (facts.get("facts_through") or {}).get("race", "")
    through_txt = f"to the {through.split('_')[0]} season, round {through.split('_')[1]}" if through else ""
    text = (
        f"**{name}** has **{val} {label}** in Formula 1 ({rank}).\n\n"
        f"• **Seasons**: {seasons}\n"
        f"• **World Championships**: {d['titles']}" + (f" ({', '.join(years)})" if years else "") + "\n"
        f"• **Career**: {d['wins']} wins, {d['poles']} poles, {d['podiums']} podiums from {d['starts']} starts\n\n"
        f"*Source: F1DB{', ' + through_txt if through_txt else ''}.*"
    )
    card = {
        "type": "driver_performance_card",
        "title": f"Career — {name}",
        "metrics": [
            {"label": label[:30], "value": f"{val}", "color": "#00F5D4"},
            {"label": "All-time rank", "value": rank, "color": "#FFB703"},
            {"label": "Starts", "value": f"{d['starts']}", "color": "#FFFFFF"},
            {"label": "World titles", "value": f"{d['titles']}", "color": "#E10600"},
        ],
    }
    roster = resolve_historical_driver(name)
    return {"driver": {"id": roster["id"] if roster else _fold(name).replace(" ", "_"), "name": name},
            "metric": label, "value": val, "text": text, "card": card}


def _race_title(key: str) -> str:
    year, rnd = key.split("_")
    from app.tools import jolpica_sync as J
    race = next((r for r in (J.schedule(int(year), net=False) or []) if str(r.get("round")) == rnd), None)
    if race:
        return f"{year} {race['raceName']}"
    names = (_f1db_facts().get("races", {}).get(key) or {}).get("circuit_names") or ["round " + rnd]
    return f"{year} race at {names[0]}"


def _grid_text(grid: Optional[int]) -> str:
    return "the pit lane" if grid is None else f"P{grid}"


def lookup_comebacks(query: str, race_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """'In what race did Antonelli win from the back of the grid?', 'biggest comeback win ever',
    'who gained the most places in this race?': starting grid against finish, from F1DB, for a
    driver, a season, one race (race_key "2026_13") or all time.
    Wins and podiums rank by how far back the driver started (the pit lane is furthest);
    other questions rank by places gained, among finishers who gained 5 or more."""
    facts = _f1db_facts()
    races = facts.get("races") or {}
    q = query.lower()
    driver = None if race_key else _f1db_driver(query)
    year = None if race_key else re.search(r"\b(19[5-9]\d|20[0-2]\d)\b", q)
    want = ("win" if re.search(r"\b(win|wins|won|winning|victory|victories)\b", q)
            else "podium" if re.search(r"\bpodiums?\b", q) else "gain")
    rows = []
    for key, race in races.items():
        if race_key and key != race_key:
            continue
        if year and not key.startswith(year.group(1) + "_"):
            continue
        for r in race.get("comebacks") or []:
            if driver and (_fold(r["first"]), _fold(r["last"])) != (_fold(driver["first"]), _fold(driver["last"])):
                continue
            if want == "win" and r["finish"] != 1 or want == "podium" and r["finish"] > 3:
                continue
            if want == "gain" and (r["grid"] is None or r["grid"] - r["finish"] < 5):
                continue
            rows.append((key, r))
    order = lambda k: tuple(map(int, k.split("_")))
    if want == "gain":
        rows.sort(key=lambda kr: (-(kr[1]["grid"] - kr[1]["finish"]), order(kr[0])))
    else:  # furthest back first; the pit lane is behind every grid slot
        rows.sort(key=lambda kr: (-(kr[1]["grid"] if kr[1]["grid"] is not None else 99), order(kr[0])))

    through = (facts.get("facts_through") or {}).get("race", "")
    source = "*Source: F1DB starting grids and results" + (
        f", to the {through.split('_')[0]} season, round {through.split('_')[1]}" if through else "") + ".*"
    name = f"{driver['first']} {driver['last']}" if driver else ""
    scope = (f" at the **{_race_title(race_key)}**" if race_key else f" in {year.group(1)}" if year else "")
    what = {"win": "win", "podium": "podium", "gain": "climb through the field"}[want]
    if not rows:
        if driver and want == "win" and not driver["wins"]:
            text = f"**{name}** has no Grand Prix wins in F1DB."
        elif race_key:
            text = f"Nobody gained five or more places{scope}."
        else:
            text = f"F1DB has no {what}{' for **' + name + '**' if driver else ''}{scope} that fits."
        return {"text": f"{text}\n\n{source}", "card": None, "driver": name}

    def line(key, r):
        gained = f" (+{r['grid'] - r['finish']})" if r["grid"] is not None else ""
        who = "" if driver else f"**{r['first']} {r['last']}** · "
        where = "" if race_key else f"{_race_title(key)} · "
        return f"• {who}{where}{_grid_text(r['grid'])} → P{r['finish']}{gained}"

    key, top = rows[0]
    who = name or f"{top['first']} {top['last']}"
    race_txt = _race_title(key)
    if race_key and want != "gain":
        head = f"At the **{race_txt}**: " + "; ".join(
            f"**{r['first']} {r['last']}** {'won' if r['finish'] == 1 else 'finished P' + str(r['finish'])} "
            f"from **{_grid_text(r['grid'])}**" for _, r in sorted(rows, key=lambda kr: kr[1]["finish"])) + "."
        rows = rows[:1]
    elif want == "win":
        head = (f"**{who}**'s win from furthest back{scope} was the **{race_txt}**: "
                f"started from **{_grid_text(top['grid'])}** and won.")
        if not driver:
            head = (f"The win from furthest back{scope}: **{who}** at the **{race_txt}**, "
                    f"from **{_grid_text(top['grid'])}**.")
    elif want == "podium":
        head = (f"{'**' + who + '**' + chr(39) + 's' if driver else 'The'} podium from furthest back{scope}: "
                f"{'' if driver else '**' + who + '** at '}the **{race_txt}**, from **{_grid_text(top['grid'])}** to **P{top['finish']}**.")
    else:
        head = (f"{'**' + who + '**' + chr(39) + 's biggest' if driver else 'The biggest'} climb through the field{scope}: "
                f"{'' if driver else '**' + who + '**, '}{'' if race_key else 'the **' + race_txt + '**, '}"
                f"from **{_grid_text(top['grid'])}** to **P{top['finish']}** (+{top['grid'] - top['finish']} places).")
    if want != "gain" and top["grid"] is not None and re.search(r"\bpit ?lane\b", q):
        head = f"Nobody has {'won' if want == 'win' else 'reached the podium'} from the pit lane{scope} in F1DB. " + head
    others = [(k, r) for k, r in rows[1:] if r["grid"] is None or r["grid"] > r["finish"]][:5]
    listing = ("\n\n**Next furthest back:**\n" if want != "gain" else "\n\n**Next biggest climbs:**\n") + \
        "\n".join(line(k, r) for k, r in others) if others else ""
    text = f"{head}{listing}\n\n{source}"
    card = {
        "type": "driver_performance_card",
        "title": f"Comeback — {who}"[:60],
        "metrics": [
            {"label": "Race", "value": race_txt, "color": "#FFFFFF"},
            {"label": "Started", "value": _grid_text(top["grid"]), "color": "#FFB703"},
            {"label": "Finished", "value": f"P{top['finish']}", "color": "#00F5D4"},
            {"label": "Places gained", "value": f"+{top['grid'] - top['finish']}" if top["grid"] else "pit lane",
             "color": "#E10600"},
        ],
    }
    return {"text": text, "card": card, "driver": who, "race": key}


# =============================================================================
# 7. HISTORIC RACE MOMENTS & FAMOUS CONTROVERSIES (1950–2026)
# =============================================================================

# Stories live in content/races/*.md (title, keywords, card figures in front matter; summary in the body).
HISTORIC_RACE_STORIES: List[Dict[str, Any]] = _content.race_stories()


def lookup_historic_race_event(query: str, year: Optional[int] = None, circuit_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Searches curated historical race stories for iconic moments and controversies."""
    q_low = query.lower()
    for story in HISTORIC_RACE_STORIES:
        if year and story["year"] == year:
            if not circuit_id or circuit_id == story["circuit_id"] or any(k in q_low for k in story["keywords"]):
                return {
                    "story": story,
                    "text": f"**{story['title']}**\n\n{story['summary']}",
                    "card": {
                        "type": "historic_race_card",
                        "title": story["title"],
                        "metrics": story["metrics"],
                        "action": f"EXPLORE {story['year']} REPLAY",
                        "target": {
                            "action_type": "jump_to_replay",
                            "year": story["year"],
                            "round": story["round"],
                            "session": "race",
                            "circuit_id": story["circuit_id"],
                            "race_name": story["race_name"]
                        }
                    }
                }
        for kw in story["keywords"]:
            if kw in q_low:
                return {
                    "story": story,
                    "text": f"**{story['title']}**\n\n{story['summary']}",
                    "card": {
                        "type": "historic_race_card",
                        "title": story["title"],
                        "metrics": story["metrics"],
                        "action": f"EXPLORE {story['year']} REPLAY",
                        "target": {
                            "action_type": "jump_to_replay",
                            "year": story["year"],
                            "round": story["round"],
                            "session": "race",
                            "circuit_id": story["circuit_id"],
                            "race_name": story["race_name"]
                        }
                    }
                }
    return None


# =============================================================================
# DATA REFRESH: keep career wins & titles in step with the official results data
# =============================================================================
# The profiles above are hand-written snapshots and go stale as seasons are raced
# (e.g. a 2025 title or 2026 wins). Wins are recounted from the cached per-season
# winners files and titles from WORLD_CHAMPIONS_BY_YEAR. Podiums, poles and starts
# are not cached for every season, so they keep their written values. If a driver's
# name cannot be matched in the data, the written values are kept unchanged.

def _norm_name(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z ]", "", s.lower()).strip()


def _same_driver(profile_name: str, given: str, family: str) -> bool:
    p = _norm_name(profile_name).split()
    fam = _norm_name(family).split()
    giv = _norm_name(given).split()
    if not p or not fam or p[-len(fam):] != fam:
        return False
    return bool(giv) and giv[0] in p[:-len(fam)]


def _refresh_profiles_from_data() -> None:
    import json as _json
    import os as _os
    cache = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))),
                          "data", "cache", "jolpica")
    winners = []  # (given, family)
    try:
        for fn in _os.listdir(cache):
            if re.match(r"^\d{4}_winners\.json$", fn):
                with open(_os.path.join(cache, fn)) as f:
                    for r in _json.load(f)["MRData"]["RaceTable"]["Races"]:
                        for x in (r.get("Results") or [])[:1]:
                            winners.append((x["Driver"]["givenName"], x["Driver"]["familyName"]))
    except Exception:
        return
    if not winners:
        return

    def _wins(name: str) -> int:
        return sum(1 for g, fam in winners if _same_driver(name, g, fam))

    def _titles(name: str) -> List[int]:
        out = []
        for y, info in WORLD_CHAMPIONS_BY_YEAR.items():
            parts = info["driver"].split()
            if len(parts) >= 2 and _same_driver(name, parts[0], parts[-1]):
                out.append(y)
        return sorted(out)

    for profile in HISTORICAL_DRIVERS.values():
        w = _wins(profile["name"])
        if w > 0:
            profile["wins"] = w
        t = _titles(profile["name"])
        if t:
            profile["championships"] = t
            profile["titles_count"] = len(t)

    # All-time leaderboards: recount wins and drivers' titles the same way.
    wins_board = ALL_TIME_RECORDS.get("wins", {}).get("leaders", [])
    for row in wins_board:
        w = _wins(row["name"])
        if w > 0:
            row["value"] = f"{w} Wins"
    wins_board.sort(key=lambda r: -int(re.match(r"\d+", r["value"]).group(0)))
    titles_board = ALL_TIME_RECORDS.get("championships", {}).get("leaders", [])
    for row in titles_board:
        t = _titles(row["name"])
        if t:
            row["value"] = f"{len(t)} Title{'s' if len(t) != 1 else ''} ({', '.join(str(y) for y in t)})"


_refresh_profiles_from_data()
