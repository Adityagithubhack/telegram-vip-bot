from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.services.onboarding import OnboardingProgress


def build_dashboard_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 GET VIP ACCESS",
                    callback_data="menu:contact_verification",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💎 VIP OPTIONS",
                    callback_data="menu:vip_options",
                ),
                InlineKeyboardButton(
                    text="📊 COMPARE VIP",
                    callback_data="menu:compare",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🎯 DAILY PICKS",
                    callback_data="menu:daily_picks",
                ),
                InlineKeyboardButton(
                    text="📖 HOW IT WORKS",
                    callback_data="menu:how_it_works",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💬 VIP SUPPORT",
                    callback_data="menu:support",
                ),
                InlineKeyboardButton(
                    text="🏠 HOME",
                    callback_data="menu:home",
                ),
            ],
        ]
    )


def _step_icon(done: bool) -> str:
    return "✅" if done else "⬜"


async def send_vip_dashboard(
    message: Message,
    *,
    first_name: str,
    progress: OnboardingProgress,
    selected_category: str = "Not selected yet",
) -> None:
    state = progress.state

    await message.answer(
        f"👋 <b>{first_name}</b>\n\n"
        "<b>VIP TIER:</b> ⬜ GUEST\n"
        f"<b>📊 SELECTED CATEGORY:</b> {selected_category}\n"
        f"<b>📈 PROGRESS:</b> {progress.progress_percent}% "
        f"({progress.completed_steps}/{progress.total_steps})\n\n"
        "<b>🏆 VIP JOURNEY</b>\n\n"
        f"{_step_icon(state.language_selected_at is not None)} Language Selected\n"
        f"{_step_icon(state.category_selected_at is not None)} VIP Category Selected\n"
        f"{_step_icon(state.registration_completed_at is not None)} Registration\n"
        f"{_step_icon(state.contact_verified_at is not None)} Contact Verification\n"
        f"{_step_icon(state.vip_access_granted_at is not None)} VIP Access\n\n"
        f"➡️ <b>NEXT STEP:</b> {progress.next_step}",
        reply_markup=build_dashboard_keyboard(),
    )
