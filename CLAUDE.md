# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Chat-on-WeWork is a fork of dify-on-wechat focused specifically on Enterprise WeChat (WeWork) channel optimization. It's an AI chatbot framework that integrates multiple AI engines (Dify, OpenAI, ByteDance Doubao, etc.) with Enterprise WeChat.

**Key Architecture**: Channel (WeChat接入) → Bot (AI引擎) → Bridge (消息桥接) → Plugins (功能扩展)

**Project Focus**: Unlike the upstream dify-on-wechat which supports multiple channels, this project is specialized for Enterprise WeChat with deep optimizations for image caching, multi-image sending, quoted message recognition, and stability.

## Running the Application

### Environment Requirements
- Python 3.10+
- **Windows OS** (Enterprise WeChat client limitation)
- **Enterprise WeChat 4.0.8.6027** (version locked - newer versions break ntwork library)

### Dependencies

**Important**: The project automatically installs plugin dependencies on startup!

- Main project dependencies: `pip install -r requirements.txt`
- Plugin dependencies: Automatically installed for enabled plugins from `plugins/<name>/requirements.txt`
- See `INSTALL.md` for detailed installation guide

### Start Application
```bash
python app.py              # Start in foreground (must run after WeCom logged in)
```

**Critical startup sequence for wework channel**:
1. Login to Enterprise WeChat 4.0.8.6027 client first
2. Start `python app.py`
3. Wait for "等待登录······" message
4. System auto-detects login (may take 1-5 minutes)
5. 60s delay for contact/room sync: "静默延迟60s，等待客户端刷新数据"
6. Ready when log shows: "wework程序初始化完成········"

On first startup or after enabling new plugins, the system will automatically detect and install required dependencies.

### Checking Status
```bash
# Windows - check if running
tasklist | findstr python

# View logs (look for latest .output file)
dir /O-D /B C:\Users\Administrator\AppData\Local\Temp\claude\C--Users-Administrator-Desktop-dify-on-wechat\tasks\*.output
```

### Restart Application
On Windows with wework channel:
```bash
# Kill all Python processes
taskkill /F /IM python.exe

# Wait 2 seconds
timeout /t 2 /nobreak

# Restart (ensure WeCom is already logged in)
python app.py
```

## Configuration

**CRITICAL**:
- Never modify `config.py` directly - it only defines available keys
- All configuration changes go in `config.json`
- `config.json` is gitignored - it contains user-specific credentials
- If `config.json` gets reset, restore from `config-template.json` or previous logs

### Configuration Structure
- `config.json` - Active configuration (gitignored, user-specific)
- `config-template.json` - Template for initial setup
- `config.py` - Configuration schema and validation only

### Key Configuration Areas

**Channel Selection** (`channel_type`):
- `wework` - Enterprise WeChat personal account (Windows only, requires 4.0.8.6027)
- `wechatmp` / `wechatmp_service` - WeChat Official Accounts
- `wechatcom_app` - Enterprise WeChat application

**Bot/Model Selection**:
- `model` - Model name (e.g., "gpt-5-mini", "dify", "coze")
- `bot_type` - Bot implementation type (e.g., "openai_proxy", "chatgpt", "dify")
- Common configurations:
  - OpenAI-compatible: `bot_type: "openai_proxy"`, `model: "gpt-4o"`, requires `open_ai_api_key`, `open_ai_api_base`
  - Dify: `model: "dify"`, requires `dify_api_base`, `dify_api_key`, `dify_app_type`
  - Vision models: Separate config like `vision_model: "gemini-2.5-pro"`

**Trigger Configuration** (critical for group chat behavior):
- `single_chat_prefix` - Prefix required for private chat replies (e.g., `[""]` = reply to all)
- `group_chat_prefix` - Prefix required for group chat replies (e.g., `["小白"]` or `[""]`)
- `group_at_off` - If false, @mentions always trigger bot regardless of prefix
- `group_name_white_list` - Whitelist of group names (`["ALL_GROUP"]` for all groups)
- **`group_chat_in_plugin_mode`** - Very important boolean:
  - `true` = All group messages enter plugin system (plugins can handle without prefix)
  - `false` = Only messages with prefix/keyword/@ trigger bot (strict filtering)
- `group_chat_keyword` - Additional keywords to trigger bot (e.g., `["识图"]` for image recognition)

### Configuration File Safety

**Common Issue**: `config.json` sometimes gets accidentally reset to template defaults.

**Prevention**:
- `config.json` is in `.gitignore` - no git backup available
- Always back up working `config.json` manually
- Check logs for config snapshots: `[INIT] load config: {model: ...}` shows loaded config

**Recovery**: If config gets reset:
1. Look in recent log files (`.output` files) for `[INIT] load config:` line
2. Extract working configuration from log
3. Restore critical fields:
   - `bot_type`, `model`
   - API keys: `open_ai_api_key`, `dify_api_key`, etc.
   - Channel settings: `channel_type`, `group_chat_prefix`
   - `group_chat_in_plugin_mode: true` (if using plugins in groups)

## Core Architecture

### Channel Layer (`channel/`)
Handles platform-specific message protocols and formatting.

**Key Files**:
- `chat_channel.py` - Abstract base with message processing pipeline
- `channel_factory.py` - Creates channel instances based on `channel_type`
- `wework/wework_channel.py` - Enterprise WeChat implementation
- `wework/wework_message.py` - Converts ntwork messages to `ChatMessage`

**Message Flow**:
1. Platform receives message → `wework_message.py` parses to `ChatMessage`
2. `wework_channel.py` calls `_compose_context()` to create `Context`
3. Context prefix/keyword matching decides if bot should reply
4. Plugins process via event system (`ON_RECEIVE_MESSAGE`, `ON_HANDLE_CONTEXT`)
5. Bot generates reply
6. `ON_DECORATE_REPLY` plugins can transform reply (e.g., text→image)
7. `_send_reply()` converts `Reply` back to platform format

**Critical Implementation Details**:
- `chat_channel.py:_compose_context()` - Where prefix filtering happens
- Quote message detection for image recognition (lines 101-144)
- Image cache integration for retrieving quoted images
- Random 1-2 second delay before processing (防止限流)

### Bot Layer (`bot/`)
Implements AI provider-specific APIs and session management.

**Structure**:
- `bot_factory.py` - Creates bot instances based on `model` config
- Each provider has subfolder: `openai/`, `openai_proxy/`, `dify/`, `coze/`, etc.
- `*_bot.py` - Main bot logic, handles text/image/voice
- `*_session.py` - Manages conversation context

**Key Bot Types**:
- `openai_proxy/` - Generic OpenAI-compatible proxy (recommended for most APIs)
- `dify/` - Dify platform integration (chatbot/agent/workflow)
- `chatgpt/` - Direct OpenAI API
- `coze/` - ByteDance Coze platform

**Session Management**:
- `session_manager.py` - Maintains per-user conversation history
- Sessions expire based on `expires_in_seconds` (default 3600s)
- Clear with special commands like `#reset` or `#清除记忆`

**Image Recognition Pattern**:
1. Check `ContextType.IMAGE` in `reply()` method
2. Read image file from path, encode to base64
3. Create messages array with `type: "image_url"`
4. Call provider's vision model (separate config from text model)
5. Return text description as `Reply(ReplyType.TEXT, content)`

### Plugin System (`plugins/`)
Event-driven plugin architecture for extending functionality.

**Plugin Lifecycle**:
1. `plugin_manager.py` scans `plugins/` directory for `@plugins.register()` decorators
2. Plugins enabled/disabled + priority set in `plugins/plugins.json`
3. **Automatic dependency installation**: Enabled plugins' `requirements.txt` auto-installed on startup
4. Execution order: highest priority first (999 → -999)

**Dependency Management**:
- Each plugin can have `plugins/<name>/requirements.txt`
- On startup, `_install_plugin_requirements()` auto-installs for enabled plugins
- Manual installation: `#installp <plugin_name>` command

**Key Events** (`event.py`):
- `ON_RECEIVE_MESSAGE` - Before any processing (early inspection/logging)
- `ON_HANDLE_CONTEXT` - After context creation, before bot reply (main processing)
- `ON_DECORATE_REPLY` - Modify reply before sending (e.g., text→image conversion)
- `ON_SEND_REPLY` - After reply sent (logging/tracking)

**Event Action Types**:
- `CONTINUE` - Pass to next plugin/handler
- `BREAK` - Stop event propagation, no further processing
- `BREAK_PASS` - Stop plugin chain but continue to bot

**Plugin Structure**:
```
plugins/plugin_name/
├── __init__.py          # Import and register main class
├── plugin_name.py       # Main plugin code with @plugins.register()
├── config.json          # Plugin configuration (optional, can use plugins/config.json)
├── requirements.txt     # Dependencies (auto-installed if plugin enabled)
└── README.md            # Documentation
```

**Creating Plugins**:
1. Inherit from `Plugin` base class
2. Use `@plugins.register(name, priority, ...)` decorator
3. Override `__init__()` to register event handlers:
   ```python
   self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
   ```
4. Implement event handler methods
5. Use `e_context.action = EventAction.BREAK_PASS` to prevent further processing
6. Use `self.load_config()` to read configuration
7. Add to `plugins/plugins.json` with `enabled: true`

**Built-in Plugins**:
- `godcmd` - Admin commands (priority 999)
- `ChatSummary` - Chat history summarization
- `video_parser` - Extract video links from Douyin/Kuaishou
- `Keyword` - Keyword auto-reply (priority 900)
- `imgbb_upload` - Auto-upload images to imgbb for URL sharing (priority 895)
- `Doubao` - ByteDance Doubao AI with 4-image generation (priority 100)
- `Jimeng` - Multi-platform image/video generation (priority 90)
- `Text2Image` - Convert long text to images (priority 50, uses playwright)
- `JinaSum` - Summarize article links (priority 10)
- `Finish` - Final cleanup (priority -999)

**Important Plugins**:

**Text2Image Plugin** (priority 50):
- Converts long text replies to images to prevent WeChat truncation
- **Three rendering engines**: playwright (default) → pillowmd → imgrender (fallback chain)
- **playwright engine** (recommended): Uses headless Chromium for HTML/CSS rendering
  - Requires: `pip install playwright markdown` + `playwright install chromium`
  - Converts markdown → HTML with GitHub-style CSS → full-page screenshot
  - Produces high-quality images with proper formatting
- Mobile-optimized: 600px width, 15px font, optimized for phone screens
- Triggers when text length ≥ `min_text_length` (default 300 characters)
- Configuration: `plugins/text2image/config.json`
- **CSS customization**: Edit HTML/CSS template in `text2image.py:_render_with_playwright()`
  - Lines 206-335: Full HTML template with inline styles
  - Key CSS areas: list styling (lines 263-283), paragraph/heading/code styles
  - Recent fix: `list-style-position: outside` for proper list item wrapping alignment

**Doubao Plugin** (priority 100):
- Integrates ByteDance Doubao AI
- Features: Text chat + Seedream 4.5 image generation (4 images per request)
- Quote reply support: Quote user's text, reply with "豆包" to generate images
- Configuration: Requires `conversation_id` and `cookie` from browser DevTools
- Commands: `豆包`, `豆`, `doubao`, `db`, `超能`, `agent`, `音乐`, `播客`

**imgbb_upload Plugin** (priority 895):
- Auto-uploads user/bot images to imgbb for permanent URLs
- Replies with imgbb URL for easy sharing
- Configuration: `api_key` required from imgbb.com

### Bridge Layer (`bridge/`)
Defines common data structures for cross-layer communication.

**Key Classes**:
- `Context` - Encapsulates message + metadata (session_id, group_name, receiver, etc.)
- `Reply` - Wraps bot response with type
- `ContextType` - Enum: TEXT, IMAGE, VOICE, VIDEO, IMAGE_CREATE, etc.
- `ReplyType` - Enum: TEXT, IMAGE, IMAGE_URL, VIDEO, VIDEO_URL, FILE, ERROR, etc.

**Important Context Fields**:
- `context['isgroup']` - Boolean, true for group chat
- `context['session_id']` - Format: `{user_id}@@{room_id}` for groups
- `context['receiver']` - Where to send reply (user_id or room_id)
- `context['msg']` - Original ChatMessage object
- `context['origin_ctype']` - Original message type before any transformation

## Common Development Patterns

### Debugging Message Filtering Issues
If bot doesn't reply when expected:

1. **Check config.json**:
   - `group_chat_prefix`: Empty string `[""]` triggers on all, specific prefix like `["小白"]` requires prefix
   - `group_at_off`: Should be `false` to allow @ triggering
   - `group_name_white_list`: Should include group name or `["ALL_GROUP"]`
   - `group_chat_in_plugin_mode`: Should be `true` if you want plugins to see all messages

2. **Search logs** for key indicators:
   - `[chat_channel] consume context:` - If missing, message filtered before processing
   - `No need reply, groupName not in whitelist` - Check whitelist config
   - `[chat_channel]receive group at` - Confirms @ detection
   - Plugin logs show if plugins handled message

3. **Check plugin priorities**: High-priority plugins can `BREAK_PASS` and prevent bot reply

4. **Verify ntwork connection**:
   - Look for "登录信息:>>>user_id:" in logs
   - Check "wework程序初始化完成" message

### Modifying Text2Image Rendering

The Text2Image plugin uses playwright to render markdown as HTML then screenshot. To modify rendering:

**File**: `plugins/text2image/text2image.py`

**Key method**: `_render_with_playwright(text: str)` (lines 172-369)

**Structure**:
1. Lines 188-198: Convert markdown to HTML using python-markdown extensions
2. Lines 201-335: Full HTML template with embedded CSS
3. Lines 206-217: Body styles (font, width, colors, word-wrap)
4. Lines 225-245: Code block styles
5. Lines 246-257: Heading styles
6. **Lines 263-283: List styles** (critical for alignment issues):
   ```python
   ul, ol {{
       padding-left: 2em;
       list-style-position: outside;  # Key for proper wrapping
   }}
   li {{
       padding-left: 0.5em;
       overflow-wrap: break-word;
       line-height: 1.8;
   }}
   ```
7. Lines 337-360: Playwright screenshot logic

**Common customizations**:
- **Mobile width**: Line 214: `max-width: {self.width}px` (currently 600px)
- **Font size**: Line 209: `font-size: {self.font_size}px` (currently 15px)
- **Colors**: Lines 211-212: `color` and `background-color`
- **List alignment**: Lines 263-283 control how list items wrap when text is long
  - `list-style-position: outside` makes bullets stay outside text flow
  - `overflow-wrap: break-word` handles long words/URLs
  - Nested lists: lines 275-278

**Testing changes**:
1. Edit CSS in the template
2. Restart `python app.py`
3. Trigger bot with >300 character response containing markdown lists
4. Check rendered image in `plugins/text2image/cache/pw_*.png`

### Image Recognition Flow
1. User sends image → saved to `tmp/` with timestamp filename
2. Image cached in `ImageCacheManager` (3-day persistent + metadata JSON)
3. **For quoted images** (Enterprise WeChat):
   - Pattern: `「用户名：[图片]」\n---\n识图`
   - `chat_channel.py:101-144` extracts quoted user from regex
   - Looks up user_id from room member cache
   - Retrieves image from `ImageCacheManager.get_image(user_id, room_id)`
4. Image path passed to bot as `Context(ContextType.IMAGE, image_path)`
5. Bot encodes image → sends to vision model → returns text reply

### Image Cache System
Located in `common/image_cache_manager.py`:
- Stores images locally in `tmp/image_cache/YYYY-MM-DD/` organized by date
- Persists for 3 days (configurable via `cache_expire_days`)
- JSON metadata: `tmp/image_cache_metadata.json` tracks all cached images
- Supports both sender images (user uploads) and bot images (bot replies)
- Background cleanup thread runs every 24 hours

**Cache key format**: `{user_id}_{room_id}_{timestamp}` or `{user_id}_{timestamp}` for DM

**Use cases**:
- Quote reply image recognition
- Image upload URL generation (imgbb_upload plugin)
- Persistent image storage beyond runtime memory

### Adding New Plugin

1. Create folder: `plugins/newplugin/`
2. Create `__init__.py`:
   ```python
   from .newplugin import NewPlugin
   ```
3. Create `newplugin.py`:
   ```python
   import plugins
   from plugins import *
   from bridge.context import ContextType
   from bridge.reply import Reply, ReplyType

   @plugins.register(
       name="NewPlugin",
       desire_priority=50,
       hidden=False,
       desc="Plugin description",
       version="1.0.0",
       author="your_name"
   )
   class NewPlugin(Plugin):
       def __init__(self):
           super().__init__()
           self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
           # Load config
           config = self.load_config()

       def on_handle_context(self, e_context: EventContext):
           if e_context['context'].type != ContextType.TEXT:
               return

           content = e_context['context'].content
           # Your logic here

           # To prevent further processing:
           # e_context.action = EventAction.BREAK_PASS

       def get_help_text(self, **kwargs):
           return "Help text for your plugin"
   ```
4. Create `config.json` (optional):
   ```json
   {
       "enabled": true,
       "setting1": "value1"
   }
   ```
5. Add to `plugins/plugins.json`:
   ```json
   "NewPlugin": {
       "enabled": true,
       "priority": 50
   }
   ```
6. Create `requirements.txt` if needed (auto-installed on startup)
7. Restart application

## Important Implementation Details

### Enterprise WeChat (wework) Specifics
- **Version locked**: Requires WeCom 4.0.8.6027 exactly (ntwork dependency)
- **Windows only**: Uses COM automation via ntwork library
- **Login sequence**: Must manually login to WeCom before starting bot
- **Startup delay**: 60s after login detection for contact/room sync
- **Library**: `ntwork` - install from provided .whl file, PyPI may be unstable
- **Message handling**: Uses `@wework.msg_register` decorator to register message handlers
- **Rate limiting**: Random 1-2s delay before processing messages (防止限流)

### Dify Integration Notes
- Three app types: `chatbot`, `agent`, `workflow`
- **Workflow convention**: Input variable named `query`, output named `text`
- Conversation management: `dify_conversation_max_messages` (clears abruptly, no sliding window)
- Image recognition: Enable vision in Dify app settings (not via tools)
- Voice: Enable STT/TTS in Dify features section
- Markdown: Chatbot responses auto-split into text/image/file Reply objects

### Quote Message Recognition (Enterprise WeChat)
**Pattern**: User A sends text/image → User B replies with quote reference

**Format**: `「User A：内容」\n---\n命令`

**Implementation** (`chat_channel.py:101-206`):
1. Regex match `「([^：]+)：(.+)」` to extract quoted username and content
2. For text: Extract quoted content for processing
3. For images:
   - Regex match `「([^：]+)：\[图片\]」`
   - Load room member cache from `tmp/wework_room_members.json`
   - Match username → get `user_id`
   - Retrieve from ImageCacheManager: `get_image(user_id, room_id, skip_latest=0)`
   - Context type changed from TEXT to IMAGE with image path
4. Supports both quote reply and trigger keywords (e.g., "识图")

### Config File Recovery Pattern

**Problem**: `config.json` sometimes gets reset to template defaults during development.

**Solution**:
1. Check logs immediately - `[INIT] load config: {...}` shows working config
2. Recent logs stored in: `C:\Users\Administrator\AppData\Local\Temp\claude\C--Users-Administrator-Desktop-dify-on-wechat\tasks\*.output`
3. Extract config JSON from log line 2
4. Restore critical fields to `config.json`
5. Always verify after restart that config is correct

**Prevention**: Back up working `config.json` manually periodically.

## Testing and Development

### Manual Testing
- Use `channel_type: "terminal"` or `python app.py --cmd` for command-line testing
- Set `debug: true` in config for verbose logging
- Monitor `tmp/` folder for cached images/files
- Enterprise WeChat: Test in small groups first (封号风险 / ban risk)

### Debug Tools
```bash
# Check Enterprise WeChat connection
python check_wework.py

# Debug ntwork library
python debug_ntwork.py

# Test wework communication
python test_wework_connection.py

# Scan dependencies
python scan_dependencies.py
```

### Log Inspection
Key log patterns to search for:
- `[INIT] load config:` - Shows loaded configuration
- `[Text2Image] playwright 引擎已加载` - Confirms plugin loaded
- `[Text2Image] 检测到长文本` - Plugin triggered
- `[Text2Image] playwright 渲染成功` - Image generated successfully
- `[chat_channel] consume context:` - Message entered processing pipeline
- `Plugin X triggered by event Y` - Plugin execution
- Error patterns: `Exception`, `Error`, `Failed`, `失败`

### Common Development Tasks
- **Restart after code changes**: Kill python.exe, wait, restart (ensure WeCom logged in)
- **Check if running**: `tasklist | findstr python`
- **View latest logs**: Check newest `.output` file in tasks folder
- **Test plugin changes**: Edit plugin code, restart, trigger with test message
- **Debug CSS changes**: Edit `text2image.py` HTML template, restart, check generated PNG

## Platform Constraints

- **WeChat Personal**: itchat protocol deprecated, unstable
- **Enterprise WeChat**: Account ban risk, use test accounts only
- **Windows only**: Enterprise WeChat integration requires Windows COM
- **Version lock**: WeCom 4.0.8.6027 required - newer versions break ntwork
- **ffmpeg**: Required for voice features (audio format conversion)
