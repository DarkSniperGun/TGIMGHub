# TG IMG Hub

一个基于 Telegram 的图片托管服务，支持拖拽上传、密码保护和自动生成多种格式的图片链接。

## 特性

- 🚀 快速上传：支持拖拽和点击上传
- 🔒 密码保护：可配置上传密码
- 📋 多格式链接：自动生成直链、HTML 和 Markdown 格式
- 🔄 实时预览：上传后即时显示图片
- 💾 永久存储：基于 Telegram 的可靠存储
- 🌐 跨平台支持：支持各种图片格式

## 部署指南

### 环境要求

- Python 3.7+
- FastAPI
- python-telegram-bot
- 一个 Telegram Bot Token

### 安装步骤

1. 克隆仓库
```bash
git clone https://github.com/DarkSniperGun/TgImgHub.git
cd TgImgHub
```

2. 安装依赖

```bash
pip install -r requirements.txt
```
3. 配置服务

复制`config.example.py`为`config.py`并修改配置  
```bash
cp config.example.py config.py
nano config.py
```

4. 设置系统服务 
修改里面的path_to/main.py为你项目的路径，可使用`pwd`查看当前路径
user填你当前的用户名
```bash
nano tgimghub.service
```
```bash
sudo cp tgimghub.service /etc/systemd/system/
sudo systemctl enable tgimghub
sudo systemctl start tgimghub
```

5. 访问主页
http://your-Ip::21351
### 配置说明

在 `config.py` 中设置以下参数：

- `BOT_TOKEN`: 你的 Telegram Bot Token
- `CHANNEL_ID`: 你的公开频道关键字
- `BASE_URL`: 你的图片服务URL
- `UPLOAD_PASSWORD`: 上传密码   

### Caddy 配置
```caddyfile
your.domain.com {
reverse_proxy localhost:21351
}
``` 

## 使用方法

1. 访问你的域名
2. 如果设置了密码，输入上传密码
3. 拖拽或点击上传图片
4. 获取生成的图片链接

## API 文档

### 上传图片

## 使用方法

1. 访问你的域名
2. 如果设置了密码，输入上传密码
3. 拖拽或点击上传图片
4. 获取生成的图片链接

## API 文档

### 上传图片

## 使用方法

1. 访问你的域名
2. 如果设置了密码，输入上传密码
3. 拖拽或点击上传图片
4. 获取生成的图片链接

## API 文档
### 使用 curl 上传图片

1. 无密码上传： 
```bash
curl -X POST http://your.domain.com/upload/ -F "file=@path_to/image.jpg"
```

2. 有密码上传：
```bash
curl -X POST http://your.domain.com/upload/ -F "file=@path_to/image.jpg" -H "Authorization: Bearer your_password"   

```
参数：
file: 图片文件
响应
```json
{
"success": true,
"url": "https://your.domain.com/image/file_id.jpg",
"file_id": "xxx",
"extension": ".jpg"
}
```


### 获取图片

`GET /image/{file_id}{extension}`

## 交流群

- Telegram 群组：[@TGIMGHub](https://t.me/TGIMGHub)

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License

## 鸣谢

- [FastAPI](https://fastapi.tiangolo.com/)
- [python-telegram-bot](https://python-telegram-bot.org/)
- [Caddy](https://caddyserver.com/)