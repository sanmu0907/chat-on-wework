# Chat-on-WeWork

> 企业微信AI聊天机器人 - 支持多种AI引擎和智能插件

基于 [dify-on-wechat](https://github.com/hanfangyuan4396/dify-on-wechat) 深度定制，专注于企业微信通道的稳定性和功能增强。

## ✨ 核心特性

### 🤖 多AI引擎支持
- **Dify平台** - Chatbot/Agent/Workflow完整支持
- **豆包AI** - 字节跳动豆包对话 + Seedream 4.5图片生成
- **OpenAI系列** - GPT-4o、GPT-4-turbo、GPT-3.5等
- **国产大模型** - DeepSeek、文心一言、月之暗面、通义千问等
- **Claude、Gemini** - 多模态模型支持

### 🎨 强大的AI生图能力
- **豆包Seedream** - 一次生成4张高质量图片，支持引用消息生图
- **即梦AI** - 图片和视频生成
- **魔搭社区** - ModelScope平台图片生成
- **智谱AI** - CogView-4图片生成
- **z-image** - FLUX.1-schnell快速生图

### 🔧 企业微信通道优化
- ✅ **稳定可靠** - 基于ntwork库深度优化
- ✅ **图片缓存系统** - 支持引用识图，3天持久化缓存
- ✅ **多图连发** - 完美支持豆包4图、批量图片发送
- ✅ **消息格式增强** - @提及、引用消息、表情回复
- ✅ **群聊优化** - 白名单、前缀触发、关键词自动回复

### 🔌 丰富的插件生态

**核心增强插件**：
- 🤖 **Doubao** - 豆包AI全能助手
  - 💬 对话 + 🎨 Seedream 4.5图片生成（4张图）
  - 🚀 **超能模式**：深度推理、多轮搜索、浏览器操作
  - 🎵 **音乐生成**：一键生成歌曲（含歌词、曲谱）
  - 🎙️ **播客生成**：网页链接秒变双人播客
  - 🔗 引用消息识图
- 🎨 **Jimeng** - 多平台AI生图（即梦/魔搭/智谱/通义）+ 视频生成
- 📚 **MMM** - 多媒体图库（美女/黑丝/JK/白丝等）

**基础功能插件**：
- **godcmd** - 管理员命令控制
- **keyword** - 关键词自动回复
- **banwords** - 敏感词过滤
- **jina_sum** - 文章链接智能总结
- **custom_dify_app** - 多群切换不同Dify应用

## 🎯 项目定位

原项目支持多种通道（gewechat、飞书、钉钉、企业微信等），本项目**专注于企业微信（WeWork）通道**：
- 深度优化企业微信的稳定性和兼容性
- 增强图片识别和多图发送能力
- 集成豆包AI等企业微信场景常用功能
- 提供完整的开发文档和调试工具

⚠️ **如果你使用其他通道**（飞书/钉钉/个人微信），建议使用 [原项目](https://github.com/hanfangyuan4396/dify-on-wechat)

## 📦 快速开始

### 环境要求
- Python 3.10+
- Windows系统（企业微信客户端限制）
- 企业微信客户端 4.0.8.6027（版本锁定）

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/samu0907/chat-on-wework.git
cd chat-on-wework
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置文件**
```bash
# 复制配置模板
cp config-template.json config.json

# 编辑config.json，配置必要参数：
# - channel_type: "wework"
# - model: 选择AI引擎（dify、chatgpt、coze等）
# - dify相关配置（如使用dify）
```

4. **启动应用**
```bash
# 先登录企业微信客户端 4.0.8.6027
python app.py
```

详细安装指南请参考：[INSTALL.md](INSTALL.md)

## 📖 使用指南

### 基本对话
```
# 私聊：直接发消息或使用前缀
你好

# 群聊：@机器人或使用前缀
@机器人 帮我写一首诗
```

### 豆包AI功能
```
# 基础对话
豆包 今天天气怎么样？

# 图片生成（4张）
豆包 画一只可爱的小猫

# 引用消息生成（推荐）
1. 发送文本描述："一只金毛犬在海边奔跑"
2. 引用该消息后回复："豆包"
3. 机器人使用引用内容生成4张图片

# 🆕 超能模式（深度推理）
超能 帮我设计一个英语学习网站的完整方案
深度思考 制作一份AI自习室的市场调研报告

# 🆕 音乐生成
音乐 写一首关于春天的歌
作曲 夕阳下的海边，温暖而浪漫

# 🆕 播客生成
播客 https://cloud.tencent.com/developer/news/2592222
podcast 人工智能的发展历史和未来趋势
```

### 多平台生图
```
即梦 赛博朋克城市          # 即梦AI生图
魔搭 科幻未来城市          # 魔搭社区生图
智谱 夕阳下的海滩          # 智谱AI生图
通义 可爱的动漫角色        # z-image快速生图
jimeng 一只狗在跑步        # 即梦视频生成
```

### 管理命令
```
#help               # 查看帮助
#reset              # 重置会话
#installp doubao    # 安装插件
```

更多使用方法请参考：[QUICKSTART.md](QUICKSTART.md)

## 🆚 与原项目对比

| 特性 | 原项目 | Chat-on-WeWork |
|------|--------|----------------|
| 支持通道 | 多通道 | **专注企业微信** |
| 企业微信稳定性 | 基础 | ✅ 深度优化 |
| 图片缓存系统 | 基础 | ✅ 引用识图+持久化 |
| 多图发送 | 单图 | ✅ 豆包4图+批量 |
| 豆包AI | ❌ | ✅ 对话+4图生成 |
| 多平台生图 | 部分 | ✅ 5个平台 |
| 开发文档 | README | ✅ CLAUDE.md完整指南 |
| 插件依赖管理 | 手动 | ✅ 自动安装 |

## 📚 文档导航

- [安装指南](INSTALL.md) - 详细的安装和配置步骤
- [快速开始](QUICKSTART.md) - 5分钟上手指南
- [开发文档](CLAUDE.md) - 架构说明和开发指南
- [部署指南](DEPLOY.md) - 生产环境部署
- [更新日志](CHANGELOG.md) - 版本更新记录

### 插件文档
- [Doubao插件](plugins/doubao/README.md) - 豆包AI使用指南
- [Jimeng插件](plugins/jimeng/README.md) - 多平台生图指南
- [MMM插件](plugins/mmm/README.md) - 多媒体库使用

## 🛠️ 开发调试

项目提供完整的开发工具：

```bash
# 检查企业微信连接
python check_wework.py

# 调试ntwork库
python debug_ntwork.py

# 测试企业微信通信
python test_wework_connection.py

# 查看依赖
python scan_dependencies.py
```

开发指南请参考：[CLAUDE.md](CLAUDE.md)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 开源协议

本项目采用 MIT 协议开源。

## 🙏 致谢

- [dify-on-wechat](https://github.com/hanfangyuan4396/dify-on-wechat) - 原始项目
- [chatgpt-on-wechat](https://github.com/zhayujie/chatgpt-on-wechat) - 上游项目
- [ntwork](https://github.com/smallevilbeast/ntwork) - 企业微信协议库
- [Dify](https://github.com/langgenius/dify) - LLMOps平台

## 📮 联系方式

- 作者：samu0907
- Email：1813145020@qq.com
- GitHub：[@samu0907](https://github.com/samu0907)

---

⭐ 如果这个项目对你有帮助，请给个Star支持一下！
