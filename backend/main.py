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

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "*",  # allow all origins (optional)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads", exist_ok=True)

# ------------------ LOAD MASTER ------------------
product_df = pd.read_excel("data/SAP Item Master 24.xlsx")[["Product","Product Description"]].reset_index(drop=True)
product_df["clean_tally"] = product_df["Product Description"].apply(
    lambda x: re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9\s]', ' ', str(x).lower())).strip()
)

# ------------------ HELPERS ------------------
def clean_text(text):
    text = str(text).lower().replace("akshayakalpa", "").replace("pack", "").replace("pouch", "")
    text = re.sub(r"\(.*?\)", "", text)
    return re.sub(r"\s+", " ", text).strip()

def extract_qty(text):
    match = re.search(r'(\d+)\s*(ml|ltr|gm|g)', text.lower())
    if match:
        val, unit = int(match.group(1)), match.group(2)
        if unit == "ltr":
            val *= 1000
        return val
    return None

def find_product_id(po_description):
    po_clean = clean_text(po_description)
    po_qty = extract_qty(po_description)
    best_match = None
    best_score = 0
    exact_qty_matches = []

    for i, row in product_df.iterrows():
        tally_clean = clean_text(row["Product Description"])
        tally_qty = extract_qty(row["Product Description"])
        score = fuzz.token_set_ratio(po_clean, tally_clean)
        if po_qty and tally_qty:
            if po_qty == tally_qty:
                score += 20
                exact_qty_matches.append((i, score))
            elif abs(po_qty - tally_qty) <= 50:
                score += 10
        if score > best_score:
            best_score = score
            best_match = i

    if exact_qty_matches:
        best_match, best_score = sorted(exact_qty_matches, key=lambda x: x[1], reverse=True)[0]

    if best_match is not None and best_score > 60:
        return {
            "product_id": int(product_df.iloc[best_match]["Product"]),
            "matched_name": product_df.iloc[best_match]["Product Description"],
            "score": float(best_score)
        }
    return None

def map_products(items):
    mapped = []
    for item in items:
        desc = item.get("description", "")
        qty = int(item.get("quantity", 0))
        result = find_product_id(desc)
        mapped.append({
            "description": desc,
            "quantity": qty,
            "product_id": result["product_id"] if result else "NOT_FOUND",
            "matched_name": result["matched_name"] if result else None,
            "score": result["score"] if result else None
        })
    return mapped

def extract_text(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    return text

def extract_with_gemini(text):
    prompt = f"""
Extract purchase order data and return ONLY valid JSON.
if you find any description includes ltr then treat as 1000ml

Format:
{{
  "po_number": "",
  "customer_name": "",
  "items": [
    {{"description": "", "quantity": 0}}
  ]
}}

Text:
{text}
"""
    response = model.generate_content(prompt)
    return response.text

def clean_json(response_text):
    try:
        cleaned = re.sub(r"```json|```", "", response_text).strip()
        return json.loads(cleaned)
    except:
        return None

# ------------------- MULTIPLE PO ROUTE -------------------
@app.post("/upload_multiple_pos")
async def upload_multiple_pos(files: list[UploadFile] = File(...)):
    temp_paths = []
    all_rows = []
    print("working")

    po_counter = {}
    current_sales_order = 1

    try:
        for file in files:
            file_path = f"uploads/{file.filename}"
            temp_paths.append(file_path)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            text = extract_text(file_path)[:6000]
            ai_output = extract_with_gemini(text)
            parsed = clean_json(ai_output)
            if not parsed or "items" not in parsed:
                continue

            mapped_items = map_products(parsed["items"])

            

            # Prepare rows for Excel
            for idx, item in enumerate(mapped_items, start=1):
                po_number = parsed.get("po_number", "UNKNOWN")
                print(po_number)
                if po_number not in po_counter:
                    po_counter[po_number] = current_sales_order
                    current_sales_order += 1
                sales_order_number = po_counter[po_number]    

                all_rows.append({
                    "Sales Order": sales_order_number,
                    "Order Type": "OR",
                    "Sales Organization" : "1000",
                    "Distribution Channel": "04",
                    "Division": "00",
                    "Sold-to Party": parsed.get("customer_name"),
                    "Ship-to Party": "",
                    "Customer Ref": parsed.get("po_number"),
                    "Requested Delevery Date" : "",
                    "Priceing Date" :"",
                    "Shiping Condition" :"",
                    "Temp id": idx,
                    "Material": item["product_id"],
                    "Customer Meterial" :"",
                    "GTIN" :"",
                    "Quantity": item["quantity"],
                    "Requested Qnt Unit" :"",
                    "Item Catogery" :"",
                    "Plant": "10CD"
                })

        # Create Excel
        export_path = "uploads/SAP_PO_Export.xlsx"
        df = pd.DataFrame(all_rows)
        df.to_excel(export_path, index=False)

        return FileResponse(
            export_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="SAP_PO_Export.xlsx"
        )

    finally:
        # Clean temp files
        for path in temp_paths:
            if os.path.exists(path):
                os.remove(path)