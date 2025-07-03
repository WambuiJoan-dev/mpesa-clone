from flask import Flask, request, jsonify, Blueprint
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from models import db, PdfDocument, Transaction, CustomerDetails, DocumentExtras, TotalSummary
from datetime import datetime
import os
from collections import defaultdict
from sqlalchemy import func
import re
from models import db, CustomerDetails, DocumentExtras, TotalSummary, Transaction
import fitz
from collections import defaultdict

extract_bp = Blueprint("extract_bp", __name__)




def calculate_duration_months(period_str):
    if " - " in period_str:
        parts = [p.strip() for p in period_str.split(" - ")]
        if len(parts) == 2:
            try:
                from_date = datetime.strptime(parts[0], "%d %b %Y")
                to_date = datetime.strptime(parts[1], "%d %b %Y")

                months = (to_date.year - from_date.year) * 12 + (to_date.month - from_date.month)
                if to_date.day < from_date.day:
                    months -= 1

                return max(months, 0)
            except ValueError as e:
                raise ValueError(f"Failed to parse dates in period: {period_str} — {e}")
    return 0

def extract_metadata(pdf_id, pdf_bytes, password=None):
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    if doc.is_encrypted:
        if not password or not doc.authenticate(password):
            raise Exception("PDF decryption failed")

    first_page_text = doc[0].get_text()
    last_page_text = doc[-1].get_text()

    name_match = re.search(r"Customer Name\s*:\s*(.*)", first_page_text)
    phone_match = re.search(r"Mobile Number\s*:\s*(.*)", first_page_text)
    email_match = re.search(r"Email Address\s*:\s*(.*)", first_page_text)
    period_match = re.search(r"Statement Period\s*:\s*(.*)", first_page_text)
    date_match = re.search(r"Request Date\s*:\s*(.*)", first_page_text)

    # Extract raw values
    period_str = period_match.group(1).strip() if period_match else "Unknown"
    request_date_str = date_match.group(1).strip() if date_match else "Unknown"

    # Compute duration in months
    duration_months = calculate_duration_months(period_str) if period_str != "Unknown" else None

    # Save customer details
    db.session.add(CustomerDetails(
        pdf_id=pdf_id,
        customer_name=name_match.group(1).strip() if name_match else "Unknown",
        mobile_number=phone_match.group(1).strip() if phone_match else "Unknown",
        email_address=email_match.group(1).strip() if email_match else "Unknown",
        statement_period=period_str,
        request_date=request_date_str,
        statement_duration_months=duration_months
    ))

    # Save footer notes
    for line in last_page_text.splitlines():
        if "verification code" in line.lower() or "disclaimer" in line.lower():
            db.session.add(DocumentExtras(
                pdf_id=pdf_id,
                note_type="footer",
                content=line.strip()
            ))

    db.session.commit()



def extract_summary_table(pdf_id, pdf_bytes, password=None):
    

    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    if doc.is_encrypted:
        if not password or not doc.authenticate(password):
            raise Exception("PDF decryption failed")

    page = doc[0]  # Only check page 1
    blocks = page.get_text("blocks")
    summary_rows = []

    header_y = None
    detailed_y = None

    # Step 1: Find the header block
    for block in blocks:
        text = block[4].lower()
        if "transaction type" in text and "paid in" in text and "paid out" in text:
            header_y = block[1]
            # print("[FOUND] Summary header at y =", header_y)
            break

    if header_y is None:
        print("[WARNING] Summary header not found on page 1")
        return

    # Step 2: Find the DETAILED STATEMENT block (to define end boundary)
    for block in blocks:
        if "detailed statement" in block[4].lower():
            detailed_y = block[1]
            # print("[FOUND] DETAILED STATEMENT at y =", detailed_y)
            break

    # Step 3: Extract rows between header_y and detailed_y
    for block in blocks:
        y0 = block[1]
        text = block[4].strip()

        if y0 > header_y and (detailed_y is None or y0 < detailed_y):
            numbers = re.findall(r"\d[\d,]*\.\d{2}", text)
            if len(numbers) >= 2:
                summary_rows.append(text)
                # print(f"[ROW BLOCK] {text}")

    # Step 4: Save clean rows
    inserted_any = False
    for line in summary_rows:
        numbers = re.findall(r"\d[\d,]*\.\d{2}", line)
        if len(numbers) < 2:
            continue

        transaction_type = re.sub(r"\d[\d,]*\.\d{2}", "", line)
        transaction_type = re.sub(r"\s+", " ", transaction_type.replace(":", "")).strip()
        paid_in = numbers[0]
        paid_out = numbers[1]

        # print(f"[INSERT] {transaction_type} | IN: {paid_in} | OUT: {paid_out}")

        db.session.add(TotalSummary(
            pdf_id=pdf_id,
            transaction_type=transaction_type,
            total_paid_in=paid_in,
            total_paid_out=paid_out
        ))
        inserted_any = True

    if inserted_any:
        db.session.commit()
    else:
        print("[WARNING] No TotalSummary rows inserted.")



def clean_amount(value):
    try:
        if value in ["", "-", None]:
            return 0.0
        return float(value.replace(",", "").strip())
    except Exception:
        return 0.0

def extract_transactions(pdf_bytes, password=None):
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')

    if doc.is_encrypted:
        if not password or not doc.authenticate(password):
            raise Exception("PDF decryption failed")

    transactions = []
    status_keywords = r"^(Completed|Failed|Pending)$"
    receipt_no_pattern = r"^[A-Z0-9]{10,}$"  # Covers receipt numbers like TFP39YYAD3, not just TF

    for page in doc:
        lines = page.get_text().split('\n')
        i = 0
        while i < len(lines):
            # Match receipt number
            if re.match(receipt_no_pattern, lines[i].strip()):
                receipt_no = lines[i].strip()
                i += 1
                if i >= len(lines): break

                completion_time = lines[i].strip()
                i += 1
                if i >= len(lines): break

                # Look ahead for transaction status
                details_lines = []
                status_line_index = None
                for j in range(i, min(i + 7, len(lines))):
                    if re.match(status_keywords, lines[j].strip()):
                        status_line_index = j
                        break

                if status_line_index is None:
                    i += 1
                    continue

                details_lines = lines[i:status_line_index]
                details = "\n".join([d.strip() for d in details_lines])
                transaction_status = lines[status_line_index].strip()
                i = status_line_index + 1

                # Extract amount and balance
                monetary_fields = []
                while i < len(lines) and len(monetary_fields) < 2:
                    line = lines[i].strip()
                    if re.match(r'^-?[\d,]+(\.\d{1,2})?$', line) or line in ["", "-"]:
                        monetary_fields.append(line)
                        i += 1
                    else:
                        break

                amount = clean_amount(monetary_fields[0]) if len(monetary_fields) > 0 else 0.0
                balance = clean_amount(monetary_fields[1]) if len(monetary_fields) > 1 else 0.0

                paid_in = amount if amount > 0 else 0.0
                withdrawn = -amount if amount < 0 else 0.0
                
                transactions.append({
                    "receipt_no": receipt_no,
                    "completion_time": completion_time,
                    "details": details,
                    "transaction_status": transaction_status,
                    "paid_in": paid_in,
                    "withdrawn": withdrawn,
                    "balance": balance
                })

            else:
                i += 1

    return transactions
