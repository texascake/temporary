import os
import subprocess
import sys
import urllib.request
import urllib.parse
import glob
import json

BOT_TOKEN = os.environ.get('TG_BOT_TOKEN')
CHAT_ID = os.environ.get('TG_CHAT_ID')
RCLONE_CONF = os.environ.get('RCLONE_CONF')
GH_TOKEN = os.environ.get('GH_TOKEN')
GH_USERNAME = os.environ.get('GH_USERNAME')
CIRRUS_TASK_ID = os.environ.get('CIRRUS_TASK_ID')

FILE_ID_PESAN = "/tmp/tg_msg.txt"

LINK_MANIFEST = "https://github.com/LineageOS-T/android"
BRANCH_ROM = "lineage-20.0"
CODENAME_DEVICE = "X00T"
GAMBAR_BANNER = "https://github.com/texascake/texascake/raw/refs/heads/main/los.png"

REPOSITORI_PERANGKAT = [
    {"nama": "Device Tree", "url": "https://github.com/texascake/android_device_asus_X00TD.git", "branch": "t", "path": "device/asus/X00T"},
    {"nama": "Vendor Tree", "url": "https://github.com/texascake/proprietary_vendor_asus.git", "branch": "t", "path": "vendor/asus"},
]

def dapatkan_id_pesan():
    if os.path.exists(FILE_ID_PESAN):
        with open(FILE_ID_PESAN, 'r') as f: return f.read().strip()
    return None

def simpan_id_pesan(msg_id):
    with open(FILE_ID_PESAN, 'w') as f: f.write(str(msg_id))

def kirim_telegram(pesan):
    if not BOT_TOKEN or not CHAT_ID: return
    id_pesan = dapatkan_id_pesan()

    if CIRRUS_TASK_ID:
        link_log = f"https://cirrus-ci.com/task/{CIRRUS_TASK_ID}"
        teks_link = f"🔗 <a href='{link_log}'>View Live Logs</a>"
    else:
        teks_link = "🔗 <i>Link Log tidak tersedia (Berjalan Lokal)</i>"

    teks_dasar = f"🚀 <b>Build ROM for {CODENAME_DEVICE}</b>\n<b>📡 ROM:</b> LineageOS ({BRANCH_ROM})\n{teks_link}\n\n{pesan}"

    if id_pesan is None:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        data = urllib.parse.urlencode({
            'chat_id': CHAT_ID,
            'photo': GAMBAR_BANNER,
            'caption': teks_dasar,
            'parse_mode': 'HTML'
        }).encode('utf-8')
        try:
            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req) as respons:
                hasil = json.loads(respons.read().decode('utf-8'))
                if hasil.get('ok'): simpan_id_pesan(hasil['result']['message_id'])
        except Exception as e: print(f"[Error] Telegram Awal: {e}", flush=True)

    else:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageCaption"
        data = urllib.parse.urlencode({
            'chat_id': CHAT_ID,
            'message_id': id_pesan,
            'caption': teks_dasar,
            'parse_mode': 'HTML'
        }).encode('utf-8')
        try: urllib.request.urlopen(urllib.request.Request(url, data=data))
        except Exception as e: print(f"[Error] Telegram Edit: {e}", flush=True)

def jalankan_perintah(perintah, pesan_gagal, abaikan_error=False):
    print(f"\n[INFO] Menjalankan: {perintah}\n" + "="*40)
    proses = subprocess.Popen(perintah, shell=True, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for baris in proses.stdout: print(baris.decode('utf-8').strip())
    proses.wait()

    if proses.returncode != 0:
        if not abaikan_error:
            kirim_telegram(f"❌ <b>GAGAL!</b>\n\n<b>Tahap:</b> {pesan_gagal}\n<b>Perintah:</b> <code>{perintah}</code>")
            sys.exit(1)
    return proses.returncode == 0

def siapkan_rclone():
    if not RCLONE_CONF: return False
    os.makedirs(os.path.expanduser('~/.config/rclone'), exist_ok=True)
    with open(os.path.expanduser('~/.config/rclone/rclone.conf'), 'w') as f: f.write(RCLONE_CONF)
    return True

def tahap_setup():
    kirim_telegram("🛠️ <b>Status:</b> Menyiapkan environment dan kredensial Git...")
    jalankan_perintah("git config --global user.name 'Bot Cirrus CI'", "Git Name")
    jalankan_perintah("git config --global user.email 'bot@cirrus.ci'", "Git Email")

    if GH_USERNAME and GH_TOKEN:
        print("[INFO] Mengatur kredensial Git Privat...")
        perintah_kredensial = f'git config --global url."https://{GH_USERNAME}:{GH_TOKEN}@github.com/".insteadOf "https://github.com/"'
        subprocess.run(perintah_kredensial, shell=True)

    jalankan_perintah(f"repo init -u {LINK_MANIFEST} -b {BRANCH_ROM} --depth=1", "Repo Init")

def tahap_sync():
    kirim_telegram("🔄 <b>Status:</b> Sinkronisasi source utama...")
    jalankan_perintah("repo sync -c --no-clone-bundle --no-tags --optimized-fetch --prune --force-sync -j$(nproc --all)", "Repo Sync")

    kirim_telegram("📦 <b>Status:</b> Menarik file Git LFS dari repo utama...")
    jalankan_perintah("repo forall -c 'git lfs install --local && git lfs pull && git lfs checkout'", "Repo Forall Git LFS")

def tahap_clone():
    kirim_telegram("📥 <b>Status:</b> Mengkloning Device, Vendor, dan Kernel Tree...")
    for repo in REPOSITORI_PERANGKAT:
        jalankan_perintah(f"rm -rf {repo['path']}", f"Clear {repo['path']}")
        jalankan_perintah(f"git clone --depth=1 -b {repo['branch']} {repo['url']} {repo['path']}", f"Kloning {repo['nama']}")

def tahap_build():
    gunakan_ccache = siapkan_rclone()
    if gunakan_ccache:
        kirim_telegram("🔄 <b>Status:</b> Mengunduh ccache dari Google Drive...")
        jalankan_perintah("rclone copy queen:reload/ccache.tar.gz /tmp/ && tar -xzf /tmp/ccache.tar.gz -C /tmp", "Download Ccache", abaikan_error=True)

    kirim_telegram("⏳ <b>Status:</b> Sedang memulai kompilasi...")
    perintah_build = f"""
    export USE_CCACHE=1
    export CCACHE_DIR=/tmp/ccache
    export CCACHE_EXEC=$(which ccache)
    ccache -M 50G
    export _JAVA_OPTIONS="-Xmx8g"
    export NINJA_HIGHMEM_NUM_JOBS=1
    timeout 95m bash -c '. build/envsetup.sh && lunch lineage_{CODENAME_DEVICE}-userdebug && mka bacon -j$(nproc --all)'
    """
    sukses_build = jalankan_perintah(perintah_build, "Kompilasi ROM", abaikan_error=True)

    if not sukses_build:
        kirim_telegram("❌ <b>BUILD GAGAL!</b>\n\nMengeksekusi penyelamatan ccache...")

    if gunakan_ccache:
        kirim_telegram("☁️ <b>Status:</b> Menyimpan ccache ke Google Drive...")
        jalankan_perintah("tar -czf /tmp/ccache.tar.gz -C /tmp ccache && rclone copy /tmp/ccache.tar.gz queen:reload/", "Upload Ccache")

    if not sukses_build:
        kirim_telegram("ℹ️ <b>Info:</b> Ccache telah diamankan. Skrip dihentikan karena build error.")
        sys.exit(1)

def tahap_upload():
    kirim_telegram("🔍 <b>Status:</b> Build sukses! Mengunggah ROM ke Google Drive...")
    siapkan_rclone()

    daftar_file_zip = glob.glob(f"out/target/product/{CODENAME_DEVICE}/lineage-*.zip")
    if daftar_file_zip:
        path_file = daftar_file_zip[0]
        nama_file = os.path.basename(path_file)
        tujuan_drive = "queen:ROM_Builds"

        try:
            subprocess.check_call(f'rclone copy "{path_file}" "{tujuan_drive}/"', shell=True, executable='/bin/bash')
            hasil_link = subprocess.check_output(f'rclone link "{tujuan_drive}/{nama_file}"', shell=True, executable='/bin/bash')
            link_rom = hasil_link.decode('utf-8').strip()
            kirim_telegram(f"✅ <b>BUILD & UPLOAD BERHASIL!</b>\n\n<b>Link ROM:</b> {link_rom}")
        except subprocess.CalledProcessError as e:
            kirim_telegram(f"⚠️ <b>Peringatan:</b> Build sukses, tapi upload ke Drive gagal: {e}")
    else:
        kirim_telegram("❌ <b>Error:</b> File .zip ROM tidak ditemukan di folder output.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Tolong sebutkan tahapannya: setup, sync, clone, build, upload")
        sys.exit(1)

    tahap = sys.argv[1]

    if tahap == "setup": tahap_setup()
    elif tahap == "sync": tahap_sync()
    elif tahap == "clone": tahap_clone()
    elif tahap == "build": tahap_build()
    elif tahap == "upload": tahap_upload()
    else: print("Tahapan tidak dikenal!")
