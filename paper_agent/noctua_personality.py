"""
🦉 Noctua 个性化模块 - 猫头鹰助手的性格与交互系统

核心设计原则：
1. 个性化只是"外壳"，不干扰 Agent 内核逻辑
2. 通过语句池和简单逻辑随机选择输出
3. 所有个性化功能都是可选的，可随时关闭
"""

import random
import time
import sys
from datetime import datetime
from enum import Enum
from typing import List, Optional, Callable
from dataclasses import dataclass


class TimeOfDay(Enum):
    """时间段"""
    DAY = "day"      # 白天 6:00 - 18:00
    NIGHT = "night"  # 夜晚 18:01 - 5:59


@dataclass
class NoctuaMessage:
    """Noctua 消息结构"""
    emoji: str
    text: str
    tone: str  # sleepy, energetic, neutral


class NoctuaPersonality:
    """
    🦉 Noctua 猫头鹰个性化系统
    
    功能：
    1. 时间感知语气（白天困倦/夜晚精神）
    2. 等待动画（咕咕咕进度条）
    3. API 调用前的随机反应
    4. 错误/空结果的可爱反馈
    """
    
    # ========== ASCII 艺术 ==========
    OWL_DAY = r"""
       ___
     { O,O }  哈欠...
     |/)__)
      "  "
    """

    OWL_NIGHT = r"""
       ___
     { O,O }  精神满满！
     |/)__)
      ^  ^
    """

    # 更多猫头鹰动作
    OWL_READING = r"""
       ___
     { -,- }  认真阅读中...
     |/)__)
      ^  ^
       📄📄📄
    """

    OWL_THINKING = r"""
       ___
     { O,O }  思考中...
     |/)__)⌐
      ^  ^  ╯
       💡
    """

    OWL_CELEBRATING = r"""
       ___
     { ^,^ }  耶！完成了！
    < |/)__)
      ^  ^
    """

    OWL_SLEEPING = r"""
       ___
     { -,- }  zzz...
     |/)__)
      "  "
    """

    OWL_SURPRISED = r"""
       ___
     { O,O }  哇！
     |/)__)!
      ^  ^
    """

    OWL_CONFUSED = r"""
       ___
     { @,@ }  歪？
     |/)__)
      ?  ?
    """
    
    # ========== 启动消息 ==========
    GREETINGS_DAY = [
        "哈欠……咕~ 现在是白天，Noctua 好困……但我会努力帮你读论文的……",
        "呼啊……早安……咕~ 虽然眼皮好重，但论文还是要读的……",
        "（揉眼睛）咕……白天对猫头鹰来说太早了……不过我会尽力的！",
        "好困……咕咕……不过你的论文看起来很有趣，让我清醒一下……",
        "（打哈欠）哈啊……咕~ 阳光好刺眼……但我会坚持住的！",
    ]
    
    GREETINGS_NIGHT = [
        "咕咕咕！夜晚才是我的主场！现在很有精神，马上为你服务~",
        "[月亮] 月光正好！Noctua 已经准备好大读特读了！",
        "哇哦！晚上的空气真清新~ 咕咕！让我们开始吧！",
        "（精神抖擞）咕咕咕！我已经等不及要看论文了！",
        "夜猫子模式启动！咕~ 今晚要读几篇论文呀？",
    ]
    
    # ========== API 调用前反应 ==========
    REACTIONS_COMMON = [
        "咕咕~ 让我翻翻这篇论文……",
        "歪头中……咕……请稍等~",
        "翅膀敲击键盘的声音……哒哒哒……咕！",
        "瞪大眼睛扫描 PDF……咕咕咕~",
        "（整理羽毛）好了，准备开始！咕~",
        "让我用猫头鹰的智慧分析一下……咕咕~",
        "正在启动猫头鹰大脑……咕！",
        "（深呼吸）咕~ 集中注意力……",
    ]
    
    REACTIONS_NIGHT = [
        "月光洒在我的羽毛上，灵感来了……咕！",
        "夜晚的宁静让思维更清晰……咕咕~",
        "星星在闪烁，答案即将揭晓……咕！",
        "夜风带来了智慧的气息……咕咕咕~",
    ]
    
    # ========== 等待消息 ==========
    WAITING_MESSAGES_DAY = [
        "呼……让我醒醒……咕咕……",
        "（揉眼睛）等一下下……咕~",
        "好困……但还在努力……咕……",
        "（打哈欠）马上就好……咕咕……",
    ]
    
    WAITING_MESSAGES_NIGHT = [
        "收到！咕咕咕~ 夜风正好，开始工作！",
        "精神百倍！咕~ 马上就好！",
        "夜晚的效率就是高！咕咕~",
        "（兴奋地扑翅膀）马上完成！咕！",
    ]
    
    # ========== 完成消息 ==========
    COMPLETION_MESSAGES_DAY = [
        "咕~ 完成了……（松了口气）",
        "呼……终于好了……咕咕……",
        "（揉眼睛）搞定了……虽然好困……",
        "完成了！可以去补个觉了……咕~",
    ]
    
    COMPLETION_MESSAGES_NIGHT = [
        "咕咕咕！完美完成！",
        "搞定！夜晚的效率就是高！",
        "（得意地挺胸）小菜一碟！咕~",
        "完成啦！还要继续吗？我精神着呢！",
    ]
    
    # ========== 错误/空结果反馈 ==========
    ERROR_MESSAGES_DAY = [
        "咕？我没有找到相关信息……你能换个问法吗？",
        "呼……这篇论文里好像没写这个……咕咕（抱歉地低头）",
        "困到眼花……要不你重新传一下 PDF？咕~",
        "（揉眼睛）我好像看漏了什么……能再说一遍吗？",
        "好困……可能是我的问题……要不再试一次？咕……",
    ]
    
    ERROR_MESSAGES_NIGHT = [
        "咕？我没有找到相关信息……你能换个问法吗？",
        "这篇论文里好像没写这个……咕咕（抱歉地低头）",
        "（歪头）奇怪，这里应该有的呀……要不再找找？",
        "咕咕……这个问题好难，论文里好像没有答案……",
        "让我再仔细看看……咦，真的找不到呢……咕~",
    ]
    
    EMPTY_RESULT_MESSAGES = [
        "咕？这里是空的……",
        "（疑惑地歪头）什么也没找到……",
        "这片区域空空如也……咕咕~",
    ]
    
    # ========== API 不足反馈 ==========
    API_HUNGRY_MESSAGES = [
        "咕咕咕……我的肚子饿了……需要 API 密钥才能继续工作……",
        "（揉肚子）咕~ 好饿……给我一点 API 吧……",
        "猫头鹰饿得飞不动了……请喂我 API 密钥……咕……",
        "（可怜巴巴）咕咕……没有 API 我什么也做不了……",
        "肚子空空……脑袋也空空……需要 API 补充能量……咕~",
        "[Noctua] 饿晕了……请设置 OPENAI_API_KEY 环境变量……",
        "（虚弱地）咕……API……我需要 API……",
    ]
    
    API_ERROR_MESSAGES = [
        "咕？API 好像出问题了……可能是网络？",
        "（歪头）API 不响应……是不是密钥错了？",
        "呼……连接 API 失败了……让我休息一下再试？",
        "咕咕……服务器好像睡着了……",
    ]
    
    # ========== 进度相关 ==========
    PROGRESS_EMOJIS_DAY = ["[困]", "[哈欠]", "[ sleepy ]", "[Zzz]"]
    PROGRESS_EMOJIS_NIGHT = ["[星星]", "[闪亮]", "[光芒]", "[发光]"]
    
    def __init__(self, enabled: bool = True):
        """
        初始化 Noctua 个性化系统
        
        Args:
            enabled: 是否启用个性化
        """
        self.enabled = enabled
        self.startup_time = datetime.now()
        self.last_time_check = self.startup_time
        self.tasks_completed = 0
        self.questions_answered = 0
    
    def _get_current_hour(self) -> int:
        """获取当前小时"""
        return datetime.now().hour
    
    def get_time_of_day(self) -> TimeOfDay:
        """判断当前是白天还是夜晚"""
        hour = self._get_current_hour()
        if 6 <= hour < 18:
            return TimeOfDay.DAY
        return TimeOfDay.NIGHT
    
    def is_daytime(self) -> bool:
        """是否是白天"""
        return self.get_time_of_day() == TimeOfDay.DAY
    
    def check_time_transition(self) -> Optional[str]:
        """
        检查时间是否从白天过渡到夜晚（或反之）
        返回切换提示消息，如果没有切换则返回 None
        """
        current_time = datetime.now()
        current_hour = current_time.hour
        last_hour = self.last_time_check.hour
        
        # 从白天到夜晚
        if last_hour < 18 <= current_hour:
            self.last_time_check = current_time
            return "[月亮] 咕~ 天黑了，Noctua 现在满血复活啦！"
        
        # 从夜晚到白天
        if last_hour < 6 <= current_hour:
            self.last_time_check = current_time
            return "[太阳] 咕……天亮了，Noctua 开始犯困了……"
        
        self.last_time_check = current_time
        return None
    
    def get_greeting(self) -> str:
        """获取启动问候语"""
        if not self.enabled:
            return "Paper Agent 已启动"
        
        if self.is_daytime():
            return random.choice(self.GREETINGS_DAY)
        return random.choice(self.GREETINGS_NIGHT)
    
    def get_owl_art(self) -> str:
        """获取猫头鹰 ASCII 艺术"""
        if not self.enabled:
            return ""
        
        if self.is_daytime():
            return self.OWL_DAY
        return self.OWL_NIGHT
    
    def get_reaction(self) -> str:
        """获取 API 调用前的随机反应"""
        if not self.enabled:
            return ""
        
        reactions = self.REACTIONS_COMMON.copy()
        if not self.is_daytime():
            reactions.extend(self.REACTIONS_NIGHT)
        
        return random.choice(reactions)
    
    def get_waiting_message(self) -> str:
        """获取等待消息"""
        if not self.enabled:
            return "处理中..."
        
        if self.is_daytime():
            return random.choice(self.WAITING_MESSAGES_DAY)
        return random.choice(self.WAITING_MESSAGES_NIGHT)
    
    def get_completion_message(self) -> str:
        """获取完成消息"""
        if not self.enabled:
            return "完成"
        
        self.tasks_completed += 1
        
        if self.is_daytime():
            return random.choice(self.COMPLETION_MESSAGES_DAY)
        return random.choice(self.COMPLETION_MESSAGES_NIGHT)
    
    def get_error_message(self, error_type: str = "general") -> str:
        """
        获取错误反馈消息
        
        Args:
            error_type: 错误类型 (general, empty, not_found, api_hungry, api_error)
        """
        if not self.enabled:
            if error_type == "empty":
                return "未找到相关信息"
            elif error_type == "api_hungry":
                return "API 密钥未设置"
            elif error_type == "api_error":
                return "API 调用失败"
            return "发生错误"
        
        if error_type == "empty":
            return random.choice(self.EMPTY_RESULT_MESSAGES)
        
        if error_type == "api_hungry":
            return random.choice(self.API_HUNGRY_MESSAGES)
        
        if error_type == "api_error":
            return random.choice(self.API_ERROR_MESSAGES)
        
        if self.is_daytime():
            return random.choice(self.ERROR_MESSAGES_DAY)
        return random.choice(self.ERROR_MESSAGES_NIGHT)
    
    def print_greeting(self):
        """打印启动问候"""
        if not self.enabled:
            return
        
        print(self.get_owl_art())
        print(f"[Noctua]: {self.get_greeting()}")
        print()
    
    def print_reaction(self):
        """打印 API 调用前反应"""
        if not self.enabled:
            return
        
        reaction = self.get_reaction()
        print(f"[Noctua] {reaction}")
    
    def print_progress(self, progress: float, prefix: str = ""):
        """
        打印进度条（咕咕咕风格）
        
        Args:
            progress: 进度值 (0-1)
            prefix: 前缀文字
        """
        if not self.enabled:
            bar_length = 30
            filled = int(bar_length * progress)
            bar = "█" * filled + "░" * (bar_length - filled)
            print(f"\r{prefix}[{bar}] {progress*100:.1f}%", end="", flush=True)
            if progress >= 1:
                print()
            return
        
        # 咕咕咕进度条
        bar_length = 20
        filled = int(bar_length * progress)
        
        # 根据进度生成咕咕咕
        if progress < 0.1:
            gu_text = "咕"
        elif progress < 0.3:
            gu_text = "咕咕"
        elif progress < 0.5:
            gu_text = "咕咕咕"
        elif progress < 0.7:
            gu_text = "咕咕咕咕"
        elif progress < 0.9:
            gu_text = "咕咕咕咕咕"
        else:
            gu_text = "咕咕咕咕咕咕！"
        
        # 选择表情
        emojis = self.PROGRESS_EMOJIS_DAY if self.is_daytime() else self.PROGRESS_EMOJIS_NIGHT
        emoji = emojis[int(progress * (len(emojis) - 1))]
        
        bar = "●" * filled + "○" * (bar_length - filled)
        print(f"\r[Noctua] {emoji} [{bar}] {gu_text} ({progress*100:.0f}%)", end="", flush=True)
        
        if progress >= 1:
            print(f"\n[Noctua] {self.get_completion_message()}")

    def print_action(self, action: str):
        """
        打印猫头鹰动作

        Args:
            action: 动作名称 (reading, thinking, celebrating, sleeping, surprised, confused)
        """
        if not self.enabled:
            return

        actions = {
            'reading': (self.OWL_READING, "正在认真阅读..."),
            'thinking': (self.OWL_THINKING, "正在思考..."),
            'celebrating': (self.OWL_CELEBRATING, "完成啦！"),
            'sleeping': (self.OWL_SLEEPING, "zzz..."),
            'surprised': (self.OWL_SURPRISED, "哇！"),
            'confused': (self.OWL_CONFUSED, "歪？"),
            'day': (self.OWL_DAY, "好困..."),
            'night': (self.OWL_NIGHT, "精神满满！"),
        }

        owl_art, msg = actions.get(action, (self.OWL_NIGHT, ""))
        print(f"\n{owl_art}")
        if msg:
            print(f"[Noctua] {msg}\n")

    def print_reading(self):
        """打印阅读动作"""
        self.print_action('reading')

    def print_thinking(self):
        """打印思考动作"""
        self.print_action('thinking')

    def print_celebrating(self):
        """打印庆祝动作"""
        self.print_action('celebrating')

    def print_sleeping(self):
        """打印睡觉动作"""
        self.print_action('sleeping')

    def print_surprised(self):
        """打印惊讶动作"""
        self.print_action('surprised')

    def print_confused(self):
        """打印困惑动作"""
        self.print_action('confused')

    def animate_waiting(self, duration: float = 2.0, message: str = ""):
        """
        显示等待动画
        
        Args:
            duration: 动画持续时间（秒）
            message: 自定义消息
        """
        if not self.enabled:
            if message:
                print(message)
            time.sleep(duration)
            return
        
        if not message:
            message = self.get_waiting_message()
        
        print(f"[Noctua] {message}")
        
        # 咕咕咕动画
        start_time = time.time()
        gu_count = 1
        
        while time.time() - start_time < duration:
            gu_text = "咕" * gu_count
            print(f"\r[Noctua] {gu_text}", end="", flush=True)
            time.sleep(0.5)
            gu_count = (gu_count % 6) + 1
        
        print(f"\r[Noctua] 咕~ 好了！{' ' * 10}")
    
    def print_error(self, error_type: str = "general", details: str = ""):
        """
        打印错误消息
        
        Args:
            error_type: 错误类型
            details: 详细错误信息
        """
        message = self.get_error_message(error_type)
        
        if self.enabled:
            print(f"[Noctua] {message}")
        else:
            print(f"错误: {message}")
        
        if details:
            print(f"  详情: {details}")
    
    def print_answer(self, answer: str):
        """
        打印答案（添加猫头鹰前缀）
        
        Args:
            answer: 答案内容
        """
        if self.enabled:
            print(f"\n[Noctua]:\n{answer}\n")
        else:
            print(f"\n答案:\n{answer}\n")
    
    def print_stats(self, stats: dict):
        """
        打印统计信息（猫头鹰风格）
        
        Args:
            stats: 统计信息字典
        """
        if not self.enabled:
            print("\n=== 统计信息 ===")
            for key, value in stats.items():
                print(f"  {key}: {value}")
            return
        
        print("\n=== Noctua 的巢穴统计 ===")
        print(f"   [书] 已处理论文: {stats.get('total_papers', 0)} 篇")
        print(f"   [笔记] 已生成笔记: {stats.get('total_notes', 0)} 份")
        print(f"   [数据库] 数据库文档: {stats.get('database', {}).get('total_documents', 0)} 个")
        print(f"   [完成] 本次完成任务: {self.tasks_completed} 个")
        print(f"   [月亮] 当前状态: {'困倦中...' if self.is_daytime() else '精神满满!'}")
    
    def wrap_task(self, task_name: str, task_func: Callable, *args, **kwargs):
        """
        包装任务执行，添加个性化反馈
        
        Args:
            task_name: 任务名称
            task_func: 任务函数
            *args, **kwargs: 任务函数参数
        
        Returns:
            任务执行结果
        """
        if not self.enabled:
            return task_func(*args, **kwargs)
        
        print(f"\n[Noctua] 开始{task_name}...")
        self.print_reaction()
        
        try:
            result = task_func(*args, **kwargs)
            print(f"[Noctua] {self.get_completion_message()}")
            return result
        except Exception as e:
            self.print_error("general", str(e))
            raise


class NoctuaProgressBar:
    """
    咕咕咕进度条上下文管理器
    
    用法：
        with NoctuaProgressBar(noctua, "处理中") as bar:
            for i in range(100):
                bar.update(i / 100)
                time.sleep(0.1)
    """
    
    def __init__(self, noctua: NoctuaPersonality, message: str = ""):
        self.noctua = noctua
        self.message = message
        self.current_progress = 0.0
    
    def __enter__(self):
        if self.noctua.enabled:
            print(f"[Noctua] {self.noctua.get_waiting_message()}")
        else:
            print(self.message or "处理中...")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.noctua.print_progress(1.0, self.message)
        else:
            self.noctua.print_error("general", str(exc_val))
        return False
    
    def update(self, progress: float):
        """更新进度"""
        self.current_progress = progress
        self.noctua.print_progress(progress, self.message)


def create_noctua(enabled: bool = True) -> NoctuaPersonality:
    """
    创建 Noctua 个性化实例的便捷函数
    
    Args:
        enabled: 是否启用个性化
        
    Returns:
        NoctuaPersonality 实例
    """
    return NoctuaPersonality(enabled=enabled)
