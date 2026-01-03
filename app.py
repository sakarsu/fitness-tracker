import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date

# --- 1. SETUP & CONFIG ---
st.set_page_config(page_title="Cloud Fitness v6.1", layout="wide")
st.title("☁️ CLOUD FITNESS v6.1 (Debug Mode)")

# --- 2. GOOGLE SHEETS CONNECTION ---
def get_google_sheet():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        # Load credentials from Streamlit Secrets
        if "gcp_service_account" not in st.secrets:
            st.error("❌ Secrets not found! Did you paste the TOML into Advanced Settings?")
            return None
            
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("Workout_DB").sheet1
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        return None

def load_data():
    sheet = get_google_sheet()
    if sheet is None: return pd.DataFrame() # Stop if no connection
    
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty and 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date']).dt.date
        return df
    except Exception as e:
        st.warning(f"⚠️ Could not read data (Sheet might be empty): {e}")
        return pd.DataFrame()

def save_workout(entry):
    sheet = get_google_sheet()
    if sheet:
        row = [
            str(entry['Date']), entry['Type'], entry['Sub_Category'],
            entry['Duration_Min'], entry['Distance_Km'], entry['Speed_Kmh'],
            entry['Avg_HR'], entry['Jog_Split_Min'], entry['Walk_Split_Min'],
            entry['Z1_Min'], entry['Z2_Min'], entry['Z3_Min'], entry['Z4_Min'], entry['Z5_Min'],
            entry['Notes']
        ]
        sheet.append_row(row)

# --- 3. HELPER: Time Parser ---
def parse_time(input_str):
    if not input_str: return 0.0
    s = str(input_str).strip()
    try:
        if ':' in s:
            parts = s.split(':')
            return float(parts[0]) + (float(parts[1]) / 60)
        return float(s)
    except:
        return 0.0

# --- 4. UI: TABS ---
tab1, tab2, tab3 = st.tabs(["📝 Log Workout", "📊 Dashboard", "💾 Data View"])

with tab1:
    st.header("Log Session")
    c1, c2 = st.columns(2)
    with c1: date_input = st.date_input("Date", date.today())
    with c2: activity_type = st.selectbox("Activity", ["Run/Walk Intervals", "Jogging", "Walking", "Cycling", "Strength", "Tennis", "Other"])

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
        with c4: distance = st.number_input("Total Distance (km)", 0.0, step=0.1)
    elif activity_type in ["Jogging", "Walking", "Cycling"]:
        with c3: duration = st.number_input("Total Duration (min)", 1, step=1)
        with c4:
            distance = st.number_input("Distance (km)", 0.0, step=0.1)
            if activity_type == "Jogging": jog_split = duration
            if activity_type == "Walking": walk_split = duration
    elif activity_type == "Strength":
        with c3: duration = st.number_input("Total Duration (min)", 1, step=1)
        with c4: sub_category = st.radio("Focus", ["Upper", "Lower", "Full"], horizontal=True)
    else:
        with c3: duration = st.number_input("Total Duration (min)", 1, step=1)

    with c5:
        avg_hr = st.number_input("Avg HR", 0, step=1)
        if duration > 0 and distance > 0:
            speed_kmh = distance / (duration / 60)
            st.metric("Avg Speed", f"{speed_kmh:.1f} km/h")

    st.divider()
    st.subheader("Heart Rate Zones (MM:SS or Minutes)")
    
    # NEW INPUT METHOD
    z_col1, z_col2, z_col3, z_col4, z_col5 = st.columns(5)
    z1 = parse_time(z_col1.text_input("Zone 1", placeholder="MM:SS"))
    z2 = parse_time(z_col2.text_input("Zone 2", placeholder="MM:SS"))
    z3 = parse_time(z_col3.text_input("Zone 3", placeholder="MM:SS"))
    z4 = parse_time(z_col4.text_input("Zone 4", placeholder="MM:SS"))
    z5 = parse_time(z_col5.text_input("Zone 5", placeholder="MM:SS"))

    total_zone_time = z1 + z2 + z3 + z4 + z5
    if total_zone_time > 0 and duration > 0:
        if abs(total_zone_time - duration) > 0.1:
            st.warning(f"⚠️ Zone Sum ({total_zone_time:.2f}) ≠ Total Duration ({duration})")
        else:
            st.success("✅ Zones match duration")

    notes = st.text_area("Notes")

    if st.button("Save to Cloud", type="primary"):
        save_workout({
            'Date': date_input, 'Type': activity_type, 'Sub_Category': sub_category,
            'Duration_Min': duration, 'Distance_Km': distance, 'Speed_Kmh': speed_kmh,
            'Avg_HR': avg_hr, 'Jog_Split_Min': jog_split, 'Walk_Split_Min': walk_split,
            'Z1_Min': z1, 'Z2_Min': z2, 'Z3_Min': z3, 'Z4_Min': z4, 'Z5_Min': z5, 'Notes': notes
        })
        st.success("Saved!")

with tab2:
    if st.button("🔄 Force Reload"): st.cache_data.clear()
    df = load_data()
    if not df.empty:
        st.metric("Total Sessions", len(df))
        st.plotly_chart(px.bar(df, x='Date', y='Duration_Min', color='Type'), use_container_width=True)

with tab3:
    st.write("Connecting to Google Sheets...")
    df = load_data()
    st.dataframe(df, use_container_width=True)
