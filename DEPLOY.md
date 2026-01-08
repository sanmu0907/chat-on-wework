# Dify-on-WeChat 快速部署指南

本文档说明如何将打包好的项目部署到新的服务器/电脑上。

## 📦 前置要求

### 系统要求
- **操作系统**: Windows / Linux / macOS
- **Python**: >= 3.8
- **网络**: 能访问 PyPI (或配置国内镜像源)
- **磁盘空间**: 至少 500MB

### 特定渠道要求
- **企业微信 (wework)**: 仅支持 Windows,需要企业微信客户端 4.0.8.6027

## 🚀 快速部署步骤

### 步骤 1: 解压项目文件

**Windows:**
```cmd
# 右键解压 ZIP 文件，或使用命令行
powershell Expand-Archive -Path dify-on-wechat_*.zip -DestinationPath .
cd dify-on-wechat
```

**Linux/Mac:**
```bash
# 解压 tar.gz
tar -xzf dify-on-wechat_*.tar.gz
cd dify-on-wechat

# 或解压 zip
unzip dify-on-wechat_*.zip
cd dify-on-wechat
```

### 步骤 2: 运行环境检查

**运行检查脚本（推荐）:**
```bash
python check_deploy.py
```

这个脚本会自动检查:
- ✓ Python 版本
- ✓ pip 工具
- ✓ 项目文件完整性
- ✓ 网络连接
- ✓ 目录权限
- ✓ 已安装的依赖

根据检查结果解决任何问题。

### 步骤 3: 创建虚拟环境（推荐但可选）

**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 步骤 4: 安装依赖

**基础安装:**
```bash
pip install -r requirements.txt
```

**使用国内镜像源（如果 PyPI 访问慢）:**
```bash
# 清华源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 阿里源
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 腾讯源
pip install -r requirements.txt -i https://mirrors.cloud.tencent.com/pypi/simple
```

**注意**: 插件依赖会在首次启动时自动安装，无需手动安装。

### 步骤 5: 配置项目

**复制配置模板:**
```bash
# Linux/Mac
cp config-template.json config.json

# Windows
copy config-template.json config.json
```

**编辑配置文件 `config.json`:**

最小化配置示例（Dify + wework）:
```json
{
  "channel_type": "wework",
  "model": "dify",
  "dify_api_base": "https://api.dify.ai/v1",
  "dify_api_key": "app-你的密钥",
  "dify_app_type": "chatbot",

  "single_chat_prefix": [""],
  "group_chat_prefix": ["@bot"],
  "group_name_white_list": ["ALL_GROUP"]
}
```

详细配置说明请查看 `config-template.json` 中的注释。

### 步骤 6: 启动项目

**前台启动（调试用）:**
```bash
python app.py
```

**后台启动:**

**Linux/Mac:**
```bash
nohup python app.py > run.log 2>&1 &

# 查看日志
tail -f run.log

# 停止
ps -ef | grep app.py | grep -v grep
kill <PID>
```

**Windows:**
```cmd
# 使用 start.bat (如果存在)
start.bat

# 或创建快捷方式指向 pythonw.exe app.py

# 停止：任务管理器结束 python.exe 进程
```

**首次启动说明:**
- 首次启动会自动安装已启用插件的依赖
- 日志会显示安装进度
- 如果有网络问题，依赖安装可能失败（见故障排除）

### 步骤 7: 验证运行

**检查日志:**
```bash
# Linux/Mac
tail -f run.log

# Windows
type run.log
```

**成功启动的标志:**
```
[INFO] Checking and installing plugin requirements...
[INFO] Successfully installed requirements for plugin XXX
...
[INFO] [WX] Start auto replying in X seconds...
或
[INFO] [wework] wework started
```

**发送测试消息:**
根据你配置的 `single_chat_prefix` 和 `group_chat_prefix`，发送消息测试。

## 🔧 故障排除

### 问题 1: Python 版本不满足要求

**症状:** `check_deploy.py` 提示 Python 版本 < 3.8

**解决:**
- 安装 Python 3.8 或更高版本
- 使用 `python3` 而不是 `python` 命令

### 问题 2: pip 安装依赖失败

**症状:** `pip install` 报错或超时

**解决方案 A - 使用镜像源:**
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**解决方案 B - 升级 pip:**
```bash
python -m pip install --upgrade pip
```

**解决方案 C - 单独安装失败的包:**
```bash
# 查看哪个包失败
pip install <package_name>
```

### 问题 3: 插件依赖自动安装失败

**症状:** 启动时提示 `[WARN] Failed to install requirements for plugin XXX`

**解决:**
```bash
# 手动安装该插件的依赖
pip install -r plugins/<plugin_name>/requirements.txt

# 或禁用该插件
# 编辑 plugins/plugins.json，将对应插件的 enabled 设为 false
```

### 问题 4: config.json 配置错误

**症状:** 启动报错 `KeyError: 'xxx'` 或 `Invalid config`

**解决:**
- 检查 `config.json` 是否是有效的 JSON（使用 JSON 验证工具）
- 确保必需的配置项都已填写
- 参考 `config-template.json` 和 CLAUDE.md

### 问题 5: 端口被占用

**症状:** `Address already in use` 或类似错误

**解决:**
```bash
# Linux/Mac - 查找占用端口的进程
lsof -i :8080  # 替换为实际端口
kill <PID>

# Windows - 查找并结束进程
netstat -ano | findstr :8080
taskkill /PID <PID> /F
```

### 问题 6: 权限问题

**症状:** `Permission denied` 错误

**Linux/Mac 解决:**
```bash
# 给脚本添加执行权限
chmod +x check_deploy.py
chmod +x app.py

# 或使用 sudo (不推荐)
sudo python app.py
```

**Windows 解决:**
- 以管理员身份运行
- 检查防火墙设置

### 问题 7: 企业微信 (wework) 无法启动

**症状:** `[ERROR] ntwork import failed` 或连接失败

**检查清单:**
- ✓ 仅支持 Windows 系统
- ✓ 企业微信客户端版本必须是 4.0.8.6027
- ✓ ntwork 库已安装（需要从 .whl 文件安装）
- ✓ 企业微信已登录

## 📋 配置检查清单

部署前请确认:

### 必需配置
- [ ] `channel_type` - 选择的渠道
- [ ] `model` - 使用的 bot 类型
- [ ] Bot API 配置（如 `dify_api_key`, `openai_api_key` 等）
- [ ] Channel 配置（根据 channel_type）

### 推荐配置
- [ ] `single_chat_prefix` - 私聊触发前缀
- [ ] `group_chat_prefix` - 群聊触发前缀
- [ ] `group_name_white_list` - 群聊白名单

### 可选配置
- [ ] `temperature` - 回复随机性（0-1）
- [ ] `voice_reply_voice` - 语音回复
- [ ] `image_create_prefix` - 图片生成触发词

## 🔄 更新部署

如果需要更新已部署的项目:

1. **备份配置和数据:**
```bash
cp config.json config.json.backup
cp -r plugins/config.json plugins/config.json.backup
cp -r tmp tmp.backup
```

2. **解压新版本到临时目录:**
```bash
tar -xzf dify-on-wechat_新版本.tar.gz -C /tmp/
```

3. **复制文件（覆盖旧版本）:**
```bash
cp -r /tmp/dify-on-wechat/* /path/to/current/dify-on-wechat/
```

4. **恢复配置:**
```bash
cp config.json.backup config.json
cp plugins/config.json.backup plugins/config.json
```

5. **更新依赖:**
```bash
pip install -r requirements.txt --upgrade
```

6. **重启服务:**
```bash
# 停止旧进程
kill <PID>

# 启动新进程
nohup python app.py > run.log 2>&1 &
```

## 📞 获取帮助

- **文档**: 查看 `INSTALL.md` 和 `CLAUDE.md`
- **Issue**: 访问项目 GitHub 仓库提 Issue
- **检查脚本**: 运行 `python check_deploy.py` 诊断问题

## 🎯 快速参考命令

```bash
# 环境检查
python check_deploy.py

# 安装依赖
pip install -r requirements.txt

# 配置项目
cp config-template.json config.json
# 编辑 config.json

# 启动项目（前台）
python app.py

# 启动项目（后台 Linux/Mac）
nohup python app.py > run.log 2>&1 &

# 查看日志
tail -f run.log

# 查看进程
ps -ef | grep app.py

# 停止项目
kill <PID>
```

祝部署顺利！🎉
