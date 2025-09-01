import textwrap

from linebot.v3.messaging.models.get_webhook_endpoint_response import re

STARTING_DATE_EXAMPLE = """
    ➡️ 支援以下格式：
    - 今天
    - 昨天
    - 明天
    - 0827 （4 碼日期，MMDD）
    - 20250827 （8 碼日期，YYYYMMDD）

    ⚠️ 請直接輸入上述其中一種格式
"""

CYCLE_PERIOD_EXAMPLE = """
    ➡️ 支援格式（數字 + 單位）：
    - 3 day   （每 3 天
    - 2 week  （每 2 週
    - 1 month （每 1 個月

    ⚠️ 單位僅支援：day, week, month
"""


class NewEventMsg:
    @staticmethod
    def prompt_for_starting_date(event_name: str) -> str:
        return textwrap.dedent(f"""
            🎯 新事件［{event_name}］

            ⏰ 請輸入事件開始日期

            {STARTING_DATE_EXAMPLE}
            """)

    @staticmethod
    def prompt_for_reminder(event_name: str) -> str:
        return textwrap.dedent(f"""
            🎯 新事件［{event_name}］

            開始日期設定完成 ✅

            請輸入是否設定提醒（Y / N）
            """)

    @staticmethod
    def prompt_for_cycle_period(event_name: str) -> str:
        return textwrap.dedent(f"""
            🎯 新事件［{event_name}］

            開啟提醒 ✅
            ⏰ 請輸入循環週期

            {CYCLE_PERIOD_EXAMPLE}
            """)

    @staticmethod
    def completed(event_name: str) -> str:
        return textwrap.dedent(f"""
            🎯 新事件［{event_name}］

            新增完成 ✅
            """)


class UpdateEventMsg:
    @staticmethod
    def prompt_for_last_done_date(event_name: str) -> str:
        return textwrap.dedent(f"""
            🎯 欲更新事件［{event_name}］

            ⏰ 請輸入新的完成時間

            {STARTING_DATE_EXAMPLE}
            """)


class EditEventMsg:
    @staticmethod
    def prompt_for_field_to_edit(event_name: str) -> str:
        return textwrap.dedent(f"""
            🎯 欲修改事件［{event_name}］

            ✏ 請輸入想要修改的設定（名稱 / 提醒）
            """)


class DeleteEventMsg:
    @staticmethod
    def prompt_for_delete_comfirmation(event_name: str) -> str:
        return textwrap.dedent(f"""
            🎯 欲刪除事件［{event_name}］

            ⚠️ 請確認是否要刪除（Y / N）
            """)


class ErrorMsg:
    @staticmethod
    def event_name_duplicated(event_name: str) -> str:
        return f"已有叫做［{event_name}］的事件🤣 請換個名稱再試一次😌"

    @staticmethod
    def event_not_found(event_name: str) -> str:
        return f"沒有找到叫做［{event_name}］的事件😱 請再試一次😌"

    @staticmethod
    def invalid_event_name(**kwargs) -> str:
        if kwargs["too_long"]:
            return "事件名稱不可以超過20字🤣 請再試一次😌"
        elif kwargs["invalid_char"]:
            return f"事件名稱不能有 {kwargs['invalid_char']} 請再試一次😌"

    @staticmethod
    def invalid_starting_date() -> str:
        return textwrap.dedent(f"""
            無法辨識輸入的日期😱 請再試一次😌

            {STARTING_DATE_EXAMPLE}
            """)

    @staticmethod
    def invalid_reminder_confirmation() -> str:
        return textwrap.dedent("""
            無法辨識輸入的回覆😱 請再試一次😌

            請輸入是否設定提醒（Y / N）
            """)

    @staticmethod
    def invalid_cycle_period() -> str:
        return textwrap.dedent(f"""
            無法辨識輸入的循環週期😱 請再試一次😌

            {CYCLE_PERIOD_EXAMPLE}
            """)

    @staticmethod
    def unrecognized_command() -> str:
        return "指令無法辨識🤣 請再試一次😌"

    @staticmethod
    def unrecognized_message() -> str:
        return "訊息無法辨識🤣 請再試一次😌"
