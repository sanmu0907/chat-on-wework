# Dify-on-WeChat 完整迁移指南

本指南说明如何将 Dify-on-WeChat 项目完整迁移到另一台电脑，包含所有配置和数据。

## 🎯 适用场景

✅ **适合你，如果：**
- 想把当前运行的项目原封不动迁移到新电脑
- 需要保留所有配置（API密钥、渠道设置等）
- 需要保留运行数据（缓存、历史记录等）
- 两台电脑系统和Python版本相同或相近

❌ **不适合，如果：**
- 想在不同系统间迁移（如 Windows → Linux）
- 想分享给别人使用（包含你的敏感配置）
- 只想要干净的代码（应该用 `pack.py` 而不是 `pack_full.py`）

## 📦 完整迁移 vs 普通打包

| 特性 | 完整迁移 (pack_full.py) | 普通打包 (pack.py) |
|------|------------------------|-------------------|
| config.json | ✅ 包含 | ❌ 不包含 |
| plugins/config.json | ✅ 包含 | ❌ 不包含 |
| tmp/ 缓存数据 | ✅ 包含 | ❌ 不包含 |
| run.log 日志 | ❌ 不包含* | ❌ 不包含 |
| 虚拟环境 | ❌ 不包含 | ❌ 不包含 |
| 源代码 | ✅ 包含 | ✅ 包含 |
| 依赖清单 | ✅ 包含 | ✅ 包含 |

*可以通过编辑 `.packignore.full` 修改

## 🚀 完整迁移步骤

### 第一步：在源电脑打包

#### 方法 1: 使用批处理脚本（Windows推荐）

```cmd
# 双击运行
pack_full.bat
```

#### 方法 2: 直接运行 Python 脚本

```bash
python pack_full.py
```

**打包过程：**
1. 脚本会扫描所有文件
2. 显示将要打包的重要配置文件
3. 要求确认（包含敏感信息警告）
4. 创建 ZIP 压缩包到 `dist/` 目录

**输出文件：**
```
dist/dify-on-wechat_FULL_YYYYMMDD_HHMMSS.zip
```

### 第二步：传输到目标电脑

选择以下任一方法：

#### 方法 1: U盘/移动硬盘
```bash
# 直接复制 ZIP 文件
```

#### 方法 2: 局域网传输
```bash
# 源电脑（Linux/Mac）
python3 -m http.server 8000

# 目标电脑
# 浏览器访问 http://源电脑IP:8000
# 下载 ZIP 文件
```

#### 方法 3: 云盘
- 上传到百度网盘、阿里云盘等
- 在目标电脑下载

#### 方法 4: SCP（Linux/Mac）
```bash
scp dist/dify-on-wechat_FULL_*.zip user@target:/path/to/
```

### 第三步：在目标电脑部署

#### 3.1 检查 Python 版本

确保目标电脑 Python 版本与源电脑相同或相近：

```bash
python --version
# 或
python3 --version
```

**建议：** 使用相同的 Python 版本（如都是 3.10.x）

#### 3.2 解压文件

**Windows:**
```cmd
# 右键解压或使用命令
powershell Expand-Archive -Path dify-on-wechat_FULL_*.zip -DestinationPath .
cd dify-on-wechat
```

**Linux/Mac:**
```bash
unzip dify-on-wechat_FULL_*.zip
cd dify-on-wechat
```

#### 3.3 安装依赖

**创建虚拟环境（推荐）:**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

**安装依赖:**
```bash
pip install -r requirements.txt
```

如果网络慢，使用镜像源：
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### 3.4 验证配置

检查配置文件是否正确迁移：

```bash
# 检查主配置
cat config.json

# 检查插件配置
cat plugins/plugins.json
```

#### 3.5 启动项目

```bash
python app.py
```

**首次启动会：**
- 自动安装已启用插件的依赖
- 加载你的配置
- 恢复之前的运行状态

## ⚠️ 重要注意事项

### 1. 安全性

**打包文件包含敏感信息：**
- ✅ API 密钥（dify_api_key, openai_api_key 等）
- ✅ 访问令牌（gewechat_token 等）
- ✅ 所有配置的账号信息

**务必做到：**
- ❌ 不要上传到公开的网盘
- ❌ 不要分享给他人
- ❌ 不要提交到 Git 仓库
- ✅ 传输后立即删除临时文件
- ✅ 使用加密传输（如 HTTPS、SFTP）

### 2. 跨系统迁移

**相同系统迁移：** ✅ 无问题
- Windows → Windows
- Linux → Linux
- macOS → macOS

**不同系统迁移：** ⚠️ 可能需要调整

**Windows → Linux/Mac:**
- 路径分隔符不同（`\` vs `/`）
- wework channel 无法使用（仅 Windows）
- 部分依赖可能需要重新安装

**Linux/Mac → Windows:**
- 某些 Linux 特定的包可能不可用
- 文件权限可能需要调整

### 3. Python 版本差异

**相同版本：** ✅ 无问题（如 3.10.5 → 3.10.8）

**不同小版本：** ⚠️ 通常可以（如 3.10 → 3.11）
- 建议重新安装依赖：`pip install -r requirements.txt --upgrade`

**跨大版本：** ❌ 不建议（如 3.9 → 3.11）
- 某些依赖可能不兼容
- 建议在目标电脑安装相同版本 Python

### 4. 企业微信 (wework) 特殊要求

如果使用 wework channel：

**必须满足：**
- ✅ 目标电脑是 Windows 系统
- ✅ 安装企业微信客户端 4.0.8.6027 版本
- ✅ 手动安装 ntwork 库（从 .whl 文件）
- ✅ 登录企业微信账号

### 5. 网络和服务依赖

**gewechat channel:**
- 需要 gewechat 服务在目标电脑上运行
- 或更新 `config.json` 中的 `gewechat_base_url` 为新地址

**其他服务:**
- Dify API - 无需修改（云服务）
- OpenAI API - 无需修改（云服务）

## 🔍 验证迁移成功

### 检查清单

运行以下检查确保迁移成功：

```bash
# 1. 检查 Python 版本
python --version

# 2. 检查配置文件存在
ls config.json
ls plugins/plugins.json

# 3. 检查依赖安装
pip list | grep requests
pip list | grep Pillow

# 4. 测试启动（Ctrl+C 停止）
python app.py
```

### 常见问题

**Q: 启动报错 "ModuleNotFoundError"**
```bash
# 重新安装依赖
pip install -r requirements.txt
```

**Q: 配置文件找不到**
```bash
# 检查是否在正确目录
pwd  # 或 Windows: cd
ls config.json
```

**Q: 依赖安装失败**
```bash
# 使用镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**Q: gewechat 连接失败**
```bash
# 检查 gewechat 服务是否在新电脑运行
# 或更新 config.json 中的地址
```

## 📝 自定义打包内容

如果需要自定义打包内容，编辑 `.packignore.full` 文件：

**包含日志文件：**
```bash
# 注释掉这些行
# run.log
# error.log
# nohup.out
```

**排除临时缓存：**
```bash
# 添加这行
tmp/
```

**包含 Claude Code 配置：**
```bash
# 注释掉这行
# .claude/
```

修改后重新运行 `pack_full.py`。

## 🔄 更新迁移

如果需要再次迁移（更新目标电脑）：

### 方法 1: 完整覆盖

```bash
# 在源电脑
python pack_full.py

# 传输到目标电脑
# 备份旧的（如果需要）
mv dify-on-wechat dify-on-wechat.old

# 解压新的
unzip dify-on-wechat_FULL_*.zip
cd dify-on-wechat
pip install -r requirements.txt
python app.py
```

### 方法 2: 只更新配置

```bash
# 只复制配置文件
scp config.json user@target:/path/to/dify-on-wechat/
scp -r plugins/config.json user@target:/path/to/dify-on-wechat/plugins/
```

## 📊 打包内容清单

完整迁移包含：

### ✅ 包含的文件

**源代码:**
- bot/, channel/, plugins/, lib/, common/, bridge/
- app.py, plugin_manager.py, config.py

**配置文件（重要）:**
- config.json
- plugins/plugins.json
- plugins/config.json（如果存在）

**依赖清单:**
- requirements.txt
- plugins/*/requirements.txt

**文档:**
- INSTALL.md, DEPLOY.md, CLAUDE.md
- README_RESUME.txt

**缓存数据（如果存在）:**
- tmp/ 目录下的文件
- 其他数据文件

### ❌ 不包含的文件

**自动生成的文件:**
- __pycache__/
- *.pyc

**虚拟环境:**
- venv/, env/, .venv/

**版本控制:**
- .git/

**日志文件（默认）:**
- run.log
- error.log
- nohup.out

**打包文件:**
- dist/
- *.zip, *.tar.gz, *.rar

## 🎯 快速参考

### 打包命令
```bash
# Windows
pack_full.bat

# 任何系统
python pack_full.py
```

### 解压命令
```bash
# Windows
powershell Expand-Archive -Path *.zip -DestinationPath .

# Linux/Mac
unzip *.zip
```

### 安装依赖
```bash
pip install -r requirements.txt
```

### 启动项目
```bash
python app.py
```

## ✨ 提示和技巧

### 1. 首次迁移

建议先在测试环境（如虚拟机）验证迁移流程，确保无问题后再在生产环境操作。

### 2. 定期备份

定期创建完整备份：
```bash
# 每周执行一次
python pack_full.py
```

### 3. 版本标记

重命名压缩包添加版本信息：
```bash
mv dify-on-wechat_FULL_*.zip dify-on-wechat_v1.0_backup.zip
```

### 4. 双重保险

保存两份备份在不同位置：
- 本地硬盘
- 云存储（加密）

---

## 📞 需要帮助？

如遇问题：
1. 检查本文档的"常见问题"部分
2. 查看 DEPLOY.md 中的故障排除
3. 运行 `python check_deploy.py` 诊断环境
4. 访问项目 GitHub 提 Issue

祝迁移顺利！🎉
