# Simple Image Hosting

无依赖的图片/文件托管服务。上传需要 API key，上传后返回可访问 URL。

代码兼容 VPS 上常见的老系统 Python 3。

## 运行

```powershell
$env:API_KEY="change-me"
$env:BASE_URL="https://img.example.com"
python server.py
```

可选环境变量：

- `PORT`：默认 `8000`
- `UPLOAD_DIR`：默认 `uploads`
- `MAX_UPLOAD_BYTES`：默认 `52428800`，50MB

## 上传

multipart：

```bash
curl -H "X-API-Key: change-me" -F "file=@cat.png" http://127.0.0.1:8000/upload
```

原始 body：

```bash
curl -H "X-API-Key: change-me" -H "X-Filename: cat.png" --data-binary @cat.png http://127.0.0.1:8000/upload
```

也支持：

```bash
curl -H "Authorization: Bearer change-me" -F "file=@cat.png" http://127.0.0.1:8000/upload
```

返回：

```json
{"url":"https://img.example.com/files/<stored-name>","filename":"<stored-name>","size":12345}
```

## VPS 部署

假设代码放在 `/opt/simpleimagehosting`：

```bash
sudo mkdir -p /opt/simpleimagehosting
sudo cp server.py /opt/simpleimagehosting/server.py
sudo mkdir -p /opt/simpleimagehosting/uploads
```

### systemd

把下面内容保存到：

```text
/etc/systemd/system/simpleimagehosting.service
```

```ini
[Unit]
Description=Simple Image Hosting
After=network.target

[Service]
WorkingDirectory=/opt/simpleimagehosting
Environment=API_KEY=change-me
Environment=BASE_URL=https://img.example.com
Environment=PORT=8000
Environment=UPLOAD_DIR=/opt/simpleimagehosting/uploads
ExecStart=/usr/bin/python3 /opt/simpleimagehosting/server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启动并设置开机自启：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now simpleimagehosting
sudo systemctl status simpleimagehosting
```

看日志：

```bash
sudo journalctl -u simpleimagehosting -f
```

### Nginx

Debian/Ubuntu 安装：

```bash
sudo apt update
sudo apt install -y nginx
```

把下面内容保存到：

```text
/etc/nginx/sites-available/simpleimagehosting
```

```nginx
server {
    listen 80;
    server_name img.example.com;

    client_max_body_size 50m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用站点并重载：

```bash
sudo ln -s /etc/nginx/sites-available/simpleimagehosting /etc/nginx/sites-enabled/simpleimagehosting
sudo nginx -t
sudo systemctl reload nginx
```

HTTPS 用 Certbot：

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d img.example.com
```

部署后把 `BASE_URL` 改成真实域名，例如 `https://img.example.com`，再重启：

```bash
sudo systemctl restart simpleimagehosting
```
