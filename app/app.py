from flask import Flask, url_for, session, redirect, flash
from functools import wraps
from datetime import datetime
import os
import qrcode
import uuid

from app.extensions import db
from app.models import User, Location, Asset


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:122391@localhost/asset_management'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'app/static/uploads'

db.init_app(app)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'photos'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'qrcodes'), exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_asset_code():
    today = datetime.utcnow().strftime('%Y%m%d')

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    count = Asset.query.filter(Asset.created_at >= today_start).count()

    code = f"AST-{today}-{count + 1:04d}"

    while Asset.query.filter_by(asset_code=code).first():
        count += 1
        code = f"AST-{today}-{count + 1:04d}"

    return code


def generate_qr_code(asset):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )

    asset_url = url_for('public_aset_detail', id=asset.id, _external=True)

    qr.add_data(asset_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    filename = f"QR_{asset.asset_code}_{uuid.uuid4().hex[:8]}.png"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'qrcodes', filename)

    img.save(filepath)

    return f"uploads/qrcodes/{filename}", asset_url


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Silakan login terlebih dahulu', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def init_db():
    with app.app_context():
        db.create_all()

        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            print("Default admin user created (username: admin, password: admin123)")

        if Location.query.count() == 0:
            default_locations = [
                'Lab Komputer 1',
                'Lab Komputer 2',
                'Lab Fisika',
                'Lab Kimia',
                'Ruang Guru',
                'Perpustakaan',
            ]
            for loc_name in default_locations:
                location = Location(name=loc_name)
                db.session.add(location)
            print(f"Created {len(default_locations)} default locations")

        db.session.commit()
        print("Database initialized successfully!")


from app.routes import *  # noqa: E402,F401 - register routes after app is created

if __name__ == '__main__':
    init_db()
    app.run(debug=True)