# Steps to Deploy Dash App on Ubuntu Server with Nginx and a Floating IP

## Setting Up the Dash App

Make sure your Dash app (`main.py`) is structured like this:

```python
from app import app  # Import your app instance

if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050)
```

## Copy Files to the Server

1. **Code**: Use `git` to clone or pull your project code onto the server.

2. **Data**: Use `rsync` or `sftp` to transfer data files. For simplicity, `sftp` can be used as follows:
   
   ```bash
   sftp username@floating-ip
   ```

3. **SSH into Server**: Connect to the server via SSH and place the app files under the `ubuntu` user or your desired directory:
   
   ```bash
   ssh username@floating-ip
   ```

## Install Dependencies

1. **Update and Install Packages**:
   
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-venv nginx
   ```

2. **Set Up a Virtual Environment** (inside your project folder):
   
   ```bash
   python3 -m venv dashenv
   source dashenv/bin/activate
   ```

3. **Install Required Libraries**:
   
   ```bash
   pip install dash pandas
   ```

## Running the App Without Gunicorn

Since Gunicorn can be tricky for smaller projects, running the app directly and using Nginx as a reverse proxy is a simpler approach. Another lightweight option is `waitress`.

1. Run the app with:
   
   ```bash
   python3 main.py
   ```

## Configure Nginx to Proxy Requests to the Dash App

1. **Edit the Nginx Configuration**:
   
   ```bash
   sudo nano /etc/nginx/sites-available/default
   ```

2. **Replace Contents with the Following Configuration**:
   
   ```nginx
   server {
       listen 80;
       server_name your_floating_ip;
   
       location / {
           proxy_pass http://127.0.0.1:8050;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

3. **Save and Exit**:
   
   - In nano, press `CTRL + O`, `Enter`, then `CTRL + X`.

4. **Restart Nginx**:
   
   ```bash
   sudo systemctl restart nginx
   ```

## Security Group Configuration

1. **Open HTTP and HTTPS Ports**: Ensure that ports `80` and `443` are open in your cloud provider’s security settings.
2. **Adjust IP Rules**: Setting to `0.0.0.0/0` will allow access from all IP addresses. Customize these rules based on your security requirements.

By following these steps, you should be able to successfully deploy your Dash app on your server with Nginx, making it accessible via your floating IP. Remember to monitor the server performance if you choose to scale your app further.



To monitor whether your Dash app is still running or has crashed, you can use a few methods on your server. Here are some ways to check the app's status:

### 1. **Check Running Processes**

Use the `ps` command to see if your app’s Python process is still running. Replace `main.py` with your app's filename if different:

```bash
ps aux | grep main.py
```

This will show you any running instances of `main.py`. If you see an entry with the Python process, it means the app is running.

### 2. **Use `systemctl` for Systemd Managed Services**

If you have set up your app as a Systemd service (like `dash_app.service`), you can check its status directly with:

```bash
sudo systemctl status dash_app.service
```

- An “active (running)” status indicates that the app is running.
- If the service has failed, you’ll see a “failed” status along with details of the last error encountered.

### 3. **Monitor Network Ports**

You can use `netstat` or `ss` to check if your app is listening on the expected port (8050 in this case). Here’s how:

```bash
sudo ss -tuln | grep :8050
```

If you see output indicating that the server is listening on port 8050, the app is running. No output suggests that it’s not active.

### 4. **Use `curl` to Check the App’s HTTP Response**

You can directly test the app by making an HTTP request to it:

```bash
curl http://127.0.0.1:8050
```

If the app is running, you should receive HTML content or a valid HTTP response. If it’s not running, you might see an error message.

### 5. **Check Nginx Logs (If Using Nginx)**

If you’ve set up Nginx as a reverse proxy for your Dash app, you can check the access and error logs for any signs that the app has stopped responding:

```bash
sudo tail -f /var/log/nginx/access.log /var/log/nginx/error.log
```

Frequent errors or lack of access log entries can indicate that the app has stopped.

Using these methods, you can quickly determine if your app is running or has crashed and take appropriate action. Once you confirm the status, you can set up Systemd or another method to ensure it restarts automatically if it crashes.

## Ensure the Dash App Restarts on Crash with Systemd

To make sure the Dash app automatically restarts if it crashes, you can set it up as a Systemd service.

### Step-by-Step Instructions

1. **Create a Systemd Service File**:
   Open a new service file for your Dash app:
   
   ```bash
   sudo nano /etc/systemd/system/dash_app.service
   ```

2. **Configure the Service**:
   Paste the following configuration into the file, which uses your specific paths:
   
   ```ini
   [Unit]
   Description=Dash App Service
   After=network.target
   
   [Service]
   User=ubuntu
   WorkingDirectory=/home/ubuntu/TTM-App-Dash  # Path to your app
   Environment="PATH=/home/ubuntu/TTM-App-Dash/dashenv/bin"  # Path to your virtual environment's bin directory
   ExecStart=/home/ubuntu/TTM-App-Dash/dashenv/bin/python3 /home/ubuntu/TTM-App-Dash/main.py  # Path to Python and main.py
   Restart=always  # Automatically restart the service on failure
   RestartSec=5  # Time to wait before restarting (in seconds)
   
   [Install]
   WantedBy=multi-user.target
   ```

3. **Save and Exit**:
   
   - Save the file by pressing `CTRL + O`, then press `Enter`.
   - Exit nano by pressing `CTRL + X`.

4. **Enable and Start the Service**:
   Enable the service to start on boot, then start the service:
   
   ```bash
   sudo systemctl enable dash_app.service
   sudo systemctl start dash_app.service
   ```

5. **Check the Service Status**:
   To make sure the service is running, check its status:
   
   ```bash
   sudo systemctl status dash_app.service
   ```
   
   You should see an “active (running)” status. If the app crashes, Systemd will automatically restart it after the specified `RestartSec` delay.

### Additional Commands

- **To Restart the Service**:
  
  ```bash
  sudo systemctl restart dash_app.service
  ```

- **To Stop the Service**:
  
  ```bash
  sudo systemctl stop dash_app.service
  ```

This setup will allow your Dash app to automatically restart if it crashes, helping to maintain uptime without manual intervention.

**Remember to restart the app after changes/git pull**

```
sudo systemctl restart dash_app.service
```