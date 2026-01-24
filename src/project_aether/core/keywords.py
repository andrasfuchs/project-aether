"""
Keyword definitions for Project Aether.
Structured by language and sentiment (positive/anomalous vs negative/false-positive).
"""

from typing import Dict, List, Set

# Default keyword dictionary
DEFAULT_KEYWORDS = {
    "English": {
        "positive": [
            "anomalous heat", "excess energy", "over-unity", "cold fusion",
            "LENR", "LANR", "transmutation", "plasma vortex", "plasmoid",
            "excess enthalpy", "non-chemical heat", "lattice assisted",
            "condensed matter nuclear", "Rydberg matter"
        ],
        "negative": [
            "spark plug", "ignition system", "internal combustion",
            "automotive", "engine", "combustion chamber",
            "fuel injection", "cylinder head", "piston"
        ]
    },
    "Russian": {
        "positive": [
            "аномальное тепловыделение", "избыточное энерговыделение",
            "холодный синтез", "холодный ядерный синтез",
            "трансмутация элементов", "плазменный вихрь",
            "тлеющий разряд", "электролизная плазма"
        ],
        "negative": [
            "свеча зажигания", "система зажигания", "внутреннего сгорания",
            "автомобильный", "двигатель", "камера сгорания"
        ]
    },
    "Polish": {
        "positive": [
            "anomalne ciepło", "nadmiar energii", "ponadjednostkowy", "zimna fuzja",
            "LENR", "LANR", "transmutacja", "wir plazmowy", "plazmoid",
            "nadmiar entalpii", "ciepło niechemiczne", "wspomagany siecią",
            "skondensowana materia jądrowa", "materia Rydberga"
        ],
        "negative": [
            "świeca zapłonowa", "układ zapłonowy", "spalanie wewnętrzne",
            "motoryzacyjny", "silnik", "komora spalania",
            "wtrysk paliwa", "głowica cylindra", "tłok"
        ]
    },
    "Romanian": {
        "positive": [
            "căldură anomală", "energie în exces", "peste-unitate", "fuziune rece",
            "LENR", "LANR", "transmutare", "vortex de plasmă", "plazmoid",
            "entalpie în exces", "căldură non-chimică", "asistat de rețea",
            "materie nucleară condensată", "materie Rydberg"
        ],
        "negative": [
            "bujie", "sistem de aprindere", "combustie internă",
            "automotive", "motor", "cameră de ardere",
            "injecție de combustibil", "chiuloasă", "piston"
        ]
    },
    "Czech": {
        "positive": [
            "anomální teplo", "přebytek energie", "nad-jednotkový", "studená fúze",
            "LENR", "LANR", "transmutace", "plazmový vír", "plazmoid",
            "přebytek entalpie", "nechemické teplo", "mřížkou asistovaný",
            "kondenzovaná jaderná hmota", "Rydbergova hmota"
        ],
        "negative": [
            "zapalovací svíčka", "zapalovací systém", "vnitřní spalování",
            "automobilový", "motor", "spalovací komora",
            "vstřikování paliva", "hlava válce", "píst"
        ]
    },
    "Dutch": {
        "positive": [
            "afwijkende warmte", "overtollige energie", "boven-eenheid", "koude fusie",
            "LENR", "LANR", "transmutatie", "plasma vortex", "plasmoïde",
            "overtollige enthalpie", "niet-chemische warmte", "rooster-ondersteund",
            "gecondenseerde materie nucleair", "Rydberg-materie"
        ],
        "negative": [
            "bougie", "ontstekingssysteem", "interne verbranding",
            "automobiel", "motor", "verbrandingskamer",
            "brandstofinjectie", "cilinderkop", "zuiger"
        ]
    },
    "Spanish": {
        "positive": [
            "calor anómalo", "energía excedente", "sobre-unidad", "fusión fría",
            "LENR", "LANR", "transmutación", "vórtice de plasma", "plasmoide",
            "entalpía excedente", "calor no químico", "asistido por red",
            "materia nuclear condensada", "materia de Rydberg"
        ],
        "negative": [
            "bujía", "sistema de encendido", "combustión interna",
            "automotriz", "motor", "cámara de combustión",
            "inyección de combustible", "culata", "pistón"
        ]
    },
    "Italian": {
        "positive": [
            "calore anomalo", "energia in eccesso", "sovra-unità", "fusione fredda",
            "LENR", "LANR", "trasmutazione", "vortice di plasma", "plasmoide",
            "entalpia in eccesso", "calore non chimico", "assistito da reticolo",
            "materia nucleare condensata", "materia di Rydberg"
        ],
        "negative": [
            "candela", "sistema di accensione", "combustione interna",
            "automobilistico", "motore", "camera di combustione",
            "iniezione di carburante", "testata", "pistone"
        ]
    },
    "Swedish": {
        "positive": [
            "anomal värme", "överskottsenergi", "över-enhet", "kall fusion",
            "LENR", "LANR", "transmutation", "plasmavortex", "plasmoid",
            "överskottsentalpi", "icke-kemisk värme", "gitterassisterad",
            "kondenserad materiens kärnfysik", "Rydberg-materia"
        ],
        "negative": [
            "tändstift", "tändsystem", "förbränningsmotor",
            "fordon", "motor", "förbränningskammare",
            "bränsleinsprutning", "topplock", "kolv"
        ]
    },
    "Norwegian": {
        "positive": [
            "anomal varme", "overskuddsenergi", "over-enhet", "kald fusjon",
            "LENR", "LANR", "transmutasjon", "plasmavorteks", "plasmoid",
            "overskuddsentalpi", "ikke-kjemisk varme", "gitterassistert",
            "kondensert materie kjernefysikk", "Rydberg-materie"
        ],
        "negative": [
            "tennplugg", "tenningssystem", "forbrenningsmotor",
            "bilindustri", "motor", "forbrenningskammer",
            "drivstoffinnsprøytning", "topplokk", "stempel"
        ]
    },
    "Finnish": {
        "positive": [
            "poikkeava lämpö", "ylimääräinen energia", "yli-yksikkö", "kylmä fuusio",
            "LENR", "LANR", "transmutaatio", "plasmapyörre", "plasmoidi",
            "ylimääräinen entalpia", "ei-kemiallinen lämpö", "hilalla avustettu",
            "tiivistynyt aineen ydinfysiikka", "Rydberg-aine"
        ],
        "negative": [
            "sytytystulppa", "syttymisjärjestelmä", "sisäinen palaminen",
            "autoteollisuus", "moottori", "palotila",
            "polttoaineen ruiskutus", "sylinterinkansi", "mäntä"
        ]
    }
}

def get_flattened_keywords(language_config: Dict[str, Dict[str, List[str]]]) -> tuple[Set[str], Set[str]]:
    """
    Flatten the structured keyword dict into two sets (positive and negative)
    for efficient lookup by the AnalystAgent.
    """
    positive_set = set()
    negative_set = set()

    for lang, categories in language_config.items():
        positive_set.update(categories.get("positive", []))
        negative_set.update(categories.get("negative", []))

    return positive_set, negative_set
