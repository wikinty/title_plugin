import re
import json
import requests
from typing import List, Tuple, Type, Optional

from src.plugin_system import (
    BasePlugin, register_plugin, BaseCommand, ConfigField, ComponentInfo
)
from src.common.logger import get_logger

logger = get_logger("title_plugin")


class titleCommand(BaseCommand):
    """头衔管理Command - 响应/title命令"""

    command_name = "title"
    command_description = "管理自定义头衔"

    # ===命令设置===
    command_pattern = r"^/title(?P<args>.*)$"  # 匹配所有/title变体

    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        """管理头衔"""
        try:
            # 获取当前用户和群组信息
            user_info = self.message.message_info.user_info
            group_info = self.message.message_info.group_info
            
            # 检查是否在群聊中（专属头衔只能在群聊中设置）
            if not group_info:
                await self.send_text("专属头衔只能在群聊中设置哦~")
                return True, "不在群聊中，无法设置头衔", False
            
            # 获取原始命令文本
            raw_text = self.message.processed_plain_text
            
            # 解析命令类型和内容
            if raw_text == "/title" or raw_text == "/title ":
                # "/title" 或 "/title " - 收回头衔
                return await self._remove_title(group_info, user_info)
            
            elif raw_text.startswith("/title "):
                # "/title <内容>" - 添加头衔
                # 删减 "/title " (共7个字符)
                content = raw_text[7:]
                return await self._set_title(group_info, user_info, content)
            else:
                # 处理其他情况
                return await self._handle_special_cases(raw_text, group_info, user_info)

        except Exception as e:
            logger.error(f"处理头衔命令时发生错误: {e}")
            await self.send_text("❌ 处理命令时发生错误，请稍后重试~")
            return True, f"处理错误: {e}", False

    async def _handle_special_cases(self, raw_text: str, group_info, user_info) -> Tuple[bool, Optional[str], bool]:
        """处理特殊情况的命令"""
        # 处理 "/title    " (多个空格) 的情况
        if re.match(r"^/title\s+$", raw_text):
            # 计算空格数量 (删减 "/title" 共6个字符后的部分)
            spaces = raw_text[6:]
            # 如果空格数量>=1，则删减一个空格
            if len(spaces) >= 1:
                spaces = spaces[1:]
            return await self._set_title(group_info, user_info, spaces)
        
        # 默认情况：尝试直接设置头衔
        return await self._set_title(group_info, user_info, raw_text[7:] if raw_text.startswith("/title ") else raw_text)

    async def _set_title(self, group_info, user_info, title_content: str) -> Tuple[bool, Optional[str], bool]:
        """设置用户头衔"""
        try:
            # 获取配置中的API地址
            api_url = self.plugin_config.get("api", {}).get("url", "http://127.0.0.1:3000")
            
            # 构建请求数据
            request_data = {
                "group_id": str(group_info.group_id),
                "user_id": str(user_info.user_id),
                "special_title": title_content
            }
            
            # 发送请求设置头衔
            full_url = f"{api_url}/set_group_special_title"
            headers = {'Content-Type': 'application/json'}
            
            logger.info(f"设置头衔请求: {full_url}, 数据: {request_data}")
            
            try:
                response = requests.post(
                    full_url, 
                    headers=headers, 
                    data=json.dumps(request_data),
                    timeout=10
                )
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"设置头衔响应: {result}")
                
                # 根据响应结果判断是否成功
                if result.get("status") == "ok" or response.status_code == 200:
                    if title_content.strip():  # 非空头衔
                        display_content = f"{title_content}" if title_content else "空头衔"
                        await self.send_text(f"✅ 已为你设置专属头衔：{display_content}")
                    else:  # 空头衔或空格头衔
                        space_count = len(title_content)
                        if space_count > 0:
                            await self.send_text(f"✅ 已为你设置专属头衔：{display_content}")
                        else:
                            await self.send_text("✅ 已收回头衔")
                    return True, f"成功设置头衔: {title_content}", False
                else:
                    error_msg = result.get("message", "未知错误")
                    await self.send_text(f"❌ 设置头衔失败：{error_msg}")
                    return True, f"设置头衔失败: {error_msg}", False
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"请求设置头衔API失败: {e}")
                await self.send_text("❌ 网络错误，请稍后重试~")
                return True, f"API请求失败: {e}", False
                
        except Exception as e:
            logger.error(f"设置头衔时发生未知错误: {e}")
            #await self.send_text("❌ 设置头衔时发生错误，请稍后重试~")
            return True, f"未知错误: {e}", False

    async def _remove_title(self, group_info, user_info) -> Tuple[bool, Optional[str], bool]:
        """收回头衔（设置为空字符串）"""
        return await self._set_title(group_info, user_info, "")


@register_plugin
class titlePlugin(BasePlugin):
    """头衔赋予插件"""

    plugin_name = "title_plugin"
    enable_plugin = True
    dependencies = []
    python_dependencies = ["requests"]
    config_file_name = "config.toml"

    config_schema: dict = {
        "plugin": {
            "name": ConfigField(type=str, default="title_plugin", description="插件名称"),
            "version": ConfigField(type=str, default="1.0.0", description="插件版本"),
            "enabled": ConfigField(type=bool, default=True, description="是否启用插件"),
        },
        "api": {
            "url": ConfigField(type=str, default="http://127.0.0.1:3000", description="API服务器地址"),
        }
    }

    def get_plugin_components(self) -> List[Tuple[ComponentInfo, Type]]:
        """返回插件包含的组件列表"""
        return [
            (titleCommand.get_command_info(), titleCommand),
        ]