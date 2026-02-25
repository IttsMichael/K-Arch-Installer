#!/usr/bin/env python
import subprocess
import sys
import os
import json
import threading
import re
from style import apply_style
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QPushButton
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile
from PySide6.QtWidgets import QListWidgetItem
from PySide6.QtCore import Qt
from PySide6.QtGui import QMovie

base_dir = os.path.dirname(os.path.abspath(__file__))

# Ensure script is running as root
if os.geteuid() != 0:
    print("Not running as root. Attempting to restart with sudo...")
    try:
        subprocess.check_call(['sudo', '-E', sys.executable] + sys.argv)
    except subprocess.CalledProcessError as e:
        print(f"Failed to restart as root: {e}")
        sys.exit(1)
    sys.exit(0)

# --- Logging Setup ---
log_file = "/tmp/k-arch-install.log"

class Tee:
    def __init__(self, filename, stream):
        try:
            self.file = open(filename, 'a')
        except PermissionError:
            if os.path.exists(filename):
                os.remove(filename)
                self.file = open(filename, 'a')
            else:
                raise
        self.stream = stream

    def write(self, message):
        self.file.write(message)
        self.stream.write(message)
        self.file.flush()
        self.stream.flush()

    def flush(self):
        self.file.flush()
        self.stream.flush()

    def isatty(self):
        return self.stream.isatty()

# Redirect stdout and stderr
sys.stdout = Tee(log_file, sys.stdout)
sys.stderr = Tee(log_file, sys.stderr)

def log_command(cmd, **kwargs):
    """Run a command and log its execution in real-time."""
    print(f"\n[EXEC] {' '.join(cmd) if isinstance(cmd, list) else cmd}")

    # Check if we need to return the output (like for lsblk)
    if kwargs.get('capture_output'):
        kwargs.pop('capture_output')
        try:
            output = subprocess.check_output(cmd, text=True, **kwargs)
            print(output)
            return type('Result', (), {'stdout': output})()
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Command failed with return code {e.returncode}")
            raise

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            **kwargs
        )

        for line in process.stdout:
            print(line, end='')

        process.wait()

        if process.returncode != 0:
            print(f"[ERROR] Command failed with return code {process.returncode}")
            raise subprocess.CalledProcessError(process.returncode, cmd)

        return type('Result', (), {'returncode': 0})()
    except Exception as e:
        if not isinstance(e, subprocess.CalledProcessError):
            print(f"[ERROR] Execution failed: {e}")
        raise

spinner_path = os.path.join(base_dir, "images", "spinner.gif")
drivers = " "
page = 0
wifi_status = "Disconnected"
disks = []
layouts = []
try:
    log_command(["rc-service", "NetworkManager", "start"])
except Exception:
    pass
connected = False
gpu_command = ""
user = "root"
password = "root"
sudo = True
installing = False
dev = False
gaming = False
template = False
useryn = False
uefi = True
pathdisk = ""



datadisk = log_command(
    ["lsblk", "-dn", "-o", "NAME,MODEL,SIZE,TYPE", "-J"],
    capture_output=True
).stdout

# Build timezone list from /usr/share/zoneinfo (no timedatectl on OpenRC)
def list_timezones():
    tzlist = []
    zoneinfo = "/usr/share/zoneinfo"
    exclude = {"posix", "right", "posixrules", "leap-seconds.list", "leapseconds", "tzdata.zi", "zone.tab", "zone1970.tab", "iso3166.tab"}
    for root, dirs, files in os.walk(zoneinfo):
        dirs[:] = [d for d in dirs if d not in exclude]
        for f in files:
            if f.startswith("."):
                continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, zoneinfo)
            tzlist.append(rel)
    tzlist.sort()
    return tzlist

timezones = list_timezones()

for device in json.loads(datadisk)["blockdevices"]:
    if device ["type"] == "disk":
        model = device["model"] or "Unknown device"
        model = model.replace("_", " ").strip()
        size = device["size"]
        name = device["name"]

        displaydisk = f"{model} ({size}) - /dev/{name}"
        pathdisk = f"/dev/{name}"

        disks.append((displaydisk, pathdisk))


def install():
    global installing
    installing = True
    uefi = True
    ttypath = "/mnt/etc/inittab"
    print("shit ahaha")
    try:
        log_command(['sudo', 'rm', '-f', '/etc/resolv.conf'])
        subprocess.run(['sudo', 'tee', '/etc/resolv.conf'], 
                    input=b'nameserver 1.1.1.1\n', 
                    check=True)
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")

    window.installStatus.setText("Installing packages...")
    
    global drivers
    global template
    global gaming
    global dev
    kde = window.checkkde.isChecked()
    xfce = window.checkxfce.isChecked()
    gnome = window.checkgnome.isChecked()
    kdestring = ""
    xfcestring = ""
    gnomesring = ""
    
    # Base Directory for scripts (assumed defined elsewhere, ensure it's accessible)
    # base_dir = os.path.dirname(os.path.realpath(__file__)) 

    add = ""
    if template:
        if dev:
            add = "git wget curl docker docker-compose neovim tmux vim python npm go rustup ripgrep fzf htop zsh"

    # key_id = "F3B60748DB35A47"
    print("gettings keys...")
    key_commands = [
        "sudo pacman-key --init",
        "sudo pacman-key --populate artix archlinux",
    ]

    print("Initializing and fetching keys...")
    for cmd in key_commands:
        try:
           
            log_command(cmd.split())
        except subprocess.CalledProcessError as e:
            print(f"Error running: {cmd}\nException: {e}")


    if kde == True:
        kdestring = ["plasma-deskop", "dolphin", "konsole"]
    else:
        kdestring = ""

    if xfce == True:
        xfcestring = ["xfce4", "xfce4-terminal", "xfce4-goodies"]
    else:
        xfcestring = ""

    if gnome == True:
        gnomestring = ["gnome", "konsole"]
    else:
        gnomestring = ""

    checked_items = []

    for i in range(window.listWidget.count()):
        item = window.listWidget.item(i)

        if item.checkState() == Qt.CheckState.Checked:
            checked_items.append(item.text())

    print("Starting base installation...")
    base_cmd = [
        "basestrap", "-G", "-K", "/mnt", 
        "base", "base-devel", 
        "linux-cachyos", "linux-cachyos-headers", "linux-firmware", 
        "openrc", "elogind-openrc", "dbus-openrc", 
        "artix-archlinux-support", 
        "networkmanager", "networkmanager-openrc", 
        "vim", "sddm", "sddm-openrc", 
        "firefox", "fastfetch", 
        "imagemagick", "pacman-contrib", 
        "libadwaita", "grub", "efibootmgr", "zramen",
        "zramen-openrc"
    ]
    
    full_command = base_cmd + drivers.split() + add.split() + kdestring + xfcestring + gnomestring + checked_items
    
    try:
        # 1. Main Package Installation
        log_command(full_command)

        # 2. Gaming Section (Multilib handling)
        if gaming:

            print("Installing gaming packages...")
            # Use basestrap to stay consistent with Artix hooks
            subprocess.run([
                "basestrap", "-K", "/mnt", 
                "steam", "wine", "giflib", "lutris", 
                "discord", "openrgb", "gamemode"
            ], check=True)

        # 3. Generate fstab
        print("Generating fstab...")
        window.installStatus.setText("Generating fstab...")
        with open("/mnt/etc/fstab", "w") as fstab_file:
            subprocess.run(["genfstab", "-U", "/mnt"], stdout=fstab_file, check=True)
            
        # 4. Copying Scripts
        window.installStatus.setText("Copying installer scripts...")
        print("Copying installer scripts...")
  
        try:
            bash_dir = os.path.join(base_dir, "bash")
            log_command(["bash", os.path.join(bash_dir, "copyscripts")])
        except NameError:
            print("Warning: base_dir not defined. Skipping script copy or use absolute path.")
        
        # 5. User and Time Configuration
        window.installStatus.setText("Post install configuration...")
        print("Running post-install configuration...")
        make_user()
        save_time()
        

        
        window.installStatus.setText("Installing bootloader...")
        print("Installing bootloader...")
        log_command(["artix-chroot", "/mnt", "/usr/local/bin/installgrub"])
        
        #    window.installStatus.setText("Installing bootloader...")
        #    print("Installing bootloader...")
        #    subprocess.run(["artix-chroot", "/mnt", "/usr/local/bin/grublegacy"], check=True)

        # 7. Enable Services, openrc: lowercase
        
        window.installStatus.setText("Enabling services...")
        print("Enabling OpenRC services...")
        services = ["dbus", "elogind", "NetworkManager", "sddm", "zramen"]
        for service in services:
            log_command(["artix-chroot", "/mnt", "rc-update", "add", service, "default"])
        
        print("disabling tty 3-6")
        print("Installing bootloader...")
        log_command(["artix-chroot", "/mnt", "/usr/local/bin/tty"])

        print("Installation finished successfully!")
        next_clicked()
        window.installButton.setEnabled(True)

    except subprocess.CalledProcessError as e:
        print(f"Installation Failed: {e}")
        window.installStatus.setText(f"Error: {e}")

def make_user():
    global user
    global useryn
    global password
    root_pass = "root"
    if useryn == True:
        window.installStatus.setText("Creating user " + user)
        print(f"Creating user {user}...")
        log_command(["arch-chroot", "/mnt", "useradd", "-m", "-G", "wheel", user])
    
    auth_string = f"{user}:{password}\nroot:{root_pass}\n"
    subprocess.run(
        ["arch-chroot", "/mnt", "chpasswd"],
        input=auth_string.encode(), 
        check=True)
    
    # Enable sudo for wheel group
    log_command(["arch-chroot", "/mnt", "sed", "-i", "s/^# %wheel ALL=(ALL:ALL) ALL/%wheel ALL=(ALL:ALL) ALL/", "/etc/sudoers"])


def toggle_swap(enabled: bool):
    window.spinSwap.setEnabled(enabled)

def check_uefi():
    global uefi
    try:
        if os.path.exists("/sys/firmware/efi/"):
            print("UEFI detected")
            uefi = True
            next_clicked()
        else:
            print("Legacy BIOS detected")
            uefi = False
            next_clicked()
    except Exception as e:
        print(f"Error checking BIOS mode: {e}")
        return None


def savedisk():
    
    window.installButton.setEnabled(False)
    next_clicked()
    window.installStatus.setText("Partitioning...")
    
    def run_partition():
        
        global uefi
        global pathdisk
        idxdisks = window.comboDisk.currentIndex()
        pathdisk = disks[idxdisks][1]
        root_size = window.spinRoot.value()
        swap_enabled = window.swapCheck.isChecked()
        swap_size = window.spinSwap.value() if swap_enabled else 0
        swapyn = "y" if swap_enabled else "n"
        root_enabled = window.rootCheck.isChecked()
        rootyn = "y" if root_enabled else "n"
        uefiyn = "y" if uefi else "n"
        vars_path = "/tmp/disk.sh"

        try:
            with open(vars_path, "w", encoding="utf-8") as f:
                f.write(f'TARGET_DISK="{pathdisk}"\n')
                f.write(f'rootsize="{root_size}"\n')
                f.write(f'swapyn="{swapyn}"\n')
                f.write(f'rootyn="{rootyn}"\n')
                f.write(f'swapsize="{swap_size}"\n')
                f.write(f'uefiyn="{uefiyn}"\n')
                f.write("export TARGET_DISK rootsize swapyn swapsize rootyn uefiyn\n")
                
            bash_dir = os.path.join(base_dir, "bash")
            partition_script = os.path.join(bash_dir, "partitionscript")
            
            env = os.environ.copy()
            env["VARS_FILE"] = vars_path
            env["BASH_SCRIPTS_DIR"] = bash_dir
            
            try:
                partition_result = log_command(["bash", partition_script], env=env)
            except subprocess.CalledProcessError as e:
                partition_result = type('Result', (), {'returncode': e.returncode})()
        
            if partition_result.returncode == 0:
                install()
            else:
                print("Partitioning failed!")
                window.installStatus.setText("Installation failed")
                window.installButton.setEnabled(True)
        
        except subprocess.CalledProcessError as e:
            print(f"{e}")
            
    threading.Thread(target=run_partition, daemon=True).start()


def check_part():
    global pathdisk 
    cmd = ["lsblk", "-b", "-d", "-n", "-o", "SIZE", f"{pathdisk}"]
    bytes_str = subprocess.check_output(cmd).decode().strip()
    
    # Convert to int first
    total_bytes = int(bytes_str)
    
    # Calculate MiB (Division by 1024 squared)
    size = total_bytes // (1024 * 1024)
    
    print(f"Variable 'size' is now: {size}")

    
    swap_enabled = window.swapCheck.isChecked()
    root_enabled = window.rootCheck.isChecked()
    selected = window.spinSwap.value() if swap_enabled else 0
    selected = selected + 0 if root_enabled else window.spinRoot.value() 
    print(selected)
    if selected > size:
        window.label_31.setText("Partitions too large")
    else:
        next_clicked()

def layout_format():
    window.comboLayout.clear()

    with open("/usr/share/X11/xkb/rules/base.lst", encoding="utf-8") as f:
        in_layouts = False
        for line in f:
            line = line.strip()
            if line.startswith("! layout"):
                in_layouts = True
                continue
            if line.startswith("!") and in_layouts:
                break
            if in_layouts and line:
                parts = line.split(None, 1)
                if len(parts) == 2:
                    code, name = parts
                    layouts.append((name, code))
                    window.comboLayout.addItem(f"{name} — {code}", code)

# unoptimised shitty function but it works
# nevermind.

def save_time():
    global installing
    layout_code = window.comboLayout.currentData()
    idxtime = window.comboZone.currentText()
    
    def run_commands():
        try:
         
            if layout_code:
           
                try:
                    log_command(["loadkeys", layout_code])
                except Exception:
                    pass
                try:
                    log_command(["setxkbmap", layout_code])
                except Exception:
                    pass
                
                # KDE Plasma Wayland support
                try:
                    log_command(["kwriteconfig6", "--file", "kxkbrc", "--group", "Layout", "--key", "LayoutList", layout_code])
                except Exception:
                    pass
                try:
                    log_command(["kwriteconfig6", "--file", "kxkbrc", "--group", "Layout", "--key", "Use", "true"])
                except Exception:
                    pass
                try:
                    log_command(["dbus-send", "--session", "--type=method_call", "--dest=org.kde.keyboard", "/Layouts", "org.kde.KeyboardLayouts.reloadConfig"])
                except Exception:
                    pass
                # openrc specific
                with open("/etc/conf.d/keymaps", "w") as f:
                    f.write(f'keymap="{layout_code}"\n')
            
            zone_path = f"/usr/share/zoneinfo/{idxtime}"
            if os.path.exists(zone_path):
                log_command(["ln", "-sf", zone_path, "/etc/localtime"])

            
            if installing and os.path.exists("/mnt/etc"):
                # Timezone
                if os.path.exists(zone_path):
                    log_command(["ln", "-sf", zone_path, "/mnt/etc/localtime"])
                    # Use artix-chroot if available, else arch-chroot
                    chroot_cmd = "artix-chroot" if os.path.exists("/usr/bin/artix-chroot") else "arch-chroot"
                    log_command([chroot_cmd, "/mnt", "hwclock", "--systohc"])
                
                # Keyboard Layout
                if layout_code:
                   
                    with open("/mnt/etc/conf.d/keymaps", "w") as f:
                        f.write(f'keymap="{layout_code}"\n')
                    
                    # Fix X11 for Plasma
                    x11_conf_dir = "/mnt/etc/X11/xorg.conf.d"
                    os.makedirs(x11_conf_dir, exist_ok=True)
                    with open(os.path.join(x11_conf_dir, "00-keyboard.conf"), "w") as f:
                        f.write('Section "InputClass"\n')
                        f.write('        Identifier "system-keyboard"\n')
                        f.write('        MatchIsKeyboard "on"\n')
                        f.write(f'        Option "XkbLayout" "{layout_code}"\n')
                        f.write('EndSection\n')

            print("Time and layout updated for Artix/OpenRC.")
        except subprocess.CalledProcessError as e:
            print(f"Error setting time/layout: {e}")

    threading.Thread(target=run_commands, daemon=True).start()
def next_clicked(plus=0):
    if isinstance(plus, bool):
        plus = 0
    print("next was clicked")
    global page
    page += 1 + plus
    print(page)
    window.stackedWidget.setCurrentIndex(page)
    page_turn()

def back(checked=False):
    print("back was clicked")
    global page
    page -= 1
    print(page)
    window.stackedWidget.setCurrentIndex(page)
    page_turn()

def page_turn():
    if page == 1:
        print("page1")
        page1()
    elif page == 2:
        print("page2")
        page2()
    elif page == 3:
        print("page3")
        page3()
    elif page == 4:
        print("page4")
    elif page == 5:
        print("page5")
        page5()
    elif page == 6:
        print("page6")
    elif page == 7:
        print("page7")
    elif page == 8:
        print("page8")
        page8()
    

def on_save_clicked():
    save_time()
    next_clicked(0)

def disconnect_wifi():
    log_command(["nmcli", "device", "disconnect", "wlan0"])
    page3()

def connect_wifi():
    
    item = window.wifiList.currentItem()
    if not item:
        return

    data = item.data(Qt.UserRole)
    ssid = data["ssid"]
    secure = data["secure"]
    password = window.passwordWifi.text().strip()

    if secure and not password:
        window.labelStatusWifi.setText("Password required")
        return

    window.labelStatusWifi.setText("Connecting...")
    window.connect_button.setEnabled(False)

    def run_connection():
        try:

            if secure:
                log_command([
                    "nmcli", "connection", "add",
                    "type", "wifi", "ifname", "*",
                    "con-name", ssid, "ssid", ssid,
                    "wifi-sec.key-mgmt", "wpa-psk",
                    "wifi-sec.psk", password
                ])

                log_command(["nmcli", "connection", "up", ssid])
                try:
                    log_command(['sudo', 'rm', '-f', '/etc/resolv.conf'])
                    subprocess.run(['sudo', 'tee', '/etc/resolv.conf'], 
                                input=b'nameserver 1.1.1.1\n', 
                                check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Command failed: {e}")
            else:
                log_command(["nmcli", "device", "wifi", "connect", ssid])
            
            
            
            print(f"Successfully connected to {ssid}")
            window.labelStatusWifi.setText("Connected")
            window.connect_button.setEnabled(True)
            page3()
            global connected
            connected = True
            print(connected)
            
        except subprocess.CalledProcessError:
            QTimer.singleShot(0, lambda: window.labelStatusWifi.setText("Connection Failed"))
        

    threading.Thread(target=run_connection, daemon=True).start()
    

def log_item():
    item = window.wifiList.currentItem()
    if item:
        print(f"User clicked: {item.text()}")
        window.passwordWifi.setEnabled(True)


def toggle_ethernet(enabled = bool):
    window.passwordWifi.setEnabled(not enabled)
    window.refreshn.setEnabled(not enabled)
    window.wifiList.setEnabled(not enabled)
    window.connect_button.setEnabled(not enabled)
    
    if enabled == True:
        command = 'nmcli device | grep "ethernet" | awk \'{print $1}\' | head -n 1'

        devicelan = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True
        )

        devicelan = devicelan.stdout.strip()
        print(f"Device found: {devicelan}")

        log_command(["nmcli", "device", "connect", devicelan])
        try:
            log_command(['sudo', 'rm', '-f', '/etc/resolv.conf'])
            subprocess.run(['sudo', 'tee', '/etc/resolv.conf'], 
                        input=b'nameserver 1.1.1.1\n', 
                        check=True)
        except subprocess.CalledProcessError as e:
            print(f"Command failed: {e}")

        global connected
        connected = True
        print(connected)


def next_internet():
    global connected
    if connected == True:
        next_clicked(1)
    else:
        next_clicked(0)

def install_drivers():
    global gpu_command
    global drivers
    drivers = gpu_command
    next_clicked()


def save_user():
    global useryn
    useryn = True
    global user
    global password
    usertest = window.userLine.text().strip()
    passwordtest = window.passLine.text().strip()
    passconfirm = window.pass2Line.text().strip()

    if not usertest:
        window.empty.setText("User can't be empty")
    else:
        if passwordtest == passconfirm and passwordtest != "":
            user = usertest
            password = passwordtest
            print(user)
            print(password)
            next_clicked()
        else:
            window.passMis.setText("Password empty or doesn't match")

def skip_user():
    global useryn
    next_clicked()
    useryn = False

def reboot():
    log_command(["reboot"])

def toggle_dev(enabled = bool):
    global dev
    dev = enabled

def toggle_gaming(enabled = bool):
    global gaming
    gaming = enabled

def save_template():
    global template
    template = True
    next_clicked()

def toggle_root(enabled = bool):
    window.spinRoot.setEnabled(not enabled)

def page1():
    layout_format()

def page2():
    pass


def page3():
    global wifi_status
    window.wifiList.clear()
    status = log_command(
    ["nmcli", "-t", "-f", "STATE", "general"],
    capture_output=True
).stdout    
    window.labelStatusWifi.setText(status.capitalize())
    wifi_status = window.labelStatusWifi.setText(status.capitalize())
    wifilist = log_command(
    ["nmcli", "-t", "-f", "IN-USE,SSID,SECURITY,SIGNAL", "device", "wifi", "list"],
    capture_output=True
).stdout
    for line in wifilist.splitlines():
        in_use, ssid, security, signal = line.split(":", 3)        
        lock = "🔒" if security != "--" else "🔓"
        text = f"{ssid}  {lock}  {signal}%"

        if in_use == "*":
            connected_icon = " ✅"
        else:
            connected_icon = ""

        item = QListWidgetItem(text)
        item.setData(Qt.UserRole, {
            "ssid": ssid,
            "secure": security != "--"
        })

        item.setText(text + connected_icon)
        window.wifiList.addItem(item)



def page5():
    global gpu_command

    gpu_vendor = log_command(
        ["bash", "-c", "lspci | grep -E 'VGA|3D'"],
        capture_output=True
    ).stdout
    print(gpu_vendor)
    
    if "NVIDIA" in gpu_vendor:
        gpu_vendor = "An NVIDIA GPU"
        gpu_command = "nvidia-dkms nvidia-utils"
        window.labelGpu.setText(gpu_vendor + " was detected")
    elif "AMD" in gpu_vendor:
        gpu_vendor = "AMD Radeon"
        gpu_command = "mesa vulkan-radeon libva-mesa-driver"
        window.labelGpu.setText(gpu_vendor + " was detected")
    elif "Intel" in gpu_vendor:
        gpu_vendor = "Intel Graphics"
        gpu_command = "mesa vulkan-intel"
        window.labelGpu.setText(gpu_vendor + " was detected")
    else:
        gpu_vendor = "Unknown"
        gpu_command = "mesa"
        window.labelGpu.setText("No specific GPU detected.")

    print(gpu_command)

def page8():
    global user
    disk_overview = window.comboDisk.currentText()
    root_size = window.spinRoot.value()
    print(disk_overview)
    print(root_size)
    window.ovDisk.setText("Selected Disk: " + disk_overview)
    window.ovRoot.setText("Root Size: " + str(root_size) + " MiB")
    window.ovUser.setText("Useraccount:  " + user)

# type and file

app = QApplication(sys.argv)
file = QFile(os.path.join(base_dir, "installer.ui"))
file.open(QFile.ReadOnly)

# loading, reading window and applying style

loader = QUiLoader()
window = loader.load(file)
file.close()

apply_style(window) # from style..py

# previous and back

window.previous.clicked.connect(back)
window.previous1.clicked.connect(back)
window.previous2.clicked.connect(back)
window.previous3.clicked.connect(back)
window.previous4.clicked.connect(back)
window.previous5.clicked.connect(back)
window.previous6.clicked.connect(back)
window.previous7.clicked.connect(back)
window.previous8.clicked.connect(back)

# save and next

window.nextButton.clicked.connect(check_uefi)
window.saveUser.clicked.connect(save_user)
window.yesgpu.clicked.connect(install_drivers)
window.next4.clicked.connect(next_clicked)
window.saveadd.clicked.connect(next_clicked)
window.installButton.clicked.connect(savedisk)
window.saveTemplate.clicked.connect(save_template)
window.nextInternet.clicked.connect(next_internet)
window.savetime.clicked.connect(on_save_clicked)
window.savedisks.clicked.connect(check_part)
window.rebootButton.clicked.connect(reboot)
window.rebootBtn.clicked.connect(reboot)

# toggles and checkmarks

window.ethernetCheck.toggled.connect(toggle_ethernet)
window.rootCheck.toggled.connect(toggle_root)
window.swapCheck.toggled.connect(toggle_swap)
window.checkDev.toggled.connect(toggle_dev)
window.checkGaming.toggled.connect(toggle_gaming)

# rest

window.connect_button.clicked.connect(connect_wifi)
window.refreshn.clicked.connect(page3)
toggle_swap(window.swapCheck.isChecked())

window.nogpu.clicked.connect(next_clicked)
window.skipLogin.clicked.connect(skip_user)
window.skipTemplate.clicked.connect(next_clicked)

# combo and spin boxes

window.comboZone.addItems(timezones)
window.comboDisk.addItems(d[0] for d in disks)
window.wifiList.itemSelectionChanged.connect(log_item)

# loading gif

movie = QMovie(spinner_path) 
window.gif_label.setMovie(movie)
window.gif_label.setScaledContents(True)
movie.start()

# open window, reset variables

window.show()
window.stackedWidget.setCurrentIndex(0)
page_turn() # ensure first page is initialized
sys.exit(app.exec())


    

