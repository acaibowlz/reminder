from datetime import datetime

from linebot.v3.messaging import (
    ButtonsTemplate,
    DatetimePickerAction,
    FlexBox,
    FlexBubble,
    FlexMessage,
    FlexSeparator,
    FlexText,
    MessageAction,
    TemplateMessage,
    TextMessage,
)

from src.routine_bot.constants import FREE_PLAN_MAX_EVENTS
from src.routine_bot.models import EventData


def flex_text_bold_line(text: str) -> FlexText:
    return FlexText(text=text, size="md", weight="bold")


def flex_text_normal_line(text: str) -> FlexText:
    return FlexText(text=text, size="md", color="#666666")


def flex_bubble_template(title: str, lines: list[str]) -> FlexBubble:
    contents = [flex_text_bold_line(title), FlexSeparator()]
    for line in lines:
        contents.append(flex_text_normal_line(line))

    bubble = FlexBubble(
        body=FlexBox(
            layout="vertical",
            paddingTop="lg",
            paddingBottom="lg",
            paddingStart="xl",
            paddingEnd="xl",
            spacing="lg",
            contents=contents,
        ),
    )
    return bubble


class NewEventMsg:
    @staticmethod
    def prompt_for_event_name() -> TextMessage:
        return TextMessage(text="🎯 請輸入欲新增的事件名稱（限 2 至 20 字元）")

    @staticmethod
    def prompt_for_start_date(chat_payload: dict[str, str]) -> TemplateMessage:
        template = ButtonsTemplate(
            title=f"🎯 新事件［{chat_payload['event_name']}］",
            text="\n⬇️ 請選擇事件起始日期",
            actions=[DatetimePickerAction(label="選擇日期", data=chat_payload["chat_id"], mode="date")],
        )
        msg = TemplateMessage(
            altText=f"🎯 新事件［{chat_payload['event_name']}］➡️ 請選擇事件起始日期", template=template
        )
        return msg

    @staticmethod
    def prompt_for_toggle_reminder(chat_payload: dict[str, str]) -> TemplateMessage:
        template = ButtonsTemplate(
            title=f"🎯 新事件［{chat_payload['event_name']}］",
            text=f"\n🗓 起始日期：{chat_payload['start_date'][:10]}\n\n⬇️ 請選擇是否設定提醒",
            actions=[
                MessageAction(label="是", text="設定提醒"),
                MessageAction(label="否", text="不設定提醒"),
            ],
        )
        msg = TemplateMessage(
            altText=f"🎯 新事件［{chat_payload['event_name']}］➡️ 請選擇是否設定提醒", template=template
        )
        return msg

    @staticmethod
    def prompt_for_reminder_cycle(chat_payload: dict[str, str]) -> TemplateMessage:
        template = ButtonsTemplate(
            title=f"🎯 新事件［{chat_payload['event_name']}］",
            text=f"\n🗓 起始日期：{chat_payload['start_date'][:10]}\n\n⬇️ 請選擇提醒週期",
            actions=[
                MessageAction(label="1 天", text="1 day"),
                MessageAction(label="1 週", text="1 week"),
                MessageAction(label="1 個月", text="1 month"),
                MessageAction(label="輸入自訂週期（點我看範例）", text="example"),
            ],
        )
        msg = TemplateMessage(altText=f"🎯 新事件［{chat_payload['event_name']}］➡️ 請選擇提醒週期", template=template)
        return msg

    @staticmethod
    def reminder_cycle_example() -> FlexMessage:
        bubble = flex_bubble_template(
            title="🌟 自訂週期輸入格式",
            lines=["支援以下格式：", "📌 3 day", "📌 2 week", "📌 1 month", "⚠️ 請直接輸入上述其中一種格式"],
        )
        return FlexMessage(altText="➡️ 輸入自訂週期", contents=bubble)

    @staticmethod
    def event_created_no_reminder(chat_payload: dict[str, str]) -> FlexMessage:
        bubble = flex_bubble_template(
            title="✅ 新增完成！",
            lines=[
                f"🎯 新事件［{chat_payload['event_name']}］",
                f"🗓 起始日期：{chat_payload['start_date'][:10]}",
                "🔕 提醒設定：關閉",
            ],
        )
        return FlexMessage(altText=f"🎯 新事件［{chat_payload['event_name']}］✅ 新增完成！", contents=bubble)

    @staticmethod
    def event_created_with_reminder(chat_payload: dict[str, str]) -> FlexMessage:
        bubble = flex_bubble_template(
            title="✅ 新增完成！",
            lines=[
                f"🎯 新事件［{chat_payload['event_name']}］",
                f"🗓 起始日期：{chat_payload['start_date'][:10]}",
                f"⏰ 提醒週期：{chat_payload['reminder_cycle']}",
            ],
        )
        return FlexMessage(altText=f"🎯 新事件［{chat_payload['event_name']}］✅ 新增完成！", contents=bubble)

    @staticmethod
    def invalid_input_for_start_date(chat_payload: dict[str, str]) -> TemplateMessage:
        template = ButtonsTemplate(
            title=f"🎯 新事件［{chat_payload['event_name']}］",
            text="\n⚠️ 無效的輸入，請再試一次\n\n⬇️ 請透過下方按鈕選擇事件起始日期",
            actions=[DatetimePickerAction(label="選擇日期", data=chat_payload["chat_id"], mode="date")],
        )
        msg = TemplateMessage(
            altText=f"🎯 新事件［{chat_payload['event_name']}］⚠️ 輸入無效，請再次選擇事件起始日期", template=template
        )
        return msg

    @staticmethod
    def invalid_input_for_toggle_reminder(chat_payload: dict[str, str]) -> TemplateMessage:
        template = ButtonsTemplate(
            title=f"🎯 新事件［{chat_payload['event_name']}］",
            text=f"\n🗓 起始日期：{chat_payload['start_date'][:10]}\n\n⚠️ 無效的輸入，請再試一次\n\n⬇️ 請透過下方按鈕是否設定提醒",
            actions=[
                MessageAction(label="是", text="設定提醒"),
                MessageAction(label="否", text="不設定提醒"),
            ],
        )
        msg = TemplateMessage(
            altText=f"🎯 新事件［{chat_payload['event_name']}］ ⚠️ 輸入無效，請再次選擇是否設定提醒", template=template
        )
        return msg

    @staticmethod
    def invalid_input_for_reminder_cycle(chat_payload: dict[str, str]) -> TemplateMessage:
        template = ButtonsTemplate(
            title=f"🎯 新事件［{chat_payload['event_name']}］",
            text=f"\n🗓 起始日期：{chat_payload['start_date'][:10]}\n\n⚠️ 無效的輸入，請再試一次\n\n⬇️ 請選擇提醒週期",
            actions=[
                MessageAction(label="1 天", text="1 day"),
                MessageAction(label="1 週", text="1 week"),
                MessageAction(label="1 個月", text="1 month"),
                MessageAction(label="輸入自訂週期（點我看範例）", text="example"),
            ],
        )
        msg = TemplateMessage(
            altText=f"🎯 新事件［{chat_payload['event_name']}］⚠️ 輸入無效，請再次選擇提醒週期", template=template
        )
        return msg


class FindEventMsg:
    @staticmethod
    def prompt_for_event_name() -> TextMessage:
        return TextMessage(text="🎯 請輸入欲查詢的事件名稱")

    @staticmethod
    def format_event_summary(event: EventData, recent_update_times: list[datetime]) -> FlexMessage:
        contents = [flex_text_bold_line(f"🎯［{event.event_name}］的事件摘要"), FlexSeparator()]
        # the use of contents.extend will unfold the list to be extended
        # which does not look good
        if event.reminder:
            contents.append(flex_text_normal_line(f"⏰ 提醒週期：{event.reminder_cycle}"))
            contents.append(flex_text_normal_line(f"🔔 下次提醒：{event.next_reminder.strftime('%Y-%m-%d')}"))

        else:
            contents.append(flex_text_normal_line("🔕 提醒設定：關閉"))
        contents.append(FlexSeparator())
        contents.append(flex_text_bold_line("🗓 最近完成日期"))
        for t in recent_update_times:
            contents.append(flex_text_normal_line(f"✅ {t.strftime('%Y-%m-%d')}"))

        bubble = FlexBubble(
            body=FlexBox(
                layout="vertical",
                paddingTop="lg",
                paddingBottom="lg",
                paddingStart="xl",
                paddingEnd="xl",
                spacing="lg",
                contents=contents,
            ),
        )
        msg = FlexMessage(altText=f"🎯［{event.event_name}］的事件摘要", contents=bubble)
        return msg


class ErrorMsg:
    @staticmethod
    def unrecognized_command() -> TextMessage:
        return TextMessage(text="指令無法辨識🤣 請再試一次😌")

    @staticmethod
    def event_name_duplicated(event_name: str) -> TextMessage:
        return TextMessage(text=f"已有叫做［{event_name}］的事件🤣 請換個名稱再試一次😌")

    @staticmethod
    def event_name_not_found(event_name: str) -> TextMessage:
        return TextMessage(text=f"找不到叫做［{event_name}］的事件😱 請再試一次😌")

    @staticmethod
    def event_name_too_long() -> TextMessage:
        return TextMessage(text="事件名稱不可以超過 20 字元🤣 請再試一次😌")

    @staticmethod
    def event_name_too_short() -> TextMessage:
        return TextMessage(text="事件名稱不可以少於 2 字元🤣 請再試一次😌")

    @staticmethod
    def max_events_reached() -> FlexMessage:
        bubble = flex_bubble_template(
            title="⚠️ 無法新增事件",
            lines=[
                f"🔒 你已超過免費方案的 {FREE_PLAN_MAX_EVENTS} 個事件上限",
                "💡 你可以選擇：",
                "🗑️ 刪除超量事件，繼續使用免費方案",
                "🚀 升級至 premium，享受新增無上限",
            ],
        )
        msg = FlexMessage(altText="⚠️ 無法新增事件，請刪除超量事件或升級至 premium", contents=bubble)
        return msg

    @staticmethod
    def reminder_disabled() -> FlexMessage:
        bubble = flex_bubble_template(
            title="🔕 提醒功能已停用",
            lines=[
                f"🔒 你已超過免費方案的 {FREE_PLAN_MAX_EVENTS} 個事件上限",
                "💡 你可以選擇：",
                "🗑️ 刪除超量事件，恢復提醒功能",
                "🚀 升級至 premium，享受提醒功能無上限",
            ],
        )
        msg = FlexMessage(altText="🔕 提醒功能已停用，請刪除超量事件或升級至 premium", contents=bubble)
        return msg


class GreetingMsg:
    @staticmethod
    def random() -> TextMessage:
        return TextMessage(text="hello!")


class AbortMsg:
    @staticmethod
    def no_ongoing_chat() -> str:
        return TextMessage(text="沒有進行中的操作可以取消🤣")

    @staticmethod
    def ongoing_chat_aborted() -> str:
        return TextMessage(text="已中止目前的操作🙏\n請重新輸入新的指令😉")
