from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'kunci_rahasia_untuk_pengembangan'

# --- KONFIGURASI DATABASE & UPLOAD --- 
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'img', 'covers')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'perpustakaan.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- KONFIGURASI FLASK-LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Halaman yang dituju jika user belum login
login_manager.login_message = "Silakan login untuk mengakses halaman ini."
login_manager.login_message_category = "warning"

# --- MODEL DATABASE ---
class Buku(db.Model):
    id = db.Column(db.String(10), primary_key=True)
    judul = db.Column(db.String(200), nullable=False)
    penulis = db.Column(db.String(100), nullable=False)
    isbn = db.Column(db.String(20), unique=True, nullable=False)
    kategori = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Tersedia')
    deskripsi = db.Column(db.Text, nullable=True)
    cover = db.Column(db.String(100), nullable=True) # Menyimpan nama file cover

    def __repr__(self):
        return f'<Buku {self.judul}>'

class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

# Buat satu pengguna admin. Di aplikasi nyata, ini akan disimpan di database.
# Passwordnya adalah 'admin'
users = {
    '1': User(id='1', username='admin', password=generate_password_hash('admin', method='pbkdf2:sha256'))
}

@login_manager.user_loader
def load_user(user_id):
    return users.get(user_id)




db_anggota = [
     {'id': 'M001', 'nama': 'Budi Santoso'},
    {'id': 'M002', 'nama': 'Siti Aminah'},
    {'id': 'M003', 'nama': 'Andi Wijaya'},
    {'id': 'M004', 'nama': 'Dewi Lestari'},
    {'id': 'M005', 'nama': 'Joko Susilo'}
]
db_transaksi = []

# --- HALAMAN-HALAMAN UTAMA ---

@app.route('/')
def index():
    total_buku = Buku.query.count()
    buku_tersedia_count = Buku.query.filter_by(status='Tersedia').count()
    list_buku_tersedia = Buku.query.filter_by(status='Tersedia').limit(5).all()

    # Kumpulkan detail buku yang sedang dipinjam berdasarkan status di db_buku
    list_buku_dipinjam_obj = Buku.query.filter_by(status='Dipinjam').all()
    list_buku_dipinjam_detail = []
    for buku in list_buku_dipinjam_obj:
        # Cari transaksi aktif untuk buku ini
        transaksi = next((t for t in reversed(db_transaksi) if t['buku_id'] == buku['id'] and t['tanggal_kembali'] is None), None)
        peminjam_info = "Informasi Peminjam Tidak Tersedia"
        tanggal_info = "-"
        if transaksi:
            anggota = next((a for a in db_anggota if a['id'] == transaksi['anggota_id']), None)
            if anggota:
                peminjam_info = anggota['nama']
                tanggal_info = transaksi['tanggal_pinjam']
        
        list_buku_dipinjam_detail.append({
            'judul': buku.judul,
            'peminjam': peminjam_info,
            'tanggal_pinjam': tanggal_info
        })

    stats = {
        'total_buku': total_buku,
        'tersedia': buku_tersedia_count,
        'dipinjam': len(list_buku_dipinjam_obj) # Sumber kebenaran adalah jumlah buku berstatus 'Dipinjam'
    }
    return render_template(
        'index.html', 
        stats=stats, 
        list_buku_tersedia=list_buku_tersedia,
        list_buku_dipinjam=list_buku_dipinjam_detail
    )

@app.route('/buku/detail/<id>')
def detail_buku(id):
    book = Buku.query.get_or_404(id)
    return render_template('detail_buku.html', book=book)

@app.route('/buku')
def daftar_buku():
    books = Buku.query.order_by(Buku.judul).all()
    # Ekstrak kategori unik untuk filter dropdown
    categories = sorted(list(set(b.kategori for b in books)))
    return render_template('buku.html', books=books, categories=categories)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Cari user berdasarkan username. Karena kita hanya punya satu, kita bisa langsung cek.
        user = next((u for u in users.values() if u.username == username), None)

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login berhasil!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Username atau password salah.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Anda telah berhasil logout.', 'info')
    return redirect(url_for('login'))

@app.route('/buku/tambah', methods=['GET', 'POST'])
@login_required
def tambah_buku():
    if request.method == 'POST':
        cover_filename = None
        # Cek jika ada file di request
        if 'cover' in request.files:
            file = request.files['cover']
            # Jika user memilih file dan file tersebut valid
            if file and file.filename != '' and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']:
                filename = secure_filename(file.filename)
                # Pastikan direktori upload ada
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                cover_filename = filename

        try:
            last_book = Buku.query.order_by(Buku.id.desc()).first()
            if last_book:
                last_id_num = int(last_book.id.replace('BK', ''))
                new_id_num = last_id_num + 1
            else:
                new_id_num = 1
            new_id = f"BK{new_id_num:03d}"

            buku_baru = Buku(
                id=new_id,
                judul=request.form['judul'],
                penulis=request.form['penulis'],
                isbn=request.form['isbn'],
                kategori=request.form['kategori'],
                deskripsi=request.form.get('deskripsi', ''),
                status='Tersedia',
                cover=cover_filename # Simpan nama file atau None
            )
            db.session.add(buku_baru)
            db.session.commit()
            flash('Buku berhasil ditambahkan!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"Gagal menambahkan buku. Error: {e}", 'danger')
        return redirect(url_for('daftar_buku'))
    return render_template('tambah_buku.html')

@app.route('/buku/edit/<id>', methods=['GET', 'POST'])
@login_required
def edit_buku(id):
    book = Buku.query.get_or_404(id)
    if request.method == 'POST':
        # Perbarui detail dari form
        book.judul = request.form['judul']
        book.penulis = request.form['penulis']
        book.isbn = request.form['isbn']
        book.kategori = request.form['kategori']
        book.deskripsi = request.form.get('deskripsi', '')

        # Cek jika ada file sampul baru yang diunggah
        if 'cover' in request.files:
            file = request.files['cover']
            if file and file.filename != '':
                if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']:
                    # Hapus cover lama jika ada
                    if book.cover:
                        old_cover_path = os.path.join(app.config['UPLOAD_FOLDER'], book.cover)
                        if os.path.exists(old_cover_path):
                            os.remove(old_cover_path)
                    
                    # Simpan cover baru
                    filename = secure_filename(file.filename)
                    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    book.cover = filename

        try:
            db.session.commit()
            flash('Data buku berhasil diperbarui!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Gagal memperbarui data. Error: {e}', 'danger')
        
        return redirect(url_for('detail_buku', id=book.id))

    return render_template('edit_buku.html', book=book)


@app.route('/peminjaman', methods=['GET', 'POST'])
@login_required
def peminjaman():
    if request.method == 'POST':
        buku_id = request.form['buku_id']
        anggota_id = request.form['anggota_id']

        # Cari buku dan ubah statusnya
        buku = Buku.query.get(buku_id)
        if buku and buku.status == 'Tersedia':
            buku.status = 'Dipinjam'

            # Buat catatan transaksi baru
            transaksi_baru = {
                'id': f"TR{len(db_transaksi)+1:03d}",
                'buku_id': buku_id,
                'anggota_id': anggota_id,
                'tanggal_pinjam': datetime.now().strftime("%Y-%m-%d"),
                'tanggal_kembali': None
            }
            db_transaksi.append(transaksi_baru)
            db.session.commit() # Commit perubahan status buku
            flash(f"Buku '{buku.judul}' berhasil dipinjam!", 'success')
        else:
            flash('Buku tidak tersedia atau tidak ditemukan.', 'danger')
        
        return redirect(url_for('daftar_buku'))

    # Untuk GET request, sediakan daftar buku yang tersedia dan anggota
    buku_tersedia = Buku.query.filter_by(status='Tersedia').all()
    return render_template('peminjaman.html', available_books=buku_tersedia, members=db_anggota)

@app.route('/pengembalian', methods=['GET', 'POST'])
@login_required
def pengembalian():
    if request.method == 'POST':
        buku_id = request.form['buku_id']

        # Cari buku dan ubah statusnya
        buku = Buku.query.get(buku_id)
        if buku and buku.status == 'Dipinjam':
            buku.status = 'Tersedia'

            # Cari transaksi yang relevan dan update tanggal kembali
            transaksi = next((t for t in db_transaksi if t['buku_id'] == buku_id and t['tanggal_kembali'] is None), None)
            if transaksi:
                transaksi['tanggal_kembali'] = datetime.now().strftime("%Y-%m-%d")
            
            db.session.commit() # Commit perubahan status buku
            flash(f"Buku '{buku.judul}' telah berhasil dikembalikan!", 'success')
        else:
            flash('Buku tidak sedang dipinjam atau tidak ditemukan.', 'danger')
        
        return redirect(url_for('daftar_buku'))

    # Untuk GET request, sediakan daftar buku yang sedang dipinjam
    buku_dipinjam = Buku.query.filter_by(status='Dipinjam').all()
    return render_template('pengembalian.html', borrowed_books=buku_dipinjam)

@app.route('/kontak', methods=['GET', 'POST'])
def kontak():
    if request.method == 'POST':
        # Dalam aplikasi nyata, di sini Anda akan memproses data formulir (misalnya, mengirim email)
        nama = request.form['nama']
        flash(f'Terima kasih, {nama}. Pesan Anda telah kami terima!', 'success')
        return redirect(url_for('kontak'))
    return render_template('kontak.html')

@app.route('/admin/reset-db')
@login_required
def reset_database():
    try:
        # Hapus semua tabel dari database
        db.drop_all()
        # Buat kembali semua tabel
        db.create_all()
        # Panggil init_db untuk membuat ulang tabel dan mengisi data awal
        init_db()
        flash('Database berhasil direset ke kondisi awal!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal mereset database: {e}', 'danger')
    return redirect(url_for('index'))

@app.route('/transaksi')
@login_required
def riwayat_transaksi():
    transaksi_lengkap = []
    # Urutkan transaksi dari yang terbaru ke terlama
    for t in sorted(db_transaksi, key=lambda x: x['id'], reverse=True):
        buku = Buku.query.get(t['buku_id'])
        anggota = next((a for a in db_anggota if a['id'] == t['anggota_id']), None)
        transaksi_lengkap.append({
            'id': t['id'],
            'judul_buku': buku.judul if buku else 'Buku Tidak Ditemukan',
            'nama_anggota': anggota['nama'] if anggota else 'Anggota Tidak Ditemukan',
            'tanggal_pinjam': t['tanggal_pinjam'],
            'tanggal_kembali': t['tanggal_kembali']
        })
    return render_template('transaksi.html', transactions=transaksi_lengkap)

def init_db():
    with app.app_context():
        db.create_all()
        if not Buku.query.first(): # Hanya isi jika database kosong
            initial_books = [
                {'id': 'BK001', 'judul': 'Filosofi Teras', 'penulis': 'Henry Manampiring', 'isbn': '978-602-03-3453-2', 'kategori': 'Filsafat', 'status': 'Tersedia', 'deskripsi': 'Sebuah pengantar praktis untuk filsafat Stoisisme yang relevan dengan kehidupan modern untuk mengatasi emosi negatif.'},
                {'id': 'BK002', 'judul': 'Laskar Pelangi', 'penulis': 'Andrea Hirata', 'isbn': '978-979-3062-79-2', 'kategori': 'Novel', 'status': 'Tersedia', 'deskripsi': 'Kisah inspiratif tentang perjuangan 10 anak dari keluarga miskin yang bersekolah di sebuah sekolah Muhammadiyah di Belitung.', 'cover': 'laskar pelangi.jpg'},
                {'id': 'BK003', 'judul': 'Bumi Manusia', 'penulis': 'Pramoedya Ananta Toer', 'isbn': '978-979-97312-3-4', 'kategori': 'Sejarah', 'status': 'Dipinjam', 'deskripsi': 'Bagian pertama dari Tetralogi Buru, novel ini menceritakan kisah Minke, seorang pemuda pribumi di era kolonial Belanda.'},
                {'id': 'BK004', 'judul': 'Sapiens: Riwayat Singkat Umat Manusia', 'penulis': 'Yuval Noah Harari', 'isbn': '978-602-424-416-3', 'kategori': 'Sains', 'status': 'Tersedia', 'deskripsi': 'Menjelajahi sejarah umat manusia dari zaman batu hingga era modern, mempertanyakan apa artinya menjadi manusia.'},
                {'id': 'BK005', 'judul': 'Atomic Habits', 'penulis': 'James Clear', 'isbn': '978-0735211292', 'kategori': 'Pengembangan Diri', 'status': 'Tersedia', 'deskripsi': 'Panduan praktis untuk membangun kebiasaan baik dan menghilangkan kebiasaan buruk melalui perubahan kecil yang konsisten.'},
            ]
            for book_data in initial_books:
                new_book = Buku(**book_data)
                db.session.add(new_book)
            db.session.commit()
            print("Database diinisialisasi dengan data awal.")

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)
