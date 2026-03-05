import os
import subprocess
import sys
import urllib.request
import urllib.parse
import glob # Modul baru untuk mencari file .zip

# --- MENGAMBIL DATA RAHASIA DARI CIRRUS CI ---
BOT_TOKEN = os.environ.get('TG_BOT_TOKEN')
CHAT_ID = os.environ.get('TG_CHAT_ID')

def kirim_telegram(pesan):
    """Fungsi untuk mengirim pesan ke Telegram Anda"""
    if not BOT_TOKEN or not CHAT_ID:
        print("[Info] Token/Chat ID Telegram tidak diatur. Melewati notifikasi Telegram.")
        return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        'chat_id': CHAT_ID, 
        'text': pesan, 
        'parse_mode': 'HTML'
    }).encode('utf-8')
    
    try:
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"[Error] Gagal mengirim pesan Telegram: {e}")

def jalankan_perintah(perintah, pesan_gagal):
    """Menjalankan perintah terminal dan mengirim log error ke Telegram jika gagal"""
    print(f"\n[INFO] Menjalankan: {perintah}\n" + "="*40)
    
    proses = subprocess.Popen(perintah, shell=True, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
    for baris in proses.stdout:
        print(baris.decode('utf-8').strip())
        
    proses.wait()
    
    if proses.returncode != 0:
        pesan_error = f"❌ <b>BUILD GAGAL!</b>\n\n<b>Tahap:</b> {pesan_gagal}\n<b>Perintah:</b> <code>{perintah}</code>\n\nSilakan cek log di Cirrus CI."
        kirim_telegram(pesan_error)
        sys.exit(1)

def upload_rom(path_file):
    """Fungsi baru: Mengunggah file ke transfer.sh dan mengembalikan link-nya"""
    print(f"\n[INFO] Mengunggah {path_file} ke server. Mohon tunggu, ini mungkin memakan waktu...")
    
    # Perintah curl untuk upload ke transfer.sh
    perintah_upload = f'curl --upload-file "{path_file}" https://transfer.sh/{os.path.basename(path_file)}'
    
    try:
        # Menjalankan perintah dan mengambil outputnya (yang berupa link download)
        hasil = subprocess.check_output(perintah_upload, shell=True, executable='/bin/bash')
        link_download = hasil.decode('utf-8').strip()
        print(f"[INFO] Upload selesai! Link: {link_download}")
        return link_download
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Gagal mengunggah file: {e}")
        return None

def utama():
    # --- VARIABEL ROM ---
    link_manifest = "https://github.com/LineageOS/android.git"
    branch_rom = "lineage-20.0" 
    codename_device = "X00TD"
    
    # --- VARIABEL DEVICE, VENDOR, & KERNEL TREE ---
    # Ganti URL dan branch di bawah ini dengan link repositori X00TD yang Anda gunakan
    repositori_perangkat = [
        {
            "nama": "Device Tree",
            "url": "https://github.com/LineageOS/android_device_asus_X00TD.git", 
            "branch": "lineage-17.1", 
            "path": "device/asus/X00TD"
        },
        {
            "nama": "Vendor Tree",
            "url": "https://github.com/TheMuppets/proprietary_vendor_asus.git", 
            "branch": "lineage-17.1", 
            "path": "vendor/asus"
        },
    ]
    
    kirim_telegram(f"🚀 <b>Mulai Build ROM!</b>\n\n<b>Perangkat:</b> {codename_device}\n<b>ROM:</b> LineageOS ({branch_rom})")

    # 1. Konfigurasi Git
    jalankan_perintah("git config --global user.name 'Bot Cirrus CI'", "Konfigurasi Git Name")
    jalankan_perintah("git config --global user.email 'bot@cirrus.ci'", "Konfigurasi Git Email")

    # 2. Inisialisasi Repo
    jalankan_perintah(f"repo init -u {link_manifest} -b {branch_rom} --depth=1", "Repo Init")

    # 3. Sinkronisasi (Sync) Source Code Dasar
    kirim_telegram("🔄 <b>Status:</b> Memulai sinkronisasi source code utama (Repo Sync)...")
    jalankan_perintah("repo sync -c --no-clone-bundle --no-tags --optimized-fetch --prune --force-sync -j8", "Repo Sync")

    # 4. MENGKLONING DEVICE, VENDOR, & KERNEL TREE (BAGIAN BARU)
    kirim_telegram("📥 <b>Status:</b> Source utama selesai. Mulai mengkloning Device, Vendor, dan Kernel Tree...")
    
    for repo in repositori_perangkat:
        # Menghapus folder lama jika sudah ada (mencegah error saat build ulang)
        jalankan_perintah(f"rm -rf {repo['path']}", f"Membersihkan folder {repo['path']}")
        
        # Mengkloning repositori
        print(f"\n[INFO] Sedang mengkloning {repo['nama']}...")
        perintah_clone = f"git clone --depth=1 -b {repo['branch']} {repo['url']} {repo['path']}"
        jalankan_perintah(perintah_clone, f"Kloning {repo['nama']}")

    # 5. Kompilasi (Build)
    kirim_telegram("⚙️ <b>Status:</b> Semua Tree berhasil dikloning. Memulai kompilasi (brunch)...")
    perintah_build = f"source build/envsetup.sh && brunch {codename_device}"
    jalankan_perintah(perintah_build, "Kompilasi ROM (Brunch)")
    
    # 6. MENCARI DAN MENGUNGGAH HASIL BUILD
    kirim_telegram("🔍 <b>Status:</b> Build selesai! Sedang mencari dan mengunggah file ROM (.zip)...")
    
    jalur_pencarian = f"out/target/product/{codename_device}/lineage-*.zip"
    daftar_file_zip = glob.glob(jalur_pencarian)
    
    if daftar_file_zip:
        file_rom = daftar_file_zip[0]
        link_rom = upload_rom(file_rom)
        
        if link_rom:
            pesan_sukses = f"✅ <b>BUILD & UPLOAD BERHASIL!</b>\n\n<b>Perangkat:</b> {codename_device}\n<b>File:</b> {os.path.basename(file_rom)}\n<b>Link Download:</b> {link_rom}"
            kirim_telegram(pesan_sukses)
        else:
            kirim_telegram("⚠️ <b>Peringatan:</b> Build berhasil, tapi proses upload ROM gagal. Silakan cek log Cirrus CI.")
    else:
        kirim_telegram("❌ <b>Error:</b> Build dilaporkan selesai, tapi file .zip tidak ditemukan di folder output.")

if __name__ == "__main__":
    utama()
