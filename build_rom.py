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
GH_TOKEN = os.environ.get('GH_TOKEN') # Variabel baru untuk Token GitHub

# ... [Fungsi kirim_telegram, jalankan_perintah, upload_rom, fungsi rclone TETAP SAMA] ...

def setup_kredensial_git():
    """Fungsi baru: Mengatur kredensial agar bisa mengkloning repo privat"""
    if not GH_TOKEN:
        print("[INFO] GH_TOKEN tidak ditemukan. Melewati pengaturan kredensial repo privat.")
        return

    print("\n[INFO] Mengatur kredensial Git untuk repositori privat...")
    # Kita menggunakan subprocess.run langsung di sini tanpa mencetak (print) perintahnya,
    # agar token rahasia Anda tidak bocor ke dalam log publik Cirrus CI.
    perintah_kredensial = f'git config --global url."https://{GH_TOKEN}@github.com/".insteadOf "https://github.com/"'
    subprocess.run(perintah_kredensial, shell=True)
    print("[INFO] Kredensial Git berhasil diatur secara rahasia!")

def utama():
    link_manifest = "https://github.com/LineageOS/android.git"
    branch_rom = "lineage-20.0" 
    codename_device = "X00TD"
    
    # URL di bawah ini tetap gunakan format biasa (https://github.com/...)
    # Sistem Git akan otomatis menyisipkan token Anda berkat trik insteadOf di atas!
    repositori_perangkat = [
        {"nama": "Device Tree", "url": "https://github.com/LineageOS/android_device_asus_X00TD.git", "branch": "lineage-20.0", "path": "device/asus/X00TD"},
        {"nama": "Vendor Tree", "url": "https://github.com/RepositoriPrivatAnda/vendor_asus.git", "branch": "lineage-20.0", "path": "vendor/asus"},
        {"nama": "Kernel Tree", "url": "https://github.com/LineageOS/android_kernel_asus_sdm660.git", "branch": "lineage-20.0", "path": "kernel/asus/sdm660"}
    ]

    kirim_telegram(f"🚀 <b>Mulai Build ROM!</b>\n\n<b>Perangkat:</b> {codename_device}\n<b>ROM:</b> LineageOS ({branch_rom})")

    jalankan_perintah("git config --global user.name 'Bot Cirrus CI'", "Git Name")
    jalankan_perintah("git config --global user.email 'bot@cirrus.ci'", "Git Email")

    setup_kredensial_git()

    jalankan_perintah(f"repo init -u {link_manifest} -b {branch_rom} --depth=1", "Repo Init")

    kirim_telegram("🔄 <b>Status:</b> Sinkronisasi source utama...")
    jalankan_perintah("repo sync -c --no-clone-bundle --no-tags --optimized-fetch --prune --force-sync -j8", "Repo Sync")

    kirim_telegram("📥 <b>Status:</b> Mengkloning Device, Vendor, dan Kernel Tree...")
    for repo in repositori_perangkat:
        jalankan_perintah(f"rm -rf {repo['path']}", f"Clear {repo['path']}")
        jalankan_perintah(f"git clone --depth=1 -b {repo['branch']} {repo['url']} {repo['path']}", f"Kloning {repo['nama']}")

    # --- SETUP CCACHE SEBELUM BUILD ---
    gunakan_ccache = siapkan_rclone()
    if gunakan_ccache:
        restore_ccache()

    kirim_telegram("⚙️ <b>Status:</b> Memulai kompilasi (brunch)...")
    
    # Perintah build dimodifikasi untuk menggunakan ccache (ditaruh di /tmp/ccache)
    perintah_build = """
    export USE_CCACHE=1
    export CCACHE_DIR=/tmp/ccache
    export CCACHE_EXEC=$(which ccache)
    ccache -M 50G
    source build/envsetup.sh && brunch X00TD
    """
    jalankan_perintah(perintah_build, "Kompilasi ROM")
    
    # --- BACKUP CCACHE SETELAH BUILD SELESAI ---
    if gunakan_ccache:
        backup_ccache()
        
    kirim_telegram("🔍 <b>Status:</b> Build selesai! Mengunggah ROM...")
    
    daftar_file_zip = glob.glob(f"out/target/product/{codename_device}/lineage-*.zip")
    if daftar_file_zip:
        file_rom = daftar_file_zip[0]
        link_rom = upload_rom(file_rom)
        if link_rom:
            kirim_telegram(f"✅ <b>BUILD BERHASIL!</b>\n\n<b>Perangkat:</b> {codename_device}\n<b>Link:</b> {link_rom}")
        else:
            kirim_telegram("⚠️ <b>Peringatan:</b> Build sukses, tapi upload gagal.")
    else:
        kirim_telegram("❌ <b>Error:</b> File .zip tidak ditemukan.")

if __name__ == "__main__":
    utama()
