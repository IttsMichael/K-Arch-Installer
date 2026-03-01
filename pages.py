import subprocess
import os
import threading
from logger import log_command

# page navigation and per-page setup logic

def next_clicked(window, page_ref, page_turn, plus=0):
    if isinstance(plus, bool):
        plus = 0
    print("next was clicked")
    page_ref[0] += 1 + plus
    print(page_ref[0])
    window.stackedWidget.setCurrentIndex(page_ref[0])
    page_turn()


def back(window, page_ref, page_turn, checked=False):
    print("back was clicked")
    page_ref[0] -= 1
    print(page_ref[0])
    window.stackedWidget.setCurrentIndex(page_ref[0])
    page_turn()


def page_turn(window, page, page1, page3, page5, page8):
    if page == 1:
        print("page1")
        page1()
    elif page == 2:
        print("page2")
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


def on_save_clicked(save_time, next_clicked):
    save_time()
    next_clicked(0)


# load keyboard layouts from xkb rules file
def layout_format(window, layouts):
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


def save_time(window, installing):
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


def page5(window, gpu_command_ref):
    gpu_vendor = log_command(
        ["bash", "-c", "lspci | grep -E 'VGA|3D'"],
        capture_output=True
    ).stdout
    print(gpu_vendor)
    
    if "NVIDIA" in gpu_vendor:
        gpu_vendor = "An NVIDIA GPU"
        gpu_command_ref[0] = "nvidia-dkms nvidia-utils"
        window.labelGpu.setText(gpu_vendor + " was detected")
    elif "AMD" in gpu_vendor:
        gpu_vendor = "AMD Radeon"
        gpu_command_ref[0] = "mesa vulkan-radeon libva-mesa-driver"
        window.labelGpu.setText(gpu_vendor + " was detected")
    elif "Intel" in gpu_vendor:
        gpu_vendor = "Intel Graphics"
        gpu_command_ref[0] = "mesa vulkan-intel"
        window.labelGpu.setText(gpu_vendor + " was detected")
    else:
        gpu_vendor = "Unknown"
        gpu_command_ref[0] = "mesa"
        window.labelGpu.setText("No specific GPU detected.")

    print(gpu_command_ref[0])


def page8(window, user, disks):
    disk_overview = window.comboDisk.currentText()
    root_size = window.spinRoot.value()
    print(disk_overview)
    print(root_size)
    window.ovDisk.setText("Selected Disk: " + disk_overview)
    window.ovRoot.setText("Root Size: " + str(root_size) + " MiB")
    window.ovUser.setText("Useraccount:  " + user)
