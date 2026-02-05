import streamlit as st
import pandas as pd
import datetime
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection

# --- APP CONFIGURATION (Mobile Optimized) ---
st.set_page_config(page_title="Sudantam Cloud", page_icon="🦷", layout="wide", initial_sidebar_state="collapsed")

# --- THEME & CSS ---
PRIMARY = "#2C7A6F"
SECONDARY = "#F0F8F5"

st.markdown(f"""
<style>
    /* App-Like Feel */
    #MainMenu, footer, header {{visibility: hidden;}}
    .stApp {{ margin-top: -40px; }}
    [data-testid="stSidebar"] {{ background-color: {SECONDARY}; }}
    
    /* Big Buttons */
    div.stButton > button {{
        width: 100%; background-color: {PRIMARY}; color: white; height: 55px;
        border-radius: 12px; border: none; font-size: 18px; margin-bottom: 8px;
    }}
    div.stButton > button:active {{ transform: scale(0.98); }}
    
    /* Inputs */
    input, select {{ height: 50px !important; font-size: 16px !important; }}
</style>
""", unsafe_allow_html=True)

# --- DATABASE CONNECTION (Google Sheets) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # Read Patients Tab (Worksheet 0)
    try:
        df = conn.read(worksheet="Patients", ttl=0) # ttl=0 means no caching (live data)
        # Ensure columns exist if sheet is empty
        required_cols = ["Patient ID", "Name", "Age", "Gender", "Contact", "Last Visit", "Next Appointment", "Medical History", "Pending Amount"]
        for col in required_cols:
            if col not in df.columns: df[col] = ""
        return df
    except:
        return pd.DataFrame(columns=["Patient ID", "Name", "Age", "Gender", "Contact", "Last Visit", "Next Appointment", "Medical History", "Pending Amount"])

def save_patient(new_entry):
    df = load_data()
    df = pd.concat([df, new_entry], ignore_index=True)
    conn.update(worksheet="Patients", data=df)

def update_data(df):
    conn.update(worksheet="Patients", data=df)

# --- STANDARD LISTS ---
TREATMENT_PRICES = { "Consultation": 200, "X-Ray": 150, "Scaling": 800, "Extraction": 500, "RCT": 3500, "Crown": 3000, "Implant": 15000, "Braces": 25000 }
COMMON_DX = ["Caries", "Abscess", "Gingivitis", "Fracture", "Pulpitis"]
MEDS = ["Augmentin 625", "Metrogyl 400", "Zerodol-SP", "Pan-D"]

# --- SIDEBAR ---
with st.sidebar:
    st.title("🦷 Sudantam")
    menu = ["➕ Add Patient", "💊 Clinical & Bill", "💰 Manage Dues", "🔍 Search"]
    choice = st.radio("Menu", menu, label_visibility="collapsed")
    
    if st.button("🔄 Force Sync"):
        st.cache_data.clear()
        st.rerun()

# --- MAIN APP LOGIC ---
df = load_data()

if choice == "➕ Add Patient":
    st.header("New Patient")
    with st.form("entry"):
        name = st.text_input("Name")
        c1, c2 = st.columns(2)
        age = c1.number_input("Age", 1, 100)
        sex = c2.selectbox("Sex", ["Male", "Female"])
        phone = st.text_input("Phone")
        
        hist = st.multiselect("Medical Hx", ["BP", "Diabetes", "Thyroid", "Allergy"])
        
        # Date & Next Visit
        today = datetime.date.today()
        nxt = st.date_input("Next Visit", today + datetime.timedelta(7))
        sched = st.checkbox("Schedule?", True)
        nxt_str = nxt.strftime("%d-%m-%Y") if sched else "Not Required"
        
        if st.form_submit_button("💾 Save to Cloud"):
            if name:
                new_data = pd.DataFrame([{
                    "Patient ID": len(df)+101, "Name": name, "Age": age, "Gender": sex, "Contact": phone,
                    "Last Visit": today.strftime("%d-%m-%Y"), "Next Appointment": nxt_str,
                    "Medical History": ", ".join(hist), "Pending Amount": 0
                }])
                save_patient(new_data)
                st.success(f"Saved {name} to Google Drive!")
            else:
                st.error("Name Required")

elif choice == "💊 Clinical & Bill":
    st.header("Billing")
    pt = st.selectbox("Patient", [""] + df["Name"].tolist())
    if pt:
        # Find Patient Row
        idx = df[df["Name"] == pt].index[0]
        p_row = df.iloc[idx]
        
        st.info(f"Due: ₹ {p_row['Pending Amount']}")
        
        txs = st.multiselect("Treatments", list(TREATMENT_PRICES.keys()))
        total = sum([TREATMENT_PRICES[t] for t in txs])
        
        st.write(f"**Total: ₹ {total}**")
        paid = st.number_input("Paid", value=total)
        
        if st.button("Update Bill"):
            new_due = (int(p_row['Pending Amount']) + total) - paid
            df.at[idx, "Pending Amount"] = new_due
            df.at[idx, "Last Visit"] = datetime.date.today().strftime("%d-%m-%Y")
            update_data(df)
            st.success("Synced to Cloud!")

elif choice == "💰 Manage Dues":
    st.header("Defaulters")
    # Convert col to numeric just in case
    df["Pending Amount"] = pd.to_numeric(df["Pending Amount"], errors='coerce').fillna(0)
    
    dues = df[df["Pending Amount"] > 0]
    st.dataframe(dues[["Name", "Contact", "Pending Amount"]], hide_index=True)

elif choice == "🔍 Search":
    st.header("Registry")
    q = st.text_input("Search")
    if q:
        mask = df.astype(str).apply(lambda x: x.str.contains(q, case=False, na=False)).any(axis=1)
        st.dataframe(df[mask])
    else:
        st.dataframe(df)