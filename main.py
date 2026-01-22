#!/usr/bin/env python

import sys
import os
import json
import subprocess
from PySide6.QtWidgets import QApplication, QPushButton
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile
base_dir = os.path.dirname(os.path.abspath(__file__))

page = 0

disks = []

datadisk = subprocess.check_output(
    ["lsblk", "-dn", "-o", "NAME,MODEL,SIZE,TYPE", "-J"],
    text=True
)

for dev in json.loads(datadisk)["blockdevices"]:
    if dev ["type"] == "disk":
        model = dev["model"] or "Unknown device"
        model = model.replace("_", " ").strip()
        size = dev["size"]
        name = dev["name"]

        displaydisk = f"{model} ({size}) - /dev/{name}"
        pathdisk = f"/dev/{name}"

        disks.append((displaydisk, pathdisk))
        
def saved():
    idxdisks = window.comboBox.currentIndex()
    pathdisk = disks[idxdisks][1]
    with open(os.path.join(base_dir, "disk.sh"), "w", encoding="utf-8") as f:
        f.write(f'TARGET_DISK="{pathdisk}"\n')

def next_clicked():
    print("next was clicked")
    global page
    page += 1
    if page == 1:
        page1()
    

def page1():
    window.stackedWidget.setCurrentIndex(1)
    window.comboBox.addItems(d[0] for d in disks)
    window.savedisks.clicked.connect(saved)


app = QApplication(sys.argv)
file = QFile(os.path.join(base_dir, "installer.ui"))
file.open(QFile.ReadOnly)


loader = QUiLoader()
window = loader.load(file)
file.close()

next_btn = window.findChild(QPushButton, "nextButton")
next_btn.clicked.connect(next_clicked)

window.show()
window.stackedWidget.setCurrentIndex(0)
sys.exit(app.exec())


    

