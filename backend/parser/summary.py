from flask import Flask, request, jsonify, Blueprint
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from models import db, PdfDocument, Transaction, SpendingSummary, ReceivedSummary
from datetime import datetime
import os
from collections import defaultdict

summary_bp = Blueprint("summary_bp", __name__)


def generate_and_save_summary(pdf_id):
    transactions = Transaction.query.filter_by(pdf_id=pdf_id).all()
    
    spending_summary = defaultdict(lambda: {'total': 0.0, 'count': 0})

    for txn in transactions:
        if not txn.withdraw or txn.withdraw == 0.0:
            continue  # Skip transactions with no withdrawal

        detail = txn.details.strip().replace('\n', ' ')
        spending_summary[detail]['total'] += txn.withdraw
        spending_summary[detail]['count'] += 1

    for detail, values in spending_summary.items():
        entry = SpendingSummary(
            pdf_id=pdf_id,
            category=detail,
            total_spent=round(values['total'], 2),
            transaction_count=values['count']
        )
        db.session.add(entry)

    db.session.commit()



def generate_and_save_received_summary(pdf_id):
    transactions = Transaction.query.filter_by(pdf_id=pdf_id).all()

    received_summary = defaultdict(lambda: {'total': 0.0, 'count': 0})

    for txn in transactions:
        if not txn.paid_in or txn.paid_in == 0.0:
            continue  # Skip transactions with no incoming amount

        detail = txn.details.strip().replace('\n', ' ')
        received_summary[detail]['total'] += txn.paid_in
        received_summary[detail]['count'] += 1

    for detail, values in received_summary.items():
        entry = ReceivedSummary(
            pdf_id=pdf_id,
            category=detail,
            total_received=round(values['total'], 2),
            transaction_count=values['count']
        )
        db.session.add(entry)

    db.session.commit()
