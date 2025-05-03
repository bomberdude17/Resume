import json
import os
import sys
import questionary
import re
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from bs4 import BeautifulSoup
# --- INIT--------------------------------------------------------------------------------------------------
CPI_SERIES_IDS = [
    "CUUR0000SA0", "CUUR0000SAF11", "CUUR0000SAF111",
    "CUUR0000SAF112", "CUUR0000SAF113", "CUUR0000SEFJ", "CUUR0000SEFV"
]
CPI_LABELS = {
    "CUUR0000SA0": "All Items",
    "CUUR0000SAF11": "Food",
    "CUUR0000SAF111": "Food at Home",
    "CUUR0000SAF112": "Cereals & Bakery",
    "CUUR0000SAF113": "Meats, Poultry, Fish & Eggs",
    "CUUR0000SEFJ": "Motor Fuel",
    "CUUR0000SEFV": "Gasoline"
}
CPI_START = datetime.now().year - 10
CPI_END   = datetime.now().year
CPI_DATA_FILE = None
UNEMP_DATA_FILE      = None
UNEMP_SERIES_ID = "LNU04000000"
TARGET_YEAR     = datetime.now().year - 10
CURRENT_YEAR       = datetime.now().year
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".Econgadget")
os.makedirs(CACHE_DIR, exist_ok=True)
BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BLS_API_KEY = 'f91c68723a1c4ea0a95456ad193373df'
# --- BLS Calls-----------------------------------------------------------------------------------------
def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def fetch_bls_json(series_ids, start_year, end_year, api_key):
    payload = {
        "seriesid": series_ids,
        "startyear": str(start_year),
        "endyear": str(end_year),
        "registrationkey": api_key
    }
    r = requests.post(BLS_API_URL, json=payload, timeout=10)
    r.raise_for_status()
    return r.json()
# --- CPI-------------------------------------------------------------------------------------------------
def save_cpi_raw(j, path=None):
    if not path:
        return
    with open(path, "w") as f:
        json.dump(j, f, indent=2)
    print(f"[CPI] raw data → {path}")

def load_cpi_raw(path=None):
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"CPI data file '{path}' not found.")
    return json.load(open(path))

def get_last_10_year_presidents():
    presidents = fetch_presidents()
    cutoff = datetime.now().year - 10
    return [p for p in presidents if p[2] >= cutoff]

def cpi_json_to_df(j):
    recs = []
    for series in j["Results"]["series"]:
        sid = series["seriesID"]
        for e in series["data"]:
            p = e["period"]
            if not p.startswith("M") or not p[1:].isdigit(): continue
            m = int(p[1:])
            if m<1 or m>12: continue
            try:
                dt  = datetime(int(e["year"]), m, 1)
                val = float(e["value"])
                recs.append({"Date": dt, "Value": val, "SeriesID": sid})
            except:
                continue
    return pd.DataFrame(recs).sort_values("Date")

def plot_cpi(df, presidents, years=10):
    df = df[df["Date"].dt.year >= TARGET_YEAR].copy()
    df["12mo"] = df["Value"].rolling(12).mean()
    fig, ax = plt.subplots(figsize=(14,6))
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
    for i, (sid, grp) in enumerate(df.groupby("SeriesID")):
        grp = grp.sort_values("Date")
        c   = colors[i % len(colors)]
        label = CPI_LABELS.get(sid, sid)
        ax.plot(grp["Date"], grp["Value"],
                linestyle="-", color=c, label=f"{label} (Actual)")
    for i, (name, sy, ey) in enumerate(presidents):
        start = max(datetime(sy,1,1), datetime(TARGET_YEAR,1,1))
        end   = datetime(ey,12,31)
        if end.year < TARGET_YEAR: continue
        col = colors[i % len(colors)]
        ax.axvspan(start, end, color=col, alpha=0.2, label=name)
    h, l = ax.get_legend_handles_labels()
    by_label = dict(zip(l, h))
    ax.legend(by_label.values(), by_label.keys(),
              loc="upper left", fontsize="small")
    ax.set_xlim(datetime(TARGET_YEAR,1,1), datetime.now())
    ax.set_title(f"CPI Series & Presidential Terms (Last {years} Years)")
    ax.set_xlabel("Date"); ax.set_ylabel("Index Value")
    ax.grid(True); fig.tight_layout(); plt.show()
# --- Unemployment--------------------------------------------------------------------------------------------
def save_unemp_raw(j, path=None):
    if not path:
        return
    with open(path, "w") as f:
        json.dump(j, f, indent=2)
    print(f"[Unemp] raw data → {path}")

def load_unemp_raw(path=None):
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"Unemployment data file '{path}' not found.")
    return json.load(open(path))

def unemp_json_to_df(j):
    recs = []
    series = j["Results"]["series"][0]
    for e in series["data"]:
        p = e["period"]
        if not p.startswith("M") or not p[1:].isdigit(): continue
        m = int(p[1:])
        if m<1 or m>12: continue
        try:
            dt = datetime(int(e["year"]), m, 1)
            recs.append({"Date": dt, "Value": float(e["value"])})
        except:
            continue
    return pd.DataFrame(recs).sort_values("Date")

def plot_unemployment(df, presidents, years=10):
    df["Year"] = df["Date"].dt.year
    df = df[df["Year"] >= TARGET_YEAR].copy()
    df["6mo"]  = df["Value"].rolling(6).mean()
    df["12mo"] = df["Value"].rolling(12).mean()
    fig, ax = plt.subplots(figsize=(14,6))
    ax.plot(df["Date"], df["Value"], linestyle="--", color="orange", label="Actual")
    ax.plot(df["Date"], df["6mo"],    linestyle="-",  color="green",  label="6‑Mo Avg")
    ax.plot(df["Date"], df["12mo"],   linestyle="-",  color="blue",   label="12‑Mo Avg")
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
    for i, (name, sy, ey) in enumerate(presidents):
        if ey < TARGET_YEAR: continue
        start = max(datetime(sy,1,1), datetime(TARGET_YEAR,1,1))
        ax.axvspan(start, datetime(ey,12,31),
                   color=colors[i % len(colors)],
                   alpha=0.2, label=name)
    h, l = ax.get_legend_handles_labels()
    by_label = dict(zip(l, h))
    ax.legend(by_label.values(), by_label.keys(),
              loc="upper left", fontsize="small")
    ax.set_xlim(datetime(TARGET_YEAR,1,1), datetime.now())
    ax.set_title(f"Unemployment Rate & Presidential Terms (Last {years} Years)")
    ax.set_xlabel("Date"); ax.set_ylabel("Unemployment Rate (%)")
    fig.tight_layout(); plt.show()

# --- Get Last 10 Years of Presidents off WIKI ---------------------------------------------------------------
def fetch_presidents():
    url  = "https://en.wikipedia.org/wiki/List_of_presidents_of_the_United_States"
    soup = BeautifulSoup(requests.get(url).content, "html.parser")
    pres = []
    for tbl in soup.find_all("table", class_="wikitable"):
        rows = tbl.find_all("tr")
        if len(rows)<10: continue
        for r in rows[1:]:
            cols = r.find_all(["th","td"])
            if len(cols)<4: continue
            try:
                a     = cols[0].find("a")
                title = a.get("title","") if a else ""
                name = re.sub(r"^(?:\w+\s+)?presidency of\s+", "", title, flags=re.IGNORECASE) if "residency of" in title.lower() else (a.text.strip() if a else "")
                spans = cols[3].find_all("span",{"data-sort-value":True})
                sd    = spans[0]["data-sort-value"][8:18]; sy = int(sd[:4])
                if len(spans)>1:
                    ed    = spans[1]["data-sort-value"][8:18]; ey = int(ed[:4])
                else:
                    ey = datetime.now().year
                if ey - sy <= 20:
                    pres.append((name, sy, ey))
            except:
                continue
    return pres

# --- MAIN -------------------------------------------------------------------------------------------
def main():
    global CPI_DATA_FILE, UNEMP_DATA_FILE, PRESIDENTS_DATA_FILE
    CPI_DATA_FILE = get_resource_path("bls_data.txt")
    UNEMP_DATA_FILE = get_resource_path("unemployment_data.json")
    PRESIDENTS_DATA_FILE = fetch_presidents()
    while True:
        action = questionary.select(
            "Choose an option:",
            choices=[
                "Plot CPI Trends",
                "Plot Unemployment Trends",
                "View Presidential Terms (Last 10 Years)",
                "❌ Exit"
            ]
        ).ask()
        if action == "Plot CPI Trends":
            recent_pres = get_last_10_year_presidents()
            if os.path.exists(CPI_DATA_FILE):
                cpi_raw = load_cpi_raw(CPI_DATA_FILE)
                print(f"[CPI] loaded from {CPI_DATA_FILE}")
            else:
                cpi_raw = fetch_bls_json(CPI_SERIES_IDS, CPI_START, CPI_END, BLS_API_KEY)
                save_cpi_raw(cpi_raw)
            df_cpi = cpi_json_to_df(cpi_raw)
            plot_cpi(df_cpi, recent_pres)
        elif action == "Plot Unemployment Trends":
            recent_pres = get_last_10_year_presidents()
            if os.path.exists(UNEMP_DATA_FILE):
                unemp_raw = load_unemp_raw()
                print(f"[Unemp] loaded from {UNEMP_DATA_FILE}")
            else:
                unemp_raw = fetch_bls_json([UNEMP_SERIES_ID], TARGET_YEAR, CURRENT_YEAR, BLS_API_KEY)
                save_unemp_raw(unemp_raw)
            df_unemp = unemp_json_to_df(unemp_raw)
            plot_unemployment(df_unemp, recent_pres)
        elif action == "View Presidential Terms (Last 10 Years)":
            pres = get_last_10_year_presidents()
            for name, start, end in pres:
                print(f"{name}: {start}–{end}")
        elif action == "❌ Exit":
            print("Goodbye!")
            sys.exit()
if __name__ == "__main__":
    main()