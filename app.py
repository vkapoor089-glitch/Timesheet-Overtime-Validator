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

                    # Open and parse the Excel file using the calamine engine
                    with zip_ref.open(file_path) as file:
                        df = pd.read_excel(file, engine='calamine')
                        
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
                st.write("Select one or more employees below to generate a consolidated draft:")
                
                selected_rows = st.dataframe(
                    df_results, 
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="multi-row" 
                )
                
                selected_indices = [0]
                if selected_rows and selected_rows.get("selection", {}).get("rows"):
                    selected_indices = selected_rows["selection"]["rows"]
                
                active_emps = [summary_data[idx]["Employee"] for idx in selected_indices]
                
            with right_pane:
                st.subheader("✉️ Email Approval Workspace")
                
                emp_names_str = ", ".join(active_emps)
                
                col_mgr, col_subj = st.columns([1, 2])
                with col_mgr:
                    mgr = st.text_input("Manager Name", value="[Manager Name]")
                with col_subj:
                    subject_line = st.text_input("Subject Line", value=f"Action Required: Overtime Approval for {emp_names_str} ({client})")
                
                table_rows_html = ""
                
                # Loop through every selected employee and build rows + individual subtotals
                for emp in active_emps:
                    active_data = overtime_records[emp]
                    emp_decimal_hours = active_data["Total_Hours"]
                    
                    # 1. Add their specific daily rows
                    for entry in active_data["Breakdown"]:
                        table_rows_html += f"""
                        <tr>
                            <td style="border: 1px solid #dddddd; padding: 8px;">{emp}</td>
                            <td style="border: 1px solid #dddddd; padding: 8px;">{entry['Date']}</td>
                            <td style="border: 1px solid #dddddd; padding: 8px; text-align: center;">{entry['Hours']}</td>
                        </tr>
                        """
                    
                    # 2. Convert THIS employee's total back to HH:MM format
                    emp_h = int(emp_decimal_hours)
                    emp_m = int(round((emp_decimal_hours - emp_h) * 60))
                    if emp_m == 60:
                        emp_h += 1
                        emp_m = 0
                    formatted_emp_total = f"{emp_h:02d}:{emp_m:02d}"
                    
                    # 3. Add the subtotal row for this employee
                    table_rows_html += f"""
                    <tr style="background-color: #f9f9f9; font-weight: bold;">
                        <td colspan="2" style="border: 1px solid #dddddd; padding: 8px; text-align: right;">Total for {emp}:</td>
                        <td style="border: 1px solid #dddddd; padding: 8px; text-align: center;">{formatted_emp_total}</td>
                    </tr>
                    """
                
                email_html = f"""
                <div style="font-family: Calibri, Arial, sans-serif; font-size: 14px; color: #333333;">
                    <p>Hi {mgr},</p>
                    <p>Please review and approve the client-site overtime for the following team members: <strong>{emp_names_str}</strong>.</p>
                    
                    <table style="border-collapse: collapse; width: 100%; max-width: 500px; margin-top: 15px; margin-bottom: 15px;">
                        <thead>
                            <tr style="background-color: #f2f2f2;">
                                <th style="border: 1px solid #dddddd; padding: 8px; text-align: left;">Employee</th>
                                <th style="border: 1px solid #dddddd; padding: 8px; text-align: left;">Date</th>
                                <th style="border: 1px solid #dddddd; padding: 8px; text-align: center;">Working Hours</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows_html}
                        </tbody>
                    </table>
                    
                    <p>Please confirm your approval by replying to this email so we can process this accordingly.</p>
                    <p>Best regards,<br>
                    <strong>Finance and Operations</strong><br>
                    Empenofore Technologies</p>
                </div>
                """
                
                st.write("**Email Body Preview:**")
                st.html(email_html)
                st.info("💡 Highlight the text and table in the preview above, copy (`Ctrl+C`), and paste it directly into your email client.")
                
        else:
            st.warning("No weekend overtime (greater than 00:00) found in the uploaded timesheets.")
            
    except Exception as e:
        st.error(f"An error occurred while processing the ZIP file: {e}")
