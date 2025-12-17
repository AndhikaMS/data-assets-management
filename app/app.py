from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
# MySQL Configuration for XAMPP
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/asset_management'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'app/static/uploads'

db = SQLAlchemy(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'photos'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'qrcodes'), exist_ok=True)

# Allowed extensions for photo upload
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_asset_code():
    """Generate unique asset code with format: AST-YYYYMMDD-XXXX"""
    today = datetime.utcnow().strftime('%Y%m%d')
    
    # Get count of assets created today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    count = Asset.query.filter(Asset.created_at >= today_start).count()
    
    # Generate code
    code = f"AST-{today}-{count + 1:04d}"
    
    # Ensure uniqueness
    while Asset.query.filter_by(asset_code=code).first():
        count += 1
        code = f"AST-{today}-{count + 1:04d}"
    
    return code

# ============ MODELS ============
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default='admin')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Location(db.Model):
    __tablename__ = 'locations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Asset(db.Model):
    __tablename__ = 'assets'
    id = db.Column(db.Integer, primary_key=True)
    asset_code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'))
    condition = db.Column(db.String(50))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    category = db.relationship('Category', backref='assets')
    location = db.relationship('Location', backref='assets')

class QRCode(db.Model):
    __tablename__ = 'qr_codes'
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'))
    file_path = db.Column(db.String(255))
    qr_value = db.Column(db.String(255))
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    asset = db.relationship('Asset', backref='qr_codes')

class AssetPhoto(db.Model):
    __tablename__ = 'asset_photos'
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'))
    file_path = db.Column(db.String(255))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    asset = db.relationship('Asset', backref='photos')

class AssetHistory(db.Model):
    __tablename__ = 'asset_history'
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100))
    description = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    asset = db.relationship('Asset', backref='history')
    user = db.relationship('User', backref='activities')

# ============ LOGIN DECORATOR ============
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Silakan login terlebih dahulu', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ============ ROUTES ============
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# ============ LOGIN & LOGOUT ============
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # Validasi input
        if not username or not password:
            flash('Username dan password tidak boleh kosong', 'danger')
            return render_template('login.html')
        
        # Cek user di database
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            # Login berhasil
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash(f'Selamat datang, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            # Login gagal
            flash('Username atau password salah', 'danger')
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah logout', 'info')
    return redirect(url_for('login'))

# ============ DASHBOARD ============
@app.route('/dashboard')
@login_required
def dashboard():
    # Get statistics
    total_assets = Asset.query.count()
    total_categories = Category.query.count()
    total_qr_generated = QRCode.query.count()
    
    # Today's activities
    today = datetime.utcnow().date()
    today_activities = AssetHistory.query.filter(
        db.func.date(AssetHistory.timestamp) == today
    ).count()
    
    # Recent activities (last 10)
    recent_activities = AssetHistory.query.order_by(
        AssetHistory.timestamp.desc()
    ).limit(10).all()
    
    return render_template('dashboard.html',
                         total_assets=total_assets,
                         total_categories=total_categories,
                         total_qr_generated=total_qr_generated,
                         today_activities=today_activities,
                         recent_activities=recent_activities)

# ============ ASSET ROUTES ============
@app.route('/aset')
@login_required
def aset_list():
    # Get filter parameters
    category_filter = request.args.get('category', '')
    location_filter = request.args.get('location', '')
    condition_filter = request.args.get('condition', '')
    search_query = request.args.get('search', '')
    
    # Base query
    query = Asset.query
    
    # Apply filters
    if category_filter:
        query = query.filter_by(category_id=category_filter)
    
    if location_filter:
        query = query.filter_by(location_id=location_filter)
    
    if condition_filter:
        query = query.filter_by(condition=condition_filter)
    
    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(
            db.or_(
                Asset.name.like(search_pattern),
                Asset.asset_code.like(search_pattern)
            )
        )
    
    assets = query.order_by(Asset.created_at.desc()).all()
    
    # Get all categories and locations for filter dropdowns
    categories = Category.query.order_by(Category.name).all()
    locations = Location.query.order_by(Location.name).all()
    
    return render_template('aset/list.html', 
                         assets=assets,
                         categories=categories,
                         locations=locations,
                         category_filter=category_filter,
                         location_filter=location_filter,
                         condition_filter=condition_filter,
                         search_query=search_query)

@app.route('/aset/detail/<int:id>')
@login_required
def aset_detail(id):
    asset = Asset.query.get_or_404(id)
    
    # Get asset history
    history = AssetHistory.query.filter_by(asset_id=id).order_by(
        AssetHistory.timestamp.desc()
    ).all()
    
    return render_template('aset/detail.html', asset=asset, history=history)

@app.route('/aset/tambah', methods=['GET', 'POST'])
@login_required
def aset_tambah():
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name', '').strip()
        category_id = request.form.get('category_id')
        location_id = request.form.get('location_id')
        condition = request.form.get('condition', '').strip()
        description = request.form.get('description', '').strip()
        
        # Validation
        if not name:
            flash('Nama aset tidak boleh kosong', 'danger')
            return redirect(url_for('aset_tambah'))
        
        if not category_id:
            flash('Kategori harus dipilih', 'danger')
            return redirect(url_for('aset_tambah'))
        
        if not location_id:
            flash('Lokasi harus dipilih', 'danger')
            return redirect(url_for('aset_tambah'))
        
        # Generate asset code
        asset_code = generate_asset_code()
        
        # Create new asset
        asset = Asset(
            asset_code=asset_code,
            name=name,
            category_id=category_id,
            location_id=location_id,
            condition=condition,
            description=description
        )
        
        db.session.add(asset)
        db.session.flush()  # Get asset.id before commit
        
        # Handle photo upload
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo and photo.filename and allowed_file(photo.filename):
                # Generate unique filename
                import uuid
                ext = photo.filename.rsplit('.', 1)[1].lower()
                filename = f"{asset.asset_code}_{uuid.uuid4().hex[:8]}.{ext}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'photos', filename)
                
                # Save file
                photo.save(filepath)
                
                # Save to database
                asset_photo = AssetPhoto(
                    asset_id=asset.id,
                    file_path=f"uploads/photos/{filename}"
                )
                db.session.add(asset_photo)
        
        # Log activity
        history = AssetHistory(
            asset_id=asset.id,
            user_id=session['user_id'],
            action='ADD',
            description=f'Menambahkan aset: {name} ({asset_code})'
        )
        db.session.add(history)
        
        db.session.commit()
        
        flash(f'Aset "{name}" berhasil ditambahkan dengan kode {asset_code}', 'success')
        return redirect(url_for('aset_list'))
    
    # GET request - show form
    categories = Category.query.order_by(Category.name).all()
    locations = Location.query.order_by(Location.name).all()
    
    return render_template('aset/tambah.html', 
                         categories=categories, 
                         locations=locations)

# ============ CATEGORY ROUTES ============
@app.route('/kategori')
@login_required
def kategori_list():
    categories = Category.query.order_by(Category.created_at.desc()).all()
    return render_template('kategori/list.html', categories=categories)

@app.route('/kategori/tambah', methods=['POST'])
@login_required
def kategori_tambah():
    name = request.form.get('name', '').strip()
    
    if not name:
        flash('Nama kategori tidak boleh kosong', 'danger')
        return redirect(url_for('kategori_list'))
    
    # Check if category already exists
    existing = Category.query.filter_by(name=name).first()
    if existing:
        flash('Nama kategori sudah digunakan', 'danger')
        return redirect(url_for('kategori_list'))
    
    # Create new category
    category = Category(name=name)
    db.session.add(category)
    
    # Log activity
    history = AssetHistory(
        user_id=session['user_id'],
        action='ADD_CATEGORY',
        description=f'Menambahkan kategori: {name}'
    )
    db.session.add(history)
    
    db.session.commit()
    flash(f'Kategori "{name}" berhasil ditambahkan', 'success')
    return redirect(url_for('kategori_list'))

@app.route('/kategori/edit/<int:id>', methods=['POST'])
@login_required
def kategori_edit(id):
    category = Category.query.get_or_404(id)
    name = request.form.get('name', '').strip()
    
    if not name:
        flash('Nama kategori tidak boleh kosong', 'danger')
        return redirect(url_for('kategori_list'))
    
    # Check if new name already exists (except current category)
    existing = Category.query.filter(Category.name == name, Category.id != id).first()
    if existing:
        flash('Nama kategori sudah digunakan', 'danger')
        return redirect(url_for('kategori_list'))
    
    old_name = category.name
    category.name = name
    category.updated_at = datetime.utcnow()
    
    # Log activity
    history = AssetHistory(
        user_id=session['user_id'],
        action='EDIT_CATEGORY',
        description=f'Mengubah kategori dari "{old_name}" menjadi "{name}"'
    )
    db.session.add(history)
    
    db.session.commit()
    flash(f'Kategori berhasil diubah menjadi "{name}"', 'success')
    return redirect(url_for('kategori_list'))

@app.route('/kategori/hapus/<int:id>', methods=['POST'])
@login_required
def kategori_hapus(id):
    category = Category.query.get_or_404(id)
    
    # Check if category is used by any asset
    asset_count = Asset.query.filter_by(category_id=id).count()
    if asset_count > 0:
        flash(f'Kategori "{category.name}" tidak dapat dihapus karena masih digunakan oleh {asset_count} aset', 'danger')
        return redirect(url_for('kategori_list'))
    
    name = category.name
    
    # Log activity
    history = AssetHistory(
        user_id=session['user_id'],
        action='DELETE_CATEGORY',
        description=f'Menghapus kategori: {name}'
    )
    db.session.add(history)
    
    db.session.delete(category)
    db.session.commit()
    
    flash(f'Kategori "{name}" berhasil dihapus', 'success')
    return redirect(url_for('kategori_list'))

# ============ LOCATION ROUTES ============
@app.route('/lokasi')
@login_required
def lokasi_list():
    locations = Location.query.order_by(Location.created_at.desc()).all()
    return render_template('lokasi/list.html', locations=locations)

@app.route('/lokasi/tambah', methods=['POST'])
@login_required
def lokasi_tambah():
    name = request.form.get('name', '').strip()
    
    if not name:
        flash('Nama lokasi tidak boleh kosong', 'danger')
        return redirect(url_for('lokasi_list'))
    
    # Check if location already exists
    existing = Location.query.filter_by(name=name).first()
    if existing:
        flash('Nama lokasi sudah digunakan', 'danger')
        return redirect(url_for('lokasi_list'))
    
    # Create new location
    location = Location(name=name)
    db.session.add(location)
    
    # Log activity
    history = AssetHistory(
        user_id=session['user_id'],
        action='ADD_LOCATION',
        description=f'Menambahkan lokasi: {name}'
    )
    db.session.add(history)
    
    db.session.commit()
    flash(f'Lokasi "{name}" berhasil ditambahkan', 'success')
    return redirect(url_for('lokasi_list'))

@app.route('/lokasi/edit/<int:id>', methods=['POST'])
@login_required
def lokasi_edit(id):
    location = Location.query.get_or_404(id)
    name = request.form.get('name', '').strip()
    
    if not name:
        flash('Nama lokasi tidak boleh kosong', 'danger')
        return redirect(url_for('lokasi_list'))
    
    # Check if new name already exists (except current location)
    existing = Location.query.filter(Location.name == name, Location.id != id).first()
    if existing:
        flash('Nama lokasi sudah digunakan', 'danger')
        return redirect(url_for('lokasi_list'))
    
    old_name = location.name
    location.name = name
    location.updated_at = datetime.utcnow()
    
    # Log activity
    history = AssetHistory(
        user_id=session['user_id'],
        action='EDIT_LOCATION',
        description=f'Mengubah lokasi dari "{old_name}" menjadi "{name}"'
    )
    db.session.add(history)
    
    db.session.commit()
    flash(f'Lokasi berhasil diubah menjadi "{name}"', 'success')
    return redirect(url_for('lokasi_list'))

@app.route('/lokasi/hapus/<int:id>', methods=['POST'])
@login_required
def lokasi_hapus(id):
    location = Location.query.get_or_404(id)
    
    # Check if location is used by any asset
    asset_count = Asset.query.filter_by(location_id=id).count()
    if asset_count > 0:
        flash(f'Lokasi "{location.name}" tidak dapat dihapus karena masih digunakan oleh {asset_count} aset', 'danger')
        return redirect(url_for('lokasi_list'))
    
    name = location.name
    
    # Log activity
    history = AssetHistory(
        user_id=session['user_id'],
        action='DELETE_LOCATION',
        description=f'Menghapus lokasi: {name}'
    )
    db.session.add(history)
    
    db.session.delete(location)
    db.session.commit()
    
    flash(f'Lokasi "{name}" berhasil dihapus', 'success')
    return redirect(url_for('lokasi_list'))

# ============ HISTORY ROUTES ============
@app.route('/riwayat')
@login_required
def riwayat_list():
    return render_template('riwayat/list.html')

# ============ INIT DB ============
def init_db():
    with app.app_context():
        db.create_all()
        
        # Create default admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            print("Default admin user created (username: admin, password: admin123)")
        
        # Create default locations if not exists
        if Location.query.count() == 0:
            default_locations = [
                'Lab Komputer 1',
                'Lab Komputer 2',
                'Lab Fisika',
                'Lab Kimia',
                'Ruang Guru',
                'Perpustakaan'
            ]
            for loc_name in default_locations:
                location = Location(name=loc_name)
                db.session.add(location)
            print(f"Created {len(default_locations)} default locations")
        
        db.session.commit()
        print("Database initialized successfully!")

if __name__ == '__main__':
    init_db()
    app.run(debug=True)