# 表白 app

## 启动

在此文件夹打开 PowerShell，运行：

```powershell
python server.py
```

电脑浏览器访问 `http://localhost:8000`。

手机和电脑连接同一 Wi-Fi 后，先在电脑 PowerShell 运行：

```powershell
ipconfig
```

在“无线局域网适配器 WLAN”的 IPv4 地址后加 `:8000`，例如 `http://192.168.1.12:8000`。首次使用时，如 Windows 询问网络访问权限，请允许 Python 在专用网络中访问。

## 让外地的人临时访问

启动本地应用后，另开一个 PowerShell 窗口运行：

```powershell
cloudflared tunnel --url http://localhost:8000
```

把终端输出的 `https://…trycloudflare.com` 链接发给对方即可。电脑必须保持开机、联网，并保留这两个 PowerShell 窗口。关闭 `cloudflared` 后链接立即失效，而且下次启动会生成新链接。

## 数据与邮件

- 每次完成的数据保存在 `data/responses.json`。断网提交的结果会保留在这里，应用保持运行并恢复联网后，会每分钟自动重试发送邮件。
- 发件邮箱设置保存在 `config.py`，该文件已加入 `.gitignore`，不要把它发给其他人。
- `images` 中目前是占位插图。收到正式图片后，用相同名称替换对应 SVG，或修改 `index.html` 中的图片路径。
