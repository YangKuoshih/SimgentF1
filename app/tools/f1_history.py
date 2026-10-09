"""
SimGent - Comprehensive Formula 1 History & Career Knowledge Base (1950–2026)
Provides authoritative data, fuzzy driver matching, career timelines, technical eras,
championship rosters, all-time records, and legendary rivalries for motorsport research and analysis.
"""

import difflib
import re
from typing import Any, Dict, List, Optional, Tuple

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

HISTORICAL_ERAS: Dict[str, Dict[str, Any]] = {
    "1950s": {
        "id": "1950s",
        "title": "1950–1959 Front-Engine Birth Era",
        "years": "1950–1959",
        "engine_type": "4.5L Atmospheric / 1.5L Supercharged Inline-8 & V12",
        "ice_power_hp": 420,
        "electric_power_hp": 0,
        "total_hp": 420,
        "downforce_concept": "Front-engine cigar tube chassis, zero aerodynamic wings",
        "dominant_teams": "Alfa Romeo (158/159 Alfetta), Ferrari (500, 375), Maserati (250F), Mercedes-Benz (W196)",
        "dominant_champions": "Juan Manuel Fangio (5 titles), Alberto Ascari (2 titles), Giuseppe Farina",
        "key_innovations": [
            "Inaugural 1950 FIA Formula One World Championship season",
            "Supercharged 1.5L engines producing 400+ hp on toxic methanol/benzene fuel mixtures",
            "Drum brakes and skinny bias-ply treaded tyres with zero driver safety barriers"
        ],
        "ai_analysis": (
            "The romantic and lethal founding decade of Formula 1. Cars were front-engined, heavy, and required "
            "massive physical strength to drift through high-speed turns. Reliability was minimal, and Fangio emerged as the undisputed maestro."
        )
    },
    "1960s": {
        "id": "1960s",
        "title": "1960–1969 Classic Rear-Engine & Cosworth DFV Era",
        "years": "1960–1969",
        "engine_type": "1.5L (1961–1965) then 3.0L V8 (Ford Cosworth DFV introduced 1967)",
        "ice_power_hp": 410,
        "electric_power_hp": 0,
        "total_hp": 410,
        "downforce_concept": "Rear mid-engine layout, aluminum monocoque, early tall wings introduced 1968",
        "dominant_teams": "Lotus, Ferrari, BRM, Brabham, Matra",
        "dominant_champions": "Jim Clark, Graham Hill, Jackie Stewart, Jack Brabham, Phil Hill, John Surtees",
        "key_innovations": [
            "Colin Chapman's Lotus 25 stressed aluminum monocoque chassis replacing steel spaceframes",
            "Ford Cosworth DFV V8 engine acting as a load-bearing chassis member",
            "Introduction of inverted aerodynamic wings on suspension uprights (1968–1969)"
        ],
        "ai_analysis": (
            "The engineering transition from front-engine roadsters to mid-engine open-wheelers. "
            "Aerodynamic drag was minimal, allowing long slipstreams, while Lotus pioneered stressed monocoques."
        )
    },
    "1970s": {
        "id": "1970s",
        "title": "1970–1976 Cosworth DFV & Downforce Dawn Era",
        "years": "1970–1976",
        "engine_type": "3.0L Naturally Aspirated V8 (Cosworth DFV) & Ferrari Flat-12",
        "ice_power_hp": 485,
        "electric_power_hp": 0,
        "total_hp": 485,
        "downforce_concept": "Integrated front/rear wings, slick tyres, wedge-shaped airboxes",
        "dominant_teams": "Tyrrell, Ferrari, Lotus, McLaren",
        "dominant_champions": "Jackie Stewart, Niki Lauda, Emerson Fittipaldi, James Hunt, Jochen Rindt",
        "key_innovations": [
            "Introduction of wide slick tyres (1971) providing dramatic mechanical grip",
            "High periscope airboxes feeding atmospheric air directly into intake trumpets",
            "Legendary 1976 championship duel between Niki Lauda and James Hunt"
        ],
        "ai_analysis": (
            "Defined by pure mechanical grip and visceral close racing. Ferrari's Flat-12 Boxer engine "
            "rivaled the omnipresent Cosworth DFV V8, while drivers pushed for modern safety gear and track barriers."
        )
    },
    "1980s": {
        "id": "1980s",
        "title": "1977–1988 1,400hp Turbo Monster Era",
        "years": "1977–1988",
        "engine_type": "1.5L Turbocharged Inline-4 & V6 (BMW M12, TAG-Porsche, Honda RA168E, Renault)",
        "ice_power_hp": 1400,
        "electric_power_hp": 0,
        "total_hp": 1400,
        "downforce_concept": "Ground-effect sliding skirts (banned 1983), flat-bottom floors, high rear downforce",
        "dominant_teams": "McLaren, Williams, Brabham, Renault, Ferrari",
        "dominant_champions": "Ayrton Senna, Alain Prost, Nelson Piquet, Niki Lauda, Keke Rosberg",
        "key_innovations": [
            "BMW M12/13 and Honda RA168E reaching over 5.5 bar boost in qualifying trim (1,400+ hp)",
            "Massive turbo lag requiring drivers to throttle up before corner apexes",
            "Carbon-fiber composite monocoques introduced by John Barnard (McLaren MP4/1, 1981)"
        ],
        "ai_analysis": (
            "The most brutal horsepower-to-weight era in motorsport history. Massive qualifying boost grenades "
            "paired with manual H-pattern transmissions made these cars untamable monsters mastered by Senna and Prost."
        )
    },
    "1990s_atmo": {
        "id": "1990s_atmo",
        "title": "1989–1994 3.5L Atmospheric & Electronic Revolution Era",
        "years": "1989–1994",
        "engine_type": "3.5L Naturally Aspirated V10 & V12 (Honda, Renault, Ferrari, Ford)",
        "ice_power_hp": 780,
        "electric_power_hp": 0,
        "total_hp": 780,
        "downforce_concept": "Stepped floors, raised noses, active hydraulic suspension (Williams FW14B)",
        "dominant_teams": "McLaren-Honda, Williams-Renault, Benetton-Ford",
        "dominant_champions": "Ayrton Senna, Alain Prost, Nigel Mansell, Michael Schumacher (1994 debut title)",
        "key_innovations": [
            "Electronic driver aids: computer-controlled active suspension, traction control, launch control",
            "Semi-automatic paddle-shift gearboxes pioneered by Ferrari 640 in 1989",
            "Adrian Newey's aerodynamic packaging dominating with Williams FW14B and FW15C"
        ],
        "ai_analysis": (
            "A technical revolution where software and aerodynamics reshaped F1. Active suspension eliminated pitch and roll, "
            "allowing Nigel Mansell and Alain Prost to obliterate lap records before aids were banned in 1994."
        )
    },
    "1995_2005": {
        "id": "1995_2005",
        "title": "1995–2005 3.0L V10 Golden Era",
        "years": "1995–2005",
        "engine_type": "3.0L Naturally Aspirated 90° V10 (20,000 RPM scream)",
        "ice_power_hp": 950,
        "electric_power_hp": 0,
        "total_hp": 950,
        "downforce_concept": "Stepped bottom, grooved dry tyres (1998–2008), complex flip-up winglets",
        "dominant_teams": "Scuderia Ferrari, McLaren-Mercedes, Williams-BMW, Renault",
        "dominant_champions": "Michael Schumacher (5 consecutive Ferrari titles), Mika Häkkinen, Fernando Alonso, Jacques Villeneuve, Damon Hill",
        "key_innovations": [
            "20,000+ RPM shrieking V10 engines (BMW P84/P85, Ferrari Tipo 053) producing intoxicating acoustics",
            "In-race refueling fueling flat-out sprint qualifying stints every single lap",
            "Bridgestone vs. Michelin tyre war driving unprecedented compound development",
            "Ferrari F2004 setting lap records that stood for nearly two decades"
        ],
        "ai_analysis": (
            "Considered by many the pinnacle of raw mechanical emotion. Michael Schumacher and Ferrari constructed "
            "the most dominant dynasty of the modern era, setting benchmarks for physical conditioning and technical precision."
        )
    },
    "2006_2013": {
        "id": "2006_2013",
        "title": "2006–2013 2.4L V8 Screamer & Blown Diffuser Era",
        "years": "2006–2013",
        "engine_type": "2.4L 90° Naturally Aspirated V8 (18,000 RPM rev-limiter)",
        "ice_power_hp": 750,
        "electric_power_hp": 80,
        "total_hp": 830,
        "downforce_concept": "High-rake chassis, off-throttle blown diffusers (Red Bull/Newey), beam wings",
        "dominant_teams": "Red Bull Racing, Ferrari, McLaren, Brawn GP",
        "dominant_champions": "Sebastian Vettel (4 consecutive titles), Fernando Alonso, Kimi Räikkönen, Lewis Hamilton, Jenson Button",
        "key_innovations": [
            "KERS (Kinetic Energy Recovery System) introducing early electrical boost (60 kW / 80 hp)",
            "DRS (Drag Reduction System) introduced in 2011 to promote overtaking",
            "Adrian Newey's exhaust blown diffusers generating artificial cornering downforce off-throttle",
            "Return to slick tyres in 2009 with mandatory standardized aerodynamics"
        ],
        "ai_analysis": (
            "Characterized by ultra-tight championship fights (2007, 2008, 2010, 2012) and Sebastian Vettel's "
            "record-breaking run with Red Bull. Acoustics remained deafening at 18,000 RPM."
        )
    },
    "2014_2021": {
        "id": "2014_2021",
        "title": "2014–2021 1.6L V6 Turbo-Hybrid Dominance Era",
        "years": "2014–2021",
        "engine_type": "1.6L Single-Turbo 90° V6 + Dual ERS (MGU-K 120kW + MGU-H turbo)",
        "ice_power_hp": 840,
        "electric_power_hp": 160,
        "total_hp": 1000,
        "downforce_concept": "Complex over-body bargeboard vortex generators, wide track (2017+), high downforce",
        "dominant_teams": "Mercedes-AMG Petronas (8 consecutive WCCs), Red Bull Racing, Ferrari",
        "dominant_champions": "Lewis Hamilton (6 titles with Mercedes), Nico Rosberg, Max Verstappen (2021)",
        "key_innovations": [
            "Over 50% thermal efficiency achieved through continuous MGU-H exhaust heat harvesting",
            "Mercedes-AMG W11 (2020) setting the fastest average lap speeds in F1 history (264.362 km/h at Monza)",
            "Halo cockpit head protection system introduced in 2018 saving multiple driver lives"
        ],
        "ai_analysis": (
            "The engineering masterpiece of thermal efficiency and raw downforce. Mercedes constructed an unprecedented "
            "8-year Constructors' streak, culminating in the historic 2021 title duel between Hamilton and Verstappen."
        )
    },
    "2022_2025": {
        "id": "2022_2025",
        "title": "2022–2025 Venturi Floor Ground Effect Era",
        "years": "2022–2025",
        "engine_type": "1.6L V6 Turbo-Hybrid + E10 Sustainable Fuel",
        "ice_power_hp": 840,
        "electric_power_hp": 160,
        "total_hp": 1000,
        "downforce_concept": "Underfloor Venturi ground-effect tunnels, 18-inch low-profile Pirelli tyres",
        "dominant_teams": "Red Bull Racing (RB18, RB19, RB20), McLaren, Ferrari, Mercedes",
        "dominant_champions": "Max Verstappen (3 consecutive titles: 2022, 2023, 2024)",
        "key_innovations": [
            "Complete aerodynamic reset to minimize dirty air wake and enable close follow within 1 second",
            "Cost cap financial regulations enforcing competitive parity across all 10 constructors",
            "Red Bull RB19 achieving 21 wins from 22 races in 2023 (95.5% win rate)"
        ],
        "ai_analysis": (
            "Ground effect transformed wheel-to-wheel overtaking while introducing physical setup challenges like porpoising. "
            "Max Verstappen achieved historical dominance before McLaren and Ferrari closed the gap in 2024–2025."
        )
    },
    "2026": {
        "id": "2026",
        "title": "2026+ Active Aerodynamics & 50/50 Electric Power Unit Era",
        "years": "2026+",
        "engine_type": "1.6L V6 Turbo + 350 kW MGU-K on 100% Drop-In E-Fuel (MGU-H eliminated)",
        "ice_power_hp": 535,
        "electric_power_hp": 470,
        "total_hp": 1005,
        "downforce_concept": "Active Aerodynamics: High-downforce Z-Mode cornering & low-drag X-Mode straights",
        "dominant_teams": "Ferrari, McLaren, Red Bull-Ford, Mercedes, Aston Martin-Honda, Audi",
        "dominant_champions": "Active 2026 World Championship Fight",
        "key_innovations": [
            "Exact 50/50 power distribution: 400 kW (535 hp) ICE + 350 kW (470 hp) MGU-K",
            "Elimination of expensive MGU-H enabling new manufacturer entries (Audi, Ford)",
            "Manual Overtake Mode (MOM) providing electrical overrides up to 337 km/h",
            "100% fossil-free drop-in sustainable advanced synthetic bio-fuel"
        ],
        "ai_analysis": (
            "The dawn of intelligent energy management and active aerodynamics. DRS is obsolete, replaced by dynamic "
            "wing configurations and electrical push-to-pass tactics."
        )
    }
}


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
            if alias in words:
                return HISTORICAL_DRIVERS.get(did)

    # 2. Token-level close match with difflib across all driver aliases
    candidates = [k for k in DRIVER_NAME_LOOKUP.keys() if len(k) >= 4 and k not in STOP_WORDS]
    for word in words:
        if len(word) < 5 or word in STOP_WORDS:
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
        # General overview of eras
        matched_era = HISTORICAL_ERAS["1995_2005"]

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
        f"> *Interactive replays and timing classifications are archived for competitive sessions across all 76 seasons.*"
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

def lookup_driver_metric(query: str) -> Optional[Dict[str, Any]]:
    """Resolves questions like 'How many podiums does Fernando Alonso have?' or 'How many wins does Max Verstappen have?'"""
    driver = resolve_historical_driver(query)
    if not driver:
        return None

    q_low = query.lower()
    val = 0
    metric_label = ""
    all_time_rank = ""

    if any(w in q_low for w in ["podium", "podiums"]):
        metric_label = "Podiums"
        val = driver.get("podiums", 0)
        all_time_rank = "#1 All-Time" if driver["id"] == "lewis_hamilton" else "#2 All-Time" if driver["id"] == "michael_schumacher" else "#3 All-Time" if driver["id"] == "max_verstappen" else "#4 All-Time" if driver["id"] == "sebastian_vettel" else "#5 All-Time" if driver["id"] == "fernando_alonso" else "Elite Contender"
    elif any(w in q_low for w in ["win", "wins", "victories", "victory"]):
        metric_label = "Grand Prix Wins"
        val = driver.get("wins", 0)
        all_time_rank = "#1 All-Time (105)" if driver["id"] == "lewis_hamilton" else "#2 All-Time (91)" if driver["id"] == "michael_schumacher" else "#3 All-Time" if driver["id"] == "max_verstappen" else "#4 All-Time (53)" if driver["id"] == "sebastian_vettel" else "#5 All-Time (51)" if driver["id"] == "alain_prost" else "#6 All-Time (41)" if driver["id"] == "ayrton_senna" else "#7 All-Time (32)" if driver["id"] == "fernando_alonso" else "Grand Prix Winner"
    elif any(w in q_low for w in ["pole", "poles", "pole position", "qualifying p1"]):
        metric_label = "Pole Positions"
        val = driver.get("poles", 0)
        all_time_rank = "#1 All-Time (104)" if driver["id"] == "lewis_hamilton" else "#2 All-Time (68)" if driver["id"] == "michael_schumacher" else "#3 All-Time (65)" if driver["id"] == "ayrton_senna" else "#4 All-Time (57)" if driver["id"] == "sebastian_vettel" else "#5 All-Time" if driver["id"] == "max_verstappen" else "Front Row Master"
    elif any(w in q_low for w in ["championship", "championships", "title", "titles", "wdc"]):
        metric_label = "World Championships"
        val = driver.get("titles_count", 0)
        all_time_rank = "= #1 All-Time (7 Titles)" if driver["id"] in ["lewis_hamilton", "michael_schumacher"] else "#2 All-Time (5 Titles)" if driver["id"] == "juan_manuel_fangio" else "= #3 All-Time (4 Titles)" if driver["id"] in ["max_verstappen", "alain_prost", "sebastian_vettel"] else "World Drivers' Champion"
    elif any(w in q_low for w in ["start", "starts", "races", "entries"]):
        metric_label = "Race Starts"
        val = driver.get("starts", 0)
        all_time_rank = "#1 All-Time (Most Starts in F1 History)" if driver["id"] == "fernando_alonso" else "#2 All-Time" if driver["id"] == "lewis_hamilton" else "#3 All-Time" if driver["id"] == "kimi_raikkonen" else "Veteran Driver"
    else:
        return None

    text = (
        f"**{driver['name']}** has amassed **{val} {metric_label}** across their Formula 1 career ({all_time_rank}).\n\n"
        f"• **Active Years**: {driver.get('active_years', '')}\n"
        f"• **World Championships**: **{driver.get('titles_count', 0)} Titles** ({', '.join(str(y) for y in driver.get('championships', [])) if driver.get('championships') else 'None'})\n"
        f"• **Career Statistics**: {driver.get('wins', 0)} Wins, {driver.get('poles', 0)} Poles, {driver.get('podiums', 0)} Podiums across {driver.get('starts', 0)} starts."
    )

    card = {
        "type": "driver_performance_card",
        "title": f"Career Milestone — {driver['name']} ({metric_label})",
        "metrics": [
            {"label": metric_label, "value": f"{val}", "color": "#00F5D4"},
            {"label": "All-Time Standing", "value": all_time_rank[:20], "color": "#FFB703"},
            {"label": "Total Starts", "value": f"{driver.get('starts', 0)} GPs", "color": "#FFFFFF"},
            {"label": "Championships", "value": f"{driver.get('titles_count', 0)} WDC", "color": "#E10600"}
        ],
        "action": f"VIEW {driver['code']} CAREER",
        "target": {
            "action_type": "open_driver_profile",
            "driver_id": driver["id"]
        }
    }
    return {
        "driver": driver,
        "metric": metric_label,
        "value": val,
        "text": text,
        "card": card
    }


# =============================================================================
# 7. HISTORIC RACE MOMENTS & FAMOUS CONTROVERSIES (1950–2026)
# =============================================================================

HISTORIC_RACE_STORIES: List[Dict[str, Any]] = [
    {
        "id": "2011_canada",
        "year": 2011,
        "round": 7,
        "circuit_id": "villeneuve",
        "race_name": "Canadian Grand Prix (Montreal)",
        "keywords": ["longest", "longest race", "longest f1 race", "2011 canada", "2011 canadian", "button last to first", "six pit stops", "four hours"],
        "title": "2011 Canadian Grand Prix — The Longest Race in F1 History",
        "summary": (
            "The 2011 Canadian Grand Prix is officially the **longest race in Formula 1 history**, lasting **4 hours, 4 minutes, and 39 seconds** "
            "due to a 2-hour torrential rain red flag.\n\n"
            "• **Jenson Button's Miracle Win**: Button made **6 pit stops**, served a drive-through penalty, collided with teammate Lewis Hamilton and Fernando Alonso, "
            "suffered a puncture, and was running in **dead last (P21) on Lap 40**.\n"
            "• **The Final Lap Drama**: Slicing through the field on drying tyres, Button hunted down championship leader Sebastian Vettel, who made a rare error "
            "sliding wide onto wet astroturf at Turn 6 on the very final lap, allowing Button to sweep past for one of the greatest comeback victories ever seen."
        ),
        "metrics": [
            {"label": "Race Duration", "value": "4h 04m 39s (Record)", "color": "#FFB703"},
            {"label": "Winner", "value": "Jenson Button (P21 → P1)", "color": "#00F5D4"},
            {"label": "Button Pit Stops", "value": "6 Stops + Drive-Thru", "color": "#FFFFFF"},
            {"label": "Safety Car Periods", "value": "6 Neutralisations", "color": "#E10600"}
        ]
    },
    {
        "id": "1989_japan",
        "year": 1989,
        "round": 15,
        "circuit_id": "suzuka",
        "race_name": "Japanese Grand Prix (Suzuka)",
        "keywords": ["1989 japan", "1989 japanese", "senna disqualified", "senna prost collision", "chicane", "balestre"],
        "title": "1989 Japanese Grand Prix — The Suzuka Chicane Collision & Senna Disqualification",
        "summary": (
            "The 1989 Japanese Grand Prix at Suzuka decided the World Championship in one of motorsport's most infamous controversies.\n\n"
            "• **The Collision**: On Lap 47 of 53, Ayrton Senna lunged down the inside of teammate Alain Prost heading into the Casio Triangle chicane. "
            "Prost turned in early, and the two McLaren-Hondas tangled with wheels interlocked, sliding into the escape road.\n"
            "• **Prost Abandons, Senna Continues**: Prost climbed out assuming the title was won. Senna waved over track marshals for a push-start, "
            "fired his Honda engine through the chicane runoff, pitted for a new nosecone, hunted down Alessandro Nannini, and took the chequered flag in P1.\n"
            "• **Controversial Disqualification**: FISA stewards (headed by French federation president Jean-Marie Balestre) disqualified Senna for "
            "'cutting the chicane' when returning to the track through the escape road. Nannini inherited victory and Prost was crowned 1989 World Champion."
        ),
        "metrics": [
            {"label": "Incident Lap", "value": "Lap 47 (Casio Chicane)", "color": "#E10600"},
            {"label": "Ruling", "value": "Senna Disqualified", "color": "#FFB703"},
            {"label": "Inherited Winner", "value": "Alessandro Nannini", "color": "#FFFFFF"},
            {"label": "1989 Champion", "value": "Alain Prost (McLaren)", "color": "#00F5D4"}
        ]
    },
    {
        "id": "1990_japan",
        "year": 1990,
        "round": 15,
        "circuit_id": "suzuka",
        "race_name": "Japanese Grand Prix (Suzuka)",
        "keywords": ["1990 japan", "1990 japanese", "turn 1 crash", "senna prost 1990", "senna revenge"],
        "title": "1990 Japanese Grand Prix — The 9-Second Turn 1 Title Collision",
        "summary": (
            "One year after their 1989 controversy, Ayrton Senna and Alain Prost (now at Ferrari) returned to Suzuka for another championship decider.\n\n"
            "• **The Pole Grid Controversy**: Senna qualified on pole but requested the FIA move pole position to the cleaner, grippier racing line on the left. "
            "Balestre refused, forcing Senna onto the dirty side of the track.\n"
            "• **The 250 km/h Collision**: Prost predictably launched better off the line. Into Turn 1, Senna refused to yield, keeping his foot planted and "
            "ramming the rear-quarter of Prost's Ferrari at 250 km/h. Both cars careened through the gravel trap into the tyre wall.\n"
            "• **Instant Title**: With both drivers eliminated 9 seconds into the race, Senna mathematically clinched his 2nd World Championship."
        ),
        "metrics": [
            {"label": "Race Elapsed", "value": "9.2 Seconds", "color": "#E10600"},
            {"label": "Impact Speed", "value": "250 km/h (Turn 1)", "color": "#FFB703"},
            {"label": "1990 Champion", "value": "Ayrton Senna", "color": "#00F5D4"},
            {"label": "Benetton 1-2", "value": "Piquet / Moreno", "color": "#FFFFFF"}
        ]
    },
    {
        "id": "1976_japan",
        "year": 1976,
        "round": 16,
        "circuit_id": "fuji",
        "race_name": "Japanese Grand Prix (Fuji Speedway)",
        "keywords": ["1976 japan", "1976 japanese", "hunt lauda 1976", "lauda withdrew", "rush f1", "fuji 1976"],
        "title": "1976 Japanese Grand Prix — The Monsoon Title Decider at Mount Fuji",
        "summary": (
            "The finale of the legendary 1976 season between Niki Lauda (Ferrari) and James Hunt (McLaren) at Fuji Speedway under torrential rain.\n\n"
            "• **Lauda's Courageous Withdrawal**: Just 6 weeks after surviving his near-fatal fireball crash at the Nürburgring, Lauda withdrew after Lap 2, "
            "stating: 'My life is worth more than a title. Under these conditions, it is insane to race.'\n"
            "• **Hunt's Heart-Stopping Charge**: Hunt needed P3 to win the championship. Leading initially, his wet tyres blistered as the track dried. "
            "He pitted late for fresh tyres dropping to P5, then mounted a ferocious charge in the dying laps to pass Alan Jones and Clay Regazzoni for P3, "
            "winning the World Championship by a solitary point (69 to 68)."
        ),
        "metrics": [
            {"label": "1976 Champion", "value": "James Hunt (69 pts)", "color": "#00F5D4"},
            {"label": "Title Margin", "value": "1 Point over Lauda", "color": "#FFB703"},
            {"label": "Lauda Exit", "value": "Lap 2 (Safety grounds)", "color": "#E10600"},
            {"label": "Race Winner", "value": "Mario Andretti (Lotus)", "color": "#FFFFFF"}
        ]
    },
    {
        "id": "1998_spa",
        "year": 1998,
        "round": 13,
        "circuit_id": "spa",
        "race_name": "Belgian Grand Prix (Spa-Francorchamps)",
        "keywords": ["1998 spa", "1998 belgian", "coulthard schumacher", "13 car crash", "jordan 1-2", "damon hill 1998"],
        "title": "1998 Belgian Grand Prix — Torrential Carnage & The Pit Lane Confrontation",
        "summary": (
            "The 1998 Belgian Grand Prix at Spa remains one of the most dramatic races in history.\n\n"
            "• **13-Car Lap 1 Pile-Up**: David Coulthard lost control on the damp descent after La Source, triggering a catastrophic 13-car chain-reaction "
            "that littered the circuit with over $10 million in carbon fibre wreckage, forcing a red flag.\n"
            "• **Schumacher vs Coulthard**: In torrential rain, Michael Schumacher led comfortably by 40 seconds. Approaching Coulthard to lap him on Lap 25, "
            "Coulthard eased off on the racing line in blinding spray. Schumacher unsighted rammed into the McLaren's rear, tearing off his right-front wheel.\n"
            "• **Pit Lane Fury**: Schumacher drove the 3-wheeled Ferrari into the pits and stormed into the McLaren garage shouting 'Are you trying to kill me?!' "
            "Damon Hill and Ralf Schumacher went on to score an emotional maiden 1-2 finish for Eddie Jordan's team."
        ),
        "metrics": [
            {"label": "Lap 1 Crash", "value": "13 Cars Eliminated", "color": "#E10600"},
            {"label": "Winner", "value": "Damon Hill (Jordan)", "color": "#FFD100"},
            {"label": "Maiden Win", "value": "Jordan Grand Prix 1-2", "color": "#00F5D4"},
            {"label": "Incident Lap", "value": "Lap 25 (Schumacher DNF)", "color": "#FFB703"}
        ]
    },
    {
        "id": "2021_abu_dhabi",
        "year": 2021,
        "round": 22,
        "circuit_id": "yas_marina",
        "race_name": "Abu Dhabi Grand Prix (Yas Marina)",
        "keywords": ["2021 abu dhabi", "2021 yas marina", "latifi crash", "verstappen hamilton final lap", "michael masi", "safety car 2021"],
        "title": "2021 Abu Dhabi Grand Prix — The Final-Lap Championship Shootout",
        "summary": (
            "Lewis Hamilton and Max Verstappen entered the 2021 season finale tied on 369.5 points after 21 epic rounds.\n\n"
            "• **The Race Lead**: Hamilton led dominant from the start and held an 11-second advantage with 5 laps remaining.\n"
            "• **The Turning Point**: On Lap 53, Nicholas Latifi crashed his Williams at Turn 14, bringing out the Safety Car. "
            "Red Bull immediately pitted Verstappen for fresh soft tyres, while Mercedes left Hamilton on 40-lap old hard tyres to protect track position.\n"
            "• **Race Director Controversy**: Race Director Michael Masi permitted only the 5 lapped cars between Hamilton and Verstappen to unlap themselves, "
            "calling the Safety Car in immediately for a 1-lap green flag shootout. On Lap 58, Verstappen lunged down the inside at Turn 5 to win the race "
            "and claim his maiden World Championship."
        ),
        "metrics": [
            {"label": "Safety Car Lap", "value": "Lap 53 (Latifi Crash)", "color": "#E10600"},
            {"label": "Pass Lap", "value": "Lap 58 / Turn 5", "color": "#00F5D4"},
            {"label": "2021 Champion", "value": "Max Verstappen (395.5 pts)", "color": "#FFB703"},
            {"label": "Pre-Race Points", "value": "369.5 Tied", "color": "#FFFFFF"}
        ]
    },
    {
        "id": "1988_monza",
        "year": 1988,
        "round": 12,
        "circuit_id": "monza",
        "race_name": "Italian Grand Prix (Monza)",
        "keywords": ["1988 monza", "1988 italian", "schlesser senna", "ferrari 1-2 1988", "enzo ferrari death", "mclaren clean sweep"],
        "title": "1988 Italian Grand Prix — Ferrari's Emotional 1-2 After Enzo's Passing",
        "summary": (
            "McLaren-Honda had won every single race of the 1988 season (11 out of 11) heading into Monza.\n\n"
            "• **Enzo's Passing**: Ferrari founder Enzo Ferrari had passed away just three weeks earlier at age 90, casting an emotional atmosphere over Monza.\n"
            "• **The Chicane Clash**: Alain Prost retired on Lap 34 with engine failure. Ayrton Senna was cruising to victory with a commanding lead with 2 laps to go. "
            "On Lap 49, attempting to lap Jean-Louis Schlesser's Williams at the Rettifilo chicane, Schlesser locked up and went wide. As Senna cut past, "
            "Schlesser came back across the kerb, clashing wheels and beaching Senna's McLaren on the kerbing.\n"
            "• **Tifosi Ecstasy**: Gerhard Berger and Michele Alboreto crossed the line for an unforgettable Ferrari 1-2 finish — McLaren's only defeat of 1988."
        ),
        "metrics": [
            {"label": "Incident Lap", "value": "Lap 49 / 51", "color": "#E10600"},
            {"label": "Ferrari Finish", "value": "Berger P1, Alboreto P2", "color": "#E10600"},
            {"label": "McLaren 1988 Record", "value": "15 Wins in 16 Races", "color": "#FFB703"},
            {"label": "Circuit", "value": "Autodromo di Monza", "color": "#FFFFFF"}
        ]
    },
    {
        "id": "2008_singapore",
        "year": 2008,
        "round": 15,
        "circuit_id": "marina_bay",
        "race_name": "Singapore Grand Prix (Marina Bay)",
        "keywords": ["2008 singapore", "crashgate", "piquet crash", "briatore", "alonso singapore 2008"],
        "title": "2008 Singapore Grand Prix — The 'Crashgate' Scandal",
        "summary": (
            "The inaugural Formula 1 night race at Marina Bay became the center of one of the biggest sporting scandals in history — known as 'Crashgate'.\n\n"
            "• **The Setup**: Fernando Alonso started P15 after a fuel pump failure in qualifying. Renault put him on an aggressive ultra-short fuel load, "
            "boxing him on Lap 12.\n"
            "• **The Deliberate Crash**: On Lap 14, teammate Nelson Piquet Jr deliberately crashed his Renault into the barrier at Turn 17, where no crane was available. "
            "Under the 2008 regulations, the pit lane was closed when the Safety Car deployed, forcing the leaders to wait or take penalties.\n"
            "• **Alonso Takes Victory**: Alonso inherited the lead as rivals pitted later, winning the race. The deliberate conspiracy was exposed by Piquet in 2009, "
            "leading to lifetime bans (later overturned) for Flavio Briatore and Pat Symonds."
        ),
        "metrics": [
            {"label": "Crash Lap", "value": "Lap 14 (Turn 17)", "color": "#E10600"},
            {"label": "Winner", "value": "Fernando Alonso (P15 → P1)", "color": "#00F5D4"},
            {"label": "Investigation", "value": "FIA World Motor Sport Council", "color": "#FFB703"},
            {"label": "Historical Event", "value": "First Ever Night Race", "color": "#FFFFFF"}
        ]
    },
    {
        "id": "2005_usa",
        "year": 2005,
        "round": 9,
        "circuit_id": "indianapolis",
        "race_name": "United States Grand Prix (Indianapolis)",
        "keywords": ["2005 usa", "2005 united states", "2005 indianapolis", "6 car race", "michelin boycott", "michelin tyre failure"],
        "title": "2005 United States Grand Prix — The 6-Car Michelin Tyre Boycott",
        "summary": (
            "One of the most surreal and controversial days in modern motorsport history at the Indianapolis Motor Speedway.\n\n"
            "• **The Tyre Failures**: During Friday practice, Ralf Schumacher suffered a massive 300 km/h crash at the high-speed banked Turn 13 due to a "
            "sidewall failure on his Michelin tyre. Michelin stated their tyres could not safely survive the banked turn without a chicane.\n"
            "• **The FIA Stand-Off**: FIA President Max Mosley refused to modify the circuit layout or add a temporary chicane, citing safety and sporting fairness.\n"
            "• **The Formation Lap Boycott**: All 14 Michelin-shod cars completed the formation lap to avoid sporting penalties, then peeled into the pit lane to retire. "
            "Only the 6 Bridgestone-shod cars (Ferrari, Jordan, Minardi) took the start. Michael Schumacher won ahead of Rubens Barrichello and Tiago Monteiro."
        ),
        "metrics": [
            {"label": "Starting Cars", "value": "6 Cars (Bridgestone only)", "color": "#E10600"},
            {"label": "Boycotting Cars", "value": "14 Cars (Michelin)", "color": "#FFB703"},
            {"label": "Winner", "value": "Michael Schumacher (Ferrari)", "color": "#00F5D4"},
            {"label": "First Podium", "value": "Tiago Monteiro (Jordan P3)", "color": "#FFFFFF"}
        ]
    }
]


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
