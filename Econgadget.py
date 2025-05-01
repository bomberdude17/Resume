import json
import os  # DONT EVER REMOVE
import re
from datetime import datetime
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pandas as pd
import requests
import seaborn as sns
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta

BLS_API_KEY = 'f91c68723a1c4ea0a95456ad193373df'
SERIES_ID = 'LNU04000000'
presidents = []

# Universal JSON path logic
# I use this to make calls to the os to find any file that ends with the term Econgadget that users downloaded
def get_data_path():
    base_dir = os.path.join(os.path.expanduser("~"), ".Econgadget")
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, "unemployment_data.json")

# I then created a simple but very bulky script to scrub wikipedia's information on presidents.
def get_presidents():
    url = "https://en.wikipedia.org/wiki/List_of_presidents_of_the_United_States"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
# It retrieves the data table using beautifulsoup prebuilt libraries to find the wikitable in which the website stores all presidents in.
    tables = soup.find_all('table', class_='wikitable')
    for table in tables:
        rows = table.find_all('tr')
        if len(rows) < 10:
            continue
        for row in rows[1:]:
            cols = row.find_all(['th', 'td'])
            if len(cols) < 4:
                continue
            try:
                name_tag = cols[0].find('a')
                if not name_tag:
                    continue
                title = name_tag.get('title', '')
                name = re.sub(r"^.*?of\s+", "", title) if "Presidency of" or "presidency of" in title else name_tag.text.strip()
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
                    if end_year - start_year <= 20:
                        presidents.append((name, start_year, end_year))
# I then iterate through the wiki table using nested for loops and try statements specifically parsing for html code headers which I head to find manually by scrubbing the data beforehand
            except:
                continue
    return presidents

def get_last_10_year_presidents():
    presidents = get_presidents()
    cutoff = datetime.now().year - 10
    return [p for p in presidents if p[2] >= cutoff]
# A simple function using above method to get presidents and parse through them comparing to PC's current system time.
def save_unemployment_data():
    json_path = get_data_path()
    if os.path.exists(json_path):
        print("✔ Existing data file found. Skipping API call.")
        return
    print("Fetching unemployment data from BLS API...")
    current_year = datetime.now().year
    start_year = current_year - 10
    data = {
        "seriesid": [SERIES_ID],
        "startyear": str(start_year),
        "endyear": str(current_year),
        "registrationkey": BLS_API_KEY
    }
    try:
        response = requests.post(
            'https://api.bls.gov/publicAPI/v2/timeseries/data/',
            json=data,
            timeout=10
        )
        response.raise_for_status()
        json_data = response.json()
        with open(json_path, 'w') as outfile:
            json.dump(json_data, outfile, indent=4)
        print("✔ Data saved to unemployment_data.json.")

    except requests.exceptions.Timeout:
        print("⏱Request timed out. Check your internet connection or try again later.")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except ValueError:
        print("Failed to parse JSON response.")
def load_unemployment_data():
    try:
        with open(get_data_path(), 'r') as infile:
            return json.load(infile)
    except FileNotFoundError:
        print("No saved data found.")
        return None

# Here was the hardest part of the project. I created this function to graph the above data (easy) and correlate the presidents from above with their correct timeframe on the graph displayed (hard)
# Uses most of the imported libraries found here which makes the program bulky. The nice thing is that it does future proof the program a bit.
# 1 I need to test this with data from 1980-1990 for regression testing.
# 2 I need to test this with data from 2035-2045 for production level testing.
# 3 Add more graphs
def plot_data(json_data, recent_presidents):
    records = []
    series = json_data.get('Results', {}).get('series', [])[0]
    for item in series.get('data', []):
        year = int(item['year'])
        period = item['period']
        if 'M01' <= period <= 'M12':
            month = int(period[1:])
            value = float(item['value'])
            date = datetime(year, month, 1)
            records.append({'Date': date, 'Value': value})
    df = pd.DataFrame(records)
    df.sort_values('Date', inplace=True)
    # Filter to last 10 years
    cutoff_date = datetime.now() - relativedelta(years=10)
    df = df[df['Date'] >= cutoff_date]
    # Calculate rolling averages
    df['6_Month_Avg'] = df['Value'].rolling(6).mean()
    df['12_Month_Avg'] = df['Value'].rolling(12).mean()
    # Assign colors
    colors = list(mcolors.TABLEAU_COLORS.values())
    president_colors = {pres[0]: colors[i % len(colors)] for i, pres in enumerate(recent_presidents)}
    # Plot
    sns.set(style="whitegrid")
    plt.figure(figsize=(14, 7))
    ax = plt.gca()
    sns.lineplot(data=df, x='Date', y='Value', label='Unemployment Rate', color='orange', linestyle='--')
    sns.lineplot(data=df, x='Date', y='6_Month_Avg', label='6-Month Avg', color='green')
    sns.lineplot(data=df, x='Date', y='12_Month_Avg', label='12-Month Avg', color='blue')
    for pres in recent_presidents:
        name, start_year, end_year = pres
        start = datetime(start_year, 1, 1)
        end = datetime(end_year, 12, 31)
        ax.axvspan(start, end, color=president_colors[name], alpha=0.2, label=name)
    handles, labels = plt.gca().get_legend_handles_labels()
    unique_labels = dict(zip(labels, handles))
    plt.legend(unique_labels.values(), unique_labels.keys(), loc='upper left')
    ax.set_xlim([datetime(2015, 1, 1), datetime.now()])
    plt.title("U.S. Unemployment Rate with Presidential Terms (Past 10 Years)")
    plt.xlabel("Date")
    plt.ylabel("Unemployment Rate (%)")
    plt.grid(True)
    plt.tight_layout()
    plt.show()
def main():
    print("Fetching presidential data...")
    presidents = get_last_10_year_presidents()
    print(presidents)

    print("Downloading unemployment data...")
    save_unemployment_data()
    json_data = load_unemployment_data()
    if json_data:
        print("Plotting data...")
        plot_data(json_data, presidents)
    else:
        print("Could not plot due to missing data.")
    input("Done! Press Enter to exit...")
if __name__ == "__main__":
    main()