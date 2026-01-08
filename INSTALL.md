# 依赖安装指南

## ⚠️ 重要：Python 版本要求

**如果使用企业微信 (wework) 通道，必须使用 Python 3.10.x！**

- ✅ **支持**: Python 3.10.0 ~ 3.10.x
- ❌ **不支持**: Python 3.9, 3.11, 3.12 或更高版本
- **原因**: ntwork 依赖仅为 Python 3.10 编译的二进制扩展 (`wcprobe.cp310-win_amd64.pyd`)
- **建议**: 使用虚拟环境锁定 Python 3.10.x

其他通道（gewechat, wechatmp 等）无此限制。

## 重要提示：自动安装功能

**从现在开始，项目会在启动时自动安装已启用插件的依赖！**

- 首次启动或添加新插件后，程序会自动检测并安装 `plugins/<plugin_name>/requirements.txt` 中列出的依赖
- 只会为 `plugins/plugins.json` 中 `enabled: true` 的插件安装依赖
- 依赖安装过程会在日志中显示，如果安装失败会有警告提示
- 你仍然可以手动安装插件依赖（见下文），但通常不再需要

**你只需要安装主项目依赖即可！**

## 主项目依赖

### 安装所有核心依赖
```bash
pip install -r requirements.txt
```

### 依赖说明

#### 必需依赖
- `requests` - HTTP 请求库
- `Pillow` - 图片处理
- `web.py` - Web 框架 (gewechat channel 需要)
- `qrcode`, `pyqrcode` - 二维码生成

#### Bot API 依赖 (根据使用的 bot_type 选择安装)
- `openai` - OpenAI/ChatGPT
- `anthropic` - Claude
- `zhipuai` - 智谱 AI
- `dashscope` - 阿里云通义千问
- `google-generativeai` - Google Gemini
- `broadscope-bailian` - 百炼

#### Channel 依赖 (根据使用的 channel_type 选择安装)
- `wechatpy` - 微信公众号 (wechatmp, wechatmp_service)
- `dingtalk-stream` - 钉钉
- `curl-cffi` - HTTP 客户端 (某些 channel 需要)

#### 特殊依赖
- `ntwork` - 企业微信 (wework channel, Windows only)
  - **⚠️ 重要**: **必须使用 Python 3.10.x**（不支持 3.9/3.11/3.12）
  - **原因**: ntwork 依赖预编译的二进制扩展 `wcprobe.cp310-win_amd64.pyd`，仅为 Python 3.10 编译
  - **安装**: 需要从 .whl 文件手动安装，不在 PyPI 上
  - **企业微信版本**: 需要企业微信客户端版本 4.0.8.6027（不可升级）
  - **操作系统**: 仅支持 Windows（使用 COM 自动化）
  - **功能限制**: 不支持发送音乐卡片（可用链接卡片替代）

## 插件依赖

每个插件都有自己的 `requirements.txt` 文件,位于 `plugins/<plugin_name>/requirements.txt`

### 安装单个插件依赖
```bash
pip install -r plugins/<plugin_name>/requirements.txt
```

### 安装所有插件依赖

**注意：通常不需要手动安装！** 程序启动时会自动安装已启用插件的依赖。

仅在以下情况需要手动安装：
- 自动安装失败
- 想在启动前预先安装所有依赖

```bash
# Linux/Mac
for plugin in plugins/*/requirements.txt; do pip install -r "$plugin"; done

# Windows PowerShell
Get-ChildItem -Path plugins\*\requirements.txt | ForEach-Object { pip install -r $_.FullName }
```

### 插件依赖列表

#### 已启用插件 (有额外依赖)
- **ChatSummary**: chatgpt_tool_hub, tiktoken, schedule, Jinja2, playwright
- **difytimetask**: arrow, openpyxl, croniter
- **flow2api**: fastapi, uvicorn, aiosqlite, pydantic, curl-cffi, tomli, bcrypt, python-multipart, python-dateutil
- **mmm**: aiohttp
- **moda**: aiohttp

#### 其他插件
- **Apilot, bdunit, helloplus, jimeng, jina_sum, keyword**: requests (已包含在主项目依赖中)
- **banwords, dungeon, finish, godcmd**: 无额外依赖

## 在新电脑上部署

### 1. 克隆/复制项目
```bash
git clone <repository_url>
cd dify-on-wechat
```

### 2. 创建虚拟环境 (推荐)
```bash
# Linux/Mac
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. 安装主项目依赖
```bash
pip install -r requirements.txt
```

### 4. 配置文件
```bash
# 复制配置模板
cp config-template.json config.json
# 编辑 config.json,填入你的配置
```

### 5. 启动程序
```bash
python app.py
```

**首次启动时，程序会自动检测并安装所有已启用插件的依赖！**

你会在日志中看到类似这样的输出：
```
[INFO] Checking and installing plugin requirements...
[INFO] Installing requirements for plugin ChatSummary...
[INFO] Successfully installed requirements for plugin ChatSummary
[INFO] Installing requirements for plugin difytimetask...
[INFO] Successfully installed requirements for plugin difytimetask
...
```

### 6. 特殊依赖处理

#### Enterprise WeChat (Windows only)
如果使用 wework channel:
1. 安装企业微信客户端 4.0.8.6027 版本
2. 从项目提供的 .whl 文件安装 ntwork:
   ```bash
   pip install ntwork-xxx.whl
   ```

#### 语音处理 (可选)
如果需要语音功能,取消 requirements.txt 中相关依赖的注释并安装:
```bash
pip install pydub SpeechRecognition gTTS pyttsx3 baidu-aip
# 还需要安装 ffmpeg
```

#### Playwright (ChatSummary 插件)
如果使用 ChatSummary 插件:
```bash
pip install -r plugins/ChatSummary/requirements.txt
playwright install  # 安装浏览器驱动
```

## 常见问题

### 1. pip 安装速度慢
使用国内镜像源:
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 2. 某些包安装失败
- Windows 用户可能需要安装 Visual C++ Build Tools
- 某些包可能需要特定的系统依赖 (如 ffmpeg)

### 3. 版本冲突
如果遇到版本冲突,可以尝试:
```bash
pip install --upgrade pip
pip install -r requirements.txt --upgrade
```

## 最小化安装

如果只使用特定的 bot 和 channel,可以只安装必需的依赖:

### 最小核心
```bash
pip install requests Pillow
```

### + Dify bot
不需要额外依赖 (Dify API 通过 requests 调用)

### + Gewechat channel
```bash
pip install web.py qrcode
```

### + 微信公众号 channel
```bash
pip install wechatpy
```

根据实际使用的功能按需安装即可。
