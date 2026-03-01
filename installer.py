import subprocess
import os
import threading
from logger import log_command

# handles package installation, user setup and disk partitioning

def install(window, base_dir, drivers, template, gaming, dev, next_clicked, make_user, save_time, page):
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
    
    kde = window.checkkde.isChecked()
    xfce = window.checkxfce.isChecked()
    gnome = window.checkgnome.isChecked()
    kdestring = ""
    xfcestring = ""
    gnomesring = ""

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
        kdestring = ["plasma-desktop", "dolphin", "konsole"]
    else:
        kdestring = []

    if xfce == True:
        xfcestring = ["xfce4", "xfce4-terminal", "xfce4-goodies"]
    else:
        xfcestring = []

    if gnome == True:
        gnomestring = ["gnome", "konsole"]
    else:
        gnomestring = []

    from PySide6.QtCore import Qt
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


def make_user(window, user, useryn, password):
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


def savedisk(window, base_dir, disks, uefi, pathdisk, install_fn):
    window.installButton.setEnabled(False)

    def run_partition():
        idxdisks = window.comboDisk.currentIndex()
        pathdisk_local = disks[idxdisks][1]
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
                f.write(f'TARGET_DISK="{pathdisk_local}"\n')
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
                install_fn()
            else:
                print("Partitioning failed!")
                window.installStatus.setText("Installation failed")
                window.installButton.setEnabled(True)
        
        except subprocess.CalledProcessError as e:
            print(f"{e}")
            
    threading.Thread(target=run_partition, daemon=True).start()


def check_part(window, pathdisk, next_clicked):
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
