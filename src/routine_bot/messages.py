from typing import Any

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

REMINDER_CYCLE_EXAMPLE = "\n".join(
    (
        "🌟 支援以下格式：",
        "- 3 day",
        "- 2 week",
        "- 1 month",
        "",
        "⚠️ 請直接輸入上述其中一種格式",
    )
)


class NewEventMsg:
    def __init__(self, chat_payload: dict[str, Any] | None = None) -> None:
        self.chat_payload = chat_payload

    def prompt_for_event_name(self) -> str:
        return "🎯 請輸入欲新增的事件名稱（限 2 至 20 字元）"

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

    def prompt_for_reminder_cycle(self) -> str:
        return "\n".join(
            (
                f"🎯 新事件［{self.chat_payload['event_name']}］",
                "",
                f"🗓 起始日期：{self.chat_payload['start_date'][:10]}",
                "",
                "➡️ 請輸入提醒週期",
                "",
                REMINDER_CYCLE_EXAMPLE,
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
                f"⏰ 提醒週期：{self.chat_payload['reminder_cycle']}",
                "",
                "✅ 新增完成！",
            )
        )


class ErrorMsg:
    @staticmethod
    def unrecognized_command() -> str:
        return "指令無法辨識🤣 請再試一次😌"

    @staticmethod
    def invalid_start_date_input() -> str:
        return "\n".join(("無效的輸入😱 請再試一次😌", "", "➡️ 請輸入事件起始日期", "", DATE_EXAMPLE))

    @staticmethod
    def invalid_reminder_cycle() -> str:
        return "\n".join(("無效的輸入😱 請再試一次😌", "", "➡️ 請輸入提醒週期", "", REMINDER_CYCLE_EXAMPLE))

    @staticmethod
    def invalid_reminder_input() -> str:
        return "\n".join(("無效的輸入😱 請再試一次😌", "", "➡️ 請輸入是否設定提醒（Y / N）"))

    @staticmethod
    def event_name_duplicated(event_name: str) -> str:
        return f"已有叫做［{event_name}］的事件🤣 請換個名稱再試一次😌"

    @staticmethod
    def event_name_too_long() -> str:
        return "事件名稱不可以超過 20 字元🤣 請再試一次😌"

    @staticmethod
    def event_name_too_short() -> str:
        return "事件名稱不可以少於 2 字元🤣 請再試一次😌"

    @staticmethod
    def invalid_char_for_event_name(char: str) -> str:
        pass


class GreetingMsg:
    @staticmethod
    def random() -> str:
        pass
