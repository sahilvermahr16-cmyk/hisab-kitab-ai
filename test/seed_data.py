# test/seed_data.py — test shuru hone se pehle test DB mein kaun-kaun pehle se hoga.
#
# Har test statement se pehle reset_test_db.py DB khaali karke YE list daalta hai,
# taaki har test ek hi haalat se shuru ho (independent test cases).
# Naam badalne / jodne ho to sirf yahi file badlo.

# Employees: (naam, role)
EMPLOYEES = [
    ("Ram", None),
    ("Sohan", None),
    ("Kitanu", "driver"),
]

# Customers
CUSTOMERS = [
    "Suresh Traders",
    "Sharma ji",
]

# Suppliers: (naam, type)
SUPPLIERS = [
    ("SBI Bhatta", "bhatta"),
]

# Family members: (naam, rishta)
FAMILY = [
    ("Papa", "papa"),
]

# Maal ki jagahen (Material Movement inhe pehchane, "storage hai ya site?" na pooche)
STORAGE_LOCATIONS = ["Gudam", "Godam", "Shop", "Dukaan"]

# Purana baaki / shuru ka cash: (khaata, naam, amount, direction)
#   direction: "lena" (humein lena hai) | "dena" (humein dena hai) | "cash"
OPENING_BALANCES = [
    ("customer", "Suresh Traders", 6000, "lena"),
    ("supplier", "SBI Bhatta", 5000, "dena"),
    ("cash", None, 40000, "cash"),
]
# Opening balance ki tareekh = test date se itne din pehle
OPENING_DAYS_BEFORE = 30

# Jaan-boojh ke DB mein NAHI hain (naye naam pe role ka sawaal test karne ke liye):
#   Mukesh, Bablu, Jagdish

# Hindi (Devanagari) run: wahi log, naam Devanagari mein — jaise Hindi mein likhne wala user likhega.
# Runner role ka jawaab dene ke liye bhi isi map se naam milata hai.
HINDI_NAMES = {
    "Ram": "राम",
    "Sohan": "सोहन",
    "Kitanu": "कितनू",
    "Suresh Traders": "सुरेश ट्रेडर्स",
    "Sharma ji": "शर्मा जी",
    "SBI Bhatta": "एसबीआई भट्टा",
    "Papa": "पापा",
    "Mukesh": "मुकेश",
    "Gudam": "गोदाम",
    "Shop": "दुकान",
}
# Hindi run mein ye jagahen bhi storage ke roop mein pehchani jayein
HINDI_STORAGE_LOCATIONS = ["गोदाम", "दुकान"]


def name_for(name, lang):
    """Seed ka naam us bhasha mein jisme test chal raha hai."""
    if lang == "hindi" and name:
        return HINDI_NAMES.get(name, name)
    return name
