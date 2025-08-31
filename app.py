import os
from datetime import datetime, timedelta, date
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, SelectField, DateField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate

# App configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///subscriptions.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Database and extensions setup
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    subscriptions = db.relationship('Subscription', backref='owner', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    cost = db.Column(db.Float, nullable=False)
    billing_frequency = db.Column(db.String(50), nullable=False) # e.g., 'monthly', 'yearly'
    next_billing_date = db.Column(db.Date, nullable=False)
    usage_frequency = db.Column(db.String(50), default='Not Tracked') # e.g., 'daily', 'weekly', 'monthly'
    value_rating = db.Column(db.Integer, default=0) # e.g., 1-5 rating
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category = db.Column(db.String(100), default='Other')

    def value_score(self):
        """
        Calculates a value score as a percentage (0-100).
        Higher score means better value.
        The score is based on a combination of low cost and high usage.
        """
        try:
            # Normalize cost to a daily figure. We'll cap the "cost score".
            # A lower cost should result in a higher score.
            cost_per_day = self.cost / 30 if self.billing_frequency == 'monthly' else self.cost / 365
            # We'll say anything over $2/day is "very expensive" for the purpose of this score.
            # This creates a score from 0-100 where lower cost is better.
            cost_score = max(0, 100 - (cost_per_day / 2 * 100))

            # Assign a score based on usage frequency. Higher usage is better.
            usage_score = 0
            if self.usage_frequency == 'daily':
                usage_score = 100
            elif self.usage_frequency == 'weekly':
                usage_score = 70
            elif self.usage_frequency == 'monthly':
                usage_score = 30
            else: # Not tracked
                usage_score = 10 # Give a small base score

            # Combine the scores. We'll weigh usage slightly higher than cost.
            # Final score is a weighted average: 60% usage, 40% cost.
            final_score = int((usage_score * 0.6) + (cost_score * 0.4))
            
            return final_score
        except:
            return 0


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Forms
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class SubscriptionForm(FlaskForm):
    name = StringField('Subscription Name', validators=[DataRequired()])
    cost = FloatField('Cost', validators=[DataRequired()])
    billing_frequency = SelectField('Billing Frequency', choices=[('monthly', 'Monthly'), ('yearly', 'Yearly')], validators=[DataRequired()])
    next_billing_date = DateField('Next Billing Date', format='%Y-%m-%d', validators=[DataRequired()])
    usage_frequency = SelectField('Usage Frequency', choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('not_tracked', 'Not Tracked')])
    category = SelectField('Category', choices=[
        ('Entertainment', 'Entertainment'),
        ('Productivity', 'Productivity'),
        ('Fitness', 'Fitness'),
        ('Education', 'Education'),
        ('Other', 'Other')
    ])
    submit = SubmitField('Save Subscription')

# Routes
@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/dashboard')
@login_required
def dashboard():
    subscriptions = Subscription.query.filter_by(user_id=current_user.id).order_by(Subscription.next_billing_date).all()
    
    # Analytics data
    monthly_total = sum(s.cost for s in subscriptions if s.billing_frequency == 'monthly')
    yearly_total = sum(s.cost for s in subscriptions if s.billing_frequency == 'yearly')
    monthly_total += yearly_total / 12
    
    category_spending = {}
    for s in subscriptions:
        cost = s.cost if s.billing_frequency == 'monthly' else s.cost / 12
        category_spending[s.category] = category_spending.get(s.category, 0) + cost

    # Recommendations
    recommendations = [s for s in subscriptions if s.value_score() == 'poor']
    potential_savings = sum(s.cost for s in recommendations if s.billing_frequency == 'monthly')
    potential_savings += sum(s.cost for s in recommendations if s.billing_frequency == 'yearly') / 12

    # --- START: NEW LOGIC FOR UPCOMING PAYMENTS ---
    today = date.today()
    reminder_threshold = today + timedelta(days=14)
    upcoming_subscriptions = [
        s for s in subscriptions if today <= s.next_billing_date <= reminder_threshold
    ]
    # --- END: NEW LOGIC ---

    return render_template('index.html', 
                           subscriptions=subscriptions,
                           monthly_total=monthly_total,
                           category_spending=category_spending,
                           recommendations=recommendations,
                           potential_savings=potential_savings,
                           upcoming_subscriptions=upcoming_subscriptions,
                           today=today)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('landing'))

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_subscription():
    form = SubscriptionForm()
    if form.validate_on_submit():
        subscription = Subscription(
            name=form.name.data,
            cost=form.cost.data,
            billing_frequency=form.billing_frequency.data,
            next_billing_date=form.next_billing_date.data,
            usage_frequency=form.usage_frequency.data,
            category=form.category.data,
            owner=current_user
        )
        db.session.add(subscription)
        db.session.commit()
        flash('Subscription added!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_subscription.html', form=form)

@app.route('/edit/<int:subscription_id>', methods=['GET', 'POST'])
@login_required
def edit_subscription(subscription_id):
    subscription = Subscription.query.get_or_404(subscription_id)
    if subscription.owner != current_user:
        abort(403)
    form = SubscriptionForm(obj=subscription)
    if form.validate_on_submit():
        subscription.name = form.name.data
        subscription.cost = form.cost.data
        subscription.billing_frequency = form.billing_frequency.data
        subscription.next_billing_date = form.next_billing_date.data
        subscription.usage_frequency = form.usage_frequency.data
        subscription.category = form.category.data
        db.session.commit()
        flash('Subscription updated!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_subscription.html', form=form)

@app.route('/delete/<int:subscription_id>', methods=['POST'])
@login_required
def delete_subscription(subscription_id):
    subscription = Subscription.query.get_or_404(subscription_id)
    if subscription.owner != current_user:
        abort(403)
    db.session.delete(subscription)
    db.session.commit()
    flash('Subscription deleted!', 'success')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)