from flask import Flask, request, jsonify, Blueprint
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from models import db, PdfDocument, Transaction, SpendingSummary,  ReceivedSummary, TotalSummary
from datetime import datetime
import os
import re
import fitz
from parser.summary import generate_and_save_summary, generate_and_save_received_summary
from parser.extract import (
    extract_transactions,
    extract_metadata,
    extract_summary_table
)

upload_bp = Blueprint("upload_bp", __name__)


@upload_bp.route('/upload', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "File must be a PDF"}), 400

    # Clean the password
    password = request.form.get('password', '').strip() or None

    try:
        pdf_bytes = file.read()
        filename = secure_filename(file.filename)

        # Check if the file is a valid PDF before saving
        try:
            fitz.open(stream=pdf_bytes, filetype='pdf')
        except Exception:
            return jsonify({"error": "Invalid or corrupted PDF file."}), 400

        #  Save the file metadata to DB
        new_doc = PdfDocument(
            filename=filename,
            content=pdf_bytes,
            uploaded_at=datetime.utcnow()
        )
        db.session.add(new_doc)
        db.session.flush()

        # Extract and save transactions
        transactions_data = extract_transactions(pdf_bytes, password)
        for txn in transactions_data:
            db.session.add(Transaction(
                pdf_id=new_doc.id,
                receipt_no=txn['receipt_no'],
                completion_time=txn['completion_time'],
                details=txn['details'],
                transaction_status=txn['transaction_status'],
                paid_in=txn['paid_in'],
                withdraw=txn['withdrawn'],
                balance=txn['balance']
            ))

        # Extract and save summaries and metadata
        generate_and_save_summary(new_doc.id)
        generate_and_save_received_summary(new_doc.id)
        extract_metadata(new_doc.id, pdf_bytes, password)
        extract_summary_table(new_doc.id, pdf_bytes, password)

        db.session.commit()

        # Fetch summaries for response
        spending = SpendingSummary.query.filter_by(pdf_id=new_doc.id).all()
        receiving = ReceivedSummary.query.filter_by(pdf_id=new_doc.id).all()
        summary_rows = TotalSummary.query.filter_by(pdf_id=new_doc.id).all()
        
        spending_summary = {s.category: s.total_spent for s in spending}
        received_summary = {r.category: r.total_received for r in receiving}
        total_summary = [
            {
                "transaction_type": s.transaction_type,
                "total_paid_in": s.total_paid_in,
                "total_paid_out": s.total_paid_out
            }
            for s in summary_rows
        ]

        return jsonify({
            "id": new_doc.id,
            "filename": new_doc.filename,
            "uploaded_at": new_doc.uploaded_at.isoformat(),
            "success": "Uploaded and analyzed successfully",
            "transactions": transactions_data,
            "spending_summary": spending_summary,
            "received_summary": received_summary,
            "total_summary": total_summary
        }), 201

    except Exception as e:
        db.session.rollback()
        print("ERROR during upload:", e)
        return jsonify({"error": str(e)}), 500
