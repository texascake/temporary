import os
import subprocess
import sys
import urllib.request
import urllib.parse
import glob
import json
import time
import re

BOT_TOKEN = os.environ.get('TG_BOT_TOKEN')
CHAT_ID = os.environ.get('TG_CHAT_ID')
RCLONE_CONF = os.environ.get('RCLONE_CONF')
GH_TOKEN = os.environ.get('GH_TOKEN')
GH_USERNAME = os.environ.get('GH_USERNAME')
CIRRUS_TASK_ID = os.environ.get('CIRRUS_TASK_ID')

MESSAGE_ID_FILE = "/tmp/tg_msg.txt"
MANIFEST_LINK = "https://github.com/keepQASSA/manifest-kasa"
ROM_BRANCH = "Q_kasa"
DEVICE_CODENAME = "X00T"
BANNER_IMAGE = "https://github.com/texascake/texascake/raw/refs/heads/main/keepqassa2.png"

DEVICE_REPOSITORIES = [
    {"name": "Device Tree", "url": "https://github.com/texascake/android_device_asus_X00TD", "branch": "qassa", "path": "device/asus/X00T"},
    {"name": "Vendor Tree", "url": "https://github.com/Tiktodz/vendor_asus", "branch": "qassa", "path": "vendor/asus"},
]

def get_message_id():
    if os.path.exists(MESSAGE_ID_FILE):
        with open(MESSAGE_ID_FILE, 'r') as f:
            return f.read().strip()
    return None

def save_message_id(msg_id):
    with open(MESSAGE_ID_FILE, 'w') as f:
        f.write(str(msg_id))

def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        return
        
    msg_id = get_message_id()
    reply_markup_json = None
    
    if CIRRUS_TASK_ID:
        log_link = f"https://cirrus-ci.com/task/{CIRRUS_TASK_ID}"
        link_text = "💡 <i>Click the button below to check real-time progress</i>"
        keyboard = {
            "inline_keyboard": [
                [{"text": "🔄 View Live Logs", "url": log_link}]
            ]
        }
        reply_markup_json = json.dumps(keyboard)
    else:
        link_text = "🔗 <i>Log Link unavailable (Running Locally)</i>"
        
    base_text = f"🚀 <b>Build ROM for {DEVICE_CODENAME}</b>\n<b>ROM:</b> KeepQASSA ({ROM_BRANCH})\n{link_text}\n\n{message}"
    
    payload = {
        'chat_id': CHAT_ID,
        'caption': base_text,
        'parse_mode': 'HTML'
    }
    if reply_markup_json:
        payload['reply_markup'] = reply_markup_json
        
    if msg_id is None:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        payload['photo'] = BANNER_IMAGE
        data = urllib.parse.urlencode(payload).encode('utf-8')
        try:
            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                if result.get('ok'):
                    save_message_id(result['result']['message_id'])
        except Exception as e:
            print(f"[Error] Initial Telegram: {e}", flush=True)
    else:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageCaption"
        payload['message_id'] = msg_id
        data = urllib.parse.urlencode(payload).encode('utf-8')
        try:
            req = urllib.request.Request(url, data=data)
            urllib.request.urlopen(req)
        except Exception as e:
            print(f"[Error] Edit Telegram: {e}", flush=True)

def run_command(command, fail_message, ignore_error=False, extract_stats=False, live_update=False):
    print(f"\n[INFO] Running: {command}\n" + "="*40)
    process = subprocess.Popen(command, shell=True, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
    last_stats = "Unknown"
    ninja_regex = re.compile(r'\[\s*\d+%?\s+(\d+/\d+)\]')
    
    start_time = time.time()
    last_update_time = start_time
    interval_update = 120 # -- 2 minutes --
    first_update_sent = False
    
    for line in iter(process.stdout.readline, b''):
        decoded_line = line.decode('utf-8', errors='replace').strip()
        if decoded_line:
            print(decoded_line)
            
        if extract_stats or live_update:
            match = ninja_regex.search(decoded_line)
            if match:
                last_stats = match.group(1)
                
        if live_update:
            current_time = time.time()
            elapsed_since_start = current_time - start_time
            is_time_to_update = False
            
            if not first_update_sent and elapsed_since_start >= 60:
                is_time_to_update = True
                first_update_sent = True
            elif first_update_sent and (current_time - last_update_time >= interval_update):
                is_time_to_update = True
                
            if is_time_to_update:
                elapsed_secs = int(elapsed_since_start)
                m, s = divmod(elapsed_secs, 60)
                h, m = divmod(m, 60)
                time_str = f"{h} hours, {m} mins" if h > 0 else f"{m} mins, {s} secs"
                send_telegram(
                    f"⏳ <b>Status:</b> Compilation is running...\n"
                    f"📊 <b>Live Progress:</b> {last_stats} actions\n"
                    f"⏱️ <b>Elapsed Time:</b> {time_str}"
                )
                last_update_time = current_time
                
    process.wait()
    if process.returncode != 0:
        if not ignore_error:
            send_telegram(f"❌ <b>FAILED!</b>\n\n<b>Stage:</b> {fail_message}\n<b>Command:</b> <code>{command}</code>")
            sys.exit(1)
        return False if not extract_stats else (False, last_stats)
    return True if not extract_stats else (True, last_stats)

def setup_rclone():
    if not RCLONE_CONF:
        return False
    os.makedirs(os.path.expanduser('~/.config/rclone'), exist_ok=True)
    with open(os.path.expanduser('~/.config/rclone/rclone.conf'), 'w') as f:
        f.write(RCLONE_CONF)
    return True

def stage_setup():
    send_telegram("🛠️ <b>Status:</b> Setting up environment and Git credentials...")
    run_command("git config --global user.name 'Bot Cirrus CI'", "Git Name")
    run_command("git config --global user.email 'bot@cirrus.ci'", "Git Email")
    
    if GH_USERNAME and GH_TOKEN:
        print("[INFO] Setting up Private Git credentials...")
        credential_cmd = f'git config --global url."https://{GH_USERNAME}:{GH_TOKEN}@github.com/".insteadOf "https://github.com/"'
        subprocess.run(credential_cmd, shell=True)
        
    run_command(f"repo init -u {MANIFEST_LINK} -b {ROM_BRANCH} --depth=1", "Repo Init")

def stage_sync():
    send_telegram("🔄 <b>Status:</b> Syncing main source...")
    run_command("repo sync -c --no-clone-bundle --no-tags --optimized-fetch --prune --force-sync -j$(nproc --all)", "Repo Sync")
    send_telegram("📦 <b>Status:</b> Pulling Git LFS files from main repo...")
    run_command("repo forall -c 'git lfs install --local && git lfs pull && git lfs checkout'", "Repo Forall Git LFS")

def stage_clone():
    send_telegram("📥 <b>Status:</b> Cloning Device, Vendor, and Kernel Trees...")
    for repo in DEVICE_REPOSITORIES:
        run_command(f"rm -rf {repo['path']}", f"Clear {repo['path']}")
        run_command(f"git clone --depth=1 -b {repo['branch']} {repo['url']} {repo['path']}", f"Clone {repo['name']}")

def stage_build():
    use_ccache = setup_rclone()
    if use_ccache:
        send_telegram("🔄 <b>Status:</b> Downloading ccache from Google Drive...")
        run_command("rclone copy queen:qassa/ccache.tar.gz /tmp/ && tar -xzf /tmp/ccache.tar.gz -C /tmp", "Download Ccache", ignore_error=True)
        
    send_telegram("⏳ <b>Status:</b> Starting compilation...")
    build_command = f"""
    export USE_CCACHE=1
    export CCACHE_DIR=/tmp/ccache
    export CCACHE_EXEC=$(which ccache)
    ccache -M 50G
    timeout 95m bash -c 'source build/envsetup.sh && lunch qassa_{DEVICE_CODENAME}-userdebug && mka qassa'
    """
    
    start_time = time.time()
    build_success, build_stats = run_command(build_command, "ROM Compilation", ignore_error=True, extract_stats=True, live_update=True)
    end_time = time.time()
    duration_secs = int(end_time - start_time)
    
    if build_success:
        stats_data = {
            "duration": duration_secs,
            "stats": build_stats
        }
        with open("/tmp/build_stats.json", "w") as f:
            json.dump(stats_data, f)
            
        # -- ADDITION: Upload ccache if build success --
        if use_ccache:
            send_telegram("☁️ <b>Status:</b> Saving updated ccache to Google Drive...")
            run_command("tar -czf /tmp/ccache.tar.gz -C /tmp ccache && rclone copy /tmp/ccache.tar.gz queen:qassa/", "Upload Ccache", ignore_error=True)
            
    else:
        send_telegram("❌ <b>BUILD FAILED!</b>\n\nExecuting ccache rescue...")
        if use_ccache:
            send_telegram("☁️ <b>Status:</b> Saving ccache to Google Drive...")
            run_command("tar -czf /tmp/ccache.tar.gz -C /tmp ccache && rclone copy /tmp/ccache.tar.gz queen:qassa/", "Upload Ccache")
        send_telegram("ℹ️ <b>Info:</b> Ccache has been secured. Script terminated due to build error.")
        sys.exit(1)

def stage_upload():
    send_telegram("🔍 <b>Status:</b> Build successful! Checking MD5 and uploading ROM to Google Drive...")
    setup_rclone()
    
    duration_str = "Unknown"
    build_stats = "Unknown"
    if os.path.exists("/tmp/build_stats.json"):
        with open("/tmp/build_stats.json", "r") as f:
            stats_data = json.load(f)
            duration_secs = stats_data.get("duration", 0)
            mins, secs = divmod(duration_secs, 60)
            hours, mins = divmod(mins, 60)
            if hours > 0:
                duration_str = f"{hours} hours, {mins} minutes, {secs} seconds"
            else:
                duration_str = f"{mins} minutes, {secs} seconds"
            build_stats = stats_data.get("stats", "Unknown")
            
    zip_file_list = glob.glob(f"out/target/product/{DEVICE_CODENAME}/qassa_*.zip")
    
    if zip_file_list:
        file_path = zip_file_list[0]
        file_name = os.path.basename(file_path)
        drive_destination = "queen:ROM_Builds"
        
        try:
            print(f"\n[INFO] Calculating MD5 for {file_name}...")
            md5_command = f"md5sum '{file_path}' | awk '{{print $1}}'"
            raw_md5_result = subprocess.check_output(md5_command, shell=True, executable='/bin/bash')
            md5_string = raw_md5_result.decode('utf-8').strip()
            print(f"[INFO] MD5 successfully obtained: {md5_string}")
        except Exception as e:
            md5_string = "Failed to calculate MD5"
            print(f"[Error] An error occurred while calculating MD5: {e}")
            
        try:
            print(f"\n[INFO] Starting upload {file_name} to {drive_destination}...")
            upload_command = f'rclone copy "{file_path}" "{drive_destination}/" -v --tpslimit 2 --transfers 1 --retries 5 --drive-chunk-size 64M'
            upload_process = subprocess.run(upload_command, shell=True, executable='/bin/bash', capture_output=True, text=True)
            
            if upload_process.returncode != 0:
                rclone_error_msg = upload_process.stderr.strip()
                if not rclone_error_msg:
                    rclone_error_msg = upload_process.stdout.strip()
                raise Exception(f"Rclone Log:\n{rclone_error_msg[-500:]}")
                
            link_result = subprocess.check_output(f'rclone link "{drive_destination}/{file_name}"', shell=True, executable='/bin/bash')
            rom_link = link_result.decode('utf-8').strip()
            
            success_message = (
                f"✅ <b>BUILD & UPLOAD SUCCESSFUL!</b>\n\n"
                f"📁 <b>File:</b> <code>{file_name}</code>\n"
                f"🛡 <b>MD5:</b> <code>{md5_string}</code>\n"
                f"⏱️ <b>Duration:</b> {duration_str}\n"
                f"📊 <b>Build Stats:</b> {build_stats} actions\n"
                f"🔗 <b>ROM Link:</b> <a href='{rom_link}'>Download here</a>"
            )
            send_telegram(success_message)
        except Exception as e:
            send_telegram(f"⚠️ <b>Warning:</b> Build successful, but upload to Drive failed:\n<code>{e}</code>")
    else:
        send_telegram("❌ <b>Error:</b> ROM .zip file not found in the output folder.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please specify the stage: setup, sync, clone, build, upload")
        sys.exit(1)
    stage = sys.argv[1]
    
    if stage == "setup":
        stage_setup()
    elif stage == "sync":
        stage_sync()
    elif stage == "clone":
        stage_clone()
    elif stage == "build":
        stage_build()
    elif stage == "upload":
        stage_upload()
    else:
        print("Unknown stage!")
