import subprocess
import os
import threading
from logger import log_command

# wifi and ethernet connection handling

def connect_wifi(window, next_clicked):
    from PySide6.QtCore import Qt, QTimer

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
            page3(window)
            return True
            
        except subprocess.CalledProcessError:
            QTimer.singleShot(0, lambda: window.labelStatusWifi.setText("Connection Failed"))
        

    threading.Thread(target=run_connection, daemon=True).start()


def disconnect_wifi(window):
    log_command(["nmcli", "device", "disconnect", "wlan0"])
    page3(window)


def toggle_ethernet(window, enabled, connected_ref):
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

        connected_ref[0] = True
        print(connected_ref[0])


def log_item(window):
    item = window.wifiList.currentItem()
    if item:
        print(f"User clicked: {item.text()}")
        window.passwordWifi.setEnabled(True)


# scan and display wifi networks
def page3(window):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QListWidgetItem

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
