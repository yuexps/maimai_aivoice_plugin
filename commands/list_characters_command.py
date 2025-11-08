from src.plugin_system import BaseCommand
from typing import Tuple, Optional
import aiohttp


class ListAICharactersCommand(BaseCommand):
    """AI角色列表查询命令 - 响应/ai_roles命令"""
    
    command_name = "list_ai_characters"
    command_description = "列出当前群可用的AI语音角色"
    command_pattern = r"^/(ai_roles|ai角色|语音角色)$"
    
    def __init__(self, message=None, plugin_config=None):
        """初始化命令组件
        
        Args:
            message: 消息对象
            plugin_config: 插件配置字典
        """
        super().__init__(message, plugin_config)
    
    async def execute(self) -> Tuple[bool, str, bool]:
        """执行角色列表查询"""
        try:
            # 获取群号
            group_info = self.message.message_info.group_info
            if not group_info or not group_info.group_id:
                await self.send_text("❌ 此命令只能在群聊中使用")
                return False, "命令只能在群聊中使用", True
            
            group_id = group_info.group_id
            
            # 获取配置
            api_url = self.get_config("napcat.api_url", "http://127.0.0.1:3000")
            access_token = self.get_config("napcat.access_token", None)
            timeout = self.get_config("timeout.request_timeout", 30)
            
            # 查询角色列表
            result = await self._fetch_characters(api_url, access_token, timeout, str(group_id))
            
            if result.get('success'):
                characters = result.get('characters', [])
                message = self._format_character_list(characters, str(group_id))
                await self.send_text(message)
                return True, f"显示了{len(characters)}个AI角色", True
            else:
                error_msg = result.get('error', '未知错误')
                await self.send_text(f"❌ 查询失败: {error_msg}")
                return False, f"查询失败: {error_msg}", True
                
        except Exception as e:
            await self.send_text(f"❌ 执行失败: {str(e)}")
            return False, f"执行失败: {str(e)}", True
    
    async def _fetch_characters(self, api_url: str, access_token: Optional[str], 
                                timeout: int, group_id: str) -> dict:
        """通过NapCat API获取角色列表"""
        try:
            url = f"{api_url}/get_ai_characters"
            # chat_type固定为1（群聊），因为API只支持群聊AI语音
            payload = {
                "group_id": int(group_id),
                "chat_type": 1
            }
            
            headers = {"Content-Type": "application/json"}
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=timeout) as response:
                    result = await response.json()
                    
                    if result.get('status') == 'ok' or result.get('retcode') == 0:
                        data = result.get('data', [])
                        characters = []
                        for category in data:
                            category_type = category.get('type', '其他')
                            for char in category.get('characters', []):
                                characters.append({
                                    'character_id': char.get('character_id', ''),
                                    'character_name': char.get('character_name', ''),
                                    'category': category_type
                                })
                        
                        return {'success': True, 'characters': characters}
                    else:
                        return {
                            'success': False,
                            'error': result.get('message', result.get('wording', '未知错误'))
                        }
        except aiohttp.ClientError as e:
            return {'success': False, 'error': f"网络请求失败: {str(e)}"}
        except Exception as e:
            return {'success': False, 'error': f"查询失败: {str(e)}"}
    
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
        
        # 按分类输出（每个角色单独一行）
        for category, chars in categories.items():
            lines.append(f"【{category}】")
            for char in chars:
                lines.append(f"  {char['character_name']} -> {char['character_id']}")
            lines.append("")
        
        lines.append("━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 使用方法：")
        lines.append("对我说：用<角色名>的声音说<内容>")
        lines.append("例如：用小新的声音说你好")
        
        return "\n".join(lines)
