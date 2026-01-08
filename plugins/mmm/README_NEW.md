# MMM 美图插件

一个功能丰富的美图插件，支持多种图片类型和关键词触发，已重构适配 dify-on-wechat 项目。

## 功能特性

### 图片类型
- **美女图片**: 关键词 "美女"、"666"、"妹子"
- **黑丝图片**: 关键词 "黑丝"
- **JK图片**: 关键词 "jk"、"JK"
- **白丝图片**: 关键词 "白丝"
- **诱惑图片**: 关键词 "诱惑"、"性感"

### 技术特性
- **多API支持**: 美女图片支持4个备用API，自动切换
- **智能重定向**: 自动处理HTTP重定向
- **JSON响应支持**: 支持返回图片URL的JSON格式API
- **容错机制**: API失败时自动尝试备用接口
- **临时文件管理**: 自动创建缓存目录和临时文件
- **关键词触发**: 消息中包含关键词即可触发

## 配置说明

### 基础配置

```json
{
  "enabled": false,  // 是否启用插件（默认false，需要手动启用）
  "triggers": {
    "美女": ["美女", "666", "妹子"],
    "黑丝": ["黑丝"],
    "JK": ["jk", "JK"],
    "白丝": ["白丝"],
    "诱惑": ["诱惑", "性感"]
  }
}
```

### API配置

```json
{
  "image_apis": {
    "美女": [
      "https://api.btstu.cn/sjbz/api.php?lx=dongman&format=images&method=mobile&lx=meizi",
      "https://cdn.seovx.com/?mom=302",
      "https://api.mhimg.cn/api/girls_img/?type=img",
      "https://api.mhimg.cn/api/Welfare_img/"
    ],
    "黑丝": "http://api.yujn.cn/api/heisi.php",
    "JK": "http://api.yujn.cn/api/jk.php",
    "白丝": "http://api.yujn.cn/api/baisi.php",
    "诱惑": "http://api.yujn.cn/api/yht.php"
  }
}
```

### 高级设置

```json
{
  "settings": {
    "timeout": 10,           // API请求超时时间（秒）
    "max_redirects": 3,      // 最大重定向次数
    "cache_dir": "tmp/mmm_cache"  // 缓存目录
  }
}
```

## 使用方法

### 启用插件

1. 编辑 `plugins/mmm/config.json`
2. 将 `"enabled": false` 改为 `"enabled": true`
3. 编辑 `plugins/plugins.json`
4. 将 MMM 插件的 `"enabled": false` 改为 `"enabled": true`
5. 重启应用

### 触发方式

在消息中包含任意触发关键词即可：

**示例**：
- "今天天气真好666" → 触发美女图片
- "黑丝小姐姐" → 触发黑丝图片
- "jk制服很可爱" → 触发JK图片
- "白丝真好看" → 触发白丝图片
- "诱惑" → 触发诱惑图片

### 自定义触发词

编辑 `config.json` 中的 `triggers` 配置：

```json
{
  "triggers": {
    "美女": ["美女", "666", "妹子", "你的自定义关键词"],
    "黑丝": ["黑丝", "hs"]
  }
}
```

## 与原版的差异

### 架构变化
- ✅ 从 AstrBot 框架迁移到 dify-on-wechat 框架
- ✅ 从异步架构(aiohttp)改为同步架构(requests)
- ✅ 使用 Plugin 基类和事件系统
- ✅ 使用 Reply 对象返回结果

### 功能调整
- ✅ 保留所有图片类型和API
- ✅ 保留关键词触发机制
- ✅ 保留重定向处理
- ✅ 保留多API备份
- ❌ 移除未实现的视频功能（可以在后续版本添加）
- ❌ 移除 AstrBot 特有的命令系统（改用关键词触发）

### 改进
- ✅ 更清晰的配置结构
- ✅ 更好的日志记录
- ✅ 更强的容错机制
- ✅ 支持 JSON 格式的API响应

## 技术实现

### 核心逻辑
```python
1. 检测消息中的触发关键词
2. 根据关键词确定图片类型
3. 从配置中获取对应的API
4. 下载图片（处理重定向和JSON）
5. 保存到临时文件
6. 返回图片Reply
```

### API类型支持
- **直接图片**: 返回图片二进制流
- **重定向**: 通过301/302跳转到图片URL
- **JSON**: 返回包含图片URL的JSON对象

### 容错策略
- 美女图片：随机尝试所有备用API
- 其他类型：处理重定向和JSON解析
- 所有失败：返回友好的错误提示

## 依赖要求

- `requests` - HTTP请求（项目已包含）
- `tempfile` - 临时文件（Python标准库）

## 兼容性

- ✅ 支持私聊和群聊
- ✅ 支持企业微信
- ✅ 兼容 dify-on-wechat 框架
- ✅ 兼容所有支持的消息平台

## 注意事项

1. **默认禁用**: 插件默认是关闭的，需要手动启用
2. **API稳定性**: 第三方API可能不稳定，建议配置多个备用
3. **内容合规**: 请确保使用符合法律法规和平台规范
4. **流量控制**: 建议在群聊中谨慎使用，避免频繁触发

## 排障指南

### 插件未生效
1. 检查 `config.json` 中 `enabled` 是否为 `true`
2. 检查 `plugins.json` 中 MMM 是否启用
3. 查看日志确认插件是否初始化成功

### 图片无法获取
1. 检查网络连接
2. 查看日志中的API请求失败信息
3. 尝试更换其他API
4. 检查超时设置是否合理

### 关键词不触发
1. 检查关键词配置是否正确
2. 确认消息内容包含完整关键词
3. 查看日志中的关键词检测信息

## 版本历史

### v1.0 (2025-11)
- ✅ 从 AstrBot 框架重构到 dify-on-wechat
- ✅ 实现所有核心功能
- ✅ 优化配置结构
- ✅ 增强错误处理

## 许可证

本插件遵循项目许可证，仅供学习和娱乐使用。

---

**重构作者**: Assistant
**原作者**: your_name
**项目**: dify-on-wechat
