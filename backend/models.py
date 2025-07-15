from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from datetime import datetime

metadata = MetaData()
db = SQLAlchemy(metadata=metadata)

# PDF Document model
class PdfDocument(db.Model):
    __tablename__ = 'pdf_document'  
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String, nullable=False)
    content = db.Column(db.LargeBinary, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

# M-PESA Transaction model
class Transaction(db.Model):
    __tablename__ = 'transaction'
    id = db.Column(db.Integer, primary_key=True)
    pdf_id = db.Column(db.Integer, db.ForeignKey('pdf_document.id'), nullable=False, index=True)

    receipt_no = db.Column(db.String, nullable=False)
    completion_time = db.Column(db.String, nullable=False)
    details = db.Column(db.String, nullable=False)
    transaction_status = db.Column(db.String, nullable=False)
    paid_in = db.Column(db.Float, nullable=True)
    withdraw = db.Column(db.Float, nullable=True)
    balance = db.Column(db.Float, nullable=True)

    document = db.relationship("PdfDocument", backref="transactions")

    def __repr__(self):
       return f"<Transaction {self.receipt_no} - {self.details}>"


# Spending Summary model
class SpendingSummary(db.Model):
    __tablename__ = 'spending_summary'
    id = db.Column(db.Integer, primary_key=True)
    pdf_id = db.Column(db.Integer, db.ForeignKey('pdf_document.id'), nullable=False, index=True)
    category = db.Column(db.String(255), nullable=False)
    total_spent = db.Column(db.Float, nullable=False)
    transaction_count = db.Column(db.Integer, default=0)

    pdf = db.relationship('PdfDocument', backref=db.backref('spending_summaries', lazy=True))

# Received Summary model
class ReceivedSummary(db.Model):
    __tablename__ = 'received_summary'
    id = db.Column(db.Integer, primary_key=True)
    pdf_id = db.Column(db.Integer, db.ForeignKey('pdf_document.id'), nullable=False, index=True)
    category = db.Column(db.String(255), nullable=False)
    total_received = db.Column(db.Float, nullable=False)
    transaction_count = db.Column(db.Integer, default=0)

    pdf = db.relationship('PdfDocument', backref=db.backref('received_summaries', lazy=True))

# Total Summary model
class TotalSummary(db.Model):
    __tablename__ = 'total_summary'
    id = db.Column(db.Integer, primary_key=True)
    pdf_id = db.Column(db.Integer, db.ForeignKey('pdf_document.id'), nullable=False, index=True)
    transaction_type = db.Column(db.String,nullable=False)
    total_paid_in = db.Column(db.String, nullable=False)
    total_paid_out = db.Column(db.String, nullable=False)

    document = db.relationship("PdfDocument", backref="total_summaries")

# Customer Details model
class CustomerDetails(db.Model):
    __tablename__ = 'customer_details'
    id = db.Column(db.Integer, primary_key=True)
    pdf_id = db.Column(db.Integer, db.ForeignKey('pdf_document.id'), nullable=False, index=True)
    customer_name = db.Column(db.String, nullable=False)
    mobile_number = db.Column(db.String, nullable=False)
    email_address = db.Column(db.String, nullable=False)
    statement_period = db.Column(db.String, nullable=False)
    request_date = db.Column(db.String, nullable=False)
    statement_duration_months = db.Column(db.Integer, nullable=False)


    document = db.relationship("PdfDocument", backref="customer_details")

class DocumentExtras(db.Model):
    __tablename__ = 'document_extras'
    id = db.Column(db.Integer, primary_key=True)
    pdf_id = db.Column(db.Integer, db.ForeignKey('pdf_document.id'), nullable=False, index=True)
    note_type = db.Column(db.String(100), nullable=False)  # e.g. "disclaimer", "footer", "custom_note"
    content = db.Column(db.Text, nullable=False)

    document = db.relationship("PdfDocument", backref="extras")
