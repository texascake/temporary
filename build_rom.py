import os
import subprocess
import sys
import urllib.request
import urllib.parse
import glob

# --- MENGAMBIL DATA RAHASIA DARI CIRRUS CI ---
BOT_TOKEN = os.environ.get('TG_BOT_TOKEN')
CHAT_ID = os.environ.get('TG_CHAT_ID')
RCLONE_CONF = os.environ.get('RCLONE_CONF')
GH_TOKEN = os.environ.get('GH_TOKEN')

def kirim_telegram(pesan):
    if not BOT_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({'chat_id': CHAT_ID, 'text': pesan, 'parse_mode': 'HTML'}).encode('utf-8')
    try: urllib.request.urlopen(urllib.request.Request(url, data=data))
    except Exception as e: print(f"[Error] Telegram: {e}")

def jalankan_perintah(perintah, pesan_gagal, abaikan_error=False):
    """Menjalankan perintah dan bisa memilih untuk lanjut meskipun error"""
    print(f"\n[INFO] Menjalankan: {perintah}\n" + "="*40)
    proses = subprocess.Popen(perintah, shell=True, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for baris in proses.stdout: print(baris.decode('utf-8').strip())
    proses.wait()
    
    if proses.returncode != 0:
        if not abaikan_error:
            # Jika abaikan_error = False (Default), skrip langsung mati
            kirim_telegram(f"❌ <b>GAGAL!</b>\n\n<b>Tahap:</b> {pesan_gagal}\n<b>Perintah:</b> <code>{perintah}</code>")
            sys.exit(1)
        else:
            # Jika abaikan_error = True, skrip tetap lanjut dan hanya mengembalikan status False
            print(f"[WARNING] Tahap '{pesan_gagal}' gagal, tetapi skrip diinstruksikan untuk lanjut.")
            
    return proses.returncode == 0 # Mengembalikan True jika sukses, False jika gagal

def upload_rom(path_file):
    print(f"\n[INFO] Mengunggah {path_file} ke transfer.sh...")
    try:
        hasil = subprocess.check_output(f'curl --upload-file "{path_file}" https://transfer.sh/{os.path.basename(path_file)}', shell=True, executable='/bin/bash')
        return hasil.decode('utf-8').strip()
    except subprocess.CalledProcessError:
        return None

def setup_kredensial_git():
    if not GH_TOKEN: return
    print("\n[INFO] Mengatur kredensial Git untuk repositori privat...")
    perintah_kredensial = f'git config --global url."https://{GH_TOKEN}@github.com/".insteadOf "https://github.com/"'
    subprocess.run(perintah_kredensial, shell=True)
    print("[INFO] Kredensial Git berhasil diatur secara rahasia!")

def siapkan_rclone():
    if not RCLONE_CONF: return False
    os.makedirs(os.path.expanduser('~/.config/rclone'), exist_ok=True)
    with open(os.path.expanduser('~/.config/rclone/rclone.conf'), 'w') as f:
        f.write(RCLONE_CONF)
    return True

def restore_ccache():
    kirim_telegram("🔄 <b>Status:</b> Mengunduh ccache dari Google Drive...")
    perintah_download = "rclone copy gdrive:ccache_X00TD/ccache.tar.gz /tmp/ && tar -xzf /tmp/ccache.tar.gz -C /tmp"
    jalankan_perintah(perintah_download, "Download Ccache", abaikan_error=True)

def backup_ccache():
    kirim_telegram("☁️ <b>Status:</b> Mengompres dan menyimpan ccache ke Google Drive...")
    perintah_upload = "tar -czf /tmp/ccache.tar.gz -C /tmp ccache && rclone copy /tmp/ccache.tar.gz gdrive:ccache_X00TD/"
    jalankan_perintah(perintah_upload, "Upload Ccache")

def utama():
    link_manifest = "https://github.com/lineageos-q-mean/android.git"
    branch_rom = "lineage-17.1" 
    codename_device = "X00TD"
    
    repositori_perangkat = [
        {"nama": "Device Tree", "url": "https://github.com/lineagos-q-mean/android_device_asus_X00TD.git", "branch": "lineage-17.1", "path": "device/asus/X00TD"},
        {"nama": "Vendor Tree", "url": "https://github.com/lineageos-q-mean/proprietary_vendor_asus.git", "branch": "lineage-17.1", "path": "vendor/asus"},
        {"nama": "Common Tree", "url": "https://github.com/lineageos-q-mean/android_kernel_asus_sdm660.git", "branch": "lineage-17.1", "path": "device/asus/sdm660-common"}
    ]
    
    kirim_telegram(f"🚀 <b>Mulai Build ROM!</b>\n\n<b>Perangkat:</b> {codename_device}\n<b>ROM:</b> LineageOS ({branch_rom})")

    jalankan_perintah("git config --global user.name 'Bot Cirrus CI'", "Git Name")
    jalankan_perintah("git config --global user.email 'bot@cirrus.ci'", "Git Email")
    setup_kredensial_git()

    jalankan_perintah(f"repo init -u {link_manifest} -b {branch_rom} --depth=1 --git-lfs", "Repo Init")

    kirim_telegram("🔄 <b>Status:</b> Sinkronisasi source utama...")
    jalankan_perintah("repo sync -c --no-clone-bundle --no-tags --optimized-fetch --prune --force-sync -j8", "Repo Sync")

    kirim_telegram("📥 <b>Status:</b> Mengkloning Device, Vendor, dan Kernel Tree...")
    for repo in repositori_perangkat:
        jalankan_perintah(f"rm -rf {repo['path']}", f"Clear {repo['path']}")
        jalankan_perintah(f"git clone --depth=1 -b {repo['branch']} {repo['url']} {repo['path']}", f"Kloning {repo['nama']}")

    gunakan_ccache = siapkan_rclone()
    if gunakan_ccache:
        restore_ccache()

    kirim_telegram("⚙️ <b>Status:</b> Memulai kompilasi (brunch)...")
    perintah_build = """
    export USE_CCACHE=1
    export CCACHE_DIR=/tmp/ccache
    export CCACHE_EXEC=$(which ccache)
    ccache -M 50G
    source build/envsetup.sh && brunch X00TD
    """
    
    # --- LOGIKA BARU UNTUK BUILD & CCACHE ---
    
    # Kita panggil perintah build dengan parameter abaikan_error=True
    # agar skrip tidak mati jika kompilasi gagal
    sukses_build = jalankan_perintah(perintah_build, "Kompilasi ROM", abaikan_error=True)
    
    if not sukses_build:
        kirim_telegram("❌ <b>BUILD GAGAL!</b>\n\nProses kompilasi terhenti karena error. Mengeksekusi penyelamatan ccache agar build selanjutnya lebih cepat...")

    # Backup ccache tetap dijalankan, terlepas dari build sukses atau gagal
    if gunakan_ccache:
        backup_ccache()

    # Jika build tadi gagal, kita matikan skripnya SEKARANG (setelah ccache aman)
    if not sukses_build:
        kirim_telegram("ℹ️ <b>Info:</b> Ccache dari build yang gagal telah berhasil diamankan ke Google Drive. Skrip dihentikan.")
        sys.exit(1)
        
    # Jika sukses_build = True, skrip akan lanjut ke bawah untuk upload ROM
    kirim_telegram("🔍 <b>Status:</b> Build sukses! Mengunggah ROM...")
    
    daftar_file_zip = glob.glob(f"out/target/product/{codename_device}/lineage-*.zip")
    if daftar_file_zip:
        file_rom = daftar_file_zip[0]
        link_rom = upload_rom(file_rom)
        if link_rom:
            kirim_telegram(f"✅ <b>BUILD & UPLOAD BERHASIL!</b>\n\n<b>Perangkat:</b> {codename_device}\n<b>Link:</b> {link_rom}")
        else:
            kirim_telegram("⚠️ <b>Peringatan:</b> Build sukses, tapi upload gagal.")
    else:
        kirim_telegram("❌ <b>Error:</b> File .zip tidak ditemukan.")

if __name__ == "__main__":
    utama()
