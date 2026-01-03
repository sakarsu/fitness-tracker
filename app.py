import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date, datetime, timedelta

# --- 1. CONFIG & GOOGLE SHEETS ---
st.set_page_config(page_title="Cloud Fitness v21", layout="wide")

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
        
        # Self-Healing Columns
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

        # Type conversion & Cleaning
        # IMPORTANT: Normalize to midnight to ensure stacking works perfectly
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.normalize()
        
        numeric_cols = [
            'Duration_Min', 'Distance_Km', 'Speed_Kmh', 'Avg_HR', 
            'Jog_Split_Min', 'Walk_Split_Min', 
            'Z1_Min', 'Z2_Min', 'Z3_Min', 'Z4_Min', 'Z5_Min'
        ]
        for col in numeric_cols:
            df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        
        # Zone 0 Calculation
        zone_sum = df[['Z1_Min', 'Z2_Min', 'Z3_Min', 'Z4_Min', 'Z5_Min']].sum(axis=1)
        df['Z0_Min'] = (df['Duration_Min'] - zone_sum).clip(lower=0)
                
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
        diff = duration - total_zones
        if diff < -0.1:
             st.warning(f"⚠️ Zones sum ({format_mmss(total_zones)}) exceeds Duration ({format_mmss(duration)})")
        elif diff > 0.1:
             st.info(f"ℹ️ Remaining {format_mmss(diff)} will be tracked as 'Zone 0' (Rest).")
        else:
             st.success("✅ Zones match perfectly")

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
            # --- AI PROMPT GENERATOR ---
            with st.expander("🤖 Generate AI Coach Prompt (Click to Expand)", expanded=False):
                st.caption("Copy this text and paste it into ChatGPT/Gemini/Claude for instant analysis.")
                
                total_dist = df['Distance_Km'].sum()
                total_time = df['Duration_Min'].sum()
                avg_hr = df[df['Avg_HR'] > 0]['Avg_HR'].mean() if not df[df['Avg_HR'] > 0].empty else 0
                
                cardio_df = df[~df['Type'].isin(['Strength', 'Other'])]
                z1_pct = (cardio_df['Z1_Min'].sum() / cardio_df['Duration_Min'].sum() * 100) if not cardio_df.empty and cardio_df['Duration_Min'].sum() > 0 else 0
                z2_pct = (cardio_df['Z2_Min'].sum() / cardio_df['Duration_Min'].sum() * 100) if not cardio_df.empty and cardio_df['Duration_Min'].sum() > 0 else 0
                z3_pct = (cardio_df['Z3_Min'].sum() / cardio_df['Duration_Min'].sum() * 100) if not cardio_df.empty and cardio_df['Duration_Min'].sum() > 0 else 0
                z4_pct = (cardio_df['Z4_Min'].sum() / cardio_df['Duration_Min'].sum() * 100) if not cardio_df.empty and cardio_df['Duration_Min'].sum() > 0 else 0
                z5_pct = (cardio_df['Z5_Min'].sum() / cardio_df['Duration_Min'].sum() * 100) if not cardio_df.empty and cardio_df['Duration_Min'].sum() > 0 else 0
                high_intensity_pct = ((cardio_df['Z4_Min'].sum() + cardio_df['Z5_Min'].sum()) / cardio_df['Duration_Min'].sum() * 100) if not cardio_df.empty and cardio_df['Duration_Min'].sum() > 0 else 0
                
                prompt_text = f"""
Act as an elite Performance Physiologist. Analyze the following training data for a 112 kg male athlete managing Metabolic Syndrome traits (High LDL, High CRP).
Here is my training data for the period: {time_range}.

**Summary:**
- Total Duration: {int(total_time)} minutes
- Number of Sessions: {len(df)}
- Average Heart Rate: {int(avg_hr)} bpm

**Intensity Distribution (Cardio):**
- Zone 1: {z1_pct:.1f}%
- Zone 2: {z2_pct:.1f}%
- Zone 3: {z3_pct:.1f}%
- Zone 4: {z4_pct:.1f}%
- Zone 5: {z5_pct:.1f}%

**Specific Workouts:**
{df[['Date', 'Type', 'Duration_Min', 'Distance_Km', 'Avg_HR']].to_string(index=False)}

**My Goal:** I want to improve my cardio base, lose weight, maintain muscle, keep my borderline blood sugar and cholesterol levels in check.
**Question:** Based on this data, am I following an efficient workout routine? Is there any thing I should change next week to improve efficiency?
"""
                st.code(prompt_text, language="text")

            # STATS
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Dist", f"{df['Distance_Km'].sum():.1f} km")
            m2.metric("Total Duration", f"{format_mmss(df['Duration_Min'].sum())}")
            m3.metric("Sessions", len(df))
            st.divider()

            # --- 1. CARDIO ZONE ANALYSIS ---
            st.subheader("🎯 Cardio Zone Analysis")
            
            df_cardio = df[ ~df['Type'].isin(['Strength', 'Other']) ].copy()
            
            if df_cardio.empty:
                st.info("No Cardio workouts found in this period.")
            else:
                z_col1, z_col2 = st.columns([2, 1])
                
                watch_colors = {
                    'Z0_Min': '#D3D3D3',
                    'Z1_Min': '#00BFFF', 'Z2_Min': '#00CC66', 'Z3_Min': '#FFCC00', 
                    'Z4_Min': '#FF9500', 'Z5_Min': '#FF3B30'
                }
                
                # CHART 1: Stacked Bar
                with z_col1:
                    df_zones = df_cardio.melt(id_vars=['Date'], value_vars=['Z0_Min', 'Z1_Min', 'Z2_Min', 'Z3_Min', 'Z4_Min', 'Z5_Min'], var_name='Zone', value_name='Minutes')
                    df_zones = df_zones[df_zones['Minutes'] > 0]
                    
                    fig_bar = px.bar(
                        df_zones, x='Date', y='Minutes', color='Zone', 
                        color_discrete_map=watch_colors,
                        title="Daily Cardio Load"
                    )
                    # FIX: Back to 'date' type for nice spacing, with strict format
                    fig_bar.update_xaxes(type='date', tickformat="%b %d, %Y")
                    st.plotly_chart(fig_bar, use_container_width=True)

                # CHART 2: Donut (FIXED LEGEND ORDER)
                with z_col2:
                    sums = df_cardio[['Z0_Min', 'Z1_Min', 'Z2_Min', 'Z3_Min', 'Z4_Min', 'Z5_Min']].sum()
                    strict_order = ['Zone 0 (Rest)', 'Zone 1 (Hafif)', 'Zone 2 (Yoğun)', 'Zone 3 (Aerobik)', 'Zone 4 (Anaerobik)', 'Zone 5 (VO2)']
                    
                    pie_data = pd.DataFrame({
                        'Zone': strict_order,
                        'Minutes': sums.values,
                        'ColorKey': ['Z0_Min', 'Z1_Min', 'Z2_Min', 'Z3_Min', 'Z4_Min', 'Z5_Min']
                    })
                    pie_data = pie_data[pie_data['Minutes'] > 0]
                    pie_data['Formatted'] = pie_data['Minutes'].apply(format_mmss)
                    
                    fig_pie = px.pie(
                        pie_data, values='Minutes', names='Zone', color='ColorKey',
                        color_discrete_map=watch_colors, hole=0.4,
                        category_orders={'Zone': strict_order},
                        title=f"Total: {format_mmss(df_cardio['Duration_Min'].sum())}"
                    )
                    
                    fig_pie.update_traces(
                        textinfo='percent',
                        hovertemplate="<b>%{label}</b><br>Time: %{customdata[0]}<br>Ratio: %{percent}",
                        customdata=pie_data[['Formatted']],
                        sort=False 
                    )
                    fig_pie.update_layout(legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
                    st.plotly_chart(fig_pie, use_container_width=True)

            st.divider()

            # --- 2. INTERVALS & EFFICIENCY ---
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Interval Evolution")
                df_splits = df.melt(id_vars=['Date', 'Type'], value_vars=['Jog_Split_Min', 'Walk_Split_Min'], var_name='Split_Type', value_name='Minutes')
                df_splits = df_splits[df_splits['Minutes'] > 0]
                
                fig_int = px.bar(
                    df_splits, x='Date', y='Minutes', color='Split_Type', 
                    title="Jog vs Walk Ratio", 
                    color_discrete_map={'Jog_Split_Min': '#FF9500', 'Walk_Split_Min': '#00BFFF'}
                )
                # FIX: Strict Date Format
                fig_int.update_xaxes(type='date', tickformat="%b %d, %Y")
                st.plotly_chart(fig_int, use_container_width=True)

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

            # --- 3. STRENGTH ---
            st.divider()
            st.subheader("🏋️ Strength Training Log")
            df_strength = df[ df['Type'] == 'Strength' ].copy()
            if df_strength.empty:
                st.info("No Strength sessions logged yet.")
            else:
                s_col1, s_col2 = st.columns([3, 1])
                with s_col1:
                    fig_str = px.bar(
                        df_strength, x='Date', y='Duration_Min', color='Sub_Category',
                        title="Strength Consistency & Focus",
                        labels={'Duration_Min': 'Duration (min)', 'Sub_Category': 'Focus Area'}
                    )
                    # FIX: Use EXACT same logic as Cardio (Date axis)
                    fig_str.update_xaxes(type='date', tickformat="%b %d, %Y")
                    st.plotly_chart(fig_str, use_container_width=True)
                with s_col2:
                    st.metric("Total Sessions", len(df_strength))
                    st.metric("Total Time", format_mmss(df_strength['Duration_Min'].sum()))

with tab3:
    st.markdown("### 💾 Raw Data (MM:SS)")
    df_display = load_data().copy()
    if not df_display.empty:
        time_cols = ['Duration_Min', 'Jog_Split_Min', 'Walk_Split_Min', 'Z1_Min', 'Z2_Min', 'Z3_Min', 'Z4_Min', 'Z5_Min']
        for col in time_cols:
            if col in df_display.columns:
                df_display[col] = df_display[col].apply(format_mmss)
    st.dataframe(df_display, use_container_width=True)
