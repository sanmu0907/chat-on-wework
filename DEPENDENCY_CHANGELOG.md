# 依赖管理改进 - 变更说明

## 更新日期
2025-12-07

## 主要改进

### 1. 自动安装插件依赖功能

**变更内容：**
- 在 `plugin_manager.py` 中添加了 `_install_plugin_requirements()` 方法
- 修改 `load_plugins()` 方法，在激活插件前自动安装依赖
- 启动时自动检测并安装所有已启用插件的 requirements.txt

**工作原理：**
1. 程序启动时，扫描 `plugins/plugins.json` 中所有 `enabled: true` 的插件
2. 检查每个插件目录下是否存在 `requirements.txt`
3. 如果存在，自动调用 `pip install -r requirements.txt` 安装依赖
4. 安装过程在日志中可见，失败时会显示警告

**用户体验改进：**
- ✅ 新电脑部署时，只需 `pip install -r requirements.txt` 安装主项目依赖
- ✅ 插件依赖完全自动化，无需手动安装
- ✅ 启用新插件后首次启动会自动安装其依赖
- ✅ 避免因缺少插件依赖导致的运行时错误

### 2. 完整的依赖文件创建

**新增文件：**
- `requirements.txt` - 主项目依赖文件
- `INSTALL.md` - 详细的安装和部署指南
- `scan_dependencies.py` - 依赖扫描工具（辅助脚本）

**为所有插件创建 requirements.txt：**
- Apilot/requirements.txt
- banwords/requirements.txt
- bdunit/requirements.txt
- dungeon/requirements.txt
- finish/requirements.txt
- godcmd/requirements.txt
- helloplus/requirements.txt
- jimeng/requirements.txt
- jina_sum/requirements.txt
- keyword/requirements.txt
- moda/requirements.txt

已有的插件依赖文件（保持不变）：
- ChatSummary/requirements.txt
- difytimetask/requirements.txt
- flow2api/requirements.txt
- mmm/requirements.txt

### 3. 文档更新

**INSTALL.md:**
- 新增"自动安装功能"重要提示
- 简化了部署步骤（不再需要手动安装插件依赖）
- 添加了自动安装的日志输出示例
- 保留手动安装说明（应对自动安装失败的情况）

**CLAUDE.md:**
- 在"Running the Application"部分添加依赖管理说明
- 在"Plugin System"部分添加自动安装依赖的说明
- 更新了插件生命周期描述

## 代码变更

### plugin_manager.py

**新增方法：**
```python
def _install_plugin_requirements(self):
    """
    自动安装已启用插件的依赖
    """
    logger.info("Checking and installing plugin requirements...")
    pconf = self.pconf

    for name, plugin in pconf["plugins"].items():
        # 只为已启用的插件安装依赖
        if not plugin.get("enabled", False):
            continue

        name_upper = name.upper()
        if name_upper not in self.plugins:
            continue

        plugin_path = self.plugins[name_upper].path
        if not plugin_path:
            continue

        requirements_path = os.path.join(plugin_path, "requirements.txt")
        if os.path.exists(requirements_path):
            logger.info(f"Installing requirements for plugin {name}...")
            try:
                import common.package_manager as pkgmgr
                pkgmgr.install_requirements(requirements_path)
                logger.info(f"Successfully installed requirements for plugin {name}")
            except Exception as e:
                logger.warn(f"Failed to install requirements for plugin {name}: {e}")
```

**修改方法：**
```python
def load_plugins(self):
    self.load_config()
    self.scan_plugins()
    self._load_all_config()
    pconf = self.pconf
    logger.debug("plugins.json config={}".format(pconf))
    for name, plugin in pconf["plugins"].items():
        if name.upper() not in self.plugins:
            logger.error("Plugin %s not found, but found in plugins.json" % name)
    # 新增：自动安装已启用插件的依赖
    self._install_plugin_requirements()
    self.activate_plugins()
```

## 向后兼容性

**完全兼容：**
- ✅ 不影响现有功能
- ✅ 手动安装依赖的方式仍然可用
- ✅ `#installp` 和 `#updatep` 命令的依赖安装逻辑保持不变
- ✅ 已安装的依赖会被 pip 跳过，不会重复安装

## 测试建议

1. **全新环境测试：**
   ```bash
   # 创建新虚拟环境
   python -m venv test_env
   source test_env/bin/activate  # Windows: test_env\Scripts\activate

   # 只安装主项目依赖
   pip install -r requirements.txt

   # 配置 config.json
   cp config-template.json config.json
   # 编辑配置...

   # 启动程序，观察是否自动安装插件依赖
   python app.py
   ```

2. **日志检查：**
   查找以下日志信息：
   - `[INFO] Checking and installing plugin requirements...`
   - `[INFO] Installing requirements for plugin <name>...`
   - `[INFO] Successfully installed requirements for plugin <name>`
   - 或 `[WARN] Failed to install requirements for plugin <name>: <error>`

3. **功能验证：**
   - 启用的插件应该能正常工作
   - 插件特定的功能（如 ChatSummary、difytimetask）应该正常运行

## 注意事项

1. **首次启动时间：** 如果有多个插件需要安装依赖，首次启动可能需要较长时间
2. **网络要求：** 需要能够访问 PyPI 或配置的镜像源
3. **权限要求：** 需要有安装 Python 包的权限
4. **失败处理：** 如果某个插件依赖安装失败，程序会记录警告但继续运行

## 后续建议

1. **可选优化：** 可以考虑添加缓存机制，避免每次启动都检查已安装的依赖
2. **离线安装：** 对于无法联网的环境，可以提供离线安装包或 wheel 文件
3. **版本锁定：** requirements.txt 中已使用 `>=` 指定最低版本，可根据需要调整为精确版本

## 相关文件

- `plugin_manager.py` - 核心代码修改
- `requirements.txt` - 主项目依赖
- `INSTALL.md` - 安装指南
- `CLAUDE.md` - 项目文档
- `plugins/*/requirements.txt` - 各插件依赖
- `scan_dependencies.py` - 依赖扫描工具
