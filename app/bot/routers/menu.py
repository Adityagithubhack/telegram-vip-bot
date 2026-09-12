from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.bot.views.dashboard import send_vip_dashboard
from app.bot.views.language import send_language_menu
from app.bot.views.membership import send_membership_gate
from app.bot.views.vip_category import send_vip_categories
from app.services.membership import MembershipService
from app.services.onboarding import OnboardingProgress, OnboardingService
from app.services.user import UserService
from app.services.vip_category import VipCategoryService

router = Router(name="menu")


def build_main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 EXPLORE VIP OPTIONS",
                    callback_data="menu:vip_options",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💎 VIP OPTIONS",
                    callback_data="menu:vip_options",
                ),
                InlineKeyboardButton(
                    text="👑 MY VIP DASHBOARD",
                    callback_data="menu:my_vip",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🎯 WINNING TIPS",
                    callback_data="menu:winning_tips",
                ),
                InlineKeyboardButton(
                    text="🔥 TODAY'S INSIGHTS",
                    callback_data="menu:insights",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🏆 LIVE STATS",
                    callback_data="menu:live_stats",
                ),
                InlineKeyboardButton(
                    text="🆚 FREE vs VIP",
                    callback_data="menu:free_vs_vip",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🎁 REFER & EARN",
                    callback_data="menu:referral",
                ),
                InlineKeyboardButton(
                    text="📖 HOW IT WORKS",
                    callback_data="menu:how_it_works",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📊 COMPARE VIP",
                    callback_data="menu:compare",
                ),
                InlineKeyboardButton(
                    text="🎯 DAILY PICKS",
                    callback_data="menu:daily_picks",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🌐 LANGUAGE",
                    callback_data="menu:language",
                ),
                InlineKeyboardButton(
                    text="🔔 NOTIFICATIONS",
                    callback_data="menu:notifications",
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


async def send_main_menu(
    message: Message,
    *,
    progress: OnboardingProgress,
) -> None:
    state = progress.state

    language_mark = (
        "✅" if state.language_selected_at else "⬜"
    )
    category_mark = (
        "✅" if state.category_selected_at else "⬜"
    )
    registration_mark = (
        "✅" if state.registration_completed_at else "⬜"
    )
    contact_mark = (
        "✅" if state.contact_verified_at else "⬜"
    )
    access_mark = (
        "✅" if state.vip_access_granted_at else "⬜"
    )

    await message.answer(
        "🏆 <b>SPIDY SPORTS INTELLIGENCE — VIP MENU</b>\n\n"
        "Welcome to <b>SPIDY’S ADMIN</b>.\n\n"
        "💎 Premium VIP options\n"
        "📊 Match intelligence & insights\n"
        "🔥 Live match updates\n\n"
        "<b>🏆 VIP JOURNEY</b>\n\n"
        f"{language_mark} Language Selected\n"
        f"{category_mark} VIP Category Selected\n"
        f"{registration_mark} Registration\n"
        f"{contact_mark} Contact Verification\n"
        f"{access_mark} VIP Access\n\n"
        f"📈 Progress: <b>{progress.progress_percent}%</b>\n\n"
        "Choose an option below 👇",
        reply_markup=build_main_menu_keyboard(),
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
    )



@router.callback_query(F.data == "menu:language")
async def handle_language_menu(
    callback: CallbackQuery,
) -> None:
    if not isinstance(callback.message, Message):
        return

    await callback.answer()
    await send_language_menu(callback.message)



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
    )


@router.callback_query(F.data == "menu:vip_options")
async def handle_vip_options(
    callback: CallbackQuery,
    vip_category_service: VipCategoryService,
) -> None:
    if not isinstance(callback.message, Message):
        return

    categories = await vip_category_service.list_active()

    await callback.answer()

    await send_vip_categories(
        callback.message,
        categories=categories,
    )


@router.callback_query(F.data.startswith("vip_category:"))
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
    )
