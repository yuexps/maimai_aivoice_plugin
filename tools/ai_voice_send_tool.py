from src.plugin_system import BaseTool, get_logger, ToolParamType
from src.plugin_system.apis import chat_api
import aiohttp
from typing import Dict, Any

class AIVoiceSendTool(BaseTool):
    """AI语音发送工具 - 自动查询角色列表并发送语音"""
    
    name = "send_ai_voice"
    description = """使用AI语音角色发送语音消息。工具内部会自动查询可用角色列表并匹配发送。

参数：
- character_name: 角色的中文名称（如"小新"、"傲娇少女"、"妲己"等）
- text: 要转换为语音的文字内容

角色选择说明：
- 如果用户指定了角色（如"用小新的声音说xxx"），使用用户指定的角色
- 如果用户没有指定角色，根据说话内容的风格、语气、场景，从已知的所有可用角色中选择最合适的
- 可以根据你的人设和当前对话氛围选择角色

使用示例：
用户："用傲娇少女的声音说你好"
→ send_ai_voice(character_name="傲娇少女", text="你好")

用户："用小新说我来啦"  
→ send_ai_voice(character_name="小新", text="我来啦")

用户："发个语音说早上好"（用户未指定，根据内容和氛围选择）
→ send_ai_voice(character_name="元气少女", text="早上好")
"""
    available_for_llm = True
    
    parameters = [
        ("character_name", ToolParamType.STRING, "AI角色的中文名称。用户指定则用指定的，未指定则从所有可用角色中根据内容风格选择最合适的", True, None),
        ("text", ToolParamType.STRING, "要转换为语音的文字内容", True, None)
    ]
    
    def __init__(self, plugin_config=None, chat_stream=None):
        super().__init__(plugin_config)
        self.chat_stream = chat_stream
        # 获取日志记录器
        self.logger = get_logger("maimai_aivoice_plugin.send_tool")
        
        # 从配置中读取设置
        self.api_url = self.get_config("napcat.api_url", "http://127.0.0.1:3000")
        self.access_token = self.get_config("napcat.access_token", None)
        self.timeout = self.get_config("timeout.request_timeout", 30)
        
        self.logger.debug(
            "AI语音发送工具初始化完成",
            api_url=self.api_url,
            timeout=self.timeout
        )
    
    async def execute(self, function_args: Dict[str, Any]):
        """执行语音发送"""
        self.logger.info("=" * 60)
        self.logger.info("[开始] 开始执行AI语音发送工具")
        self.logger.info(f"[参数] 收到的参数: {function_args}")
        
        try:
            character_name = function_args.get("character_name")
            text = function_args.get("text")
            
            self.logger.info(f"[解析] 解析参数:")
            self.logger.info(f"   - character_name: {character_name}")
            self.logger.info(f"   - text: {text}")
            
            # 从chat_stream自动获取group_id
            group_id = None
            self.logger.info("[查询] 从chat_stream获取群号")
            
            if self.chat_stream:
                try:
                    stream_info = chat_api.get_stream_info(self.chat_stream)
                    group_id = stream_info.get('group_id')
                    if group_id:
                        self.logger.info(f"   [成功] 成功获取group_id: {group_id}")
                except Exception as e:
                    self.logger.warning(f"   [警告] 获取stream_info失败: {e}")
            
            # 参数验证
            if not character_name:
                self.logger.error("[错误] 参数验证失败: 缺少character_name参数")
                return {
                    "name": self.name,
                    "content": "[错误] 缺少必需参数: character_name (AI角色名称)"
                }
            
            if not group_id:
                self.logger.error("[错误] 参数验证失败: 无法获取group_id")
                return {
                    "name": self.name,
                    "content": "[错误] 无法获取群号，此功能只能在群聊中使用"
                }
            
            if not text:
                self.logger.error("[错误] 参数验证失败: 缺少text参数")
                return {
                    "name": self.name,
                    "content": "[错误] 缺少必需参数: text (语音内容)"
                }
            
            self.logger.info("[成功] 参数验证通过")
            
            # 步骤1：获取角色列表
            self.logger.info("[步骤1] 步骤1/2: 查询角色列表")
            characters_result = await self._fetch_characters(group_id)
            
            if not characters_result.get('success'):
                error_msg = characters_result.get('error', '未知错误')
                self.logger.error(f"[错误] 查询角色列表失败: {error_msg}")
                return {
                    "name": self.name,
                    "content": f"[错误] 查询角色列表失败: {error_msg}"
                }
            
            characters = characters_result.get('characters', [])
            self.logger.info(f"[成功] 成功获取 {len(characters)} 个角色")
            
            # 步骤2：查找匹配的角色
            self.logger.info(f"[步骤2] 步骤2/2: 查找角色 '{character_name}'")
            character_id = None
            for char in characters:
                if char['character_name'] == character_name:
                    character_id = char['character_id']
                    self.logger.info(f"[成功] 找到匹配角色: {character_name} -> {character_id}")
                    break
            
            if not character_id:
                self.logger.error(f"[错误] 未找到角色: {character_name}")
                available_names = [c['character_name'] for c in characters[:10]]
                return {
                    "name": self.name,
                    "content": f"[错误] 未找到角色'{character_name}'。可用角色示例：{', '.join(available_names)}等"
                }
            
            # 步骤3：发送语音
            self.logger.info(f"[步骤3] 步骤3/3: 发送语音")
            send_result = await self._send_ai_voice(character_id, group_id, text)
            
            if send_result.get('success'):
                message_id = send_result.get('message_id', '未知')
                self.logger.info(f"[成功] 语音发送成功! message_id={message_id}")
                self.logger.info("=" * 60)
                return {
                    "name": self.name,
                    "content": f"[成功] 已使用'{character_name}'的声音说出：{text}"
                }
            else:
                error_msg = send_result.get('error', '未知错误')
                self.logger.error(f"[错误] 发送语音失败: {error_msg}")
                self.logger.info("=" * 60)
                return {
                    "name": self.name,
                    "content": f"[错误] 发送语音失败: {error_msg}"
                }
            
        except Exception as e:
            self.logger.exception(f"[异常] 执行快速语音发送时发生异常: {str(e)}")
            self.logger.info("=" * 60)
            return {
                "name": self.name,
                "content": f"[错误] 执行失败: {str(e)}"
            }
    
    async def _fetch_characters(self, group_id: str) -> Dict[str, Any]:
        """获取角色列表"""
        try:
            url = f"{self.api_url}/get_ai_characters"
            payload = {
                "group_id": int(group_id),
                "chat_type": 1
            }
            
            headers = {"Content-Type": "application/json"}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=self.timeout) as response:
                    result = await response.json()
                    
                    if result.get('status') == 'ok' or result.get('retcode') == 0:
                        data = result.get('data', [])
                        characters = []
                        for category in data:
                            for char in category.get('characters', []):
                                characters.append({
                                    'character_id': char.get('character_id', ''),
                                    'character_name': char.get('character_name', ''),
                                    'category': category.get('type', '其他')
                                })
                        return {'success': True, 'characters': characters}
                    else:
                        return {'success': False, 'error': result.get('message', '未知错误')}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _send_ai_voice(self, character: str, group_id: str, text: str) -> Dict[str, Any]:
        """发送AI语音"""
        try:
            url = f"{self.api_url}/send_group_ai_record"
            payload = {
                "group_id": int(group_id),
                "character": character,
                "text": text
            }
            
            headers = {"Content-Type": "application/json"}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=self.timeout) as response:
                    result = await response.json()
                    
                    if result.get('status') == 'ok' or result.get('retcode') == 0:
                        return {'success': True, 'message_id': result.get('data', {}).get('message_id', '')}
                    else:
                        return {'success': False, 'error': result.get('message', '未知错误')}
        except Exception as e:
            return {'success': False, 'error': str(e)}
