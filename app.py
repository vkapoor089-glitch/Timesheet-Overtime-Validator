import streamlit as st
import pandas as pd
import zipfile

st.set_page_config(page_title="Timesheet Overtime Workspace", layout="wide")

st.title("Empenofore Technologies: Timesheet Validator")
st.write("Upload the weekly timesheet ZIP file to extract weekend overtime from employee folders.")

col_client, col_file = st.columns([1, 2])
with col_client:
    client = st.selectbox("Select Client Account", ["Macquarie", "Saxo", "Mashreq", "Zinnia", "Other"])
with col_file:
    uploaded_zip = st.file_uploader("Upload ZIP file containing employee folders", type="zip")

st.divider()

if uploaded_zip is not None:
    overtime_records = {}

    try:
        with zipfile.ZipFile(uploaded_zip, 'r') as zip_ref:
            for file_path in zip_ref.namelist():
                
                # Target ONLY the "Manage Attendance Report" files
                if 'Manage Attendance Report' in file_path and file_path.endswith('.xlsx') and '__MACOSX' not in file_path:
                    
                    # Extract Employee Name from the folder path 
                    path_parts = file_path.split('/')
                    if len(path_parts) >= 2:
                        emp_name = path_parts[-2]
                    else:
                        emp_name = "Unknown Employee"

                    # Open and parse the Excel file using the new 'calamine' engine
                    with zip_ref.open(file_path) as file:
                        df = pd.read_excel(file, engine='calamine')
                        
                        # Clean column headers
                        df.columns = df.columns.str.strip()
                        
                        if 'Date' in df.columns and 'Hours' in df.columns:
                            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                            
                            # Filter for Weekends (Sat=5, Sun=6)
                            weekend_work = df[df['Date'].dt.dayofweek >= 5].copy()
                            
                            def parse_hours(time_str):
                                try:
                                    t = str(time_str).strip()
                                    if ':' in t:
                                        h, m = t.split(':')
                                        return int(h) + int(m) / 60.0
                                    return float(t)
                                except:
                                    return 0.0

                            # Apply hour conversion and filter out 00:00 days
                            weekend_work['Decimal_Hours'] = weekend_work['Hours'].apply(parse_hours)
                            weekend_work = weekend_work[weekend_work['Decimal_Hours'] > 0]
                            
                            if not weekend_work.empty:
                                if emp_name not in overtime_records:
                                    overtime_records[emp_name] = {
                                        "Total_Hours": 0.0,
                                        "Breakdown": []
                                    }
                                
                                for _, row in weekend_work.iterrows():
                                    date_str = row['Date'].strftime('%d/%b/%Y')
                                    hrs_str = str(row['Hours']).strip()
                                    decimal_hrs = row['Decimal_Hours']
                                    
                                    overtime_records[emp_name]["Total_Hours"] += decimal_hrs
                                    overtime_records[emp_name]["Breakdown"].append({
                                        "Date": date_str,
                                        "Hours": hrs_str
                                    })

        # --- Render the Workspace Dashboard ---
        if overtime_records:
            summary_data = []
            for emp, details in overtime_records.items():
                summary_data.append({
                    "Employee": emp, 
                    "Total Weekend Hours": round(details["Total_Hours"], 2)
                })
                
            df_results = pd.DataFrame(summary_data)
            
            left_pane, right_pane = st.columns([4, 5], gap="large")
            
            with left_pane:
                st.subheader("📋 Overtime Summary")
                st.write("Click an employee to generate their draft:")
                
                selected_rows = st.dataframe(
                    df_results, 
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row"
                )
                
                selected_row_idx = 0
                if selected_rows and selected_rows.get("selection", {}).get("rows"):
                    selected_row_idx = selected_rows["selection"]["rows"][0]
                
                active_emp = summary_data[selected_row_idx]["Employee"]
                active_data = overtime_records[active_emp]
                
            with right_pane:
                st.subheader("✉️ Email Approval Workspace")
                
                col_mgr, col_subj = st.columns([1, 2])
                with col_mgr:
                    mgr = st.text_input("Manager Name", value="[Manager Name]")
                with col_subj:
                    subject_line = st.text_input("Subject Line", value=f"Action Required: Overtime Approval for {active_emp} ({client})")
                
                table_rows_html = ""
                for entry in active_data["Breakdown"]:
                    table_rows_html += f"""
                    <tr>
                        <td style="border: 1px
