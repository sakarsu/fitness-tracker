import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date

# --- 1. Google Sheets Setup ---
def get_google_sheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("Workout_DB").sheet1

def load_data():
    try:
        sheet = get_google_sheet()
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date']).dt.date
        return df
    except Exception:
        return pd.DataFrame()

def save_workout(entry):
    sheet = get_google_sheet()
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

# --- HELPER: Time Parser (The Magic Part) ---
def parse_time(input_str):
    """Converts 'MM:SS' string to decimal minutes (float)."""
    if not input_str: return 0.0
    s = str(input_str).strip()
    try:
        if ':' in s:
            parts = s.split(':')
            minutes = float(parts[0])
            seconds = float(parts[1])
            return minutes + (seconds / 60)
        else:
            return float(s)
    except ValueError:
        return 0.0

# --- 2. Interface ---
st.set_page_config(page_title="Cloud Fitness v6", layout="wide")
st.title("☁️ Cloud Fitness Tracker")

tab1, tab2, tab3 = st.tabs(["📝 Log Workout", "📊 Dashboard", "💾 Data View"])

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
    
    # --- NEW ZONE INPUT SECTION ---
    st.subheader("Heart Rate Zones")
    st.caption("Enter as Minutes (e.g. '12') or MM:SS (e.g. '12:30')")
    
    # Using text_input instead of number_input
    z_col1, z_col2, z_col3, z_col4, z_col5 = st.columns(5)
    
    z1_str = z_col1.text_input("Zone 1", placeholder="MM:SS")
    z2_str = z_col2.text_input("Zone 2", placeholder="MM:SS")
    z3_str = z_col3.text_input("Zone 3", placeholder="MM:SS")
    z4_str = z_col4.text_input("Zone 4", placeholder="MM:SS")
    z5_str = z_col5.text_input("Zone 5", placeholder="MM:SS")

    # Convert inputs to float (decimal minutes) instantly
    z1, z2, z3, z4, z5 = parse_time(z1_str), parse_time(z2_str), parse_time(z3_str), parse_time(z4_str), parse_time(z5_str)
    
    # Validation
    total_zone_time = z1 + z2 + z3 + z4 + z5
    # Allow a small margin of error (0.1) for floating point math
    if total_zone_time > 0 and duration > 0:
        if abs(total_zone_time - duration) > 0.1:
            st.warning(f"⚠️ Zone Sum ({total_zone_time:.2f} min) ≠ Total Duration ({duration} min)")
        else:
            st.success("✅ Zones match total duration")

    notes = st.text_area("Notes")

    if st.button("Save to Cloud", type="primary"):
        save_workout({
            'Date': date_input, 'Type': activity_type, 'Sub_Category': sub_category,
            'Duration_Min': duration, 'Distance_Km': distance, 'Speed_Kmh': speed_kmh,
            'Avg_HR': avg_hr, 'Jog_Split_Min': jog_split, 'Walk_Split_Min': walk_split,
            'Z1_Min': z1, 'Z2_Min': z2, 'Z3_Min': z3, 'Z4_Min': z4, 'Z5_Min': z5,
            'Notes': notes
        })
        st.success("Saved to Google Sheet!")

# --- DASHBOARD (Unchanged) ---
with tab2:
    if st.button("🔄 Refresh Data"): st.cache_data.clear()
    df = load_data()
    if not df.empty:
        st.markdown("### 📈 Dashboard")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total KM", f"{df['Distance_Km'].sum():.1f}")
        m2.metric("Total Hours", f"{df['Duration_Min'].sum()/60:.1f}")
        m3.metric("Sessions", len(df))
        
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.pie(df, names='Type', title="Activity Types"), use_container_width=True)
        with c2:
            df_zones = df.melt(id_vars=['Date'], value_vars=['Z1_Min', 'Z2_Min', 'Z3_Min', 'Z4_Min', 'Z5_Min'], var_name='Zone', value_name='Minutes')
            st.plotly_chart(px.bar(df_zones, x='Date', y='Minutes', color='Zone', title="Weekly Zone Load", color_discrete_map={'Z1_Min':'#A1C9F4', 'Z2_Min':'#FFB482', 'Z3_Min':'#8DE5A1', 'Z4_Min':'#FF9F9B', 'Z5_Min':'#D0BBFF'}), use_container_width=True)

with tab3:
    st.dataframe(load_data(), use_container_width=True)