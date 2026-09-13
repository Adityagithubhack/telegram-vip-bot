from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.bot.states.daily_pick import DailyPickStates
from app.bot.states.vip_settings import VipSettingsStates
from app.config.settings import get_settings
from app.services.admin_vip import AdminVipService
from app.services.daily_pick import DailyPickService
from app.services.onboarding import OnboardingService
from app.services.user import UserService
from app.services.vip_category import VipCategoryService
from app.services.vip_menu_settings import VipMenuSettingsService

router = Router(name="admin")


def _is_super_admin(telegram_user_id: int) -> bool:
    settings = get_settings()

    return (
        settings.super_admin_telegram_id is not None
        and telegram_user_id == settings.super_admin_telegram_id
    )


def _admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⏳ PENDING VIP APPROVALS",
                    callback_data="admin:vip_pending",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 CREATE DAILY PICK",
                    callback_data="admin:daily_pick_create",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚙️ VIP SETTINGS",
                    callback_data="admin:vip_settings",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🧩 VIP MENU SETTINGS",
                    callback_data="admin:vip_menu_settings",
                )
            ],
        ]
    )


@router.message(Command("admin"))
async def handle_admin(message: Message) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await message.answer("⛔ You are not authorized.")
        return

    await message.answer(
        "🛡 <b>ADMIN PANEL</b>\n\n"
        "✅ Super admin access verified.",
        reply_markup=_admin_keyboard(),
    )


@router.callback_query(F.data == "admin:vip_pending")
async def handle_pending_vip_approvals(
    callback: CallbackQuery,
    onboarding_service: OnboardingService,
    user_service: UserService,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Unauthorized",
            show_alert=True,
        )
        return

    pending = await onboarding_service.list_pending_vip_approvals()

    if not pending:
        await callback.answer()
        if isinstance(callback.message, Message):
            await callback.message.answer(
                "✅ No pending VIP approvals."
            )
        return

    users = await user_service.get_by_ids(
        [item.user_id for item in pending]
    )

    users_by_id = {
        user.id: user
        for user in users
    }

    lines = [
        "⏳ <b>PENDING VIP APPROVALS</b>",
        "",
    ]

    keyboard_rows: list[list[InlineKeyboardButton]] = []

    for item in pending:
        user = users_by_id.get(item.user_id)

        if user is None:
            continue

        display_name = (
            user.first_name
            or user.username
            or str(user.telegram_user_id)
        )

        username = (
            f"@{user.username}"
            if user.username
            else "No username"
        )

        lines.append(
            f"👤 <b>{display_name}</b>\n"
            f"ID: <code>{user.telegram_user_id}</code>\n"
            f"{username}"
        )
        lines.append("")

        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text=f"✅ Approve {display_name}",
                    callback_data=f"admin:vip_approve:{user.id}",
                )
            ]
        )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=keyboard_rows
            ),
        )

    await callback.answer()

@router.callback_query(F.data.startswith("admin:vip_approve:"))
async def handle_vip_approve(
    callback: CallbackQuery,
    admin_vip_service: AdminVipService,
    bot: Bot,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Unauthorized",
            show_alert=True,
        )
        return

    if callback.data is None:
        return

    try:
        user_id = int(
            callback.data.removeprefix(
                "admin:vip_approve:"
            )
        )
    except ValueError:
        await callback.answer(
            "Invalid approval request",
            show_alert=True,
        )
        return

    result = await admin_vip_service.approve_vip(
        actor_telegram_user_id=callback.from_user.id,
        user_id=user_id,
    )

    if not result.granted:
        messages = {
            "onboarding_not_found": "❌ User onboarding not found",
            "already_granted": "ℹ️ VIP access already granted",
            "contact_not_verified": "❌ Contact verification is incomplete",
        }

        await callback.answer(
            messages.get(
                result.reason,
                "❌ VIP approval failed",
            ),
            show_alert=True,
        )
        return

    if result.telegram_user_id is not None:
        await bot.send_message(
            chat_id=result.telegram_user_id,
            text=(
                "👑 <b>VIP ACCESS GRANTED</b>\n\n"
                "Your VIP access has been approved successfully.\n"
                "Open your dashboard to continue."
            ),
        )

    await callback.answer(
        "✅ VIP access granted",
        show_alert=True,
    )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "👑 <b>VIP ACCESS GRANTED</b>\n\n"
            f"Internal user ID: <code>{user_id}</code>"
        )


@router.callback_query(F.data == "admin:daily_pick_create")
async def handle_daily_pick_create(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Unauthorized",
            show_alert=True,
        )
        return

    await state.clear()
    await state.set_state(DailyPickStates.sport)

    await callback.answer()

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "📝 <b>CREATE DAILY PICK</b>\n\n"
            "Step 1/7 — Enter the sport.\n\n"
            "Example: <code>Football</code>"
        )


@router.message(DailyPickStates.sport)
async def daily_pick_sport(
    message: Message,
    state: FSMContext,
) -> None:
    if message.from_user is None or not _is_super_admin(message.from_user.id):
        return

    sport = (message.text or "").strip()

    if not sport:
        await message.answer("❌ Please enter a sport.")
        return

    await state.update_data(sport=sport)
    await state.set_state(DailyPickStates.event_title)

    await message.answer(
        "Step 2/7 — Enter the event/match title.\n\n"
        "Example: <code>Arsenal vs Chelsea</code>"
    )


@router.message(DailyPickStates.event_title)
async def daily_pick_event(
    message: Message,
    state: FSMContext,
) -> None:
    if message.from_user is None or not _is_super_admin(message.from_user.id):
        return

    event_title = (message.text or "").strip()

    if not event_title:
        await message.answer("❌ Please enter an event title.")
        return

    await state.update_data(event_title=event_title)
    await state.set_state(DailyPickStates.selection)

    await message.answer(
        "Step 3/7 — Enter your selection/pick.\n\n"
        "Example: <code>Arsenal to win</code>"
    )


@router.message(DailyPickStates.selection)
async def daily_pick_selection(
    message: Message,
    state: FSMContext,
) -> None:
    if message.from_user is None or not _is_super_admin(message.from_user.id):
        return

    selection = (message.text or "").strip()

    if not selection:
        await message.answer("❌ Please enter a selection.")
        return

    await state.update_data(selection=selection)
    await state.set_state(DailyPickStates.confidence)

    await message.answer(
        "Step 4/7 — Enter confidence from <b>0 to 100</b>.\n\n"
        "Example: <code>85</code>"
    )


@router.message(DailyPickStates.confidence)
async def daily_pick_confidence(
    message: Message,
    state: FSMContext,
) -> None:
    if message.from_user is None or not _is_super_admin(message.from_user.id):
        return

    try:
        confidence = int((message.text or "").strip())
    except ValueError:
        await message.answer("❌ Enter a whole number from 0 to 100.")
        return

    if not 0 <= confidence <= 100:
        await message.answer("❌ Confidence must be between 0 and 100.")
        return

    await state.update_data(confidence=confidence)
    await state.set_state(DailyPickStates.odds)

    await message.answer(
        "Step 5/7 — Enter odds.\n\n"
        "Example: <code>1.85</code>\n"
        "If there are no odds, enter <code>skip</code>."
    )


@router.message(DailyPickStates.odds)
async def daily_pick_odds(
    message: Message,
    state: FSMContext,
) -> None:
    if message.from_user is None or not _is_super_admin(message.from_user.id):
        return

    value = (message.text or "").strip()

    if value.lower() == "skip":
        odds = None
    else:
        try:
            odds = float(value)
        except ValueError:
            await message.answer(
                "❌ Enter valid odds, for example <code>1.85</code>, "
                "or type <code>skip</code>."
            )
            return

        if odds <= 0:
            await message.answer("❌ Odds must be greater than 0.")
            return

    await state.update_data(odds=odds)
    await state.set_state(DailyPickStates.analysis)

    await message.answer(
        "Step 6/7 — Enter the analysis/reason.\n\n"
        "You can write a short explanation of the pick."
    )


@router.message(DailyPickStates.analysis)
async def daily_pick_analysis(
    message: Message,
    state: FSMContext,
) -> None:
    if message.from_user is None or not _is_super_admin(message.from_user.id):
        return

    analysis = (message.text or "").strip()

    if not analysis:
        await message.answer("❌ Please enter the analysis.")
        return

    await state.update_data(analysis=analysis)
    await state.set_state(DailyPickStates.preview)

    data = await state.get_data()

    odds_text = (
        str(data["odds"])
        if data.get("odds") is not None
        else "Not specified"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 PUBLISH PICK",
                    callback_data="admin:daily_pick_publish",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ CANCEL",
                    callback_data="admin:daily_pick_cancel",
                )
            ],
        ]
    )

    await message.answer(
        "👀 <b>DAILY PICK PREVIEW</b>\n\n"
        f"🏅 Sport: <b>{data['sport']}</b>\n"
        f"🏟 Event: <b>{data['event_title']}</b>\n"
        f"🎯 Selection: <b>{data['selection']}</b>\n"
        f"🔥 Confidence: <b>{data['confidence']}%</b>\n"
        f"📈 Odds: <b>{odds_text}</b>\n"
        f"📝 Analysis: {data['analysis']}\n\n"
        "Publish this pick?",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "admin:daily_pick_publish")
async def handle_daily_pick_publish(
    callback: CallbackQuery,
    state: FSMContext,
    daily_pick_service: DailyPickService,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Unauthorized",
            show_alert=True,
        )
        return

    data = await state.get_data()

    required = (
        "sport",
        "event_title",
        "selection",
        "confidence",
        "analysis",
    )

    if any(key not in data for key in required):
        await state.clear()
        await callback.answer(
            "❌ Pick data expired. Start again.",
            show_alert=True,
        )
        return

    pick = await daily_pick_service.create_pick(
        sport=str(data["sport"]),
        event_title=str(data["event_title"]),
        selection=str(data["selection"]),
        confidence=int(data["confidence"]),
        odds=data.get("odds"),
        analysis=str(data["analysis"]),
    )

    published = await daily_pick_service.publish_pick(
        actor_telegram_user_id=callback.from_user.id,
        pick_id=pick.id,
    )

    await state.clear()

    if published is None:
        await callback.answer(
            "❌ Could not publish pick.",
            show_alert=True,
        )
        return

    await callback.answer(
        "✅ Daily Pick published",
        show_alert=True,
    )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "🎯 <b>DAILY PICK PUBLISHED</b>\n\n"
            f"🏟 {published.event_title}\n"
            f"🎯 {published.selection}\n"
            f"🔥 Confidence: {published.confidence}%"
        )


@router.callback_query(F.data == "admin:daily_pick_cancel")
async def handle_daily_pick_cancel(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Unauthorized",
            show_alert=True,
        )
        return

    await state.clear()

    await callback.answer(
        "Daily Pick cancelled",
        show_alert=False,
    )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "❌ <b>Daily Pick creation cancelled.</b>"
        )


@router.callback_query(F.data == "admin:vip_settings")
async def handle_vip_settings(
    callback: CallbackQuery,
    vip_category_service: VipCategoryService,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Unauthorized",
            show_alert=True,
        )
        return

    if not isinstance(callback.message, Message):
        return

    categories = await vip_category_service.list_all()

    rows: list[list[InlineKeyboardButton]] = []

    for category in categories:
        label = category.display_name

        if not category.is_active:
            label = f"🔴 {label} (INACTIVE)"

        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"admin:vip_settings:{category.id}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="➕ ADD NEW VIP",
                callback_data="admin:vip_add",
            )
        ]
    )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ BACK TO ADMIN",
                callback_data="admin:home",
            )
        ]
    )

    await callback.message.answer(
        "⚙️ <b>VIP SETTINGS</b>\n\n"
        "Choose the VIP category you want to manage:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows,
        ),
    )

    await callback.answer()


@router.callback_query(F.data == "admin:home")
async def handle_admin_home(
    callback: CallbackQuery,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Unauthorized",
            show_alert=True,
        )
        return

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "🛡 <b>ADMIN PANEL</b>",
            reply_markup=_admin_keyboard(),
        )

    await callback.answer()

@router.callback_query(F.data.startswith("admin:vip_settings:"))
async def handle_vip_category_settings(
    callback: CallbackQuery,
    vip_category_service: VipCategoryService,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Unauthorized",
            show_alert=True,
        )
        return

    if not isinstance(callback.message, Message):
        return

    if callback.data is None:
        return

    raw_category_id = callback.data.removeprefix(
        "admin:vip_settings:"
    )

    try:
        category_id = int(raw_category_id)
    except ValueError:
        await callback.answer(
            "Invalid VIP category",
            show_alert=True,
        )
        return

    category = await vip_category_service.get_any_by_id(
        category_id=category_id,
    )

    if category is None:
        await callback.answer(
            "VIP category not found",
            show_alert=True,
        )
        return

    labels = {
        "standard": "⭐ STANDARD VIP",
        "premium": "💎 PREMIUM VIP",
        "elite": "👑 ELITE VIP",
    }

    title = labels.get(
        category.code,
        category.code.replace("_", " ").upper(),
    )

    media_status = (
        f"✅ {category.media_type or 'media'} configured"
        if category.media_file_id
        else "❌ Not configured"
    )

    link_status = (
        "✅ Configured"
        if category.registration_url
        else "❌ Not configured"
    )

    promo_status = (
        f"✅ {category.promo_code}"
        if category.promo_code
        else "❌ Not configured"
    )

    support_status = (
        f"✅ @{category.support_username}"
        if category.support_username
        else "❌ Not configured"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎬 CHANGE VIDEO / MEDIA",
                    callback_data=f"admin:vip_media:{category.id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔗 CHANGE REGISTRATION LINK",
                    callback_data=f"admin:vip_link:{category.id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎁 CHANGE PROMO CODE",
                    callback_data=f"admin:vip_promo:{category.id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 CHANGE VIP SUPPORT USERNAME",
                    callback_data=f"admin:vip_support:{category.id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ CHANGE VIP NAME",
                    callback_data=f"admin:vip_name:{category.id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 CHANGE VIP INFO",
                    callback_data=f"admin:vip_info:{category.id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 CHANGE COMPARE INFO",
                    callback_data=f"admin:vip_compare_info:{category.id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬆️ MOVE UP",
                    callback_data=f"admin:vip_move_up:{category.id}",
                ),
                InlineKeyboardButton(
                    text="⬇️ MOVE DOWN",
                    callback_data=f"admin:vip_move_down:{category.id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=(
                        "🗑 DEACTIVATE VIP"
                        if category.is_active
                        else "♻️ REACTIVATE VIP"
                    ),
                    callback_data=(
                        f"admin:vip_deactivate:{category.id}"
                        if category.is_active
                        else f"admin:vip_reactivate:{category.id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ BACK TO VIP SETTINGS",
                    callback_data="admin:vip_settings",
                )
            ],
        ]
    )

    await callback.message.answer(
        f"⚙️ <b>MANAGE {title}</b>\n\n"
        f"🎬 Media: {media_status}\n"
        f"🔗 Registration Link: {link_status}\n"
        f"🎁 Promo Code: {promo_status}\n"
        f"👤 VIP Support: {support_status}",
        reply_markup=keyboard,
    )

    await callback.answer()

@router.callback_query(F.data.startswith("admin:vip_media:"))
async def handle_vip_media_change(
    callback: CallbackQuery,
    state: FSMContext,
    vip_category_service: VipCategoryService,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Unauthorized",
            show_alert=True,
        )
        return

    if callback.data is None:
        return

    raw_category_id = callback.data.removeprefix(
        "admin:vip_media:"
    )

    try:
        category_id = int(raw_category_id)
    except ValueError:
        await callback.answer(
            "Invalid VIP category",
            show_alert=True,
        )
        return

    category = await vip_category_service.get_by_id(
        category_id=category_id,
    )

    if category is None:
        await callback.answer(
            "VIP category not found",
            show_alert=True,
        )
        return

    await state.set_state(
        VipSettingsStates.waiting_for_media
    )
    await state.update_data(
        vip_category_id=category_id,
    )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "🎬 <b>SEND NEW VIP MEDIA</b>\n\n"
            "Send a <b>video</b> or <b>photo</b> now.\n\n"
            "The new media will replace the current media "
            "for this VIP category."
        )

    await callback.answer()


@router.message(VipSettingsStates.waiting_for_media)
async def handle_vip_media_upload(
    message: Message,
    state: FSMContext,
    vip_category_service: VipCategoryService,
) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ You are not authorized.")
        return

    data = await state.get_data()
    raw_category_id = data.get("vip_category_id")

    if raw_category_id is None:
        await state.clear()
        await message.answer(
            "❌ VIP category context was lost. Please try again."
        )
        return

    category_id = int(raw_category_id)

    media_file_id: str | None = None
    media_type: str | None = None

    if message.video is not None:
        media_file_id = message.video.file_id
        media_type = "video"
    elif message.photo:
        media_file_id = message.photo[-1].file_id
        media_type = "photo"

    if media_file_id is None or media_type is None:
        await message.answer(
            "❌ Please send a video or photo only."
        )
        return

    updated = await vip_category_service.update_media(
        category_id=category_id,
        media_file_id=media_file_id,
        media_type=media_type,
    )

    if not updated:
        await state.clear()
        await message.answer(
            "❌ Could not update VIP media."
        )
        return

    await state.clear()

    await message.answer(
        f"✅ <b>VIP {media_type.upper()} UPDATED</b>\n\n"
        "Users opening this VIP option will now see "
        "the new media."
    )

@router.callback_query(F.data.startswith("admin:vip_link:"))
async def handle_vip_registration_link_change(
    callback: CallbackQuery,
    state: FSMContext,
    vip_category_service: VipCategoryService,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Unauthorized",
            show_alert=True,
        )
        return

    if callback.data is None:
        return

    raw_category_id = callback.data.removeprefix(
        "admin:vip_link:"
    )

    try:
        category_id = int(raw_category_id)
    except ValueError:
        await callback.answer(
            "Invalid VIP category",
            show_alert=True,
        )
        return

    category = await vip_category_service.get_by_id(
        category_id=category_id,
    )

    if category is None:
        await callback.answer(
            "VIP category not found",
            show_alert=True,
        )
        return

    await state.set_state(
        VipSettingsStates.waiting_for_registration_url
    )
    await state.update_data(
        vip_category_id=category_id,
    )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "🔗 <b>SEND NEW REGISTRATION LINK</b>\n\n"
            "Send the full registration/referral URL now.\n\n"
            "Example:\n"
            "<code>https://example.com/register</code>"
        )

    await callback.answer()


@router.message(VipSettingsStates.waiting_for_registration_url)
async def handle_vip_registration_link_input(
    message: Message,
    state: FSMContext,
    vip_category_service: VipCategoryService,
) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ You are not authorized.")
        return

    if message.text is None:
        await message.answer(
            "❌ Please send the registration link as text."
        )
        return

    registration_url = message.text.strip()

    if not (
        registration_url.startswith("https://")
        or registration_url.startswith("http://")
    ):
        await message.answer(
            "❌ Please send a valid link starting with "
            "<code>https://</code> or <code>http://</code>."
        )
        return

    data = await state.get_data()
    raw_category_id = data.get("vip_category_id")

    if raw_category_id is None:
        await state.clear()
        await message.answer(
            "❌ VIP category context was lost. Please try again."
        )
        return

    category_id = int(raw_category_id)

    updated = await vip_category_service.update_registration_url(
        category_id=category_id,
        registration_url=registration_url,
    )

    if not updated:
        await state.clear()
        await message.answer(
            "❌ Could not update registration link."
        )
        return

    await state.clear()

    await message.answer(
        "✅ <b>REGISTRATION LINK UPDATED</b>\n\n"
        "Users opening this VIP option will now see "
        "the new REGISTER NOW link."
    )

@router.callback_query(F.data.startswith("admin:vip_promo:"))
async def handle_vip_promo_change(
    callback: CallbackQuery,
    state: FSMContext,
    vip_category_service: VipCategoryService,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Unauthorized",
            show_alert=True,
        )
        return

    if callback.data is None:
        return

    raw_category_id = callback.data.removeprefix(
        "admin:vip_promo:"
    )

    try:
        category_id = int(raw_category_id)
    except ValueError:
        await callback.answer(
            "Invalid VIP category",
            show_alert=True,
        )
        return

    category = await vip_category_service.get_by_id(
        category_id=category_id,
    )

    if category is None:
        await callback.answer(
            "VIP category not found",
            show_alert=True,
        )
        return

    await state.set_state(
        VipSettingsStates.waiting_for_promo_code
    )
    await state.update_data(
        vip_category_id=category_id,
    )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "🎁 <b>SEND NEW PROMO CODE</b>\n\n"
            "Send the promo code you want users to see "
            "for this VIP category."
        )

    await callback.answer()


@router.message(VipSettingsStates.waiting_for_promo_code)
async def handle_vip_promo_input(
    message: Message,
    state: FSMContext,
    vip_category_service: VipCategoryService,
) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ You are not authorized.")
        return

    if message.text is None:
        await message.answer(
            "❌ Please send the promo code as text."
        )
        return

    promo_code = message.text.strip()

    if not promo_code:
        await message.answer(
            "❌ Promo code cannot be empty."
        )
        return

    if len(promo_code) > 128:
        await message.answer(
            "❌ Promo code is too long."
        )
        return

    data = await state.get_data()
    raw_category_id = data.get("vip_category_id")

    if raw_category_id is None:
        await state.clear()
        await message.answer(
            "❌ VIP category context was lost. Please try again."
        )
        return

    category_id = int(raw_category_id)

    updated = await vip_category_service.update_promo_code(
        category_id=category_id,
        promo_code=promo_code,
    )

    if not updated:
        await state.clear()
        await message.answer(
            "❌ Could not update promo code."
        )
        return

    await state.clear()

    await message.answer(
        "✅ <b>PROMO CODE UPDATED</b>\n\n"
        "Users opening this VIP option will now see "
        f"<code>{promo_code}</code>."
    )

@router.callback_query(F.data.startswith("admin:vip_support:"))
async def handle_vip_support_change(
    callback: CallbackQuery,
    state: FSMContext,
    vip_category_service: VipCategoryService,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Unauthorized",
            show_alert=True,
        )
        return

    if callback.data is None:
        return

    raw_category_id = callback.data.removeprefix(
        "admin:vip_support:"
    )

    try:
        category_id = int(raw_category_id)
    except ValueError:
        await callback.answer(
            "Invalid VIP category",
            show_alert=True,
        )
        return

    category = await vip_category_service.get_by_id(
        category_id=category_id,
    )

    if category is None:
        await callback.answer(
            "VIP category not found",
            show_alert=True,
        )
        return

    await state.set_state(
        VipSettingsStates.waiting_for_support_username
    )
    await state.update_data(
        vip_category_id=category_id,
    )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "👤 <b>SEND VIP SUPPORT USERNAME</b>\n\n"
            "Send the Telegram username for this VIP category.\n"
            "Example: <code>@yourusername</code>"
        )

    await callback.answer()


@router.message(VipSettingsStates.waiting_for_support_username)
async def handle_vip_support_input(
    message: Message,
    state: FSMContext,
    vip_category_service: VipCategoryService,
) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ You are not authorized.")
        return

    if message.text is None:
        await message.answer(
            "❌ Please send the Telegram username as text."
        )
        return

    username = message.text.strip().removeprefix("@")

    if not username:
        await message.answer(
            "❌ Username cannot be empty."
        )
        return

    if len(username) > 32:
        await message.answer(
            "❌ Telegram username is too long."
        )
        return

    if not username.replace("_", "").isalnum():
        await message.answer(
            "❌ Invalid Telegram username."
        )
        return

    data = await state.get_data()
    category_id = data.get("vip_category_id")

    if not isinstance(category_id, int):
        await state.clear()
        await message.answer(
            "❌ VIP category state is invalid. Please try again."
        )
        return

    updated = await vip_category_service.update_support_username(
        category_id=category_id,
        support_username=username,
    )

    if not updated:
        await state.clear()
        await message.answer(
            "❌ VIP category could not be updated."
        )
        return

    await state.clear()

    await message.answer(
        "✅ <b>VIP SUPPORT USERNAME UPDATED</b>\n\n"
        f"Support: @{username}\n"
        f"Link: https://t.me/{username}"
    )

@router.callback_query(F.data.startswith("admin:vip_info:"))
async def handle_vip_info_change(
    callback: CallbackQuery,
    state: FSMContext,
    vip_category_service: VipCategoryService,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Unauthorized",
            show_alert=True,
        )
        return

    if callback.data is None:
        return

    raw_category_id = callback.data.removeprefix(
        "admin:vip_info:"
    )

    try:
        category_id = int(raw_category_id)
    except ValueError:
        await callback.answer(
            "Invalid VIP category",
            show_alert=True,
        )
        return

    category = await vip_category_service.get_by_id(
        category_id=category_id,
    )

    if category is None:
        await callback.answer(
            "VIP category not found",
            show_alert=True,
        )
        return

    await state.set_state(
        VipSettingsStates.waiting_for_vip_info
    )
    await state.update_data(
        vip_category_id=category_id,
    )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "📝 <b>SEND VIP INFO</b>\n\n"
            "Send the description/info you want users to see "
            "when they open this VIP category.\n\n"
            "You can use multiple lines."
        )

    await callback.answer()


@router.message(VipSettingsStates.waiting_for_vip_info)
async def handle_vip_info_input(
    message: Message,
    state: FSMContext,
    vip_category_service: VipCategoryService,
) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ You are not authorized.")
        return

    if message.text is None:
        await message.answer(
            "❌ Please send the VIP info as text."
        )
        return

    vip_info = message.text.strip()

    if not vip_info:
        await message.answer(
            "❌ VIP info cannot be empty."
        )
        return

    if len(vip_info) > 4000:
        await message.answer(
            "❌ VIP info is too long. Maximum 4000 characters."
        )
        return

    data = await state.get_data()
    category_id = data.get("vip_category_id")

    if not isinstance(category_id, int):
        await state.clear()
        await message.answer(
            "❌ VIP category state is invalid. Please try again."
        )
        return

    updated = await vip_category_service.update_vip_info(
        category_id=category_id,
        vip_info=vip_info,
    )

    if not updated:
        await state.clear()
        await message.answer(
            "❌ VIP category could not be updated."
        )
        return

    await state.clear()

    await message.answer(
        "✅ <b>VIP INFO UPDATED</b>\n\n"
        "Users will now see this information when they open this VIP category."
    )

@router.callback_query(F.data == "admin:vip_menu_settings")
async def handle_vip_menu_settings(
    callback: CallbackQuery,
    vip_menu_settings_service: VipMenuSettingsService,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Unauthorized",
            show_alert=True,
        )
        return

    settings = await vip_menu_settings_service.get()

    if settings is None:
        await callback.answer(
            "VIP menu settings not found",
            show_alert=True,
        )
        return

    if not isinstance(callback.message, Message):
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ CHANGE HEADING",
                    callback_data="admin:vip_menu_heading",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 CHANGE DESCRIPTION",
                    callback_data="admin:vip_menu_description",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👇 CHANGE FOOTER TEXT",
                    callback_data="admin:vip_menu_footer",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 CHANGE COMPARE HEADING",
                    callback_data="admin:compare_heading",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 CHANGE COMPARE INTRO",
                    callback_data="admin:compare_intro",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🆚 CHANGE FREE vs VIP HEADING",
                    callback_data="admin:free_vs_vip_heading",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 CHANGE FREE vs VIP INFO",
                    callback_data="admin:free_vs_vip_info",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎁 CHANGE FREE vs VIP PROMO CODE",
                    callback_data="admin:free_vs_vip_promo",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💬 CHANGE FREE vs VIP SUPPORT",
                    callback_data="admin:free_vs_vip_support",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔴 CHANGE LIVE BETS HEADING",
                    callback_data="admin:live_bets_heading",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 CHANGE LIVE BETS INFO",
                    callback_data="admin:live_bets_info",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🖼 CHANGE LIVE BETS MEDIA",
                    callback_data="admin:live_bets_media",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎯 CHANGE PRE-MATCH HEADING",
                    callback_data="admin:pre_match_bets_heading",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 CHANGE PRE-MATCH INFO",
                    callback_data="admin:pre_match_bets_info",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🖼 CHANGE PRE-MATCH MEDIA",
                    callback_data="admin:pre_match_bets_media",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ BACK TO ADMIN",
                    callback_data="admin:home",
                )
            ],
        ]
    )

    description = settings.description or "Not configured"

    await callback.message.answer(
        "🧩 <b>VIP MENU SETTINGS</b>\n\n"
        f"<b>Heading:</b>\n{settings.heading}\n\n"
        f"<b>Description:</b>\n{description}\n\n"
        f"<b>Footer:</b>\n{settings.footer_text}",
        reply_markup=keyboard,
    )

    await callback.answer()


@router.callback_query(F.data == "admin:vip_menu_heading")
async def handle_change_vip_menu_heading(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Unauthorized",
            show_alert=True,
        )
        return

    await state.set_state(
        VipSettingsStates.waiting_for_vip_menu_heading
    )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "✏️ <b>CHANGE VIP MENU HEADING</b>\n\n"
            "Send the new heading.\n\n"
            "Example:\n"
            "<code>WHICH VIP EXPERIENCE INTERESTS YOU MOST?</code>"
        )

    await callback.answer()


@router.message(VipSettingsStates.waiting_for_vip_menu_heading)
async def save_vip_menu_heading(
    message: Message,
    state: FSMContext,
    vip_menu_settings_service: VipMenuSettingsService,
) -> None:
    if message.from_user is None:
        await state.clear()
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        return

    heading = (message.text or "").strip()

    if not heading:
        await message.answer("❌ Heading cannot be empty.")
        return

    if len(heading) > 255:
        await message.answer(
            "❌ Heading is too long. Maximum 255 characters."
        )
        return

    current = await vip_menu_settings_service.get()

    if current is None:
        await state.clear()
        await message.answer("❌ VIP menu settings not found.")
        return

    updated = await vip_menu_settings_service.update(
        heading=heading,
        description=current.description,
        footer_text=current.footer_text,
        free_vs_vip_heading=current.free_vs_vip_heading,
        free_vs_vip_info=current.free_vs_vip_info,
        free_vs_vip_promo_code=current.free_vs_vip_promo_code,
        free_vs_vip_support_username=current.free_vs_vip_support_username,
        compare_heading=current.compare_heading,
        compare_intro=current.compare_intro,
        live_bets_heading=current.live_bets_heading,
        live_bets_info=current.live_bets_info,
        pre_match_bets_heading=current.pre_match_bets_heading,
        pre_match_bets_info=current.pre_match_bets_info,
    )

    if not updated:
        await state.clear()
        await message.answer("❌ Could not update VIP menu heading.")
        return

    await state.clear()

    await message.answer(
        "✅ <b>VIP MENU HEADING UPDATED</b>\n\n"
        f"{escape(heading)}"
    )


@router.callback_query(F.data == "admin:vip_menu_description")
async def handle_change_vip_menu_description(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Unauthorized",
            show_alert=True,
        )
        return

    await state.set_state(
        VipSettingsStates.waiting_for_vip_menu_description
    )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "📝 <b>CHANGE VIP MENU DESCRIPTION</b>\n\n"
            "Send the new description."
        )

    await callback.answer()


@router.message(VipSettingsStates.waiting_for_vip_menu_description)
async def save_vip_menu_description(
    message: Message,
    state: FSMContext,
    vip_menu_settings_service: VipMenuSettingsService,
) -> None:
    if message.from_user is None:
        await state.clear()
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        return

    description = (message.text or "").strip()

    if not description:
        await message.answer("❌ Description cannot be empty.")
        return

    if len(description) > 4000:
        await message.answer(
            "❌ Description is too long. Maximum 4000 characters."
        )
        return

    current = await vip_menu_settings_service.get()

    if current is None:
        await state.clear()
        await message.answer("❌ VIP menu settings not found.")
        return

    updated = await vip_menu_settings_service.update(
        heading=current.heading,
        description=description,
        footer_text=current.footer_text,
        free_vs_vip_heading=current.free_vs_vip_heading,
        free_vs_vip_info=current.free_vs_vip_info,
        free_vs_vip_promo_code=current.free_vs_vip_promo_code,
        free_vs_vip_support_username=current.free_vs_vip_support_username,
        compare_heading=current.compare_heading,
        compare_intro=current.compare_intro,
        live_bets_heading=current.live_bets_heading,
        live_bets_info=current.live_bets_info,
        pre_match_bets_heading=current.pre_match_bets_heading,
        pre_match_bets_info=current.pre_match_bets_info,
    )

    if not updated:
        await state.clear()
        await message.answer("❌ Could not update VIP menu description.")
        return

    await state.clear()

    await message.answer(
        "✅ <b>VIP MENU DESCRIPTION UPDATED</b>\n\n"
        f"{escape(description)}"
    )


@router.callback_query(F.data == "admin:vip_menu_footer")
async def handle_change_vip_menu_footer(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Unauthorized",
            show_alert=True,
        )
        return

    await state.set_state(
        VipSettingsStates.waiting_for_vip_menu_footer
    )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "👇 <b>CHANGE VIP MENU FOOTER</b>\n\n"
            "Send the new footer text.\n\n"
            "Example:\n"
            "<code>Tap any option below 👇</code>"
        )

    await callback.answer()


@router.message(VipSettingsStates.waiting_for_vip_menu_footer)
async def save_vip_menu_footer(
    message: Message,
    state: FSMContext,
    vip_menu_settings_service: VipMenuSettingsService,
) -> None:
    if message.from_user is None:
        await state.clear()
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        return

    footer_text = (message.text or "").strip()

    if not footer_text:
        await message.answer("❌ Footer text cannot be empty.")
        return

    if len(footer_text) > 255:
        await message.answer(
            "❌ Footer text is too long. Maximum 255 characters."
        )
        return

    current = await vip_menu_settings_service.get()

    if current is None:
        await state.clear()
        await message.answer("❌ VIP menu settings not found.")
        return

    updated = await vip_menu_settings_service.update(
        heading=current.heading,
        description=current.description,
        footer_text=footer_text,
        free_vs_vip_heading=current.free_vs_vip_heading,
        free_vs_vip_info=current.free_vs_vip_info,
        free_vs_vip_promo_code=current.free_vs_vip_promo_code,
        free_vs_vip_support_username=current.free_vs_vip_support_username,
        compare_heading=current.compare_heading,
        compare_intro=current.compare_intro,
        live_bets_heading=current.live_bets_heading,
        live_bets_info=current.live_bets_info,
        pre_match_bets_heading=current.pre_match_bets_heading,
        pre_match_bets_info=current.pre_match_bets_info,
    )

    if not updated:
        await state.clear()
        await message.answer("❌ Could not update VIP menu footer.")
        return

    await state.clear()

    await message.answer(
        "✅ <b>VIP MENU FOOTER UPDATED</b>\n\n"
        f"{escape(footer_text)}"
    )


@router.callback_query(F.data.startswith("admin:vip_name:"))
async def handle_vip_name_change(
    callback: CallbackQuery,
    state: FSMContext,
    vip_category_service: VipCategoryService,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Unauthorized",
            show_alert=True,
        )
        return

    if callback.data is None:
        return

    raw_category_id = callback.data.removeprefix(
        "admin:vip_name:"
    )

    try:
        category_id = int(raw_category_id)
    except ValueError:
        await callback.answer(
            "Invalid VIP category",
            show_alert=True,
        )
        return

    category = await vip_category_service.get_by_id(
        category_id=category_id,
    )

    if category is None:
        await callback.answer(
            "VIP category not found",
            show_alert=True,
        )
        return

    await state.set_state(
        VipSettingsStates.waiting_for_display_name
    )

    await state.update_data(
        vip_category_id=category_id,
    )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "✏️ <b>CHANGE VIP NAME</b>\n\n"
            f"Current name: <b>{escape(category.display_name)}</b>\n\n"
            "Send the new VIP name.\n\n"
            "Example:\n"
            "<code>SPIDY PRO VIP</code>"
        )

    await callback.answer()


@router.message(VipSettingsStates.waiting_for_display_name)
async def save_vip_display_name(
    message: Message,
    state: FSMContext,
    vip_category_service: VipCategoryService,
) -> None:
    if message.from_user is None:
        await state.clear()
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        return

    display_name = (message.text or "").strip()

    if not display_name:
        await message.answer("❌ VIP name cannot be empty.")
        return

    if len(display_name) > 128:
        await message.answer(
            "❌ VIP name is too long. Maximum 128 characters."
        )
        return

    data = await state.get_data()
    category_id = data.get("vip_category_id")

    if not isinstance(category_id, int):
        await state.clear()
        await message.answer("❌ VIP category session expired.")
        return

    updated = await vip_category_service.update_display_name(
        category_id=category_id,
        display_name=display_name,
    )

    if not updated:
        await state.clear()
        await message.answer("❌ Could not update VIP name.")
        return

    await state.clear()

    await message.answer(
        "✅ <b>VIP NAME UPDATED</b>\n\n"
        f"New name: <b>{escape(display_name)}</b>"
    )


@router.callback_query(F.data == "admin:vip_add")
async def handle_add_new_vip(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Unauthorized",
            show_alert=True,
        )
        return

    await state.set_state(
        VipSettingsStates.waiting_for_new_vip_name
    )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "➕ <b>ADD NEW VIP</b>\n\n"
            "Send the name of the new VIP.\n\n"
            "Examples:\n"
            "<code>MEGA VIP</code>\n"
            "<code>ULTRA VIP</code>\n"
            "<code>CHAMPIONS VIP</code>"
        )

    await callback.answer()


@router.message(VipSettingsStates.waiting_for_new_vip_name)
async def save_new_vip(
    message: Message,
    state: FSMContext,
) -> None:
    if message.from_user is None:
        await state.clear()
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ You are not authorized.")
        return

    display_name = (message.text or "").strip()

    if not display_name:
        await message.answer(
            "❌ VIP name cannot be empty."
        )
        return

    if len(display_name) > 128:
        await message.answer(
            "❌ VIP name is too long. Maximum 128 characters."
        )
        return

    await state.update_data(
        new_vip_display_name=display_name,
    )

    await state.set_state(
        VipSettingsStates.waiting_for_new_vip_code
    )

    await message.answer(
        "🔑 <b>ENTER VIP CODE</b>\n\n"
        "Enter a unique internal code for this VIP.\n\n"
        "Use lowercase letters, numbers and underscores.\n\n"
        "Example:\n"
        "<code>platinum</code>"
    )


@router.callback_query(F.data.startswith("admin:vip_deactivate:"))
async def handle_vip_deactivate_confirm(
    callback: CallbackQuery,
    vip_category_service: VipCategoryService,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer("⛔ Unauthorized", show_alert=True)
        return

    if callback.data is None:
        return

    raw_category_id = callback.data.removeprefix(
        "admin:vip_deactivate:"
    )

    try:
        category_id = int(raw_category_id)
    except ValueError:
        await callback.answer(
            "Invalid VIP category",
            show_alert=True,
        )
        return

    category = await vip_category_service.get_by_id(
        category_id=category_id,
    )

    if category is None:
        await callback.answer(
            "VIP category not found",
            show_alert=True,
        )
        return

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "⚠️ <b>DEACTIVATE VIP?</b>\n\n"
            f"VIP: <b>{escape(category.display_name)}</b>\n\n"
            "This will hide it from VIP Options.\n"
            "Existing database history will stay safe.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ YES, DEACTIVATE",
                            callback_data=(
                                f"admin:vip_deactivate_confirm:{category.id}"
                            ),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="❌ CANCEL",
                            callback_data=(
                                f"admin:vip_settings:{category.id}"
                            ),
                        )
                    ],
                ]
            ),
        )

    await callback.answer()


@router.callback_query(
    F.data.startswith("admin:vip_deactivate_confirm:")
)
async def handle_vip_deactivate(
    callback: CallbackQuery,
    vip_category_service: VipCategoryService,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer("⛔ Unauthorized", show_alert=True)
        return

    if callback.data is None:
        return

    raw_category_id = callback.data.removeprefix(
        "admin:vip_deactivate_confirm:"
    )

    try:
        category_id = int(raw_category_id)
    except ValueError:
        await callback.answer(
            "Invalid VIP category",
            show_alert=True,
        )
        return

    updated = await vip_category_service.set_active(
        category_id=category_id,
        is_active=False,
    )

    if not updated:
        await callback.answer(
            "Could not deactivate VIP",
            show_alert=True,
        )
        return

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "✅ <b>VIP DEACTIVATED</b>\n\n"
            "It is now hidden from user VIP Options.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="⚙️ BACK TO VIP SETTINGS",
                            callback_data="admin:vip_settings",
                        )
                    ]
                ]
            ),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("admin:vip_reactivate:"))
async def handle_vip_reactivate(
    callback: CallbackQuery,
    vip_category_service: VipCategoryService,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Unauthorized",
            show_alert=True,
        )
        return

    if callback.data is None:
        return

    raw_category_id = callback.data.removeprefix(
        "admin:vip_reactivate:"
    )

    try:
        category_id = int(raw_category_id)
    except ValueError:
        await callback.answer(
            "Invalid VIP category",
            show_alert=True,
        )
        return

    category = await vip_category_service.get_any_by_id(
        category_id=category_id,
    )

    if category is None:
        await callback.answer(
            "VIP category not found",
            show_alert=True,
        )
        return

    updated = await vip_category_service.set_active(
        category_id=category_id,
        is_active=True,
    )

    if not updated:
        await callback.answer(
            "Could not reactivate VIP",
            show_alert=True,
        )
        return

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "✅ <b>VIP REACTIVATED</b>\n\n"
            f"<b>{escape(category.display_name)}</b> is active again.\n\n"
            "It will now appear in user VIP Options.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="⚙️ BACK TO VIP SETTINGS",
                            callback_data="admin:vip_settings",
                        )
                    ]
                ]
            ),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("admin:vip_move_up:"))
async def handle_vip_move_up(
    callback: CallbackQuery,
    vip_category_service: VipCategoryService,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer("⛔ Unauthorized", show_alert=True)
        return

    if callback.data is None:
        return

    raw_category_id = callback.data.removeprefix(
        "admin:vip_move_up:"
    )

    try:
        category_id = int(raw_category_id)
    except ValueError:
        await callback.answer(
            "Invalid VIP category",
            show_alert=True,
        )
        return

    moved = await vip_category_service.move(
        category_id=category_id,
        direction="up",
    )

    if not moved:
        await callback.answer(
            "VIP is already at the top.",
            show_alert=True,
        )
        return

    await callback.answer("✅ VIP moved up")

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "✅ VIP order updated.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="⚙️ BACK TO VIP SETTINGS",
                            callback_data="admin:vip_settings",
                        )
                    ]
                ]
            ),
        )


@router.callback_query(F.data.startswith("admin:vip_move_down:"))
async def handle_vip_move_down(
    callback: CallbackQuery,
    vip_category_service: VipCategoryService,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer("⛔ Unauthorized", show_alert=True)
        return

    if callback.data is None:
        return

    raw_category_id = callback.data.removeprefix(
        "admin:vip_move_down:"
    )

    try:
        category_id = int(raw_category_id)
    except ValueError:
        await callback.answer(
            "Invalid VIP category",
            show_alert=True,
        )
        return

    moved = await vip_category_service.move(
        category_id=category_id,
        direction="down",
    )

    if not moved:
        await callback.answer(
            "VIP is already at the bottom.",
            show_alert=True,
        )
        return

    await callback.answer("✅ VIP moved down")

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "✅ VIP order updated.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="⚙️ BACK TO VIP SETTINGS",
                            callback_data="admin:vip_settings",
                        )
                    ]
                ]
            ),
        )


@router.callback_query(F.data.startswith("admin:vip_compare_info:"))
async def handle_vip_compare_info_change(
    callback: CallbackQuery,
    state: FSMContext,
    vip_category_service: VipCategoryService,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Unauthorized",
            show_alert=True,
        )
        return

    if callback.data is None:
        return

    raw_category_id = callback.data.removeprefix(
        "admin:vip_compare_info:"
    )

    try:
        category_id = int(raw_category_id)
    except ValueError:
        await callback.answer(
            "Invalid VIP category",
            show_alert=True,
        )
        return

    category = await vip_category_service.get_any_by_id(
        category_id=category_id,
    )

    if category is None:
        await callback.answer(
            "VIP category not found",
            show_alert=True,
        )
        return

    await state.set_state(
        VipSettingsStates.waiting_for_compare_info
    )
    await state.update_data(
        vip_category_id=category_id,
    )

    if isinstance(callback.message, Message):
        current_info = (
            escape(category.compare_info)
            if category.compare_info
            else "Not set yet"
        )

        await callback.message.answer(
            "📊 <b>SEND COMPARE INFO</b>\n\n"
            f"<b>VIP:</b> {escape(category.display_name)}\n\n"
            f"<b>Current compare info:</b>\n{current_info}\n\n"
            "Send the comparison description you want users to see "
            "for this VIP on the Compare VIP screen.\n\n"
            "You can use multiple lines."
        )

    await callback.answer()


@router.message(VipSettingsStates.waiting_for_compare_info)
async def handle_vip_compare_info_input(
    message: Message,
    state: FSMContext,
    vip_category_service: VipCategoryService,
) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ You are not authorized.")
        return

    if message.text is None:
        await message.answer(
            "❌ Please send the compare info as text."
        )
        return

    compare_info = message.text.strip()

    if not compare_info:
        await message.answer(
            "❌ Compare info cannot be empty."
        )
        return

    if len(compare_info) > 4000:
        await message.answer(
            "❌ Compare info is too long. Maximum 4000 characters."
        )
        return

    data = await state.get_data()
    category_id = data.get("vip_category_id")

    if not isinstance(category_id, int):
        await state.clear()
        await message.answer(
            "❌ VIP category state is invalid. Please try again."
        )
        return

    updated = await vip_category_service.update_compare_info(
        category_id=category_id,
        compare_info=compare_info,
    )

    if not updated:
        await state.clear()
        await message.answer(
            "❌ VIP compare info could not be updated."
        )
        return

    await state.clear()

    await message.answer(
        "✅ <b>VIP COMPARE INFO UPDATED</b>\n\n"
        f"{escape(compare_info)}"
    )


@router.callback_query(F.data == "admin:compare_heading")
async def handle_compare_heading_change(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer("⛔ Unauthorized", show_alert=True)
        return

    await state.set_state(
        VipSettingsStates.waiting_for_compare_heading
    )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "📊 <b>CHANGE COMPARE HEADING</b>\n\n"
            "Send the new Compare VIP heading."
        )

    await callback.answer()


@router.message(VipSettingsStates.waiting_for_compare_heading)
async def handle_compare_heading_input(
    message: Message,
    state: FSMContext,
    vip_menu_settings_service: VipMenuSettingsService,
) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ You are not authorized.")
        return

    heading = (message.text or "").strip()

    if not heading:
        await message.answer("❌ Heading cannot be empty.")
        return

    if len(heading) > 255:
        await message.answer(
            "❌ Heading is too long. Maximum 255 characters."
        )
        return

    current = await vip_menu_settings_service.get()

    if current is None:
        await state.clear()
        await message.answer("❌ VIP menu settings not found.")
        return

    updated = await vip_menu_settings_service.update(
        heading=current.heading,
        description=current.description,
        footer_text=current.footer_text,
        free_vs_vip_heading=current.free_vs_vip_heading,
        free_vs_vip_info=current.free_vs_vip_info,
        free_vs_vip_promo_code=current.free_vs_vip_promo_code,
        free_vs_vip_support_username=current.free_vs_vip_support_username,
        compare_heading=heading,
        compare_intro=current.compare_intro,
        live_bets_heading=current.live_bets_heading,
        live_bets_info=current.live_bets_info,
        pre_match_bets_heading=current.pre_match_bets_heading,
        pre_match_bets_info=current.pre_match_bets_info,
    )

    await state.clear()

    if not updated:
        await message.answer("❌ Could not update Compare heading.")
        return

    await message.answer(
        "✅ <b>COMPARE HEADING UPDATED</b>\n\n"
        f"{escape(heading)}"
    )


@router.callback_query(F.data == "admin:compare_intro")
async def handle_compare_intro_change(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer("⛔ Unauthorized", show_alert=True)
        return

    await state.set_state(
        VipSettingsStates.waiting_for_compare_intro
    )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "📝 <b>CHANGE COMPARE INTRO</b>\n\n"
            "Send the intro text shown above the VIP comparison."
        )

    await callback.answer()


@router.message(VipSettingsStates.waiting_for_compare_intro)
async def handle_compare_intro_input(
    message: Message,
    state: FSMContext,
    vip_menu_settings_service: VipMenuSettingsService,
) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ You are not authorized.")
        return

    intro = (message.text or "").strip()

    if not intro:
        await message.answer("❌ Compare intro cannot be empty.")
        return

    if len(intro) > 4000:
        await message.answer(
            "❌ Compare intro is too long. Maximum 4000 characters."
        )
        return

    current = await vip_menu_settings_service.get()

    if current is None:
        await state.clear()
        await message.answer("❌ VIP menu settings not found.")
        return

    updated = await vip_menu_settings_service.update(
        heading=current.heading,
        description=current.description,
        footer_text=current.footer_text,
        free_vs_vip_heading=current.free_vs_vip_heading,
        free_vs_vip_info=current.free_vs_vip_info,
        free_vs_vip_promo_code=current.free_vs_vip_promo_code,
        free_vs_vip_support_username=current.free_vs_vip_support_username,
        compare_heading=current.compare_heading,
        compare_intro=intro,
        live_bets_heading=current.live_bets_heading,
        live_bets_info=current.live_bets_info,
        pre_match_bets_heading=current.pre_match_bets_heading,
        pre_match_bets_info=current.pre_match_bets_info,
    )

    await state.clear()

    if not updated:
        await message.answer("❌ Could not update Compare intro.")
        return

    await message.answer(
        "✅ <b>COMPARE INTRO UPDATED</b>\n\n"
        f"{escape(intro)}"
    )


@router.callback_query(F.data == "admin:free_vs_vip_heading")
async def handle_free_vs_vip_heading_change(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer("⛔ Unauthorized", show_alert=True)
        return

    await state.set_state(
        VipSettingsStates.waiting_for_free_vs_vip_heading
    )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "🆚 <b>CHANGE FREE vs VIP HEADING</b>\n\n"
            "Send the new heading."
        )

    await callback.answer()


@router.message(VipSettingsStates.waiting_for_free_vs_vip_heading)
async def handle_free_vs_vip_heading_input(
    message: Message,
    state: FSMContext,
    vip_menu_settings_service: VipMenuSettingsService,
) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ You are not authorized.")
        return

    value = (message.text or "").strip()

    if not value:
        await message.answer("❌ Heading cannot be empty.")
        return

    if len(value) > 255:
        await message.answer("❌ Maximum 255 characters.")
        return

    current = await vip_menu_settings_service.get()

    if current is None:
        await state.clear()
        await message.answer("❌ VIP menu settings not found.")
        return

    updated = await vip_menu_settings_service.update(
        heading=current.heading,
        description=current.description,
        footer_text=current.footer_text,
        free_vs_vip_heading=value,
        free_vs_vip_info=current.free_vs_vip_info,
        free_vs_vip_promo_code=current.free_vs_vip_promo_code,
        free_vs_vip_support_username=current.free_vs_vip_support_username,
        compare_heading=current.compare_heading,
        compare_intro=current.compare_intro,
        live_bets_heading=current.live_bets_heading,
        live_bets_info=current.live_bets_info,
        pre_match_bets_heading=current.pre_match_bets_heading,
        pre_match_bets_info=current.pre_match_bets_info,
    )

    await state.clear()

    if not updated:
        await message.answer("❌ Could not update heading.")
        return

    await message.answer(
        "✅ <b>FREE vs VIP HEADING UPDATED</b>\n\n"
        f"{escape(value)}"
    )


@router.callback_query(F.data == "admin:free_vs_vip_info")
async def handle_free_vs_vip_info_change(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer("⛔ Unauthorized", show_alert=True)
        return

    await state.set_state(
        VipSettingsStates.waiting_for_free_vs_vip_info
    )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "📝 <b>CHANGE FREE vs VIP INFO</b>\n\n"
            "Send the full Free vs VIP information.\n\n"
            "Multiple lines are allowed."
        )

    await callback.answer()


@router.message(VipSettingsStates.waiting_for_free_vs_vip_info)
async def handle_free_vs_vip_info_input(
    message: Message,
    state: FSMContext,
    vip_menu_settings_service: VipMenuSettingsService,
) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ You are not authorized.")
        return

    value = (message.text or "").strip()

    if not value:
        await message.answer("❌ Info cannot be empty.")
        return

    if len(value) > 4000:
        await message.answer("❌ Maximum 4000 characters.")
        return

    current = await vip_menu_settings_service.get()

    if current is None:
        await state.clear()
        await message.answer("❌ VIP menu settings not found.")
        return

    updated = await vip_menu_settings_service.update(
        heading=current.heading,
        description=current.description,
        footer_text=current.footer_text,
        free_vs_vip_heading=current.free_vs_vip_heading,
        free_vs_vip_info=value,
        free_vs_vip_promo_code=current.free_vs_vip_promo_code,
        free_vs_vip_support_username=current.free_vs_vip_support_username,
        compare_heading=current.compare_heading,
        compare_intro=current.compare_intro,
        live_bets_heading=current.live_bets_heading,
        live_bets_info=current.live_bets_info,
        pre_match_bets_heading=current.pre_match_bets_heading,
        pre_match_bets_info=current.pre_match_bets_info,
    )

    await state.clear()

    if not updated:
        await message.answer("❌ Could not update Free vs VIP info.")
        return

    await message.answer(
        "✅ <b>FREE vs VIP INFO UPDATED</b>"
    )


@router.callback_query(F.data == "admin:free_vs_vip_promo")
async def handle_free_vs_vip_promo_change(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer("⛔ Unauthorized", show_alert=True)
        return

    await state.set_state(
        VipSettingsStates.waiting_for_free_vs_vip_promo
    )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "🎁 <b>CHANGE FREE vs VIP PROMO CODE</b>\n\n"
            "Send the promo code."
        )

    await callback.answer()


@router.message(VipSettingsStates.waiting_for_free_vs_vip_promo)
async def handle_free_vs_vip_promo_input(
    message: Message,
    state: FSMContext,
    vip_menu_settings_service: VipMenuSettingsService,
) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ You are not authorized.")
        return

    value = (message.text or "").strip()

    if not value:
        await message.answer("❌ Promo code cannot be empty.")
        return

    if len(value) > 128:
        await message.answer("❌ Maximum 128 characters.")
        return

    current = await vip_menu_settings_service.get()

    if current is None:
        await state.clear()
        await message.answer("❌ VIP menu settings not found.")
        return

    updated = await vip_menu_settings_service.update(
        heading=current.heading,
        description=current.description,
        footer_text=current.footer_text,
        free_vs_vip_heading=current.free_vs_vip_heading,
        free_vs_vip_info=current.free_vs_vip_info,
        free_vs_vip_promo_code=value,
        free_vs_vip_support_username=current.free_vs_vip_support_username,
        compare_heading=current.compare_heading,
        compare_intro=current.compare_intro,
        live_bets_heading=current.live_bets_heading,
        live_bets_info=current.live_bets_info,
        pre_match_bets_heading=current.pre_match_bets_heading,
        pre_match_bets_info=current.pre_match_bets_info,
    )

    await state.clear()

    if not updated:
        await message.answer("❌ Could not update promo code.")
        return

    await message.answer(
        "✅ <b>PROMO CODE UPDATED</b>\n\n"
        f"<code>{escape(value)}</code>"
    )


@router.callback_query(F.data == "admin:free_vs_vip_support")
async def handle_free_vs_vip_support_change(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer("⛔ Unauthorized", show_alert=True)
        return

    await state.set_state(
        VipSettingsStates.waiting_for_free_vs_vip_support
    )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "💬 <b>CHANGE FREE vs VIP SUPPORT</b>\n\n"
            "Send Telegram username.\n"
            "Example: <code>spidysupport</code>"
        )

    await callback.answer()


@router.message(VipSettingsStates.waiting_for_free_vs_vip_support)
async def handle_free_vs_vip_support_input(
    message: Message,
    state: FSMContext,
    vip_menu_settings_service: VipMenuSettingsService,
) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ You are not authorized.")
        return

    value = (message.text or "").strip().lstrip("@")

    if not value:
        await message.answer("❌ Username cannot be empty.")
        return

    if len(value) > 32 or not value.replace("_", "").isalnum():
        await message.answer(
            "❌ Invalid Telegram username."
        )
        return

    current = await vip_menu_settings_service.get()

    if current is None:
        await state.clear()
        await message.answer("❌ VIP menu settings not found.")
        return

    updated = await vip_menu_settings_service.update(
        heading=current.heading,
        description=current.description,
        footer_text=current.footer_text,
        free_vs_vip_heading=current.free_vs_vip_heading,
        free_vs_vip_info=current.free_vs_vip_info,
        free_vs_vip_promo_code=current.free_vs_vip_promo_code,
        free_vs_vip_support_username=value,
        compare_heading=current.compare_heading,
        compare_intro=current.compare_intro,
        live_bets_heading=current.live_bets_heading,
        live_bets_info=current.live_bets_info,
        pre_match_bets_heading=current.pre_match_bets_heading,
        pre_match_bets_info=current.pre_match_bets_info,
    )

    await state.clear()

    if not updated:
        await message.answer("❌ Could not update support username.")
        return

    await message.answer(
        "✅ <b>FREE vs VIP SUPPORT UPDATED</b>\n\n"
        f"@{escape(value)}"
    )




@router.message(VipSettingsStates.waiting_for_new_vip_code)
async def handle_new_vip_code_input(
    message: Message,
    state: FSMContext,
    vip_category_service: VipCategoryService,
) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer(
            "⛔ You are not authorized."
        )
        return

    code = (message.text or "").strip().lower()

    if not code:
        await message.answer(
            "❌ VIP code cannot be empty."
        )
        return

    if len(code) > 64:
        await message.answer(
            "❌ VIP code is too long. Maximum 64 characters."
        )
        return

    if not all(
        character.isalnum() or character == "_"
        for character in code
    ):
        await message.answer(
            "❌ Invalid VIP code.\n\n"
            "Use only lowercase letters, numbers and underscores.\n\n"
            "Example: <code>platinum</code>"
        )
        return

    categories = await vip_category_service.list_all()

    if any(category.code == code for category in categories):
        await message.answer(
            "❌ This VIP code already exists.\n\n"
            "Please enter a different code."
        )
        return

    data = await state.get_data()
    display_name = data.get("new_vip_display_name")

    if not isinstance(display_name, str) or not display_name:
        await state.clear()
        await message.answer(
            "❌ VIP name state is missing. Please start again."
        )
        return

    await state.update_data(
        new_vip_code=code,
    )

    await state.set_state(
        VipSettingsStates.waiting_for_new_vip_info
    )

    await message.answer(
        "📝 <b>ENTER VIP INFO</b>\n\n"
        f"VIP: <b>{display_name}</b>\n"
        f"Code: <code>{code}</code>\n\n"
        "Send the information users should see "
        "when they open this VIP.\n\n"
        "Multiple lines are allowed."
    )


@router.message(VipSettingsStates.waiting_for_new_vip_info)
async def handle_new_vip_info_input(
    message: Message,
    state: FSMContext,
) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ You are not authorized.")
        return

    vip_info = (message.text or "").strip()

    if not vip_info:
        await message.answer("❌ VIP info cannot be empty.")
        return

    if len(vip_info) > 4000:
        await message.answer(
            "❌ VIP info is too long. Maximum 4000 characters."
        )
        return

    data = await state.get_data()

    if not isinstance(data.get("new_vip_display_name"), str):
        await state.clear()
        await message.answer(
            "❌ VIP name is missing. Please start again."
        )
        return

    if not isinstance(data.get("new_vip_code"), str):
        await state.clear()
        await message.answer(
            "❌ VIP code is missing. Please start again."
        )
        return

    await state.update_data(
        new_vip_info=vip_info,
    )

    await state.set_state(
        VipSettingsStates.waiting_for_new_vip_compare_info
    )

    await message.answer(
        "📊 <b>ENTER COMPARE INFO</b>\n\n"
        "Send the information that should appear "
        "for this VIP on the Compare VIP screen.\n\n"
        "Multiple lines are allowed."
    )


@router.message(VipSettingsStates.waiting_for_new_vip_compare_info)
async def handle_new_vip_compare_info_input(
    message: Message,
    state: FSMContext,
) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ You are not authorized.")
        return

    compare_info = (message.text or "").strip()

    if not compare_info:
        await message.answer(
            "❌ Compare info cannot be empty."
        )
        return

    if len(compare_info) > 4000:
        await message.answer(
            "❌ Compare info is too long. Maximum 4000 characters."
        )
        return

    data = await state.get_data()

    if not isinstance(data.get("new_vip_display_name"), str):
        await state.clear()
        await message.answer(
            "❌ VIP name is missing. Please start again."
        )
        return

    await state.update_data(
        new_vip_compare_info=compare_info,
    )

    await state.set_state(
        VipSettingsStates.waiting_for_new_vip_registration_url
    )

    await message.answer(
        "🔗 <b>ENTER REGISTRATION LINK</b>\n\n"
        "Send the registration URL for this VIP.\n\n"
        "Example:\n"
        "<code>https://example.com/register</code>\n\n"
        "If there is no registration link, send:\n"
        "<code>skip</code>"
    )


@router.message(VipSettingsStates.waiting_for_new_vip_registration_url)
async def handle_new_vip_registration_url_input(
    message: Message,
    state: FSMContext,
) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ You are not authorized.")
        return

    value = (message.text or "").strip()

    if not value:
        await message.answer(
            "❌ Registration link cannot be empty.\n\n"
            "Send a URL or type <code>skip</code>."
        )
        return

    if value.lower() == "skip":
        registration_url = None
    else:
        if len(value) > 2000:
            await message.answer(
                "❌ Registration link is too long."
            )
            return

        if not (
            value.startswith("http://")
            or value.startswith("https://")
        ):
            await message.answer(
                "❌ Invalid registration link.\n\n"
                "The link must start with http:// or https://\n\n"
                "Or type <code>skip</code>."
            )
            return

        registration_url = value

    await state.update_data(
        new_vip_registration_url=registration_url,
    )

    await state.set_state(
        VipSettingsStates.waiting_for_new_vip_promo_code
    )

    await message.answer(
        "🎁 <b>ENTER PROMO CODE</b>\n\n"
        "Send the promo code users should use for this VIP.\n\n"
        "If there is no promo code, type:\n"
        "<code>skip</code>"
    )


@router.message(VipSettingsStates.waiting_for_new_vip_promo_code)
async def handle_new_vip_promo_code_input(
    message: Message,
    state: FSMContext,
) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ You are not authorized.")
        return

    value = (message.text or "").strip()

    if not value:
        await message.answer(
            "❌ Promo code cannot be empty.\n\n"
            "Send a promo code or type <code>skip</code>."
        )
        return

    promo_code = None if value.lower() == "skip" else value

    if promo_code is not None and len(promo_code) > 255:
        await message.answer(
            "❌ Promo code is too long. Maximum 255 characters."
        )
        return

    await state.update_data(
        new_vip_promo_code=promo_code,
    )

    await state.set_state(
        VipSettingsStates.waiting_for_new_vip_support_username
    )

    await message.answer(
        "👤 <b>ENTER VIP SUPPORT USERNAME</b>\n\n"
        "Send the Telegram username for VIP support.\n\n"
        "Example:\n"
        "<code>vip_support</code>\n\n"
        "You can include or omit @.\n\n"
        "If there is no support username, type:\n"
        "<code>skip</code>"
    )


@router.message(VipSettingsStates.waiting_for_new_vip_support_username)
async def handle_new_vip_support_username_input(
    message: Message,
    state: FSMContext,
) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ You are not authorized.")
        return

    value = (message.text or "").strip()

    if not value:
        await message.answer(
            "❌ Username cannot be empty.\n\n"
            "Send a username or type <code>skip</code>."
        )
        return

    if value.lower() == "skip":
        username = None
    else:
        username = value.lstrip("@").strip()

        if (
            not username
            or len(username) > 32
            or not username.replace("_", "").isalnum()
        ):
            await message.answer(
                "❌ Invalid Telegram username.\n\n"
                "Example: <code>vip_support</code>\n"
                "Or type <code>skip</code>."
            )
            return

    await state.update_data(
        new_vip_support_username=username,
    )

    await state.set_state(
        VipSettingsStates.waiting_for_new_vip_media
    )

    await message.answer(
        "🎬 <b>ADD VIP MEDIA</b>\n\n"
        "Send a photo or video for this VIP category.\n\n"
        "If you don't want to add media now, type:\n"
        "<code>skip</code>"
    )


@router.message(VipSettingsStates.waiting_for_new_vip_media)
async def handle_new_vip_media_input(
    message: Message,
    state: FSMContext,
) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ You are not authorized.")
        return

    media_file_id: str | None = None
    media_type: str | None = None

    if message.video is not None:
        media_file_id = message.video.file_id
        media_type = "video"
    elif message.photo:
        media_file_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.text and message.text.strip().lower() == "skip":
        pass
    else:
        await message.answer(
            "❌ Please send a photo or video.\n\n"
            "Or type <code>skip</code>."
        )
        return

    await state.update_data(
        new_vip_media_file_id=media_file_id,
        new_vip_media_type=media_type,
    )

    await state.set_state(
        VipSettingsStates.waiting_for_new_vip_sort_order
    )

    await message.answer(
        "🔢 <b>ENTER SORT ORDER</b>\n\n"
        "Enter a number to control where this VIP appears.\n\n"
        "Example:\n"
        "<code>40</code>\n\n"
        "Lower numbers appear first."
    )


@router.message(VipSettingsStates.waiting_for_new_vip_sort_order)
async def handle_new_vip_sort_order_input(
    message: Message,
    state: FSMContext,
    vip_category_service: VipCategoryService,
) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ You are not authorized.")
        return

    value = (message.text or "").strip()

    try:
        sort_order = int(value)
    except ValueError:
        await message.answer(
            "❌ Sort order must be a whole number.\n\n"
            "Example: <code>40</code>"
        )
        return

    if sort_order < 0 or sort_order > 9999:
        await message.answer(
            "❌ Sort order must be between 0 and 9999."
        )
        return

    data = await state.get_data()

    code = data.get("new_vip_code")
    display_name = data.get("new_vip_display_name")
    vip_info = data.get("new_vip_info")
    compare_info = data.get("new_vip_compare_info")
    registration_url = data.get("new_vip_registration_url")
    promo_code = data.get("new_vip_promo_code")
    support_username = data.get("new_vip_support_username")
    media_file_id = data.get("new_vip_media_file_id")
    media_type = data.get("new_vip_media_type")

    if not isinstance(code, str) or not code:
        await state.clear()
        await message.answer(
            "❌ VIP code is missing. Please start again."
        )
        return

    if not isinstance(display_name, str) or not display_name:
        await state.clear()
        await message.answer(
            "❌ VIP name is missing. Please start again."
        )
        return

    if not isinstance(vip_info, str) or not vip_info:
        await state.clear()
        await message.answer(
            "❌ VIP info is missing. Please start again."
        )
        return

    if not isinstance(compare_info, str) or not compare_info:
        await state.clear()
        await message.answer(
            "❌ Compare info is missing. Please start again."
        )
        return

    if registration_url is not None and not isinstance(
        registration_url, str
    ):
        registration_url = None

    if promo_code is not None and not isinstance(
        promo_code, str
    ):
        promo_code = None

    if support_username is not None and not isinstance(
        support_username, str
    ):
        support_username = None

    if media_file_id is not None and not isinstance(
        media_file_id, str
    ):
        media_file_id = None

    if media_type is not None and not isinstance(
        media_type, str
    ):
        media_type = None

    await state.update_data(
        new_vip_sort_order=sort_order,
    )

    await message.answer(
        "⏳ <b>CREATING VIP...</b>"
    )

    try:
        created = await vip_category_service.create(
            code=code,
            display_name=display_name,
            name_key=code,
            sort_order=sort_order,
            vip_info=vip_info,
            compare_info=compare_info,
            registration_url=registration_url,
            promo_code=promo_code,
            support_username=support_username,
            media_file_id=media_file_id,
            media_type=media_type,
        )
    except Exception:
        await state.clear()
        await message.answer(
            "❌ Could not create the VIP.\n\n"
            "Please check that the VIP code is unique "
            "and try again."
        )
        return

    if not created:
        await state.clear()
        await message.answer(
            "❌ VIP could not be created."
        )
        return

    await state.clear()

    await message.answer(
        "✅ <b>NEW VIP CREATED</b>\n\n"
        f"👑 Name: <b>{display_name}</b>\n"
        f"🔑 Code: <code>{code}</code>\n"
        f"🔢 Sort Order: <code>{sort_order}</code>\n\n"
        "The VIP is now active and will appear in "
        "VIP OPTIONS."
    )


@router.callback_query(F.data == "admin:live_bets_heading")
async def handle_live_bets_heading_change(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer("⛔ Unauthorized", show_alert=True)
        return

    await state.set_state(VipSettingsStates.waiting_for_live_bets_heading)

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "🔴 <b>CHANGE LIVE BETS HEADING</b>\n\n"
            "Send the new Live Bets heading."
        )

    await callback.answer()


@router.message(VipSettingsStates.waiting_for_live_bets_heading)
async def handle_live_bets_heading_input(
    message: Message,
    state: FSMContext,
    vip_menu_settings_service: VipMenuSettingsService,
) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ You are not authorized.")
        return

    value = (message.text or "").strip()

    if not value:
        await message.answer("❌ Heading cannot be empty.")
        return

    if len(value) > 255:
        await message.answer("❌ Maximum 255 characters.")
        return

    current = await vip_menu_settings_service.get()

    if current is None:
        await state.clear()
        await message.answer("❌ VIP menu settings not found.")
        return

    updated = await vip_menu_settings_service.update(
        heading=current.heading,
        description=current.description,
        footer_text=current.footer_text,
        free_vs_vip_heading=current.free_vs_vip_heading,
        free_vs_vip_info=current.free_vs_vip_info,
        free_vs_vip_promo_code=current.free_vs_vip_promo_code,
        free_vs_vip_support_username=current.free_vs_vip_support_username,
        compare_heading=current.compare_heading,
        compare_intro=current.compare_intro,
        live_bets_heading=value,
        live_bets_info=current.live_bets_info,
        pre_match_bets_heading=current.pre_match_bets_heading,
        pre_match_bets_info=current.pre_match_bets_info,
    )

    await state.clear()

    if not updated:
        await message.answer("❌ Could not update Live Bets heading.")
        return

    await message.answer(
        "✅ <b>LIVE BETS HEADING UPDATED</b>\n\n"
        f"{escape(value)}"
    )


@router.callback_query(F.data == "admin:live_bets_info")
async def handle_live_bets_info_change(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer("⛔ Unauthorized", show_alert=True)
        return

    await state.set_state(VipSettingsStates.waiting_for_live_bets_info)

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "📝 <b>CHANGE LIVE BETS INFO</b>\n\n"
            "Send the Live Bets information.\n\n"
            "Multiple lines are allowed."
        )

    await callback.answer()


@router.message(VipSettingsStates.waiting_for_live_bets_info)
async def handle_live_bets_info_input(
    message: Message,
    state: FSMContext,
    vip_menu_settings_service: VipMenuSettingsService,
) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ You are not authorized.")
        return

    value = (message.text or "").strip()

    if not value:
        await message.answer("❌ Info cannot be empty.")
        return

    if len(value) > 4000:
        await message.answer("❌ Maximum 4000 characters.")
        return

    current = await vip_menu_settings_service.get()

    if current is None:
        await state.clear()
        await message.answer("❌ VIP menu settings not found.")
        return

    updated = await vip_menu_settings_service.update(
        heading=current.heading,
        description=current.description,
        footer_text=current.footer_text,
        free_vs_vip_heading=current.free_vs_vip_heading,
        free_vs_vip_info=current.free_vs_vip_info,
        free_vs_vip_promo_code=current.free_vs_vip_promo_code,
        free_vs_vip_support_username=current.free_vs_vip_support_username,
        compare_heading=current.compare_heading,
        compare_intro=current.compare_intro,
        live_bets_heading=current.live_bets_heading,
        live_bets_info=value,
        pre_match_bets_heading=current.pre_match_bets_heading,
        pre_match_bets_info=current.pre_match_bets_info,
    )

    await state.clear()

    if not updated:
        await message.answer("❌ Could not update Live Bets info.")
        return

    await message.answer("✅ <b>LIVE BETS INFO UPDATED</b>")


@router.callback_query(F.data == "admin:pre_match_bets_heading")
async def handle_pre_match_bets_heading_change(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer("⛔ Unauthorized", show_alert=True)
        return

    await state.set_state(
        VipSettingsStates.waiting_for_pre_match_bets_heading
    )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "🎯 <b>CHANGE PRE-MATCH BETS HEADING</b>\n\n"
            "Send the new Pre-Match Bets heading."
        )

    await callback.answer()


@router.message(VipSettingsStates.waiting_for_pre_match_bets_heading)
async def handle_pre_match_bets_heading_input(
    message: Message,
    state: FSMContext,
    vip_menu_settings_service: VipMenuSettingsService,
) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ You are not authorized.")
        return

    value = (message.text or "").strip()

    if not value:
        await message.answer("❌ Heading cannot be empty.")
        return

    if len(value) > 255:
        await message.answer("❌ Maximum 255 characters.")
        return

    current = await vip_menu_settings_service.get()

    if current is None:
        await state.clear()
        await message.answer("❌ VIP menu settings not found.")
        return

    updated = await vip_menu_settings_service.update(
        heading=current.heading,
        description=current.description,
        footer_text=current.footer_text,
        free_vs_vip_heading=current.free_vs_vip_heading,
        free_vs_vip_info=current.free_vs_vip_info,
        free_vs_vip_promo_code=current.free_vs_vip_promo_code,
        free_vs_vip_support_username=current.free_vs_vip_support_username,
        compare_heading=current.compare_heading,
        compare_intro=current.compare_intro,
        live_bets_heading=current.live_bets_heading,
        live_bets_info=current.live_bets_info,
        pre_match_bets_heading=value,
        pre_match_bets_info=current.pre_match_bets_info,
    )

    await state.clear()

    if not updated:
        await message.answer("❌ Could not update Pre-Match heading.")
        return

    await message.answer(
        "✅ <b>PRE-MATCH BETS HEADING UPDATED</b>\n\n"
        f"{escape(value)}"
    )


@router.callback_query(F.data == "admin:pre_match_bets_info")
async def handle_pre_match_bets_info_change(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer("⛔ Unauthorized", show_alert=True)
        return

    await state.set_state(VipSettingsStates.waiting_for_pre_match_bets_info)

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "📝 <b>CHANGE PRE-MATCH BETS INFO</b>\n\n"
            "Send the Pre-Match Bets information.\n\n"
            "Multiple lines are allowed."
        )

    await callback.answer()


@router.message(VipSettingsStates.waiting_for_pre_match_bets_info)
async def handle_pre_match_bets_info_input(
    message: Message,
    state: FSMContext,
    vip_menu_settings_service: VipMenuSettingsService,
) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ You are not authorized.")
        return

    value = (message.text or "").strip()

    if not value:
        await message.answer("❌ Info cannot be empty.")
        return

    if len(value) > 4000:
        await message.answer("❌ Maximum 4000 characters.")
        return

    current = await vip_menu_settings_service.get()

    if current is None:
        await state.clear()
        await message.answer("❌ VIP menu settings not found.")
        return

    updated = await vip_menu_settings_service.update(
        heading=current.heading,
        description=current.description,
        footer_text=current.footer_text,
        free_vs_vip_heading=current.free_vs_vip_heading,
        free_vs_vip_info=current.free_vs_vip_info,
        free_vs_vip_promo_code=current.free_vs_vip_promo_code,
        free_vs_vip_support_username=current.free_vs_vip_support_username,
        compare_heading=current.compare_heading,
        compare_intro=current.compare_intro,
        live_bets_heading=current.live_bets_heading,
        live_bets_info=current.live_bets_info,
        pre_match_bets_heading=current.pre_match_bets_heading,
        pre_match_bets_info=value,
    )

    await state.clear()

    if not updated:
        await message.answer("❌ Could not update Pre-Match info.")
        return

    await message.answer("✅ <b>PRE-MATCH BETS INFO UPDATED</b>")


@router.callback_query(F.data == "admin:live_bets_media")
async def handle_live_bets_media_change(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer("⛔ Unauthorized", show_alert=True)
        return

    await state.set_state(
        VipSettingsStates.waiting_for_live_bets_media
    )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "🔴 <b>CHANGE LIVE BETS MEDIA</b>\n\n"
            "Send a <b>photo</b> or <b>video</b> now.\n\n"
            "The new media will replace the current Live Bets media."
        )

    await callback.answer()


@router.message(VipSettingsStates.waiting_for_live_bets_media)
async def handle_live_bets_media_upload(
    message: Message,
    state: FSMContext,
    vip_menu_settings_service: VipMenuSettingsService,
) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ You are not authorized.")
        return

    media_file_id: str | None = None
    media_type: str | None = None

    if message.video is not None:
        media_file_id = message.video.file_id
        media_type = "video"
    elif message.photo:
        media_file_id = message.photo[-1].file_id
        media_type = "photo"

    if media_file_id is None or media_type is None:
        await message.answer(
            "❌ Please send a video or photo only."
        )
        return

    updated = await vip_menu_settings_service.update_live_bets_media(
        media_file_id=media_file_id,
        media_type=media_type,
    )

    if not updated:
        await state.clear()
        await message.answer(
            "❌ Could not update Live Bets media."
        )
        return

    await state.clear()

    await message.answer(
        f"✅ <b>LIVE BETS {media_type.upper()} UPDATED</b>\n\n"
        "Users opening Live Bets will now see the new media."
    )


@router.callback_query(F.data == "admin:pre_match_bets_media")
async def handle_pre_match_bets_media_change(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer("⛔ Unauthorized", show_alert=True)
        return

    await state.set_state(
        VipSettingsStates.waiting_for_pre_match_bets_media
    )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "🎯 <b>CHANGE PRE-MATCH BETS MEDIA</b>\n\n"
            "Send a <b>photo</b> or <b>video</b> now.\n\n"
            "The new media will replace the current Pre-Match Bets media."
        )

    await callback.answer()


@router.message(VipSettingsStates.waiting_for_pre_match_bets_media)
async def handle_pre_match_bets_media_upload(
    message: Message,
    state: FSMContext,
    vip_menu_settings_service: VipMenuSettingsService,
) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await state.clear()
        await message.answer("⛔ You are not authorized.")
        return

    media_file_id: str | None = None
    media_type: str | None = None

    if message.video is not None:
        media_file_id = message.video.file_id
        media_type = "video"
    elif message.photo:
        media_file_id = message.photo[-1].file_id
        media_type = "photo"

    if media_file_id is None or media_type is None:
        await message.answer(
            "❌ Please send a video or photo only."
        )
        return

    updated = await vip_menu_settings_service.update_pre_match_bets_media(
        media_file_id=media_file_id,
        media_type=media_type,
    )

    if not updated:
        await state.clear()
        await message.answer(
            "❌ Could not update Pre-Match Bets media."
        )
        return

    await state.clear()

    await message.answer(
        f"✅ <b>PRE-MATCH BETS {media_type.upper()} UPDATED</b>\n\n"
        "Users opening Pre-Match Bets will now see the new media."
    )
