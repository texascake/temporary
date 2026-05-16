# 🚀 Android ROM Build on Cirrus CI

> A complete and modern guide for building Android ROMs using **Cirrus CI** with automated sync, compilation, ccache optimization, Telegram notifications, and release upload.

---

# 📚 Table of Contents

1. Introduction
2. Features
3. Requirements
4. Repository Structure
5. Creating a Cirrus CI Account
6. Connecting GitHub Repository
7. Preparing Build Scripts
8. Setting Up `.cirrus.yml`
9. Environment Variables
10. Using CCache
11. ROM Sync Process
12. Building the ROM
13. Uploading Build Results
14. Telegram Notifications
15. Recommended Machine Configurations
16. Troubleshooting
17. Optimization Tips
18. Example Build Scripts
19. Security Recommendations
20. Credits

---

# 📖 Introduction

This repository contains everything needed to build Android Custom ROMs using **Cirrus CI**.

Cirrus CI provides powerful cloud-based virtual machines that can compile Android ROMs automatically without requiring a local Linux server.

Using Cirrus CI allows developers to:

* Build from anywhere
* Automate nightly builds
* Reduce local hardware usage
* Share build infrastructure easily
* Integrate Telegram notifications and release uploads

This guide supports most Android ROM projects including:

* LineageOS
* PixelExperience
* crDroid
* Evolution X
* ArrowOS
* Project Elixir
* DerpFest
* RisingOS
* and many more.

---

# ✨ Features

✅ Automated source sync
✅ Automated ROM compilation
✅ CCache support
✅ Telegram build notifications
✅ OTA package upload
✅ GitHub Release integration
✅ Configurable lunch target
✅ Parallel compilation support
✅ Easy environment customization
✅ Clean and readable CI workflow

---

# 🛠 Requirements

Before starting, make sure you have:

| Requirement             | Description                                |
| ----------------------- | ------------------------------------------ |
| GitHub Account          | To host your ROM build repository          |
| Cirrus CI Account       | CI/CD platform                             |
| Android ROM Source      | ROM manifest and device tree               |
| Telegram Bot (Optional) | For notifications                          |
| Release Storage         | GitHub Releases / SourceForge / Pixeldrain |

Recommended knowledge:

* Basic Linux commands
* Git usage
* Android ROM build process
* Shell scripting

---

# 📂 Repository Structure

Example project structure:

```bash
.
├── .cirrus.yml
├── build.sh
├── sync.sh
├── upload.sh
├── telegram.sh
├── patches/
└── README.md
```

### File Descriptions

| File          | Purpose                       |
| ------------- | ----------------------------- |
| `.cirrus.yml` | Main Cirrus CI configuration  |
| `build.sh`    | ROM compilation script        |
| `sync.sh`     | Source synchronization script |
| `upload.sh`   | Upload compiled ROM           |
| `telegram.sh` | Send Telegram notifications   |

---

# ☁️ Creating a Cirrus CI Account

1. Visit:

   urlCirrus CI[https://cirrus-ci.com](https://cirrus-ci.com)

2. Login using your GitHub account.

3. Authorize Cirrus CI.

4. Enable your repository.

---

# 🔗 Connecting GitHub Repository

Push your ROM build project to GitHub:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/USERNAME/REPO.git
git push -u origin main
```

Then:

1. Open Cirrus CI Dashboard
2. Enable the repository
3. Trigger the first build

---

# ⚙️ Preparing Build Scripts

Create executable scripts:

```bash
chmod +x build.sh
chmod +x sync.sh
chmod +x upload.sh
chmod +x telegram.sh
```

---

# 🧩 Setting Up `.cirrus.yml`

Below is a modern example configuration:

```yaml
task:
  timeout_in: 240m

  name: Android ROM Build

  container:
    image: ubuntu:22.04
    cpu: 8
    memory: 32G

  environment:
    CIRRUS_CLONE_DEPTH: 1
    CCACHE_DIR: /tmp/ccache

  install_script:
    - apt update && apt upgrade -y
    - apt install -y git curl python3 zip unzip bc bison build-essential \
      ccache flex g++-multilib gcc-multilib gnupg gperf imagemagick \
      lib32ncurses5-dev lib32readline-dev lib32z1-dev liblz4-tool \
      libncurses5-dev libsdl1.2-dev libssl-dev libxml2 libxml2-utils \
      lzop pngcrush rsync schedtool squashfs-tools xsltproc zip zlib1g-dev

  sync_script:
    - bash sync.sh

  build_script:
    - bash build.sh

  upload_artifacts:
    path: out/target/product/*/*.zip
    type: application/zip
```

---

# 🔐 Environment Variables

Set environment variables inside Cirrus CI:

## Required Variables

| Variable       | Description          |
| -------------- | -------------------- |
| `BOT_TOKEN`    | Telegram bot token   |
| `CHAT_ID`      | Telegram chat ID     |
| `GITHUB_TOKEN` | GitHub release token |
| `ROM_NAME`     | ROM name             |
| `DEVICE`       | Device codename      |

### Adding Variables

1. Open repository settings in Cirrus CI
2. Navigate to Environment Variables
3. Add secrets securely

---

# ⚡ Using CCache

CCache dramatically reduces build times.

Enable ccache:

```bash
export USE_CCACHE=1
export CCACHE_EXEC=$(which ccache)
ccache -M 100G
```

Check statistics:

```bash
ccache -s
```

---

# 🔄 ROM Sync Process

Example `sync.sh`:

```bash
#!/bin/bash

set -e

mkdir rom
cd rom

repo init -u https://github.com/ROM/manifest.git -b android-15
repo sync -c --force-sync --optimized-fetch --no-tags --no-clone-bundle -j$(nproc --all)
```

Explanation:

| Command        | Function                         |
| -------------- | -------------------------------- |
| `repo init`    | Initialize ROM manifest          |
| `repo sync`    | Download source code             |
| `--force-sync` | Replace conflicting repositories |
| `-j`           | Parallel sync threads            |

---

# 🏗 Building the ROM

Example `build.sh`:

```bash
#!/bin/bash

set -e

cd rom

export USE_CCACHE=1
export CCACHE_EXEC=$(which ccache)
ccache -M 100G

source build/envsetup.sh

lunch lineage_DEVICE-userdebug

make bacon -j$(nproc --all)
```

Alternative build commands:

| ROM Type  | Build Command     |
| --------- | ----------------- |
| LineageOS | `make bacon`      |
| AOSP      | `make otapackage` |
| PixelOS   | `mka bacon`       |
| crDroid   | `brunch DEVICE`   |

---

# 📦 Uploading Build Results

Example `upload.sh`:

```bash
#!/bin/bash

FILE=$(find out/target/product -name "*.zip" | head -n 1)

curl -F file=@$FILE https://pixeldrain.com/api/file/
```

Alternative upload services:

* GitHub Releases
* SourceForge
* Pixeldrain
* Transfer.sh
* Google Drive

---

# 📲 Telegram Notifications

Example `telegram.sh`:

```bash
#!/bin/bash

MESSAGE="✅ ROM Build Finished Successfully"

curl -s -X POST https://api.telegram.org/bot${BOT_TOKEN}/sendMessage \
-d chat_id=${CHAT_ID} \
-d text="${MESSAGE}"
```

Example notification events:

* Build started
* Sync completed
* Build failed
* Build successful
* Upload finished

---

# 🖥 Recommended Machine Configurations

| Build Type   | CPU     | RAM   | Storage |
| ------------ | ------- | ----- | ------- |
| Small ROM    | 4 Core  | 16 GB | 100 GB  |
| Standard ROM | 8 Core  | 32 GB | 200 GB  |
| Heavy ROM    | 16 Core | 64 GB | 400 GB  |

Recommended:

* Ubuntu 22.04
* SSD storage
* Stable internet connection

---

# 🐞 Troubleshooting

## Out of Memory

Symptoms:

```bash
Killed
```

Fix:

* Reduce parallel jobs:

```bash
make bacon -j4
```

---

## Sync Failure

Fix:

```bash
repo sync --force-sync
```

---

## Java Version Error

Check Java version:

```bash
java -version
```

Install correct JDK:

```bash
apt install openjdk-17-jdk
```

---

## Disk Full

Clean temporary files:

```bash
rm -rf out/
rm -rf .repo/local_manifests
```

---

# 🚀 Optimization Tips

## Use Shallow Clone

```bash
repo sync --depth=1
```

## Enable Ninja Build

```bash
export USE_NINJA=true
```

## Parallel Sync

```bash
repo sync -j8
```

## Compress Logs

```bash
tar -czf logs.tar.gz logs/
```

---

# 🧪 Example Full Workflow

```yaml
task:
  timeout_in: 240m

  environment:
    USE_CCACHE: 1

  setup_script:
    - apt update
    - apt install -y git curl ccache

  sync_script:
    - bash sync.sh

  build_script:
    - bash build.sh

  upload_script:
    - bash upload.sh
```

---

# 🔒 Security Recommendations

* Never expose API keys publicly
* Use encrypted environment variables
* Avoid uploading private signing keys
* Rotate tokens regularly
* Use private repositories for sensitive projects

---

# 📈 Recommended Workflow

```text
Push Commit
    ↓
Cirrus CI Triggered
    ↓
Install Dependencies
    ↓
Sync ROM Source
    ↓
Compile ROM
    ↓
Upload ZIP
    ↓
Send Telegram Notification
```

---

# ❤️ Credits

Special thanks to:

* Android Open Source Project (AOSP)
* Cirrus CI Team
* Android ROM Community
* Open Source Contributors

---

# 📜 License

This project is licensed under the MIT License.

```text
MIT License
Copyright (c) 2026
```

---

# 🌟 Final Notes

Building Android ROMs in the cloud using Cirrus CI is one of the best ways to automate development workflows while reducing local hardware requirements.

This setup is highly customizable and can be expanded with:

* OTA automation
* Automatic changelog generation
* Kernel compilation
* Multi-device builds
* Docker-based environments
* Scheduled nightly builds

Happy Building 🚀
