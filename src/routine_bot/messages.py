from typing import Any, Optional

DATE_EXAMPLE = "\n".join(
    (
        "🌟 支援以下格式：",
        "- 今天",
        "- 明天",
        "- 昨天",
        "- 0827 （4 碼日期）",
        "- 20250827 （8 碼日期）",
        "",
        "⚠️ 請直接輸入上述其中一種格式",
    )
)

CYCLE_PERIOD_EXAMPLE = "\n".join(
    (
        "🌟 支援以下格式（數字 + 單位）：",
        "- 3 day",
        "- 2 week",
        "- 1 month",
        "",
        "⚠️ 單位僅支援：day, week, month",
    )
)


class NewEventMsg:
    def __init__(self, chat_payload: Optional[dict[str, Any]] = None) -> None:
        self.chat_payload = chat_payload

    def prompt_for_event_name(self) -> str:
        return "🎯 請輸入欲新增的事件名稱（限 20 字元內）"

    def prompt_for_start_date(self) -> str:
        return "\n".join(
            (
                f"🎯 新事件［{self.chat_payload['event_name']}］",
                "",
                "➡️ 請輸入事件起始日期",
                "",
                DATE_EXAMPLE,
            )
        )

    def prompt_for_reminder(self) -> str:
        return "\n".join(
            (
                f"🎯 新事件［{self.chat_payload['event_name']}］",
                "",
                f"🗓 起始日期：{self.chat_payload['start_date'][:10]}",
                "",
                "➡️ 請輸入是否設定提醒（Y / N）",
            )
        )

    def prompt_for_cycle_period(self) -> str:
        return "\n".join(
            (
                f"🎯 新事件［{self.chat_payload['event_name']}］",
                "",
                f"🗓 起始日期：{self.chat_payload['start_date'][:10]}",
                "",
                "➡️ 請輸入提醒週期",
                "",
                CYCLE_PERIOD_EXAMPLE,
            )
        )

    def completion_no_reminder(self):
        return "\n".join(
            (
                f"🎯 新事件［{self.chat_payload['event_name']}］",
                "",
                f"🗓 起始日期：{self.chat_payload['start_date'][:10]}",
                "",
                "⏰ 提醒設定：關閉",
                "",
                "✅ 新增完成！",
            )
        )

    def completion_with_reminder(self):
        return "\n".join(
            (
                f"🎯 新事件［{self.chat_payload['event_name']}］",
                "",
                f"🗓 起始日期：{self.chat_payload['start_date'][:10]}",
                "",
                f"⏰ 提醒設定：{self.chat_payload['cycle_period']}",
                "",
                "✅ 新增完成！",
            )
        )


class ErrorMsg:
    @staticmethod
    def unrecognized_command() -> str:
        return "指令無法辨識🤣 請再試一次😌"

    @staticmethod
    def unrecognized_date() -> str:
        return "\n".join(("無法辨識輸入的日期😱", "請再試一次😌", "", DATE_EXAMPLE))

    @staticmethod
    def unrecognized_cycle_period() -> str:
        pass

    @staticmethod
    def unrecognized_reminder_input() -> str:
        return "\n".join(("無校的輸入😱 請再試一次😌", "", "➡️ 請輸入是否設定提醒（Y / N）"))

    @staticmethod
    def event_name_duplicated(event_name: str) -> str:
        return f"已有叫做［{event_name}］的事件🤣 請換個名稱再試一次😌"

    @staticmethod
    def event_name_too_long() -> str:
        return "事件名稱不可以超過 20 字元🤣 請再試一次😌"


# class ErrorMsg:
#     @staticmethod
#     def event_name_duplicated(event_name: str) -> str:
#         return f"已有叫做［{event_name}］的事件🤣 請換個名稱再試一次😌"

#     @staticmethod
#     def event_not_found(event_name: str) -> str:
#         return f"沒有找到叫做［{event_name}］的事件😱 請再試一次😌"

#     @staticmethod
#     def invalid_event_name(**kwargs) -> str:
#         if kwargs["too_long"]:
#             return "事件名稱不可以超過20字🤣 請再試一次😌"
#         elif kwargs["invalid_char"]:
#             return f"事件名稱不能有 {kwargs['invalid_char']} 請再試一次😌"

#     @staticmethod
#     def invalid_start_date() -> str:
#         return textwrap.dedent(f"""
#             無法辨識輸入的日期😱 請再試一次😌

#             {DATE_EXAMPLE}
#             """)

#     @staticmethod
#     def invalid_reminder_confirmation() -> str:
#         return textwrap.dedent("""
#             無法辨識輸入的回覆😱 請再試一次😌

#             請輸入是否設定提醒（Y / N）
#             """)

#     @staticmethod
#     def invalid_cycle_period() -> str:
#         return textwrap.dedent(f"""
#             無法辨識輸入的循環週期😱 請再試一次😌

#             {CYCLE_PERIOD_EXAMPLE}
#             """)

#     @staticmethod
#     def unrecognized_command() -> str:
#         return "指令無法辨識🤣 請再試一次😌"

#     @staticmethod
#     def unrecognized_message() -> str:
#         return "訊息無法辨識🤣 請再試一次😌"
