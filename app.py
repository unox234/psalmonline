from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin, AnonymousUserMixin
import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask import send_from_directory
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
import uuid

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///liturgie.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
migrate = Migrate(app, db)

# Models
class Church(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=False, nullable=False)  # New field for activation state
    contact_email = db.Column(db.String(150), default='')
    contact_phone = db.Column(db.String(50), default='')
    contact_address = db.Column(db.String(200), default='')
    logo_filename = db.Column(db.String(300), nullable=True)  # New field for logo filename
    users = db.relationship('User', backref='church', lazy=True)
    boards = db.relationship('Liturgiebord', backref='church', lazy=True)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    church_id = db.Column(db.Integer, db.ForeignKey('church.id'), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

# Association table for many-to-many relationship
board_schedule_association = db.Table('board_schedule',
    db.Column('board_id', db.Integer, db.ForeignKey('liturgiebord.id'), primary_key=True),
    db.Column('schedule_id', db.Integer, db.ForeignKey('schedule.id'), primary_key=True)
)

class Liturgiebord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unique_id = db.Column(db.String(32), unique=True, nullable=False, default=lambda: uuid.uuid4().hex)
    name = db.Column(db.String(150), nullable=False)
    church_id = db.Column(db.Integer, db.ForeignKey('church.id'), nullable=False)
    line1 = db.Column(db.String(200), default='')
    line2 = db.Column(db.String(200), default='')
    line3 = db.Column(db.String(200), default='')
    line4 = db.Column(db.String(200), default='')
    line5 = db.Column(db.String(200), default='')
    line6 = db.Column(db.String(200), default='')
    line7 = db.Column(db.String(200), default='')
    line8 = db.Column(db.String(200), default='')
    line9 = db.Column(db.String(200), default='')
    line10 = db.Column(db.String(200), default='')
    background_image = db.Column(db.String(300), default=None)
    # Updated relationship: many-to-many
    schedules = db.relationship('Schedule', secondary=board_schedule_association, back_populates='boards', lazy='dynamic')

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Removed board_id to make schedules global
    name = db.Column(db.String(150), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    date = db.Column(db.Date, nullable=False)
    content = db.Column(db.Text, nullable=False)  # separate lines with \n
    # Many-to-many relationship back to boards
    boards = db.relationship('Liturgiebord', secondary=board_schedule_association, back_populates='schedules', lazy='dynamic')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

# --- Church Settings Route ---
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

@app.route('/church/settings', methods=['GET', 'POST'])
@login_required
def church_settings():
    church = current_user.church
    msg = None
    if request.method == 'POST' and request.form.get('form_type') == 'contact':
        church.name = request.form.get('name', '').strip()
        church.contact_email = request.form.get('contact_email', '').strip()
        church.contact_phone = request.form.get('contact_phone', '').strip()
        church.contact_address = request.form.get('contact_address', '').strip()

        # Handle logo upload
        if 'logo' in request.files:
            logo = request.files['logo']
            if logo and allowed_file(logo.filename):
                filename = secure_filename(f'church_{church.id}_logo_{logo.filename}')
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                logo.save(filepath)
                church.logo_filename = filename

        db.session.commit()
        msg = 'Kerkgegevens opgeslagen!'
    elif request.method == 'POST' and request.form.get('form_type') == 'user':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if not username or not password:
            msg = 'Gebruikersnaam en wachtwoord zijn verplicht.'
        elif User.query.filter_by(username=username).first():
            msg = 'Gebruikersnaam bestaat al.'
        else:
            user = User(username=username, password=generate_password_hash(password), church_id=church.id)
            db.session.add(user)
            db.session.commit()
            msg = f'Gebruiker {username} toegevoegd aan deze kerk.'
    users = church.users
    return render_template('church_settings.html', church=church, users=users, msg=msg)
# Placeholder routes for login, register, church portal, board management, and display
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('portal'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('portal'))
        else:
            flash('Ongeldige gebruikersnaam of wachtwoord')
    return render_template('login.html')


@app.route('/church/delete_user/<int:user_id>', methods=['POST'])
@login_required
def church_delete_user(user_id):
    user_to_delete = User.query.get_or_404(user_id)
    # Confirm user belongs to the same church
    if user_to_delete.church_id != current_user.church_id:
        flash('Geen toegang tot deze gebruiker')
        return redirect(url_for('church_settings'))
    # Disallow deleting self
    if user_to_delete.id == current_user.id:
        flash('Je kunt jezelf niet verwijderen')
        return redirect(url_for('church_settings'))
    # Disallow deleting admin users
    if user_to_delete.is_admin:
        flash('Kan admin-gebruiker niet verwijderen')
        return redirect(url_for('church_settings'))
    db.session.delete(user_to_delete)
    db.session.commit()
    flash(f'Gebruiker {user_to_delete.username} verwijderd!')
    return redirect(url_for('church_settings'))

@app.route('/logout')
@login_required
def logout():
    session.pop('impersonate_id', None)
    session.pop('admin_id', None)
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    import re
    if current_user.is_authenticated:
        return redirect(url_for('portal'))
    if request.method == 'POST':
        email = request.form['username'].strip()
        password = request.form['password']
        church_name = request.form['church'].strip()
        # Validate basic email format
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash('Voer een geldig e-mailadres in')
            return render_template('register.html')
        if User.query.filter_by(username=email).first():
            flash('Emailadres bestaat al')
            return render_template('register.html')
        church = Church.query.filter_by(name=church_name).first()
        if church:
            # Prevent registering to an existing church to avoid security risk
            flash('Het church name bestaat al. Maak een unieke church aan.')
            return render_template('register.html')
        else:
            church = Church(name=church_name, is_active=False)  # New churches start inactive
            db.session.add(church)
            db.session.commit()

        hashed_pw = generate_password_hash(password)
        user = User(username=email, password=hashed_pw, church_id=church.id)
        db.session.add(user)
        db.session.commit()
        flash('Registratie gelukt! Je kunt nu inloggen.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/portal')
@login_required
def portal():
    boards = Liturgiebord.query.filter_by(church_id=current_user.church_id).all()
    return render_template('portal.html', boards=boards)

@app.route('/board/add', methods=['GET', 'POST'])
@login_required
def add_board():
    if request.method == 'POST':
        name = request.form.get('name')
        board = Liturgiebord(name=name, church_id=current_user.church_id)
        db.session.add(board)
        db.session.commit()
        return redirect(url_for('portal'))
    return render_template('add_board.html')

@app.route('/board/<int:board_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_board(board_id):
    board = Liturgiebord.query.get_or_404(board_id)
    if board.church_id != current_user.church_id:
        flash('Geen toegang tot dit bord')
        return redirect(url_for('portal'))
    if request.method == 'POST':
        # If changing the name
        if request.form.get('form_type') == 'name':
            new_name = request.form.get('name', '').strip()
            if new_name:
                board.name = new_name
                db.session.commit()
                flash('Naam van het bord gewijzigd!')
            else:
                flash('Naam mag niet leeg zijn.')
            return redirect(url_for('edit_board', board_id=board.id))
        # Otherwise, update lines
        for i in range(1, 11):
            setattr(board, f'line{i}', request.form.get(f'line{i}', ''))
        db.session.commit()
        flash('Bord bijgewerkt!')
        return redirect(url_for('portal'))
    # Get schedules assigned to this board
    schedules = board.schedules.order_by(Schedule.date.desc(), Schedule.start_time).all()

    # Find the active schedule object
    active_schedule = None
    now = datetime.now()
    today = now.date()
    current_time = now.time()
    for schedule in schedules:
        if schedule.date == today and schedule.start_time <= current_time <= schedule.end_time:
            active_schedule = schedule
            break

    schedule_active = active_schedule is not None

    schedule_content = None
    if schedule_active:
        schedule_content = active_schedule.content

    return render_template('edit_board.html', board=board, schedules=schedules, schedule_active=schedule_active, active_schedule=active_schedule, schedule_content=schedule_content)

from datetime import datetime

# Helper to get active schedule for a board
from sqlalchemy import and_, or_
def get_active_schedule(board):
    now = datetime.now()
    today = now.date()
    current_time = now.time()
    for schedule in board.schedules:
        if schedule.date != today:
            continue
        if not (schedule.start_time <= current_time <= schedule.end_time):
            continue
        return schedule.content
    return None

@app.route('/board/<int:board_id>')
def display_board(board_id):
    board = Liturgiebord.query.get_or_404(board_id)
    schedule_content = get_active_schedule(board)
    return render_template('display_board.html', board=board, schedule_content=schedule_content)

from flask import jsonify

@app.route('/board/<int:board_id>/active_schedule_json')
def active_schedule_json(board_id):
    board = Liturgiebord.query.get_or_404(board_id)
    schedule_content = get_active_schedule(board)
    # Return schedule lines if active, else board input lines
    if schedule_content:
        lines = schedule_content.split('\n')
    else:
        # Use board lines if no active schedule
        lines = [
            board.line1 or ' ',
            board.line2 or ' ',
            board.line3 or ' ',
            board.line4 or ' ',
            board.line5 or ' ',
            board.line6 or ' ',
            board.line7 or ' ',
            board.line8 or ' ',
            board.line9 or ' ',
            board.line10 or ' '
        ]
    # Also include background info for completeness
    bg_url = None
    if board.background_image:
        # Determine URL path, check if default or uploaded
        from flask import url_for
        if board.background_image.startswith('default_'):
            bg_url = url_for('static', filename=board.background_image)
        else:
            bg_url = url_for('uploaded_file', filename=board.background_image)
    return jsonify({
        'lines': lines,
        'background': bg_url
    })

@app.route('/board/<int:board_id>/delete', methods=['POST'])
@login_required
def delete_board(board_id):
    board = Liturgiebord.query.get_or_404(board_id)
    if board.church_id != current_user.church_id and not current_user.is_admin:
        flash('Geen toegang tot dit bord')
        return redirect(url_for('portal'))
    # Remove schedule associations but keep schedules intact
    board.schedules = []
    db.session.commit()
    # Then delete the board
    db.session.delete(board)
    db.session.commit()
    flash('Liturgiebord verwijderd!')
    return redirect(url_for('portal'))


from flask import abort

# Remove old per-board schedule management routes

@app.route('/schedules')
@login_required
def global_schedules():
    user_church_id = current_user.church_id
    if current_user.is_admin:
        # Admin sees all schedules
        schedules = Schedule.query.order_by(Schedule.date.desc(), Schedule.start_time).all()
    else:
        # Non-admin: show only schedules linked to boards of their church
        schedules = []
        boards = Liturgiebord.query.filter_by(church_id=user_church_id).all()
        board_ids = [b.id for b in boards]
        all_schedules = Schedule.query.order_by(Schedule.date.desc(), Schedule.start_time).all()
        for schedule in all_schedules:
            # Check if schedule belongs to any board_id of current church
            for board in schedule.boards:
                if board.id in board_ids:
                    schedules.append(schedule)
                    break
    boards = Liturgiebord.query.filter_by(church_id=user_church_id).all()
    return render_template('global_schedules.html', schedules=schedules, boards=boards)

@app.route('/schedules/add', methods=['GET', 'POST'])
@login_required
def add_global_schedule():
    user_church_id = current_user.church_id
    boards = Liturgiebord.query.filter_by(church_id=user_church_id).all()
    if request.method == 'POST':
        from datetime import datetime
        sched_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        start_time = datetime.strptime(request.form['start_time'], '%H:%M').time()
        end_time = datetime.strptime(request.form['end_time'], '%H:%M').time()
        lines = []
        for i in range(1, 11):
            line = request.form.get(f'line{i}', '').strip()
            if line == '':
                line = ' '
            lines.append(line)
        content = '\n'.join(lines)
        name = request.form['name']
        board_ids = request.form.getlist('boards')

        schedule_obj = Schedule(
            name=name,
            start_time=start_time,
            end_time=end_time,
            content=content,
            date=sched_date
        )
        # Assign boards
        for board_id in board_ids:
            board = Liturgiebord.query.get(int(board_id))
            if board and (board.church_id == user_church_id or current_user.is_admin):
                schedule_obj.boards.append(board)

        db.session.add(schedule_obj)
        db.session.commit()
        flash('Nieuwe planning toegevoegd.')
        return redirect(url_for('global_schedules'))
    return render_template('schedule_form.html', schedule=None, boards=boards)

@app.route('/schedules/<int:schedule_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_global_schedule(schedule_id):
    user_church_id = current_user.church_id
    schedule = Schedule.query.get_or_404(schedule_id)
    # Convert boards dynamic relationship to list for template
    schedule.boards_list = schedule.boards.all()

    # Check user has access via any board or admin
    accessible = False
    for board in schedule.boards_list:
        if board.church_id == user_church_id:
            accessible = True
            break
    if not (accessible or current_user.is_admin):
        abort(403)

    boards = Liturgiebord.query.filter_by(church_id=user_church_id).all()

    if request.method == 'POST':
        from datetime import datetime
        schedule.date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        schedule.start_time = datetime.strptime(request.form['start_time'], '%H:%M').time()
        schedule.end_time = datetime.strptime(request.form['end_time'], '%H:%M').time()
        lines = []
        for i in range(1, 11):
            line = request.form.get(f'line{i}', '').strip()
            if line == '':
                line = ' '
            lines.append(line)
        schedule.content = '\n'.join(lines)
        schedule.name = request.form['name']

        # Update board assignments
        board_ids = request.form.getlist('boards')
        schedule.boards = []  # Clear old assignments
        for board_id in board_ids:
            board = Liturgiebord.query.get(int(board_id))
            if board and (board.church_id == user_church_id or current_user.is_admin):
                schedule.boards.append(board)

        db.session.commit()
        flash('Planning bijgewerkt.')
        return redirect(url_for('global_schedules'))
    return render_template('schedule_form.html', schedule=schedule, boards=boards)

@app.route('/schedules/<int:schedule_id>/delete', methods=['POST'])
@login_required
def delete_global_schedule(schedule_id):
    schedule = Schedule.query.get_or_404(schedule_id)
    # Check user has access via any board or admin
    user_church_id = current_user.church_id
    accessible = False
    for board in schedule.boards:
        if board.church_id == user_church_id:
            accessible = True
            break
    if not (accessible or current_user.is_admin):
        abort(403)
    db.session.delete(schedule)
    db.session.commit()
    flash('Planning verwijderd.')
    return redirect(url_for('global_schedules'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
@app.route('/board/<int:board_id>/background', methods=['GET', 'POST'])
@login_required
def upload_background(board_id):
    board = Liturgiebord.query.get_or_404(board_id)
    if board.church_id != current_user.church_id:
        flash('Geen toegang tot dit bord')
        return redirect(url_for('portal'))
    if request.method == 'POST':
        # handle setting default wallpaper
        default_background = request.form.get('default_background')
        if default_background:
            # Set the default wallpaper filename directly
            # We assume the filename is safe and known
            board.background_image = default_background
            db.session.commit()
            flash('Achtergrondafbeelding ingesteld!')
            return redirect(url_for('edit_board', board_id=board.id))

        if 'background' not in request.files:
            flash('Geen bestand geselecteerd')
            return redirect(request.url)
        file = request.files['background']
        if file and allowed_file(file.filename):
            filename = secure_filename(f'board_{board.id}_bg_{file.filename}')
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            board.background_image = filename
            db.session.commit()
            flash('Achtergrondafbeelding bijgewerkt!')
            return redirect(url_for('edit_board', board_id=board.id))
        else:
            flash('Ongeldig bestandstype')
    return render_template('upload_background.html', board=board)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, is_admin=True).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Ongeldige admin-inloggegevens')
    return render_template('admin_login.html')

from flask import request

@app.route('/admin/delete_church/<int:church_id>', methods=['POST'])
@login_required
def admin_delete_church(church_id):
    if not current_user.is_admin:
        flash('Geen toegang')
        return redirect(url_for('portal'))
    church = Church.query.get_or_404(church_id)
    # Delete associated boards and users
    for board in church.boards:
        db.session.delete(board)
    for user in church.users:
        db.session.delete(user)
    db.session.delete(church)
    db.session.commit()
    flash(f'Kerk {church.name} en alle bijbehorende data verwijderd!')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Geen toegang')
        return redirect(url_for('portal'))

    if request.method == 'POST':
        # Update church activation states
        for church in Church.query.all():
            checkbox_val = request.form.get(f'church_active_{church.id}')
            church.is_active = checkbox_val == 'on'
        db.session.commit()
        flash('Kerken activatiestatus bijgewerkt.')

    churches = Church.query.all()
    users = User.query.all()
    return render_template('admin_dashboard.html', churches=churches, users=users)

@app.route('/admin/impersonate/<int:user_id>')
@login_required
def admin_impersonate(user_id):
    if not current_user.is_admin:
        flash('Geen toegang')
        return redirect(url_for('portal'))
    user = User.query.get_or_404(user_id)
    session['impersonate_id'] = user.id
    session['admin_id'] = current_user.id
    flash(f'Je bent nu ingelogd als {user.username}')
    return redirect(url_for('portal'))

@app.before_request
def impersonate_user():
    if 'impersonate_id' in session and 'admin_id' in session:
        # Only impersonate if the real admin is logged in
        admin = User.query.get(session['admin_id'])
        if admin and admin.is_authenticated and admin.is_admin:
            user = User.query.get(session['impersonate_id'])
            if user:
                # Use Flask-Login's login_user to switch context
                login_user(user)
                # Attach a proxy attribute to current_user to allow admin checks
                current_user._is_impersonated = True
                current_user._real_admin_id = admin.id
    else:
        # Not impersonating, ensure _is_impersonated is not set
        if hasattr(current_user, '_is_impersonated'):
            delattr(current_user, '_is_impersonated')
        if hasattr(current_user, '_real_admin_id'):
            delattr(current_user, '_real_admin_id')


@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('Geen toegang')
        return redirect(url_for('portal'))
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if not current_user.is_admin:
        flash('Geen toegang')
        return redirect(url_for('portal'))
    user = User.query.get_or_404(user_id)
    church = user.church
    if user.is_admin:
        flash('Kan geen admin-gebruiker verwijderen!')
        return redirect(url_for('admin_users'))
    if len(church.users) > 1:
        # Just delete the user
        db.session.delete(user)
        db.session.commit()
        flash(f'Gebruiker {user.username} verwijderd!')
    else:
        # Last user, delete user, church, boards
        for board in church.boards:
            db.session.delete(board)
        db.session.delete(user)
        db.session.delete(church)
        db.session.commit()
        flash(f'Laatste gebruiker verwijderd. Kerk en data ook verwijderd ({user.username}, {church.name})!')
    return redirect(url_for('admin_users'))

@app.route('/display/<unique_id>')
def display_board_unique(unique_id):
    board = Liturgiebord.query.filter_by(unique_id=unique_id).first_or_404()
    schedule_content = get_active_schedule(board)
    return render_template('display_board.html', board=board, schedule_content=schedule_content)

from werkzeug.security import check_password_hash

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    msg = None
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        if not check_password_hash(current_user.password, current_password):
            msg = 'Huidig wachtwoord is onjuist.'
        elif not new_password or not confirm_password:
            msg = 'Voer een nieuw wachtwoord in.'
        elif new_password != confirm_password:
            msg = 'De nieuwe wachtwoorden komen niet overeen.'
        else:
            current_user.password = generate_password_hash(new_password)
            db.session.commit()
            msg = 'Wachtwoord succesvol gewijzigd.'
    return render_template('change_password.html', msg=msg)

if __name__ == '__main__':
    if not os.path.exists('liturgie.db'):
        with app.app_context():
            db.create_all()
            # Create initial admin user if not exists
            if not User.query.filter_by(username='admin').first():
                admin_church = Church.query.filter_by(name='Admin').first()
                if not admin_church:
                    admin_church = Church(name='Admin')
                    db.session.add(admin_church)
                    db.session.commit()
                admin_user = User(username='admin', password=generate_password_hash('admin'), church_id=admin_church.id, is_admin=True)
                db.session.add(admin_user)
                db.session.commit()
    app.run(host='0.0.0.0')