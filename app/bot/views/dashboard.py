from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.services.onboarding import OnboardingProgress
from app.i18n.translations import t


def build_dashboard_keyboard(
    progress: OnboardingProgress,
    locale: str = "en",
) -> InlineKeyboardMarkup:
    state = progress.state

    if state.registration_completed_at is None:
        primary_text = f"📝 {t(locale, 'complete_registration')}"
        primary_callback = "menu:registration"
    elif state.contact_verified_at is None:
        primary_text = f"📞 {t(locale, 'verify_contact')}"
        primary_callback = "menu:contact_verification"
    elif state.vip_access_granted_at is None:
        primary_text = f"⏳ {t(locale, 'awaiting_vip_approval')}"
        primary_callback = "menu:vip_pending"
    else:
        primary_text = f"👑 {t(locale, 'vip_active')}"
        primary_callback = "menu:vip_active"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=primary_text,
                    callback_data=primary_callback,
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"💎 {t(locale, 'vip_options')}",
                    callback_data="menu:vip_options",
                ),
                InlineKeyboardButton(
                    text=f"📊 {t(locale, 'compare_vip')}",
                    callback_data="menu:compare",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"🎯 {t(locale, 'daily_picks')}",
                    callback_data="menu:daily_picks",
                ),
                InlineKeyboardButton(
                    text=f"📖 {t(locale, 'how_it_works')}",
                    callback_data="menu:how_it_works",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"💬 {t(locale, 'vip_support')}",
                    callback_data="menu:support",
                ),
                InlineKeyboardButton(
                    text=f"🏠 {t(locale, 'home')}",
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
    locale: str = "en",
) -> None:
    state = progress.state

    await message.answer(
        f"👋 <b>{first_name}</b>\n\n"
        f"<b>VIP TIER:</b> ⬜ {t(locale, 'guest')}\n"
        f"<b>📊 {t(locale, 'selected_category')}:</b> {selected_category}\n"
        f"<b>📈 {t(locale, 'progress')}:</b> {progress.progress_percent}% "
        f"({progress.completed_steps}/{progress.total_steps})\n\n"
        f"<b>🏆 {t(locale, 'vip_journey')}</b>\n\n"
        f"{_step_icon(state.language_selected_at is not None)} {t(locale, 'language_selected')}\n"
        f"{_step_icon(state.category_selected_at is not None)} {t(locale, 'vip_category_selected')}\n"
        f"{_step_icon(state.registration_completed_at is not None)} {t(locale, 'registration')}\n"
        f"{_step_icon(state.contact_verified_at is not None)} {t(locale, 'contact_verification')}\n"
        f"{_step_icon(state.vip_access_granted_at is not None)} {t(locale, 'vip_access')}\n\n"
        f"➡️ <b>{t(locale, 'next_step')}:</b> {progress.next_step}",
        reply_markup=build_dashboard_keyboard(progress, locale),
    )
