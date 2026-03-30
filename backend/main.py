from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
import shutil, os, json, pandas as pd, pdfplumber, re
from rapidfuzz import fuzz
from dotenv import load_dotenv
import google.generativeai as genai
from fastapi.middleware.cors import CORSMiddleware

# ------------------ CONFIG ------------------
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.5-flash")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads", exist_ok=True)

# ------------------ LOAD MASTER ------------------
product_df = pd.read_excel("data/SAP Item Master 24.xlsx")[["Product","Product Description"]]

customer_df = pd.read_excel("data/Customers Master.xlsx")[
    ["Name 1", "Business Partner ID", "Street", "City", "Postal Code"]
].fillna("")

# ------------------ CLEANING ------------------
def clean_text(text):
    text = str(text).lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

customer_df["clean_name"] = customer_df["Name 1"].apply(clean_text)
customer_df["clean_street"] = customer_df["Street"].apply(clean_text)
customer_df["clean_city"] = customer_df["City"].apply(clean_text)
customer_df["postal"] = customer_df["Postal Code"].astype(str).str.extract(r'(\d{6})')[0]

# ------------------ QUANTITY EXTRACT (FIXED) ------------------
def extract_qty(text):
    text = str(text).lower().replace(" ", "")
    match = re.search(r'(\d+(?:\.\d+)?)(ml|ltr|l|gm|g)', text)

    if match:
        val = float(match.group(1))
        unit = match.group(2)

        if unit in ["ltr", "l"]:
            val *= 1000

        return int(val)
    return None

# ------------------ PRODUCT MATCH (STRICT) ------------------
def find_product_id(desc):
    desc_clean = clean_text(desc)
    po_qty = extract_qty(desc)

    strict_matches = []
    close_matches = []

    for _, row in product_df.iterrows():
        prod_desc = str(row["Product Description"])
        prod_clean = clean_text(prod_desc)
        prod_qty = extract_qty(prod_desc)

        # ❌ skip if qty missing
        if po_qty is None or prod_qty is None:
            continue

        score = fuzz.token_set_ratio(desc_clean, prod_clean)

        # ✅ exact match
        if po_qty == prod_qty:
            strict_matches.append((score, row))

        # ✅ small tolerance
        elif abs(po_qty - prod_qty) <= 50:
            close_matches.append((score, row))

        # ❌ ignore wrong size completely
        else:
            continue

    if strict_matches:
        strict_matches.sort(key=lambda x: x[0], reverse=True)
        best = strict_matches[0][1]
        print("✅ STRICT:", desc, "→", best["Product Description"])
        return int(best["Product"])

    if close_matches:
        close_matches.sort(key=lambda x: x[0], reverse=True)
        best = close_matches[0][1]
        print("🟡 CLOSE:", desc, "→", best["Product Description"])
        return int(best["Product"])

    print("❌ NOT FOUND:", desc)
    return "NOT_FOUND"

# ------------------ PDF TEXT ------------------
def extract_text(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for p in pdf.pages:
            t = p.extract_text()
            if t:
                text += t
    return text

# ------------------ GEMINI ------------------
def extract_with_gemini(text):
    prompt = f"""
Extract purchase order data in STRICT JSON.

Format:
{{
  "po_number": "",
  "customer_name": "",
  "shipping_address": "",
  "postal_code": "",
  "items": [
    {{"description": "", "quantity": 0}}
  ]
}}

Text:
{text}
"""
    res = model.generate_content(prompt)
    return res.text

# ------------------ CLEAN JSON ------------------
def clean_json(text):
    try:
        text = re.sub(r"```json|```", "", text)
        text = text[text.find("{"):text.rfind("}")+1]
        return json.loads(text)
    except Exception as e:
        print("JSON ERROR:", e)
        return None

# ------------------ CUSTOMER MATCH ------------------
def find_customer_id(po_name, po_address, po_postal):

    po_name = clean_text(po_name)
    po_address = clean_text(po_address)

    po_postal_match = re.search(r'\d{6}', str(po_postal))
    po_postal = po_postal_match.group() if po_postal_match else ""

    best_score = 0
    best_customer = None

    for _, row in customer_df.iterrows():

        # ✅ strict postal filter
        if po_postal and row["postal"] != po_postal:
            continue

        name_score = fuzz.token_set_ratio(po_name, row["clean_name"])
        street_score = fuzz.token_set_ratio(po_address, row["clean_street"])
        city_score = fuzz.token_set_ratio(po_address, row["clean_city"])

        score = (
            name_score * 0.6 +
            street_score * 0.3 +
            city_score * 0.1
        )

        if score > best_score:
            best_score = score
            best_customer = row

    print("BEST CUSTOMER SCORE:", best_score)

    if best_customer is not None:
        return best_customer["Business Partner ID"]

    return "NOT_FOUND"

# ------------------ ROOT ------------------
@app.get("/")
def root():
    return {
        "message": (
            "🐉🔥 SAP DRAGON BACKEND 🔥🐉\n\n"
            "════════════════════════════\n"
            "  SYSTEM STATUS : ACTIVE 🟢\n"
            "  PO ENGINE     : RUNNING 🚀\n"
            "  AI MATCHING   : ENABLED 🤖\n"
            "════════════════════════════"
        )
    }

# ------------------ MAIN API ------------------
@app.post("/upload_multiple_pos")
async def upload_multiple_pos(files: list[UploadFile] = File(...)):

    all_rows = []
    po_counter = {}
    current_so = 1
    temp_paths = []

    try:
        for file in files:

            path = f"uploads/{file.filename}"
            temp_paths.append(path)

            with open(path, "wb") as f:
                shutil.copyfileobj(file.file, f)

            text = extract_text(path)[:6000]

            ai_raw = extract_with_gemini(text)
            parsed = clean_json(ai_raw)

            if not parsed:
                continue

            po_number = parsed.get("po_number", "UNKNOWN")
            customer_name = parsed.get("customer_name", "")
            shipping_address = parsed.get("shipping_address", "")
            postal_code = parsed.get("postal_code", "")

            customer_id = find_customer_id(
                customer_name,
                shipping_address,
                postal_code
            )

            print("MATCHED CUSTOMER:", customer_id)

            for idx, item in enumerate(parsed.get("items", []), start=1):

                if po_number not in po_counter:
                    po_counter[po_number] = current_so
                    current_so += 1

                all_rows.append({
                    "Sales Order": po_counter[po_number],
                    "Order Type": "OR",
                    "Sales Organization": "1000",
                    "Distribution Channel": "04",
                    "Division": "00",
                    "Sold-to Party": customer_id,
                    "Ship-to Part" :"",
                    "Customer Ref": po_number,
                    "Requested Delevery Date" :"",
                    "Pricing Date" :"",
                    "shipping Conditions" : "",
                    "Temp id": idx,
                    "Material": find_product_id(item["description"]),
                    "Customer Material" : "",
                    "GSTIN (EAN/UPC)" :"",
                    "Quantity": item["quantity"],
                    "Requested Qty Unit" :"",
                    "Item Category":"",
                    "Plant": "10CD",
                    
                })

        df = pd.DataFrame(all_rows)
        df = df.sort_values(["Sales Order", "Temp id"])
        df.fillna("", inplace=True)

        out = "uploads/output.xlsx"
        df.to_excel(out, index=False)

        return FileResponse(out)

    finally:
        for p in temp_paths:
            if os.path.exists(p):
                os.remove(p)