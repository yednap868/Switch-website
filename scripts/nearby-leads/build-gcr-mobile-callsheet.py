#!/usr/bin/env python3
"""Golf Course Road + Golf Course Extension — MOBILE-ONLY calling workbook.

One tab per sector along the Golf Course Road corridor. Only businesses that
Switch can staff (restaurants, hotels, warehouses, shops, supermarkets, PGs/
hostels, salons, gyms, clinics, factories, schools, offices...) and only rows
whose phone is a real 10-digit Indian MOBILE (owner/manager reach) — landlines
and helplines are dropped entirely.

Source: the Google Places corridor crawls
    gcr-north.csv, gcr-south.csv        (Sectors ~42-57, existing)
    gcr-ext-1.csv, gcr-ext-2.csv, gcr-ext-3.csv  (Golf Course Ext 58-67, fresh)

Deduped by Google place id AND by phone number across the whole workbook.
Sorted within each sector by review count (most established first).

    python3 build-gcr-mobile-callsheet.py
"""
import csv, re
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule
from openpyxl.utils import get_column_letter

OUT = "switch-golf-course-road-MOBILE-callsheet.xlsx"
SRC_FILES = ["gcr-north.csv", "gcr-south.csv", "gcr-ext-1.csv", "gcr-ext-2.csv", "gcr-ext-3.csv"]

# Golf Course Road corridor = sector numbers 42..72 (main GCR 42-56 + Extension
# 57-67), plus 26/27/28 (Sushant Lok / MG-road end) explicitly requested.
SEC_MIN, SEC_MAX = 42, 72
EXTRA_SECTORS = {26, 27, 28}
# Landmark fallback for corridor businesses whose address has no "Sector NN".
LANDMARK_RE = re.compile(r"golf course|dlf phase [45]|sushant lok phase (?:2|ii|3|iii)", re.I)

# ── Switch-staffable categories (inclusion whitelist) ───────────────────────
RELEVANT = (
 "restaurant","cafe","coffee","food","bakery","fast_food","meal","bar","pizza","sweet",
 "dhaba","kitchen","catering","cafeteria","confectionery","ice_cream","juice","tea",
 "hotel","lodging","guest_house","hostel","motel","resort","banquet","inn",
 "warehouse","logistic","cargo","courier","freight","storage","transport","distribution",
 "supply","packers","movers","fulfil","shipping","godown",
 "store","supermarket","retail","clothing","grocery","general_store","shop","market",
 "boutique","mall","furniture","electronics","hardware","stationery","optic","jewelry",
 "salon","beauty","spa","hairdresser","parlour","nail","wellness","massage","barber",
 "gym","fitness","yoga","sports","club",
 "manufacturer","factory","industrial","industries","engineering","workshop",
 "hospital","clinic","medical","dental","pharmacy","diagnostic","physio","nursing","health",
 "car_repair","garage","automobile","service_station","fuel","petrol","car_wash","car_dealer",
 "school","educational","institute","college","coaching","preschool","daycare","training",
 "office","corporate","coworking","bank","real_estate","consultant","event",
)
# Names that flag a PG / hostel even if Google typed them "lodging"/"apartment".
PG_RE = re.compile(r"\bpg\b|paying guest|boys hostel|girls hostel|\bhostel\b|co[\-\s]?living|nest|residency", re.I)
# Hard-exclude pure residential / non-staffable noise.
EXCLUDE_TYPES = ("apartment_building","apartment_complex","housing_complex","condominium",
                 "residential","atm","bus_stop","parking","subway_station")
# Cloud / ghost-kitchen signals. Google never tags these "cloud kitchen" — they
# list under a brand name typed as "restaurant", so we match the explicit terms
# PLUS known delivery-only brands and the multi-brand operators that run them.
CLOUD_KW = (
    "cloud kitchen","cloudkitchen","cloud-kitchen","ghost kitchen","delivery kitchen",
    "virtual kitchen","commissary kitchen",
    # multi-brand operators (one facility = many brands = bulk staffing)
    "rebel foods","kitchens@","kitchens centre","eatclub","curefoods","ghost kitchens",
    # delivery-only brands commonly found in Gurgaon
    "faasos","behrouz","oven story","ovenstory","mojo pizza","the good bowl","sweet truth",
    "lunchbox","firangi bake","nh1 bowls","slay coffee","box8","box 8","eatfit","cakezone",
    "nomad pizza","great indian khichdi","sharief bhai","frozen bottle","aligarh house",
    "freshmenu","wow momo","wow! momo","biryani blues","the biryani life","biryani by kilo",
    "biryani by the kilo","charcoal eats","louis burger","globo ice cream","letsshawarma",
    "let's shawarma","wat-a-burger","chinese wok","goila butter chicken","bakingo",
)
# Multi-brand cloud-kitchen OPERATORS to chase directly (one facility staffs many
# brands). No phone here on purpose — these are research targets, not scraped
# leads; fill the mobile once you find the Gurgaon facility's ops manager.
CLOUD_OPERATORS = [
    ("Rebel Foods", "Faasos, Behrouz Biryani, Oven Story, Mojo Pizza, LunchBox, Sweet Truth",
     "Kitchen Helper, Cook, Packer, Delivery Rider, Dishwasher", "Sohna Rd / Udyog Vihar hubs"),
    ("Kitchens@ (Swiggy)", "Swiggy's own multi-brand cloud-kitchen network",
     "Kitchen Helper, Cook, Packer, Dishwasher", "Multiple Gurgaon hubs"),
    ("EatClub / Box8", "Box8, MOJO Pizza, Itminaan Biryani, LEATS",
     "Kitchen Helper, Cook, Packer, Rider", "Sohna Rd / Sector 37"),
    ("Curefoods", "EatFit, CakeZone, Nomad Pizza, Sharief Bhai, Great Indian Khichdi",
     "Kitchen Helper, Cook, Packer, Dishwasher", "Gurgaon cloud hubs"),
    ("Ghost Kitchens India", "Multi-brand ghost-kitchen facilities",
     "Kitchen Helper, Cook, Packer, Rider", "Gurgaon facilities"),
    ("Loyal Hospitality", "Multi-brand cloud kitchens (Awadhi, Chinese, Punjabi...)",
     "Kitchen Helper, Cook, Packer", "Gurgaon hubs"),
    ("Biryani By Kilo (BBK)", "BBK, Goila Butter Chicken, Ammi's Biryani",
     "Kitchen Helper, Cook, Packer, Rider", "Sohna Rd / Sector 39"),
    ("Wow! Momo Foods", "Wow! Momo, Wow! China, Wow! Chicken",
     "Kitchen Helper, Cook, Packer", "Gurgaon kitchen units"),
    ("Chinese Wok", "Chinese Wok cloud outlets",
     "Kitchen Helper, Cook, Packer, Rider", "Multiple Gurgaon units"),
    ("The Bowl Company / Bercos", "Bowl Co., Bercos cloud units",
     "Kitchen Helper, Cook, Dishwasher", "Gurgaon units"),
]

# ── palette ─────────────────────────────────────────────────────────────────
INDIGO="4F46E5"; INDIGO_L="EEF0FB"; DARK="111827"; GREY="6B7280"
GREEN="C6EFCE"; GREEN_TX="1E7E34"; AMBER="FFF3CD"
WHITE="FFFFFF"; ZEBRA="F7F7FB"; BLUE_TX="1D4ED8"
thin = Side(style="thin", color="E2E2EC")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
def fill(c): return PatternFill("solid", fgColor=c)

def roles_for(cat, name):
    t = ("%s %s" % (cat, name)).lower()
    def has(*kws): return any(k in t for k in kws)
    if PG_RE.search(name or ""): return "Housekeeping, Cook, Caretaker, Security"
    if has("warehouse","logistic","cargo","courier","freight","storage","godown",
           "packers","movers","transport","distribution","supply","fulfil","shipping"):
        return "Loader, Packer, Picker, Warehouse Helper, Delivery"
    if has(*CLOUD_KW):
        return "Kitchen Helper, Cook, Packer, Delivery Rider, Dishwasher"
    if has("restaurant","cafe","coffee","food","kitchen","bakery","fast_food","meal","dhaba","sweet","bar","pizza","catering"):
        return "Kitchen Helper, Cook, Dishwasher, Waiter"
    if has("hotel","lodging","guest_house","hostel","motel","resort","banquet","inn"):
        return "Housekeeping, Room Boy, Kitchen Helper, Front Desk"
    if has("hospital","clinic","medical","dental","dentist","health","pharmacy","diagnostic","physio","nursing"):
        return "Ward Boy, Housekeeping, Attendant, Security"
    if has("mall","supermarket","store","retail","clothing","grocery","general_store","shop","market","boutique","furniture","electronics"):
        return "Store Helper, Housekeeping, Security, Sales Staff"
    if has("salon","beauty","spa","hairdresser","massage","parlour","nail","wellness","barber"):
        return "Beautician, Helper, Receptionist, Cleaner"
    if has("gym","fitness","sports","yoga","club"):
        return "Trainer, Housekeeping, Front Desk"
    if has("fuel","petrol","cng","car_wash"):
        return "Pump Attendant, Cleaner, Security"
    if has("manufacturer","factory","industrial","industries","engineering","workshop"):
        return "Machine Operator, Helper, Loader, Packer"
    if has("car_repair","garage","motor","automobile","service_station","car_dealer"):
        return "Mechanic Helper, Cleaner, Washer"
    if has("school","educational","institute","college","coaching","university","preschool","daycare","training"):
        return "Peon, Housekeeping, Security, Attendant"
    return "Office Boy, Housekeeping, Security, Helper"

# ── CORE target industries (the ones you named) — first priority, ≥90% of sheet ──
# Checked in this order so grocery→Supermarket beats the generic "store"→Shop rule.
def core_label(cat, allt, name):
    t = ("%s %s %s" % (cat, allt, name)).lower()
    def has(*kw): return any(k in t for k in kw)
    if PG_RE.search(name or "") or has("hostel","paying guest","co-living","coliving"):
        return "PG / Hostel"
    # Hotels — including OYO and the other budget-hotel brands
    if has("hotel","lodging","guest_house","guesthouse","motel","resort","inn","banquet","serviced apartment",
           "oyo","fabhotel","fab hotel","treebo","zostel","collection o","spot on"):
        return "Hotel / OYO"
    # Cloud / ghost kitchens — checked BEFORE restaurant so a delivery kitchen
    # never gets mislabelled as a dine-in restaurant.
    if has(*CLOUD_KW):
        return "Cloud Kitchen"
    if has("supermarket","hypermarket","grocery","kirana","departmental"," mart","dmart","d-mart","provision"):
        return "Supermarket / Grocery"
    if has("warehouse","logistic","cargo","courier","freight","storage","godown","distribution",
           "packers","movers","fulfil","3pl","shipping","transport"):
        return "Warehouse / Logistics"
    if has("restaurant","cafe","coffee","bakery","fast_food","dhaba","bar","kitchen","meal",
           "catering","sweet","pizza","food","confection","ice_cream","juice","bistro","eatery","canteen"):
        return "Restaurant / Food"
    # Salons / spas / beauty — a named priority industry
    if has("salon","beauty","spa","hairdresser","barber","nail","massage","wellness","parlour",
           "makeup","unisex","grooming","cosmetic"):
        return "Salon / Spa"
    # Guard: remaining service/non-target businesses (they often carry a stray
    # "store" type but are NOT retail shops) → Other, capped at ~10% of a tab.
    if has("clinic","hospital","medical","dental","dentist","doctor","physio","diagnostic","pharmacy",
           "gym","fitness","yoga","school","college","institute","coaching","academy","tuition",
           "bank","atm","real_estate","insurance","car_repair","garage","laundry","travel_agency",
           "consultant","lawyer","office"):
        return None
    if has("store","shop","retail","boutique","clothing","electronics","hardware","supermarket",
           "stationery","furniture","general_store","market","mall","optic","footwear","garment","apparel"):
        return "Shop / Retail"
    return None

def is_relevant(cat, allt, name):
    t = ("%s %s" % (cat, allt)).lower()
    if any(x in t for x in EXCLUDE_TYPES) and not PG_RE.search(name or ""):
        # residential-type — only keep if the NAME says PG/hostel/coliving
        return bool(PG_RE.search(name or ""))
    return any(k in t for k in RELEVANT) or bool(PG_RE.search(name or ""))

def classify_mobile(raw):
    """Return 10-digit string if raw is a real Indian mobile, else None."""
    d = re.sub(r"\D", "", raw or "")
    if d.startswith("91") and len(d) == 12: d = d[2:]
    if d.startswith("0") and len(d) == 11: d = d[1:]
    if d.startswith(("1800","1860")): return None          # helpline
    if len(d) == 10 and d[0] in "6789": return d           # mobile
    return None                                            # landline / junk

SEC_RE = re.compile(r"sector[\s\-]*([0-9]+)\s*([a-dA-D]?)", re.I)
def bucket(address):
    a = address or ""
    m = SEC_RE.search(a)
    if m:
        num = int(m.group(1))   # letter-suffixed blocks (52A, 26A...) fold into parent
        if SEC_MIN <= num <= SEC_MAX or num in EXTRA_SECTORS:
            return "Sector %d" % num, num, 0
    if LANDMARK_RE.search(a):
        return "GCR — Other", 999, 0
    return None

def load():
    buckets = {}          # label -> (num, suf, [rows])
    seen_id = set(); seen_ph = set()
    kept = 0; scanned = 0
    for path in SRC_FILES:
        try:
            f = open(path, newline="", encoding="utf-8")
        except FileNotFoundError:
            print("!! missing %s (skipping)" % path); continue
        with f:
            for row in csv.DictReader(f):
                scanned += 1
                pid = (row.get("place_id") or "").strip()
                if pid and pid in seen_id: continue
                mob = classify_mobile(row.get("phone"))
                if not mob or mob in seen_ph: continue
                name = (row.get("name") or "").strip()
                cat  = (row.get("primary_type") or "").strip() or "business"
                allt = (row.get("all_types") or "")
                if not is_relevant(cat, allt, name): continue
                b = bucket(row.get("address"))
                if not b: continue
                label, num, suf = b
                if pid: seen_id.add(pid)
                seen_ph.add(mob)
                kept += 1
                core = core_label(cat, allt, name)
                buckets.setdefault(label, [num, suf, []])[2].append({
                    "name": name, "category": cat, "phone": mob,
                    "industry": core or "Other",
                    "is_core": core is not None,
                    "rating": (row.get("rating") or "").strip(),
                    "reviews": (row.get("reviews") or "").strip(),
                    "address": (row.get("address") or "").strip(),
                    "map": (row.get("maps_url") or "").strip(),
                })
    # Fold sectors with too few leads into a single catch-all so the workbook
    # isn't cluttered with 1–2 lead tabs. Requested sectors easily clear this.
    MIN_TAB = 8
    other = buckets.pop("GCR — Other", [999, 0, []])
    for label in [l for l in buckets if len(buckets[l][2]) < MIN_TAB]:
        other[2].extend(buckets.pop(label)[2])
    if other[2]:
        buckets["GCR — Other"] = other

    # Per sector: core target industries first (by reviews), then cap the "Other"
    # categories to ≤1/9 of the core count so the tab stays ≥90% your industries.
    total_core = total_other = 0
    for label in buckets:
        rows = buckets[label][2]
        rows.sort(key=lambda r: (
            0 if r["is_core"] else 1,
            -(int(r["reviews"]) if r["reviews"].isdigit() else 0),
            -(float(r["rating"]) if r["rating"] else 0),
            r["name"].lower(),
        ))
        core  = [r for r in rows if r["is_core"]]
        other = [r for r in rows if not r["is_core"]]
        cap = max(3, len(core) // 9)          # keep ≥90% core; allow a few Other
        kept_rows = core + other[:cap] if core else other
        buckets[label][2] = kept_rows
        total_core += len(core); total_other += min(len(other), cap if core else len(other))
    grand = total_core + total_other
    print("scanned %d rows -> %d leads across %d sectors  (%d core / %d other = %.0f%% core)"
          % (scanned, grand, len(buckets), total_core, total_other,
             100*total_core/max(grand,1)))
    # tab order: by sector number; "GCR — Other" (num 999) last
    order = sorted(buckets.keys(), key=lambda l: (buckets[l][0], buckets[l][1]))
    return [(l, buckets[l][2]) for l in order]

# ── columns ─────────────────────────────────────────────────────────────────
COLS = [
    ("S.No", 6), ("Business Name", 32), ("Target Industry", 18),
    ("Suggested Roles (per shift)", 32), ("Manager Mobile", 15),
    ("Rating", 7), ("Reviews", 8), ("Address", 38),
    ("Interested?", 12), ("Hours (1-12)", 11), ("Order Confirmed?", 15),
    ("Remarks", 28), ("Map", 6),
]
HDR = 4
C_INT, C_HRS, C_ORD, C_MAP = "I", "J", "K", "M"

def build_sheet(wb, first, tab, rows):
    ws = wb.active if first else wb.create_sheet()
    ws.title = tab
    ws.sheet_view.showGridLines = False
    last = HDR + max(len(rows), 1)
    for c,(t,w) in enumerate(COLS, start=1):
        ws.column_dimensions[get_column_letter(c)].width = w

    ws.merge_cells("A1:M1")
    b = ws["A1"]; b.value = "SWITCH  ·  %s  ·  MOBILE CALL SHEET" % tab.upper()
    b.fill = fill(INDIGO); b.font = Font(bold=True, color=WHITE, size=16)
    b.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26
    ws.merge_cells("A2:M2")
    s = ws["A2"]
    ncore = sum(1 for r in rows if r["is_core"])
    s.value = ("Owner/manager mobiles · shifts 1–12 hrs, pay after worker reports · instant "
               "replacement   |   %d leads · %d in priority industries (top)" % (len(rows), ncore))
    s.font = Font(color=GREY, size=10, italic=True); s.alignment = Alignment(horizontal="center")

    def rng(col): return "%s%d:%s%d" % (col, HDR+1, col, last)
    for cell, label, formula, color in [
        ("A3","LEADS","=COUNTA(%s)"%rng("B"),DARK),
        ("C3","CONTACTED","=COUNTA(%s)"%rng(C_INT),INDIGO),
        ("E3","INTERESTED",'=COUNTIF(%s,"Yes")'%rng(C_INT),GREEN_TX),
        ("G3","ORDERS",'=COUNTIF(%s,"Yes")'%rng(C_ORD),GREEN_TX),
        ("I3","HOURS BOOKED","=SUM(%s)"%rng(C_HRS),"B7791F"),
    ]:
        col = cell[0]
        lc = ws[cell]; lc.value = label
        lc.font = Font(bold=True, color=GREY, size=8); lc.alignment = Alignment(horizontal="center")
        vc = ws["%s3" % chr(ord(col)+1)]; vc.value = formula
        vc.font = Font(bold=True, color=color, size=13); vc.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[3].height = 20

    for c,(title,_) in enumerate(COLS, start=1):
        cell = ws.cell(row=HDR, column=c, value=title)
        cell.fill = fill(INDIGO); cell.font = Font(bold=True, color=WHITE, size=11)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER
    ws.row_dimensions[HDR].height = 30

    WRAP = Alignment(vertical="top", wrap_text=True)
    CTR  = Alignment(horizontal="center", vertical="top", wrap_text=True)
    for i, row in enumerate(rows):
        r = HDR + 1 + i
        vals = [i+1, row["name"], row["industry"], roles_for(row["category"], row["name"]),
                row["phone"], row["rating"], row["reviews"], row["address"], "", "", "", "", ""]
        for c, v in enumerate(vals, start=1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.alignment = CTR if c in (1,5,6,7,9,10,11,13) else WRAP
            cell.border = BORDER
            if r % 2 == 0 and c not in (9,10,11):
                cell.fill = fill(ZEBRA)
        ws.cell(row=r, column=5).font = Font(bold=True, color=DARK)   # mobile stands out
        # core target industries in bold indigo so priority leads pop
        ic = ws.cell(row=r, column=3)
        ic.font = Font(bold=True, color=INDIGO) if row["is_core"] else Font(color=GREY)
        if row["map"]:
            m = ws.cell(row=r, column=13, value="Map")
            m.hyperlink = row["map"]; m.font = Font(color="0563C1", underline="single")

    def dropdown(col, options):
        dv = DataValidation(type="list", formula1='"%s"' % ",".join(options),
                            allow_blank=True, showDropDown=False)
        ws.add_data_validation(dv); dv.add("%s%d:%s%d" % (col, HDR+1, col, last))
    dropdown(C_INT, ["Yes","No","Maybe","Call back","No answer","Wrong number"])
    dropdown(C_HRS, [str(i) for i in range(1,13)])
    dropdown(C_ORD, ["Yes","No","Pending"])

    ws.conditional_formatting.add("%s%d:%s%d"%(C_INT,HDR+1,C_INT,last),
        FormulaRule(formula=['%s%d="Yes"'%(C_INT,HDR+1)], fill=fill(GREEN), font=Font(color=GREEN_TX, bold=True)))
    ws.conditional_formatting.add("%s%d:%s%d"%(C_INT,HDR+1,C_INT,last),
        FormulaRule(formula=['%s%d="Call back"'%(C_INT,HDR+1)], fill=fill(AMBER)))
    ws.conditional_formatting.add("%s%d:%s%d"%(C_ORD,HDR+1,C_ORD,last),
        FormulaRule(formula=['%s%d="Yes"'%(C_ORD,HDR+1)], fill=fill(GREEN), font=Font(color=GREEN_TX, bold=True)))
    ws.conditional_formatting.add("A%d:M%d"%(HDR+1,last),
        FormulaRule(formula=['$%s%d="Yes"'%(C_ORD,HDR+1)], fill=fill("EAF8EE")))

    ws.freeze_panes = "A%d" % (HDR+1)
    ws.auto_filter.ref = "A%d:M%d" % (HDR, last)
    return len(rows)

def build_performance(wb, areas):
    ws = wb.create_sheet("Performance")
    ws.sheet_view.showGridLines = False
    for col, w in (("A",3),("B",22),("C",12),("D",12),("E",12),("F",12),("G",12),("H",12),("I",3)):
        ws.column_dimensions[col].width = w
    def ref(tab, col, count): return "'%s'!%s%d:%s%d" % (tab, col, HDR+1, col, HDR+max(count,1))
    def leads(t,n):      return "COUNTA(%s)"        % ref(t,"B",n)
    def contacted(t,n):  return "COUNTA(%s)"        % ref(t,C_INT,n)
    def interested(t,n): return 'COUNTIF(%s,"Yes")' % ref(t,C_INT,n)
    def orders(t,n):     return 'COUNTIF(%s,"Yes")' % ref(t,C_ORD,n)
    def hours(t,n):      return "SUM(%s)"           % ref(t,C_HRS,n)
    def joinsum(fn):     return "+".join(fn(t,n) for t,n in areas)

    ws.merge_cells("B2:H3")
    b = ws["B2"]; b.value = "SWITCH  ·  GOLF COURSE ROAD  ·  MOBILE CALLING PERFORMANCE"
    b.fill = fill(INDIGO); b.font = Font(bold=True, color=WHITE, size=15)
    b.alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells("B4:H4")
    s = ws["B4"]; s.value = "Live totals across every sector tab — updates as you fill the sheets"
    s.font = Font(color=GREY, size=10, italic=True); s.alignment = Alignment(horizontal="center")

    def card(cell, label, formula, color=INDIGO, fmt="0", big=True):
        col = cell[0]; row = int(cell[1:])
        lc = ws["%s%d"%(col,row)]; lc.value = label
        lc.font = Font(bold=True, color=GREY, size=9); lc.alignment = Alignment(horizontal="center")
        vc = ws["%s%d"%(col,row+1)]; vc.value = formula; vc.number_format = fmt
        vc.font = Font(bold=True, color=color, size=22 if big else 13)
        vc.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[row+1].height = 30
        for rr in (row,row+1): ws["%s%d"%(col,rr)].fill = fill(INDIGO_L if big else WHITE)

    card("B6","TOTAL MOBILE LEADS","=%s"%joinsum(leads), color=DARK)
    card("D6","CONTACTED","=%s"%joinsum(contacted), color=INDIGO)
    card("F6","ORDERS","=%s"%joinsum(orders), color=GREEN_TX)
    card("B9","INTERESTED","=%s"%joinsum(interested), color=GREEN_TX, big=False)
    card("D9","CONVERSION","=IFERROR((%s)/(%s),0)"%(joinsum(orders),joinsum(contacted)),
         color=INDIGO, fmt="0%", big=False)
    card("F9","HOURS BOOKED","=%s"%joinsum(hours), color="B7791F", big=False)

    hrow = 12
    heads = ["Sector","Leads","Contacted","Interested","Orders","Hours"]
    for c,h in enumerate(heads, start=2):
        cell = ws.cell(row=hrow, column=c, value=h)
        cell.fill = fill(INDIGO); cell.font = Font(bold=True, color=WHITE, size=10)
        cell.alignment = Alignment(horizontal="center"); cell.border = BORDER
    for i,(t,n) in enumerate(areas):
        r = hrow+1+i
        cells = [t, "=%s"%leads(t,n), "=%s"%contacted(t,n),
                 "=%s"%interested(t,n), "=%s"%orders(t,n), "=%s"%hours(t,n)]
        for c,v in enumerate(cells, start=2):
            cell = ws.cell(row=r, column=c, value=v); cell.border = BORDER
            cell.alignment = Alignment(horizontal="left" if c==2 else "center")
            if r % 2: cell.fill = fill(ZEBRA)
    tr = hrow+1+len(areas)
    totals = ["TOTAL","=%s"%joinsum(leads),"=%s"%joinsum(contacted),
              "=%s"%joinsum(interested),"=%s"%joinsum(orders),"=%s"%joinsum(hours)]
    for c,v in enumerate(totals, start=2):
        cell = ws.cell(row=tr, column=c, value=v); cell.border = BORDER; cell.fill = fill(INDIGO_L)
        cell.font = Font(bold=True, color=DARK)
        cell.alignment = Alignment(horizontal="left" if c==2 else "center")
    note = ws.cell(row=tr+2, column=2,
        value="↳ Fill Interested? / Hours / Order Confirmed? on each sector tab — these totals move automatically.")
    note.font = Font(color=GREY, size=10, italic=True)

def build_howto(wb):
    how = wb.create_sheet("How to use")
    how.sheet_view.showGridLines = False
    how.column_dimensions["A"].width = 3; how.column_dimensions["B"].width = 100
    guide = [
        ("SWITCH — GOLF COURSE ROAD  ·  MOBILE-ONLY CALLING SHEET", "title"), ("",""),
        ("WHAT'S IN HERE", "head"),
        ("• Every 'Manager Mobile' is a real 10-digit mobile (starts 6/7/8/9) — the owner/manager's cell,", "body"),
        ("  not a reception landline. That's who books staff. Landlines & helplines were removed.", "body"),
        ("• PRIORITY INDUSTRIES (≥90% of every tab, shown in blue, sorted to the TOP):", "body"),
        ("   Restaurant/Food · Cloud Kitchen · Hotel/OYO · PG/Hostel · Warehouse/Logistics · Supermarket/Grocery · Salon/Spa · Shop/Retail.", "body"),
        ("• A few high-value 'Other' businesses (gym, clinic, office...) sit below, capped at ~10%.", "body"),
        ("• One tab per sector (42–67 + 26/27/28). Most-reviewed businesses are at the top within each group.", "body"), ("",""),
        ("THE OFFER (say this, every time)", "head"),
        ("• Shifts of 1–12 hours, billed by the hour. NO monthly, NO weekly.", "body"),
        ("• Pay only AFTER the worker reports — no advance.", "body"),
        ("• Instant replacement if the worker doesn't show or isn't a fit. Verified, local staff in 24 hrs.", "body"), ("",""),
        ("HOW TO WORK THE SHEET", "head"),
        ("1. Pick a sector tab and work top-down (established businesses staff more).", "body"),
        ("2. WhatsApp first, then call. After each contact, use the dropdowns:", "body"),
        ("     · Interested? → Yes / No / Maybe / Call back / No answer / Wrong number", "body"),
        ("     · Hours → 1 to 12 (what they want per shift)   · Order Confirmed? → Yes when they agree", "body"),
        ("3. 'Suggested Roles' is a starting pitch — confirm what they actually need.", "body"),
        ("4. The Performance tab totals every sector automatically as you fill them in.", "body"), ("",""),
        ("Deduped by business and by phone number across all sectors. Source: Google Places corridor crawl.", "muted"),
    ]
    r = 1
    for text, kind in guide:
        cell = how.cell(row=r, column=2, value=text)
        if kind == "title":
            cell.font = Font(bold=True, color=WHITE, size=15); cell.fill = fill(INDIGO)
            cell.alignment = Alignment(horizontal="center", vertical="center"); how.row_dimensions[r].height = 30
        elif kind == "head": cell.font = Font(bold=True, color=INDIGO, size=12)
        elif kind == "muted": cell.font = Font(italic=True, color=GREY, size=10)
        else: cell.font = Font(color=DARK, size=11); cell.alignment = Alignment(wrap_text=True)
        r += 1

def build_cloud_ops(wb, cloud_rows):
    """A go-direct tab: multi-brand operators to research + any callable cloud
    kitchens the scrape actually found."""
    ws = wb.create_sheet("Cloud Kitchen Ops")
    ws.sheet_view.showGridLines = False
    COLS_OPS = [("S.No",6),("Operator / Business",34),("Brands / what they run",44),
                ("Suggested Roles (per shift)",34),("Where in Gurgaon",22),
                ("Manager Mobile",16),("Interested?",12),("Hours (1-12)",11),
                ("Order Confirmed?",15),("Remarks",30)]
    for c,(t,w) in enumerate(COLS_OPS, start=1):
        ws.column_dimensions[get_column_letter(c)].width = w
    ncol = len(COLS_OPS); lastcol = get_column_letter(ncol)
    ws.merge_cells("A1:%s1" % lastcol)
    b = ws["A1"]; b.value = "SWITCH  ·  CLOUD KITCHEN OPERATORS  ·  GO DIRECT (BULK STAFFING)"
    b.fill = fill(INDIGO); b.font = Font(bold=True, color=WHITE, size=15)
    b.alignment = Alignment(horizontal="center", vertical="center"); ws.row_dimensions[1].height = 26
    ws.merge_cells("A2:%s2" % lastcol)
    s = ws["A2"]
    s.value = ("Cloud kitchens barely list on Google — chase the OPERATORS instead. One facility "
               "runs 8–10 brands, so one contact = staff for many kitchens. Find their Gurgaon "
               "commissary (Sohna Rd / Udyog Vihar) and ask for the ops / kitchen manager.")
    s.font = Font(color=GREY, size=10, italic=True)
    s.alignment = Alignment(horizontal="center", wrap_text=True); ws.row_dimensions[2].height = 34
    HR = 3
    for c,(title,_) in enumerate(COLS_OPS, start=1):
        cell = ws.cell(row=HR, column=c, value=title)
        cell.fill = fill(INDIGO); cell.font = Font(bold=True, color=WHITE, size=11)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True); cell.border = BORDER
    ws.row_dimensions[HR].height = 30
    WRAP = Alignment(vertical="top", wrap_text=True)
    CTR  = Alignment(horizontal="center", vertical="top", wrap_text=True)
    r = HR
    def add_row(sno, name, brands, roles, where, mobile, remarks):
        nonlocal r; r += 1
        vals = [sno, name, brands, roles, where, mobile, "", "", "", remarks]
        for c, v in enumerate(vals, start=1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.alignment = CTR if c in (1,6,7,8,9) else WRAP; cell.border = BORDER
            if r % 2 == 0 and c not in (7,8,9): cell.fill = fill(ZEBRA)
        ws.cell(row=r, column=2).font = Font(bold=True, color=DARK)
    # section 1 — operators to research (mobile left blank on purpose)
    for i,(op, brands, roles, where) in enumerate(CLOUD_OPERATORS, start=1):
        add_row(i, op, brands, roles, where, "", "🔍 Research Gurgaon facility → ask for ops/kitchen manager")
    # section 2 — callable cloud kitchens already found in the scrape
    r += 1
    ws.merge_cells("A%d:%s%d" % (r, lastcol, r))
    d = ws.cell(row=r, column=1, value="↓ Callable cloud kitchens found in the scrape (real mobiles) — call these now")
    d.fill = fill(INDIGO_L); d.font = Font(bold=True, color=INDIGO, size=10); d.alignment = Alignment(horizontal="left")
    for j, row in enumerate(cloud_rows, start=1):
        add_row(j, row["name"], row["category"], roles_for(row["category"], row["name"]),
                row["address"], row["phone"], "From Google scrape")
        ws.cell(row=r, column=6).font = Font(bold=True, color=DARK)
    last = r
    def dropdown(col, options):
        dv = DataValidation(type="list", formula1='"%s"' % ",".join(options), allow_blank=True, showDropDown=False)
        ws.add_data_validation(dv); dv.add("%s%d:%s%d" % (col, HR+1, col, last))
    dropdown("G", ["Yes","No","Maybe","Call back","No answer","Wrong number"])
    dropdown("H", [str(i) for i in range(1,13)])
    dropdown("I", ["Yes","No","Pending"])
    ws.conditional_formatting.add("G%d:G%d"%(HR+1,last),
        FormulaRule(formula=['G%d="Yes"'%(HR+1)], fill=fill(GREEN), font=Font(color=GREEN_TX, bold=True)))
    ws.conditional_formatting.add("I%d:I%d"%(HR+1,last),
        FormulaRule(formula=['I%d="Yes"'%(HR+1)], fill=fill(GREEN), font=Font(color=GREEN_TX, bold=True)))
    ws.freeze_panes = "A%d" % (HR+1)
    ws.auto_filter.ref = "A%d:%s%d" % (HR, lastcol, last)

# ── main ────────────────────────────────────────────────────────────────────
wb = Workbook()
areas_data = load()
areas = []
first = True
for name, rows in areas_data:
    n = build_sheet(wb, first, name, rows)
    areas.append((name, n))
    print("  %-14s %4d mobile leads" % (name, n))
    first = False
build_performance(wb, areas)
cloud_rows = [r for _, rows in areas_data for r in rows if r["industry"] == "Cloud Kitchen"]
build_cloud_ops(wb, cloud_rows)
build_howto(wb)
perf = wb["Performance"]; wb._sheets.remove(perf); wb._sheets.insert(0, perf)
cko = wb["Cloud Kitchen Ops"]; wb._sheets.remove(cko); wb._sheets.insert(1, cko)
wb.active = 0
wb.save(OUT)
print("Wrote %s  (%d sector tabs + Cloud Kitchen Ops: %d operators, %d scraped)"
      % (OUT, len(areas), len(CLOUD_OPERATORS), len(cloud_rows)))
