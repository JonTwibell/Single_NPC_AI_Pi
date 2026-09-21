# Running Bavlorna as a systemd Service

A guide for auto-starting the Bavlorna AI character script on boot on a Raspberry Pi.

## 1. Create the Service File

Open a terminal on your Raspberry Pi and create a new systemd service file:

```bash
sudo nano /etc/systemd/system/bavlorna.service
```

Paste the following configuration into the editor:

```ini
[Unit]
Description=Bavlorna AI Character Script
After=network-online.target sound.target
Wants=network-online.target sound.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/your_project_folder
ExecStart=/home/pi/your_project_folder/venv/bin/python3 /home/pi/your_project_folder/SingleCharacter.py
Restart=on-failure
RestartSec=5s

# Audio environment configuration
Environment=XDG_RUNTIME_DIR=/run/user/1000

[Install]
WantedBy=multi-user.target
```

> **Note:** Update `/home/pi/your_project_folder` to match the exact absolute
> directory path where your project and `venv` folder are located
> (e.g. `/home/pi/bavlorna`). If your username is not `pi`, change `User=pi`
> to your actual username.

## 2. Enable and Start the Service

Reload the systemd daemon to register the new configuration, then enable the service to boot automatically and start it immediately:

```bash
sudo systemctl daemon-reload
sudo systemctl enable bavlorna.service
sudo systemctl start bavlorna.service
```

## 3. Service Management Commands

Use the following commands to check the status, view logs, or control the service.

**Check status:**

```bash
sudo systemctl status bavlorna.service
```

**View live print logs (stdout/stderr):**

```bash
sudo journalctl -u bavlorna.service -f
```

**Stop the service:**

```bash
sudo systemctl stop bavlorna.service
```

**Restart the service:**

```bash
sudo systemctl restart bavlorna.service
```
