from datetime import datetime

from flask import render_template, request, redirect, url_for, session, flash

from app.app import app, allowed_file, generate_asset_code, generate_qr_code, login_required
from app.extensions import db
from app.models import User, Location, Category, Asset, QRCode, AssetPhoto, AssetHistory


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Username dan password tidak boleh kosong', 'danger')
            return render_template('login.html')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash(f'Selamat datang, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Username atau password salah', 'danger')
            return render_template('login.html')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah logout', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    total_assets = Asset.query.count()
    total_categories = Category.query.count()
    total_qr_generated = QRCode.query.count()

    today = datetime.utcnow().date()
    today_activities = AssetHistory.query.filter(
        db.func.date(AssetHistory.timestamp) == today
    ).count()

    recent_activities = AssetHistory.query.order_by(
        AssetHistory.timestamp.desc()
    ).limit(10).all()

    return render_template(
        'dashboard.html',
        total_assets=total_assets,
        total_categories=total_categories,
        total_qr_generated=total_qr_generated,
        today_activities=today_activities,
        recent_activities=recent_activities,
    )


@app.route('/aset')
@login_required
def aset_list():
    category_filter = request.args.get('category', '')
    location_filter = request.args.get('location', '')
    condition_filter = request.args.get('condition', '')
    search_query = request.args.get('search', '')

    query = Asset.query

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
                Asset.asset_code.like(search_pattern),
            )
        )

    assets = query.order_by(Asset.created_at.desc()).all()

    categories = Category.query.order_by(Category.name).all()
    locations = Location.query.order_by(Location.name).all()

    return render_template(
        'aset/list.html',
        assets=assets,
        categories=categories,
        locations=locations,
        category_filter=category_filter,
        location_filter=location_filter,
        condition_filter=condition_filter,
        search_query=search_query,
    )


@app.route('/aset/detail/<int:id>')
@login_required
def aset_detail(id):
    asset = Asset.query.get_or_404(id)

    history = AssetHistory.query.filter_by(asset_id=id).order_by(
        AssetHistory.timestamp.desc()
    ).all()

    return render_template('aset/detail.html', asset=asset, history=history)


@app.route('/aset/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def aset_edit(id):
    asset = Asset.query.get_or_404(id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category_id = request.form.get('category_id')
        location_id = request.form.get('location_id')
        condition = request.form.get('condition', '').strip()
        description = request.form.get('description', '').strip()

        if not name:
            flash('Nama aset tidak boleh kosong', 'danger')
            return redirect(url_for('aset_edit', id=id))

        if not category_id:
            flash('Kategori harus dipilih', 'danger')
            return redirect(url_for('aset_edit', id=id))

        if not location_id:
            flash('Lokasi harus dipilih', 'danger')
            return redirect(url_for('aset_edit', id=id))

        changes = []
        if asset.name != name:
            changes.append(f"nama: '{asset.name}' → '{name}'")
            asset.name = name

        if str(asset.category_id) != category_id:
            old_cat = asset.category.name
            new_cat = Category.query.get(category_id).name
            changes.append(f"kategori: '{old_cat}' → '{new_cat}'")
            asset.category_id = category_id

        if str(asset.location_id) != location_id:
            old_loc = asset.location.name
            new_loc = Location.query.get(location_id).name
            changes.append(f"lokasi: '{old_loc}' → '{new_loc}'")
            asset.location_id = location_id

        if asset.condition != condition:
            changes.append(f"kondisi: '{asset.condition}' → '{condition}'")
            asset.condition = condition

        if asset.description != description:
            changes.append('deskripsi diperbarui')
            asset.description = description

        asset.updated_at = datetime.utcnow()

        if 'photo' in request.files:
            photo = request.files['photo']
            if photo and photo.filename and allowed_file(photo.filename):
                import uuid

                ext = photo.filename.rsplit('.', 1)[1].lower()
                filename = f"{asset.asset_code}_{uuid.uuid4().hex[:8]}.{ext}"
                filepath = app.config['UPLOAD_FOLDER'] + '/photos/' + filename

                from os import path

                photo.save(filepath)

                asset_photo = AssetPhoto(
                    asset_id=asset.id,
                    file_path=f"uploads/photos/{filename}",
                )
                db.session.add(asset_photo)
                changes.append('foto baru ditambahkan')

        if changes:
            change_desc = ', '.join(changes)
            history = AssetHistory(
                asset_id=asset.id,
                user_id=session['user_id'],
                action='EDIT',
                description=f'Mengubah aset {asset.asset_code}: {change_desc}',
            )
            db.session.add(history)

        db.session.commit()

        flash(f'Aset "{name}" berhasil diperbarui', 'success')
        return redirect(url_for('aset_detail', id=id))

    categories = Category.query.order_by(Category.name).all()
    locations = Location.query.order_by(Location.name).all()

    return render_template(
        'aset/edit.html', asset=asset, categories=categories, locations=locations
    )


@app.route('/aset/hapus/<int:id>', methods=['POST'])
@login_required
def aset_hapus(id):
    import os

    asset = Asset.query.get_or_404(id)
    asset_name = asset.name
    asset_code = asset.asset_code

    for photo in asset.photos:
        photo_path = os.path.join('app/static', photo.file_path)
        if os.path.exists(photo_path):
            os.remove(photo_path)
        db.session.delete(photo)

    for qr in asset.qr_codes:
        qr_path = os.path.join('app/static', qr.file_path)
        if os.path.exists(qr_path):
            os.remove(qr_path)
        db.session.delete(qr)

    AssetHistory.query.filter_by(asset_id=id).delete()

    history = AssetHistory(
        user_id=session['user_id'],
        action='DELETE',
        description=f'Menghapus aset: {asset_name} ({asset_code})',
    )
    db.session.add(history)

    db.session.delete(asset)
    db.session.commit()

    flash(f'Aset "{asset_name}" ({asset_code}) berhasil dihapus', 'success')
    return redirect(url_for('aset_list'))


@app.route('/aset/foto/hapus/<int:id>', methods=['POST'])
@login_required
def aset_foto_hapus(id):
    import os

    photo = AssetPhoto.query.get_or_404(id)
    asset_id = photo.asset_id
    asset = photo.asset

    photo_path = os.path.join('app/static', photo.file_path)
    if os.path.exists(photo_path):
        os.remove(photo_path)

    db.session.delete(photo)

    history = AssetHistory(
        asset_id=asset_id,
        user_id=session['user_id'],
        action='DELETE_PHOTO',
        description=f'Menghapus foto dari aset {asset.asset_code}',
    )
    db.session.add(history)

    db.session.commit()

    flash('Foto berhasil dihapus', 'success')
    return redirect(url_for('aset_detail', id=asset_id))


@app.route('/aset/qr/generate/<int:id>', methods=['POST'])
@login_required
def qr_generate(id):
    asset = Asset.query.get_or_404(id)

    existing_qr = QRCode.query.filter_by(asset_id=id).first()
    if existing_qr:
        flash('QR Code sudah ada. Gunakan "Regenerate" untuk membuat ulang.', 'warning')
        return redirect(url_for('aset_detail', id=id))

    qr_path, qr_value = generate_qr_code(asset)

    qr_code = QRCode(asset_id=asset.id, file_path=qr_path, qr_value=qr_value)
    db.session.add(qr_code)

    history = AssetHistory(
        asset_id=asset.id,
        user_id=session['user_id'],
        action='GENERATE_QR',
        description=f'Generate QR Code untuk aset {asset.asset_code}',
    )
    db.session.add(history)

    db.session.commit()

    flash('QR Code berhasil di-generate', 'success')
    return redirect(url_for('aset_detail', id=id))


@app.route('/aset/qr/regenerate/<int:id>', methods=['POST'])
@login_required
def qr_regenerate(id):
    import os

    asset = Asset.query.get_or_404(id)

    old_qrs = QRCode.query.filter_by(asset_id=id).all()
    for old_qr in old_qrs:
        qr_path = os.path.join('app/static', old_qr.file_path)
        if os.path.exists(qr_path):
            os.remove(qr_path)
        db.session.delete(old_qr)

    qr_path, qr_value = generate_qr_code(asset)

    qr_code = QRCode(asset_id=asset.id, file_path=qr_path, qr_value=qr_value)
    db.session.add(qr_code)

    history = AssetHistory(
        asset_id=asset.id,
        user_id=session['user_id'],
        action='REGENERATE_QR',
        description=f'Regenerate QR Code untuk aset {asset.asset_code}',
    )
    db.session.add(history)

    db.session.commit()

    flash('QR Code berhasil di-regenerate', 'success')
    return redirect(url_for('aset_detail', id=id))


@app.route('/scan')
@login_required
def scan_qr():
    return render_template('scan/qr_scanner.html')


@app.route('/public/aset/<int:id>')
def public_aset_detail(id):
    asset = Asset.query.get_or_404(id)
    return render_template('public/aset_detail.html', asset=asset)


@app.route('/aset/tambah', methods=['GET', 'POST'])
@login_required
def aset_tambah():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category_id = request.form.get('category_id')
        location_id = request.form.get('location_id')
        condition = request.form.get('condition', '').strip()
        description = request.form.get('description', '').strip()

        if not name:
            flash('Nama aset tidak boleh kosong', 'danger')
            return redirect(url_for('aset_tambah'))

        if not category_id:
            flash('Kategori harus dipilih', 'danger')
            return redirect(url_for('aset_tambah'))

        if not location_id:
            flash('Lokasi harus dipilih', 'danger')
            return redirect(url_for('aset_tambah'))

        asset_code = generate_asset_code()

        asset = Asset(
            asset_code=asset_code,
            name=name,
            category_id=category_id,
            location_id=location_id,
            condition=condition,
            description=description,
        )

        db.session.add(asset)
        db.session.flush()

        if 'photo' in request.files:
            photo = request.files['photo']
            if photo and photo.filename and allowed_file(photo.filename):
                import uuid

                ext = photo.filename.rsplit('.', 1)[1].lower()
                filename = f"{asset.asset_code}_{uuid.uuid4().hex[:8]}.{ext}"
                filepath = app.config['UPLOAD_FOLDER'] + '/photos/' + filename

                from os import path

                photo.save(filepath)

                asset_photo = AssetPhoto(
                    asset_id=asset.id,
                    file_path=f"uploads/photos/{filename}",
                )
                db.session.add(asset_photo)

        qr_path, qr_value = generate_qr_code(asset)
        qr_code = QRCode(asset_id=asset.id, file_path=qr_path, qr_value=qr_value)
        db.session.add(qr_code)

        history = AssetHistory(
            asset_id=asset.id,
            user_id=session['user_id'],
            action='ADD',
            description=f'Menambahkan aset: {name} ({asset_code})',
        )
        db.session.add(history)

        db.session.commit()

        flash(
            f'Aset "{name}" berhasil ditambahkan dengan kode {asset_code}',
            'success',
        )
        return redirect(url_for('aset_list'))

    categories = Category.query.order_by(Category.name).all()
    locations = Location.query.order_by(Location.name).all()

    return render_template(
        'aset/tambah.html', categories=categories, locations=locations
    )


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

    existing = Category.query.filter_by(name=name).first()
    if existing:
        flash('Nama kategori sudah digunakan', 'danger')
        return redirect(url_for('kategori_list'))

    category = Category(name=name)
    db.session.add(category)

    history = AssetHistory(
        user_id=session['user_id'],
        action='ADD_CATEGORY',
        description=f'Menambahkan kategori: {name}',
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

    existing = Category.query.filter(
        Category.name == name, Category.id != id
    ).first()
    if existing:
        flash('Nama kategori sudah digunakan', 'danger')
        return redirect(url_for('kategori_list'))

    old_name = category.name
    category.name = name
    category.updated_at = datetime.utcnow()

    history = AssetHistory(
        user_id=session['user_id'],
        action='EDIT_CATEGORY',
        description=f'Mengubah kategori dari "{old_name}" menjadi "{name}"',
    )
    db.session.add(history)

    db.session.commit()
    flash(f'Kategori berhasil diubah menjadi "{name}"', 'success')
    return redirect(url_for('kategori_list'))


@app.route('/kategori/hapus/<int:id>', methods=['POST'])
@login_required
def kategori_hapus(id):
    category = Category.query.get_or_404(id)

    asset_count = Asset.query.filter_by(category_id=id).count()
    if asset_count > 0:
        flash(
            f'Kategori "{category.name}" tidak dapat dihapus karena masih digunakan oleh {asset_count} aset',
            'danger',
        )
        return redirect(url_for('kategori_list'))

    name = category.name

    history = AssetHistory(
        user_id=session['user_id'],
        action='DELETE_CATEGORY',
        description=f'Menghapus kategori: {name}',
    )
    db.session.add(history)

    db.session.delete(category)
    db.session.commit()

    flash(f'Kategori "{name}" berhasil dihapus', 'success')
    return redirect(url_for('kategori_list'))


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

    existing = Location.query.filter_by(name=name).first()
    if existing:
        flash('Nama lokasi sudah digunakan', 'danger')
        return redirect(url_for('lokasi_list'))

    location = Location(name=name)
    db.session.add(location)

    history = AssetHistory(
        user_id=session['user_id'],
        action='ADD_LOCATION',
        description=f'Menambahkan lokasi: {name}',
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

    existing = Location.query.filter(Location.name == name, Location.id != id).first()
    if existing:
        flash('Nama lokasi sudah digunakan', 'danger')
        return redirect(url_for('lokasi_list'))

    old_name = location.name
    location.name = name
    location.updated_at = datetime.utcnow()

    history = AssetHistory(
        user_id=session['user_id'],
        action='EDIT_LOCATION',
        description=f'Mengubah lokasi dari "{old_name}" menjadi "{name}"',
    )
    db.session.add(history)

    db.session.commit()
    flash(f'Lokasi berhasil diubah menjadi "{name}"', 'success')
    return redirect(url_for('lokasi_list'))


@app.route('/lokasi/hapus/<int:id>', methods=['POST'])
@login_required
def lokasi_hapus(id):
    location = Location.query.get_or_404(id)

    asset_count = Asset.query.filter_by(location_id=id).count()
    if asset_count > 0:
        flash(
            f'Lokasi "{location.name}" tidak dapat dihapus karena masih digunakan oleh {asset_count} aset',
            'danger',
        )
        return redirect(url_for('lokasi_list'))

    name = location.name

    history = AssetHistory(
        user_id=session['user_id'],
        action='DELETE_LOCATION',
        description=f'Menghapus lokasi: {name}',
    )
    db.session.add(history)

    db.session.delete(location)
    db.session.commit()

    flash(f'Lokasi "{name}" berhasil dihapus', 'success')
    return redirect(url_for('lokasi_list'))


@app.route('/riwayat')
@login_required
def riwayat_list():
    user_filter = request.args.get('user', '')
    action_filter = request.args.get('action', '')
    date_filter = request.args.get('date', '')

    query = AssetHistory.query

    if user_filter:
        query = query.filter_by(user_id=user_filter)

    if action_filter:
        query = query.filter_by(action=action_filter)

    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(db.func.date(AssetHistory.timestamp) == filter_date)
        except ValueError:
            pass

    activities = query.order_by(AssetHistory.timestamp.desc()).all()

    users = User.query.order_by(User.username).all()

    actions = (
        db.session.query(AssetHistory.action)
        .distinct()
        .order_by(AssetHistory.action)
        .all()
    )
    actions = [a[0] for a in actions if a[0]]

    return render_template(
        'riwayat/list.html',
        activities=activities,
        users=users,
        actions=actions,
        user_filter=user_filter,
        action_filter=action_filter,
        date_filter=date_filter,
    )
