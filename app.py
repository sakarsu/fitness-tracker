import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date

# --- 1. Google Sheets Setup ---
# We use Streamlit Secrets to store passwords securely on the cloud
def get_google_sheet():
    # Define the scope
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # Load credentials from Streamlit Secrets (we will set this up in Phase 3)
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    
    client = gspread.authorize(creds)
    # Open the sheet by name. Make sure your Google Sheet is named exactly this:
    sheet = client.open("Workout_DB").sheet1
    return sheet

def load_data():
    try:
        sheet = get_google_sheet()
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        # Helper: Ensure date is parsed correctly
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date']).dt.date
        return df
    except Exception as e:
        # If sheet is empty or error, return structure
        return pd.DataFrame(columns=[
            'Date', 'Type', 'Sub_Category', 'Duration_Min', 
            'Distance_Km', 'Speed_Kmh', 'Avg_HR', 
            'Jog_Split_Min', 'Walk_Split_Min',
            'Z1_Min', 'Z2_Min', 'Z3_Min', 'Z4_Min', 'Z5_Min', 'Notes'
        ])

def save_workout(entry):
    sheet = get_google_sheet()
    # Convert dates/numbers to strings/floats that Google Sheets likes
    row = [
        str(entry['Date']),
        entry['Type'],
        entry['Sub_Category'],
        entry['Duration_Min'],
        entry['Distance_Km'],
        entry['Speed_Kmh'],
        entry['Avg_HR'],
        entry['Jog_Split_Min'],
        entry['Walk_Split_Min'],
        entry['Z1_Min'], entry['Z2_Min'], entry['Z3_Min'], entry['Z4_Min'], entry['Z5_Min'],
        entry['Notes']
    ]
    sheet.append_row(row)

# --- 2. Interface (Same as v4) ---
st.set_page_config(page_title="Cloud Fitness", layout="wide")
st.title("☁️ Cloud Fitness Tracker")

tab1, tab2, tab3 = st.tabs(["📝 Log Workout", "📊 Dashboard", "💾 Data View"])

# --- TAB 1: LOGGING ---
with tab1:
    st.header("Log Session")
    c1, c2 = st.columns(2)
    with c1:
        date_input = st.date_input("Date", date.today())
    with c2:
        activity_type = st.selectbox("Activity", ["Run/Walk Intervals", "Jogging", "Walking", "Cycling", "Strength", "Tennis", "Other"])

    st.subheader("Session Details")
    c3, c4, c5 = st.columns(3)
    duration, jog_split, walk_split, distance, speed_kmh = 0, 0, 0, 0.0, 0.0
    sub_category = "N/A"

    if activity_type == "Run/Walk Intervals":
        with c3:
            st.info("Interval Breakdown")
            jog_split = st.number_input("Jogging (min)", 0, step=1)
            walk_split = st.number_input("Walking (min)", 0, step=1)
            duration = jog_split + walk_split
            st.write(f"**Total: {duration} min**")
        with c4:
            distance = st.number_input("Total Distance (km)", 0.0, step=0.1)
    elif activity_type in ["Jogging", "Walking", "Cycling"]:
        with c3:
            duration = st.number_input("Total Duration (min)", 1, step=1)
        with c4:
            distance = st.number_input("Distance (km)", 0.0, step=0.1)
            if activity_type == "Jogging": jog_split = duration
            if activity_type == "Walking": walk_split = duration
    elif activity_type == "Strength":
        with c3:
            duration = st.number_input("Total Duration (min)", 1, step=1)
        with c4:
            sub_category = st.radio("Focus", ["Upper", "Lower", "Full"], horizontal=True)
    elif activity_type in ["Tennis", "Other"]:
        with c3:
            duration = st.number_input("Total Duration (min)", 1, step=1)

    with c5:
        avg_hr = st.number_input("Avg HR", 0, step=1)
        if duration > 0 and distance > 0:
            speed_kmh = distance / (duration / 60)
            st.metric("Avg Speed", f"{speed_kmh:.1f} km/h")

    st.divider()
    st.subheader("Heart Rate Zones")
    z_cols = st.columns(5)
    zones = [col.number_input(f"Z{i+1}", 0, step=1) for i, col in enumerate(z_cols)]
    
    notes = st.text_area("Notes")

    if st.button("Save to Cloud", type="primary"):
        save_workout({
            'Date': date_input, 'Type': activity_type, 'Sub_Category': sub_category,
            'Duration_Min': duration, 'Distance_Km': distance, 'Speed_Kmh': speed_kmh,
            'Avg_HR': avg_hr, 'Jog_Split_Min': jog_split, 'Walk_Split_Min': walk_split,
            'Z1_Min': zones[0], 'Z2_Min': zones[1], 'Z3_Min': zones[2], 'Z4_Min': zones[3], 'Z5_Min': zones[4],
            'Notes': notes
        })
        st.success("Saved to Google Sheet!")

# --- TAB 2: DASHBOARD ---
with tab2:
    # Adding a Refresh button because Cloud data doesn't update instantly like local
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        
    df = load_data()
    if not df.empty:
        # Simple Stats
        m1, m2, m3 = st.columns(3)
        m1.metric("Total KM", f"{df['Distance_Km'].sum():.1f}")
        m2.metric("Total Min", df['Duration_Min'].sum())
        m3.metric("Sessions", len(df))
        
        # Charts
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.caption("Activity Type")
            st.plotly_chart(px.pie(df, names='Type'), use_container_width=True)
        with c2:
            st.caption("Weekly Volume")
            st.plotly_chart(px.bar(df, x='Date', y='Duration_Min', color='Type'), use_container_width=True)
            
        st.caption("Weekly Zone Load")
        zone_cols = ['Z1_Min', 'Z2_Min', 'Z3_Min', 'Z4_Min', 'Z5_Min']
        df_zones = df.melt(id_vars=['Date'], value_vars=zone_cols, var_name='Zone', value_name='Minutes')
        st.plotly_chart(px.bar(df_zones, x='Date', y='Minutes', color='Zone', color_discrete_map={'Z1_Min':'#A1C9F4', 'Z2_Min':'#FFB482', 'Z3_Min':'#8DE5A1', 'Z4_Min':'#FF9F9B', 'Z5_Min':'#D0BBFF'}), use_container_width=True)
    else:
        st.info("Database is empty or could not connect.")

# --- TAB 3: DATA ---
with tab3:
    st.dataframe(load_data(), use_container_width=True)