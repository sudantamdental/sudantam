import streamlit as st
import pandas as pd
import datetime
from PIL import Image
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection
import io

# ==========================================
# 1. SETUP & ICON
# ==========================================

# Using the exact name of your logo file on GitHub
LOGO_FILE = "Final Logo_Vertical Color 2.png"
try:
    icon_img = Image.open(LOGO_FILE)
except:
    icon_img = "🦷"

st.set_page_config(
    page_title="Sudantam Clinic",
    page_icon=icon_img,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Mobile-friendly styling
st.markdown(f"""
<style>
    #MainMenu, footer, header {{visibility: hidden;}}
    .stApp {{ margin-top: -30px; }}
    div.stButton > button {{
        width: 100%; background-color: #2C7A6F; color: white; height: 55px;
        font-size: 18px; border-radius: 12px; border: none; margin-bottom: 10px;
    }}
    input, select, textarea {{ font-size: 16px !important; border-radius: 10px !important; }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATABASE CONNECTION (PUBLIC MODE)
# ==========================================

# This connects to your public Google Sheet
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="Patients", ttl=0)
        # Ensure standard columns are present
        cols = ["Name", "Age", "Gender", "Contact", "Last Visit", "Next Appointment", "Medical History", "Pending Amount"]
        for c in cols:
            if c not in df.columns: df[c] = ""
        return df
    except:
        return pd.DataFrame(columns=["Name", "Age", "Gender", "Contact", "Last Visit", "Next Appointment", "Medical History", "Pending Amount"])

def save_to_cloud(updated_df):
    # This sends data to the "Patients" tab of your Google Sheet
    conn.update(worksheet="Patients", data=updated_df)
    st.cache_data.clear()

# ==========================================
# 3. PDF GENERATOR
# ==========================================
class PDF(FPDF):
    def header(self):
        try: self.image(LOGO_FILE, 10, 8, 25) 
        except: pass
        self.set_font('Arial', 'B', 16)
        self.set_text_color(44, 122, 111)
        self.cell(0, 8, 'Dr. Sugam Jangid', 0, 1, 'R')
        self.ln(10)
        self.line(10, 35, 200, 35)

def create_pdf(name, age, sex, date, nxt, diag, advice, meds, total, paid, due):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"Patient: {name} ({age}/{sex})", 0, 1)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 6, f"Date: {date} | Next Visit: {nxt}", 0, 1)
    pdf.ln(5)
    pdf.multi_cell(0, 6, f"Diagnosis: {diag}\nAdvised: {advice}\nRx: {meds}")
    pdf.ln(5)
    pdf.cell(0, 8, f"Total: {total} | Paid: {paid} | Due: {due}", 0, 1)
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 4. MAIN INTERFACE
# ==========================================

st.title("🦷 Sudantam Clinic")
df = load_data()

menu = st.sidebar.radio("Menu", ["➕ Add Patient", "💊 Clinical & Bill", "💰 Dues", "📂 Records"])

if menu == "➕ Add Patient":
    with st.form("new_pt"):
        name = st.text_input("Full Name")
        c1, c2 = st.columns(2)
        age = c1.number_input("Age", 1, 100)
        sex = c2.selectbox("Gender", ["Male", "Female"])
        phone = st.text_input("Contact Number")
        
        if st.form_submit_button("💾 Save Patient"):
            if name:
                new_pt = pd.DataFrame([{
                    "Name": name, "Age": age, "Gender": sex, "Contact": phone,
                    "Last Visit": datetime.date.today().strftime("%d-%m-%Y"),
                    "Next Appointment": "TBD", "Pending Amount": 0
                }])
                final_df = pd.concat([df, new_pt], ignore_index=True)
                save_to_cloud(final_df)
                st.success(f"Saved {name} to Cloud!")
            else: st.error("Name is required")

elif menu == "💊 Clinical & Bill":
    pt = st.selectbox("Select Patient", [""] + df["Name"].tolist())
    if pt:
        idx = df[df["Name"] == pt].index[0]
        st.write(f"**Current Due:** ₹{df.at[idx, 'Pending Amount']}")
        
        diag = st.text_area("Diagnosis")
        meds = st.text_area("Medicines")
        bill = st.number_input("Bill Amount", value=0)
        paid = st.number_input("Paid Now", value=0)
        
        if st.button("Save & Generate PDF"):
            # Math
            new_due = (float(df.at[idx, 'Pending Amount']) + bill) - paid
            df.at[idx, 'Pending Amount'] = new_due
            save_to_cloud(df)
            
            # PDF
            pdf_bytes = create_pdf(pt, df.at[idx, 'Age'], df.at[idx, 'Gender'], 
                                   datetime.date.today().strftime("%d-%m-%Y"), "Next Week",
                                   diag, "Procedures Done", meds, bill, paid, new_due)
            st.download_button("📂 Download Prescription", pdf_bytes, f"{pt}_Rx.pdf")
            st.success("Record Updated!")

elif menu == "💰 Dues":
    df["Pending Amount"] = pd.to_numeric(df["Pending Amount"], errors='coerce').fillna(0)
    dues = df[df["Pending Amount"] > 0]
    st.table(dues[["Name", "Contact", "Pending Amount"]])

elif menu == "📂 Records":
    st.dataframe(df)
