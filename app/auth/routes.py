from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app.auth import auth
from app.models.user import User, Flat
from app import db

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('auth/login.html')

@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        is_flat_leader = request.form.get('is_flat_leader') == 'on'
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('auth.signup'))
        
        user = User(email=email, username=username, is_flat_leader=is_flat_leader)
        user.set_password(password)
        
        if is_flat_leader:
            flat_name = request.form.get('flat_name')
            flat = Flat(name=flat_name)
            db.session.add(flat)
            db.session.flush()
            user.flat_id = flat.id
        
        db.session.add(user)
        db.session.commit()
        
        flash('Account created successfully!', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/signup.html')

@auth.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
