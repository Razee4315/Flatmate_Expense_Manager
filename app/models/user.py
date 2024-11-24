from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_flat_leader = db.Column(db.Boolean, default=False)
    flat_id = db.Column(db.Integer, db.ForeignKey('flat.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    expenses_created = db.relationship('Expense', backref='creator', lazy=True)
    expense_shares = db.relationship('ExpenseShare', backref='shared_user', lazy=True)
    payments_made = db.relationship('Payment', 
                                  foreign_keys='Payment.payer_id',
                                  backref=db.backref('payer', lazy=True),
                                  lazy=True)
    payments_received = db.relationship('Payment', 
                                      foreign_keys='Payment.recipient_id',
                                      backref=db.backref('recipient', lazy=True),
                                      lazy=True)
    grocery_items_added = db.relationship('GroceryItem', backref='added_by', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Flat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    members = db.relationship('User', backref='flat', lazy=True)
    expenses = db.relationship('Expense', backref='flat', lazy=True)
    grocery_items = db.relationship('GroceryItem', backref='flat', lazy=True)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    is_shared = db.Column(db.Boolean, default=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    flat_id = db.Column(db.Integer, db.ForeignKey('flat.id'), nullable=False)
    
    # Relationships
    shares = db.relationship('ExpenseShare', backref='expense', lazy=True, cascade='all, delete-orphan')

class ExpenseShare(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey('expense.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    share_amount = db.Column(db.Float, nullable=False)
    is_paid = db.Column(db.Boolean, default=False)
    
    # Relationships
    payments = db.relationship('Payment', backref='expense_share', lazy=True)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    payer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    expense_share_id = db.Column(db.Integer, db.ForeignKey('expense_share.id'))

class GroceryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.String(50))
    is_bought = db.Column(db.Boolean, default=False)
    added_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    flat_id = db.Column(db.Integer, db.ForeignKey('flat.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
