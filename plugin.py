"""麦麦AI语音插件主类"""

from src.plugin_system import BasePlugin, register_plugin, ConfigField, ComponentInfo
from typing import List, Tuple, Type

# 导入工具类以便注册
from .tools.ai_character_list_tool import AICharacterListTool
from .tools.ai_voice_send_tool import AIVoiceSendTool

# 导入命令类
from .commands.list_characters_command import ListAICharactersCommand


@register_plugin
class AIVoicePlugin(BasePlugin):
    """QQ AI语音插件
    
    使用QQ自带的AI语音功能，通过NapCat API将文本转换为语音发送到群聊。
    提供角色查询和语音发送两个核心功能。
    """
    
    # 插件基本信息（必需 - 作为类属性）
    plugin_name: str = "maimai_aivoice_plugin"
    enable_plugin: bool = True
    dependencies: List[str] = []
    python_dependencies: List[str] = []
    config_file_name: str = "config.toml"
    
    # 配置节描述
    config_section_descriptions = {
        "plugin": "插件基本配置",
        "napcat": "NapCat API连接配置",
        "timeout": "超时设置",
        "logging": "日志配置"
    }
    
    # 配置Schema
    config_schema: dict = {
        "plugin": {
            "enabled": ConfigField(
                type=bool,
                default=False,
                description="是否启用AI语音插件"
            ),
            "config_version": ConfigField(
                type=str,
                default="1.0.0",
                description="配置文件版本"
            )
        },
        "napcat": {
            "api_url": ConfigField(
                type=str,
                default="http://127.0.0.1:3000",
                description="NapCat HTTP API地址",
                example="http://127.0.0.1:3000"
            ),
            "access_token": ConfigField(
                type=str,
                default="",
                description="访问令牌（可选，如果NapCat设置了token认证则需要配置）"
            )
        },
        "timeout": {
            "request_timeout": ConfigField(
                type=int,
                default=30,
                description="HTTP请求超时时间（秒）"
            )
        },
        "logging": {
            "level": ConfigField(
                type=str,
                default="INFO",
                description="日志记录级别",
                choices=["DEBUG", "INFO", "WARNING", "ERROR"]
            ),
            "enable_debug": ConfigField(
                type=bool,
                default=False,
                description="是否启用调试日志"
            )
        }
    }
    
    def get_plugin_components(self) -> List[Tuple[ComponentInfo, Type]]:
        """返回插件提供的组件列表
        
        Returns:
            [(ComponentInfo, ToolClass/CommandClass), ...] 元组列表
        """
        return [
            (AICharacterListTool.get_tool_info(), AICharacterListTool),
            (AIVoiceSendTool.get_tool_info(), AIVoiceSendTool),
            (ListAICharactersCommand.get_command_info(), ListAICharactersCommand),
        ]
