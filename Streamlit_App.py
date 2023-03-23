import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


# This script supports a web hosted streamlit app for a user to explore flood water
# levels provided by the Using the Real Time flood-monitoring AP at
# (https://environment.data.gov.uk/flood-monitoring/doc/reference)

last_24h_datetime = datetime.now() - timedelta(hours=24)
url_formatted_dt = str(last_24h_datetime).replace(" ", "T")[:-4] + "Z"

st.title("Oisín's Flood-Monitoring Tool")

st.markdown(
    "This tool may be used to view flood monitoring data, which is sourced from the [flood-monitoring API](https://environment.data.gov.uk/flood-monitoring/doc/reference) provided by the Environmental Agency. "
)


##### Real time measurements APIs used
root = "http://environment.data.gov.uk/flood-monitoring/"
stations_api = root + "id/stations"  # all measurement stations


@st.cache_data  # check if below function has been called with same arguments and return cached data to caller if so
def make_df(url: str) -> pd.DataFrame:
    """Takes the url of the API, extracts the items block and turns it into a DataFrame.
    By extracting all station data before filtering, we can cache and filter much quicker than
    extracting each time an individual station is selected.
    Although this could be done in place without defining a function, it is useful to do so because of the caching feature.

    Args:
        url (str): url of the flood data API

    Returns:
        pd.DataFrame:
    """
    r = requests.get(url)
    json = r.json()
    df = pd.DataFrame(json["items"])
    return df


data_load_state = st.text("Loading station list...")
stations_df = make_df(stations_api)
stations_df = stations_df[stations_df["label"] != " Huscote FAS"]
# first station has incompatible dateTime data and nonsensical water level data. As such is ignored for the purpose of this project
data_load_state.text("Station list loaded!")

st.header("UK flood monitoring stations")
map_data = (
    stations_df[["lat", "long"]].rename(columns={"long": "lon"}).dropna()
)  # st.map looks for a column called 'lon' and won't find 'long'
st.map(map_data)


st.markdown(
    "Water levels and flows are regularly monitored, usually every 15 minutes. However, data is transferred back to the Environment Agency at various frequencies, usually depending on the site and level of flood risk. Transfer of data is typically once or twice per day, but usually increases during times of heightened flood risk. "
)
st.header("Water level over last 24 hours")
station_select = st.selectbox(
    "Select monitoring station",
    stations_df["label"].sort_values().unique(),
    format_func=lambda a: a.lower().title(),
)

# station_id = stations_df.loc[stations_df["label"] == station_select]["@id"].iloc[0]
station_id = (
    stations_df.loc[stations_df["label"] == station_select]["notation"]
    .iloc[0]
    .replace("_", "")
)

filtered_by_station = (
    root + "id/stations/" + station_id + "/readings" + "?since=" + url_formatted_dt
)

data_load_state = st.text("Loading filtered station data...")
filtered_df = make_df(filtered_by_station)
data_load_state.text("Filtered station data loaded!")
filtered_df["dateTime"] = pd.to_datetime(
    filtered_df["dateTime"]
)  # fix date format from ISO 8601 to format readable by pd


table = (
    filtered_df[["dateTime", "value"]]
    .rename(columns={"dateTime": "Date and Time", "value": "Water Level"})
    .transpose()
)

# CSS to inject contained in a string, make table look nicer by hiding first column with indices
hide_table_row_index = """
            <style>
            thead tr:first-child {display:none} th
            tbody th {display:none}
            </style>
            """

# Inject CSS with Markdown
st.markdown(hide_table_row_index, unsafe_allow_html=True)

fig, ax = plt.subplots()
ax.plot(filtered_df["dateTime"], filtered_df["value"])
ax.set(
    xlabel="Time",
    ylabel="Water Level (m)",
    title=f"Water level at {station_select} over the last 24 hours",
)

ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

fig.autofmt_xdate()  # Rotate and align x tick labels

fig.autofmt_xdate()
st.pyplot(fig)

if st.checkbox("Show table of water levels over time"):
    st.subheader(
        f"Water level data for station: {station_select} over the last 24 hours"
    )
    st.table(table)

if st.checkbox("Show raw data"):
    st.subheader(f"Raw data for station: {station_select}")
    st.dataframe(filtered_df)
