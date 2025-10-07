from src.routine_bot.models import EventData

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
    @staticmethod
    def prompt_for_event_name() -> str:
        return "🎯 請輸入欲新增的事件名稱（限 2 至 20 字元）"

    @staticmethod
    def prompt_for_start_date(chat_payload: dict[str, str]) -> str:
        return "\n".join(
            (
                f"🎯 新事件［{chat_payload['event_name']}］",
                "",
                "➡️ 請輸入事件起始日期",
                "",
                DATE_EXAMPLE,
            )
        )

    @staticmethod
    def prompt_for_reminder(chat_payload: dict[str, str]) -> str:
        return "\n".join(
            (
                f"🎯 新事件［{chat_payload['event_name']}］",
                "",
                f"🗓 起始日期：{chat_payload['start_date'][:10]}",
                "",
                "➡️ 請輸入是否設定提醒（Y / N）",
            )
        )

    @staticmethod
    def prompt_for_reminder_cycle(chat_payload: dict[str, str]) -> str:
        return "\n".join(
            (
                f"🎯 新事件［{chat_payload['event_name']}］",
                "",
                f"🗓 起始日期：{chat_payload['start_date'][:10]}",
                "",
                "➡️ 請輸入提醒週期",
                "",
                REMINDER_CYCLE_EXAMPLE,
            )
        )

    @staticmethod
    def completion_no_reminder(chat_payload: dict[str, str]):
        return "\n".join(
            (
                f"🎯 新事件［{chat_payload['event_name']}］",
                "",
                f"🗓 起始日期：{chat_payload['start_date'][:10]}",
                "",
                "🔕 提醒設定：關閉",
                "",
                "✅ 新增完成！",
            )
        )

    @staticmethod
    def completion_with_reminder(chat_payload: dict[str, str]):
        return "\n".join(
            (
                f"🎯 新事件［{chat_payload['event_name']}］",
                "",
                f"🗓 起始日期：{chat_payload['start_date'][:10]}",
                "",
                f"⏰ 提醒週期：{chat_payload['reminder_cycle']}",
                "",
                "✅ 新增完成！",
            )
        )


class FindEventMsg:
    @staticmethod
    def prompt_for_event_name() -> str:
        return "🎯 請輸入欲查詢的事件名稱"

    @staticmethod
    def show_event_info(event_data: EventData) -> str:
        lines = [
            f"🎯 事件名稱：{event_data.event_name}",
            "",
            f"🗓 最近完成時間：{event_data.last_done_at.strftime('%Y-%m-%d')}",
            "",
        ]
        if event_data.reminder:
            lines.extend(
                [
                    f"⏰ 提醒週期：{event_data.reminder_cycle}",
                    "",
                    f"🔔 下次提醒時間：{event_data.next_reminder.strftime('%Y-%m-%d')}",
                ]
            )
        else:
            lines.append("🔕 提醒設定：關閉")
        return "\n".join(lines)


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
    def event_name_not_found(event_name: str) -> str:
        return f"找不到叫做［{event_name}］的事件😱 請再試一次😌"

    @staticmethod
    def event_name_too_long() -> str:
        return "事件名稱不可以超過 20 字元🤣 請再試一次😌"

    @staticmethod
    def event_name_too_short() -> str:
        return "事件名稱不可以少於 2 字元🤣 請再試一次😌"


class GreetingMsg:
    @staticmethod
    def random() -> str:
        pass


class AbortMsg:
    @staticmethod
    def no_ongoing_chat() -> str:
        return "沒有進行中的操作可以取消🤣"

    @staticmethod
    def ongoing_chat_aborted() -> str:
        return "已中止目前的操作🙏\n請重新輸入新的指令😉"
