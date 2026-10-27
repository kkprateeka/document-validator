from fastapi import FastAPI, UploadFile, File
from typing import List
import time
from models.rule import Rule
from services.rule_engine import execute_rules
from services.pdf_praser import extract_pdf_text,extract_pdf_content
from services.word_praser import parse_word
from services.excel_praser import load_excel
import shutil
import traceback
from database import get_user_role
from fastapi import Form
from pydantic import BaseModel
from database import get_default_word, set_default_word
import os
from fastapi.middleware.cors import CORSMiddleware
os.makedirs("temp", exist_ok=True)
os.makedirs("storage", exist_ok=True)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "Document Validation Service Running"}

class LoginRequest(BaseModel):
    emp_id: str

@app.post("/login")
def login(data: LoginRequest):
    role = get_user_role(data.emp_id)
    if not role:
        return {"error": "Invalid Employee ID"}

    return {
    "emp_id": data.emp_id,
    "role": role
}
@app.post("/admin/set-word")
async def set_word(
    emp_id: str = Form(...),
    word: UploadFile = File(...)
):
    
    role = get_user_role(emp_id)

    if role != "admin":
        return {"error": "Unauthorized"}

    filename = os.path.basename(word.filename)
    word_path = f"storage/default_{int(time.time())}_{filename}"

    with open(word_path, "wb") as buffer:
        shutil.copyfileobj(word.file, buffer)

    success = set_default_word(word_path)

    if success:
        return {"message": "Default Word updated"}
    else:
        return {"error": "Failed to update"}
    
@app.post("/process")
async def process_files(
    emp_id: str = Form(...),
    pdf: UploadFile = File(...),
    excel: UploadFile = File(...),
    word: UploadFile = File(None)   # optional
):
    try:
        print("🔥 Python API HIT")

        # ✅ CHECK ROLE
        role = get_user_role(emp_id)

        if not role:
            return {"error": "Invalid Employee ID"}

        print(f"👤 Role: {role}")

        # ✅ FILE PATHS
        pdf_path = f"temp/{int(time.time())}_{pdf.filename}"
        excel_path = f"temp/{int(time.time())}_{excel.filename}"
        word_path = None

        if not pdf.filename.endswith(".pdf"):
            return {"error": "Invalid PDF file"}
        if not excel.filename.endswith((".xlsx", ".xls")):
            return {"error": "Invalid Excel file"}

        # Save PDF
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(pdf.file, buffer)

        # Save Excel
        with open(excel_path, "wb") as buffer:
            shutil.copyfileobj(excel.file, buffer)

        if role == "admin":
            if word:
                if not word.filename.endswith(".docx"):
                    return {"error": "Invalid Word file (.docx only)"}
                word_path = f"temp/{int(time.time())}_{word.filename}"
                with open(word_path, "wb") as buffer:
                    shutil.copyfileobj(word.file, buffer)
            else:
                # fallback to default
                word_path = get_default_word()
                if not word_path or not os.path.exists(word_path):
                    return {"error": "Default Word file not found on server"}
        else:
            if word:
                return {"error": "Employees cannot upload Word file"}
            word_path = get_default_word()
            print("👤 EMPLOYEE USING WORD:", word_path)
            if not word_path or not os.path.exists(word_path):
                print("❌ FILE NOT FOUND:", word_path)
                return {"error": "No default Word file set by admin"}

        print("📄 Files saved")

        # Extract
        rules = parse_word(word_path)
        print("✅ Word parsed")

        pdf_data = extract_pdf_content(pdf_path)
        print("✅ PDF processed")

        excel_df = load_excel(excel_path)
        print("✅ Excel loaded")

        # Execute rules
        results = execute_rules(
            rules,
            pdf_data["text"],
            excel_df,
            pdf_path,
            pdf_data["tables"],
            pdf_data["meta"]
        )

        print("✅ Rules executed")

        return {
            "role": role,
            "results": results,
            "pdf_meta": pdf_data["meta"]
        }
            

    except Exception as e:
        print("❌ ERROR OCCURRED:")
        traceback.print_exc()

        return {
            "error": str(e)
        }
    finally:
        for path in [pdf_path, excel_path, word_path]:
            try:
                if path and "temp/" in path and os.path.exists(path):
                    os.remove(path)
            except:
                pass

    