import streamlit as st
import pandas as pd
import datetime
from PIL import Image
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection
import io

# ==========================================
# 1. CONFIGURATION & SETUP
# ==========================================

# --- LOAD LOGO ROBUSTLY ---
# We try to load your specific logo file. If it fails, we use a tooth emoji.
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

# --- THEME (Mobile Friendly) ---
PRIMARY = "#2C7A6F"
SECONDARY = "#F0F8F5"

st.markdown(f"""
<style>
    /* Clean Mobile UI */
    #MainMenu, footer, header {{visibility: hidden;}}
    .stApp {{ margin-top: -30px; }}
    [data-testid="stSidebar"] {{ background-color: {SECONDARY}; }}
    
    /* Big Touch-Friendly Buttons */
    div.stButton > button {{
        width: 100%; background-color: {PRIMARY}; color: white; height: 55px;
        font-size: 18px; border-radius: 12px; border: none; margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    div.stButton > button:active {{ transform: scale(0.98); }}
    
    /* Input Fields */
    input, select, textarea {{ font-size: 16px !important; border-radius: 10px !important; }}
    
    /* Success/Error Messages */
    .stAlert {{ padding: 10px; border-radius: 10px; }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATABASE & HELPER FUNCTIONS
# ==========================================

# Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    """Loads patient data from the 'Patients' tab of your Google Sheet."""
    try:
        df = conn.read(worksheet="Patients", ttl=0) # ttl=0 means no caching (always fresh)
        # Ensure necessary columns exist
        cols = ["Patient ID", "Name", "Age", "Gender", "Contact", "Last Visit", "Next Appointment", "Medical History", "Pending Amount"]
        for c in cols:
            if c not in df.columns: df[c] = ""
        return df
    except:
        return pd.DataFrame(columns=["Patient ID", "Name", "Age", "Gender", "Contact", "Last Visit", "Next Appointment", "Medical History", "Pending Amount"])

def update_data(df):
    """Saves the dataframe back to Google Sheets."""
    conn.update(worksheet="Patients", data=df)
    st.cache_data.clear() # Clear cache to force reload

# Standard Lists
TREATMENT_PRICES = {
    "Consultation": 200, "X-Ray (IOPA)": 150, "Scaling": 800, "Extraction": 500, 
    "Restoration": 1000, "RCT": 3500, "Crown (Metal)": 2000, "Crown (Ceramic)": 4000, 
    "Implant": 15000, "Braces": 25000, "Bleaching": 5000
}
MED_HISTORY = ["Diabetes", "BP", "Thyroid", "Cardiac", "Allergy", "Pregnancy"]
COMMON_DX = ["Caries", "Abscess", "Gingivitis", "Fracture", "Mobile Tooth", "Impaction", "Pulpitis"]
COMMON_MEDS = ["Augmentin 625", "Amoxicillin 500", "Metrogyl 400", "Zerodol-SP", "Ketorol-DT", "Pan-D", "Hexidine"]

# ==========================================
# 3. PDF GENERATION CLASS
# ==========================================
class PDF(FPDF):
    def header(self):
        # Logo handling for PDF
        try:
            self.image(LOGO_FILE, 10, 8, 25) 
        except: pass # If logo missing on server, skip it
        
        self.set_font('Arial', 'B', 16)
        self.set_text_color(44, 122, 111) # Sudantam Green
        self.cell(0, 8, 'Dr. Sugam Jangid', 0, 1, 'R')
        self.set_font('Arial', 'I', 10)
        self.set_text_color(50)
        self.cell(0, 5, 'Dental Surgeon (BDS)', 0, 1, 'R')
        self.cell(0, 5, '+91-8078656835', 0, 1, 'R')
        self.ln(10)
        self.line(10, 35, 200, 35)

    def footer(self):
        self.set_y(-25)
        self.set_font('Arial', 'I', 9)
        self.set_text_color(128)
        self.cell(0, 5, 'Opposite Agrasen Bhawan, Kishangarh', 0, 1, 'C')
        self.cell(0, 5, 'Timing: 9AM-2PM & 4PM-8PM', 0, 1, 'C')

def create_pdf(pt_name, age, sex, date, next_visit, diag, advice, meds, treatments, total, paid, due):
    pdf = PDF()
    pdf.add_page()
    
    # Patient Info
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(0)
    pdf.cell(0, 8, f"Patient: {pt_name}  ({age}/{sex})", 0, 1)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 6, f"Date: {date}", 0, 1)
    if next_visit != "Not Required":
        pdf.set_text_color(200, 0, 0)
        pdf.cell(0, 6, f"Next Appointment: {next_visit}", 0, 1)
    pdf.ln(5)

    # Clinical Notes
    pdf.set_text_color(0)
    if diag:
        pdf.set_font("Arial", 'B', 11); pdf.cell(0, 6, "Diagnosis:", 0, 1)
        pdf.set_font("Arial", '', 11); pdf.multi_cell(0, 6, f"- {diag}")
        pdf.ln(2)
    
    if advice:
        pdf.set_font("Arial", 'B', 11); pdf.cell(0, 6, "Treatment Done / Advised:", 0, 1)
        pdf.set_font("Arial", '', 11); pdf.multi_cell(0, 6, f"- {advice}")
        pdf.ln(2)

    if meds:
        pdf.set_font("Arial", 'B', 11); pdf.cell(0, 6, "Prescription (Rx):", 0, 1)
        pdf.set_font("Arial", '', 11); pdf.multi_cell(0, 6, meds)
        pdf.ln(5)

    # Billing Section
    if treatments:
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 12); pdf.cell(0, 8, "INVOICE", 0, 1, 'C')
        
        pdf.set_font("Arial", '', 11)
        for tx in treatments:
            pdf.cell(140, 7, tx[0], 1)
            pdf.cell(50, 7, f"{tx[1]}", 1, 1, 'R')
            
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(140, 8, "Total Amount", 1); pdf.cell(50, 8, f"{total}", 1, 1, 'R')
        pdf.cell(140, 8, "Paid Now", 1); pdf.cell(50, 8, f"{paid}", 1, 1, 'R')
        
        if due > 0:
            pdf.set_text_color(200, 0, 0)
            pdf.cell(140, 8, "Balance Due", 1); pdf.cell(50, 8, f"{due}", 1, 1, 'R')
        else:
            pdf.set_text_color(0, 128, 0)
            pdf.cell(140, 8, "Status", 1); pdf.cell(50, 8, "Paid", 1, 1, 'R')

    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 4. MAIN APP UI
# ==========================================

# --- HEADER ---
c1, c2 = st.columns([1, 5])
with c1:
    try: st.image(LOGO_FILE, width=70)
    except: st.write("🦷")
with c2:
    st.markdown(f"<h1 style='color:{PRIMARY}; margin:0; padding-top:10px;'>Sudantam Clinic</h1>", unsafe_allow_html=True)

# --- SIDEBAR MENU ---
with st.sidebar:
    st.title("Menu")
    menu = ["➕ New Patient", "💊 Clinical & Bill", "💰 Manage Dues", "🔍 Patient Records"]
    choice = st.radio("", menu, label_visibility="collapsed")
    st.markdown("---")
    if st.button("🔄 Force Sync Data"):
        st.cache_data.clear()
        st.rerun()

df = load_data()

# --- PAGE 1: NEW PATIENT ---
if choice == "➕ New Patient":
    st.markdown("### Add New Patient")
    with st.form("new_pt_form"):
        name = st.text_input("Full Name")
        c1, c2 = st.columns(2)
        age = c1.number_input("Age", 1, 100, step=1)
        gender = c2.selectbox("Gender", ["Male", "Female", "Other"])
        phone = st.text_input("Phone Number")
        
        st.markdown("**Medical History**")
        hist = st.multiselect("Select Conditions", MED_HISTORY)
        
        # Dental Chart (Simplified for Mobile)
        st.markdown("**Teeth Selection**")
        with st.expander("Open Dental Chart"):
            teeth_sel = []
            tc1, tc2 = st.columns(2)
            with tc1:
                st.caption("Left Side")
                for i in range(8, 0, -1):
                    if st.checkbox(f"Upper L {i}", key=f"UL{i}"): teeth_sel.append(f"UL{i}")
                for i in range(8, 0, -1):
                    if st.checkbox(f"Lower L {i}", key=f"LL{i}"): teeth_sel.append(f"LL{i}")
            with tc2:
                st.caption("Right Side")
                for i in range(1, 9):
                    if st.checkbox(f"Upper R {i}", key=f"UR{i}"): teeth_sel.append(f"UR{i}")
                for i in range(1, 9):
                    if st.checkbox(f"Lower R {i}", key=f"LR{i}"): teeth_sel.append(f"LR{i}")
            teeth_str = ", ".join(teeth_sel)

        today = datetime.date.today()
        sched = st.checkbox("Schedule Next Visit?", True)
        if sched:
            nxt = st.date_input("Next Appointment", today + datetime.timedelta(days=7))
            nxt_str = nxt.strftime("%d-%m-%Y")
        else:
            nxt_str = "Not Required"
        
        if st.form_submit_button("💾 Save Patient"):
            if name:
                new_entry = pd.DataFrame([{
                    "Patient ID": len(df)+101, "Name": name, "Age": age, "Gender": gender, "Contact": phone,
                    "Last Visit": today.strftime("%d-%m-%Y"), "Next Appointment": nxt_str,
                    "Medical History": ", ".join(hist) + (f" | Teeth: {teeth_str}" if teeth_str else ""),
                    "Pending Amount": 0
                }])
                df = pd.concat([df, new_entry], ignore_index=True)
                update_data(df)
                st.success(f"✅ {name} added successfully!")
            else:
                st.error("⚠️ Name is required.")

# --- PAGE 2: CLINICAL & BILLING ---
elif choice == "💊 Clinical & Bill":
    st.markdown("### Clinical & Billing")
    
    pt_list = [""] + df["Name"].tolist()
    pt = st.selectbox("Select Patient", pt_list)
    
    if pt:
        # Get Patient Data
        idx = df[df["Name"] == pt].index[0]
        p_row = df.iloc[idx]
        prev_due = float(p_row.get("Pending Amount", 0) or 0)
        
        if prev_due > 0:
            st.error(f"⚠️ Previous Dues: ₹ {prev_due}")
        
        # --- TABBED INTERFACE ---
        tab1, tab2 = st.tabs(["🩺 Clinical Notes", "💵 Billing"])
        
        with tab1:
            diag = st.multiselect("Diagnosis", COMMON_DX)
            diag_note = st.text_area("Diagnosis Details", ", ".join(diag))
            
            adv = st.multiselect("Procedures Done/Advised", list(TREATMENT_PRICES.keys()))
            adv_note = st.text_area("Treatment Note", ", ".join(adv))
            
            meds = st.multiselect("Medicines", COMMON_MEDS)
            med_note = st.text_area("Rx Note", "\n".join([f"{m} - 1 Tab BD x 3 Days" for m in meds]))
            
            sched = st.checkbox("Schedule Next Visit?", value=True)
            if sched:
                nxt = st.date_input("Next Date", datetime.date.today() + datetime.timedelta(7))
                nxt_str = nxt.strftime("%d-%m-%Y")
            else: nxt_str = "Not Required"

        with tab2:
            st.caption("Select Treatments for Billing")
            
            bill_items = []
            total_bill = 0
            
            # Smart Billing: Auto-select items from Clinical tab
            default_items = [x for x in adv if x in TREATMENT_PRICES]
            selected_tx = st.multiselect("Add to Invoice", list(TREATMENT_PRICES.keys()), default=default_items)
            
            for tx in selected_tx:
                c1, c2 = st.columns([3, 1])
                price = c2.number_input(f"Price: {tx}", value=TREATMENT_PRICES[tx], step=100)
                bill_items.append((tx, price))
                total_bill += price
            
            st.divider()
            grand_total = total_bill + prev_due
            st.write(f"**Current Bill: ₹{total_bill}**")
            st.write(f"**+ Previous Due: ₹{prev_due}**")
            st.markdown(f"### Grand Total: ₹{grand_total}")
            
            paid = st.number_input("Amount Paid Now", value=float(grand_total), step=100.0)
            new_due = grand_total - paid
            
            if new_due > 0: st.warning(f"Remaining Due: ₹{new_due}")
            else: st.success("Fully Paid! ✅")

        # --- ACTIONS ---
        c1, c2 = st.columns(2)
        if c1.button("💾 Save Record"):
            # Update Database
            df.at[idx, "Pending Amount"] = new_due
            df.at[idx, "Last Visit"] = datetime.date.today().strftime("%d-%m-%Y")
            df.at[idx, "Next Appointment"] = nxt_str
            update_data(df)
            st.toast("Record Saved to Cloud!")

            # Generate PDF
            pdf_bytes = create_pdf(pt, p_row['Age'], p_row['Gender'], datetime.date.today().strftime("%d-%m-%Y"), 
                                   nxt_str, diag_note, adv_note, med_note, bill_items, grand_total, paid, new_due)
            
            # Show Download Button
            st.download_button(
                label="📄 Download PDF Prescription",
                data=pdf_bytes,
                file_name=f"{pt}_Rx.pdf",
                mime="application/pdf"
            )

        # WhatsApp Link
        if pt and p_row['Contact']:
            clean_ph = str(p_row['Contact']).replace(" ", "").replace("-", "").replace("+", "")
            if not clean_ph.startswith("91"): clean_ph = "91" + clean_ph
            wa_msg = f"Hello {pt}, Your checkup is done at Sudantam. Total: {grand_total}, Paid: {paid}, Due: {new_due}. Next Visit: {nxt_str}."
            wa_url = f"https://wa.me/{clean_ph}?text={wa_msg.replace(' ', '%20')}"
            st.link_button("💬 Send on WhatsApp", wa_url)

# --- PAGE 3: MANAGE DUES ---
elif choice == "💰 Manage Dues":
    st.markdown("### Pending Dues")
    
    # Ensure numeric
    df["Pending Amount"] = pd.to_numeric(df["Pending Amount"], errors='coerce').fillna(0)
    defaulters = df[df["Pending Amount"] > 0]
    
    if defaulters.empty:
        st.success("🎉 No Pending Dues!")
    else:
        st.dataframe(defaulters[["Name", "Contact", "Pending Amount"]], hide_index=True)
        
        st.divider()
        st.write("**Clear Dues**")
        p_clear = st.selectbox("Select Patient to Clear", defaulters["Name"].unique())
        
        if p_clear:
            idx_d = df[df["Name"] == p_clear].index[0]
            cur_due = df.at[idx_d, "Pending Amount"]
            st.info(f"Current Due: ₹{cur_due}")
            
            pay_amt = st.number_input("Amount Received", max_value=float(cur_due), value=float(cur_due))
            
            if st.button("Update Balance"):
                df.at[idx_d, "Pending Amount"] = cur_due - pay_amt
                update_data(df)
                st.success("Balance Updated!")
                st.rerun()

# --- PAGE 4: RECORDS ---
elif choice == "🔍 Patient Records":
    st.markdown("### 📂 Database")
    q = st.text_input("Search by Name or Phone")
    
    if q:
        mask = df.astype(str).apply(lambda x: x.str.contains(q, case=False, na=False)).any(axis=1)
        res = df[mask]
    else:
        res = df
        
    st.dataframe(res, hide_index=True)
