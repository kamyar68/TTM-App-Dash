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
