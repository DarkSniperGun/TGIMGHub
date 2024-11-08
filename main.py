from fastapi import FastAPI, UploadFile, HTTPException, Response, File, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from telegram.ext import Application
from telegram import Bot
from typing import Optional
import aiohttp
import io
import config
import logging
import sys
import traceback
from urllib.parse import quote
import mimetypes

# 设置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# 全局bot实例
bot = None

# 使用 lifespan 替代 on_event
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    global bot
    try:
        bot = Bot(token=config.BOT_TOKEN)
        me = await bot.get_me()
        logger.info(f"Bot initialized successfully: {me.username}")
    except Exception as e:
        logger.error(f"Failed to initialize bot: {e}")
        raise
    
    yield
    
    # 关闭时执行
    if bot:
        await bot.close()

app = FastAPI(lifespan=lifespan)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.post("/upload/")
async def upload_image(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None)
):
    global bot
    try:
        # 验证密码
        if config.UPLOAD_PASSWORD:  # 如果设置了密码
            if not authorization:
                return JSONResponse(
                    status_code=401,
                    content={"success": False, "error": "需要密码"}
                )
            if authorization != f"Bearer {config.UPLOAD_PASSWORD}":
                return JSONResponse(
                    status_code=403,
                    content={"success": False, "error": "密码错误"}
                )

        if not bot:
            logger.error("Bot not initialized")
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Bot not initialized"}
            )

        logger.info(f"开始接收文件: {file.filename}")
        
        # 检查文件大小（20MB 限制）
        content = await file.read()
        file_size = len(content)
        if file_size > 20 * 1024 * 1024:  # 20MB in bytes
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "文件大小不能超过20MB"}
            )

        logger.info(f"文件大小: {file_size} bytes")
        
        # 创建内存文件对象
        file_obj = io.BytesIO(content)
        file_obj.seek(0)

        # 测试频道ID
        logger.info(f"使用的频道ID: {config.CHANNEL_ID}")
        
        # 获取文件扩展名
        file_ext = get_file_extension(file.filename)
        logger.info(f"文件扩展名: {file_ext}")
            
        try:
            # 发送到Telegram
            logger.info("开始发送到Telegram")
            if file.content_type.startswith('image/'):
                message = await bot.send_photo(
                    chat_id=config.CHANNEL_ID,
                    photo=file_obj
                )
                file_id = message.photo[-1].file_id
            else:
                message = await bot.send_document(
                    chat_id=config.CHANNEL_ID,
                    document=file_obj,
                    filename=file.filename
                )
                file_id = message.document.file_id
                
            logger.info("Telegram发送成功")
            logger.info(f"获取到file_id: {file_id}")
            
            # URL 安全的文件名处理
            safe_filename = quote(file.filename)
            download_url = f"{config.BASE_URL}/file/{file_id}/{safe_filename}"
            
            response_data = {
                "success": True,
                "url": download_url,
                "file_id": file_id,
                "filename": safe_filename,
                "size": file_size,
                "content_type": file.content_type
            }
            
            logger.info(f"返回数据: {response_data}")
            return JSONResponse(content=response_data)
            
        except Exception as e:
            logger.error(f"Telegram错误: {str(e)}")
            logger.error(traceback.format_exc())
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": f"Telegram错误: {str(e)}"}
            )
            
    except Exception as e:
        logger.error(f"上传错误: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"上传错误: {str(e)}"}
        )

# 添加一个获取文件扩展名的函数
def get_file_extension(filename: str) -> str:
    """从文件名中获取扩展名，包括点号"""
    if not filename:
        return '.jpg'  # 默认扩展名
    
    # 分割文件名并获取扩展名
    parts = filename.rsplit('.', 1)
    if len(parts) > 1:
        ext = parts[1].lower()
        # 检查是否是支持的图片格式
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            return f'.{ext}'
    
    return '.jpg'  # 如果没有有效扩展名，返回默认值

# 修改图片获取端点以处理带扩展名的URL
@app.get("/image/{file_id}{ext:path}")
async def get_image(file_id: str, ext: str = '.jpg'):
    try:
        logger.info(f"接收到请求 - file_id: {file_id}, ext: {ext}")
        
        # 清理 file_id，移除扩展名和任何额外的点号
        real_file_id = file_id
        if '.' in real_file_id:
            real_file_id = real_file_id.split('.')[0]
        
        logger.info(f"处理后的 file_id: {real_file_id}")
        
        if not real_file_id:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "file_id不能为空"}
            )
        
        # 设置正确的content type
        content_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        
        content_type = content_type_map.get(ext.lower(), 'image/jpeg')
        
        global bot
        if not bot:
            logger.error("Bot not initialized")
            try:
                bot = Bot(token=config.BOT_TOKEN)
                logger.info("Bot重新初始化成功")
            except Exception as e:
                logger.error(f"Bot重新初始化失败: {str(e)}")
                return JSONResponse(
                    status_code=500,
                    content={"success": False, "error": "Bot初始化失败"}
                )

        # 获取文件信息
        try:
            logger.info(f"正在从Telegram获取文件信息... file_id: {real_file_id}")
            file = await bot.get_file(real_file_id)
            logger.info(f"成功获取文件信息, 文件路径: {file.file_path}")
        except Exception as e:
            logger.error(f"获取Telegram文件信息失败: {str(e)}")
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": f"获取文件信息失败: {str(e)}"}
            )

        # 下载文件
        try:
            logger.info(f"开始从Telegram下载文件: {file.file_path}")
            async with aiohttp.ClientSession() as session:
                async with session.get(file.file_path) as response:
                    logger.info(f"Telegram响应状态码: {response.status}")
                    
                    if response.status == 200:
                        content = await response.read()
                        content_length = len(content)
                        logger.info(f"成功下载文件，大小: {content_length} bytes")
                        
                        # 获取内容类型
                        content_type = response.headers.get('Content-Type', 'image/jpeg')
                        logger.info(f"文件类型: {content_type}")
                        
                        # 设置响应头
                        headers = {
                            "Content-Type": content_type,
                            "Content-Length": str(content_length),
                            "Cache-Control": "public, max-age=31536000",
                            "Access-Control-Allow-Origin": "*"
                        }
                        
                        return Response(
                            content=content,
                            headers=headers,
                            media_type=content_type
                        )
                    else:
                        error_text = await response.text()
                        logger.error(f"下载文件失败，状态码: {response.status}, 错误: {error_text}")
                        return JSONResponse(
                            status_code=response.status,
                            content={"success": False, "error": f"下载文件失败: {error_text}"}
                        )
                        
        except aiohttp.ClientError as e:
            logger.error(f"下载文件时网络错误: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": f"下载文件时网络错误: {str(e)}"}
            )
        except Exception as e:
            logger.error(f"下载文件时发生未知错误: {str(e)}")
            logger.error(traceback.format_exc())
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": f"下载文件时发生错误: {str(e)}"}
            )
            
    except Exception as e:
        logger.error(f"处理请求时发生错误: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"处理请求时发生错误: {str(e)}"}
        )

# 新的文件获取端点
@app.get("/file/{file_id}/{filename}")
async def get_file(file_id: str, filename: str):
    try:
        # URL 解码文件名
        from urllib.parse import unquote
        decoded_filename = unquote(filename)
        logger.info(f"接收到文件请求 - file_id: {file_id}, filename: {decoded_filename}")
        
        if not file_id:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "file_id不能为空"}
            )
        
        global bot
        if not bot:
            logger.error("Bot not initialized")
            try:
                bot = Bot(token=config.BOT_TOKEN)
                logger.info("Bot重新初始化成功")
            except Exception as e:
                logger.error(f"Bot重新初始化失败: {str(e)}")
                return JSONResponse(
                    status_code=500,
                    content={"success": False, "error": "Bot初始化失败"}
                )

        # 获取文件信息
        try:
            logger.info(f"正在从Telegram获取文件信息... file_id: {file_id}")
            file = await bot.get_file(file_id)
            logger.info(f"成功获取文件信息, 文件路径: {file.file_path}")
        except Exception as e:
            logger.error(f"获取Telegram文件信息失败: {str(e)}")
            logger.error(traceback.format_exc())
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": f"获取文件信息失败: {str(e)}"}
            )

        # 下载文件
        try:
            logger.info(f"开始从Telegram下载文件: {file.file_path}")
            async with aiohttp.ClientSession() as session:
                async with session.get(file.file_path) as response:
                    logger.info(f"Telegram响应状态码: {response.status}")
                    
                    if response.status == 200:
                        content = await response.read()
                        content_length = len(content)
                        logger.info(f"成功下载文件，大小: {content_length} bytes")
                        
                        # 设置正确的content type
                        content_type = get_content_type(decoded_filename)
                        logger.info(f"文件类型: {content_type}")
                        
                        # 修改 Content-Disposition header
                        headers = {
                            "Content-Type": content_type,
                            "Content-Length": str(content_length),
                            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(decoded_filename)}",
                            "Cache-Control": "public, max-age=31536000",
                            "Access-Control-Allow-Origin": "*"
                        }
                        
                        return Response(
                            content=content,
                            headers=headers,
                            media_type=content_type
                        )
                    else:
                        error_text = await response.text()
                        logger.error(f"下载文件失败，状态码: {response.status}, 错误: {error_text}")
                        return JSONResponse(
                            status_code=response.status,
                            content={"success": False, "error": f"下载文件失败: {error_text}"}
                        )
                        
        except aiohttp.ClientError as e:
            logger.error(f"下载文件时网络错误: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": f"下载文件时网络错误: {str(e)}"}
            )
        except Exception as e:
            logger.error(f"下载文件时发生错误: {str(e)}")
            logger.error(traceback.format_exc())
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": f"下载文件时发生错误: {str(e)}"}
            )
            
    except Exception as e:
        logger.error(f"处理请求时发生错误: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"处理请求时发生错误: {str(e)}"}
        )

def get_content_type(filename: str) -> str:
    """获取文件的 MIME 类型"""
    content_type, _ = mimetypes.guess_type(filename)
    if not content_type:
        # 如果无法确定类型，对于二进制文件返回通用二进制类型
        if filename.endswith(('.exe', '.dll', '.bin')):
            return 'application/octet-stream'
        # 对于文本文件返回文本类型
        elif filename.endswith(('.txt', '.log', '.py', '.js', '.html', '.css')):
            return 'text/plain'
        else:
            return 'application/octet-stream'
    return content_type

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=21351,  # 使用你的端口
        log_level="debug"
    )