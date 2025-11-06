# 🎤 麦麦AI语音插件

通过NapCat API使用QQ自带的AI语音功能，将文本转换为语音发送到群聊。

## ✨ 功能

- 🎭 发送AI语音消息（30+角色可选）
- 🔍 查询可用角色列表
- ⚡ 命令：`/ai_roles` `/ai角色` `/语音角色`

## 🎭 常用角色

小新、猴哥、妲己、酥心御姐、霸道总裁、**元气少女**、磁性大叔、**邻家小妹**、**暖心姐姐**、傲娇少女等

> 💡 使用 `/ai_roles` 命令查看完整列表

## 🤖 系统提示词（推荐配置）

在麦麦的系统提示词中添加：

```
你拥有发送QQ语音的能力！当用户要求发送语音时，使用 send_ai_voice 工具。

角色选择规则：
- 用户指定了角色 → 使用指定角色
- 用户未指定 → 根据内容风格或人设选择，推荐：元气少女、暖心姐姐、邻家小妹

示例：
- "用小新声音说你好" → send_ai_voice(character_name="小新", text="你好")  
- "发个语音说早安" → send_ai_voice(character_name="元气少女", text="早安")
```

## 📦 安装配置

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置文件

首次加载后会自动生成 `config.toml`，修改以下配置：

```toml
[plugin]
enabled = true  # 启用插件

[napcat]
api_url = "http://127.0.0.1:3000"  # NapCat HTTP API地址
access_token = ""  # 如有token认证，填写此处
```

### 3. 重启麦麦

## 🐛 常见问题

**Q: 连接失败？**  
A: 检查 `api_url` 配置，确认 NapCat 正在运行

**Q: 找不到角色？**  
A: 使用 `/ai_roles` 命令查看可用角色，注意使用准确的中文名称

**Q: 启用调试日志？**  
A: `config.toml` 中设置 `logging.level = "DEBUG"`

---

📚 [麦麦文档](https://docs.mai-mai.org/) | [插件开发指南](https://docs.mai-mai.org/develop/plugin_develop/) | [NapCat文档](https://napcat.apifox.cn/)
