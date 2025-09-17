# Valheim Dedicated Server on Proxmox (Debian 13 CT)

**with [LinuxGSM](https://linuxgsm.com/servers/vhserver/) + [Valheim Mod Manager](https://github.com/cdp1337/Valheim-Mod-Manager) (fork)**

This repository documents how to set up a **modded Valheim server**.
It has been tested on **Proxmox 9** with a **Debian 13 container**.

---

## Features

- Fully automated server management with **LinuxGSM**
- Mod support using **BepInEx** via **Valheim Mod Manager (fork)**
- Clean separation of configs and update-proof BepInEx wrapper
- Easy world backups and client mod export
- **Cron jobs** for health monitoring and automatic updates

---

## 1. Base System Setup

Run as **root**:

```bash
dpkg --add-architecture i386
apt update && apt -y upgrade

apt install -y \
  bc binutils bsdmainutils distro-info jq \
  lib32gcc-s1 lib32stdc++6 libatomic1 libc6-dev libc6:i386 \
  libpulse-dev libsdl2-2.0-0:i386 \
  netcat-openbsd pigz tmux unzip uuid-runtime \
  curl wget ca-certificates file xz-utils bzip2 python3 \
  mc nano \
  python3-packaging python3-magic python3-paramiko python3-dateutil git

# Create a dedicated user
adduser vhserver
```

---

## 2. Install LinuxGSM & Valheim

Switch to the service user:

```bash
su - vhserver
```

Download LinuxGSM and install Valheim server:

```bash
curl -Lo linuxgsm.sh https://linuxgsm.sh && chmod +x linuxgsm.sh && bash linuxgsm.sh vhserver

./vhserver install
```

---

## 3. Install the Mod Manager

Clone my fork:

```bash
git clone https://github.com/triuk/Valheim-Mod-Manager.git
```

Create a launcher:

```bash
printf '%s\n' '#!/bin/sh' 'SCRIPT_DIR="$(cd -- "$(dirname -- "$(readlink -f -- "$0")")" && pwd -P)/Valheim-Mod-Manager"' 'cd "$SCRIPT_DIR" || exit 1' 'exec python3 ./cli.py "$@"' > vhserver-mods && chmod +x vhserver-mods
```

Install **BepInEx**:

```bash
./vhserver-mods
```

Choose:

```
2: Install New Mod → BepInExPack_Valheim (denikson)
Q: Quit
```

---

## 4. Make BepInEx Update-Proof

Copy and fix the startup wrapper:

```bash
cp -p serverfiles/start_server_bepinex.sh       serverfiles/start_server_bepinex_local.sh

sed -i 's|^exec ./valheim_server\.x86_64.*|exec ./valheim_server.x86_64 "$@"|'   serverfiles/start_server_bepinex_local.sh
```

---

## 5. Configure the Server

Edit config:

```bash
nano lgsm/config-lgsm/vhserver/vhserver.cfg
```

Example:

```ini
servername="MyAwesomeServer"
serverpassword="strongPassword"
worldname="MyNeatWorld"
port="2456"
# public="1"
# maxplayers="10"
executable="./start_server_bepinex_local.sh"
```

---

## 6. Running the Server

Start:

```bash
./vhserver start
```

Details:

```bash
./vhserver details
```

Debug:

```bash
./vhserver debug
```

---

## 7. Cron Automation (Optional)

Edit crontab as vhserver user:

```bash
crontab -e
```

Add:

```cron
@reboot /home/vhserver/vhserver start >/dev/null 2>&1
*/5 * * * * /home/vhserver/vhserver monitor > /dev/null 2>&1
*/30 * * * * /home/vhserver/vhserver update > /dev/null 2>&1
0 0 * * 0 /home/vhserver/vhserver update-lgsm > /dev/null 2>&1
```

---

## 8. Mod Management (for details see the [original](https://github.com/cdp1337/Valheim-Mod-Manager))

- Manage mods:

  ```bash
  ./vhserver-mods
  ```
- You must run the server at least once with the new mod to show up its config in:
  `serverfiles/BepInEx/config`

  - Apply mod changes and create new mod configs with:

  ```bash
  ./vhserver restart
  ```

- **Export client modpack** with `7: Export/Package Mods`:

  - The pack location is in `Valheim-Mod-Manager/exports/`.
  - There are many archives, but I recommend copy content of the newest `*-configs.zip` to client's game folder to have a maximum sync.
  - If you are on client Linux Steam, set Valheim launch options: `./start_game_bepinex.sh %command%` and do not forget make the sh script executable (+x)!

---

## 9. Worlds, Saves & Backups

- Save directory (you can copy existing world's flw+db here):
  ```
  /home/vhserver/.config/unity3d/IronGate/Valheim/worlds_local/
  ```
- Backup:
  ```bash
  ./vhserver backup
  ```

---

## 10. Networking

Forward **UDP 2456–2457** (always defined port and port+1) to your container IP.

---

## 11. Useful Commands

```bash
./vhserver                # Show commands
./vhserver details        # Server info
./vhserver debug          # Verbose run
./vhserver validate       # Validate Steam files
tail -f log/console/vhserver-console.log   # Live log
```

---

## 12. Troubleshooting

- **Mods not loading (`isModded: False` during `./vhserver debug`)**
  
  (STEP 5) Ensure line `executable="./start_server_bepinex_local.sh"` is in `lgsm/config-lgsm/vhserver/vhserver.cfg`

  (STEP 4) Ensure file `serverfiles/start_server_bepinex_local.sh` has `exec ./valheim_server.x86_64 "$@"`
- **Wrong world loads, wrong password**

  Check the above (STEP 5) and (STEP 4) and in there:

  ```ini
  worldname="MyNeatWorld"
  ```
- **Server not listed / can’t join**

  (STEP 10) Check UDP ports 2456–2457 forwarding and firewall rules.

- **Client not launching after mod archive extract in Linux**
  
  (STEP 8) Confirm the `start_game_bepinex.sh` in client game folder is executable (+x).

- **Server disconnects after a while, unstable**

  (STEP 7) remove all except the `@reboot` line from cron.

---

## 13. Running multiple servers
Follow the same instructions, just:
- Create different user e.g. `adduser vhserver2`
- STEP 3 before running the script you must change gamedir in
  
  `nano Valheim-Mod-Manager/config.yml`
  
  to the new user e.g.
  
  `gamedir: '/home/vhserver2/serverfiles/'`
  
- STEP 5 define different port. Remember, the server always uses two: port and port+1, so if the first server was `port="2456"` (2457), this one must be e.g. `port="2458"` (2459)
- STEP 10 include new ports in the firewall
- If you copy something e.g. BepInEx plugins from different server, do not forget to check the owner `chown -R vhserver2:vhserver2 /home/vhserver2/serverfiles`

---

## Changelog to the [original Valheim Mod Manager](https://github.com/cdp1337/Valheim-Mod-Manager)

- ready to use `config.yml`, no changes needed for LGSM, unless you make multiple-instances server.

- added configs export function to have mod configs in sync with the client (not always the server config prevails).
