import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date

# --- 1. CONFIG & SETUP ---
st.set_page_config(page_title="Cloud Fitness v7", layout="wide")
st.title("☁️ CLOUD FITNESS v7 (Seconds Edition)")

# --- 2. GOOGLE SHEETS CONNECTION ---
def get_google_sheet():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        if "gcp_service_account" not in st.secrets:
            st.error("❌ Secrets missing.")
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
    if sheet is None: return pd.DataFrame()
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty and 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date']).dt.date
        return df
    except:
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

# --- 3. HELPER: Display Formatter (Minutes -> MM:SS) ---
def format_mmss(minutes):
    if pd.isna(minutes) or minutes == 0:
        return "00:00"
    mins = int(minutes)
    secs = int((minutes - mins) * 60)
    return f"{mins}:{secs:02d}"

# --- 4. INTERFACE ---
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
    
    # --- CHANGED: INPUT SECONDS ---
    st.subheader("Heart Rate Zones (Enter SECONDS)")
    st.caption("Example: 90 seconds = 1 min 30 sec")
    
    z_col1, z_col2, z_col3, z_col4, z_col5 = st.columns(5)
    
    # Inputs are Integers (Seconds)
    s1 = z_col1.number_input("Zone 1 (Sec)", min_value=0, step=1)
    s2 = z_col2.number_input("Zone 2 (Sec)", min_value=0, step=1)
    s3 = z_col3.number_input("Zone 3 (Sec)", min_value=0, step=1)
    s4 = z_col4.number_input("Zone 4 (Sec)", min_value=0, step=1)
    s5 = z_col5.number_input("Zone 5 (Sec)", min_value=0, step=1)

    # Convert to Minutes for calculation and storage
    z1, z2, z3, z4, z5 = s1/60, s2/60, s3/60, s4/60, s5/60
    
    total_zone_min = z1 + z2 + z3 + z4 + z5
    
    # Validation
    if total_zone_min > 0 and duration > 0:
        # We allow a small error margin (0.1 min) because seconds -> minutes isn't always perfect integer
        if abs(total_zone_min - duration) > 0.1:
            st.warning(f"⚠️ Zone Sum ({format_mmss(total_zone_min)}) ≠ Total Duration ({duration}:00)")
        else:
            st.success(f"✅ Zones match! ({format_mmss(total_zone_min)})")

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
    if st.button("🔄 Reload Data"): st.cache_data.clear()
    df = load_data()
    if not df.empty:
        # Apply the MM:SS formatter to the display dataframe only
        display_df = df.copy()
        zone_cols = ['Z1_Min', 'Z2_Min', 'Z3_Min', 'Z4_Min', 'Z5_Min']
        for col in zone_cols:
             if col in display_df.columns:
                 display_df[col] = display_df[col].apply(format_mmss)
        
        st.markdown("### 📈 Recent Activity")
        st.dataframe(display_df[['Date', 'Type', 'Duration_Min', 'Distance_Km', 'Z1_Min', 'Z2_Min', 'Z3_Min', 'Z4_Min', 'Z5_Min']], use_container_width=True)
        
        st.divider()
        st.caption("Visuals use Decimal Minutes for accuracy")
        # Stacked Bar Chart (Uses original df with floats, which is better for plotting)
        df_zones = df.melt(id_vars=['Date'], value_vars=zone_cols, var_name='Zone', value_name='Minutes')
        st.plotly_chart(px.bar(df_zones, x='Date', y='Minutes', color='Zone', 
                      color_discrete_map={'Z1_Min':'#A1C9F4', 'Z2_Min':'#FFB482', 'Z3_Min':'#8DE5A1', 'Z4_Min':'#FF9F9B', 'Z5_Min':'#D0BBFF'}), use_container_width=True)

with tab3:
    st.dataframe(load_data(), use_container_width=True)