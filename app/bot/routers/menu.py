from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.bot.views.dashboard import send_vip_dashboard
from app.bot.views.language import send_language_menu
from app.bot.views.membership import send_membership_gate
from app.bot.views.vip_category import (
    send_vip_categories,
    send_vip_category_detail,
)
from app.i18n.translations import t
from app.services.content_screen_settings import ContentScreenSettingsService
from app.services.daily_pick import DailyPickService
from app.services.membership import MembershipService
from app.services.referral import ReferralService
from app.services.onboarding import OnboardingProgress, OnboardingService
from app.services.user import UserService
from app.services.vip_category import VipCategoryService
from app.services.vip_menu_settings import VipMenuSettingsService

router = Router(name="menu")


def build_main_menu_keyboard(
    locale: str = "en",
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🚀 {t(locale, 'explore_vip_options')}",
                    callback_data="menu:vip_options",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"💎 {t(locale, 'vip_options')}",
                    callback_data="menu:vip_options",
                ),
                InlineKeyboardButton(
                    text=f"👑 {t(locale, 'my_vip_dashboard')}",
                    callback_data="menu:my_vip",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"🎯 {t(locale, 'winning_tips')}",
                    callback_data="menu:winning_tips",
                ),
                InlineKeyboardButton(
                    text=f"🔥 {t(locale, 'todays_insights')}",
                    callback_data="menu:today_insights",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"🏆 {t(locale, 'live_stats')}",
                    callback_data="menu:live_stats",
                ),
                InlineKeyboardButton(
                    text=f"🆚 {t(locale, 'free_vs_vip')}",
                    callback_data="menu:free_vs_vip",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"🔴 {t(locale, 'live_bets')}",
                    callback_data="menu:live_bets",
                ),
                InlineKeyboardButton(
                    text=f"🎯 {t(locale, 'pre_match_bets')}",
                    callback_data="menu:pre_match_bets",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"🎁 {t(locale, 'refer_and_earn')}",
                    callback_data="menu:referral",
                ),
                InlineKeyboardButton(
                    text=f"📖 {t(locale, 'how_it_works')}",
                    callback_data="menu:how_it_works",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"📊 {t(locale, 'compare_vip')}",
                    callback_data="menu:compare",
                ),
                InlineKeyboardButton(
                    text=f"🎯 {t(locale, 'daily_picks')}",
                    callback_data="menu:daily_picks",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"🌐 {t(locale, 'language')}",
                    callback_data="menu:language",
                ),
                InlineKeyboardButton(
                    text=f"🔔 {t(locale, 'notifications')}",
                    callback_data="menu:notifications",
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


async def send_main_menu(
    message: Message,
    *,
    progress: OnboardingProgress,
    locale: str = "en",
) -> None:
    state = progress.state

    language_mark = "✅" if state.language_selected_at else "⬜"
    category_mark = "✅" if state.category_selected_at else "⬜"
    registration_mark = "✅" if state.registration_completed_at else "⬜"
    contact_mark = "✅" if state.contact_verified_at else "⬜"
    access_mark = "✅" if state.vip_access_granted_at else "⬜"

    await message.answer(
        f"🏆 <b>{t(locale, 'main_menu_title')}</b>\n\n"
        f"{t(locale, 'welcome_admin')}\n\n"
        f"💎 {t(locale, 'premium_vip_options')}\n"
        f"📊 {t(locale, 'match_intelligence')}\n"
        f"🔥 {t(locale, 'live_match_updates')}\n\n"
        f"<b>🏆 {t(locale, 'vip_journey')}</b>\n\n"
        f"{language_mark} {t(locale, 'language_selected')}\n"
        f"{category_mark} {t(locale, 'vip_category_selected')}\n"
        f"{registration_mark} {t(locale, 'registration')}\n"
        f"{contact_mark} {t(locale, 'contact_verification')}\n"
        f"{access_mark} {t(locale, 'vip_access')}\n\n"
        f"📈 {t(locale, 'progress')}: "
        f"<b>{progress.progress_percent}%</b>\n\n"
        f"{t(locale, 'choose_option')}",
        reply_markup=build_main_menu_keyboard(locale),
    )


def _category_label(code: str) -> str:
    labels = {
        "standard": "⭐ STANDARD VIP",
        "premium": "💎 PREMIUM VIP",
        "elite": "👑 ELITE VIP",
    }
    return labels.get(
        code,
        code.replace("_", " ").upper(),
    )


@router.message(Command("menu"))
async def handle_menu(
    message: Message,
    user_service: UserService,
    membership_service: MembershipService,
    onboarding_service: OnboardingService,
) -> None:
    if message.from_user is None:
        return

    user = await user_service.upsert_from_telegram(
        message.from_user
    )

    decision = await membership_service.check_required_channels(
        user=user,
    )

    if not decision.channels:
        await message.answer(
            "⚠️ No required channels are configured."
        )
        return

    if not decision.all_required_joined:
        await send_membership_gate(
            message,
            decision,
        )
        return

    progress = await onboarding_service.get_progress(
        user_id=user.id,
    )

    await send_main_menu(
        message,
        progress=progress,
        locale=user.locale,
    )



@router.message(Command("myvip"))
async def handle_my_vip_command(
    message: Message,
    user_service: UserService,
    onboarding_service: OnboardingService,
    vip_category_service: VipCategoryService,
) -> None:
    if message.from_user is None:
        return

    user = await user_service.upsert_from_telegram(
        message.from_user
    )

    progress = await onboarding_service.get_progress(
        user_id=user.id,
    )

    selected_category = "Not selected yet"

    if progress.state.vip_category_id is not None:
        category = await vip_category_service.get_by_id(
            category_id=progress.state.vip_category_id,
        )

        if category is not None:
            selected_category = _category_label(category.code)

    await send_vip_dashboard(
        message,
        first_name=user.first_name or "VIP USER",
        progress=progress,
        selected_category=selected_category,
        locale=user.locale,
    )


@router.callback_query(F.data == "menu:my_vip")
async def handle_my_vip(
    callback: CallbackQuery,
    user_service: UserService,
    onboarding_service: OnboardingService,
    vip_category_service: VipCategoryService,
) -> None:
    if not isinstance(callback.message, Message):
        return

    user = await user_service.upsert_from_telegram(
        callback.from_user
    )

    progress = await onboarding_service.get_progress(
        user_id=user.id,
    )

    selected_category = "Not selected yet"

    if progress.state.vip_category_id is not None:
        category = await vip_category_service.get_by_id(
            category_id=progress.state.vip_category_id,
        )

        if category is not None:
            selected_category = _category_label(category.code)

    await callback.answer()

    await send_vip_dashboard(
        callback.message,
        first_name=user.first_name or "VIP USER",
        progress=progress,
        selected_category=selected_category,
        locale=user.locale,
    )



@router.callback_query(F.data == "menu:language")
async def handle_language_menu(
    callback: CallbackQuery,
) -> None:
    if not isinstance(callback.message, Message):
        return

    await callback.answer()
    await send_language_menu(callback.message)



@router.message(Command("language"))
async def handle_language_command(
    message: Message,
) -> None:
    await send_language_menu(message)


@router.callback_query(F.data.startswith("language:"))
async def handle_language_selection(
    callback: CallbackQuery,
    user_service: UserService,
    onboarding_service: OnboardingService,
) -> None:
    if not isinstance(callback.message, Message):
        return

    if callback.data is None:
        return

    language_code = callback.data.split(":", maxsplit=1)[1]

    allowed_languages = {
        "en": "English",
        "hi": "Hindi",
        "bn": "Bengali",
        "ne": "Nepali",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "pt": "Portuguese",
        "it": "Italian",
        "ru": "Russian",
        "ar": "Arabic",
        "tr": "Turkish",
        "id": "Indonesian",
        "ja": "Japanese",
        "ko": "Korean",
        "zh": "Chinese",
        "nl": "Dutch",
        "pl": "Polish",
        "vi": "Vietnamese",
        "th": "Thai",
        "fa": "Persian",
        "uk": "Ukrainian",
        "ms": "Malay",
        "fil": "Filipino",
    }

    language_name = allowed_languages.get(language_code)

    if language_name is None:
        await callback.answer(
            "Unsupported language",
            show_alert=True,
        )
        return

    user = await user_service.upsert_from_telegram(
        callback.from_user
    )

    await user_service.set_locale(
        user_id=user.id,
        locale=language_code,
    )

    await onboarding_service.select_language(
        user_id=user.id,
    )

    progress = await onboarding_service.get_progress(
        user_id=user.id,
    )

    await callback.answer(
        f"✅ {language_name} selected"
    )

    await send_vip_dashboard(
        callback.message,
        first_name=user.first_name or "VIP USER",
        progress=progress,
        locale=user.locale,
    )


@router.message(Command("vip"))
async def handle_vip_command(
    message: Message,
    vip_category_service: VipCategoryService,
    vip_menu_settings_service: VipMenuSettingsService,
) -> None:
    categories = await vip_category_service.list_active()
    menu_settings = await vip_menu_settings_service.get()

    await send_vip_categories(
        message,
        categories=categories,
        settings=menu_settings,
    )


@router.callback_query(F.data == "menu:vip_options")
async def handle_vip_options(
    callback: CallbackQuery,
    vip_category_service: VipCategoryService,
    vip_menu_settings_service: VipMenuSettingsService,
) -> None:
    if not isinstance(callback.message, Message):
        return

    categories = await vip_category_service.list_active()
    menu_settings = await vip_menu_settings_service.get()

    await callback.answer()

    await send_vip_categories(
        callback.message,
        categories=categories,
        settings=menu_settings,
    )


@router.callback_query(F.data.startswith("vip_category:"))
async def handle_vip_category_details(
    callback: CallbackQuery,
    vip_category_service: VipCategoryService,
) -> None:
    if not isinstance(callback.message, Message):
        return

    if callback.data is None:
        return

    raw_category_id = callback.data.split(":", maxsplit=1)[1]

    try:
        vip_category_id = int(raw_category_id)
    except ValueError:
        await callback.answer(
            "Invalid VIP category",
            show_alert=True,
        )
        return

    category = await vip_category_service.get_by_id(
        category_id=vip_category_id,
    )

    if category is None:
        await callback.answer(
            "VIP category not found",
            show_alert=True,
        )
        return

    await callback.answer()

    await send_vip_category_detail(
        callback.message,
        category=category,
    )


@router.callback_query(F.data.startswith("vip_category_select:"))
async def handle_vip_category_selection(
    callback: CallbackQuery,
    user_service: UserService,
    onboarding_service: OnboardingService,
) -> None:
    if not isinstance(callback.message, Message):
        return

    if callback.data is None:
        return

    raw_category_id = callback.data.split(":", maxsplit=1)[1]

    try:
        vip_category_id = int(raw_category_id)
    except ValueError:
        await callback.answer(
            "Invalid VIP category",
            show_alert=True,
        )
        return

    user = await user_service.upsert_from_telegram(
        callback.from_user
    )

    await onboarding_service.select_vip_category(
        user_id=user.id,
        vip_category_id=vip_category_id,
    )

    progress = await onboarding_service.get_progress(
        user_id=user.id,
    )

    await callback.answer(
        "✅ VIP category selected"
    )

    await send_vip_dashboard(
        callback.message,
        first_name=user.first_name or "VIP USER",
        progress=progress,
        locale=user.locale,
    )


@router.callback_query(F.data == "menu:registration")
async def handle_registration(
    callback: CallbackQuery,
) -> None:
    if not isinstance(callback.message, Message):
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ COMPLETE REGISTRATION",
                    callback_data="registration:complete",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ BACK TO DASHBOARD",
                    callback_data="menu:my_vip",
                )
            ],
        ]
    )

    await callback.message.answer(
        "📝 <b>VIP REGISTRATION</b>\n\n"
        "You're about to complete your registration step.\n\n"
        "After confirmation, your VIP journey progress "
        "will move to <b>60%</b>.\n\n"
        "Tap the button below to confirm.",
        reply_markup=keyboard,
    )

    await callback.answer()

@router.callback_query(F.data == "registration:complete")
async def handle_registration_complete(
    callback: CallbackQuery,
    user_service: UserService,
    onboarding_service: OnboardingService,
    vip_category_service: VipCategoryService,
) -> None:
    if not isinstance(callback.message, Message):
        return

    user = await user_service.upsert_from_telegram(
        callback.from_user
    )

    await onboarding_service.complete_registration(
        user_id=user.id,
    )

    progress = await onboarding_service.get_progress(
        user_id=user.id,
    )

    selected_category = "Not selected yet"

    if progress.state.vip_category_id is not None:
        category = await vip_category_service.get_by_id(
            category_id=progress.state.vip_category_id,
        )

        if category is not None:
            selected_category = _category_label(
                category.code
            )

    await callback.answer(
        "✅ Registration completed"
    )

    await send_vip_dashboard(
        callback.message,
        first_name=callback.from_user.first_name,
        progress=progress,
        selected_category=selected_category,
        locale=user.locale,
    )

@router.callback_query(F.data == "menu:contact_verification")
async def handle_contact_verification(
    callback: CallbackQuery,
) -> None:
    if not isinstance(callback.message, Message):
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ VERIFY CONTACT",
                    callback_data="contact:verify",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ BACK TO DASHBOARD",
                    callback_data="menu:my_vip",
                )
            ],
        ]
    )

    await callback.message.answer(
        "📞 <b>CONTACT VERIFICATION</b>\n\n"
        "Confirm your contact verification step.\n\n"
        "After verification, your VIP journey progress "
        "will move to <b>80%</b>.",
        reply_markup=keyboard,
    )

    await callback.answer()

@router.callback_query(F.data == "contact:verify")
async def handle_contact_verified(
    callback: CallbackQuery,
    user_service: UserService,
    onboarding_service: OnboardingService,
    vip_category_service: VipCategoryService,
) -> None:
    if not isinstance(callback.message, Message):
        return

    user = await user_service.upsert_from_telegram(
        callback.from_user
    )

    await onboarding_service.verify_contact(
        user_id=user.id,
    )

    progress = await onboarding_service.get_progress(
        user_id=user.id,
    )

    selected_category = "Not selected yet"

    if progress.state.vip_category_id is not None:
        category = await vip_category_service.get_by_id(
            category_id=progress.state.vip_category_id,
        )

        if category is not None:
            selected_category = _category_label(
                category.code
            )

    await callback.answer(
        "✅ Contact verified"
    )

    await send_vip_dashboard(
        callback.message,
        first_name=callback.from_user.first_name,
        progress=progress,
        selected_category=selected_category,
        locale=user.locale,
    )

@router.callback_query(F.data == "menu:vip_pending")
async def handle_vip_pending(
    callback: CallbackQuery,
) -> None:
    if not isinstance(callback.message, Message):
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👑 MY VIP DASHBOARD",
                    callback_data="menu:my_vip",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💬 VIP SUPPORT",
                    callback_data="menu:support",
                ),
                InlineKeyboardButton(
                    text="🏠 MAIN MENU",
                    callback_data="menu:home",
                ),
            ],
        ]
    )

    await callback.message.answer(
        "⏳ <b>VIP APPROVAL PENDING</b>\n\n"
        "Your registration and contact verification are complete.\n\n"
        "✅ 4 of 5 VIP journey steps completed\n"
        "👑 Final VIP access requires admin approval.\n\n"
        "You do not need to complete any additional steps right now.",
        reply_markup=keyboard,
    )

    await callback.answer()


@router.callback_query(F.data == "menu:vip_active")
async def handle_vip_active(
    callback: CallbackQuery,
) -> None:
    if not isinstance(callback.message, Message):
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👑 MY VIP DASHBOARD",
                    callback_data="menu:my_vip",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 DAILY PICKS",
                    callback_data="menu:daily_picks",
                ),
                InlineKeyboardButton(
                    text="🏠 MAIN MENU",
                    callback_data="menu:home",
                ),
            ],
        ]
    )

    await callback.message.answer(
        "👑 <b>VIP ACCESS ACTIVE</b>\n\n"
        "Your VIP access is active and your onboarding journey is complete.\n\n"
        "✅ All 5 VIP journey steps completed\n"
        "🎯 You can now access VIP features from your dashboard.",
        reply_markup=keyboard,
    )

    await callback.answer()


@router.callback_query(F.data == "menu:daily_picks")
async def handle_daily_picks(
    callback: CallbackQuery,
    user_service: UserService,
    onboarding_service: OnboardingService,
    daily_pick_service: DailyPickService,
) -> None:
    if not isinstance(callback.message, Message):
        return

    user = await user_service.upsert_from_telegram(
        callback.from_user,
    )

    progress = await onboarding_service.get_progress(
        user_id=user.id,
    )

    if progress.state.vip_access_granted_at is None:
        await callback.answer(
            "⛔ VIP access required",
            show_alert=True,
        )
        return

    picks = await daily_pick_service.list_published()

    if not picks:
        await callback.message.answer(
            "🎯 <b>DAILY PICKS</b>\n\n"
            "No VIP picks have been published yet.\n"
            "Check back soon.",
        )
        await callback.answer()
        return

    lines = [
        "🎯 <b>DAILY VIP PICKS</b>",
        "",
    ]

    for pick in picks:
        lines.append(
            f"🏟 <b>{pick.event_title}</b>\n"
            f"🏅 Sport: {pick.sport}\n"
            f"🎯 Pick: <b>{pick.selection}</b>\n"
            f"🔥 Confidence: <b>{pick.confidence}%</b>"
        )

        if pick.odds is not None:
            lines.append(f"📈 Odds: <b>{pick.odds}</b>")

        if pick.analysis:
            lines.append(f"📝 {pick.analysis}")

        lines.append("")

    await callback.message.answer(
        "\n".join(lines),
    )

    await callback.answer()


@router.message(Command("dailypicks"))
async def handle_daily_picks_command(
    message: Message,
    user_service: UserService,
    onboarding_service: OnboardingService,
    daily_pick_service: DailyPickService,
) -> None:
    if message.from_user is None:
        return

    user = await user_service.upsert_from_telegram(
        message.from_user,
    )

    progress = await onboarding_service.get_progress(
        user_id=user.id,
    )

    if progress.state.vip_access_granted_at is None:
        await message.answer(
            "⛔ VIP access required",
        )
        return

    picks = await daily_pick_service.list_published()

    if not picks:
        await message.answer(
            "🎯 <b>DAILY PICKS</b>\n\n"
            "No VIP picks have been published yet.\n"
            "Check back soon.",
        )
        return

    lines = [
        "🎯 <b>DAILY VIP PICKS</b>",
        "",
    ]

    for pick in picks:
        lines.append(
            f"🏟 <b>{pick.event_title}</b>\n"
            f"🏅 Sport: {pick.sport}\n"
            f"🎯 Pick: <b>{pick.selection}</b>\n"
            f"🔥 Confidence: <b>{pick.confidence}%</b>"
        )

        if pick.odds is not None:
            lines.append(f"📈 Odds: <b>{pick.odds}</b>")

        if pick.analysis:
            lines.append(f"📝 {pick.analysis}")

        lines.append("")

    await message.answer(
        "\n".join(lines),
    )


@router.callback_query(F.data == "menu:how_it_works")
async def handle_how_it_works(
    callback: CallbackQuery,
    content_screen_settings_service: ContentScreenSettingsService,
) -> None:
    if not isinstance(callback.message, Message):
        return

    settings = await content_screen_settings_service.get(
        "how_it_works"
    )

    heading = (
        escape(settings.heading)
        if settings and settings.heading
        else "📖 HOW IT WORKS"
    )

    body = (
        escape(settings.body)
        if settings and settings.body
        else (
            "1️⃣ Choose your VIP option.\n"
            "2️⃣ Complete registration.\n"
            "3️⃣ Follow the verification instructions.\n"
            "4️⃣ Wait for VIP access approval.\n"
            "5️⃣ Start receiving VIP content."
        )
    )

    registration_url = (
        settings.registration_url
        if settings
        else None
    )

    promo_code = (
        escape(settings.promo_code)
        if settings and settings.promo_code
        else None
    )

    support_username = (
        settings.support_username
        if settings
        else None
    )

    if support_username:
        support_username = support_username.lstrip("@")

    rows: list[list[InlineKeyboardButton]] = []

    if registration_url:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🚀 GET VIP ACCESS",
                    url=registration_url,
                )
            ]
        )
    else:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🚀 GET VIP ACCESS",
                    callback_data="menu:vip_options",
                )
            ]
        )

    if support_username:
        rows.append(
            [
                InlineKeyboardButton(
                    text="💬 VIP SUPPORT",
                    url=f"https://t.me/{support_username}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🏠 MAIN MENU",
                callback_data="menu:home",
            )
        ]
    )

    promo_text = (
        f"\n\n🎁 <b>Promo Code:</b> <code>{promo_code}</code>"
        if promo_code
        else ""
    )

    await callback.message.answer(
        f"<b>{heading}</b>\n\n"
        f"{body}"
        f"{promo_text}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows
        ),
    )

    await callback.answer()


@router.message(Command("howitworks"))
async def handle_how_it_works_command(
    message: Message,
    content_screen_settings_service: ContentScreenSettingsService,
) -> None:
    settings = await content_screen_settings_service.get(
        "how_it_works"
    )

    heading = (
        escape(settings.heading)
        if settings and settings.heading
        else "📖 HOW IT WORKS"
    )

    body = (
        escape(settings.body)
        if settings and settings.body
        else (
            "1️⃣ Choose your VIP option.\n"
            "2️⃣ Complete registration.\n"
            "3️⃣ Follow the verification instructions.\n"
            "4️⃣ Wait for VIP access approval.\n"
            "5️⃣ Start receiving VIP content."
        )
    )

    registration_url = (
        settings.registration_url
        if settings
        else None
    )

    promo_code = (
        escape(settings.promo_code)
        if settings and settings.promo_code
        else None
    )

    support_username = (
        settings.support_username
        if settings
        else None
    )

    if support_username:
        support_username = support_username.lstrip("@")

    rows: list[list[InlineKeyboardButton]] = []

    if registration_url:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🚀 GET VIP ACCESS",
                    url=registration_url,
                )
            ]
        )
    else:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🚀 GET VIP ACCESS",
                    callback_data="menu:vip_options",
                )
            ]
        )

    if support_username:
        rows.append(
            [
                InlineKeyboardButton(
                    text="💬 VIP SUPPORT",
                    url=f"https://t.me/{support_username}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🏠 MAIN MENU",
                callback_data="menu:home",
            )
        ]
    )

    promo_text = (
        f"\n\n🎁 <b>Promo Code:</b> <code>{promo_code}</code>"
        if promo_code
        else ""
    )

    await message.answer(
        f"<b>{heading}</b>\n\n"
        f"{body}"
        f"{promo_text}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows
        ),
    )


@router.callback_query(F.data == "menu:support")
async def handle_support(
    callback: CallbackQuery,
    content_screen_settings_service: ContentScreenSettingsService,
) -> None:
    if not isinstance(callback.message, Message):
        return

    settings = await content_screen_settings_service.get("support")

    heading = (
        escape(settings.heading)
        if settings and settings.heading
        else "💬 VIP SUPPORT"
    )

    body = (
        escape(settings.body)
        if settings and settings.body
        else (
            "Need help with registration, verification, "
            "VIP access, or your account?\n\n"
            "Contact our VIP support team below."
        )
    )

    support_username = (
        settings.support_username
        if settings
        else None
    )

    if support_username:
        support_username = support_username.lstrip("@")

    rows: list[list[InlineKeyboardButton]] = []

    if support_username:
        rows.append(
            [
                InlineKeyboardButton(
                    text="💬 VIP SUPPORT",
                    url=f"https://t.me/{support_username}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🏠 MAIN MENU",
                callback_data="menu:home",
            )
        ]
    )

    await callback.message.answer(
        f"<b>{heading}</b>\n\n"
        f"{body}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows
        ),
    )

    await callback.answer()


@router.message(Command("support"))
async def handle_support_command(
    message: Message,
    content_screen_settings_service: ContentScreenSettingsService,
) -> None:
    settings = await content_screen_settings_service.get("support")

    heading = (
        escape(settings.heading)
        if settings and settings.heading
        else "💬 VIP SUPPORT"
    )

    body = (
        escape(settings.body)
        if settings and settings.body
        else (
            "Need help with registration, verification, "
            "VIP access, or your account?\n\n"
            "Contact our VIP support team below."
        )
    )

    support_username = (
        settings.support_username
        if settings
        else None
    )

    if support_username:
        support_username = support_username.lstrip("@")

    rows: list[list[InlineKeyboardButton]] = []

    if support_username:
        rows.append(
            [
                InlineKeyboardButton(
                    text="💬 VIP SUPPORT",
                    url=f"https://t.me/{support_username}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🏠 MAIN MENU",
                callback_data="menu:home",
            )
        ]
    )

    await message.answer(
        f"<b>{heading}</b>\n\n"
        f"{body}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows
        ),
    )


@router.callback_query(F.data == "menu:winning_tips")
async def handle_winning_tips(
    callback: CallbackQuery,
    content_screen_settings_service: ContentScreenSettingsService,
) -> None:
    if not isinstance(callback.message, Message):
        return

    settings = await content_screen_settings_service.get("winning_tips")

    if settings is None:
        await callback.answer(
            "Winning Tips are not configured yet.",
            show_alert=True,
        )
        return

    heading = escape(
        settings.heading
        if settings.heading
        else "🎯 WINNING TIPS"
    )

    body = escape(
        settings.body
        if settings.body
        else "Winning tips and insights will appear here."
    )

    footer = escape(settings.footer) if settings.footer else ""

    if settings.media_file_id:
        if settings.media_type == "video":
            await callback.message.answer_video(
                video=settings.media_file_id,
            )
        elif settings.media_type == "photo":
            await callback.message.answer_photo(
                photo=settings.media_file_id,
            )

    text_parts = [
        f"<b>{heading}</b>",
        "",
        body,
    ]

    if footer:
        text_parts.extend(["", footer])

    rows: list[list[InlineKeyboardButton]] = []

    if settings.registration_url:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🚀 GET VIP ACCESS",
                    url=settings.registration_url,
                )
            ]
        )

    if settings.promo_code:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🎟 PROMO CODE",
                    callback_data="menu:vip_options",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="📊 COMPARE VIP",
                callback_data="menu:compare",
            )
        ]
    )

    rows.append(
        [
            InlineKeyboardButton(
                text="🏠 MAIN MENU",
                callback_data="menu:home",
            )
        ]
    )

    await callback.message.answer(
        "\n".join(text_parts),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows,
        ),
    )

    await callback.answer()


@router.callback_query(F.data == "menu:today_insights")
async def handle_today_insights(
    callback: CallbackQuery,
    content_screen_settings_service: ContentScreenSettingsService,
) -> None:
    if not isinstance(callback.message, Message):
        return

    settings = await content_screen_settings_service.get("today_insights")

    if settings is None:
        await callback.answer(
            "Today's Insights are not configured yet.",
            show_alert=True,
        )
        return

    heading = escape(
        settings.heading
        if settings.heading
        else "🔥 TODAY'S INSIGHTS"
    )

    body = escape(
        settings.body
        if settings.body
        else "Today's insights will appear here."
    )

    footer = escape(settings.footer) if settings.footer else ""

    text_parts = [
        f"<b>{heading}</b>",
        "",
        body,
    ]

    if footer:
        text_parts.extend(["", footer])

    rows: list[list[InlineKeyboardButton]] = []

    if settings.registration_url:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🚀 GET VIP ACCESS",
                    url=settings.registration_url,
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="📊 COMPARE VIP",
                callback_data="menu:compare",
            )
        ]
    )

    rows.append(
        [
            InlineKeyboardButton(
                text="🏠 MAIN MENU",
                callback_data="menu:home",
            )
        ]
    )

    await callback.message.answer(
        "\n".join(text_parts),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows,
        ),
    )

    await callback.answer()


@router.callback_query(F.data == "menu:live_stats")
async def handle_live_stats(
    callback: CallbackQuery,
    content_screen_settings_service: ContentScreenSettingsService,
) -> None:
    if not isinstance(callback.message, Message):
        return

    settings = await content_screen_settings_service.get("live_stats")

    if settings is None:
        await callback.answer(
            "Live Stats are not configured yet.",
            show_alert=True,
        )
        return

    heading = escape(
        settings.heading
        if settings.heading
        else "🏆 LIVE STATS"
    )

    body = escape(
        settings.body
        if settings.body
        else "Live bet updates will appear here."
    )

    footer = escape(settings.footer) if settings.footer else ""

    text_parts = [
        f"<b>{heading}</b>",
        "",
        body,
    ]

    if footer:
        text_parts.extend(["", footer])

    rows: list[list[InlineKeyboardButton]] = []

    if settings.registration_url:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🚀 GET VIP ACCESS",
                    url=settings.registration_url,
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="📊 COMPARE VIP",
                callback_data="menu:compare",
            )
        ]
    )

    rows.append(
        [
            InlineKeyboardButton(
                text="🏠 MAIN MENU",
                callback_data="menu:home",
            )
        ]
    )

    await callback.message.answer(
        "\n".join(text_parts),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows,
        ),
    )

    await callback.answer()


@router.callback_query(F.data == "menu:referral")
async def handle_referral(
    callback: CallbackQuery,
    referral_service: ReferralService,
    user_service: UserService,
) -> None:
    if not isinstance(callback.message, Message):
        return

    user = await user_service.upsert_from_telegram(
        callback.from_user
    )

    info = await referral_service.get_info(
        user_id=user.id,
    )

    bot_info = await callback.bot.get_me()
    bot_username = bot_info.username

    if not bot_username:
        await callback.answer(
            "Referral link is temporarily unavailable.",
            show_alert=True,
        )
        return

    referral_link = (
        f"https://t.me/{bot_username}"
        f"?start=ref_{info.referral_code}"
    )

    heading = "🎁 REFER & EARN"
    body = (
        "Invite your friends and earn rewards "
        "when they join through your personal referral link."
    )

    promo_code = info.promo_code or "Not set"

    rows: list[list[InlineKeyboardButton]] = []

    if info.vip_link:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🔗 OPEN VIP LINK",
                    url=info.vip_link,
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="📤 SHARE MY LINK",
                url=(
                    "https://t.me/share/url"
                    f"?url={referral_link}"
                    "&text=Join%20SPIDY%20SPORTS%20INTELLIGENCE"
                    "%20with%20my%20referral%20link"
                ),
            )
        ]
    )

    if info.claim_username:
        claim_username = info.claim_username.lstrip("@")
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"💰 CLAIM MY {info.commission_percent}%",
                    url=f"https://t.me/{claim_username}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🏠 MAIN MENU",
                callback_data="menu:home",
            )
        ]
    )

    await callback.message.answer(
        f"<b>{heading}</b>\n\n"
        f"{body}\n\n"
        f"💰 <b>Commission:</b> {info.commission_percent}%\n"
        f"🎟 <b>Promo Code:</b> <code>{escape(promo_code)}</code>\n\n"
        f"🔗 <b>Your Personal Referral Link:</b>\n"
        f"<code>{escape(referral_link)}</code>\n\n"
        f"👥 <b>Friends Joined:</b> {info.friends_joined}\n\n"
        "Share your personal link with friends. "
        "Each user can be attributed only once.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows,
        ),
    )

    await callback.answer()


@router.callback_query(F.data == "menu:notifications")
async def handle_notifications(
    callback: CallbackQuery,
    notification_preference_service: NotificationPreferenceService,
    user_service: UserService,
) -> None:
    if not isinstance(callback.message, Message):
        return

    user = await user_service.upsert_from_telegram(
        callback.from_user
    )

    preference = await notification_preference_service.get(
        user_id=user.id,
    )

    status = "🟢 ON" if preference.enabled else "🔴 OFF"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔴 TURN OFF" if preference.enabled else "🟢 TURN ON",
                    callback_data="notifications:toggle",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 MAIN MENU",
                    callback_data="menu:home",
                )
            ],
        ]
    )

    await callback.message.answer(
        "🔔 <b>NOTIFICATIONS</b>\n\n"
        f"VIP journey notifications: <b>{status}</b>\n\n"
        "You can change your notification preference below.",
        reply_markup=keyboard,
    )

    await callback.answer()


@router.callback_query(F.data == "notifications:toggle")
async def handle_notifications_toggle(
    callback: CallbackQuery,
    notification_preference_service: NotificationPreferenceService,
    user_service: UserService,
) -> None:
    if not isinstance(callback.message, Message):
        return

    user = await user_service.upsert_from_telegram(
        callback.from_user
    )

    preference = await notification_preference_service.toggle(
        user_id=user.id,
    )

    status = "🟢 ON" if preference.enabled else "🔴 OFF"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔴 TURN OFF" if preference.enabled else "🟢 TURN ON",
                    callback_data="notifications:toggle",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 MAIN MENU",
                    callback_data="menu:home",
                )
            ],
        ]
    )

    await callback.message.edit_text(
        "🔔 <b>NOTIFICATIONS</b>\n\n"
        f"VIP journey notifications: <b>{status}</b>\n\n"
        "Your notification preference has been updated.",
        reply_markup=keyboard,
    )

    await callback.answer(
        "Notification preference updated."
    )


@router.callback_query(F.data == "menu:home")
async def handle_home(
    callback: CallbackQuery,
) -> None:
    if not isinstance(callback.message, Message):
        return

    await callback.message.answer(
        "🏠 <b>MAIN MENU</b>\n\n"
        "Welcome back to <b>SPIDY’S ADMIN</b>.\n\n"
        "Choose an option below 👇",
        reply_markup=build_main_menu_keyboard(),
    )

    await callback.answer()


@router.message(Command("compare"))
async def handle_compare_command(
    message: Message,
    vip_category_service: VipCategoryService,
    vip_menu_settings_service: VipMenuSettingsService,
) -> None:
    categories = await vip_category_service.list_active()
    settings = await vip_menu_settings_service.get()

    if not categories:
        await message.answer(
            "📊 <b>COMPARE VIP OPTIONS</b>\n\n"
            "No VIP options are available right now.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="💎 VIP OPTIONS",
                            callback_data="menu:vip_options",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🏠 MAIN MENU",
                            callback_data="menu:home",
                        )
                    ],
                ]
            ),
        )
        return

    heading = escape(
        settings.compare_heading
        if settings and settings.compare_heading
        else "COMPARE VIP OPTIONS"
    )

    intro = escape(
        settings.compare_intro
        if settings and settings.compare_intro
        else "Compare the available VIP experiences below."
    )

    lines = [
        f"📊 <b>{heading}</b>",
        "",
        intro,
        "",
        "━━━━━━━━━━━━━━━━━━",
    ]

    keyboard_rows: list[list[InlineKeyboardButton]] = []

    for category in categories:
        display_name = escape(category.display_name)

        compare_info = (
            escape(category.compare_info)
            if category.compare_info
            else "Comparison information coming soon."
        )

        lines.extend(
            [
                "",
                f"💎 <b>{display_name}</b>",
                compare_info,
            ]
        )

        if category.promo_code:
            lines.append(
                "🎁 <b>Promo Code:</b> "
                f"<code>{escape(category.promo_code)}</code>"
            )

        if category.support_username:
            lines.append(
                "💬 <b>Support:</b> "
                f"@{escape(category.support_username)}"
            )

        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━")

        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text=f"✅ {category.display_name} — SELECT THIS VIP",
                    callback_data=f"vip_category:{category.id}",
                )
            ]
        )

    keyboard_rows.append(
        [
            InlineKeyboardButton(
                text="🔴 LIVE BETS",
                callback_data="menu:live_bets",
            ),
            InlineKeyboardButton(
                text="🎯 PRE-MATCH BETS",
                callback_data="menu:pre_match_bets",
            ),
        ]
    )

    keyboard_rows.append(
        [
            InlineKeyboardButton(
                text="💎 VIP OPTIONS",
                callback_data="menu:vip_options",
            )
        ]
    )

    keyboard_rows.append(
        [
            InlineKeyboardButton(
                text="🏠 MAIN MENU",
                callback_data="menu:home",
            )
        ]
    )

    await message.answer(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=keyboard_rows
        ),
    )


@router.callback_query(F.data == "menu:compare")
async def handle_compare_vip(
    callback: CallbackQuery,
    vip_category_service: VipCategoryService,
    vip_menu_settings_service: VipMenuSettingsService,
) -> None:
    if not isinstance(callback.message, Message):
        return

    categories = await vip_category_service.list_active()
    settings = await vip_menu_settings_service.get()

    if not categories:
        await callback.message.answer(
            "📊 <b>COMPARE VIP OPTIONS</b>\n\n"
            "No VIP options are available right now.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="💎 VIP OPTIONS",
                            callback_data="menu:vip_options",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🏠 MAIN MENU",
                            callback_data="menu:home",
                        )
                    ],
                ]
            ),
        )
        await callback.answer()
        return

    heading = escape(
        settings.compare_heading
        if settings and settings.compare_heading
        else "COMPARE VIP OPTIONS"
    )

    intro = escape(
        settings.compare_intro
        if settings and settings.compare_intro
        else "Compare the available VIP experiences below."
    )

    lines = [
        f"📊 <b>{heading}</b>",
        "",
        intro,
        "",
        "━━━━━━━━━━━━━━━━━━",
    ]

    keyboard_rows: list[list[InlineKeyboardButton]] = []

    for category in categories:
        display_name = escape(category.display_name)

        compare_info = (
            escape(category.compare_info)
            if category.compare_info
            else "Comparison information coming soon."
        )

        lines.extend(
            [
                "",
                f"💎 <b>{display_name}</b>",
                compare_info,
            ]
        )

        if category.promo_code:
            lines.append(
                "🎁 <b>Promo Code:</b> "
                f"<code>{escape(category.promo_code)}</code>"
            )

        if category.support_username:
            lines.append(
                "💬 <b>Support:</b> "
                f"@{escape(category.support_username)}"
            )

        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━")

        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text=f"✅ {category.display_name} — SELECT THIS VIP",
                    callback_data=f"vip_category:{category.id}",
                )
            ]
        )

    keyboard_rows.append(
        [
            InlineKeyboardButton(
                text="🔴 LIVE BETS",
                callback_data="menu:live_bets",
            ),
            InlineKeyboardButton(
                text="🎯 PRE-MATCH BETS",
                callback_data="menu:pre_match_bets",
            ),
        ]
    )

    keyboard_rows.append(
        [
            InlineKeyboardButton(
                text="💎 VIP OPTIONS",
                callback_data="menu:vip_options",
            )
        ]
    )

    keyboard_rows.append(
        [
            InlineKeyboardButton(
                text="🏠 MAIN MENU",
                callback_data="menu:home",
            )
        ]
    )

    await callback.message.answer(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=keyboard_rows
        ),
    )

    await callback.answer()


@router.callback_query(F.data == "menu:free_vs_vip")
async def handle_free_vs_vip(
    callback: CallbackQuery,
    vip_menu_settings_service: VipMenuSettingsService,
) -> None:
    if not isinstance(callback.message, Message):
        return

    settings = await vip_menu_settings_service.get()

    heading = escape(
        settings.free_vs_vip_heading
        if settings and settings.free_vs_vip_heading
        else "FREE vs VIP"
    )

    info = escape(
        settings.free_vs_vip_info
        if settings and settings.free_vs_vip_info
        else (
            "Compare the free experience with VIP access "
            "and choose what suits you best."
        )
    )

    lines = [
        f"🆚 <b>{heading}</b>",
        "",
        info,
    ]

    if settings and settings.free_vs_vip_promo_code:
        lines.extend(
            [
                "",
                "🎁 <b>Promo Code:</b> "
                f"<code>{escape(settings.free_vs_vip_promo_code)}</code>",
            ]
        )

    if settings and settings.free_vs_vip_support_username:
        lines.extend(
            [
                "",
                "💬 <b>Support:</b> "
                f"@{escape(settings.free_vs_vip_support_username)}",
            ]
        )

    keyboard_rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text="🚀 UPGRADE TO VIP",
                callback_data="menu:vip_options",
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 COMPARE VIP",
                callback_data="menu:compare",
            )
        ],
        [
            InlineKeyboardButton(
                text="💎 VIP OPTIONS",
                callback_data="menu:vip_options",
            )
        ],
    ]

    if settings and settings.free_vs_vip_support_username:
        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text="💬 VIP SUPPORT",
                    url=(
                        "https://t.me/"
                        f"{settings.free_vs_vip_support_username}"
                    ),
                )
            ]
        )

    keyboard_rows.append(
        [
            InlineKeyboardButton(
                text="🏠 MAIN MENU",
                callback_data="menu:home",
            )
        ]
    )

    await callback.message.answer(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=keyboard_rows
        ),
    )

    await callback.answer()




@router.callback_query(F.data == "menu:live_bets")
async def handle_live_bets(
    callback: CallbackQuery,
    vip_menu_settings_service: VipMenuSettingsService,
) -> None:
    if not isinstance(callback.message, Message):
        return

    settings = await vip_menu_settings_service.get()

    heading = escape(
        settings.live_bets_heading
        if settings and settings.live_bets_heading
        else "LIVE BETS"
    )

    info = escape(
        settings.live_bets_info
        if settings and settings.live_bets_info
        else "Live betting insights will appear here when configured."
    )

    if settings is not None and settings.live_bets_media_file_id:
        if settings.live_bets_media_type == "video":
            await callback.message.answer_video(
                video=settings.live_bets_media_file_id,
            )
        elif settings.live_bets_media_type == "photo":
            await callback.message.answer_photo(
                photo=settings.live_bets_media_file_id,
            )

    await callback.message.answer(
        f"🔴 <b>{heading}</b>\n\n"
        f"{info}\n\n"
        "No prediction or outcome is guaranteed.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🎯 PRE-MATCH BETS",
                        callback_data="menu:pre_match_bets",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📊 COMPARE VIP",
                        callback_data="menu:compare",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="💎 VIP OPTIONS",
                        callback_data="menu:vip_options",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🏠 MAIN MENU",
                        callback_data="menu:home",
                    )
                ],
            ]
        ),
    )

    await callback.answer()


@router.callback_query(F.data == "menu:pre_match_bets")
async def handle_pre_match_bets(
    callback: CallbackQuery,
    vip_menu_settings_service: VipMenuSettingsService,
) -> None:
    if not isinstance(callback.message, Message):
        return

    settings = await vip_menu_settings_service.get()

    heading = escape(
        settings.pre_match_bets_heading
        if settings and settings.pre_match_bets_heading
        else "PRE-MATCH BETS"
    )

    info = escape(
        settings.pre_match_bets_info
        if settings and settings.pre_match_bets_info
        else "Pre-match insights will appear here when configured."
    )

    if settings is not None and settings.pre_match_bets_media_file_id:
        if settings.pre_match_bets_media_type == "video":
            await callback.message.answer_video(
                video=settings.pre_match_bets_media_file_id,
            )
        elif settings.pre_match_bets_media_type == "photo":
            await callback.message.answer_photo(
                photo=settings.pre_match_bets_media_file_id,
            )

    await callback.message.answer(
        f"🎯 <b>{heading}</b>\n\n"
        f"{info}\n\n"
        "No prediction or outcome is guaranteed.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔴 LIVE BETS",
                        callback_data="menu:live_bets",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📊 COMPARE VIP",
                        callback_data="menu:compare",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="💎 VIP OPTIONS",
                        callback_data="menu:vip_options",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🏠 MAIN MENU",
                        callback_data="menu:home",
                    )
                ],
            ]
        ),
    )

    await callback.answer()
