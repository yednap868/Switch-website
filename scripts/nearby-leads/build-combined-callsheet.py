#!/usr/bin/env python3
"""Combined Switch calling workbook — one tab per area, phone numbers only.

Tabs:
  • Udyog Vihar  — call sheet (from udyog-vihar-leads.csv, Google Places)
  • Sector 52    — call sheet (from sector-52-gurgaon-leads.csv, OSM)
  • How to use   — the offer + a 30-second guide

Only businesses WITH a phone number are kept. Deduped by phone within each area.
Each call-sheet tab has its own live counters, click-to-select dropdowns and
colour-coded status. Opens in Excel; imports cleanly into Google Sheets.

    python3 build-combined-callsheet.py
"""
import csv, re
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule
from openpyxl.utils import get_column_letter

OUT = "switch-udyogvihar-galleria-callsheet.xlsx"

# Each source + how its columns map. Google and OSM CSVs have different schemas.
SOURCES = [
    {
        "tab": "Udyog Vihar",
        "file": "udyog-vihar-leads.csv",
        "name": "name", "category": "primary_type",
        "phone": "phone", "rating": "rating", "address": "address", "map": "maps_url",
    },
    {
        "tab": "Galleria Market",
        "file": "galleria-market-leads.csv",
        "name": "name", "category": "primary_type",
        "phone": "phone", "rating": "rating", "address": "address", "map": "maps_url",
    },
]

# ── palette (matches the site) ──────────────────────────────────────────────
INDIGO="4F46E5"; INDIGO_L="EEF0FB"; DARK="111827"; GREY="6B7280"
GREEN="C6EFCE"; GREEN_TX="1E7E34"; RED="FFC7CE"; AMBER="FFF3CD"
WHITE="FFFFFF"; ZEBRA="F7F7FB"
thin = Side(style="thin", color="E2E2EC")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
def fill(c): return PatternFill("solid", fgColor=c)

# ── category -> roles Switch can staff ──────────────────────────────────────
def roles_for(cat, name):
    t = ("%s %s" % (cat, name)).lower()
    def has(*kws): return any(k in t for k in kws)
    if has("warehouse","logistic","cargo","courier","freight","storage","godown",
           "packers","movers","transport","distribution","supply","3pl","fulfil","shipping"):
        return "Loader, Packer, Picker, Warehouse Helper, Delivery"
    if has("restaurant","cafe","coffee","food","kitchen","bakery","fast_food","meal","dhaba","sweet"):
        return "Kitchen Helper, Cook, Dishwasher, Waiter"
    if has("hotel","lodging","guest_house","hostel","motel","resort"):
        return "Housekeeping, Room Boy, Kitchen Helper, Front Desk"
    if has("hospital","clinic","medical","dental","dentist","health","pharmacy","doctor","diagnostic"):
        return "Ward Boy, Housekeeping, Attendant, Security"
    if has("mall","supermarket","store","retail","clothing","grocery","general_store","shop","market"):
        return "Store Helper, Housekeeping, Security, Sales Staff"
    if has("salon","beauty","spa","hairdresser","massage","parlour"):
        return "Beautician, Helper, Receptionist, Cleaner"
    if has("gym","fitness","sports"):
        return "Trainer, Housekeeping, Front Desk"
    if has("fuel","petrol","cng","charging"):
        return "Pump Attendant, Cleaner, Security"
    if has("manufacturer","factory","industrial","industries","engineering"):
        return "Machine Operator, Helper, Loader, Packer"
    if has("car_repair","garage","motor","automobile","service_station"):
        return "Mechanic Helper, Cleaner, Washer"
    if has("school","educational","institute","college","coaching","university"):
        return "Peon, Housekeeping, Security, Attendant"
    if has("bank","office","corporate","consultant","association","finance","insurance","real_estate","government"):
        return "Office Boy, Housekeeping, Security, Data Entry"
    return "Helper, Housekeeping, Security, Office Boy"

def clean_phone(p):
    return re.sub(r"\D", "", p or "")

def load(src):
    rows, seen = [], set()
    try:
        with open(src["file"], newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                phone = (row.get(src["phone"]) or "").strip()
                if not phone:
                    continue                      # phone numbers only
                key = clean_phone(phone)
                if len(key) < 7 or key in seen:    # dedupe + drop junk
                    continue
                seen.add(key)
                rows.append({
                    "name": (row.get(src["name"]) or "").strip(),
                    "category": (row.get(src["category"]) or "").strip() or "business",
                    "phone": phone,
                    "rating": (row.get(src["rating"]) or "").strip() if src["rating"] else "",
                    "address": (row.get(src["address"]) or "").strip(),
                    "map": (row.get(src["map"]) or "").strip(),
                })
    except FileNotFoundError:
        print("!! missing %s — skipping %s" % (src["file"], src["tab"]))
    # highest-rated first (blank ratings sink to the bottom), then by name
    rows.sort(key=lambda r: (-(float(r["rating"]) if r["rating"] else 0), r["name"].lower()))
    return rows

# ── columns ─────────────────────────────────────────────────────────────────
COLS = [
    ("S.No", 6), ("Business Name", 32), ("Category", 18),
    ("Suggested Roles (per shift)", 34), ("Phone", 16), ("Rating", 8),
    ("Address", 40), ("Interested?", 13), ("Hours (1-12)", 12),
    ("Order Confirmed?", 15), ("Remarks", 34), ("Map", 7),
]
HDR = 4                     # header row (banner+counters sit above)
# column letters we reference in formulas
C_INT, C_HRS, C_ORD = "H", "I", "J"

def build_sheet(wb, first, tab, rows):
    ws = wb.active if first else wb.create_sheet()
    ws.title = tab
    ws.sheet_view.showGridLines = False
    last = HDR + max(len(rows), 1)

    for c,(t,w) in enumerate(COLS, start=1):
        ws.column_dimensions[get_column_letter(c)].width = w

    # banner
    ws.merge_cells("A1:L1")
    b = ws["A1"]
    b.value = "SWITCH  ·  %s  ·  CALL SHEET" % tab.upper()
    b.fill = fill(INDIGO); b.font = Font(bold=True, color=WHITE, size=16)
    b.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26
    ws.merge_cells("A2:L2")
    s = ws["A2"]
    s.value = ("Shifts of 1–12 hrs, billed per hour · pay after worker reports · "
               "instant replacement · %d leads with phone" % len(rows))
    s.font = Font(color=GREY, size=10, italic=True)
    s.alignment = Alignment(horizontal="center")

    # inline live counters on row 3
    def rng(col): return "%s%d:%s%d" % (col, HDR+1, col, last)
    counters = [
        ("A3", "LEADS", "=COUNTA(%s)" % rng("B")),
        ("C3", "CONTACTED", "=COUNTA(%s)" % rng(C_INT)),
        ("E3", "INTERESTED", '=COUNTIF(%s,"Yes")' % rng(C_INT)),
        ("G3", "ORDERS", '=COUNTIF(%s,"Yes")' % rng(C_ORD)),
        ("I3", "HOURS BOOKED", "=SUM(%s)" % rng(C_HRS)),
    ]
    for cell, label, formula in counters:
        col = cell[0]
        lc = ws[cell]; lc.value = label
        lc.font = Font(bold=True, color=GREY, size=8)
        lc.alignment = Alignment(horizontal="center")
        vcell = "%s%d" % (col, 3)  # label and value share cell? -> put value in next col
        vc = ws["%s3" % chr(ord(col)+1)]
        vc.value = formula
        vc.font = Font(bold=True, color=INDIGO, size=13)
        vc.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[3].height = 20

    # header row
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
        vals = [i+1, row["name"], row["category"], roles_for(row["category"], row["name"]),
                row["phone"], row["rating"], row["address"], "", "", "", "", ""]
        for c, v in enumerate(vals, start=1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.alignment = CTR if c in (1,5,6,8,9,10,12) else WRAP
            cell.border = BORDER
            if r % 2 == 0 and c not in (8,9,10):
                cell.fill = fill(ZEBRA)
        if row["map"]:
            m = ws.cell(row=r, column=12, value="Map")
            m.hyperlink = row["map"]; m.font = Font(color="0563C1", underline="single")

    # dropdowns
    def dropdown(col, options):
        dv = DataValidation(type="list", formula1='"%s"' % ",".join(options),
                            allow_blank=True, showDropDown=False)
        dv.prompt = "Click the arrow and choose"; dv.promptTitle = "Pick one"
        ws.add_data_validation(dv)
        dv.add("%s%d:%s%d" % (col, HDR+1, col, last))
    dropdown(C_INT, ["Yes","No","Maybe","Call back","No answer","Wrong number"])
    dropdown(C_HRS, [str(i) for i in range(1,13)])
    dropdown(C_ORD, ["Yes","No","Pending"])

    # colour status cells + tint confirmed rows
    ws.conditional_formatting.add("%s%d:%s%d" % (C_INT,HDR+1,C_INT,last),
        FormulaRule(formula=['%s%d="Yes"' % (C_INT,HDR+1)], fill=fill(GREEN), font=Font(color=GREEN_TX, bold=True)))
    ws.conditional_formatting.add("%s%d:%s%d" % (C_INT,HDR+1,C_INT,last),
        FormulaRule(formula=['%s%d="Call back"' % (C_INT,HDR+1)], fill=fill(AMBER)))
    ws.conditional_formatting.add("%s%d:%s%d" % (C_ORD,HDR+1,C_ORD,last),
        FormulaRule(formula=['%s%d="Yes"' % (C_ORD,HDR+1)], fill=fill(GREEN), font=Font(color=GREEN_TX, bold=True)))
    ws.conditional_formatting.add("A%d:L%d" % (HDR+1,last),
        FormulaRule(formula=['$%s%d="Yes"' % (C_ORD,HDR+1)], fill=fill("EAF8EE")))

    ws.freeze_panes = "A%d" % (HDR+1)
    ws.auto_filter.ref = "A%d:L%d" % (HDR, last)
    return len(rows)

# ── performance tab ─────────────────────────────────────────────────────────
def build_performance(wb, areas):
    """areas: list of (tab_name, lead_count). Live formulas pull from each tab."""
    ws = wb.create_sheet("Performance")
    ws.sheet_view.showGridLines = False
    for col, w in (("A",3),("B",26),("C",15),("D",15),("E",15),("F",15),("G",15),("H",3)):
        ws.column_dimensions[col].width = w

    # per-area data ranges (data starts at HDR+1, ends at HDR+count)
    def ref(tab, col, count):
        return "'%s'!%s%d:%s%d" % (tab, col, HDR+1, col, HDR+max(count,1))
    def leads(t,n):     return "COUNTA(%s)"           % ref(t,"B",n)
    def contacted(t,n): return "COUNTA(%s)"           % ref(t,"H",n)
    def interested(t,n):return 'COUNTIF(%s,"Yes")'    % ref(t,"H",n)
    def orders(t,n):    return 'COUNTIF(%s,"Yes")'    % ref(t,"J",n)
    def hours(t,n):     return "SUM(%s)"              % ref(t,"I",n)
    def joinsum(fn):    return "+".join(fn(t,n) for t,n in areas)

    # banner
    ws.merge_cells("B2:G3")
    b = ws["B2"]; b.value = "SWITCH  ·  CALLING PERFORMANCE"
    b.fill = fill(INDIGO); b.font = Font(bold=True, color=WHITE, size=18)
    b.alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells("B4:G4")
    s = ws["B4"]; s.value = "Live totals across all area tabs — updates as you fill the call sheets"
    s.font = Font(color=GREY, size=10, italic=True); s.alignment = Alignment(horizontal="center")

    def card(cell, label, formula, color=INDIGO, fmt="0", big=True):
        col = cell[0]; row = int(cell[1:])
        lc = ws["%s%d" % (col,row)]; lc.value = label
        lc.font = Font(bold=True, color=GREY, size=9); lc.alignment = Alignment(horizontal="center")
        vc = ws["%s%d" % (col,row+1)]; vc.value = formula; vc.number_format = fmt
        vc.font = Font(bold=True, color=color, size=24 if big else 14)
        vc.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[row+1].height = 32
        for rr in (row,row+1): ws["%s%d"%(col,rr)].fill = fill(INDIGO_L if big else WHITE)

    # headline cards
    card("B6", "TOTAL LEADS",   "=%s" % joinsum(leads),      color=DARK)
    card("D6", "CONTACTED",     "=%s" % joinsum(contacted),  color=INDIGO)
    card("F6", "ORDERS",        "=%s" % joinsum(orders),     color=GREEN_TX)
    # secondary cards
    card("B9", "INTERESTED",    "=%s" % joinsum(interested), color=GREEN_TX, big=False)
    card("D9", "CONVERSION",    "=IFERROR((%s)/(%s),0)" % (joinsum(orders), joinsum(contacted)),
         color=INDIGO, fmt="0%", big=False)
    card("F9", "HOURS BOOKED",  "=%s" % joinsum(hours),      color="B7791F", big=False)

    # per-area breakdown table
    hrow = 12
    heads = ["Area","Leads","Contacted","Interested","Orders","Hours"]
    for c,h in enumerate(heads, start=2):
        cell = ws.cell(row=hrow, column=c, value=h)
        cell.fill = fill(INDIGO); cell.font = Font(bold=True, color=WHITE, size=10)
        cell.alignment = Alignment(horizontal="center"); cell.border = BORDER
    for i,(t,n) in enumerate(areas):
        r = hrow+1+i
        cells = [t, "=%s"%leads(t,n), "=%s"%contacted(t,n),
                 "=%s"%interested(t,n), "=%s"%orders(t,n), "=%s"%hours(t,n)]
        for c,v in enumerate(cells, start=2):
            cell = ws.cell(row=r, column=c, value=v)
            cell.border = BORDER
            cell.alignment = Alignment(horizontal="left" if c==2 else "center")
            if r % 2: cell.fill = fill(ZEBRA)
    # totals row
    tr = hrow+1+len(areas)
    totals = ["TOTAL", "=%s"%joinsum(leads), "=%s"%joinsum(contacted),
              "=%s"%joinsum(interested), "=%s"%joinsum(orders), "=%s"%joinsum(hours)]
    for c,v in enumerate(totals, start=2):
        cell = ws.cell(row=tr, column=c, value=v)
        cell.border = BORDER; cell.fill = fill(INDIGO_L)
        cell.font = Font(bold=True, color=DARK)
        cell.alignment = Alignment(horizontal="left" if c==2 else "center")

    note = ws.cell(row=tr+2, column=2,
        value="↳ Fill the Interested? / Hours / Order Confirmed? columns on each area tab — these numbers move automatically.")
    note.font = Font(color=GREY, size=10, italic=True)

# ── how-to tab ──────────────────────────────────────────────────────────────
def build_howto(wb):
    how = wb.create_sheet("How to use")
    how.sheet_view.showGridLines = False
    how.column_dimensions["A"].width = 3
    how.column_dimensions["B"].width = 95
    guide = [
        ("SWITCH — CALLING SHEET  ·  HOW TO USE", "title"), ("",""),
        ("THE OFFER (say this, every time)", "head"),
        ("• Shifts of 1–12 hours, billed by the hour. NO monthly, NO weekly.", "body"),
        ("• Pay only AFTER the worker reports — no advance.", "body"),
        ("• Instant replacement if the worker doesn't show or isn't a fit.", "body"),
        ("• Verified, local staff delivered in 24 hours.", "body"), ("",""),
        ("HOW TO WORK THE SHEET", "head"),
        ("1. Two tabs: 'Udyog Vihar' and 'Sector 52'. Work each top-down.", "body"),
        ("2. WhatsApp first, then call. After each contact, click the dropdowns:", "body"),
        ("     · Interested? → Yes / No / Maybe / Call back / No answer / Wrong number", "body"),
        ("     · Hours → 1 to 12 (what they want per shift)", "body"),
        ("     · Order Confirmed? → Yes once they agree to take staff", "body"),
        ("3. 'Suggested Roles' is a starting pitch — confirm what they actually need.", "body"),
        ("4. Counters at the top of each tab update automatically as you fill it in.", "body"), ("",""),
        ("Only businesses with a phone number are included. Deduped by number.", "muted"),
    ]
    r = 1
    for text, kind in guide:
        cell = how.cell(row=r, column=2, value=text)
        if kind == "title":
            cell.font = Font(bold=True, color=WHITE, size=15); cell.fill = fill(INDIGO)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            how.row_dimensions[r].height = 30
        elif kind == "head":
            cell.font = Font(bold=True, color=INDIGO, size=12)
        elif kind == "muted":
            cell.font = Font(italic=True, color=GREY, size=10)
        else:
            cell.font = Font(color=DARK, size=11); cell.alignment = Alignment(wrap_text=True)
        r += 1

# ── main ────────────────────────────────────────────────────────────────────
wb = Workbook()
counts = {}
areas = []
for i, src in enumerate(SOURCES):
    rows = load(src)
    n = build_sheet(wb, i == 0, src["tab"], rows)
    counts[src["tab"]] = n
    areas.append((src["tab"], n))
build_performance(wb, areas)
build_howto(wb)
# put Performance first so the workbook opens on it
perf = wb["Performance"]
wb._sheets.remove(perf)
wb._sheets.insert(0, perf)
wb.active = 0
wb.save(OUT)
print("Wrote %s" % OUT)
for tab, n in counts.items():
    print("  %-14s %d leads (with phone)" % (tab, n))
