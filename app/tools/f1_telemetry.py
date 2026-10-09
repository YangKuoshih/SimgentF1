"""
SimGent - Telemetry, Multi-Circuit & Historical Analytics Data Engine
Provides access to OpenF1 API, circuit geometries, Race Control events (SC/VSC/Flags/Crashes),
WDC/WCC Championship standings, and F1 Technical Regulations Era comparisons.
"""

import os
import json
import math
import urllib.request
from typing import Dict, List, Any, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# -------------------------------------------------------------
# Team-inspired colors (hex codes)
# -------------------------------------------------------------
TEAM_LIVERIES = {
    "Red Bull Racing": {"primary": "#3671C6", "secondary": "#FFD700", "accent": "#E10600", "text": "#FFFFFF"},
    "McLaren": {"primary": "#FF8000", "secondary": "#47C7FC", "accent": "#1A1A1A", "text": "#000000"},
    "Ferrari": {"primary": "#E80020", "secondary": "#FFFFFF", "accent": "#FFF200", "text": "#FFFFFF"},
    "Mercedes": {"primary": "#27F4D2", "secondary": "#C0C0C0", "accent": "#000000", "text": "#000000"},
    "Aston Martin": {"primary": "#229971", "secondary": "#CEDC00", "accent": "#00594F", "text": "#FFFFFF"},
    "Alpine": {"primary": "#0090FF", "secondary": "#FF87BC", "accent": "#0A1128", "text": "#FFFFFF"},
    "Williams": {"primary": "#64C4FF", "secondary": "#041E42", "accent": "#FFFFFF", "text": "#FFFFFF"},
    "RB": {"primary": "#6692FF", "secondary": "#FFFFFF", "accent": "#E80020", "text": "#FFFFFF"},
    "Kick Sauber": {"primary": "#52E252", "secondary": "#1E1E1E", "accent": "#FFFFFF", "text": "#000000"},
    "Haas F1 Team": {"primary": "#B6BABD", "secondary": "#E80020", "accent": "#1E1E1E", "text": "#000000"},
    "Audi F1 Team": {"primary": "#E21B23", "secondary": "#1E1E1E", "accent": "#FFFFFF", "text": "#FFFFFF"},
    "Cadillac F1": {"primary": "#C59B27", "secondary": "#0A0A0A", "accent": "#FFFFFF", "text": "#FFFFFF"}
}

# -------------------------------------------------------------
# Circuit Blueprints & Spline Generators
# -------------------------------------------------------------
TRACK_BLUEPRINTS = {
    "silverstone": {
        "name": "Silverstone Circuit",
        "country": "Great Britain",
        "country_code": "GBR",
        "length_km": 5.891,
        "turns_count": 18,
        "lap_record": "1:27.097 (M. Verstappen, 2020)",
        "full_throttle_pct": 78,
        "tyre_stress": "Level 5/5",
        "pit_loss_s": 19.8,
        "turns": [
            {"number": 1, "name": "Abbey", "type": "High Speed Right"},
            {"number": 3, "name": "Village", "type": "Hairpin Right"},
            {"number": 4, "name": "The Loop", "type": "Hairpin Left"},
            {"number": 6, "name": "Brooklands", "type": "Medium Left"},
            {"number": 7, "name": "Luffield", "type": "Carousel Right"},
            {"number": 9, "name": "Copse", "type": "Ultra High Speed Right"},
            {"number": 10, "name": "Maggotts", "type": "High Speed Left"},
            {"number": 11, "name": "Becketts", "type": "High Speed Right"},
            {"number": 12, "name": "Chapel", "type": "High Speed Left"},
            {"number": 15, "name": "Stowe", "type": "Heavy Braking Right"},
            {"number": 16, "name": "Vale", "type": "Hard Left Chicane"},
            {"number": 18, "name": "Club", "type": "Medium Right Exit"}
        ]
    },
    "monaco": {
        "name": "Circuit de Monaco",
        "country": "Monaco",
        "country_code": "MCO",
        "length_km": 3.337,
        "turns_count": 19,
        "lap_record": "1:12.909 (L. Hamilton, 2021)",
        "full_throttle_pct": 45,
        "tyre_stress": "Level 1/5",
        "pit_loss_s": 22.1,
        "turns": [
            {"number": 1, "name": "Sainte Dévote", "type": "Tight Right"},
            {"number": 3, "name": "Massenet", "type": "Long Left"},
            {"number": 4, "name": "Casino Square", "type": "Blind Crest Right"},
            {"number": 5, "name": "Mirabeau", "type": "Downhill Right"},
            {"number": 6, "name": "Grand Hotel Hairpin", "type": "Slowest Hairpin (48 km/h)"},
            {"number": 8, "name": "Portier", "type": "Tunnel Entry Right"},
            {"number": 10, "name": "Nouvelle Chicane", "type": "Braking from Tunnel"},
            {"number": 12, "name": "Tabac", "type": "Fast Left"},
            {"number": 15, "name": "Swimming Pool", "type": "High Speed Chicane"},
            {"number": 18, "name": "La Rascasse", "type": "Tight Double Hairpin"}
        ]
    },
    "spa": {
        "name": "Circuit de Spa-Francorchamps",
        "country": "Belgium",
        "country_code": "BEL",
        "length_km": 7.004,
        "turns_count": 19,
        "lap_record": "1:46.286 (V. Bottas, 2018)",
        "full_throttle_pct": 72,
        "tyre_stress": "Level 5/5",
        "pit_loss_s": 20.4,
        "turns": [
            {"number": 1, "name": "La Source", "type": "Hairpin Right"},
            {"number": 2, "name": "Eau Rouge", "type": "Uphill Compression Left"},
            {"number": 4, "name": "Raidillon", "type": "Blind Crest Right"},
            {"number": 5, "name": "Les Combes", "type": "Heavy Braking Chicane"},
            {"number": 8, "name": "Bruxelles", "type": "Downhill Carousel"},
            {"number": 10, "name": "Pouhon", "type": "Double Apex Left (280 km/h)"},
            {"number": 16, "name": "Blanchimont", "type": "Flat Out Left (310 km/h)"},
            {"number": 19, "name": "Bus Stop Chicane", "type": "Right-Left Chicane"}
        ]
    },
    "monza": {
        "name": "Autodromo Nazionale Monza",
        "country": "Italy",
        "country_code": "ITA",
        "length_km": 5.793,
        "turns_count": 11,
        "lap_record": "1:21.046 (R. Barrichello, 2004)",
        "full_throttle_pct": 82,
        "tyre_stress": "Level 3/5",
        "pit_loss_s": 24.2,
        "turns": [
            {"number": 1, "name": "Prima Variante", "type": "Heavy Braking 350 -> 70 km/h"},
            {"number": 3, "name": "Curva Grande", "type": "Flat Out Sweeper"},
            {"number": 4, "name": "Variante della Roggia", "type": "Chicane Left-Right"},
            {"number": 6, "name": "Lesmo 1", "type": "Medium Right"},
            {"number": 7, "name": "Lesmo 2", "type": "Medium Right"},
            {"number": 8, "name": "Variante Ascari", "type": "High Speed Triple Chicane"},
            {"number": 11, "name": "Curva Parabolica", "type": "High Speed Radius Right"}
        ]
    },
    "miami": {
        "name": "Miami International Autodrome",
        "country": "United States",
        "country_code": "USA",
        "length_km": 5.412,
        "turns_count": 19,
        "lap_record": "1:29.708 (M. Verstappen, 2023)",
        "full_throttle_pct": 68,
        "tyre_stress": "Level 4/5",
        "pit_loss_s": 19.5,
        "turns": [
            {"number": 1, "name": "Turn 1", "type": "Heavy Braking Right"},
            {"number": 7, "name": "Marina Complex", "type": "S-curves"},
            {"number": 11, "name": "Turn 11", "type": "Left Entry onto Straight"},
            {"number": 14, "name": "Turn 14/15 Chicane", "type": "Slow Uphill Chicane"},
            {"number": 17, "name": "Turn 17 Hairpin", "type": "Heavy Braking Left"}
        ]
    },
    "bahrain": {
        "name": "Bahrain International Circuit",
        "country": "Bahrain",
        "country_code": "BHR",
        "length_km": 5.412,
        "turns_count": 15,
        "lap_record": "1:31.447 (P. de la Rosa, 2005)",
        "full_throttle_pct": 70,
        "tyre_stress": "Level 4/5",
        "pit_loss_s": 23.0,
        "turns": [
            {"number": 1, "name": "Turn 1 Michael Schumacher", "type": "Heavy Braking Right"},
            {"number": 4, "name": "Turn 4", "type": "Medium Right Exit"},
            {"number": 8, "name": "Turn 8", "type": "Hairpin Right"},
            {"number": 10, "name": "Turn 10", "type": "Tricky Off-Camber Downhill Left"},
            {"number": 12, "name": "Turn 12", "type": "Flat Out Sweeper"},
            {"number": 14, "name": "Turn 14/15", "type": "Final Corner Right"}
        ]
    },
    "austin": {
        "name": "Circuit of the Americas (COTA)",
        "country": "United States",
        "country_code": "USA",
        "length_km": 5.513,
        "turns_count": 20,
        "lap_record": "1:36.169 (C. Leclerc, 2019)",
        "full_throttle_pct": 67,
        "tyre_stress": "Level 4/5",
        "pit_loss_s": 20.8,
        "turns": [
            {"number": 1, "name": "Turn 1 Big Hill", "type": "Blind Uphill Left Hairpin"},
            {"number": 3, "name": "Turns 3-6 Esses", "type": "Maggotts/Becketts Style Flow"},
            {"number": 11, "name": "Turn 11", "type": "Hairpin onto Long Back Straight"},
            {"number": 12, "name": "Turn 12", "type": "Heavy Braking from 335 km/h"},
            {"number": 16, "name": "Turns 16-18 Carousel", "type": "Multi-Apex High Load Right"}
        ]
    },
    "interlagos": {
        "name": "Autódromo José Carlos Pace (Interlagos)",
        "country": "Brazil",
        "country_code": "BRA",
        "length_km": 4.309,
        "turns_count": 15,
        "lap_record": "1:10.540 (V. Bottas, 2018)",
        "full_throttle_pct": 71,
        "tyre_stress": "Level 3/5",
        "pit_loss_s": 21.2,
        "turns": [
            {"number": 1, "name": "Senna 'S'", "type": "Downhill Left-Right Drop"},
            {"number": 4, "name": "Descida do Lago", "type": "Heavy Braking Left"},
            {"number": 8, "name": "Ferradura", "type": "Uphill Double Right"},
            {"number": 10, "name": "Bico de Pato", "type": "Slow Hairpin Right"},
            {"number": 12, "name": "Mergulho", "type": "Fast Downhill Left"},
            {"number": 14, "name": "Junção", "type": "Crucial Traction Left onto Main Straight"}
        ]
    },
    "albert_park": {
        "name": "Albert Park Circuit",
        "country": "Australia",
        "country_code": "AUS",
        "length_km": 5.278,
        "turns_count": 14,
        "lap_record": "1:19.813 (C. Leclerc, 2024)",
        "full_throttle_pct": 72,
        "tyre_stress": "Level 3/5",
        "pit_loss_s": 20.4,
        "turns": [
            {"number": 1, "name": "Turn 1-2 Brabham", "type": "High Speed Chicane"},
            {"number": 6, "name": "Turn 6", "type": "Fast Apex Right"},
            {"number": 9, "name": "Turn 9-10 Lakeside Sweep", "type": "Flat Out Left-Right Sweep (300 km/h)"},
            {"number": 11, "name": "Turn 11-12", "type": "Heavy Braking Left-Right Chicane"},
            {"number": 13, "name": "Turn 13 Ascari", "type": "Tight Right onto Pit Entry"}
        ]
    },
    "suzuka": {
        "name": "Suzuka International Racing Course",
        "country": "Japan",
        "country_code": "JPN",
        "length_km": 5.807,
        "turns_count": 18,
        "lap_record": "1:30.983 (L. Hamilton, 2019)",
        "full_throttle_pct": 68,
        "tyre_stress": "Level 5/5",
        "pit_loss_s": 22.4,
        "turns": [
            {"number": 1, "name": "Turn 1-2", "type": "Double Apex High Speed Right"},
            {"number": 3, "name": "S-Curves (T3-T6)", "type": "High Lateral G Rhythm Flow"},
            {"number": 8, "name": "Degner 1 & 2", "type": "Fast Blind Right into 90-Deg Kerb"},
            {"number": 11, "name": "Hairpin", "type": "Heavy Braking Slow Hairpin"},
            {"number": 13, "name": "Spoon Curve", "type": "Double-Apex Left onto Back Straight"},
            {"number": 15, "name": "130R", "type": "Iconic Flat-Out 315 km/h Left"},
            {"number": 16, "name": "Casio Triangle", "type": "Tight Chicane before Pit Straight"}
        ]
    },
    "red_bull_ring": {
        "name": "Red Bull Ring (Spielberg)",
        "country": "Austria",
        "country_code": "AUT",
        "length_km": 4.318,
        "turns_count": 10,
        "lap_record": "1:05.619 (C. Sainz, 2020)",
        "full_throttle_pct": 77,
        "tyre_stress": "Level 3/5",
        "pit_loss_s": 19.2,
        "turns": [
            {"number": 1, "name": "Niki Lauda Kurve", "type": "Uphill 90-Deg Right"},
            {"number": 3, "name": "Remus Hairpin", "type": "Steep Uphill Tight Right (Best Overtaking)"},
            {"number": 4, "name": "Schlossgold", "type": "Downhill Medium Right"},
            {"number": 9, "name": "Jochen Rindt", "type": "Fast Downhill Right"},
            {"number": 10, "name": "Turn 10", "type": "Tricky Off-Camber Final Apex"}
        ]
    },
    "zandvoort": {
        "name": "Circuit Zandvoort",
        "country": "Netherlands",
        "country_code": "NLD",
        "length_km": 4.259,
        "turns_count": 14,
        "lap_record": "1:11.097 (L. Hamilton, 2021)",
        "full_throttle_pct": 65,
        "tyre_stress": "Level 4/5",
        "pit_loss_s": 20.1,
        "turns": [
            {"number": 1, "name": "Tarzanbocht", "type": "Famous Heavy Braking Right Hairpin"},
            {"number": 3, "name": "Hugenholtzbocht", "type": "19-Degree Progressive Banked Left"},
            {"number": 7, "name": "Scheivlak", "type": "Fast Blind Downhill Right"},
            {"number": 14, "name": "Arie Luyendykbocht", "type": "18-Degree Banked Parabolic Sweeper"}
        ]
    },
    "baku": {
        "name": "Baku City Circuit",
        "country": "Azerbaijan",
        "country_code": "AZE",
        "length_km": 6.003,
        "turns_count": 20,
        "lap_record": "1:43.009 (C. Leclerc, 2019)",
        "full_throttle_pct": 73,
        "tyre_stress": "Level 3/5",
        "pit_loss_s": 21.5,
        "turns": [
            {"number": 1, "name": "Turn 1", "type": "Heavy Braking from 345 km/h"},
            {"number": 8, "name": "Castle Section (T8-T11)", "type": "Narrow Medieval Street (7.6m Wide)"},
            {"number": 15, "name": "Turn 15", "type": "Downhill Blind Left into Barrier"},
            {"number": 16, "name": "Turn 16", "type": "Traction Exit onto 2.2km Flat-Out Straight"}
        ]
    },
    "jeddah": {
        "name": "Jeddah Corniche Circuit",
        "country": "Saudi Arabia",
        "country_code": "SAU",
        "length_km": 6.174,
        "turns_count": 27,
        "lap_record": "1:30.734 (L. Hamilton, 2021)",
        "full_throttle_pct": 79,
        "tyre_stress": "Level 4/5",
        "pit_loss_s": 21.0,
        "turns": [
            {"number": 1, "name": "Turns 1-2 Chicane", "type": "Tight Left-Right Hairpin"},
            {"number": 13, "name": "Turn 13 Banked Hairpin", "type": "12-Degree High Load Banked Left"},
            {"number": 22, "name": "Turns 22-24 Esses", "type": "High Speed 260 km/h Chicane"},
            {"number": 27, "name": "Turn 27", "type": "Heavy Braking Hairpin onto Main Straight"}
        ]
    },
    "yas_marina": {
        "name": "Yas Marina Circuit",
        "country": "Abu Dhabi (UAE)",
        "country_code": "UAE",
        "length_km": 5.281,
        "turns_count": 16,
        "lap_record": "1:26.103 (M. Verstappen, 2021)",
        "full_throttle_pct": 64,
        "tyre_stress": "Level 3/5",
        "pit_loss_s": 21.6,
        "turns": [
            {"number": 5, "name": "Turn 5 Hairpin", "type": "Heavy Braking onto 1.2km Back Straight"},
            {"number": 9, "name": "Turn 9 Marsa", "type": "Fast Sweeping Banked Left"},
            {"number": 12, "name": "Hotel Complex (T12-T15)", "type": "Flowing Technical Marina Turns"}
        ]
    },
    "villeneuve": {
        "name": "Circuit Gilles-Villeneuve (Montreal)",
        "country": "Canada",
        "country_code": "CAN",
        "length_km": 4.361,
        "turns_count": 14,
        "lap_record": "1:13.078 (V. Bottas, 2019)",
        "full_throttle_pct": 65,
        "tyre_stress": "Level 4/5",
        "pit_loss_s": 20.0,
        "turns": [
            {"number": 1, "name": "Senna 'S'", "type": "Tight Downhill Left-Right"},
            {"number": 10, "name": "L'Epingle Hairpin", "type": "Heavy Braking 180-Deg Hairpin"},
            {"number": 13, "name": "Wall of Champions (T13-14)", "type": "Aggressive Kerb Chicane into Wall"}
        ]
    },
    "sepang": {
        "name": "Sepang International Circuit",
        "country": "Malaysia",
        "country_code": "MYS",
        "length_km": 5.543,
        "turns_count": 15,
        "lap_record": "1:34.080 (S. Vettel, 2017)",
        "full_throttle_pct": 70,
        "tyre_stress": "Level 4/5",
        "pit_loss_s": 22.1,
        "turns": [
            {"number": 1, "name": "Turn 1-2 Chicane", "type": "Heavy Braking Right-Left Drop"},
            {"number": 4, "name": "Turn 4", "type": "Sweeping Off-Camber Right"},
            {"number": 7, "name": "Turn 7-8 S-Bends", "type": "High Speed Lateral Flow"},
            {"number": 9, "name": "Turn 9 Berkembar", "type": "Uphill Tight Left Hairpin"},
            {"number": 14, "name": "Turn 14", "type": "Crucial Traction onto Back Straight"},
            {"number": 15, "name": "Turn 15 Sunway Hairpin", "type": "Wide Radius Final Hairpin onto Pit Straight"}
        ]
    }
}

# -------------------------------------------------------------
# F1 Technical Regulations & Power Unit Era Matrix
# -------------------------------------------------------------
F1_REGULATIONS_ERAS = [
    {
        "era_id": "2026",
        "title": "2026 Active Aero & 50/50 Hybrid Era",
        "years": "2026+",
        "engine_type": "1.6L V6 Turbo Hybrid (100% Sustainable Fuel)",
        "ice_power_hp": 535,
        "electric_power_hp": 470,
        "electric_kw": 350,
        "total_hp": 1005,
        "downforce_concept": "Active Aerodynamics (Z-mode cornering / X-mode low-drag straights)",
        "energy_balance": "50% ICE / 50% Electrical (350kW MGU-K, MGU-H eliminated)",
        "key_innovations": [
            "Manual Overtake Mode (MOM) providing electrical overrides up to 337 km/h",
            "Elimination of expensive MGU-H for cost reduction & manufacturer entry (Audi, Ford)",
            "100% drop-in sustainable advanced synthetic bio-fuel",
            "Narrower track (1900mm) and 30kg lighter minimum car weight"
        ],
        "ai_analysis": "The 2026 regulations shift tactical focus to energy management. Drivers can no longer harvest infinitely from exhaust gases (no MGU-H), making aggressive regenerative braking and tactical electrical deployment crucial for overtaking."
    },
    {
        "era_id": "2022_2025",
        "title": "2022–2025 Ground Effect Era",
        "years": "2022–2025",
        "engine_type": "1.6L V6 Turbo Hybrid + E10 Fuel",
        "ice_power_hp": 840,
        "electric_power_hp": 160,
        "electric_kw": 120,
        "total_hp": 1000,
        "downforce_concept": "Venturi Tunnel Underfloor Ground Effect",
        "energy_balance": "84% ICE / 16% Electrical (120kW MGU-K + continuous MGU-H)",
        "key_innovations": [
            "Venturi floor tunnels creating downforce with minimal dirty air wake",
            "18-inch low-profile Pirelli tires reducing sidewall flex",
            "Simplified front wing cascades to enable close following within 1 second",
            "Thermal efficiency exceeding 52% in Mercedes, Ferrari, and Honda PUs"
        ],
        "ai_analysis": "Ground effect dramatically improved close wheel-to-wheel battles in high-speed corners like Becketts and Pouhon, though stiff suspensions made curb-riding harsher and porpoising a key setup hurdle."
    },
    {
        "era_id": "2014_2021",
        "title": "2014–2021 Turbo Hybrid Era",
        "years": "2014–2021",
        "engine_type": "1.6L 90° V6 Single Turbo Hybrid",
        "ice_power_hp": 800,
        "electric_power_hp": 160,
        "electric_kw": 120,
        "total_hp": 960,
        "downforce_concept": "Complex Over-body Vortex Aerodynamics & Front Wing Cascades",
        "energy_balance": "80% ICE / 20% Electrical",
        "key_innovations": [
            "Introduction of dual ERS: MGU-K (kinetic) + MGU-H (heat turbo)",
            "100 kg/hr strict fuel flow limiter",
            "2017 high-downforce wide-track evolution creating all-time track records"
        ],
        "ai_analysis": "The pinnacle of raw cornering grip and thermal engine efficiency. However, intense aerodynamic wake ('dirty air') made overtaking difficult without large tire degradation deltas or DRS assistance."
    },
    {
        "era_id": "2006_2013",
        "title": "2006–2013 V8 Screamer Era",
        "years": "2006–2013",
        "engine_type": "2.4L 90° Naturally Aspirated V8",
        "ice_power_hp": 750,
        "electric_power_hp": 80,
        "electric_kw": 60,
        "total_hp": 810,
        "downforce_concept": "High-rake Blown Diffusers (Red Bull/Newey) & Beam Wings",
        "energy_balance": "90% ICE / 10% KERS Battery Boost (introduced 2009)",
        "key_innovations": [
            "18,000 RPM rev limiters producing iconic acoustic scream",
            "KERS (Kinetic Energy Recovery System) push-to-pass button (60kW for 6.6s/lap)",
            "DRS (Drag Reduction System) introduced in 2011 to encourage overtaking"
        ],
        "ai_analysis": "Famous for tight championship battles and Red Bull's blown diffuser innovation, channeling exhaust gases through the floor to generate artificial downforce off-throttle."
    },
    {
        "era_id": "1995_2005",
        "title": "1995–2005 V10 Golden Era",
        "years": "1995–2005",
        "engine_type": "3.0L Naturally Aspirated V10",
        "ice_power_hp": 950,
        "electric_power_hp": 0,
        "electric_kw": 0,
        "total_hp": 950,
        "downforce_concept": "High-downforce stepped floor, grooved tires, traction control",
        "energy_balance": "100% Pure Chemical ICE (Zero Hybrid)",
        "key_innovations": [
            "20,000+ RPM shrieking engines (BMW P84/P85, Ferrari 053)",
            "In-race refueling fueling aggressive sprint qualifying stints",
            "Lightweight chassis (~600 kg with driver)",
            "Tire wars between Bridgestone and Michelin"
        ],
        "ai_analysis": "Raw mechanical velocity and qualifying lap records that stood for decades. In-race refueling meant drivers executed multiple 100% flat-out sprint stints rather than conserving tires."
    },
    {
        "era_id": "1980s",
        "title": "1980s 1400hp Turbo Monster Era",
        "years": "1977–1988",
        "engine_type": "1.5L Turbocharged Inline-4 & V6",
        "ice_power_hp": 1400,
        "electric_power_hp": 0,
        "electric_kw": 0,
        "total_hp": 1400,
        "downforce_concept": "Early ground-effect skirts followed by flat floors and giant wings",
        "energy_balance": "100% ICE",
        "key_innovations": [
            "BMW M12/13 and Honda RA168E reaching over 5.5 bar boost in qualifying",
            "Manual H-pattern gearboxes and mechanical clutches with high turbo lag"
        ],
        "ai_analysis": "The most extreme horsepower-to-weight ratio in motorsport history. Massive turbo lag meant drivers had to step on the throttle before entering the corner to have power on exit."
    },
    {
        "era_id": "1960s",
        "title": "1960s Classic DFV Era",
        "years": "1960–1969",
        "engine_type": "1.5L / 3.0L Naturally Aspirated (Ford Cosworth DFV)",
        "ice_power_hp": 410,
        "electric_power_hp": 0,
        "electric_kw": 0,
        "total_hp": 410,
        "downforce_concept": "Cigar-tube monocoque with zero aerodynamic wings",
        "energy_balance": "100% ICE",
        "key_innovations": [
            "Lotus 25/49 aluminum monocoque chassis",
            "Cosworth DFV stressed-member engine bolted directly to chassis",
            "Pure mechanical grip on treaded bias-ply tires"
        ],
        "ai_analysis": "Aerodynamic drag was minimal, allowing long four-wheel drifts and drafting slipstreams down every straight. Reliability and driver courage dictated the race result."
    }
]

# -------------------------------------------------------------
# 2024 Season Championship Standings (WDC & WCC)
# -------------------------------------------------------------
STANDINGS_2024 = {
    "drivers": [
        {"rank": 1, "driver": "Max Verstappen", "acronym": "VER", "team": "Red Bull Racing", "color": "#3671C6", "points": 437, "wins": 9, "podiums": 14},
        {"rank": 2, "driver": "Lando Norris", "acronym": "NOR", "team": "McLaren", "color": "#FF8000", "points": 374, "wins": 3, "podiums": 12},
        {"rank": 3, "driver": "Charles Leclerc", "acronym": "LEC", "team": "Ferrari", "color": "#E80020", "points": 356, "wins": 3, "podiums": 13},
        {"rank": 4, "driver": "Oscar Piastri", "acronym": "PIA", "team": "McLaren", "color": "#FF8000", "points": 292, "wins": 2, "podiums": 9},
        {"rank": 5, "driver": "Carlos Sainz", "acronym": "SAI", "team": "Ferrari", "color": "#E80020", "points": 290, "wins": 2, "podiums": 9},
        {"rank": 6, "driver": "George Russell", "acronym": "RUS", "team": "Mercedes", "color": "#27F4D2", "points": 245, "wins": 2, "podiums": 4},
        {"rank": 7, "driver": "Lewis Hamilton", "acronym": "HAM", "team": "Mercedes", "color": "#27F4D2", "points": 223, "wins": 2, "podiums": 4},
        {"rank": 8, "driver": "Sergio Perez", "acronym": "PER", "team": "Red Bull Racing", "color": "#3671C6", "points": 152, "wins": 0, "podiums": 4},
        {"rank": 9, "driver": "Fernando Alonso", "acronym": "ALO", "team": "Aston Martin", "color": "#229971", "points": 70, "wins": 0, "podiums": 0},
        {"rank": 10, "driver": "Pierre Gasly", "acronym": "GAS", "team": "Alpine", "color": "#FF87BC", "points": 42, "wins": 0, "podiums": 1}
    ],
    "constructors": [
        {"rank": 1, "team": "McLaren", "color": "#FF8000", "points": 666, "wins": 5, "podiums": 21, "status": "Champions"},
        {"rank": 2, "team": "Ferrari", "color": "#E80020", "points": 652, "wins": 5, "podiums": 22, "status": "Runner-Up (-14 pts)"},
        {"rank": 3, "team": "Red Bull Racing", "color": "#3671C6", "points": 589, "wins": 9, "podiums": 18, "status": "P3 (-77 pts)"},
        {"rank": 4, "team": "Mercedes", "color": "#27F4D2", "points": 468, "wins": 4, "podiums": 8, "status": "P4"},
        {"rank": 5, "team": "Aston Martin", "color": "#229971", "points": 94, "wins": 0, "podiums": 0, "status": "P5"},
        {"rank": 6, "team": "Alpine", "color": "#FF87BC", "points": 65, "wins": 0, "podiums": 2, "status": "P6"}
    ]
}

# -------------------------------------------------------------
# 2026 Season Championship Standings (Active Aero / 50-50 Hybrid Era)
# -------------------------------------------------------------
STANDINGS_2026 = {
    "drivers": [
        {"rank": 1, "driver": "Max Verstappen", "acronym": "VER", "team": "Red Bull-Ford", "color": "#3671C6", "points": 312, "wins": 7, "podiums": 12},
        {"rank": 2, "driver": "Charles Leclerc", "acronym": "LEC", "team": "Ferrari", "color": "#E80020", "points": 298, "wins": 5, "podiums": 11},
        {"rank": 3, "driver": "Lewis Hamilton", "acronym": "HAM", "team": "Ferrari", "color": "#E80020", "points": 274, "wins": 4, "podiums": 10},
        {"rank": 4, "driver": "Lando Norris", "acronym": "NOR", "team": "McLaren", "color": "#FF8000", "points": 268, "wins": 3, "podiums": 9},
        {"rank": 5, "driver": "George Russell", "acronym": "RUS", "team": "Mercedes", "color": "#27F4D2", "points": 220, "wins": 2, "podiums": 6},
        {"rank": 6, "driver": "Kimi Antonelli", "acronym": "ANT", "team": "Mercedes", "color": "#27F4D2", "points": 142, "wins": 1, "podiums": 3},
        {"rank": 7, "driver": "Nico Hulkenberg", "acronym": "HUL", "team": "Audi F1 Team", "color": "#E21B23", "points": 88, "wins": 0, "podiums": 2},
        {"rank": 8, "driver": "Carlos Sainz", "acronym": "SAI", "team": "Williams", "color": "#64C4FF", "points": 84, "wins": 0, "podiums": 1},
        {"rank": 9, "driver": "Fernando Alonso", "acronym": "ALO", "team": "Aston Martin", "color": "#229971", "points": 68, "wins": 0, "podiums": 1},
        {"rank": 10, "driver": "Gabriel Bortoleto", "acronym": "BOR", "team": "Audi F1 Team", "color": "#E21B23", "points": 36, "wins": 0, "podiums": 0}
    ],
    "constructors": [
        {"rank": 1, "team": "Ferrari", "color": "#E80020", "points": 572, "wins": 9, "podiums": 21, "status": "Leading Championship"},
        {"rank": 2, "team": "Red Bull-Ford", "color": "#3671C6", "points": 486, "wins": 7, "podiums": 15, "status": "P2 (-86 pts)"},
        {"rank": 3, "team": "McLaren", "color": "#FF8000", "points": 435, "wins": 4, "podiums": 14, "status": "P3"},
        {"rank": 4, "team": "Mercedes", "color": "#27F4D2", "points": 362, "wins": 3, "podiums": 9, "status": "P4"},
        {"rank": 5, "team": "Audi F1 Team", "color": "#E21B23", "points": 124, "wins": 0, "podiums": 2, "status": "Debut Season P5"},
        {"rank": 6, "team": "Williams", "color": "#64C4FF", "points": 108, "wins": 0, "podiums": 1, "status": "P6"}
    ]
}

# -------------------------------------------------------------
# Detailed Race Control Incidents & Safety Car Catalog
# -------------------------------------------------------------
RACE_CONTROL_EVENTS = {
    # Silverstone 2024
    9558: [
        {"lap": 1, "flag": "GREEN", "type": "FLAG", "message": "GREEN LIGHT - PIT EXIT OPEN", "consequence": "Clean race start under overcast skies."},
        {"lap": 19, "flag": "YELLOW", "type": "LOW_GRIP", "message": "LOW GRIP CONDITIONS - RAIN ARRIVING AT COPSE", "consequence": "DRS Disabled. Hamilton and Norris overtake Russell as track surface wets."},
        {"lap": 27, "flag": "YELLOW", "type": "INCIDENT", "message": "TRACK SURFACE SLIPPERY SECTOR 2 & 3", "consequence": "Norris leads, McLaren delays switch to Inters by 1 lap."},
        {"lap": 34, "flag": "GREEN", "type": "PIT_WINDOW", "message": "TRACK DRYING - SLICK CROSSOVER THRESHOLD APPROACHING", "consequence": "Critical pit window opens. Hamilton boxes on Lap 38 for softs, undercut successful."},
        {"lap": 48, "flag": "GREEN", "type": "BATTLE", "message": "VERSTAPPEN ON HARD TYRES PASSING NORRIS FOR P2", "consequence": "Verstappen closes within 1.4s of Hamilton at the checkered flag."}
    ],
    # Miami 2024 (Maiden Norris win via Safety Car)
    9507: [
        {"lap": 1, "flag": "YELLOW", "type": "INCIDENT", "message": "TURN 1 INCIDENT INVOLVING CAR 11 (PEREZ)", "consequence": "Perez lockup, Verstappen escapes into lead."},
        {"lap": 23, "flag": "YELLOW", "type": "VSC", "message": "VIRTUAL SAFETY CAR DEPLOYED - DEBRIS TURN 15", "consequence": "Brief VSC window, pit loss reduced to 9.2s."},
        {"lap": 28, "flag": "YELLOW", "type": "SAFETY_CAR", "message": "SAFETY CAR DEPLOYED - COLLISION CAR 20 (MAG) AND CAR 2 (SAR)", "consequence": "CRITICAL TURNING POINT: Norris was leading and hadn't pitted. Took pit stop under SC, emerged P1 ahead of Verstappen!"},
        {"lap": 32, "flag": "GREEN", "type": "RESTART", "message": "SAFETY CAR IN THIS LAP - RACE RESTART", "consequence": "Norris defends on restart and pulls a 7.6-second gap to take maiden F1 victory."}
    ],
    # Monaco 2024 (Red flag lap 1 crash)
    9523: [
        {"lap": 1, "flag": "RED", "type": "RED_FLAG", "message": "RED FLAG - MASSIVE COLLISION BEAU RIVAGE (PEREZ, MAGNUSSEN, HULKENBERG)", "consequence": "Severe crash damages barriers. All drivers get a free tire change during the 40-minute stoppage, cementing Leclerc's home victory."},
        {"lap": 1, "flag": "GREEN", "type": "RESTART", "message": "STANDING RESTART LAP 1", "consequence": "Leclerc leads Piastri and Sainz in processional pace management to the finish."}
    ],
    # Spa 2024 (Russell 1-stop disqualification & Hamilton win)
    9574: [
        {"lap": 1, "flag": "GREEN", "type": "START", "message": "CLEAN START AT LA SOURCE", "consequence": "Hamilton overtakes Perez for P2."},
        {"lap": 11, "flag": "GREEN", "type": "PIT_CYCLE", "message": "HAMILTON BOXES FOR HARD TYRES", "consequence": "Russell commits to bold 1-stop strategy, holding off Hamilton in the closing 5 laps."},
        {"lap": 44, "flag": "CHEQUERED", "type": "FINISH", "message": "RUSSELL WINS ON TRACK - LATER DISQUALIFIED UNDERWEIGHT", "consequence": "Hamilton awarded victory after Russell's car was found 1.5kg underweight post-race."}
    ],
    # Monza 2024 (Leclerc Ferrari 1-stop triumph)
    9590: [
        {"lap": 1, "flag": "GREEN", "type": "START", "message": "PIASTRI OVERTAKES NORRIS AT VARIANTE DELLA ROGGIA", "consequence": "Aggressive McLaren move opens door for Leclerc to pass Norris into P2."},
        {"lap": 38, "flag": "GREEN", "type": "STRATEGY", "message": "MCLAREN 2-STOP VS FERRARI 1-STOP GAMBLE", "consequence": "Leclerc nurtures front-left hard tyre over 38-lap stint, winning in front of the Tifosi by 2.6s!"}
    ],
    # 2026 Season Opener - Bahrain (Hamilton Ferrari Debut & Active Aero debut)
    9801: [
        {"lap": 1, "flag": "GREEN", "type": "START", "message": "INAUGURAL 2026 ACTIVE AERO START - LEWIS HAMILTON DEBUTS IN SCUDERIA FERRARI", "consequence": "Drivers deploy low-drag X-mode on straight. Hamilton vaults past Norris into Turn 1."},
        {"lap": 18, "flag": "YELLOW", "type": "VSC", "message": "VIRTUAL SAFETY CAR - AUDI F1 RECOVERY (BORTOLETO MGU-K ISOLATION)", "consequence": "Audi power unit software failsafe. Teams trigger manual energy recharge cycles."},
        {"lap": 32, "flag": "YELLOW", "type": "SAFETY_CAR", "message": "FULL SAFETY CAR DEPLOYED - DEBRIS CLEANUP TURN 4", "consequence": "Hamilton & Leclerc double-stack in Ferrari box. 350kW MGU-K full electrical override primed for restart."},
        {"lap": 36, "flag": "GREEN", "type": "RESTART", "message": "MANUAL OVERTAKE MODE (MOM) ACTIVATED ON RESTART", "consequence": "Hamilton uses 350kW electrical boost up to 337 km/h to challenge Verstappen for victory!"}
    ],
    # 2026 Silverstone British GP (350kW Hybrid Showcase)
    9812: [
        {"lap": 1, "flag": "GREEN", "type": "START", "message": "ROARING 2026 CAPACITY CROWD AT SILVERSTONE", "consequence": "Active Aero Z-mode provides 300+ km/h downforce through Copse and Maggotts-Becketts."},
        {"lap": 24, "flag": "YELLOW", "type": "LOW_GRIP", "message": "LIGHT SUMMER DRIZZLE REPORTED AT STOWE", "consequence": "Active flap balance switches to maximum high-downforce cornering profile."},
        {"lap": 42, "flag": "GREEN", "type": "BATTLE", "message": "THREE-WAY TITLE DUEL: HAMILTON VS VERSTAPPEN VS NORRIS", "consequence": "Ferrari 50/50 hybrid thermal efficiency matches Red Bull-Ford in thrilling final stint."}
    ]
}

# -------------------------------------------------------------
# Accurate 2D Track Splines for Major Circuits
# -------------------------------------------------------------
def generate_circuit_spline(circuit_key: str = "silverstone") -> List[Dict[str, float]]:
    """Generates normalized vector spline points [0.0 - 1.0] for any circuit."""
    c = circuit_key.lower()

    if c == "monaco":
        raw = [
            (250, 750), (320, 720), (370, 680), (410, 600), # Sainte Dévote -> Beau Rivage
            (440, 500), (460, 420), (450, 360), (400, 320), # Massenet -> Casino Square
            (360, 340), (330, 380), (310, 440), (280, 480), # Mirabeau -> Hairpin
            (300, 530), (360, 560), (430, 570), (510, 580), # Portier -> Tunnel
            (580, 590), (660, 600), (740, 610), (810, 630), # Tunnel exit -> Chicane
            (830, 670), (810, 710), (760, 720), (710, 710), # Tabac
            (680, 730), (660, 780), (670, 830), (640, 870), # Swimming Pool
            (580, 880), (500, 870), (420, 850), (340, 820), # Rascasse -> Antony Noghès
            (280, 790), (250, 750)
        ]
    elif c == "spa":
        raw = [
            (300, 700), (280, 650), (280, 600), (310, 560), # La Source
            (350, 530), (400, 500), (450, 470), (500, 430), # Eau Rouge & Raidillon
            (560, 390), (630, 340), (700, 290), (770, 240), # Kemmel Straight
            (830, 210), (870, 220), (880, 260), (850, 300), # Les Combes
            (820, 350), (800, 410), (810, 470), (830, 520), # Malmedy & Bruxelles
            (810, 570), (760, 610), (700, 640), (640, 650), # Speaker's Corner
            (580, 680), (530, 720), (480, 760), (450, 800), # Pouhon (double apex)
            (470, 840), (520, 860), (580, 870), (650, 880), # Fagnes & Stavelot
            (730, 870), (810, 840), (870, 800), (920, 740), # Blanchimont
            (880, 710), (800, 710), (720, 710), (600, 710), # Bus Stop Chicane
            (450, 710), (300, 700)
        ]
    elif c == "monza":
        raw = [
            (250, 650), (320, 650), (400, 650), (500, 650), # Rettifilo Straight
            (600, 650), (700, 650), (780, 650), (830, 630), # Approach Prima Variante
            (840, 590), (820, 560), (830, 520), (870, 480), # Variante del Rettifilo
            (910, 430), (920, 370), (900, 310), (860, 260), # Curva Grande
            (800, 230), (730, 220), (680, 240), (670, 280), # Variante della Roggia
            (650, 320), (610, 340), (560, 330), (520, 300), # Lesmo 1 & Lesmo 2
            (470, 280), (410, 280), (350, 300), (300, 340), # Serraglio
            (270, 390), (280, 440), (320, 470), (370, 480), # Variante Ascari
            (430, 490), (480, 510), (490, 560), (460, 600), # Back straight
            (380, 620), (300, 630), (250, 650)              # Parabolica curve
        ]
    elif c == "miami":
        raw = [
            (300, 750), (360, 750), (430, 730), (480, 690), # Turn 1-3
            (520, 630), (540, 560), (520, 500), (480, 450), # S-bends 4-6
            (420, 420), (370, 410), (330, 420), (290, 450), # Turn 7 Marina
            (260, 500), (250, 560), (270, 620), (310, 660), # Turn 8-10
            (380, 650), (470, 630), (580, 600), (700, 560), # Back straight
            (780, 520), (840, 480), (860, 440), (840, 400), # Chicane 14-15
            (780, 390), (710, 400), (630, 420), (540, 440), # Highway return
            (440, 480), (350, 540), (280, 620), (260, 700), # Hairpin 17
            (300, 750)
        ]
    else: # Default Silverstone
        raw = [
            (480, 720), (520, 700), (550, 670), (560, 630),
            (540, 590), (490, 570), (450, 550), (430, 530),
            (440, 500), (470, 480), (530, 470), (600, 460),
            (660, 450), (710, 440), (750, 440), (780, 460),
            (800, 490), (810, 530), (800, 570), (770, 600),
            (720, 630), (660, 660), (600, 700), (550, 730),
            (510, 760), (460, 800), (400, 830), (340, 850),
            (280, 830), (250, 790), (240, 740),
            (230, 690), (210, 640), (180, 590),
            (160, 550), (150, 510), (160, 470),
            (180, 440), (210, 410), (250, 390),
            (310, 380), (380, 370), (460, 360), (540, 350),
            (620, 340), (700, 330), (770, 320), (830, 320),
            (870, 350), (880, 390), (860, 430),
            (820, 480), (780, 540), (740, 600), (710, 660),
            (670, 710), (610, 740), (540, 750), (480, 720)
        ]

    min_x = min(p[0] for p in raw)
    max_x = max(p[0] for p in raw)
    min_y = min(p[1] for p in raw)
    max_y = max(p[1] for p in raw)

    points = []
    for i in range(len(raw) - 1):
        p1 = raw[i]
        p2 = raw[i + 1]
        steps = 6
        for s in range(steps):
            t = s / steps
            x = p1[0] + (p2[0] - p1[0]) * t
            y = p1[1] + (p2[1] - p1[1]) * t
            norm_x = (x - min_x) / (max_x - min_x)
            norm_y = (y - min_y) / (max_y - min_y)
            points.append({"x": round(norm_x, 4), "y": round(norm_y, 4)})

    return points

# -------------------------------------------------------------
# Data Accessors
# -------------------------------------------------------------
def get_seasons() -> List[Dict[str, Any]]:
    return [
        {"year": 2026, "label": "2026 Active Aero & 50/50 Hybrid (Current)", "rounds": 24, "status": "Active / Live Telemetry Stream"},
        {"year": 2025, "label": "2025 Season", "rounds": 24, "status": "Completed / Archival Stream"},
        {"year": 2024, "label": "2024 World Championship", "rounds": 24, "status": "Completed (VER WDC / McLaren WCC)"},
        {"year": 2023, "label": "2023 Record Dominance", "rounds": 22, "status": "Completed (Red Bull 21 Wins)"},
        {"year": 2021, "label": "2021 Title Battle", "rounds": 22, "status": "Historical Vault"}
    ]

def get_season_races(year: int = 2026) -> List[Dict[str, Any]]:
    if year == 2026:
        return [
            {"round": 1, "session_key": 9801, "country": "Bahrain", "circuit_name": "Sakhir (Active Aero Debut)", "circuit_key": "bahrain", "winner": "L. Hamilton", "team": "Ferrari", "date": "2026-03-01", "weather": "Dry Night / 350kW MGU-K Boost"},
            {"round": 2, "session_key": 9802, "country": "Saudi Arabia", "circuit_name": "Jeddah Corniche", "circuit_key": "jeddah", "winner": "M. Verstappen", "team": "Red Bull-Ford", "date": "2026-03-08", "weather": "Night / 345 km/h X-Mode"},
            {"round": 3, "session_key": 9803, "country": "Australia", "circuit_name": "Albert Park Melbourne", "circuit_key": "albert_park", "winner": "C. Leclerc", "team": "Ferrari", "date": "2026-03-22", "weather": "Sunny"},
            {"round": 4, "session_key": 9804, "country": "Japan", "circuit_name": "Suzuka", "circuit_key": "suzuka", "winner": "M. Verstappen", "team": "Red Bull-Ford", "date": "2026-04-05", "weather": "Cool / Z-Mode High Downforce"},
            {"round": 5, "session_key": 9805, "country": "China", "circuit_name": "Shanghai", "circuit_key": "shanghai", "winner": "L. Norris", "team": "McLaren", "date": "2026-04-19", "weather": "Overcast"},
            {"round": 6, "session_key": 9806, "country": "United States", "circuit_name": "Miami", "circuit_key": "miami", "winner": "L. Hamilton", "team": "Ferrari", "date": "2026-05-03", "weather": "Hot / Electric Override Pass"},
            {"round": 7, "session_key": 9807, "country": "Italy", "circuit_name": "Imola", "circuit_key": "imola", "winner": "C. Leclerc", "team": "Ferrari", "date": "2026-05-17", "weather": "Tifosi Jubilation"},
            {"round": 8, "session_key": 9808, "country": "Monaco", "circuit_name": "Monte Carlo", "circuit_key": "monaco", "winner": "C. Leclerc", "team": "Ferrari", "date": "2026-05-24", "weather": "Sunny / Tight Track Agility"},
            {"round": 9, "session_key": 9809, "country": "Canada", "circuit_name": "Montreal", "circuit_key": "montreal", "winner": "G. Russell", "team": "Mercedes", "date": "2026-06-07", "weather": "Variable / Regen Braking Heavy"},
            {"round": 10, "session_key": 9810, "country": "Spain", "circuit_name": "Barcelona", "circuit_key": "barcelona", "winner": "M. Verstappen", "team": "Red Bull-Ford", "date": "2026-06-21", "weather": "Hot"},
            {"round": 11, "session_key": 9811, "country": "Austria", "circuit_name": "Red Bull Ring", "circuit_key": "spielberg", "winner": "L. Norris", "team": "McLaren", "date": "2026-06-28", "weather": "Sunny"},
            {"round": 12, "session_key": 9812, "country": "Great Britain", "circuit_name": "Silverstone", "circuit_key": "silverstone", "winner": "L. Hamilton", "team": "Ferrari", "date": "2026-07-05", "weather": "Variable / Epic 3-Way Battle"},
            {"round": 13, "session_key": 9813, "country": "Belgium", "circuit_name": "Spa-Francorchamps", "circuit_key": "spa", "winner": "M. Verstappen", "team": "Red Bull-Ford", "date": "2026-07-26", "weather": "Kemmel Straight Overrides"},
            {"round": 14, "session_key": 9814, "country": "Hungary", "circuit_name": "Hungaroring", "circuit_key": "hungaroring", "winner": "O. Piastri", "team": "McLaren", "date": "2026-08-02", "weather": "Sweltering"},
            {"round": 15, "session_key": 9815, "country": "Netherlands", "circuit_name": "Zandvoort", "circuit_key": "zandvoort", "winner": "M. Verstappen", "team": "Red Bull-Ford", "date": "2026-08-30", "weather": "Windy Dunes"},
            {"round": 16, "session_key": 9816, "country": "Italy", "circuit_name": "Monza", "circuit_key": "monza", "winner": "C. Leclerc", "team": "Ferrari", "date": "2026-09-06", "weather": "Temple of Speed 350 km/h"},
            {"round": 17, "session_key": 9817, "country": "Azerbaijan", "circuit_name": "Baku", "circuit_key": "baku", "winner": "L. Norris", "team": "McLaren", "date": "2026-09-20", "weather": "Long Straight Slipstream"},
            {"round": 18, "session_key": 9818, "country": "Singapore", "circuit_name": "Marina Bay", "circuit_key": "singapore", "winner": "C. Leclerc", "team": "Ferrari", "date": "2026-10-04", "weather": "Night Humid"},
            {"round": 19, "session_key": 9819, "country": "United States", "circuit_name": "Austin COTA", "circuit_key": "austin", "winner": "TBD", "team": "Upcoming", "date": "2026-10-18", "weather": "Scheduled"},
            {"round": 20, "session_key": 9820, "country": "Mexico", "circuit_name": "Mexico City", "circuit_key": "mexico", "winner": "TBD", "team": "Upcoming", "date": "2026-10-25", "weather": "Scheduled"},
            {"round": 21, "session_key": 9821, "country": "Brazil", "circuit_name": "Interlagos", "circuit_key": "interlagos", "winner": "TBD", "team": "Upcoming", "date": "2026-11-08", "weather": "Scheduled"},
            {"round": 22, "session_key": 9822, "country": "United States", "circuit_name": "Las Vegas", "circuit_key": "las_vegas", "winner": "TBD", "team": "Upcoming", "date": "2026-11-21", "weather": "Scheduled"},
            {"round": 23, "session_key": 9823, "country": "Qatar", "circuit_name": "Lusail", "circuit_key": "lusail", "winner": "TBD", "team": "Upcoming", "date": "2026-11-29", "weather": "Scheduled"},
            {"round": 24, "session_key": 9824, "country": "United Arab Emirates", "circuit_name": "Yas Marina", "circuit_key": "abu_dhabi", "winner": "TBD", "team": "Upcoming", "date": "2026-12-06", "weather": "Season Finale"}
        ]

    return [
        {"round": 1, "session_key": 9472, "country": "Bahrain", "circuit_name": "Sakhir", "circuit_key": "bahrain", "winner": "M. Verstappen", "team": "Red Bull", "date": "2024-03-02", "weather": "Dry Night"},
        {"round": 2, "session_key": 9480, "country": "Saudi Arabia", "circuit_name": "Jeddah", "circuit_key": "jeddah", "winner": "M. Verstappen", "team": "Red Bull", "date": "2024-03-09", "weather": "Dry Night"},
        {"round": 3, "session_key": 9488, "country": "Australia", "circuit_name": "Melbourne", "circuit_key": "albert_park", "winner": "C. Sainz", "team": "Ferrari", "date": "2024-03-24", "weather": "Sunny"},
        {"round": 4, "session_key": 9496, "country": "Japan", "circuit_name": "Suzuka", "circuit_key": "suzuka", "winner": "M. Verstappen", "team": "Red Bull", "date": "2024-04-07", "weather": "Cool / Dry"},
        {"round": 5, "session_key": 9673, "country": "China", "circuit_name": "Shanghai", "circuit_key": "shanghai", "winner": "M. Verstappen", "team": "Red Bull", "date": "2024-04-21", "weather": "Overcast"},
        {"round": 6, "session_key": 9507, "country": "United States", "circuit_name": "Miami", "circuit_key": "miami", "winner": "L. Norris", "team": "McLaren", "date": "2024-05-05", "weather": "Hot / Safety Car Turnaround"},
        {"round": 7, "session_key": 9515, "country": "Italy", "circuit_name": "Imola", "circuit_key": "imola", "winner": "M. Verstappen", "team": "Red Bull", "date": "2024-05-19", "weather": "Warm"},
        {"round": 8, "session_key": 9523, "country": "Monaco", "circuit_name": "Monte Carlo", "circuit_key": "monaco", "winner": "C. Leclerc", "team": "Ferrari", "date": "2024-05-26", "weather": "Sunny / Red Flag Lap 1"},
        {"round": 9, "session_key": 9531, "country": "Canada", "circuit_name": "Montreal", "circuit_key": "montreal", "winner": "M. Verstappen", "team": "Red Bull", "date": "2024-06-09", "weather": "Heavy Rain / Safety Cars"},
        {"round": 10, "session_key": 9539, "country": "Spain", "circuit_name": "Barcelona", "circuit_key": "barcelona", "winner": "M. Verstappen", "team": "Red Bull", "date": "2024-06-23", "weather": "Hot"},
        {"round": 11, "session_key": 9550, "country": "Austria", "circuit_name": "Red Bull Ring", "circuit_key": "spielberg", "winner": "G. Russell", "team": "Mercedes", "date": "2024-06-30", "weather": "Sunny / VER-NOR Collision"},
        {"round": 12, "session_key": 9558, "country": "Great Britain", "circuit_name": "Silverstone", "circuit_key": "silverstone", "winner": "L. Hamilton", "team": "Mercedes", "date": "2024-07-07", "weather": "Variable Rain / Inters"},
        {"round": 13, "session_key": 9566, "country": "Hungary", "circuit_name": "Hungaroring", "circuit_key": "hungaroring", "winner": "O. Piastri", "team": "McLaren", "date": "2024-07-21", "weather": "Sweltering"},
        {"round": 14, "session_key": 9574, "country": "Belgium", "circuit_name": "Spa-Francorchamps", "circuit_key": "spa", "winner": "L. Hamilton", "team": "Mercedes", "date": "2024-07-28", "weather": "Dry / Russell 1-Stop DSQ"},
        {"round": 15, "session_key": 9582, "country": "Netherlands", "circuit_name": "Zandvoort", "circuit_key": "zandvoort", "winner": "L. Norris", "team": "McLaren", "date": "2024-08-25", "weather": "Windy"},
        {"round": 16, "session_key": 9590, "country": "Italy", "circuit_name": "Monza", "circuit_key": "monza", "winner": "C. Leclerc", "team": "Ferrari", "date": "2024-09-01", "weather": "Hot / Leclerc 1-Stop Masterclass"},
        {"round": 17, "session_key": 9598, "country": "Azerbaijan", "circuit_name": "Baku", "circuit_key": "baku", "winner": "O. Piastri", "team": "McLaren", "date": "2024-09-15", "weather": "Street / VSC Lap 50 Crash"},
        {"round": 18, "session_key": 9606, "country": "Singapore", "circuit_name": "Marina Bay", "circuit_key": "singapore", "winner": "L. Norris", "team": "McLaren", "date": "2024-09-22", "weather": "Night Humid"},
        {"round": 19, "session_key": 9617, "country": "United States", "circuit_name": "Austin COTA", "circuit_key": "austin", "winner": "C. Leclerc", "team": "Ferrari", "date": "2024-10-20", "weather": "Warm"},
        {"round": 20, "session_key": 9625, "country": "Mexico", "circuit_name": "Mexico City", "circuit_key": "mexico", "winner": "C. Sainz", "team": "Ferrari", "date": "2024-10-27", "weather": "Altitude Dry"},
        {"round": 21, "session_key": 9636, "country": "Brazil", "circuit_name": "Interlagos", "circuit_key": "interlagos", "winner": "M. Verstappen", "team": "Red Bull", "date": "2024-11-03", "weather": "Torrential Rain / VER P17 to P1"},
        {"round": 22, "session_key": 9644, "country": "United States", "circuit_name": "Las Vegas", "circuit_key": "las_vegas", "winner": "G. Russell", "team": "Mercedes", "date": "2024-11-23", "weather": "Cold Night"},
        {"round": 23, "session_key": 9655, "country": "Qatar", "circuit_name": "Lusail", "circuit_key": "lusail", "winner": "M. Verstappen", "team": "Red Bull", "date": "2024-12-01", "weather": "Night Wind"},
        {"round": 24, "session_key": 9662, "country": "United Arab Emirates", "circuit_name": "Yas Marina", "circuit_key": "abu_dhabi", "winner": "L. Norris", "team": "McLaren", "date": "2024-12-08", "weather": "Twilight"}
    ]

def get_session_drivers(session_key: int = 9558) -> List[Dict[str, Any]]:
    # Specific results for key sessions
    # 2026 Season Grid (Hamilton at Ferrari, Antonelli at Mercedes, Audi F1 Team)
    if session_key in [9801, 9802, 9803, 9804, 9805, 9806, 9807, 9808, 9809, 9810, 9811, 9812, 9813, 9814, 9815, 9816, 9817, 9818]:
        return [
            {"driver_number": 44, "acronym": "HAM", "full_name": "Lewis Hamilton", "team_name": "Ferrari", "team_colour": "#E80020", "position": 1, "gap": "LEADER", "tyre": "M", "tyre_age": 16, "pits": 1, "last_lap": "1:26.418"},
            {"driver_number": 1, "acronym": "VER", "full_name": "Max Verstappen", "team_name": "Red Bull Racing", "team_colour": "#3671C6", "position": 2, "gap": "+0.842s", "tyre": "H", "tyre_age": 22, "pits": 1, "last_lap": "1:26.290"},
            {"driver_number": 16, "acronym": "LEC", "full_name": "Charles Leclerc", "team_name": "Ferrari", "team_colour": "#E80020", "position": 3, "gap": "+4.115s", "tyre": "M", "tyre_age": 16, "pits": 1, "last_lap": "1:26.710"},
            {"driver_number": 4, "acronym": "NOR", "full_name": "Lando Norris", "team_name": "McLaren", "team_colour": "#FF8000", "position": 4, "gap": "+5.980s", "tyre": "M", "tyre_age": 18, "pits": 1, "last_lap": "1:26.650"},
            {"driver_number": 63, "acronym": "RUS", "full_name": "George Russell", "team_name": "Mercedes", "team_colour": "#27F4D2", "position": 5, "gap": "+11.230s", "tyre": "H", "tyre_age": 24, "pits": 1, "last_lap": "1:27.120"},
            {"driver_number": 81, "acronym": "PIA", "full_name": "Oscar Piastri", "team_name": "McLaren", "team_colour": "#FF8000", "position": 6, "gap": "+14.890s", "tyre": "H", "tyre_age": 20, "pits": 1, "last_lap": "1:27.350"},
            {"driver_number": 12, "acronym": "ANT", "full_name": "Kimi Antonelli", "team_name": "Mercedes", "team_colour": "#27F4D2", "position": 7, "gap": "+21.450s", "tyre": "M", "tyre_age": 15, "pits": 1, "last_lap": "1:27.560"},
            {"driver_number": 27, "acronym": "HUL", "full_name": "Nico Hulkenberg", "team_name": "Audi F1 Team", "team_colour": "#E21B23", "position": 8, "gap": "+34.120s", "tyre": "H", "tyre_age": 28, "pits": 1, "last_lap": "1:28.110"},
            {"driver_number": 55, "acronym": "SAI", "full_name": "Carlos Sainz", "team_name": "Williams", "team_colour": "#64C4FF", "position": 9, "gap": "+38.450s", "tyre": "H", "tyre_age": 26, "pits": 1, "last_lap": "1:28.240"},
            {"driver_number": 14, "acronym": "ALO", "full_name": "Fernando Alonso", "team_name": "Aston Martin", "team_colour": "#229971", "position": 10, "gap": "+42.110s", "tyre": "M", "tyre_age": 19, "pits": 1, "last_lap": "1:28.530"}
        ]
    elif session_key == 9507: # Miami GP (Norris win)
        return [
            {"driver_number": 4, "acronym": "NOR", "full_name": "Lando Norris", "team_name": "McLaren", "team_colour": "#FF8000", "position": 1, "gap": "LEADER", "tyre": "M", "tyre_age": 14, "pits": 1, "last_lap": "1:30.634"},
            {"driver_number": 1, "acronym": "VER", "full_name": "Max Verstappen", "team_name": "Red Bull Racing", "team_colour": "#3671C6", "position": 2, "gap": "+7.612s", "tyre": "H", "tyre_age": 25, "pits": 1, "last_lap": "1:31.025"},
            {"driver_number": 16, "acronym": "LEC", "full_name": "Charles Leclerc", "team_name": "Ferrari", "team_colour": "#E80020", "position": 3, "gap": "+9.920s", "tyre": "H", "tyre_age": 28, "pits": 1, "last_lap": "1:31.110"},
            {"driver_number": 55, "acronym": "SAI", "full_name": "Carlos Sainz", "team_name": "Ferrari", "team_colour": "#E80020", "position": 4, "gap": "+11.407s", "tyre": "H", "tyre_age": 27, "pits": 1, "last_lap": "1:31.250"},
            {"driver_number": 11, "acronym": "PER", "full_name": "Sergio Perez", "team_name": "Red Bull Racing", "team_colour": "#3671C6", "position": 5, "gap": "+14.650s", "tyre": "M", "tyre_age": 22, "pits": 2, "last_lap": "1:31.390"},
            {"driver_number": 44, "acronym": "HAM", "full_name": "Lewis Hamilton", "team_name": "Mercedes", "team_colour": "#27F4D2", "position": 6, "gap": "+16.585s", "tyre": "M", "tyre_age": 24, "pits": 1, "last_lap": "1:31.420"}
        ]
    elif session_key == 9523: # Monaco GP (Leclerc win)
        return [
            {"driver_number": 16, "acronym": "LEC", "full_name": "Charles Leclerc", "team_name": "Ferrari", "team_colour": "#E80020", "position": 1, "gap": "LEADER", "tyre": "H", "tyre_age": 77, "pits": 0, "last_lap": "1:15.112"},
            {"driver_number": 81, "acronym": "PIA", "full_name": "Oscar Piastri", "team_name": "McLaren", "team_colour": "#FF8000", "position": 2, "gap": "+7.152s", "tyre": "H", "tyre_age": 77, "pits": 0, "last_lap": "1:15.890"},
            {"driver_number": 55, "acronym": "SAI", "full_name": "Carlos Sainz", "team_name": "Ferrari", "team_colour": "#E80020", "position": 3, "gap": "+7.585s", "tyre": "H", "tyre_age": 77, "pits": 0, "last_lap": "1:15.950"},
            {"driver_number": 4, "acronym": "NOR", "full_name": "Lando Norris", "team_name": "McLaren", "team_colour": "#FF8000", "position": 4, "gap": "+8.650s", "tyre": "H", "tyre_age": 77, "pits": 0, "last_lap": "1:16.020"},
            {"driver_number": 63, "acronym": "RUS", "full_name": "George Russell", "team_name": "Mercedes", "team_colour": "#27F4D2", "position": 5, "gap": "+13.309s", "tyre": "M", "tyre_age": 77, "pits": 0, "last_lap": "1:16.410"},
            {"driver_number": 1, "acronym": "VER", "full_name": "Max Verstappen", "team_name": "Red Bull Racing", "team_colour": "#3671C6", "position": 6, "gap": "+13.853s", "tyre": "H", "tyre_age": 28, "pits": 1, "last_lap": "1:14.569"}
        ]
    elif session_key == 9590: # Monza GP (Leclerc 1-stop)
        return [
            {"driver_number": 16, "acronym": "LEC", "full_name": "Charles Leclerc", "team_name": "Ferrari", "team_colour": "#E80020", "position": 1, "gap": "LEADER", "tyre": "H", "tyre_age": 38, "pits": 1, "last_lap": "1:22.950"},
            {"driver_number": 81, "acronym": "PIA", "full_name": "Oscar Piastri", "team_name": "McLaren", "team_colour": "#FF8000", "position": 2, "gap": "+2.664s", "tyre": "H", "tyre_age": 14, "pits": 2, "last_lap": "1:21.432"},
            {"driver_number": 4, "acronym": "NOR", "full_name": "Lando Norris", "team_name": "McLaren", "team_colour": "#FF8000", "position": 3, "gap": "+6.153s", "tyre": "H", "tyre_age": 19, "pits": 2, "last_lap": "1:21.430"},
            {"driver_number": 55, "acronym": "SAI", "full_name": "Carlos Sainz", "team_name": "Ferrari", "team_colour": "#E80020", "position": 4, "gap": "+15.621s", "tyre": "H", "tyre_age": 34, "pits": 1, "last_lap": "1:23.210"},
            {"driver_number": 44, "acronym": "HAM", "full_name": "Lewis Hamilton", "team_name": "Mercedes", "team_colour": "#27F4D2", "position": 5, "gap": "+22.820s", "tyre": "H", "tyre_age": 16, "pits": 2, "last_lap": "1:22.500"},
            {"driver_number": 1, "acronym": "VER", "full_name": "Max Verstappen", "team_name": "Red Bull Racing", "team_colour": "#3671C6", "position": 6, "gap": "+37.932s", "tyre": "H", "tyre_age": 12, "pits": 2, "last_lap": "1:22.420"}
        ]
    
    # Default Silverstone 2024
    return [
        {"driver_number": 44, "acronym": "HAM", "full_name": "Lewis Hamilton", "team_name": "Mercedes", "team_colour": "#27F4D2", "position": 1, "gap": "LEADER", "tyre": "S", "tyre_age": 14, "pits": 2, "last_lap": "1:28.299"},
        {"driver_number": 1, "acronym": "VER", "full_name": "Max Verstappen", "team_name": "Red Bull Racing", "team_colour": "#3671C6", "position": 2, "gap": "+1.465s", "tyre": "H", "tyre_age": 14, "pits": 2, "last_lap": "1:28.012"},
        {"driver_number": 4, "acronym": "NOR", "full_name": "Lando Norris", "team_name": "McLaren", "team_colour": "#FF8000", "position": 3, "gap": "+7.547s", "tyre": "S", "tyre_age": 13, "pits": 2, "last_lap": "1:28.750"},
        {"driver_number": 81, "acronym": "PIA", "full_name": "Oscar Piastri", "team_name": "McLaren", "team_colour": "#FF8000", "position": 4, "gap": "+12.429s", "tyre": "M", "tyre_age": 13, "pits": 2, "last_lap": "1:28.320"},
        {"driver_number": 55, "acronym": "SAI", "full_name": "Carlos Sainz", "team_name": "Ferrari", "team_colour": "#E80020", "position": 5, "gap": "+47.318s", "tyre": "S", "tyre_age": 2, "pits": 3, "last_lap": "1:28.293"},
        {"driver_number": 27, "acronym": "HUL", "full_name": "Nico Hulkenberg", "team_name": "Haas F1 Team", "team_colour": "#B6BABD", "position": 6, "gap": "+55.731s", "tyre": "S", "tyre_age": 14, "pits": 2, "last_lap": "1:29.810"},
        {"driver_number": 18, "acronym": "STR", "full_name": "Lance Stroll", "team_name": "Aston Martin", "team_colour": "#229971", "position": 7, "gap": "+56.569s", "tyre": "M", "tyre_age": 14, "pits": 2, "last_lap": "1:29.950"},
        {"driver_number": 14, "acronym": "ALO", "full_name": "Fernando Alonso", "team_name": "Aston Martin", "team_colour": "#229971", "position": 8, "gap": "+1:03.577", "tyre": "M", "tyre_age": 14, "pits": 2, "last_lap": "1:30.120"},
        {"driver_number": 23, "acronym": "ALB", "full_name": "Alexander Albon", "team_name": "Williams", "team_colour": "#64C4FF", "position": 9, "gap": "+1:08.387", "tyre": "M", "tyre_age": 14, "pits": 2, "last_lap": "1:30.410"},
        {"driver_number": 22, "acronym": "TSU", "full_name": "Yuki Tsunoda", "team_name": "RB", "team_colour": "#6692FF", "position": 10, "gap": "+1:19.303", "tyre": "S", "tyre_age": 14, "pits": 2, "last_lap": "1:30.820"}
    ]

def get_race_control(session_key: int = 9558) -> List[Dict[str, Any]]:
    return RACE_CONTROL_EVENTS.get(session_key, RACE_CONTROL_EVENTS[9558])

def get_replay_frame(lap_progress: float = 0.65, circuit_key: str = "silverstone", session_key: int = 9558) -> List[Dict[str, Any]]:
    spline = generate_circuit_spline(circuit_key)
    total_pts = len(spline)
    drivers = get_session_drivers(session_key)

    # Check for Safety Car on current progress
    events = get_race_control(session_key)
    sc_active = any(ev.get("type") in ["SAFETY_CAR", "VSC"] and 0.5 <= lap_progress <= 0.65 for ev in events)

    frame_cars = []
    offsets = [
        0.000, -0.012, -0.035, -0.052, -0.088, -0.110, -0.145, -0.170, -0.198, -0.220,
        -0.240, -0.260, -0.280, -0.305, -0.330, -0.350, -0.380, -0.400, -0.440, -0.470
    ]

    for i, d in enumerate(drivers):
        offset = offsets[i] if i < len(offsets) else -0.02 * i
        driver_progress = (lap_progress + offset) % 1.0
        idx = int(driver_progress * total_pts) % total_pts
        next_idx = (idx + 1) % total_pts

        pt = spline[idx]
        next_pt = spline[next_idx]

        dx = next_pt["x"] - pt["x"]
        dy = next_pt["y"] - pt["y"]
        heading_rad = math.atan2(dy, dx)
        heading_deg = math.degrees(heading_rad)

        base_speed = 310 if not sc_active else 140
        speed = int(base_speed + math.sin(driver_progress * 18) * 35)
        gear = 8 if not sc_active else 4
        drs = 1 if (0.65 <= driver_progress <= 0.78 and not sc_active) else 0

        frame_cars.append({
            "driver_number": d["driver_number"],
            "acronym": d["acronym"],
            "team_name": d["team_name"],
            "team_colour": d["team_colour"],
            "position": i + 1,
            "x": pt["x"],
            "y": pt["y"],
            "heading_deg": round(heading_deg, 1),
            "speed_kmh": max(70, min(340, speed)),
            "gear": gear,
            "drs": drs,
            "tyre": d.get("tyre", "M"),
            "gap": d.get("gap", "--"),
            "sc_active": sc_active
        })

    return frame_cars

def get_telemetry_trace(driver_1: int = 1, driver_2: int = 4) -> Dict[str, Any]:
    distance_points = 100
    data = {
        "corner": "High Speed Braking & Apex Zone",
        "distance_m": [],
        "driver_1": {"number": driver_1, "name": "VER (Red Bull)", "color": "#3671C6", "speed": [], "throttle": [], "brake": [], "gear": []},
        "driver_2": {"number": driver_2, "name": "NOR (McLaren)", "color": "#FF8000", "speed": [], "throttle": [], "brake": [], "gear": []},
        "delta_time_s": []
    }

    for m in range(distance_points):
        dist = m * 5
        data["distance_m"].append(dist)
        if dist < 240:
            speed_1, throttle_1, brake_1, gear_1 = 328.0, 100.0, 0.0, 8
        elif dist < 340:
            pct = (dist - 240) / 100.0
            speed_1 = 328.0 - (pct ** 0.8) * 144.0
            throttle_1, brake_1 = 0.0, round(min(100.0, 95.0 * (1.0 - (pct - 0.2)**2)), 1)
            gear_1 = max(5, int(8 - pct * 3))
        else:
            pct = (dist - 340) / 160.0
            speed_1 = 184.0 + pct * 90.0
            throttle_1, brake_1 = round(min(100.0, pct * 110.0), 1), 0.0
            gear_1 = min(7, int(5 + pct * 2))

        if dist < 252:
            speed_2, throttle_2, brake_2, gear_2 = 332.0, 100.0, 0.0, 8
        elif dist < 345:
            pct = (dist - 252) / 93.0
            speed_2 = 332.0 - (pct ** 0.85) * 144.0
            throttle_2, brake_2 = 0.0, round(min(100.0, 100.0 * (1.0 - (pct - 0.15)**2)), 1)
            gear_2 = max(5, int(8 - pct * 3))
        else:
            pct = (dist - 345) / 155.0
            speed_2 = 188.0 + pct * 88.0
            throttle_2, brake_2 = round(min(100.0, pct * 105.0), 1), 0.0
            gear_2 = min(7, int(5 + pct * 2))

        data["driver_1"]["speed"].append(round(speed_1, 1))
        data["driver_1"]["throttle"].append(throttle_1)
        data["driver_1"]["brake"].append(brake_1)
        data["driver_1"]["gear"].append(gear_1)
        data["driver_2"]["speed"].append(round(speed_2, 1))
        data["driver_2"]["throttle"].append(throttle_2)
        data["driver_2"]["brake"].append(brake_2)
        data["driver_2"]["gear"].append(gear_2)
        data["delta_time_s"].append(round((speed_1 - speed_2) * 0.0018, 3))

    return data

def simulate_undercut(
    pit_lap: int = 35,
    target_compound: str = "H",
    disruption: str = "Normal",
    target_driver: Optional[str] = None,
    rival_driver: Optional[str] = None,
    circuit_name: Optional[str] = None,
    total_laps: Optional[int] = None
) -> Dict[str, Any]:
    # Determine base pit stop loss for the circuit
    c_lower = (circuit_name or "").lower()
    base_pit_loss = 20.5
    if "monza" in c_lower:
        base_pit_loss = 24.2
    elif "spa" in c_lower or "francorchamps" in c_lower:
        base_pit_loss = 22.1
    elif "baku" in c_lower:
        base_pit_loss = 20.8
    elif "silverstone" in c_lower:
        base_pit_loss = 19.8
    elif "albert" in c_lower or "melbourne" in c_lower:
        base_pit_loss = 19.8
    elif "monaco" in c_lower:
        base_pit_loss = 21.0
    elif "bahrain" in c_lower or "sakhir" in c_lower:
        base_pit_loss = 23.0
    elif "interlagos" in c_lower or "brazil" in c_lower:
        base_pit_loss = 20.2
    elif "yas" in c_lower or "abu dhabi" in c_lower:
        base_pit_loss = 21.5

    pit_loss = base_pit_loss
    if disruption == "Virtual Safety Car":
        pit_loss = round(base_pit_loss * 0.46, 1)  # Delta saved under delta 40% VSC limit
    elif disruption == "Full Safety Car":
        pit_loss = round(base_pit_loss * 0.60, 1)  # Delta saved under SC queue speed

    # Compound pace deltas on fresh rubber (seconds per lap advantage over worn rival rubber)
    compound_deltas = {"S": 1.35, "M": 0.95, "H": 0.65}
    pace_gain_per_lap = compound_deltas.get(target_compound.upper(), 0.85)

    tot = total_laps or 55
    # Out-lap + in-lap delta: The attacker gets 1 flying lap on fresh rubber before rival stops
    delta_out_lap = round(pace_gain_per_lap * 1.4, 2)
    # Estimated lead/deficit gap after rival stops 1 lap later
    baseline_gap = 1.8 if disruption == "Normal" else 3.4
    lap_modifier = (tot * 0.6 - pit_lap) * 0.08
    estimated_lead_gap = round(baseline_gap + lap_modifier + (pace_gain_per_lap - 0.7) * 1.2, 2)

    # Success probability calculation
    base_prob = 84.0
    if disruption == "Virtual Safety Car":
        base_prob = 96.5
    elif disruption == "Full Safety Car":
        base_prob = 98.2
    elif target_compound.upper() == "S":
        base_prob = 92.0
    elif target_compound.upper() == "M":
        base_prob = 88.5

    success_prob = round(min(99.0, max(65.0, base_prob + (1.2 if estimated_lead_gap > 1.5 else -4.0))), 1)

    t_name = target_driver or "Attacking Driver"
    r_name = rival_driver or "Race Leader"
    clean_air = round(2.8 + (1.5 if disruption != "Normal" else 0.4), 1)

    c_names_map = {"S": "Soft (Red C5/C4)", "M": "Medium (Yellow C3)", "H": "Hard (White C2/C1)"}
    compound_full = c_names_map.get(target_compound.upper(), f"Compound {target_compound}")

    verdict = (
        f"BOX LAP {pit_lap} for {compound_full}. Fresh rubber produces a +{delta_out_lap:.2f}s out-lap pace delta. "
        f"Projected to leapfrog {r_name} by ~{abs(estimated_lead_gap):.1f}s when they box on Lap {pit_lap + 1}."
    )

    return {
        "target_driver": t_name,
        "rival_driver": r_name,
        "pit_lap": pit_lap,
        "total_laps": tot,
        "compound": target_compound,
        "compound_full": compound_full,
        "disruption": disruption,
        "circuit": circuit_name or "Circuit Default",
        "pit_stop_loss_s": pit_loss,
        "fresh_tyre_delta_s": delta_out_lap,
        "success_probability_pct": success_prob,
        "estimated_lead_gap_s": estimated_lead_gap,
        "projected_reentry_position": "P2 / Clean Corridor" if estimated_lead_gap > 0 else "P3 / Traffic Risk",
        "clean_air_corridor_s": clean_air,
        "traffic_clearance_probability_pct": round(min(99.0, 92.0 + (clean_air * 1.8)), 1),
        "recommended_verdict": verdict
    }
