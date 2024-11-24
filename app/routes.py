from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models.user import Expense, ExpenseShare, GroceryItem, Payment, User, Flat
from app import db
from datetime import datetime
from sqlalchemy import func
from calendar import monthrange
import os
from werkzeug.utils import secure_filename
from flask import current_app

main = Blueprint('main', __name__)

@main.route('/')
@main.route('/dashboard')
@login_required
def dashboard():
    if not current_user.flat:
        flash('Please join or create a flat first.', 'warning')
        return redirect(url_for('main.manage_flat'))

    # Get all expenses for the flat
    expenses = Expense.query.filter_by(flat_id=current_user.flat_id).order_by(Expense.date.desc()).all()
    
    # Calculate total expenses and personal share
    total_flat_expenses = sum(e.amount for e in expenses if e.is_shared)
    personal_expenses = sum(e.amount for e in expenses if not e.is_shared and e.creator_id == current_user.id)
    
    # Get monthly expense data for charts
    from datetime import datetime, timedelta
    import calendar
    
    # Last 6 months of data
    today = datetime.today()
    months_data = []
    categories_data = {}
    user_expenses = {user.id: 0 for user in User.query.filter_by(flat_id=current_user.flat_id)}
    
    for i in range(5, -1, -1):
        date = today - timedelta(days=30*i)
        month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if i > 0:
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
        else:
            month_end = today
            
        month_expenses = Expense.query.filter(
            Expense.flat_id == current_user.flat_id,
            Expense.date >= month_start,
            Expense.date <= month_end
        ).all()
        
        month_total = sum(e.amount for e in month_expenses)
        months_data.append({
            'month': calendar.month_name[date.month],
            'amount': month_total
        })
        
        # Aggregate category data
        for expense in month_expenses:
            if expense.category not in categories_data:
                categories_data[expense.category] = 0
            categories_data[expense.category] += expense.amount
            
            # Track expenses by user
            user_expenses[expense.creator_id] += expense.amount
    
    # Calculate unpaid balances
    unpaid_shares = ExpenseShare.query.join(Expense)\
        .filter(Expense.flat_id == current_user.flat_id)\
        .filter(ExpenseShare.is_paid == False).all()
    
    my_unpaid = sum(share.share_amount for share in unpaid_shares if share.user_id == current_user.id)
    owed_to_me = sum(share.share_amount for share in unpaid_shares 
                    if share.expense.creator_id == current_user.id and share.user_id != current_user.id)
    
    # Get recent activity
    recent_activities = []
    
    # Add expenses to activity
    for expense in expenses[:10]:  # Last 10 expenses
        user = User.query.get(expense.creator_id)
        recent_activities.append({
            'type': 'expense',
            'date': expense.date,
            'user': {
                'id': user.id,
                'username': user.username
            },
            'description': expense.description,
            'amount': expense.amount,
            'category': expense.category,
            'id': expense.id
        })
    
    # Add recent payments to activity
    recent_payments = Payment.query.filter(
        (Payment.payer_id == current_user.id) | (Payment.recipient_id == current_user.id)
    ).order_by(Payment.date.desc()).limit(10).all()
    
    for payment in recent_payments:
        recent_activities.append({
            'type': 'payment',
            'date': payment.date,
            'payer': User.query.get(payment.payer_id),
            'recipient': User.query.get(payment.recipient_id),
            'amount': payment.amount
        })
    
    # Sort combined activities by date
    recent_activities.sort(key=lambda x: x['date'], reverse=True)
    recent_activities = recent_activities[:10]  # Keep only 10 most recent
    
    # Get all flatmates
    flatmates = User.query.filter_by(flat_id=current_user.flat_id).all()
    
    return render_template('dashboard.html',
                         expenses=expenses,
                         total_flat_expenses=total_flat_expenses,
                         personal_expenses=personal_expenses,
                         months_data=months_data,
                         categories_data=categories_data,
                         user_expenses=user_expenses,
                         my_unpaid=my_unpaid,
                         owed_to_me=owed_to_me,
                         recent_activities=recent_activities,
                         flatmates=flatmates)

@main.route('/manage-flat', methods=['GET', 'POST'])
@login_required
def manage_flat():
    # Get all available flats
    available_flats = Flat.query.all()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create':
            flat_name = request.form.get('flat_name')
            if not flat_name:
                flash('Please provide a flat name', 'error')
                return redirect(url_for('main.manage_flat'))
            
            new_flat = Flat(name=flat_name)
            db.session.add(new_flat)
            db.session.commit()
            
            current_user.flat = new_flat
            current_user.is_flat_leader = True
            db.session.commit()
            
            flash(f'Created new flat: {flat_name}', 'success')
            return redirect(url_for('main.dashboard'))
            
        elif action == 'join':
            flat_id = request.form.get('flat_id')
            if not flat_id:
                flash('Please select a flat to join', 'error')
                return redirect(url_for('main.manage_flat'))
            
            flat = Flat.query.get(flat_id)
            if not flat:
                flash('Invalid flat selection', 'error')
                return redirect(url_for('main.manage_flat'))
            
            current_user.flat = flat
            db.session.commit()
            
            flash(f'Joined flat: {flat.name}', 'success')
            return redirect(url_for('main.dashboard'))
    
    return render_template('manage_flat.html', available_flats=available_flats)

@main.route('/add_expense', methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        description = request.form.get('description')
        amount = float(request.form.get('amount'))
        category = request.form.get('category')
        is_shared = request.form.get('is_shared') == 'on'
        split_type = request.form.get('split_type', 'equal')
        
        # Create and save the expense
        expense = Expense(
            description=description,
            amount=amount,
            category=category,
            is_shared=is_shared,
            creator_id=current_user.id,
            flat_id=current_user.flat_id
        )
        db.session.add(expense)
        db.session.commit()  # Commit to get the expense ID
        
        if is_shared:
            if split_type == 'equal':
                # Get selected members to split with
                member_ids = request.form.getlist('members')
                if not member_ids:
                    flash('Please select at least one member to share the expense with.', 'error')
                    return redirect(url_for('main.add_expense'))
                
                # Add creator to the split if not already included
                member_ids = [str(id) for id in member_ids]  # Convert all IDs to strings
                if str(current_user.id) not in member_ids:
                    member_ids.append(str(current_user.id))
                    
                num_members = len(member_ids)
                share_amount = amount / num_members
                
                # Create equal expense shares
                for member_id in member_ids:
                    share = ExpenseShare(
                        expense_id=expense.id,
                        user_id=int(member_id),
                        share_amount=share_amount,
                        is_paid=(int(member_id) == current_user.id)  # Mark as paid for the creator
                    )
                    db.session.add(share)
            else:  # Custom split
                # Get custom shares for each flatmate
                total_custom_shares = 0
                shares_data = []
                
                for key, value in request.form.items():
                    if key.startswith('custom_share_'):
                        user_id = int(key.replace('custom_share_', ''))
                        if value:  # Only process if amount is provided
                            share_amount = float(value)
                            total_custom_shares += share_amount
                            shares_data.append((user_id, share_amount))
                
                # Calculate creator's share
                creator_share = amount - total_custom_shares
                
                # Validate total matches expense amount
                if abs(total_custom_shares - amount) > 0.01 and abs(total_custom_shares) > 0:
                    flash('The sum of shares must equal the total amount.', 'error')
                    return redirect(url_for('main.add_expense'))
                
                # Create custom expense shares
                for user_id, share_amount in shares_data:
                    share = ExpenseShare(
                        expense_id=expense.id,
                        user_id=user_id,
                        share_amount=share_amount,
                        is_paid=False
                    )
                    db.session.add(share)
                
                # Add creator's share
                if creator_share > 0:
                    share = ExpenseShare(
                        expense_id=expense.id,
                        user_id=current_user.id,
                        share_amount=creator_share,
                        is_paid=True  # Creator's share is always paid
                    )
                    db.session.add(share)
            
            db.session.commit()  # Commit all shares
        else:
            # If not shared, create a single expense share for the creator
            share = ExpenseShare(
                expense_id=expense.id,
                user_id=current_user.id,
                share_amount=amount,
                is_paid=True  # Creator's own expense is always paid
            )
            db.session.add(share)
            db.session.commit()
            
        flash('Expense added successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    
    flatmates = User.query.filter_by(flat_id=current_user.flat_id).all()
    return render_template('add_expense.html', flatmates=flatmates)

@main.route('/grocery_list')
@login_required
def grocery_list():
    items = GroceryItem.query.filter_by(flat_id=current_user.flat_id).order_by(GroceryItem.created_at.desc()).all()
    return render_template('grocery_list.html', items=items)

@main.route('/add_grocery_item', methods=['POST'])
@login_required
def add_grocery_item():
    name = request.form.get('name')
    quantity = request.form.get('quantity')
    
    item = GroceryItem(
        name=name,
        quantity=quantity,
        added_by_id=current_user.id,
        flat_id=current_user.flat_id
    )
    db.session.add(item)
    db.session.commit()
    
    return jsonify({'success': True})

@main.route('/toggle_grocery_item/<int:item_id>', methods=['POST'])
@login_required
def toggle_grocery_item(item_id):
    item = GroceryItem.query.get_or_404(item_id)
    item.is_bought = not item.is_bought
    db.session.commit()
    return jsonify({'success': True})

@main.route('/settle_balances')
@login_required
def settle_balances():
    # Get all expenses for the flat
    expenses = Expense.query.filter_by(flat_id=current_user.flat_id).all()
    
    # Calculate balances
    balances = {}
    
    for expense in expenses:
        # Initialize balances for all users involved
        if expense.creator_id not in balances:
            balances[expense.creator_id] = 0
            
        # Get all shares for this expense
        shares = ExpenseShare.query.filter_by(expense_id=expense.id).all()
        
        for share in shares:
            if share.user_id not in balances:
                balances[share.user_id] = 0
                
            if not share.is_paid:
                # Deduct from the person who owes
                balances[share.user_id] -= share.share_amount
                # Add to the person who paid
                balances[expense.creator_id] += share.share_amount
    
    # Get user details
    users = {user.id: user for user in User.query.filter_by(flat_id=current_user.flat_id)}
    
    # Create a list of who owes whom
    transactions = []
    for debtor_id, amount in balances.items():
        if amount < 0:  # This person owes money
            for creditor_id, creditor_amount in balances.items():
                if creditor_amount > 0:  # This person should receive money
                    # Calculate how much of the debt goes to this creditor
                    share_percentage = creditor_amount / sum(amt for amt in balances.values() if amt > 0)
                    owed_amount = abs(amount) * share_percentage
                    if owed_amount >= 0.01:  # Only show transactions worth at least 1 cent
                        transactions.append({
                            'debtor': users[debtor_id],
                            'creditor': users[creditor_id],
                            'amount': owed_amount
                        })
    
    return render_template('settle_balances.html', 
                         balances=balances, 
                         users=users, 
                         transactions=transactions)

@main.route('/mark_paid/<int:user_id>', methods=['POST'])
@login_required
def mark_paid(user_id):
    amount = float(request.form.get('amount'))
    
    payment = Payment(
        amount=amount,
        payer_id=user_id,
        recipient_id=current_user.id
    )
    db.session.add(payment)
    
    # Mark relevant expense shares as paid
    shares = ExpenseShare.query.join(Expense)\
        .filter(ExpenseShare.user_id == user_id)\
        .filter(Expense.creator_id == current_user.id)\
        .filter(ExpenseShare.is_paid == False)\
        .order_by(Expense.date).all()
    
    remaining_amount = amount
    for share in shares:
        if remaining_amount >= share.share_amount:
            share.is_paid = True
            remaining_amount -= share.share_amount
        if remaining_amount <= 0:
            break
    
    db.session.commit()
    return redirect(url_for('main.settle_balances'))

@main.route('/delete_expense/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    
    # Check if the user is authorized to delete this expense
    if expense.creator_id != current_user.id and not current_user.is_flat_leader:
        flash('You are not authorized to delete this expense.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Delete associated expense shares first
    ExpenseShare.query.filter_by(expense_id=expense_id).delete()
    
    # Delete the expense
    db.session.delete(expense)
    db.session.commit()
    
    flash('Expense deleted successfully.', 'success')
    return redirect(url_for('main.dashboard'))

@main.route('/edit_expense/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    
    # Check if the user is authorized to edit this expense
    if expense.creator_id != current_user.id and not current_user.is_flat_leader:
        flash('You are not authorized to edit this expense.', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        expense.description = request.form.get('description')
        expense.amount = float(request.form.get('amount'))
        expense.category = request.form.get('category')
        expense.is_shared = request.form.get('is_shared') == 'on'
        
        # Update expense shares if it's a shared expense
        if expense.is_shared:
            # Delete existing shares
            ExpenseShare.query.filter_by(expense_id=expense_id).delete()
            
            split_type = request.form.get('split_type', 'equal')
            if split_type == 'equal':
                member_ids = request.form.getlist('members')
                if not member_ids:
                    flash('Please select at least one member to share the expense with.', 'error')
                    return redirect(url_for('main.edit_expense', expense_id=expense_id))
                
                # Add creator to the split if not already included
                member_ids = [str(id) for id in member_ids]
                if str(current_user.id) not in member_ids:
                    member_ids.append(str(current_user.id))
                
                # Calculate equal shares
                share_amount = expense.amount / len(member_ids)
                
                # Create new expense shares
                for member_id in member_ids:
                    share = ExpenseShare(
                        expense_id=expense.id,
                        user_id=int(member_id),
                        share_amount=share_amount,
                        is_paid=False
                    )
                    db.session.add(share)
            else:  # Custom split
                for key, value in request.form.items():
                    if key.startswith('custom_share_'):
                        user_id = int(key.replace('custom_share_', ''))
                        share_amount = float(value) if value else 0
                        if share_amount > 0:
                            share = ExpenseShare(
                                expense_id=expense.id,
                                user_id=user_id,
                                share_amount=share_amount,
                                is_paid=False
                            )
                            db.session.add(share)
        
        db.session.commit()
        flash('Expense updated successfully.', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('edit_expense.html', expense=expense, flatmates=User.query.filter_by(flat_id=current_user.flat_id).all())
