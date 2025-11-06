"""AI角色列表查询工具 - 获取QQ群可用的AI语音角色"""

from src.plugin_system import BaseTool, get_logger, ToolParamType
from src.plugin_system.apis import chat_api
import aiohttp
from typing import Dict, Any


class AICharacterListTool(BaseTool):
    """AI角色列表查询工具 - 查询QQ群当前可用的AI语音角色列表"""
    
    name = "get_ai_character_list"
    description = """【准备阶段】获取QQ群可用的AI语音角色列表。
    
重要：调用本工具后，你必须立即调用send_ai_voice工具完成发送！不要只获取列表就停止！

完整流程（两步缺一不可）：
步骤1: 调用本工具get_ai_character_list → 获取角色列表
步骤2: 立即调用send_ai_voice → 使用character_id发送语音

返回格式示例：
  小新 -> lucy-voice-laibixiaoxin
  妲己 -> lucy-voice-daji

你必须从箭头右侧获取character_id，然后立即调用send_ai_voice工具！"""
    available_for_llm = True
    
    # 占位参数，实际不使用（框架要求必须定义非空parameters）
    parameters = [
        ("None", ToolParamType.STRING, "None", False, None)
    ]
    
    def __init__(self, plugin_config=None, chat_stream=None):
        super().__init__(plugin_config)
        self.chat_stream = chat_stream
        # 获取日志记录器
        self.logger = get_logger("maimai_aivoice_plugin.character_list_tool")
        
        # 从配置中读取设置
        self.api_url = self.get_config("napcat.api_url", "http://127.0.0.1:3000")
        self.access_token = self.get_config("napcat.access_token", None)
        self.timeout = self.get_config("timeout.request_timeout", 30)
        
        self.logger.debug(
            "AI角色列表工具初始化完成",
            api_url=self.api_url,
            timeout=self.timeout
        )
    
    async def execute(self, function_args: Dict[str, Any]):
        """执行角色列表查询"""
        self.logger.info("=" * 60)
        self.logger.info("🎭 开始执行AI角色列表查询工具")
        self.logger.info(f"📥 收到的参数: {function_args}")
        
        try:
            # 从chat_stream自动获取group_id
            group_id = None
            self.logger.info("🔍 从chat_stream获取群号")
            
            if self.chat_stream:
                self.logger.info(f"   - chat_stream存在: {self.chat_stream}")
                try:
                    # 使用官方API获取聊天流信息
                    stream_info = chat_api.get_stream_info(self.chat_stream)
                    group_id = stream_info.get('group_id')
                    if group_id:
                        self.logger.info(f"   ✅ 成功获取group_id: {group_id}")
                    else:
                        self.logger.warning("   ⚠️ stream_info中没有group_id（可能不是群聊）")
                except Exception as e:
                    self.logger.warning(f"   ⚠️ 获取stream_info失败: {e}")
            else:
                self.logger.warning("   ⚠️ chat_stream为None")
            
            # 参数验证
            if not group_id:
                self.logger.error("❌ 参数验证失败: 无法获取group_id")
                self.logger.info("=" * 60)
                return {
                    "name": self.name,
                    "content": "❌ 无法获取群号，此功能只能在群聊中使用"
                }
            
            self.logger.info("✅ 参数验证通过")
            self.logger.info(f"📤 准备查询群 {group_id} 的AI角色列表")
            
            # 获取角色列表
            self.logger.info("🚀 调用 _fetch_characters 方法")
            result = await self._fetch_characters(group_id)
            self.logger.info(f"📨 _fetch_characters 返回结果: success={result.get('success')}, characters_count={len(result.get('characters', []))}")
            
            if result.get('success'):
                characters = result.get('characters', [])
                self.logger.info(
                    f"🎉 成功获取角色列表! 共 {len(characters)} 个角色",
                    group_id=group_id,
                    character_count=len(characters)
                )
                formatted_result = self._format_character_list(characters, group_id)
                self.logger.info(f"📝 格式化的结果长度: {len(formatted_result)} 字符")
                self.logger.info("=" * 60)
                return {
                    "name": self.name,
                    "content": formatted_result
                }
            else:
                error_msg = result.get('error', '未知错误')
                self.logger.error(
                    f"❌ 查询角色列表失败: {error_msg}",
                    error=error_msg,
                    group_id=group_id
                )
                self.logger.info("=" * 60)
                return {
                    "name": self.name,
                    "content": f"❌ 查询角色列表失败: {error_msg}"
                }
            
        except Exception as e:
            self.logger.exception(f"💥 执行角色列表查询时发生异常: {str(e)}")
            self.logger.info("=" * 60)
            return {
                "name": self.name,
                "content": f"❌ 执行失败: {str(e)}"
            }
    
    async def _fetch_characters(self, group_id: str) -> Dict[str, Any]:
        """通过NapCat API获取角色列表
        
        Args:
            group_id: QQ群号
            
        Returns:
            包含成功状态和角色列表的字典
        """
        try:
            url = f"{self.api_url}/get_ai_characters"
            
            self.logger.info(f"🌐 准备发送HTTP请求到: {url}")
            
            # 构建请求数据（chat_type固定为1，表示群聊）
            payload = {
                "group_id": int(group_id),
                "chat_type": 1
            }
            
            self.logger.info(f"📦 请求体payload: {payload}")
            
            # 构建请求头
            headers = {"Content-Type": "application/json"}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
                self.logger.info(f"🔑 已添加access_token到请求头")
            else:
                self.logger.info(f"ℹ️ 未配置access_token")
            
            self.logger.info(f"📋 请求头headers: {headers}")
            
            # 发送HTTP POST请求
            self.logger.info(f"⏳ 开始发送HTTP POST请求 (timeout={self.timeout}s)")
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, 
                    json=payload, 
                    headers=headers, 
                    timeout=self.timeout
                ) as response:
                    self.logger.info(f"📡 收到HTTP响应，状态码: {response.status}")
                    
                    result = await response.json()
                    
                    self.logger.info(f"📄 API响应内容: {result}")
                    
                    # 解析结果
                    status = result.get('status')
                    retcode = result.get('retcode')
                    self.logger.info(f"🔍 解析响应: status={status}, retcode={retcode}")
                    
                    if result.get('status') == 'ok' or result.get('retcode') == 0:
                        data = result.get('data', [])
                        
                        self.logger.info(f"📊 API返回了 {len(data)} 个分类")
                        
                        # 解析角色数据
                        characters = []
                        for category in data:
                            category_type = category.get('type', '其他')
                            category_chars = category.get('characters', [])
                            self.logger.info(f"   - 分类 '{category_type}': {len(category_chars)} 个角色")
                            
                            for char in category_chars:
                                char_id = char.get('character_id', '')
                                char_name = char.get('character_name', '')
                                characters.append({
                                    'character_id': char_id,
                                    'character_name': char_name,
                                    'category': category_type,
                                    'preview_url': char.get('preview_url', '')
                                })
                                self.logger.debug(f"     * {char_name} ({char_id})")
                        
                        self.logger.info(f"✅ 成功解析，共 {len(characters)} 个角色")
                        return {
                            'success': True,
                            'characters': characters
                        }
                    else:
                        error_msg = result.get('message', result.get('wording', '未知错误'))
                        self.logger.error(f"⚠️ API返回错误: {error_msg}, retcode={retcode}")
                        return {
                            'success': False,
                            'error': error_msg
                        }
                
        except aiohttp.ClientError as e:
            self.logger.error(f"🌐 网络请求失败: {str(e)}", error=str(e))
            return {
                'success': False,
                'error': f"网络请求失败: {str(e)}"
            }
        except Exception as e:
            self.logger.exception(f"💥 查询角色列表时发生异常: {str(e)}", error=str(e))
            return {
                'success': False,
                'error': f"查询失败: {str(e)}"
            }
    
    def _format_character_list(self, characters: list, group_id: str) -> str:
        """格式化角色列表为易读的文本"""
        if not characters:
            return "❌ 未找到可用的AI语音角色"
        
        # 按分类组织
        categories = {}
        for char in characters:
            category = char['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(char)
        
        # 构建输出
        lines = [
            f"🎭 群 {group_id} 可用的AI语音角色",
            "━━━━━━━━━━━━━━━━━━━━━━",
            f"共 {len(characters)} 个角色",
            ""
        ]
        
        # 按分类输出（简化格式，只显示名称到ID的映射）
        for category, chars in categories.items():
            lines.append(f"【{category}】")
            for char in chars:
                char_id = char['character_id']
                char_name = char['character_name']
                # 格式：名称 -> character_id
                lines.append(f"  {char_name} -> {char_id}")
            lines.append("")
        
        lines.append("━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("⚠️ 重要：使用send_ai_voice时，character参数必须填写箭头右侧的character_id（lucy-voice-xxx格式）")
        lines.append("")
        lines.append("🔔 下一步操作：立即调用send_ai_voice工具发送语音！")
        lines.append("   示例：send_ai_voice(character='lucy-voice-f38', text='你好')")
        
        return "\n".join(lines)
