from src.plugin_system import BaseTool, get_logger, ToolParamType
from src.plugin_system.apis import chat_api
import aiohttp
from typing import Dict, Any


class AICharacterListTool(BaseTool):
    """AI角色列表查询工具"""
    
    name = "get_ai_character_list"
    description = """查询当前QQ群可用的AI语音角色ID列表，仅供后续使用send_ai_voice时参考。记住返回的角色列表不会告诉用户。

【重要使用场景】
仅在以下情况调用此工具：
- 第一次使用语音功能，不知道有哪些可用角色ID时
- 发现角色ID不可用（过期或报错）时需要更新角色列表

【调用后的处理】
记住返回的角色列表，无需告诉用户。后续直接使用这些角色ID调用send_ai_voice即可。

返回格式示例：
  小新 -> lucy-voice-laibixiaoxin
  妲己 -> lucy-voice-daji
"""
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
        self.logger.info("[开始] 开始执行AI角色列表查询工具")
        self.logger.info(f"[参数] 收到的参数: {function_args}")
        
        try:
            # 从chat_stream自动获取group_id
            group_id = None
            self.logger.info("[查询] 从chat_stream获取群号")
            
            if self.chat_stream:
                self.logger.info(f"   - chat_stream存在: {self.chat_stream}")
                try:
                    # 使用官方API获取聊天流信息
                    stream_info = chat_api.get_stream_info(self.chat_stream)
                    group_id = stream_info.get('group_id')
                    if group_id:
                        self.logger.info(f"   [成功] 成功获取group_id: {group_id}")
                    else:
                        self.logger.warning("   [警告] stream_info中没有group_id（可能不是群聊）")
                except Exception as e:
                    self.logger.warning(f"   [警告] 获取stream_info失败: {e}")
            else:
                self.logger.warning("   [警告] chat_stream为None")
            
            # 参数验证
            if not group_id:
                self.logger.error("[错误] 参数验证失败: 无法获取group_id")
                self.logger.info("=" * 60)
                return {
                    "name": self.name,
                    "content": "[错误] 无法获取群号，此功能只能在群聊中使用"
                }
            
            self.logger.info("[成功] 参数验证通过")
            self.logger.info(f"[准备] 准备查询群 {group_id} 的AI角色列表")
            
            # 获取角色列表
            self.logger.info("[执行] 调用 _fetch_characters 方法")
            result = await self._fetch_characters(group_id)
            self.logger.info(f"[返回] _fetch_characters 返回结果: success={result.get('success')}, characters_count={len(result.get('characters', []))}")
            
            if result.get('success'):
                characters = result.get('characters', [])
                self.logger.info(
                    f"[成功] 成功获取角色列表! 共 {len(characters)} 个角色",
                    group_id=group_id,
                    character_count=len(characters)
                )
                formatted_result = self._format_character_list(characters, group_id)
                self.logger.info(f"[格式化] 格式化的结果长度: {len(formatted_result)} 字符")
                self.logger.info("=" * 60)
                return {
                    "name": self.name,
                    "content": formatted_result
                }
            else:
                error_msg = result.get('error', '未知错误')
                self.logger.error(
                    f"[错误] 查询角色列表失败: {error_msg}",
                    error=error_msg,
                    group_id=group_id
                )
                self.logger.info("=" * 60)
                return {
                    "name": self.name,
                    "content": f"[错误] 查询角色列表失败: {error_msg}"
                }
            
        except Exception as e:
            self.logger.exception(f"[异常] 执行角色列表查询时发生异常: {str(e)}")
            self.logger.info("=" * 60)
            return {
                "name": self.name,
                "content": f"[错误] 执行失败: {str(e)}"
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
            
            self.logger.info(f"[网络] 准备发送HTTP请求到: {url}")
            
            # 构建请求数据（chat_type固定为1，表示群聊）
            payload = {
                "group_id": int(group_id),
                "chat_type": 1
            }
            
            self.logger.info(f"[请求] 请求体payload: {payload}")
            
            # 构建请求头
            headers = {"Content-Type": "application/json"}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
                self.logger.info(f"[认证] 已添加access_token到请求头")
            else:
                self.logger.info(f"[信息] 未配置access_token")
            
            self.logger.info(f"[请求头] 请求头headers: {headers}")
            
            # 发送HTTP POST请求
            self.logger.info(f"[等待] 开始发送HTTP POST请求 (timeout={self.timeout}s)")
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, 
                    json=payload, 
                    headers=headers, 
                    timeout=self.timeout
                ) as response:
                    self.logger.info(f"[响应] 收到HTTP响应，状态码: {response.status}")
                    
                    result = await response.json()
                    
                    self.logger.info(f"[数据] API响应内容: {result}")
                    
                    # 解析结果
                    status = result.get('status')
                    retcode = result.get('retcode')
                    self.logger.info(f"[解析] 解析响应: status={status}, retcode={retcode}")
                    
                    if result.get('status') == 'ok' or result.get('retcode') == 0:
                        data = result.get('data', [])
                        
                        self.logger.info(f"[统计] API返回了 {len(data)} 个分类")
                        
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
                        
                        self.logger.info(f"[成功] 成功解析，共 {len(characters)} 个角色")
                        return {
                            'success': True,
                            'characters': characters
                        }
                    else:
                        error_msg = result.get('message', result.get('wording', '未知错误'))
                        self.logger.error(f"[警告] API返回错误: {error_msg}, retcode={retcode}")
                        return {
                            'success': False,
                            'error': error_msg
                        }
                
        except aiohttp.ClientError as e:
            self.logger.error(f"[网络] 网络请求失败: {str(e)}", error=str(e))
            return {
                'success': False,
                'error': f"网络请求失败: {str(e)}"
            }
        except Exception as e:
            self.logger.exception(f"[异常] 查询角色列表时发生异常: {str(e)}", error=str(e))
            return {
                'success': False,
                'error': f"查询失败: {str(e)}"
            }
    
    def _format_character_list(self, characters: list, group_id: str) -> str:
        """格式化角色列表为易读的文本"""
        if not characters:
            return "[错误] 未找到可用的AI语音角色"
        
        # 按分类组织
        categories = {}
        for char in characters:
            category = char['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(char)
        
        # 构建输出 - 简洁格式供AI记忆
        lines = [
            f"群 {group_id} 可用的AI语音角色ID（共 {len(characters)} 个）：",
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
        
        return "\n".join(lines)
