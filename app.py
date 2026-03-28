import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
import hashlib

# PENGATURAN HALAMAN
st.set_page_config(page_title="Sistem Deadline Pesanan", page_icon="📦", layout="wide")

# Pilihan status dan prioritas
PILIHAN_STATUS    = ["Belum", "Proses", "Selesai", "Terlambat"]
PILIHAN_PRIORITAS = ["Tinggi", "Normal", "Rendah"]

# Warna untuk status
WARNA_STATUS = {
    "Belum"    : "#95a5a6",  # abu
    "Proses"   : "#f39c12",  # oranye
    "Selesai"  : "#2ecc71",  # hijau
    "Terlambat": "#e74c3c",  # merah 
    }

# Warna untuk prioritas
WARNA_PRIORITAS = {
    "Tinggi": "#e74c3c",  # merah
    "Normal": "#3498db",  # biru
    "Rendah": "#95a5a6",  # abu
    }

ADMIN_USERNAME      = "admin"
ADMIN_PASSWORD = "admin123"

# DATABASE
@st.cache_resource
def buat_koneksi():
    """Buat koneksi ke database dan buat tabel jika belum ada."""
    conn = sqlite3.connect("pesanan.db", check_same_thread=False)
    conn.executescript("""CREATE TABLE IF NOT EXISTS pesanan (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_pelanggan TEXT NOT NULL,
            nama_pesanan   TEXT NOT NULL,
            deadline       TEXT NOT NULL,
            prioritas      TEXT NOT NULL DEFAULT 'Normal',
            status         TEXT NOT NULL DEFAULT 'Belum',
            dibuat         TEXT NOT NULL); """)
    conn.commit()
    return conn


def jalankan(sql, params=()):
    """Jalankan perintah SQL yang mengubah data."""
    conn = buat_koneksi()
    conn.execute(sql, params)
    conn.commit()


def ambil_data(sql, params=()):
    """Ambil data dari database, kembalikan sebagai list of dict."""
    conn = buat_koneksi()
    conn.row_factory = sqlite3.Row
    hasil = conn.execute(sql, params).fetchall()
    return [dict(baris) for baris in hasil]

# FUNGSI PESANAN
def ambil_semua_pesanan():
    return ambil_data("SELECT * FROM pesanan ORDER BY deadline ASC")

def tambah_pesanan(nama_pelanggan, nama_pesanan, deadline, prioritas):
    jalankan(
        "INSERT INTO pesanan (nama_pelanggan, nama_pesanan, deadline, prioritas, status, dibuat) VALUES (?,?,?,?,?,?)",
        (nama_pelanggan, nama_pesanan, deadline, prioritas, "Belum", date.today().isoformat()))

def ubah_pesanan(id_pesanan, nama_pelanggan, nama_pesanan, deadline, prioritas, status):
    jalankan(
        "UPDATE pesanan SET nama_pelanggan=?, nama_pesanan=?, deadline=?, prioritas=?, status=? WHERE id=?",
        (nama_pelanggan, nama_pesanan, deadline, prioritas, status, id_pesanan) )

def hapus_pesanan(id_pesanan):
    jalankan("DELETE FROM pesanan WHERE id=?", (id_pesanan,))

def update_status(id_pesanan, status_baru):
    jalankan("UPDATE pesanan SET status=? WHERE id=?", (status_baru, id_pesanan))

def perbarui_status_terlambat():
    """Otomatis ubah status jadi Terlambat jika deadline sudah lewat dan masih Proses."""
    hari_ini = date.today().isoformat()
    jalankan("UPDATE pesanan SET status='Terlambat' WHERE status='Proses' AND deadline < ?",(hari_ini,))

# SESSION STATE
if "is_admin"   not in st.session_state:
    st.session_state.is_admin  = False
if "edit_id" not in st.session_state:
    st.session_state.edit_id = None
if "filter_status" not in st.session_state:
    st.session_state.filter_status = "Semua"

# JALANKAN PENGECEKAN OTOMATIS TERLAMBAT
perbarui_status_terlambat()

# AMBIL DATA & HITUNG STATISTIK
semua_pesanan = ambil_semua_pesanan()
hari_ini      = date.today()

total_pesanan   = len(semua_pesanan)
total_belum     = sum(1 for p in semua_pesanan if p["status"] == "Belum")
total_proses    = sum(1 for p in semua_pesanan if p["status"] == "Proses")
total_selesai   = sum(1 for p in semua_pesanan if p["status"] == "Selesai")
total_terlambat = sum(1 for p in semua_pesanan if p["status"] == "Terlambat")

# Pesanan yang deadlinenya <= 3 hari lagi dan masih Proses atau Belum
akan_terlambat = [
    p for p in semua_pesanan
    if p["status"] in ("Proses", "Belum")
    and (date.fromisoformat(p["deadline"]) - hari_ini).days <= 3
    and (date.fromisoformat(p["deadline"]) - hari_ini).days >= 0]

# TAMPILAN - JUDUL
st.title("📦 Sistem Deadline Pesanan")
st.caption("Kelola dan pantau deadline pesanan pelanggan Anda")
st.divider()

# TAMPILAN - NOTIFIKASI PERINGATAN
if akan_terlambat:
    st.warning(f"⚠️ **{len(akan_terlambat)} pesanan** mendekati deadline!")
    with st.expander("Lihat pesanan yang mendekati deadline"):
        for p in akan_terlambat:
            dl    = date.fromisoformat(p["deadline"])
            sisa  = (dl - hari_ini).days
            label = "Hari ini!" if sisa == 0 else f"{sisa} hari lagi"
            st.write(f"{p['nama_pelanggan']} — {p['nama_pesanan']} — Deadline: {dl.strftime('%d %b %Y')} ({label})")

# TAMPILAN - STATISTIK
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Pesanan",  total_pesanan)
k2.metric("Belum Dimulai",  total_belum)
k3.metric("Sedang Proses",  total_proses)
k4.metric("Selesai",        total_selesai)
k5.metric("Terlambat",      total_terlambat)

st.divider()

# TAMPILAN - LAYOUT UTAMA
kolom_kiri, kolom_kanan = st.columns([1, 2], gap="large")

# KOLOM KIRI - Form Tambah / Edit Pesanan
with st.sidebar:
    st.header("Panel Admin")
 
    if st.session_state.is_admin:
        st.success(f"Login sebagai **{ADMIN_USERNAME}**")
        if st.button("Logout", use_container_width=True):
            st.session_state.is_admin = False
            st.session_state.edit_id  = None
            st.rerun()

    else:
        st.info("Login sebagai admin untuk mengelola pesanan.")
        with st.form("form_login"):
            username = st.text_input("Username")
            password = st.text_input("Sandi", type="password")
            masuk    = st.form_submit_button("🔑 Masuk", use_container_width=True)
            if masuk:
                if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                    st.session_state.is_admin = True
                    st.success("Login berhasil!")
                    st.rerun()
                else:
                    st.error("Username atau sandi salah.")

    st.divider()
    st.caption("📦 Sistem Deadline Pesanan")
    st.caption(f"Hari ini: {hari_ini.strftime('%d %b %Y')}")


with kolom_kiri:

    if st.session_state.is_admin:
            pesanan_diedit = next(
                (p for p in semua_pesanan if p["id"] == st.session_state.edit_id),
                None)

            pesanan_diedit = None

            for p in semua_pesanan:
                if p["id"] == st.session_state.edit_id:
                    pesanan_diedit = p
                    break

        # pesanan_diedit = next((p for p in semua_pesanan if p["id"] == st.session_state.edit_id), None)
            
            judul_form = "Edit Pesanan" if pesanan_diedit else "Tambah Pesanan Baru"
            st.subheader(judul_form)

            with st.form("form_pesanan", clear_on_submit=True):

                nama_pelanggan = st.text_input("Nama Pelanggan", value=pesanan_diedit["nama_pelanggan"] 
                                            if pesanan_diedit else "", placeholder="Contoh: Budi Santoso")

                nama_pesanan = st.text_input("Nama / Deskripsi Pesanan", value=pesanan_diedit["nama_pesanan"] 
                                            if pesanan_diedit else "", placeholder="Contoh: 3 meja 2 kursi")

                deadline = st.date_input("Tanggal Deadline", value=date.fromisoformat(pesanan_diedit["deadline"]) 
                                        if pesanan_diedit else hari_ini, min_value=hari_ini if not pesanan_diedit else date(2020, 1, 1))

                prioritas = st.selectbox("Prioritas", PILIHAN_PRIORITAS, index=PILIHAN_PRIORITAS.index(pesanan_diedit["prioritas"]) 
                                        if pesanan_diedit else 1)

                # Status hanya tampil saat edit
                if pesanan_diedit:
                    status = st.selectbox("Status", PILIHAN_STATUS, index=PILIHAN_STATUS.index(pesanan_diedit["status"]))
                else:
                    status = "Belum"  

                label_tombol = "Simpan Perubahan" if pesanan_diedit else "Tambah Pesanan"
                kirim = st.form_submit_button(label_tombol, use_container_width=True)

                if kirim:
                    if not nama_pelanggan.strip():
                        st.error("Nama pelanggan wajib diisi!")
                    elif not nama_pesanan.strip():
                        st.error("Nama pesanan wajib diisi!")
                    else:
                        if pesanan_diedit:
                            ubah_pesanan(
                                st.session_state.edit_id,
                                nama_pelanggan.strip(),
                                nama_pesanan.strip(),
                                deadline.isoformat(),
                                prioritas,
                                status)
                            st.success("Pesanan berhasil diperbarui!")
                            st.session_state.edit_id = None
                        else:
                            tambah_pesanan(
                                nama_pelanggan.strip(),
                                nama_pesanan.strip(),
                                deadline.isoformat(),
                                prioritas)
                            st.success(f"Pesanan '{nama_pesanan}' berhasil ditambahkan!")
                        st.rerun()

            if pesanan_diedit:
                if st.button("✕ Batal Edit", use_container_width=True):
                    st.session_state.edit_id = None
                    st.rerun()

    else:
        # Tampilan untuk pengunjung (bukan admin)
        st.subheader("🔒 Area Admin")
        st.info(
            "Silakan **login sebagai admin** melalui panel di sebelah kiri "
            "untuk menambah atau mengedit pesanan."
        )
        st.markdown("""
            **Sebagai pengunjung, Anda tetap bisa:**
            - Melihat seluruh daftar pesanan
            - Memfilter pesanan berdasarkan status
            - Melihat ringkasan tabel""")

# KOLOM KANAN - Daftar Pesanan
with kolom_kanan:
    st.subheader("Daftar Pesanan")

    filter_dipilih = st.segmented_control(
        "Filter Status",
        options=["Semua", "Belum", "Proses", "Selesai", "Terlambat"],
        default="Semua",
        key="filter_status_ctrl")

    if filter_dipilih and filter_dipilih != "Semua":
        pesanan_tampil = [p for p in semua_pesanan if p["status"] == filter_dipilih]
    else:
        pesanan_tampil = semua_pesanan

    if not pesanan_tampil:
        st.info("Tidak ada pesanan untuk ditampilkan.")
    else:
        for p in pesanan_tampil:
            dl       = date.fromisoformat(p["deadline"])
            sisa     = (dl - hari_ini).days
            warna_s  = WARNA_STATUS.get(p["status"], "#999")
            warna_pr = WARNA_PRIORITAS.get(p["prioritas"], "#999")

            if p["status"] == "Selesai":
                label_sisa = "Selesai"
            elif sisa < 0:
                label_sisa = f"Terlambat {abs(sisa)} hari"
            elif sisa == 0:
                label_sisa = "Deadline hari ini!"
            elif sisa <= 3:
                label_sisa = f"⚠️ {sisa} hari lagi"
            else:
                label_sisa = f"{sisa} hari lagi"

            with st.container(border=True):
                baris1, baris2 = st.columns([4, 2])

                with baris1:
                    st.caption(f"👤 {p['nama_pelanggan']}")
                    st.markdown(f"**{p['nama_pesanan']}**")
                    st.markdown(
                        f'<span style="background:{warna_s};color:white;padding:2px 8px;border-radius:4px;font-size:12px">{p["status"]}</span>'
                        f'&nbsp;&nbsp;'
                        f'<span style="background:{warna_pr};color:white;padding:2px 8px;border-radius:4px;font-size:12px">{p["prioritas"]}</span>',
                        unsafe_allow_html=True)

                with baris2:
                    st.markdown(f"🗓️ **{dl.strftime('%d %b %Y')}**")
                    st.caption(label_sisa)

                if st.session_state.is_admin:
                    ak1, ak2, ak3, ak4, ak5 = st.columns(5)

                    # Mulai Proses (hanya jika status Belum)
                    if p["status"] == "Belum":
                        if ak1.button("Proses", key=f"proses_{p['id']}"):
                            update_status(p["id"], "Proses")
                            st.rerun()

                    # Tandai Selesai (jika belum selesai)
                    if p["status"] != "Selesai":
                        if ak2.button("Selesai", key=f"selesai_{p['id']}"):
                            update_status(p["id"], "Selesai")
                            st.rerun()

                    # Kembalikan ke Belum (jika Selesai atau Terlambat)
                    if p["status"] in ["Selesai", "Terlambat"]:
                        if ak3.button("Belum", key=f"belum_{p['id']}"):
                            update_status(p["id"], "Belum")
                            st.rerun()

                    if ak4.button("Edit", key=f"edit_{p['id']}"):
                        st.session_state.edit_id = p["id"]
                        st.rerun()

                    if ak5.button("Hapus", key=f"hapus_{p['id']}"):
                        hapus_pesanan(p["id"])
                        st.success("Pesanan dihapus.")
                        st.rerun()

                else:
                    st.caption("🔒 Login sebagai admin untuk mengelola pesanan ini.")

    st.divider()
    st.subheader("Ringkasan Tabel")

    if semua_pesanan:
        df = pd.DataFrame(semua_pesanan)[["nama_pelanggan", "nama_pesanan", "deadline", "prioritas", "status", "dibuat"]]
        df.columns = ["Pelanggan", "Pesanan", "Deadline", "Prioritas", "Status", "Dibuat"]
        df["Deadline"] = pd.to_datetime(df["Deadline"]).dt.strftime("%d %b %Y")
        df["Dibuat"]   = pd.to_datetime(df["Dibuat"]).dt.strftime("%d %b %Y")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada data pesanan.")