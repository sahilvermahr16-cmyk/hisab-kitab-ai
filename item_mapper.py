"""
Normalize different names of the same inventory item.
"""

LOCATION_ALIASES = {
    "gudam": "गोदाम",
    "godam": "गोदाम",
    "warehouse": "गोदाम",
    "godown": "गोदाम",
    "gudaam": "गोदाम",
    "गोदाम": "गोदाम",

    "palate": "पलाट",
    "plot": "पलाट",
    "पलाट": "पलाट",

    "shop": "दुकान",
    "dukaan": "दुकान",
    "दुकान": "दुकान",

    "site": "साइट",
    "sites": "साइट",
    "साइट": "साइट",

    "home": "घर",
    "ghar": "घर",
    "घर": "घर",
}

ITEM_ALIASES = {

    # Iron
    "sariya": "सरिया",
    "rod": "सरिया",
    "iron rod": "सरिया",
    "सरिया": "सरिया",

    # Windows
    "window": "जंगला",
    "windows": "जंगला",
    "jangla": "जंगला",
    "jaangla": "जंगला",
    "jangalaa": "जंगला",
    "जंगला": "जंगला",

    # Frames
    "frame": "चौखट",
    "frames": "चौखट",
    "door frame": "चौखट",
    "door frames": "चौखट",
    "chokhat": "चौखट",
    "chokhath": "चौखट",
    "चौखट": "चौखट",

    # Single Door
    "door": "पल्ला",
    "doors": "पल्ला",
    "single door": "पल्ला",
    "single doors": "पल्ला",
    "palaa": "पल्ला",
    "palla": "पल्ला",
    "पल्ला": "पल्ला",

    # Double Door
    "double door": "जोड़ी",
    "double doors": "जोड़ी",
    "jodi": "जोड़ी",
    "जोड़ी": "जोड़ी",

    # Roshandan
    "roshan dan": "रोशनदान",
    "roshandan": "रोशनदान",
    "roshan_dan": "रोशनदान",
    "roshandaan": "रोशनदान",
    "रोशनदान": "रोशनदान",

    # Iron Gate
    "iron gate": "लोहे का गेट",
    "iron gates": "लोहे का गेट",
    "loha gate": "लोहे का गेट",
    "loha gates": "लोहे का गेट",
    "लोहे का गेट": "लोहे का गेट",

    # Iron Mesh
    "iron mesh": "लोहे की जाली",
    "iron grill": "लोहे की जाली",
    "loha jaal": "लोहे की जाली",
    "loha jaali": "लोहे की जाली",
    "jaal": "लोहे की जाली",
    "jaali": "लोहे की जाली",
    "लोहे की जाली": "लोहे की जाली",

    # Wood
    "balita": "बल्लीता",
    "wood waste": "बल्लीता",
    "balita": "बल्लीता",
    "kadi": "कड़ी",
    "कड़ी": "कड़ी",
    "fate": "फट्टे",
    "फट्टे": "फट्टे",

    # Furniture
    "furniture": "फर्नीचर",
    "almari": "फर्नीचर",
    "bed": "फर्नीचर",
    "table": "फर्नीचर",
    "chair": "फर्नीचर",
    "sofa": "फर्नीचर",
    "फर्नीचर": "फर्नीचर",

    # Bricks
    "brick": "ईंट",
    "bricks": "ईंट",
    "eent": "ईंट",
    "ईंट": "ईंट",
    "malba": "मलबा",
    "मलबा": "मलबा",

    # Paint
    "paint": "पेंट",
    "पेंट": "पेंट",
    "primer": "प्राइमर",
    "प्राइमर": "प्राइमर",
    "puti": "पुट्टी",
    "पुट्टी": "पुट्टी",

    # Cement
    "cement": "सीमेंट",
    "cement bag": "सीमेंट",
    "cement bags": "सीमेंट",
    "सीमेंट": "सीमेंट",

    # Misc
    "misc": "अन्य",
    "miscellaneous": "अन्य",
    "अन्य": "अन्य",
}

def normalize_item(item_name: str) -> str:
    """
    Normalizes an item name to its canonical (Hindi) form using
    ITEM_ALIASES. Falls back to the original (lowercase, stripped)
    name if no alias match is found, so unknown items don't crash
    or get silently dropped.
    """
    if not item_name:
        return ""

    key = item_name.strip().lower()
    return ITEM_ALIASES.get(key, item_name.strip())

def normalize_location(location_name: str) -> str:
    """
    Normalizes a location name to its canonical (Hindi) form using
    LOCATION_ALIASES. Falls back to the original (lowercase, stripped)
    name if no alias match is found.
    """
    if not location_name:
        return ""

    key = location_name.strip().lower()
    return LOCATION_ALIASES.get(key, location_name.strip())



