#!/usr/bin/env python
import subprocess
import sys
import os
import json
import re

from style import apply_style
from PySide6.QtCore import QTimer, QFile, Qt
from PySide6.QtWidgets import QApplication, QPushButton, QListWidgetItem
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QMovie

from logger import Tee, log_command
import installer
import network
import pages

base_dir = os.path.dirname(os.path.abspath(__file__))

# restart as root if needed
if os.geteuid() != 0:
    print("Not running as root. Attempting to restart with sudo...")
    try:
        subprocess.check_call(['sudo', '-E', sys.executable] + sys.argv)
    except subprocess.CalledProcessError as e:
        print(f"Failed to restart as root: {e}")
        sys.exit(1)
    sys.exit(0)

# redirect stdout and stderr to log file
log_file = "/tmp/k-arch-install.log"
sys.stdout = Tee(log_file, sys.stdout)
sys.stderr = Tee(log_file, sys.stderr)

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

# build timezone list from zoneinfo since timedatectl isnt on openrc
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


# --- wrappers that close over globals ---

def _page_turn():
    def _p1(): pages.layout_format(window, layouts)
    def _p3(): network.page3(window)
    def _p5(): pages.page5(window, gpu_command_ref)
    def _p8(): pages.page8(window, user, disks)
    pages.page_turn(window, page, _p1, _p3, _p5, _p8)

def _next_clicked(plus=0):
    global page
    page_ref = [page]
    pages.next_clicked(window, page_ref, _page_turn, plus)
    page = page_ref[0]

def _back(checked=False):
    global page
    page_ref = [page]
    pages.back(window, page_ref, _page_turn, checked)
    page = page_ref[0]

def _save_time():
    pages.save_time(window, installing)

def _on_save_clicked():
    pages.on_save_clicked(_save_time, _next_clicked)

def _make_user():
    installer.make_user(window, user, useryn, password)

def _install():
    installer.install(window, base_dir, drivers, template, gaming, dev, _next_clicked, _make_user, _save_time, page)

def savedisk():
    window.installStatus.setText("Partitioning...")
    _next_clicked()
    installer.savedisk(window, base_dir, disks, uefi, pathdisk, _install)

def check_part():
    installer.check_part(window, pathdisk, _next_clicked)

def check_uefi():
    global uefi
    try:
        if os.path.exists("/sys/firmware/efi/"):
            print("UEFI detected")
            uefi = True
            _next_clicked()
        else:
            print("Legacy BIOS detected")
            uefi = False
            _next_clicked()
    except Exception as e:
        print(f"Error checking BIOS mode: {e}")
        return None

def toggle_swap(enabled: bool):
    window.spinSwap.setEnabled(enabled)

def toggle_root(enabled = bool):
    window.spinRoot.setEnabled(not enabled)

def toggle_dev(enabled = bool):
    global dev
    dev = enabled

def toggle_gaming(enabled = bool):
    global gaming
    gaming = enabled

def save_template():
    global template
    template = True
    _next_clicked()

def install_drivers():
    global gpu_command
    global drivers
    drivers = gpu_command_ref[0]
    _next_clicked()

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
            _next_clicked()
        else:
            window.passMis.setText("Password empty or doesn't match")

def skip_user():
    global useryn
    _next_clicked()
    useryn = False

def reboot():
    log_command(["reboot"])

def next_internet():
    global connected
    if connected == True:
        _next_clicked(1)
    else:
        _next_clicked(0)

def _connect_wifi():
    def set_connected():
        global connected
        connected = True
        print(connected)
    network.connect_wifi(window, _next_clicked)

def _disconnect_wifi():
    network.disconnect_wifi(window)

def _toggle_ethernet(enabled):
    global connected
    conn_ref = [connected]
    network.toggle_ethernet(window, enabled, conn_ref)
    connected = conn_ref[0]

def _log_item():
    network.log_item(window)

def page1():
    pages.layout_format(window, layouts)


# shared mutable ref for gpu_command (used by page5 and install_drivers)
gpu_command_ref = [gpu_command]

# type and file
app = QApplication(sys.argv)
file = QFile(os.path.join(base_dir, "installer.ui"))
file.open(QFile.ReadOnly)

# loading, reading window and applying style
loader = QUiLoader()
window = loader.load(file)
file.close()

apply_style(window) # from style.py

# previous and back
window.previous.clicked.connect(_back)
window.previous1.clicked.connect(_back)
window.previous2.clicked.connect(_back)
window.previous3.clicked.connect(_back)
window.previous4.clicked.connect(_back)
window.previous5.clicked.connect(_back)
window.previous6.clicked.connect(_back)
window.previous7.clicked.connect(_back)
window.previous8.clicked.connect(_back)

# save and next
window.nextButton.clicked.connect(check_uefi)
window.saveUser.clicked.connect(save_user)
window.yesgpu.clicked.connect(install_drivers)
window.next4.clicked.connect(_next_clicked)
window.saveadd.clicked.connect(_next_clicked)
window.installButton.clicked.connect(savedisk)
window.saveTemplate.clicked.connect(save_template)
window.nextInternet.clicked.connect(next_internet)
window.savetime.clicked.connect(_on_save_clicked)
window.savedisks.clicked.connect(check_part)
window.rebootButton.clicked.connect(reboot)
window.rebootBtn.clicked.connect(reboot)

# toggles and checkmarks
window.ethernetCheck.toggled.connect(_toggle_ethernet)
window.rootCheck.toggled.connect(toggle_root)
window.swapCheck.toggled.connect(toggle_swap)
window.checkDev.toggled.connect(toggle_dev)
window.checkGaming.toggled.connect(toggle_gaming)

# rest
window.connect_button.clicked.connect(_connect_wifi)
window.refreshn.clicked.connect(lambda: network.page3(window))
toggle_swap(window.swapCheck.isChecked())

window.nogpu.clicked.connect(_next_clicked)
window.skipLogin.clicked.connect(skip_user)
window.skipTemplate.clicked.connect(_next_clicked)

# combo and spin boxes
window.comboZone.addItems(timezones)
window.comboDisk.addItems(d[0] for d in disks)
window.wifiList.itemSelectionChanged.connect(_log_item)

# loading gif
movie = QMovie(spinner_path) 
window.gif_label.setMovie(movie)
window.gif_label.setScaledContents(True)
movie.start()

# open window, reset variables
window.show()
window.stackedWidget.setCurrentIndex(0)
_page_turn() # ensure first page is initialized
sys.exit(app.exec())
