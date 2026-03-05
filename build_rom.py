import os
import subprocess
import sys
import urllib.request
import urllib.parse

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
        pesan_error = f"❌ <b>BUILD GAGAL!</b>\n\n<b>Tahap:</b> {pesan_gagal}\n<b>Perintah:</b> <code>{perintah}</code>\n\nSilakan cek log di Cirrus CI untuk detailnya."
        kirim_telegram(pesan_error)
        sys.exit(1) # Hentikan skrip jika gagal

def utama():
    # --- VARIABEL ROM ---
    link_manifest = "https://github.com/LineageOS/android.git"
    branch_rom = "lineage-20.0" # Sesuaikan jika Anda menggunakan versi lain (misal: lineage-19.1)
    codename_device = "X00TD"
    
    kirim_telegram(f"🚀 <b>Mulai Build ROM!</b>\n\n<b>Perangkat:</b> {codename_device}\n<b>ROM:</b> LineageOS ({branch_rom})\n<b>Status:</b> Menyiapkan environment...")

    # 1. Konfigurasi Git
    jalankan_perintah("git config --global user.name 'Bot Cirrus CI'", "Konfigurasi Git Name")
    jalankan_perintah("git config --global user.email 'bot@cirrus.ci'", "Konfigurasi Git Email")

    # 2. Inisialisasi Repo
    jalankan_perintah(f"repo init -u {link_manifest} -b {branch_rom} --depth=1", "Repo Init")

    # 3. Sinkronisasi (Sync)
    kirim_telegram("🔄 <b>Status:</b> Memulai sinkronisasi source code (Repo Sync). Ini akan memakan waktu cukup lama...")
    jalankan_perintah("repo sync -c --no-clone-bundle --no-tags --optimized-fetch --prune --force-sync -j8", "Repo Sync")

    # 4. Kompilasi (Build)
    kirim_telegram("⚙️ <b>Status:</b> Source code tersinkronisasi. Memulai kompilasi (brunch)...")
    perintah_build = f"source build/envsetup.sh && brunch {codename_device}"
    jalankan_perintah(perintah_build, "Kompilasi ROM (Brunch)")
    
    # 5. Berhasil
    kirim_telegram(f"✅ <b>BUILD BERHASIL!</b>\n\nROM untuk {codename_device} telah selesai dikompilasi.")

if __name__ == "__main__":
    utama()
