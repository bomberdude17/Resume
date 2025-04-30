import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import json
import prettytable
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.colors as mcolors
import seaborn as sns
from dateutil.relativedelta import relativedelta



def get_presidents():
    url="https://en.wikipedia.org/wiki/List_of_presidents_of_the_United_States"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception("Failed to fetch Wikipedia page")

    soup = BeautifulSoup(response.content, 'html.parser')
    presidents = []
    tables=soup.find_all('table', class_='wikitable')

    for table in tables:
        rows = table.find_all('tr')
        if len(rows) < 10:
            continue

        for row in rows[1:]:
            cols = row.find_all(['th', 'td'])
            if len(cols) < 4:
                continue

            #Extract name
            try:
                name_tag=cols[0].find('a')
                if not name_tag:
                    continue
                title = name_tag.get('title', '')
                name = re.sub(r"^.*?of\s+", "", title) if "Presidency of" or 'presidency of' in title else name_tag.text.strip()

                #Extract start and end years
                term_col = cols[3]
                span_tags = term_col.find_all('span', attrs={'data-sort-value': True})
                if len(span_tags) >= 1:
                    start_date = span_tags[0]['data-sort-value'][8:18]
                    start_year = int(start_date[:4])
                    if len(span_tags) >= 2:
                        end_date = span_tags[1]['data-sort-value'][8:18]
                        end_year = int(end_date[:4])
                    else:
                        end_year = datetime.now().year

                    # Filter out obviously wrong terms (e.g. 1841–2025)
                    if end_year - start_year <= 12:
                        presidents.append((name, start_year, end_year))

            except Exception as e:
                print(f"Error processing row: {e}")
                continue
    return presidents


def get_last_10_presidents():
    presidents = get_presidents()
    return [p for p in presidents if p[2] >= datetime.now().year - 10]


def assign_president_globals():
    recent_presidents = get_last_10_presidents()
    for idx, pres in enumerate(recent_presidents):
        globals()[f'president_{idx + 1}'] = pres
    return recent_presidents


# --- Fetch and Print the Last 10 Presidents ---
recent_presidents_sorted = assign_president_globals()
print(recent_presidents_sorted)
BLS_API_KEY = 'f91c68723a1c4ea0a95456ad193373df'
SERIES_ID = 'LNU04000000'
# Function to save unemployment data
def save_unemployment_data():
    current_year = datetime.now().year
    start_year = current_year - 10

    data = {
        "seriesid": [SERIES_ID],
        "startyear": str(start_year),
        "endyear": str(current_year),
        "registrationkey": BLS_API_KEY
    }

    response = requests.post('https://api.bls.gov/publicAPI/v2/timeseries/data/', json=data)

    if response.status_code == 200:
        try:
            json_data = response.json()
            with open('unemployment_data.json', 'w') as outfile:
                json.dump(json_data, outfile, indent=4)
            print("Data saved to unemployment_data.json.")
        except ValueError:
            print("Failed to parse JSON response.")
    else:
        print(f"Failed to fetch data. HTTP Status Code: {response.status_code}")

def load_unemployment_data():
    try:
        with open('unemployment_data.json', 'r') as infile:
            return json.load(infile)
    except FileNotFoundError:
        print("No saved data found. Please download the data first.")
        return None

# Save and load the unemployment data
save_unemployment_data()
json_data = load_unemployment_data()
if json_data:
    table = prettytable.PrettyTable(["Series ID", "Year", "Period", "Value", "Footnotes"])
    records = []
    series_list = json_data.get('Results', {}).get('series', [])
    if series_list:
        series = series_list[0]
        series_id = series.get('seriesID', SERIES_ID)
        for item in series.get('data', []):
            year = item.get('year')
            period = item.get('period')
            value = item.get('value')
            footnotes = ','.join([f.get('text', '') for f in item.get('footnotes', []) if f.get('text')])

            if 'M01' <= period <= 'M12':
                table.add_row([series_id, year, period, value, footnotes.strip(',')])
                month = int(period[1:])
                date = datetime(int(year), month, 1)
                records.append({'Date': date, 'Value': float(value)})

        with open(f"{series_id}.txt", 'w') as output:
            output.write(table.get_string())

        df = pd.DataFrame(records)
        df.sort_values('Date', inplace=True)

        # --- DataFrame Setup ---
        df = pd.DataFrame(records)
        df.sort_values('Date', inplace=True)
        df['6_Month_Avg'] = df['Value'].rolling(6).mean()
        df['12_Month_Avg'] = df['Value'].rolling(12).mean()

        # --- Create Color Map for Presidents ---
        recent_presidents = recent_presidents_sorted
        colors = list(mcolors.TABLEAU_COLORS.values()) + list(mcolors.CSS4_COLORS.values())
        president_colors = {pres[0]: colors[i % len(colors)] for i, pres in enumerate(recent_presidents)}
        plt.figure(figsize=(14, 7))
        ax = plt.gca()
        # Plot the 3 lines
        sns.lineplot(data=df, x='Date', y='Value', label='Unemployment Rate', color='orange', linestyle='--')
        sns.lineplot(data=df, x='Date', y='6_Month_Avg', label='6-Month Avg', color='green')
        sns.lineplot(data=df, x='Date', y='12_Month_Avg', label='12-Month Avg', color='blue')
        # Shading each president's term
        for pres in recent_presidents:
            name, start_year, end_year = pres
            start_date = datetime(start_year, 1, 1)
            end_date = datetime(end_year, 12, 31)
            ax.axvspan(start_date, end_date, color=president_colors[name], alpha=0.2, label=name)
        # Formatting
        handles, labels = plt.gca().get_legend_handles_labels()
        unique_labels = dict(zip(labels, handles))  # Remove duplicates
        plt.legend(unique_labels.values(), unique_labels.keys(), loc='upper left')
        plt.title("U.S. Unemployment Rate Over Last 10 Years with Presidential Terms")
        plt.xlabel("Date")
        plt.ylabel("Unemployment Rate (%)")
        plt.grid(True)
        start_time = datetime.now().year -10
        ax.set_xlim([datetime(start_time, 1, 1), datetime.now()])
        plt.tight_layout()
        plt.show()
    else:
        print("No series data found in the response.")
else:
    print("No valid data to plot.")