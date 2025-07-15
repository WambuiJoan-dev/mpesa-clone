from flask import Flask, request, jsonify, Blueprint
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from models import db, PdfDocument, Transaction, SpendingSummary, ReceivedSummary, CustomerDetails, TotalSummary
from datetime import datetime
import os
from collections import defaultdict

fetching_bp = Blueprint("fetching_bp", __name__)


@fetching_bp.route("/fetching/<int:pdf_id>", methods=["GET"])
def get_customer_details(pdf_id):
    customer = CustomerDetails.query.filter_by(pdf_id=pdf_id).first()

    if not customer:
        return jsonify({"error":"Customer details not found"})

    return jsonify({
        "pdf_id": customer.pdf_id,
        "customer_name": customer.customer_name,
        "mobile_number": customer.mobile_number,
        "email_address": customer.email_address,
        "statement_period": customer.statement_period,
        "request_date": customer.request_date,
        "statement_duration_months": customer.statement_duration_months
    }), 200



@fetching_bp.route("/summary/spending/<int:pdf_id>", methods=["GET"])
def summary_spending(pdf_id):
    spending = SpendingSummary.query.filter_by(pdf_id=pdf_id).all()

    if not spending:
        return jsonify({"error": "No spending summary found for the given PDF ID"}), 404

    return jsonify([
        {
            'pdf_id': entry.pdf_id,
            'category': entry.category,
            'total_spent': entry.total_spent,
            'transaction_count': entry.transaction_count
        }
        for entry in spending
    ])


@fetching_bp.route("/summary/received/<int:pdf_id>", methods=["GET"])
def summary_received(pdf_id):
    received = ReceivedSummary.query.filter_by(pdf_id=pdf_id).all()

    if not received:
        return jsonify({"error": "No received summary found for the given PDF ID"}), 404

    return jsonify([
        {
            'pdf_id': entry.pdf_id,
            'category': entry.category,
            'total_received': entry.total_received,
            'transaction_count': entry.transaction_count
        }
        for entry in received
    ])


@fetching_bp.route("/documents", methods=["GET"])
def list_uploaded_documents():
    documents = PdfDocument.query.order_by(PdfDocument.uploaded_at.desc()).all()

    result = [
        {
            "id": doc.id,
            "filename": doc.filename,
            "uploaded_at": doc.uploaded_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for doc in documents
    ]

    return jsonify(result)


@fetching_bp.route("/totalsummary/<int:pdf_id>", methods=["GET"])
def total_summary(pdf_id):
    total = TotalSummary.query.filter_by(pdf_id=pdf_id).all()

    if not total:
        return jsonify({"error": "No Total Summary found for the given PDF ID"}), 404

    return jsonify([
        {
            'pdf_id': total_money.pdf_id,
            'transaction_type': total_money.transaction_type,
            'total_paid_in': total_money.total_paid_in,
            'total_paid_out': total_money.total_paid_out
        }
        for total_money in total
    ])

