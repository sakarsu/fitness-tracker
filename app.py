import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date, datetime, timedelta

# --- 1. CONFIG & GOOGLE SHEETS ---
st.set_page_config(page_title="Cloud Fitness v16", layout="wide")

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
        
        # Self-Healing: Ensure columns exist
        expected_cols = [
            'Date', 'Type', 'Sub_Category', 'Duration_Min', 'Distance_Km', 
            'Speed_Kmh', 'Avg_HR', 'Jog_Split_Min', 'Walk_Split_Min', 
            'Z1_Min', 'Z2_Min', 'Z3_Min', 'Z4_Min', 'Z5_Min', 'Notes'
        ]
        
        if df.empty:
            return pd.DataFrame(columns=expected_cols)

        for col in expected_cols:
            if col not in df.columns:
                df[col] = "" if col in ['Notes', 'Type', 'Sub_Category'] else 0.0

        # Date & Number conversion
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        
        numeric_cols = [
            'Duration_Min', 'Distance_Km', 'Speed_Kmh', 'Avg_HR', 
            'Jog_Split_Min', 'Walk_Split_Min', 
            'Z1_Min', 'Z2_Min', 'Z3_Min', 'Z4_Min', 'Z5_Min'
        ]
        for col in numeric_cols:
            # Comma Fixer: 1,27 -> 1.27
            df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
                
        return df
    except Exception:
        return pd.DataFrame()

def save_workout(entry):
    sheet = get_google_sheet()
    row = [
        str(entry['Date']), entry['Type'], entry['Sub_Category'],
        entry['Duration_Min'], entry['Distance_Km'], entry['Speed_Kmh'],
        entry['Avg_HR'], entry['Jog_Split_Min'], entry['Walk_Split_Min'],
        entry['Z1_Min'], entry['Z2_Min'], entry['Z3_Min'], entry['Z4_Min'], entry['Z5_Min'],
        entry['Notes']
    ]
    sheet.append_row(row)

# --- HELPERS ---
def parse_time(input_str):
    if not input_str: return 0.0
    s = str(input_str).strip().replace(',', '.') 
    try:
        if ':' in s:
            parts = s.split(':')
            return float(parts[0]) + (float(parts[1]) / 60)
        return float(s)
    except ValueError:
        return 0.0

def format_mmss(minutes):
    if minutes == 0: return "00:00"
    mins = int(minutes)
    secs = int((minutes - mins) * 60)
    return f"{mins}:{secs:02d}"

# --- 2. INTERFACE ---
st.title("☁️ Cloud Fitness Tracker")
tab1, tab2, tab3 = st.tabs(["📝 Log Workout", "📊 Dashboard", "💾 Data View"])

# --- TAB 1: LOGGING ---
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
            jog_str = st.text_input("Jogging Time", placeholder="MM:SS")
            walk_str = st.text_input("Walking Time", placeholder="MM:SS")
            jog_split = parse_time(jog_str)
            walk_split = parse_time(walk_str)
            duration = jog_split + walk_split
            st.write(f"**Total: {format_mmss(duration)}**")
        with c4: 
            dist_str = st.text_input("Total Distance (km)", placeholder="5,2")
            distance = float(dist_str.replace(',', '.')) if dist_str else 0.0
            
    elif activity_type in ["Jogging", "Walking", "Cycling"]:
        with c3: 
            dur_str = st.text_input("Total Duration", placeholder="MM:SS")
            duration = parse_time(dur_str)
        with c4:
            dist_str = st.text_input("Distance (km)", placeholder="5,2")
            distance = float(dist_str.replace(',', '.')) if dist_str else 0.0
            if activity_type == "Jogging": jog_split = duration
            if activity_type == "Walking": walk_split = duration
            
    elif activity_type == "Strength":
        with c3: 
            dur_str = st.text_input("Total Duration", placeholder="MM:SS")
            duration = parse_time(dur_str)
        with c4: sub_category = st.radio("Focus", ["Upper", "Lower", "Full"], horizontal=True)
        
    elif activity_type in ["Tennis", "Other"]:
        with c3: 
            dur_str = st.text_input("Total Duration", placeholder="MM:SS")
            duration = parse_time(dur_str)

    with c5:
        avg_hr = st.number_input("Avg HR", 0, step=1)
        if duration > 0 and distance > 0:
            speed_kmh = distance / (duration / 60)
            st.metric("Avg Speed", f"{speed_kmh:.1f} km/h")

    st.divider()
    st.subheader("Heart Rate Zones (MM:SS)")
    z_col1, z_col2, z_col3, z_col4, z_col5 = st.columns(5)
    z1 = parse_time(z_col1.text_input("Zone 1 (Hafif)", placeholder="MM:SS"))
    z2 = parse_time(z_col2.text_input("Zone 2 (Yoğun)", placeholder="MM:SS"))
    z3 = parse_time(z_col3.text_input("Zone 3 (Aerobik)", placeholder="MM:SS"))
    z4 = parse_time(z_col4.text_input("Zone 4 (Anaerobik)", placeholder="MM:SS"))
    z5 = parse_time(z_col5.text_input("Zone 5 (VO2)", placeholder="MM:SS"))

    total_zones = z1+z2+z3+z4+z5
    if total_zones > 0 and duration > 0:
        if abs(total_zones - duration) > 0.1:
            st.warning(f"⚠️ Sum ({format_mmss(total_zones)}) ≠ Duration ({format_mmss(duration)})")
        else:
            st.success("✅ Zones match")

    notes = st.text_area("Notes")

    if st.button("Save to Cloud", type="primary"):
        save_workout({
            'Date': date_input, 'Type': activity_type, 'Sub_Category': sub_category,
            'Duration_Min': duration, 'Distance_Km': distance, 'Speed_Kmh': speed_kmh,
            'Avg_HR': avg_hr, 'Jog_Split_Min': jog_split, 'Walk_Split_Min': walk_split,
            'Z1_Min': z1, 'Z2_Min': z2, 'Z3_Min': z3, 'Z4_Min': z4, 'Z5_Min': z5, 'Notes': notes
        })
        st.success("Saved!")

# --- TAB 2: DASHBOARD ---
with tab2:
    if st.button("🔄 Refresh Data"): st.cache_data.clear()
    
    df_raw = load_data()
    
    if not df_raw.empty:
        # FILTER
        st.markdown("### 📅 Time Filter")
        c_filter1, c_filter2 = st.columns([1, 2])
        with c_filter1:
            time_range = st.radio("Select Period:", ["This Week", "This Month", "All Time", "Custom Range"])
            
        today = pd.Timestamp.now().normalize()
        start_date, end_date = None, None
        
        if time_range == "This Week":
            start_date = today - timedelta(days=today.weekday())
            end_date = today
        elif time_range == "This Month":
            start_date = today.replace(day=1)
            end_date = today
        elif time_range == "Custom Range":
            with c_filter2:
                custom_dates = st.date_input("Pick Range", [today - timedelta(days=30), today])
                if len(custom_dates) == 2:
                    start_date, end_date = pd.Timestamp(custom_dates[0]), pd.Timestamp(custom_dates[1])

        df = df_raw.copy()
        if time_range != "All Time" and start_date and end_date:
            df = df[ (df['Date'] >= start_date) & (df['Date'] <= end_date) ]

        if df.empty:
            st.warning("No data for this period.")
        else:
            # Stats
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Dist", f"{df['Distance_Km'].sum():.1f} km")
            m2.metric("Total Duration", f"{format_mmss(df['Duration_Min'].sum())}")
            m3.metric("Sessions", len(df))
            st.divider()

            # --- 1. ZONE ANALYSIS (Replacing Calendar) ---
            st.subheader("🎯 Zone Analysis")
            z_col1, z_col2 = st.columns([2, 1])
            
            # CHART 1: Daily Stacked Bar (When did I do it?)
            with z_col1:
                df_zones = df.melt(id_vars=['Date'], value_vars=['Z1_Min', 'Z2_Min', 'Z3_Min', 'Z4_Min', 'Z5_Min'], var_name='Zone', value_name='Minutes')
                watch_colors = {'Z1_Min':'#00BFFF', 'Z2_Min':'#00CC66', 'Z3_Min':'#FFCC00', 'Z4_Min':'#FF9500', 'Z5_Min':'#FF3B30'}
                
                fig_bar = px.bar(
                    df_zones, x='Date', y='Minutes', color='Zone', 
                    color_discrete_map=watch_colors,
                    title="Daily Zone Load"
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            # CHART 2: Summary Donut (What are the totals?)
            with z_col2:
                # Calculate sums for the Donut
                total_z1 = df['Z1_Min'].sum()
                total_z2 = df['Z2_Min'].sum()
                total_z3 = df['Z3_Min'].sum()
                total_z4 = df['Z4_Min'].sum()
                total_z5 = df['Z5_Min'].sum()
                
                # Create mini DataFrame for Plotly
                pie_data = pd.DataFrame({
                    'Zone': ['Zone 1 (Hafif)', 'Zone 2 (Yoğun)', 'Zone 3 (Aerobik)', 'Zone 4 (Anaerobik)', 'Zone 5 (VO2)'],
                    'Minutes': [total_z1, total_z2, total_z3, total_z4, total_z5],
                    'ColorKey': ['Z1_Min', 'Z2_Min', 'Z3_Min', 'Z4_Min', 'Z5_Min']
                })
                # Filter out zeroes to keep chart clean
                pie_data = pie_data[pie_data['Minutes'] > 0]
                
                # Add formatted time for hover
                pie_data['Formatted'] = pie_data['Minutes'].apply(format_mmss)
                
                fig_pie = px.pie(
                    pie_data, 
                    values='Minutes', 
                    names='Zone',
                    color='ColorKey',
                    color_discrete_map=watch_colors,
                    hole=0.4, # Makes it a Donut
                    title=f"Total: {format_mmss(df['Duration_Min'].sum())}"
                )
                
                # CUSTOM HOVER & TEXT: Shows "12:30 (55%)"
                fig_pie.update_traces(
                    textinfo='percent',
                    hovertemplate="<b>%{label}</b><br>Time: %{customdata[0]}<br>Ratio: %{percent}",
                    customdata=pie_data[['Formatted']]
                )
                # Move legend to bottom to save width
                fig_pie.update_layout(legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
                
                st.plotly_chart(fig_pie, use_container_width=True)

            st.divider()

            # --- 2. INTERVALS & EFFICIENCY ---
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Interval Evolution")
                df_splits = df.melt(id_vars=['Date', 'Type'], value_vars=['Jog_Split_Min', 'Walk_Split_Min'], var_name='Split_Type', value_name='Minutes')
                df_splits = df_splits[df_splits['Minutes'] > 0]
                st.plotly_chart(px.bar(df_splits, x='Date', y='Minutes', color='Split_Type', title="Jog vs Walk Ratio", color_discrete_map={'Jog_Split_Min': '#FF9500', 'Walk_Split_Min': '#00BFFF'}), use_container_width=True)

            with c2:
                st.subheader("Efficiency Analysis")
                df_move = df[ (df['Speed_Kmh'] > 0) & (df['Avg_HR'] > 0) ].copy()
                if not df_move.empty:
                    df_move['Distance_Km'] = df_move['Distance_Km'].clip(lower=0.5)
                    st.plotly_chart(px.scatter(
                        df_move, x='Avg_HR', y='Speed_Kmh', color='Type', 
                        size='Distance_Km', 
                        hover_data=['Date', 'Notes'] if 'Notes' in df_move.columns else ['Date'], 
                        title="Efficiency (Goal: Top-Left)"
                    ), use_container_width=True)
                else:
                    st.info("Log runs with Speed & HR to see chart.")

with tab3:
    st.markdown("### 💾 Raw Data (MM:SS)")
    df_display = load_data().copy()
    if not df_display.empty:
        time_cols = ['Duration_Min', 'Jog_Split_Min', 'Walk_Split_Min', 'Z1_Min', 'Z2_Min', 'Z3_Min', 'Z4_Min', 'Z5_Min']
        for col in time_cols:
            if col in df_display.columns:
                df_display[col] = df_display[col].apply(format_mmss)
    st.dataframe(df_display, use_container_width=True)
