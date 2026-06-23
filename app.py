import streamlit as st
import pandas as pd
import zipfile
import io

# Setup the webpage layout
st.set_page_config(page_title="Timesheet Overtime Validator", layout="wide")

st.title("Empenofore Technologies: Timesheet Validator")
st.write("Upload the weekly timesheet ZIP file to automatically calculate weekend overtime and generate approval drafts.")

# Optional: Client selector for tracking
client = st.selectbox("Select Client Account", ["Macquarie", "Saxo", "Mashreq", "Zinnia", "Other"])

# The File Uploader
uploaded_zip = st.file_uploader("Upload ZIP file containing timesheets (.xlsx)", type="zip")

if uploaded_zip is not None:
    st.info("Scanning timesheets...")
    overtime_data = []

    try:
        # Open the ZIP file directly from memory
        with zipfile.ZipFile(uploaded_zip, 'r') as zip_ref:
            for file_name in zip_ref.namelist():
                # Process only Excel files and ignore hidden Mac files
                if file_name.endswith('.xlsx') and not file_name.startswith('__MACOSX'):
                    with zip_ref.open(file_name) as file:
                        df = pd.read_excel(file)
                        
                        # Ensure 'Date' column exists to prevent errors
                        if 'Date' in df.columns:
                            df['Date'] = pd.to_datetime(df['Date'])
                            
                            # Filter for Saturday (5) and Sunday (6)
                            weekend_work = df[df['Date'].dt.dayofweek >= 5]
                            
                            if not weekend_work.empty:
                                # Calculate total weekend hours per employee/manager combination
                                summary = weekend_work.groupby(['Employee Name', 'Manager Name'])['Hours'].sum().reset_index()
                                for _, row in summary.iterrows():
                                    overtime_data.append({
                                        'Employee': row['Employee Name'],
                                        'Manager': row['Manager Name'],
                                        'Total_Weekend_Hours': row['Hours']
                                    })

        # Display Results
        if overtime_data:
            st.success(f"Overtime data successfully extracted for {client}.")
            
            st.subheader("Overtime Summary")
            results_df = pd.DataFrame(overtime_data)
            st.dataframe(results_df, use_container_width=True)

            st.divider()
            
            st.subheader("Email Drafts for Management Approval")
            for data in overtime_data:
                emp = data['Employee']
                mgr = data['Manager']
                hrs = data['Total_Weekend_Hours']
                
                draft = f"""**Subject:** Action Required: Overtime Approval for {emp} ({client} Account)

Hi {mgr},

Please review and approve the client-site overtime for {emp}. 
They have logged a total of {hrs} hours of weekend work during this billing cycle.

Please confirm your approval by replying to this email so we can process this accordingly.

Best regards,
Finance and Operations
Empenofore Technologies
"""
                # Put each draft in a neat dropdown box
                with st.expander(f"Draft for {emp} (Manager: {mgr})"):
                    st.markdown(draft)
                    
        else:
            st.warning("No weekend overtime found in the uploaded timesheets.")
            
    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")
