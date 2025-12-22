# Aplikasi Asset Management (Flask)

Aplikasi ini adalah sistem manajemen aset berbasis web menggunakan Flask + MySQL.

## 1. Prasyarat

- Python 3.9+ (disarankan sama dengan versi yang kamu pakai sekarang)
- MySQL (contoh: XAMPP / Laragon / MySQL Server)
- Git (opsional)

## 2. Clone / Salin Project

Jika dari Git:

```bash
git clone <url-repo>
cd data-asset-management
```

Jika project ini sudah ada di komputer, cukup masuk ke folder project:

```bash
cd data-asset-management
```

## 3. Buat Virtual Environment (opsional tapi disarankan)

Windows (PowerShell):

```bash
python -m venv venv
venv\Scripts\activate
```

Jika sudah aktif, prompt akan berubah menampilkan `(venv)` di depan.

## 4. Install Dependency

Dari root project (folder yang ada `requirements.txt`):

```bash
pip install -r requirements.txt
```

## 5. Konfigurasi Database MySQL

Secara default, aplikasi menggunakan koneksi:

```text
mysql+pymysql://root:@localhost/asset_management
```

Artinya:

- **user**: `root`
- **password**: `password_anda`
- **host**: `localhost`
- **nama database**: `asset_management`

### 5.1. Buat database

Masuk ke MySQL (phpMyAdmin / CLI), kemudian buat database:

```sql
CREATE DATABASE asset_management CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Jika user/password MySQL kamu berbeda, ubah konfigurasi di `app/app.py`:

```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://USER:PASSWORD@HOST/NAMA_DB'
```

## 6. Struktur Backend Singkat

- `run.py` → entry point untuk menjalankan server Flask.
- `app/app.py` → inisialisasi Flask app, konfigurasi, helper, dan registrasi routes.
- `app/extensions.py` → instance `db = SQLAlchemy()`.
- `app/models/` → semua model database (`User`, `Asset`, `Location`, dll).
- `app/routes/` → semua route / endpoint Flask.
- `app/templates/` → file HTML (Jinja2 templates).
- `app/static/` → file statis (CSS, JS, gambar, upload).

## 7. Menjalankan Aplikasi (Development)

Pastikan virtualenv aktif dan dependency sudah ter-install, lalu dari root project jalankan:

```bash
python run.py
```

Secara default, server akan jalan di:

```text
http://127.0.0.1:5000
```

## 8. Inisialisasi Database & User Admin Default

Saat pertama kali dijalankan, aplikasi akan:

- Membuat semua tabel yang dibutuhkan.
- Membuat user admin default jika belum ada:
  - **username**: `admin`
  - **password**: `admin123`
- Menambahkan beberapa lokasi default (Lab, Perpustakaan, dll).

Kamu bisa login ke sistem dengan akun admin tersebut lalu mulai mengelola aset.

## 9. Lokasi File Upload

- Upload disimpan di folder: `app/static/uploads/`
  - Foto aset: `app/static/uploads/photos/`
  - QR code: `app/static/uploads/qrcodes/`

Folder akan otomatis dibuat saat aplikasi dijalankan.

## 10. Catatan Tambahan

- Untuk production, **ganti** nilai `SECRET_KEY` di `app/app.py` dengan nilai yang lebih aman.
- Jangan gunakan password MySQL hard-coded untuk environment production; gunakan environment variable.
- Jika port 5000 bentrok, kamu bisa menjalankan Flask di port lain (misal dengan mengubah cara menjalankan atau memodifikasi `run.py`).
