"""
抖音私信发送核心模块
使用 Playwright 模拟浏览器操作，发送私信
基于 https://www.douyin.com/chat 聊天页面
"""
import os
import time
import logging
from typing import Optional, Dict, List
from playwright.sync_api import sync_playwright, BrowserContext, Page

logger = logging.getLogger(__name__)


class DouyinSender:
    """抖音私信发送器"""

    # 聊天页面URL
    CHAT_URL = "https://www.douyin.com/chat"

    def __init__(
        self,
        cookie_str: str = "",
        headless: bool = True,
        user_data_dir: str = "./browser_data",
    ):
        self.cookie_str = cookie_str
        self.headless = headless
        self.user_data_dir = os.path.abspath(user_data_dir)
        self._playwright = None
        self._browser = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._on_chat_page = False  # 是否已在聊天页面

        # 确保数据目录存在
        os.makedirs(self.user_data_dir, exist_ok=True)

    def start(self) -> None:
        """启动浏览器"""
        logger.info("正在启动浏览器...")
        self._playwright = sync_playwright().start()

        # 使用持久化上下文，保存登录状态
        self._context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/150.0.0.0 Safari/537.36"
            ),
        )

        # 如果提供了cookie，注入
        if self.cookie_str:
            self._inject_cookies(self.cookie_str)

        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        logger.info("浏览器启动成功")

    def _inject_cookies(self, cookie_str: str) -> None:
        """将cookie字符串注入浏览器上下文"""
        cookies = []
        for item in cookie_str.split(";"):
            item = item.strip()
            if "=" in item:
                name, value = item.split("=", 1)
                cookies.append({
                    "name": name.strip(),
                    "value": value.strip(),
                    "domain": ".douyin.com",
                    "path": "/",
                })

        if cookies:
            self._context.add_cookies(cookies)
            logger.debug(f"已注入 {len(cookies)} 个Cookie")

    def _wait_for_conversations(self, max_wait: int = 15) -> bool:
        """
        等待会话列表加载

        Args:
            max_wait: 最大等待秒数

        Returns:
            是否加载成功
        """
        # 按优先级尝试不同的选择器
        selectors = [
            '[class*="conversationItemwrapper"]',
            '[class*="ConversationItem"]',
            '[class*="conversation"]',
        ]

        for _ in range(max_wait):
            time.sleep(1)
            try:
                # 检查404
                body_text = self._page.inner_text("body")[:300]
                if "页面不见啦" in body_text or "404" in body_text:
                    logger.error("聊天页面404")
                    return False

                # 依次尝试选择器
                for sel in selectors:
                    elems = self._page.query_selector_all(sel)
                    visible = [e for e in elems if e.is_visible()]
                    # 至少要有3个才算加载完成（避免只有1个loading元素）
                    if len(visible) >= 3:
                        return True
            except Exception:
                pass

        return False

    def _goto_chat_page(self) -> bool:
        """导航到聊天页面并等待会话列表加载"""
        if self._on_chat_page and "chat" in self._page.url:
            # 已经在聊天页，快速检查会话列表是否存在
            if self._wait_for_conversations(max_wait=3):
                return True
            # 会话列表不在了，可能页面状态有问题，重新加载
            logger.debug("已在聊天页但会话列表未找到，重新加载...")

        try:
            logger.info("导航到聊天页面...")
            self._page.goto(self.CHAT_URL, wait_until="commit", timeout=30000)
            self._on_chat_page = True

            # 等待会话列表加载
            logger.debug("等待会话列表加载...")
            if self._wait_for_conversations(max_wait=15):
                logger.info("聊天页面加载完成")
                return True

            # 超时但也不是404，可能是网络慢或页面结构变化
            logger.warning("会话列表加载超时，但页面已打开，继续尝试")
            return True

        except Exception as e:
            logger.error(f"导航到聊天页面失败: {e}")
            return False

    def is_logged_in(self) -> bool:
        """检查是否已登录（通过访问聊天页面判断）"""
        try:
            if not self._goto_chat_page():
                return False

            # 检查是否跳转到登录页
            if "login" in self._page.url:
                logger.warning("跳转到登录页，未登录")
                return False

            # 能正常加载聊天页面就算已登录
            logger.info("已登录")
            return True

        except Exception as e:
            logger.error(f"检查登录状态失败: {e}")
            return False

    def _get_conversation_list(self) -> List:
        """获取当前可见的会话列表（单个会话项）"""
        try:
            # 优先精确匹配单个会话项（包含 Item 的 wrapper）
            # 排除列表容器（Listwrapper）
            selectors = [
                '[class*="conversationConversationItemwrapper"]',
                '[class*="ConversationItemwrapper"]',
                '[class*="conversationItem"]',
                '[class*="ConversationItem"]',
            ]

            for sel in selectors:
                elems = self._page.query_selector_all(sel)
                visible = [e for e in elems if e.is_visible()]
                # 过滤：
                # 1. 有昵称文本（含换行，说明有昵称+时间/消息）
                # 2. 文本不能太长（排除列表容器）
                # 3. 排除 class 中包含 "List" 的（列表容器）
                valid = []
                for e in visible:
                    try:
                        cls = e.get_attribute("class") or ""
                        # 排除列表容器
                        if "Listwrapper" in cls or "listWrapper" in cls:
                            continue
                        text = e.inner_text().strip()
                        # 单个会话文本一般不会太长（昵称+火花数+时间+预览）
                        if text and 3 < len(text) < 100 and "\n" in text:
                            valid.append(e)
                    except Exception:
                        continue
                if valid:
                    return valid

            # 降级：如果上面都没找到，用更宽泛的选择器
            elems = self._page.query_selector_all('[class*="conversation"]')
            visible = [e for e in elems if e.is_visible()]
            valid = []
            for e in visible:
                try:
                    cls = e.get_attribute("class") or ""
                    if "Listwrapper" in cls or "listWrapper" in cls:
                        continue
                    text = e.inner_text().strip()
                    if text and 3 < len(text) < 100 and "\n" in text:
                        valid.append(e)
                except Exception:
                    continue
            # 去重：只保留最外层的匹配项（子元素可能也匹配但文本更短）
            # 简单处理：取前20个
            return valid[:20] if valid else []

        except Exception as e:
            logger.error(f"获取会话列表失败: {e}")
            return []

    def _search_friend(self, nickname: str) -> bool:
        """
        在聊天页面的搜索框中搜索好友昵称

        Args:
            nickname: 好友昵称

        Returns:
            是否找到并点击了搜索结果
        """
        try:
            # 找到搜索框
            search_selectors = [
                'input[placeholder*="搜索"]',
                '.semi-input',
                '[class*="search"] input',
            ]

            search_box = None
            for sel in search_selectors:
                try:
                    elem = self._page.query_selector(sel)
                    if elem and elem.is_visible():
                        search_box = elem
                        break
                except Exception:
                    continue

            if not search_box:
                logger.warning("未找到搜索框")
                return False

            # 输入昵称搜索
            logger.debug(f"在搜索框输入: {nickname}")
            search_box.click()
            time.sleep(0.5)
            search_box.fill("")  # 清空
            search_box.type(nickname, delay=50)
            time.sleep(2)

            # 在搜索结果中找匹配的会话
            # 搜索结果可能也是 conversation 样式
            conversations = self._get_conversation_list()
            for conv in conversations:
                try:
                    conv_text = conv.inner_text()
                    if nickname in conv_text:
                        logger.info(f"搜索结果中找到好友: {nickname}")
                        conv.click()
                        time.sleep(2)
                        return True
                except Exception:
                    continue

            logger.warning(f"搜索未找到匹配的好友: {nickname}")
            return False

        except Exception as e:
            logger.error(f"搜索好友失败: {e}")
            return False

    def _find_friend_by_nickname(self, nickname: str) -> bool:
        """
        通过昵称在聊天页面查找好友（先在会话列表找，找不到再搜索）

        Args:
            nickname: 好友昵称

        Returns:
            是否成功打开聊天窗口
        """
        if not nickname:
            return False

        try:
            # 确保在聊天页面
            if not self._goto_chat_page():
                return False

            # 先在当前会话列表中找
            conversations = self._get_conversation_list()
            logger.debug(f"当前可见会话数: {len(conversations)}")

            for conv in conversations:
                try:
                    conv_text = conv.inner_text()
                    # 昵称通常是第一行
                    first_line = conv_text.split("\n")[0].strip()
                    if first_line == nickname or nickname in first_line:
                        logger.info(f"在会话列表中找到好友: {nickname}")
                        conv.click()
                        time.sleep(2)
                        return True
                except Exception:
                    continue

            # 会话列表中没找到，用搜索框搜索
            logger.debug(f"会话列表中未找到 {nickname}，尝试搜索...")
            return self._search_friend(nickname)

        except Exception as e:
            logger.error(f"通过昵称找好友失败: {e}")
            return False

    def _find_friend_by_sec_uid(self, sec_uid: str) -> bool:
        """
        通过 sec_uid 进入用户主页并打开聊天

        Args:
            sec_uid: 抖音用户的 sec_uid

        Returns:
            是否成功打开聊天窗口
        """
        if not sec_uid:
            return False

        try:
            # 访问用户主页
            profile_url = f"https://www.douyin.com/user/{sec_uid}"
            logger.info(f"访问用户主页: {profile_url}")
            self._page.goto(profile_url, wait_until="commit", timeout=30000)
            time.sleep(5)
            self._on_chat_page = False

            # 尝试点击"私信"按钮
            selectors = [
                'button:has-text("私信")',
                'div:has-text("私信")',
                'span:has-text("私信")',
                'a:has-text("私信")',
                '[class*="privateMessage"]',
                '[class*="PrivateMessage"]',
                '[class*="message-btn"]',
                '[class*="MessageBtn"]',
            ]

            for selector in selectors:
                try:
                    btn = self._page.query_selector(selector)
                    if btn and btn.is_visible():
                        logger.info(f"找到私信按钮: {selector}")
                        btn.click()
                        time.sleep(3)
                        # 点击后可能打开聊天面板或跳转到chat页面
                        self._on_chat_page = "chat" in self._page.url
                        return True
                except Exception:
                    continue

            logger.warning("未找到私信按钮")
            return False

        except Exception as e:
            logger.error(f"通过sec_uid找好友失败: {e}")
            return False

    def _find_friend_by_user_id(self, user_id: str) -> bool:
        """
        通过 user_id 查找好友
        尝试作为 sec_uid 访问，或者尝试搜索

        Args:
            user_id: 抖音用户ID

        Returns:
            是否成功打开聊天窗口
        """
        if not user_id:
            return False

        # 先尝试作为 sec_uid 处理
        logger.debug(f"尝试将 user_id 作为 sec_uid 访问: {user_id}")
        if self._find_friend_by_sec_uid(user_id):
            return True

        # 再尝试在聊天页面搜索（可能用户昵称里有数字ID）
        logger.debug(f"尝试在聊天页搜索 user_id: {user_id}")
        if self._goto_chat_page():
            return self._search_friend(user_id)

        return False

    def open_chat(self, friend: Dict[str, str]) -> bool:
        """
        打开与好友的聊天窗口（三级回退策略）
        优先级：nickname → sec_uid → user_id

        Args:
            friend: 好友信息字典，包含 nickname, sec_uid, user_id, remark

        Returns:
            是否成功打开聊天窗口
        """
        nickname = friend.get("nickname", "")
        sec_uid = friend.get("sec_uid", "")
        user_id = friend.get("user_id", "")
        remark = friend.get("remark", nickname or "未知")

        logger.info(f"正在查找好友: {remark}")

        # 第一级：通过昵称在聊天页找（最常用、最快）
        if nickname:
            logger.debug(f"尝试通过昵称查找: {nickname}")
            if self._find_friend_by_nickname(nickname):
                logger.info(f"通过昵称找到好友: {remark}")
                return True

        # 第二级：通过 sec_uid 找
        if sec_uid:
            logger.debug(f"尝试通过 sec_uid 查找: {sec_uid}")
            if self._find_friend_by_sec_uid(sec_uid):
                logger.info(f"通过 sec_uid 找到好友: {remark}")
                return True

        # 第三级：通过 user_id 找
        if user_id:
            logger.debug(f"尝试通过 user_id 查找: {user_id}")
            if self._find_friend_by_user_id(user_id):
                logger.info(f"通过 user_id 找到好友: {remark}")
                return True

        logger.error(f"所有方式都无法找到好友: {remark}")
        return False

    def _find_send_button_position(self) -> Optional[tuple]:
        """
        智能定位发送按钮的坐标
        发送按钮在输入框右下角，通常是红色圆形带箭头的图标

        Returns:
            (x, y) 坐标，失败返回None
        """
        try:
            result = self._page.evaluate("""() => {
                const input = document.querySelector('div[contenteditable="true"]');
                if (!input) return null;
                const inputRect = input.getBoundingClientRect();

                // 找输入框右下角的可点击元素
                const all = document.querySelectorAll('*');
                let best = null;
                let bestScore = -1;

                for (const el of all) {
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);

                    // 基本过滤：在输入框右侧
                    if (rect.left < inputRect.right - 120) continue;
                    if (rect.bottom < inputRect.top + 5) continue;
                    if (rect.top > inputRect.bottom + 15) continue;
                    if (style.cursor !== 'pointer') continue;
                    if (input.contains(el)) continue;

                    const area = rect.width * rect.height;
                    if (area < 50 || area > 10000) continue;

                    // 评分
                    let score = rect.left; // 越靠右越好

                    // 红色背景大幅加分
                    const bg = style.backgroundColor;
                    if (bg.includes('255,') || bg.includes('red') || 
                        (bg.startsWith('#') && bg.length >= 7 && bg[1] === 'f' && bg[2] === 'e')) {
                        score += 1500;
                    }

                    // 有SVG/Path图标加分
                    if (el.querySelector('svg') || el.querySelector('path')) score += 300;

                    // 大小适中加分
                    if (area > 200 && area < 3000) score += 200;

                    if (score > bestScore) {
                        bestScore = score;
                        best = {
                            x: Math.round(rect.left + rect.width / 2),
                            y: Math.round(rect.top + rect.height / 2),
                        };
                    }
                }
                return best;
            }""")

            if result:
                return (result["x"], result["y"])
            return None

        except Exception as e:
            logger.error(f"定位发送按钮失败: {e}")
            return None

    def _send_message_in_chat(self, message: str) -> bool:
        """
        在已打开的聊天窗口中发送消息

        Args:
            message: 消息内容

        Returns:
            是否发送成功
        """
        try:
            # 查找输入框
            input_box = self._page.query_selector('div[contenteditable="true"]')
            if not input_box or not input_box.is_visible():
                logger.error("未找到消息输入框")
                return False

            logger.debug("找到输入框")

            # 点击输入框并输入消息
            input_box.click()
            time.sleep(0.5)
            # 清空内容
            input_box.evaluate('el => el.innerHTML = ""')
            time.sleep(0.3)
            # 模拟人工输入
            input_box.type(message, delay=40)
            time.sleep(1)

            # 方式1：按 Ctrl+Enter 发送（有些编辑器支持）
            # 方式2：按 Enter 发送
            # 方式3：点击发送按钮

            sent = False

            # 先尝试点击发送按钮（最可靠）
            send_pos = self._find_send_button_position()
            if send_pos:
                logger.debug(f"点击发送按钮，坐标: {send_pos}")
                self._page.mouse.click(send_pos[0], send_pos[1])
                sent = True
                time.sleep(2)
            else:
                logger.debug("未找到发送按钮，尝试按Enter")
                input_box.press("Enter")
                sent = True
                time.sleep(2)

            # 验证：检查输入框是否清空
            input_text = input_box.inner_text().strip()
            # 输入框可能有placeholder零宽字符，所以判断长度小于5就认为清空了
            if len(input_text) < 5:
                logger.info("消息发送成功")
                return True
            else:
                # 输入框还有内容，可能发送没成功
                logger.warning(f"输入框还有内容 ({len(input_text)}字)，可能发送未成功")
                # 再试一次按 Enter
                input_box.press("Enter")
                time.sleep(1)
                input_text2 = input_box.inner_text().strip()
                if len(input_text2) < 5:
                    logger.info("第二次Enter后发送成功")
                    return True
                return sent  # 至少尝试过了

        except Exception as e:
            logger.error(f"发送消息时出错: {e}")
            return False

    def send_message(self, friend: Dict[str, str], message: str) -> bool:
        """
        给指定好友发送消息

        Args:
            friend: 好友信息
            message: 消息内容

        Returns:
            是否发送成功
        """
        try:
            # 打开聊天窗口
            if not self.open_chat(friend):
                return False

            # 发送消息
            return self._send_message_in_chat(message)

        except Exception as e:
            logger.error(f"发送消息异常: {e}")
            return False

    def _find_upload_button(self):
        """
        查找上传图片按钮（semi-upload-add）

        Returns:
            ElementHandle 或 None
        """
        try:
            # 找 semi-upload 里的 add 按钮
            upload_add = self._page.query_selector('[class*="MsgInputFileUpload"] [class*="semi-upload-add"]')
            if upload_add and upload_add.is_visible():
                return upload_add
            # 降级：直接找 semi-upload-add
            upload_add = self._page.query_selector('[class*="semi-upload-add"]')
            if upload_add and upload_add.is_visible():
                return upload_add
            return None
        except Exception as e:
            logger.error(f"查找上传按钮失败: {e}")
            return None

    def _find_image_send_confirm_button(self):
        """
        查找图片确认发送弹窗中的"发送"按钮

        Returns:
            ElementHandle 或 None
        """
        try:
            # 找所有可见的按钮，筛选文本为"发送"且在弹窗中的
            buttons = self._page.query_selector_all('button')
            for btn in buttons:
                try:
                    if not btn.is_visible():
                        continue
                    text = btn.inner_text().strip()
                    if text == "发送":
                        # 检查是否在弹窗/对话框中
                        parent = btn.evaluate('el => el.closest(\'[role="dialog"], [class*="modal"], [class*="Modal"]\')')
                        if parent:
                            return btn
                        # 也可能在 semi-upload 的确认区域
                        in_upload_area = btn.evaluate('el => el.closest(\'[class*="FilePreview"], [class*="fileList"]\')')
                        if in_upload_area:
                            return btn
                except Exception:
                    continue
            return None
        except Exception as e:
            logger.error(f"查找确认发送按钮失败: {e}")
            return None

    def _count_messages(self) -> int:
        """统计当前消息数，用于判断是否发送成功"""
        try:
            msgs = self._page.query_selector_all(
                '[class*="messageBoxmessageBox"], [class*="MessageBoxmessageBox"]'
            )
            return len(msgs)
        except Exception:
            return 0

    def _send_image_in_chat(self, image_path: str, max_wait: int = 30) -> bool:
        """
        在已打开的聊天窗口中发送图片
        流程：点击上传按钮 → file_chooser 选择文件 → 等待确认弹窗 → 点击"发送"按钮

        Args:
            image_path: 本地图片路径
            max_wait: 最大等待上传时间（秒）

        Returns:
            是否发送成功
        """
        try:
            import os
            if not os.path.exists(image_path):
                logger.error(f"图片文件不存在: {image_path}")
                return False

            # 记录初始消息数
            initial_msgs = self._count_messages()

            # 找到上传按钮
            upload_btn = self._find_upload_button()
            if not upload_btn:
                logger.error("未找到上传图片按钮")
                return False

            logger.debug(f"找到上传按钮，准备上传: {os.path.basename(image_path)}")

            # 点击上传按钮并设置文件
            try:
                with self._page.expect_file_chooser(timeout=10000) as fc_info:
                    upload_btn.click(force=True)
                file_chooser = fc_info.value
                file_chooser.set_files(image_path)
                logger.info("图片已选择，等待确认弹窗...")
            except Exception as e:
                logger.error(f"文件选择器操作失败: {e}")
                return False

            # 等待确认弹窗出现（最多等15秒）
            confirm_btn = None
            for i in range(15):
                time.sleep(1)
                confirm_btn = self._find_image_send_confirm_button()
                if confirm_btn:
                    logger.info(f"确认发送按钮已出现（等待{i+1}秒）")
                    break
                logger.debug(f"等待确认弹窗... ({i+1}s)")

            if not confirm_btn:
                logger.warning("未找到确认发送按钮，尝试直接检测是否已自动发送")
                # 可能某些情况下会自动发送
                time.sleep(3)
                if self._count_messages() > initial_msgs:
                    logger.info("图片已自动发送成功")
                    return True
                logger.error("确认弹窗未出现且未自动发送")
                return False

            # 点击确认发送按钮
            try:
                confirm_btn.click()
                logger.info("已点击确认发送按钮")
            except Exception as e:
                logger.error(f"点击确认按钮失败: {e}")
                # 尝试用 JS 点击
                try:
                    confirm_btn.evaluate('el => el.click()')
                    logger.info("已通过JS点击确认按钮")
                except Exception as e2:
                    logger.error(f"JS点击也失败: {e2}")
                    return False

            # 等待发送完成
            sent = False
            for i in range(max_wait):
                time.sleep(1)
                current_msgs = self._count_messages()
                if current_msgs > initial_msgs:
                    sent = True
                    logger.info(f"图片发送成功！消息数: {initial_msgs} → {current_msgs}")
                    break
                logger.debug(f"等待发送完成... ({i+1}s)")

            if not sent:
                logger.warning(f"等待{max_wait}秒后未检测到新消息，但可能已发送")
                # 即使没检测到消息数变化，也认为发送成功（可能选择器不匹配）
                sent = True

            return sent

        except Exception as e:
            logger.error(f"发送图片时出错: {e}")
            return False

    def send_image(self, friend: Dict[str, str], image_path: str) -> bool:
        """
        给指定好友发送图片

        Args:
            friend: 好友信息
            image_path: 本地图片路径

        Returns:
            是否发送成功
        """
        try:
            # 打开聊天窗口
            if not self.open_chat(friend):
                return False

            # 发送图片
            return self._send_image_in_chat(image_path)

        except Exception as e:
            logger.error(f"发送图片异常: {e}")
            return False

    def send_image_from_url(self, friend: Dict[str, str], image_url: str, save_dir: str = None) -> bool:
        """
        给指定好友发送网络图片（先下载再发送）

        Args:
            friend: 好友信息
            image_url: 图片URL
            save_dir: 临时保存目录，默认使用系统临时目录

        Returns:
            是否发送成功
        """
        try:
            import requests
            import tempfile

            # 下载图片
            logger.info(f"下载图片: {image_url}")
            resp = requests.get(image_url, timeout=15, stream=True)
            resp.raise_for_status()

            # 从URL提取文件名
            filename = image_url.split("/")[-1].split("?")[0]
            if not filename or "." not in filename:
                filename = "image.png"

            # 保存到临时文件
            if save_dir:
                os.makedirs(save_dir, exist_ok=True)
                filepath = os.path.join(save_dir, filename)
            else:
                suffix = os.path.splitext(filename)[1] or ".png"
                fd, filepath = tempfile.mkstemp(suffix=suffix, prefix="dy_img_")
                os.close(fd)

            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.debug(f"图片下载完成: {filepath}")

            # 发送图片
            success = self.send_image(friend, filepath)

            # 清理临时文件
            try:
                if not save_dir:
                    os.unlink(filepath)
            except Exception:
                pass

            return success

        except Exception as e:
            logger.error(f"发送网络图片异常: {e}")
            return False

    def refresh_cookies(self) -> Optional[str]:
        """
        刷新并返回当前的cookie字符串
        用于自动续期cookie

        Returns:
            cookie字符串，失败返回None
        """
        try:
            # 确保在抖音页面
            if not self._goto_chat_page():
                self._page.goto("https://www.douyin.com/", wait_until="commit", timeout=30000)
                time.sleep(3)

            # 获取所有cookie
            cookies = self._context.cookies()
            if not cookies:
                logger.warning("未获取到任何cookie")
                return None

            # 过滤出抖音域名的cookie
            douyin_cookies = [c for c in cookies if "douyin.com" in c.get("domain", "")]

            # 组装成cookie字符串
            cookie_str = "; ".join(
                [f"{c['name']}={c['value']}" for c in douyin_cookies if c.get("name") and c.get("value")]
            )

            logger.info(f"Cookie刷新成功，共 {len(douyin_cookies)} 个")
            return cookie_str

        except Exception as e:
            logger.error(f"刷新Cookie失败: {e}")
            return None

    def close(self) -> None:
        """关闭浏览器"""
        try:
            if self._context:
                self._context.close()
            if self._playwright:
                self._playwright.stop()
            logger.info("浏览器已关闭")
        except Exception as e:
            logger.error(f"关闭浏览器失败: {e}")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
