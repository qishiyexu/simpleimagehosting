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

用测试脚本上传：

```bash
python test_upload.py --url http://127.0.0.1:8000/upload --api-key change-me cat.png
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

### 413 Request Entity Too Large

这个错误是 Nginx 拦截了上传，通常是 `client_max_body_size` 没生效。

先确认配置真的被 Nginx 加载：

```bash
sudo nginx -T | grep -n "client_max_body_size\|server_name"
```

如果没看到你的域名和 `client_max_body_size 50m;`，检查站点是否启用：

```bash
ls -l /etc/nginx/sites-enabled/
sudo ln -s /etc/nginx/sites-available/simpleimagehosting /etc/nginx/sites-enabled/simpleimagehosting
```

也可以直接把大小限制放到 `/etc/nginx/nginx.conf` 的 `http { ... }` 里面，全站生效：

```nginx
http {
    client_max_body_size 50m;
}
```

改完检查并重载：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

如果还有 413，说明请求进了另一个 Nginx server 块；用 `sudo nginx -T` 找到匹配当前域名的 `server_name`，把 `client_max_body_size 50m;` 加到那个 `server { ... }` 里。

### 404 Not Found

如果返回页脚是 `nginx/版本号`，说明 404 来自 Nginx，不是 Python 服务。

先确认上传地址带 `/upload`：

```bash
python3 test_upload.py --url https://img.example.com/upload --api-key change-me cat.png
```

再在 VPS 上检查 Python 服务：

```bash
curl http://127.0.0.1:8000/health
```

应该返回：

```json
{"ok": true}
```

然后检查公网域名有没有进反代：

```bash
curl -i https://img.example.com/health
sudo nginx -T | grep -n "server_name\|proxy_pass"
```

如果公网 `/health` 还是 Nginx 404，把下面这个 `location /` 加到当前域名实际匹配的 `server { ... }` 里：

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

改完：

```bash
sudo nginx -t
sudo systemctl reload nginx
```
