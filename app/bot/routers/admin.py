from html import escape
from zoneinfo import ZoneInfo

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.exceptions import TelegramBadRequest

from app.bot.states.admin_management import AdminManagementStates
from app.bot.states.channel_settings import ChannelSettingsStates
from app.bot.states.content_settings import (
    ContentSettingsStates,
    ReferralSettingsStates,
)
from app.bot.states.daily_pick import DailyPickStates
from app.bot.states.vip_settings import VipSettingsStates
from app.services.admin import AdminService
from app.services.audit_log import AuditLogService
from app.services.channel_settings import ChannelSettingsService
from app.services.content_screen_settings import ContentScreenSettingsService
from app.services.admin_vip import AdminVipService
from app.services.daily_pick import DailyPickService
from app.services.onboarding import OnboardingService
from app.services.referral import ReferralService
from app.services.user import UserService
from app.services.vip_category import VipCategoryService
from app.services.vip_menu_settings import VipMenuSettingsService

router = Router(name="admin")


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
                    text="👥 MANAGE USERS",
                    callback_data="admin:manage_users",
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
            [
                InlineKeyboardButton(
                    text="📝 CONTENT SETTINGS",
                    callback_data="admin:content_settings",
                )
            ],
        ]
    )



def _content_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎯 WINNING TIPS",
                    callback_data="admin:content:winning_tips",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔥 TODAY'S INSIGHTS",
                    callback_data="admin:content:today_insights",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏆 LIVE STATS",
                    callback_data="admin:content:live_stats",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎁 REFER & EARN",
                    callback_data="admin:content:referral",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 REFERRAL STATS",
                    callback_data="admin:referral_stats",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📖 HOW IT WORKS",
                    callback_data="admin:content:how_it_works",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔔 NOTIFICATIONS",
                    callback_data="admin:content:notifications",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💬 SUPPORT",
                    callback_data="admin:content:support",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ BACK",
                    callback_data="admin:back",
                )
            ],
        ]
    )


@router.message(Command("admin"))
async def handle_admin(message: Message) -> None:
    if message.from_user is None:
        return

    await message.answer(
        "🛡 <b>ADMIN PANEL</b>\n\n"
        "✅ Admin access verified.",
        reply_markup=_admin_keyboard(),
    )


@router.callback_query(F.data == "admin:vip_pending")
async def handle_pending_vip_approvals(
    callback: CallbackQuery,
    onboarding_service: OnboardingService,
    user_service: UserService,
) -> None:

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
    if message.from_user is None:
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
    if message.from_user is None:
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
    if message.from_user is None:
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
    if message.from_user is None:
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
    if message.from_user is None:
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
    if message.from_user is None:
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
            "<code>PREMIUM VIP</code>"
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

    await state.set_state(
        VipSettingsStates.waiting_for_free_vs_vip_support
    )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "💬 <b>CHANGE FREE vs VIP SUPPORT</b>\n\n"
            "Send Telegram username.\n"
            "Example: <code>your_support_username</code>"
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


def _owner_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛡 MANAGE ADMINS",
                    callback_data="owner:manage_admins",
                )
            ],
            [
                InlineKeyboardButton(
                    text="➕ ADD ADMIN",
                    callback_data="owner:add_admin",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👑 TRANSFER OWNERSHIP",
                    callback_data="owner:transfer_ownership",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👥 MANAGE USERS",
                    callback_data="owner:manage_users",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 RESET ALL VERIFICATIONS",
                    callback_data="owner:reset_all_confirm",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 AUDIT LOG",
                    callback_data="owner:audit_log",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🌍 TIMEZONE",
                    callback_data="owner:timezone",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📢 CHANNEL SETTINGS",
                    callback_data="owner:channel_settings",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚙️ ADMIN PANEL",
                    callback_data="owner:admin_panel",
                )
            ],
        ]
    )


@router.message(Command("owner"))
async def handle_owner(
    message: Message,
    admin_service: AdminService,
) -> None:
    if message.from_user is None:
        return

    if not await admin_service.is_owner(
        message.from_user.id
    ):
        return

    admins = await admin_service.list_admins()

    active_admins = [
        admin
        for admin in admins
        if admin.is_active and admin.role == "admin"
    ]

    await message.answer(
        "👑 <b>OWNER CONTROL PANEL</b>\n\n"
        f"🛡 Admins: {len(active_admins)}",
        reply_markup=_owner_keyboard(),
    )


@router.callback_query(F.data == "owner:manage_admins")
async def handle_owner_manage_admins(
    callback: CallbackQuery,
    admin_service: AdminService,
    user_service: UserService,
) -> None:
    if not await admin_service.is_owner(
        callback.from_user.id
    ):
        await callback.answer(
            "⛔ Owner only",
            show_alert=True,
        )
        return

    admins = await admin_service.list_admins()

    lines = [
        "🛡 <b>ADMIN TEAM</b>",
        "",
    ]

    keyboard_rows: list[list[InlineKeyboardButton]] = []

    for admin in admins:
        user = await user_service.get_by_telegram_id(
            admin.telegram_user_id
        )

        username = (
            f"@{user.username}"
            if user is not None and user.username
            else "No username"
        )

        if admin.role == "owner":
            icon = "👑"
            role_label = "OWNER"
        else:
            icon = "🛡"
            role_label = "ADMIN"

        status = (
            "ACTIVE"
            if admin.is_active
            else "DISABLED"
        )

        lines.append(
            f"{icon} {escape(username)} "
            f"• <code>{admin.telegram_user_id}</code> "
            f"• {role_label} • {status}"
        )

        if admin.role != "owner":
            keyboard_rows.append(
                [
                    InlineKeyboardButton(
                        text=(
                            f"{'🟢' if admin.is_active else '🔴'} "
                            f"{username}"
                        ),
                        callback_data=(
                            f"owner:admin:{admin.telegram_user_id}"
                        ),
                    )
                ]
            )

    keyboard_rows.append(
        [
            InlineKeyboardButton(
                text="➕ ADD ADMIN",
                callback_data="owner:add_admin",
            )
        ]
    )

    keyboard_rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ BACK",
                callback_data="owner:back",
            )
        ]
    )

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=keyboard_rows
            ),
        )

    await callback.answer()


@router.callback_query(F.data == "owner:back")
async def handle_owner_back(
    callback: CallbackQuery,
    admin_service: AdminService,
) -> None:
    if not await admin_service.is_owner(
        callback.from_user.id
    ):
        await callback.answer(
            "⛔ Owner only",
            show_alert=True,
        )
        return

    admins = await admin_service.list_admins()

    active_admins = [
        admin
        for admin in admins
        if admin.is_active and admin.role == "admin"
    ]

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "👑 <b>OWNER CONTROL PANEL</b>\n\n"
            f"🛡 Admins: {len(active_admins)}",
            reply_markup=_owner_keyboard(),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("owner:admin:"))
async def handle_owner_admin_details(
    callback: CallbackQuery,
    admin_service: AdminService,
    user_service: UserService,
) -> None:
    if not await admin_service.is_owner(
        callback.from_user.id
    ):
        await callback.answer(
            "⛔ Owner only",
            show_alert=True,
        )
        return

    if callback.data is None:
        return

    raw_id = callback.data.removeprefix("owner:admin:")

    try:
        telegram_user_id = int(raw_id)
    except ValueError:
        await callback.answer(
            "Invalid admin ID",
            show_alert=True,
        )
        return

    admin = await admin_service.get_admin(
        telegram_user_id
    )

    if admin is None or admin.role == "owner":
        await callback.answer(
            "Admin not found",
            show_alert=True,
        )
        return

    user = await user_service.get_by_telegram_id(
        admin.telegram_user_id
    )

    username = (
        f"@{user.username}"
        if user is not None and user.username
        else "No username"
    )

    status = (
        "ACTIVE"
        if admin.is_active
        else "DISABLED"
    )

    action_text = (
        "🚫 DISABLE ADMIN"
        if admin.is_active
        else "✅ ENABLE ADMIN"
    )

    action_callback = (
        f"owner:disable_admin:{telegram_user_id}"
        if admin.is_active
        else f"owner:enable_admin:{telegram_user_id}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=action_text,
                    callback_data=action_callback,
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 DELETE ADMIN",
                    callback_data=f"owner:delete_admin_confirm:{telegram_user_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ BACK",
                    callback_data="owner:manage_admins",
                )
            ],
        ]
    )

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "🛡 <b>ADMIN DETAILS</b>\n\n"
            f"Username: {escape(username)}\n"
            f"Telegram ID: <code>{admin.telegram_user_id}</code>\n"
            f"Role: {admin.role.upper()}\n"
            f"Status: {status}",
            reply_markup=keyboard,
        )

    await callback.answer()


@router.callback_query(F.data.startswith("owner:disable_admin:"))
async def handle_owner_disable_admin(
    callback: CallbackQuery,
    admin_service: AdminService,
    audit_log_service: AuditLogService,
    user_service: UserService,
) -> None:
    if not await admin_service.is_owner(
        callback.from_user.id
    ):
        await callback.answer(
            "⛔ Owner only",
            show_alert=True,
        )
        return

    if callback.data is None:
        return

    raw_id = callback.data.removeprefix(
        "owner:disable_admin:"
    )

    try:
        telegram_user_id = int(raw_id)
    except ValueError:
        await callback.answer(
            "Invalid admin ID",
            show_alert=True,
        )
        return

    admin = await admin_service.get_admin(
        telegram_user_id
    )

    if admin is None or admin.role == "owner":
        await callback.answer(
            "Admin not found",
            show_alert=True,
        )
        return

    await admin_service.set_admin_active(
        telegram_user_id,
        False,
    )

    await audit_log_service.record(
        actor_telegram_user_id=callback.from_user.id,
        action="admin_disabled",
        target_type="admin",
        target_id=str(telegram_user_id),
        details=f"role={admin.role}",
    )

    user = await user_service.get_by_telegram_id(
        telegram_user_id
    )
    username = (
        f"@{user.username}"
        if user is not None and user.username
        else "No username"
    )

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "🛡 <b>ADMIN DETAILS</b>\n\n"
            f"Username: {escape(username)}\n"
            f"Telegram ID: <code>{telegram_user_id}</code>\n"
            "Role: ADMIN\n"
            "Status: DISABLED",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ ENABLE ADMIN",
                            callback_data=f"owner:enable_admin:{telegram_user_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🗑 DELETE ADMIN",
                            callback_data=f"owner:delete_admin_confirm:{telegram_user_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="⬅️ BACK",
                            callback_data="owner:manage_admins",
                        )
                    ],
                ]
            ),
        )

    await callback.answer("Admin disabled ✅")


@router.callback_query(F.data.startswith("owner:enable_admin:"))
async def handle_owner_enable_admin(
    callback: CallbackQuery,
    admin_service: AdminService,
    audit_log_service: AuditLogService,
    user_service: UserService,
) -> None:
    if not await admin_service.is_owner(
        callback.from_user.id
    ):
        await callback.answer(
            "⛔ Owner only",
            show_alert=True,
        )
        return

    if callback.data is None:
        return

    raw_id = callback.data.removeprefix(
        "owner:enable_admin:"
    )

    try:
        telegram_user_id = int(raw_id)
    except ValueError:
        await callback.answer(
            "Invalid admin ID",
            show_alert=True,
        )
        return

    admin = await admin_service.get_admin(
        telegram_user_id
    )

    if admin is None or admin.role == "owner":
        await callback.answer(
            "Admin not found",
            show_alert=True,
        )
        return

    await admin_service.set_admin_active(
        telegram_user_id,
        True,
    )

    await audit_log_service.record(
        actor_telegram_user_id=callback.from_user.id,
        action="admin_enabled",
        target_type="admin",
        target_id=str(telegram_user_id),
        details=f"role={admin.role}",
    )

    user = await user_service.get_by_telegram_id(
        telegram_user_id
    )
    username = (
        f"@{user.username}"
        if user is not None and user.username
        else "No username"
    )

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "🛡 <b>ADMIN DETAILS</b>\n\n"
            f"Username: {escape(username)}\n"
            f"Telegram ID: <code>{telegram_user_id}</code>\n"
            "Role: ADMIN\n"
            "Status: ACTIVE",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🚫 DISABLE ADMIN",
                            callback_data=f"owner:disable_admin:{telegram_user_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🗑 DELETE ADMIN",
                            callback_data=f"owner:delete_admin_confirm:{telegram_user_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="⬅️ BACK",
                            callback_data="owner:manage_admins",
                        )
                    ],
                ]
            ),
        )

    await callback.answer("Admin enabled ✅")


@router.callback_query(F.data == "owner:add_admin")
async def handle_owner_add_admin(
    callback: CallbackQuery,
    state: FSMContext,
    admin_service: AdminService,
) -> None:
    if not await admin_service.is_owner(
        callback.from_user.id
    ):
        await callback.answer(
            "⛔ Owner only",
            show_alert=True,
        )
        return

    await state.set_state(
        AdminManagementStates.waiting_for_admin_telegram_id
    )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "➕ <b>ADD ADMIN</b>\n\n"
            "Send the Telegram ID or @username of the new admin.\n\n"
            "Examples:\n"
            "<code>123456789</code>\n"
            "<code>@username</code>"
        )

    await callback.answer()


@router.message(
    AdminManagementStates.waiting_for_admin_telegram_id
)
async def handle_owner_add_admin_id(
    message: Message,
    state: FSMContext,
    admin_service: AdminService,
    audit_log_service: AuditLogService,
    user_service: UserService,
) -> None:
    if message.from_user is None:
        return

    if not await admin_service.is_owner(
        message.from_user.id
    ):
        await state.clear()
        return

    if message.text is None:
        await message.answer(
            "❌ Send the Telegram ID as text."
        )
        return

    raw_input = message.text.strip()

    resolved_user = None

    if raw_input.startswith("@"):
        username = raw_input.lstrip("@").strip()

        if not username:
            await message.answer(
                "❌ Invalid username.\n"
                "Example: <code>@username</code>"
            )
            return

        resolved_user = await user_service.get_by_username(
            username
        )

        if resolved_user is None:
            await message.answer(
                "❌ Username not found in bot users.\n\n"
                "Ask that user to start the bot first, then try again."
            )
            return

        telegram_user_id = resolved_user.telegram_user_id

    else:
        try:
            telegram_user_id = int(raw_input)
        except ValueError:
            await message.answer(
                "❌ Send a Telegram ID or @username.\n\n"
                "Examples:\n"
                "<code>123456789</code>\n"
                "<code>@username</code>"
            )
            return

        if telegram_user_id <= 0:
            await message.answer(
                "❌ Invalid Telegram ID."
            )
            return

        resolved_user = await user_service.get_by_telegram_id(
            telegram_user_id
        )

    existing = await admin_service.get_admin(
        telegram_user_id
    )

    if (
        existing is not None
        and existing.role == "owner"
    ):
        await state.clear()
        await message.answer(
            "👑 This user is already the owner.",
            reply_markup=_owner_keyboard(),
        )
        return

    admin = await admin_service.add_admin(
        telegram_user_id
    )

    await audit_log_service.record(
        actor_telegram_user_id=message.from_user.id,
        action="admin_added",
        target_type="admin",
        target_id=str(telegram_user_id),
        details="Admin added or re-enabled by owner.",
    )

    await state.clear()

    username = (
        f"@{resolved_user.username}"
        if resolved_user is not None and resolved_user.username
        else "No username"
    )

    await message.answer(
        "✅ <b>ADMIN ADDED</b>\n\n"
        f"Username: {escape(username)}\n"
        f"Telegram ID: <code>{admin.telegram_user_id}</code>\n"
        "Role: ADMIN\n"
        "Status: ACTIVE",
        reply_markup=_owner_keyboard(),
    )


@router.callback_query(F.data == "owner:admin_panel")
async def handle_owner_admin_panel(
    callback: CallbackQuery,
    admin_service: AdminService,
) -> None:
    if not await admin_service.is_owner(
        callback.from_user.id
    ):
        await callback.answer(
            "⛔ Owner only",
            show_alert=True,
        )
        return

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "🛡 <b>ADMIN PANEL</b>\n\n"
            "✅ Admin access verified.",
            reply_markup=_admin_keyboard(),
        )

    await callback.answer()


@router.callback_query(F.data == "owner:reset_all_confirm")
async def handle_owner_reset_all_confirm(
    callback: CallbackQuery,
    admin_service: AdminService,
) -> None:
    if callback.from_user is None:
        return

    if not await admin_service.is_owner(callback.from_user.id):
        await callback.answer(
            "⛔ Owner only",
            show_alert=True,
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚠️ YES, RESET ALL",
                    callback_data="owner:reset_all_execute",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ CANCEL",
                    callback_data="owner:back",
                )
            ],
        ]
    )

    if callback.message is not None:
        await callback.message.edit_text(
            "⚠️ <b>RESET ALL VERIFICATIONS?</b>\n\n"
            "This will reset verification status for "
            "<b>all users</b>.\n\n"
            "The following will be cleared:\n"
            "• Registration completion\n"
            "• Contact verification\n"
            "• VIP access\n\n"
            "Language and VIP category selection will remain unchanged.\n\n"
            "<b>This action cannot be undone.</b>",
            reply_markup=keyboard,
        )

    await callback.answer()


@router.callback_query(F.data == "owner:reset_all_execute")
async def handle_owner_reset_all_execute(
    callback: CallbackQuery,
    admin_service: AdminService,
    onboarding_service: OnboardingService,
    audit_log_service: AuditLogService,
) -> None:
    if callback.from_user is None:
        return

    if not await admin_service.is_owner(callback.from_user.id):
        await callback.answer(
            "⛔ Owner only",
            show_alert=True,
        )
        return

    count = await onboarding_service.reset_all_verifications()

    await audit_log_service.record(
        actor_telegram_user_id=callback.from_user.id,
        action="all_user_verifications_reset",
        target_type="system",
        target_id="all_users",
        details=f"Reset {count} onboarding records.",
    )

    if callback.message is not None:
        await callback.message.edit_text(
            "✅ <b>ALL VERIFICATIONS RESET</b>\n\n"
            f"Reset records: <b>{count}</b>\n\n"
            "All affected users must complete verification again.\n"
            "Language and VIP category selections were preserved.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="👥 MANAGE USERS",
                            callback_data="owner:manage_users",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="⬅️ OWNER PANEL",
                            callback_data="owner:back",
                        )
                    ],
                ]
            ),
        )

    await callback.answer(
        "All verifications reset ✅",
        show_alert=True,
    )


@router.callback_query(F.data == "owner:manage_users")
async def handle_owner_manage_users(
    callback: CallbackQuery,
    admin_service: AdminService,
    user_service: UserService,
) -> None:
    if not await admin_service.is_owner(
        callback.from_user.id
    ):
        await callback.answer(
            "⛔ Owner only",
            show_alert=True,
        )
        return

    users = await user_service.list_all(
        limit=50,
        offset=0,
    )

    lines = [
        "👥 <b>USERS</b>",
        "",
        f"Total shown: {len(users)}",
        "",
    ]

    keyboard_rows: list[list[InlineKeyboardButton]] = []

    for user in users:
        name = (
            user.first_name
            or user.username
            or str(user.telegram_user_id)
        )

        lines.append(
            f"• {escape(name)} "
            f"(<code>{user.telegram_user_id}</code>)"
        )

        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text=f"👤 {name[:28]}",
                    callback_data=(
                        f"owner:user:{user.id}"
                    ),
                )
            ]
        )

    keyboard_rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ BACK",
                callback_data="owner:back",
            )
        ]
    )

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=keyboard_rows
            ),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("owner:user:"))
async def handle_owner_user_details(
    callback: CallbackQuery,
    admin_service: AdminService,
    user_service: UserService,
    onboarding_service: OnboardingService,
) -> None:
    if not await admin_service.is_owner(
        callback.from_user.id
    ):
        await callback.answer(
            "⛔ Owner only",
            show_alert=True,
        )
        return

    if callback.data is None:
        return

    raw_id = callback.data.removeprefix("owner:user:")

    try:
        user_id = int(raw_id)
    except ValueError:
        await callback.answer(
            "Invalid user ID",
            show_alert=True,
        )
        return

    users = await user_service.get_by_ids([user_id])

    if not users:
        await callback.answer(
            "User not found",
            show_alert=True,
        )
        return

    user = users[0]

    state = await onboarding_service.get_state(
        user_id=user.id
    )

    if state is None:
        verification_status = "⚪ NOT STARTED"
        vip_status = "❌ NO ACCESS"
        selected_vip = "None"
    else:
        if state.vip_access_granted_at is not None:
            verification_status = "🟢 APPROVED"
            vip_status = "✅ ACTIVE"
        elif state.contact_verified_at is not None:
            verification_status = "🟡 PENDING APPROVAL"
            vip_status = "⏳ WAITING"
        else:
            verification_status = "⚪ INCOMPLETE"
            vip_status = "❌ NO ACCESS"

        selected_vip = (
            str(state.vip_category_id)
            if state.vip_category_id is not None
            else "None"
        )

    username = (
        f"@{user.username}"
        if user.username
        else "None"
    )

    name = " ".join(
        part
        for part in [
            user.first_name,
            user.last_name,
        ]
        if part
    ) or "Unknown"

    keyboard_rows = []

    if (
        state is not None
        and state.contact_verified_at is not None
        and state.vip_access_granted_at is None
    ):
        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text="✅ APPROVE",
                    callback_data=f"owner:user_approve:{user.id}",
                )
            ]
        )

    if (
        state is not None
        and state.vip_access_granted_at is not None
    ):
        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text="🚫 REMOVE ACCESS",
                    callback_data=f"owner:user_revoke:{user.id}",
                )
            ]
        )

    keyboard_rows.append(
        [
            InlineKeyboardButton(
                text="🔄 RESET VERIFICATION",
                callback_data=f"owner:user_reset:{user.id}",
            )
        ]
    )

    if not await admin_service.is_owner(
        user.telegram_user_id
    ):
        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text="🗑 DELETE USER",
                    callback_data=f"owner:user_delete_confirm:{user.id}",
                )
            ]
        )

    keyboard_rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ BACK",
                callback_data="owner:manage_users",
            )
        ]
    )

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "👤 <b>USER DETAILS</b>\n\n"
            f"Name: {escape(name)}\n"
            f"Telegram ID: <code>{user.telegram_user_id}</code>\n"
            f"Username: {escape(username)}\n"
            f"Joined: {user.created_at:%Y-%m-%d %H:%M}\n"
            f"Verification: {verification_status}\n"
            f"VIP Status: {vip_status}\n"
            f"Selected VIP ID: {selected_vip}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=keyboard_rows
            ),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("owner:user_approve:"))
async def handle_owner_user_approve(
    callback: CallbackQuery,
    admin_service: AdminService,
    onboarding_service: OnboardingService,
    audit_log_service: AuditLogService,
) -> None:
    if not await admin_service.is_owner(
        callback.from_user.id
    ):
        await callback.answer(
            "⛔ Owner only",
            show_alert=True,
        )
        return

    if callback.data is None:
        return

    raw_id = callback.data.removeprefix(
        "owner:user_approve:"
    )

    try:
        user_id = int(raw_id)
    except ValueError:
        await callback.answer(
            "Invalid user ID",
            show_alert=True,
        )
        return

    result = await onboarding_service.grant_vip_access(
        user_id=user_id
    )

    if not result.granted:
        await callback.answer(
            f"Could not approve: {result.reason}",
            show_alert=True,
        )
        return

    await audit_log_service.record(
        actor_telegram_user_id=callback.from_user.id,
        action="user_approved",
        target_type="user",
        target_id=str(user_id),
        details="VIP access granted.",
    )

    await callback.answer(
        "User approved ✅"
    )

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "✅ <b>USER APPROVED</b>\n\n"
            "VIP access has been granted.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="👤 VIEW USER",
                            callback_data=f"owner:user:{user_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="⬅️ USERS",
                            callback_data="owner:manage_users",
                        )
                    ],
                ]
            ),
        )


@router.callback_query(F.data.startswith("owner:user_revoke:"))
async def handle_owner_user_revoke(
    callback: CallbackQuery,
    admin_service: AdminService,
    onboarding_service: OnboardingService,
    audit_log_service: AuditLogService,
) -> None:
    if not await admin_service.is_owner(
        callback.from_user.id
    ):
        await callback.answer(
            "⛔ Owner only",
            show_alert=True,
        )
        return

    if callback.data is None:
        return

    raw_id = callback.data.removeprefix(
        "owner:user_revoke:"
    )

    try:
        user_id = int(raw_id)
    except ValueError:
        await callback.answer(
            "Invalid user ID",
            show_alert=True,
        )
        return

    await onboarding_service.revoke_vip_access(
        user_id=user_id
    )

    await audit_log_service.record(
        actor_telegram_user_id=callback.from_user.id,
        action="user_access_revoked",
        target_type="user",
        target_id=str(user_id),
        details="VIP access revoked.",
    )

    await callback.answer(
        "Access removed ✅"
    )

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "🚫 <b>ACCESS REMOVED</b>\n\n"
            "The user's VIP access has been revoked.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="👤 VIEW USER",
                            callback_data=f"owner:user:{user_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="⬅️ USERS",
                            callback_data="owner:manage_users",
                        )
                    ],
                ]
            ),
        )


@router.callback_query(F.data.startswith("owner:user_reset:"))
async def handle_owner_user_reset(
    callback: CallbackQuery,
    admin_service: AdminService,
    onboarding_service: OnboardingService,
    audit_log_service: AuditLogService,
) -> None:
    if not await admin_service.is_owner(
        callback.from_user.id
    ):
        await callback.answer(
            "⛔ Owner only",
            show_alert=True,
        )
        return

    if callback.data is None:
        return

    raw_id = callback.data.removeprefix(
        "owner:user_reset:"
    )

    try:
        user_id = int(raw_id)
    except ValueError:
        await callback.answer(
            "Invalid user ID",
            show_alert=True,
        )
        return

    await onboarding_service.reset_verification(
        user_id=user_id
    )

    await audit_log_service.record(
        actor_telegram_user_id=callback.from_user.id,
        action="user_verification_reset",
        target_type="user",
        target_id=str(user_id),
        details="User verification reset.",
    )

    await callback.answer(
        "Verification reset ✅"
    )

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "🔄 <b>VERIFICATION RESET</b>\n\n"
            "The user must complete verification again.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="👤 VIEW USER",
                            callback_data=f"owner:user:{user_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="⬅️ USERS",
                            callback_data="owner:manage_users",
                        )
                    ],
                ]
            ),
        )


@router.callback_query(F.data == "admin:manage_users")
async def handle_admin_manage_users(
    callback: CallbackQuery,
    admin_service: AdminService,
    user_service: UserService,
) -> None:
    users = await user_service.list_all(
        limit=50,
        offset=0,
    )

    visible_users = []

    for user in users:
        if await admin_service.is_owner(
            user.telegram_user_id
        ):
            continue

        visible_users.append(user)

    lines = [
        "👥 <b>MANAGE USERS</b>",
        "",
        f"Total shown: {len(visible_users)}",
        "",
    ]

    keyboard_rows: list[list[InlineKeyboardButton]] = []

    for user in visible_users:
        name = (
            user.first_name
            or user.username
            or str(user.telegram_user_id)
        )

        lines.append(
            f"• {escape(name)} "
            f"(<code>{user.telegram_user_id}</code>)"
        )

        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text=f"👤 {name[:28]}",
                    callback_data=f"admin:user:{user.id}",
                )
            ]
        )

    keyboard_rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ BACK",
                callback_data="admin:back",
            )
        ]
    )

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=keyboard_rows
            ),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("admin:user:"))
async def handle_admin_user_details(
    callback: CallbackQuery,
    admin_service: AdminService,
    user_service: UserService,
    onboarding_service: OnboardingService,
) -> None:
    if callback.data is None:
        return

    raw_id = callback.data.removeprefix("admin:user:")

    try:
        user_id = int(raw_id)
    except ValueError:
        await callback.answer(
            "Invalid user ID",
            show_alert=True,
        )
        return

    users = await user_service.get_by_ids([user_id])

    if not users:
        await callback.answer(
            "User not found",
            show_alert=True,
        )
        return

    user = users[0]

    if await admin_service.is_owner(
        user.telegram_user_id
    ):
        await callback.answer(
            "⛔ Owner account cannot be managed here.",
            show_alert=True,
        )
        return

    state = await onboarding_service.get_state(
        user_id=user.id
    )

    if state is None:
        verification_status = "⚪ NOT STARTED"
        vip_status = "❌ NO ACCESS"
        selected_vip = "None"
    else:
        if state.vip_access_granted_at is not None:
            verification_status = "🟢 APPROVED"
            vip_status = "✅ ACTIVE"
        elif state.contact_verified_at is not None:
            verification_status = "🟡 PENDING APPROVAL"
            vip_status = "⏳ WAITING"
        else:
            verification_status = "⚪ INCOMPLETE"
            vip_status = "❌ NO ACCESS"

        selected_vip = (
            str(state.vip_category_id)
            if state.vip_category_id is not None
            else "None"
        )

    username = (
        f"@{user.username}"
        if user.username
        else "None"
    )

    name = " ".join(
        part
        for part in [
            user.first_name,
            user.last_name,
        ]
        if part
    ) or "Unknown"

    keyboard_rows = []

    if (
        state is not None
        and state.contact_verified_at is not None
        and state.vip_access_granted_at is None
    ):
        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text="✅ APPROVE",
                    callback_data=f"admin:user_approve:{user.id}",
                )
            ]
        )

    if (
        state is not None
        and state.vip_access_granted_at is not None
    ):
        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text="🚫 REMOVE ACCESS",
                    callback_data=f"admin:user_revoke:{user.id}",
                )
            ]
        )

    keyboard_rows.append(
        [
            InlineKeyboardButton(
                text="🔄 RESET VERIFICATION",
                callback_data=f"admin:user_reset:{user.id}",
            )
        ]
    )

    keyboard_rows.append(
        [
            InlineKeyboardButton(
                text="🗑 DELETE USER",
                callback_data=f"admin:user_delete_confirm:{user.id}",
            )
        ]
    )

    keyboard_rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ BACK",
                callback_data="admin:manage_users",
            )
        ]
    )

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "👤 <b>USER DETAILS</b>\n\n"
            f"Name: {escape(name)}\n"
            f"Telegram ID: <code>{user.telegram_user_id}</code>\n"
            f"Username: {escape(username)}\n"
            f"Joined: {user.created_at:%Y-%m-%d %H:%M}\n"
            f"Verification: {verification_status}\n"
            f"VIP Status: {vip_status}\n"
            f"Selected VIP ID: {selected_vip}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=keyboard_rows
            ),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("admin:user_approve:"))
async def handle_admin_user_approve(
    callback: CallbackQuery,
    admin_service: AdminService,
    user_service: UserService,
    onboarding_service: OnboardingService,
    audit_log_service: AuditLogService,
) -> None:
    if callback.data is None:
        return

    raw_id = callback.data.removeprefix(
        "admin:user_approve:"
    )

    try:
        user_id = int(raw_id)
    except ValueError:
        await callback.answer(
            "Invalid user ID",
            show_alert=True,
        )
        return

    users = await user_service.get_by_ids([user_id])

    if not users:
        await callback.answer(
            "User not found",
            show_alert=True,
        )
        return

    user = users[0]

    if await admin_service.is_owner(
        user.telegram_user_id
    ):
        await callback.answer(
            "⛔ Owner account cannot be managed.",
            show_alert=True,
        )
        return

    result = await onboarding_service.grant_vip_access(
        user_id=user_id
    )

    if not result.granted:
        await callback.answer(
            f"Could not approve: {result.reason}",
            show_alert=True,
        )
        return

    await audit_log_service.record(
        actor_telegram_user_id=callback.from_user.id,
        action="user_approved",
        target_type="user",
        target_id=str(user_id),
        details="VIP access granted by admin.",
    )

    await callback.answer("User approved ✅")

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "✅ <b>USER APPROVED</b>\n\n"
            "VIP access has been granted.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="👤 VIEW USER",
                            callback_data=f"admin:user:{user_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="⬅️ USERS",
                            callback_data="admin:manage_users",
                        )
                    ],
                ]
            ),
        )


@router.callback_query(F.data.startswith("admin:user_revoke:"))
async def handle_admin_user_revoke(
    callback: CallbackQuery,
    admin_service: AdminService,
    user_service: UserService,
    onboarding_service: OnboardingService,
    audit_log_service: AuditLogService,
) -> None:
    if callback.data is None:
        return

    raw_id = callback.data.removeprefix(
        "admin:user_revoke:"
    )

    try:
        user_id = int(raw_id)
    except ValueError:
        await callback.answer(
            "Invalid user ID",
            show_alert=True,
        )
        return

    users = await user_service.get_by_ids([user_id])

    if not users:
        await callback.answer(
            "User not found",
            show_alert=True,
        )
        return

    user = users[0]

    if await admin_service.is_owner(
        user.telegram_user_id
    ):
        await callback.answer(
            "⛔ Owner account cannot be managed.",
            show_alert=True,
        )
        return

    await onboarding_service.revoke_vip_access(
        user_id=user_id
    )

    await audit_log_service.record(
        actor_telegram_user_id=callback.from_user.id,
        action="user_access_revoked",
        target_type="user",
        target_id=str(user_id),
        details="VIP access revoked by admin.",
    )

    await callback.answer("Access removed ✅")

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "🚫 <b>ACCESS REMOVED</b>\n\n"
            "The user's VIP access has been revoked.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="👤 VIEW USER",
                            callback_data=f"admin:user:{user_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="⬅️ USERS",
                            callback_data="admin:manage_users",
                        )
                    ],
                ]
            ),
        )


@router.callback_query(F.data.startswith("admin:user_reset:"))
async def handle_admin_user_reset(
    callback: CallbackQuery,
    admin_service: AdminService,
    user_service: UserService,
    onboarding_service: OnboardingService,
    audit_log_service: AuditLogService,
) -> None:
    if callback.data is None:
        return

    raw_id = callback.data.removeprefix(
        "admin:user_reset:"
    )

    try:
        user_id = int(raw_id)
    except ValueError:
        await callback.answer(
            "Invalid user ID",
            show_alert=True,
        )
        return

    users = await user_service.get_by_ids([user_id])

    if not users:
        await callback.answer(
            "User not found",
            show_alert=True,
        )
        return

    user = users[0]

    if await admin_service.is_owner(
        user.telegram_user_id
    ):
        await callback.answer(
            "⛔ Owner account cannot be managed.",
            show_alert=True,
        )
        return

    await onboarding_service.reset_verification(
        user_id=user_id
    )

    await audit_log_service.record(
        actor_telegram_user_id=callback.from_user.id,
        action="user_verification_reset",
        target_type="user",
        target_id=str(user_id),
        details="User verification reset by admin.",
    )

    await callback.answer("Verification reset ✅")

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "🔄 <b>VERIFICATION RESET</b>\n\n"
            "The user must complete verification again.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="👤 VIEW USER",
                            callback_data=f"admin:user:{user_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="⬅️ USERS",
                            callback_data="admin:manage_users",
                        )
                    ],
                ]
            ),
        )


@router.callback_query(F.data == "admin:back")
async def handle_admin_back(
    callback: CallbackQuery,
) -> None:
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "🛡 <b>ADMIN PANEL</b>\n\n"
            "✅ Admin access verified.",
            reply_markup=_admin_keyboard(),
        )

    await callback.answer()


@router.callback_query(F.data == "owner:audit_log")
async def handle_owner_audit_log(
    callback: CallbackQuery,
    admin_service: AdminService,
    audit_log_service: AuditLogService,
    user_service: UserService,
) -> None:
    if not await admin_service.is_owner(
        callback.from_user.id
    ):
        await callback.answer(
            "⛔ Owner only",
            show_alert=True,
        )
        return

    owner_admin = await admin_service.get_admin(
        callback.from_user.id
    )

    timezone_name = (
        owner_admin.timezone
        if owner_admin is not None and owner_admin.timezone
        else "UTC"
    )

    try:
        owner_timezone = ZoneInfo(timezone_name)
    except Exception:
        timezone_name = "UTC"
        owner_timezone = ZoneInfo("UTC")

    logs = await audit_log_service.list_recent(
        limit=20
    )

    lines = [
        "📋 <b>AUDIT LOG</b>",
        f"🌍 Timezone: <code>{escape(timezone_name)}</code>",
        "",
    ]

    if not logs:
        lines.append("No audit activity recorded yet.")
    else:
        for log in logs:
            created_at = log.created_at

            if created_at.tzinfo is None:
                created_at = created_at.replace(
                    tzinfo=ZoneInfo("UTC")
                )

            local_created_at = created_at.astimezone(
                owner_timezone
            )

            created = local_created_at.strftime(
                "%d %b %Y • %I:%M %p %Z"
            )

            actor_user = await user_service.get_by_telegram_id(
                log.actor_telegram_user_id
            )

            if actor_user and actor_user.username:
                actor_label = (
                    f"@{escape(actor_user.username)} "
                    f"(<code>{log.actor_telegram_user_id}</code>)"
                )
            else:
                actor_label = (
                    f"<code>{log.actor_telegram_user_id}</code>"
                )

            target_label = (
                f"{escape(log.target_type)} "
                f"<code>{escape(log.target_id)}</code>"
            )

            if log.target_type == "user":
                try:
                    target_user_id = int(log.target_id)
                except (TypeError, ValueError):
                    target_user_id = None

                if target_user_id is not None:
                    users = await user_service.get_by_ids(
                        [target_user_id]
                    )

                    if users:
                        target_user = users[0]

                        if target_user.username:
                            target_label = (
                                f"@{escape(target_user.username)} "
                                f"(<code>{target_user.telegram_user_id}</code>)"
                            )
                        else:
                            target_label = (
                                f"<code>{target_user.telegram_user_id}</code>"
                            )

            elif log.target_type == "admin":
                try:
                    target_telegram_id = int(log.target_id)
                except (TypeError, ValueError):
                    target_telegram_id = None

                if target_telegram_id is not None:
                    target_user = await user_service.get_by_telegram_id(
                        target_telegram_id
                    )

                    if target_user and target_user.username:
                        target_label = (
                            f"@{escape(target_user.username)} "
                            f"(<code>{target_telegram_id}</code>)"
                        )
                    else:
                        target_label = (
                            f"<code>{target_telegram_id}</code>"
                        )

            lines.extend(
                [
                    f"🕒 {created}",
                    f"👤 Actor: {actor_label}",
                    f"⚡ Action: {escape(log.action)}",
                    f"🎯 Target: {target_label}",
                ]
            )

            if log.details:
                lines.append(
                    f"📝 {escape(log.details)}"
                )

            lines.append("")

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔄 REFRESH",
                            callback_data="owner:audit_log",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="⬅️ BACK",
                            callback_data="owner:back",
                        )
                    ],
                ]
            ),
        )

    await callback.answer()


@router.callback_query(
    F.data.startswith("owner:delete_admin_confirm:")
)
async def handle_owner_delete_admin_confirm(
    callback: CallbackQuery,
    admin_service: AdminService,
) -> None:
    if not await admin_service.is_owner(
        callback.from_user.id
    ):
        await callback.answer(
            "⛔ Owner only",
            show_alert=True,
        )
        return

    if callback.data is None:
        return

    raw_id = callback.data.removeprefix(
        "owner:delete_admin_confirm:"
    )

    try:
        telegram_user_id = int(raw_id)
    except ValueError:
        await callback.answer(
            "Invalid admin ID",
            show_alert=True,
        )
        return

    admin = await admin_service.get_admin(
        telegram_user_id
    )

    if admin is None or admin.role == "owner":
        await callback.answer(
            "Admin not found",
            show_alert=True,
        )
        return

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "⚠️ <b>DELETE ADMIN?</b>\n\n"
            f"Telegram ID: <code>{telegram_user_id}</code>\n\n"
            "This will permanently remove this admin role.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🗑 YES, DELETE",
                            callback_data=(
                                f"owner:delete_admin:{telegram_user_id}"
                            ),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="❌ CANCEL",
                            callback_data=(
                                f"owner:admin:{telegram_user_id}"
                            ),
                        )
                    ],
                ]
            ),
        )

    await callback.answer()


@router.callback_query(
    F.data.startswith("owner:delete_admin:")
)
async def handle_owner_delete_admin(
    callback: CallbackQuery,
    admin_service: AdminService,
    audit_log_service: AuditLogService,
) -> None:
    if not await admin_service.is_owner(
        callback.from_user.id
    ):
        await callback.answer(
            "⛔ Owner only",
            show_alert=True,
        )
        return

    if callback.data is None:
        return

    raw_id = callback.data.removeprefix(
        "owner:delete_admin:"
    )

    try:
        telegram_user_id = int(raw_id)
    except ValueError:
        await callback.answer(
            "Invalid admin ID",
            show_alert=True,
        )
        return

    deleted = await admin_service.delete_admin(
        telegram_user_id
    )

    if not deleted:
        await callback.answer(
            "Could not delete admin.",
            show_alert=True,
        )
        return

    await audit_log_service.record(
        actor_telegram_user_id=callback.from_user.id,
        action="admin_deleted",
        target_type="admin",
        target_id=str(telegram_user_id),
        details="Admin permanently removed by owner.",
    )

    await callback.answer(
        "Admin deleted ✅"
    )

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "🗑 <b>ADMIN DELETED</b>\n\n"
            f"<code>{telegram_user_id}</code> "
            "is no longer an admin.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="⬅️ MANAGE ADMINS",
                            callback_data="owner:manage_admins",
                        )
                    ]
                ]
            ),
        )


@router.callback_query(
    F.data.startswith("owner:user_delete_confirm:")
)
async def handle_owner_user_delete_confirm(
    callback: CallbackQuery,
    admin_service: AdminService,
    user_service: UserService,
) -> None:
    if not await admin_service.is_owner(
        callback.from_user.id
    ):
        await callback.answer(
            "⛔ Owner only",
            show_alert=True,
        )
        return

    if callback.data is None:
        return

    raw_id = callback.data.removeprefix(
        "owner:user_delete_confirm:"
    )

    try:
        user_id = int(raw_id)
    except ValueError:
        await callback.answer(
            "Invalid user ID",
            show_alert=True,
        )
        return

    users = await user_service.get_by_ids([user_id])

    if not users:
        await callback.answer(
            "User not found",
            show_alert=True,
        )
        return

    user = users[0]

    if await admin_service.is_owner(
        user.telegram_user_id
    ):
        await callback.answer(
            "⛔ Owner account cannot be deleted.",
            show_alert=True,
        )
        return

    username = (
        f"@{user.username}"
        if user.username
        else "No username"
    )

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "⚠️ <b>DELETE USER?</b>\n\n"
            f"User: {escape(username)}\n"
            f"Telegram ID: <code>{user.telegram_user_id}</code>\n\n"
            "This will permanently delete the user and related onboarding/membership data.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🗑 YES, DELETE",
                            callback_data=f"owner:user_delete:{user.id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="❌ CANCEL",
                            callback_data=f"owner:user:{user.id}",
                        )
                    ],
                ]
            ),
        )

    await callback.answer()


@router.callback_query(
    F.data.startswith("owner:user_delete:")
)
async def handle_owner_user_delete(
    callback: CallbackQuery,
    admin_service: AdminService,
    user_service: UserService,
    audit_log_service: AuditLogService,
) -> None:
    if not await admin_service.is_owner(
        callback.from_user.id
    ):
        await callback.answer(
            "⛔ Owner only",
            show_alert=True,
        )
        return

    if callback.data is None:
        return

    raw_id = callback.data.removeprefix(
        "owner:user_delete:"
    )

    try:
        user_id = int(raw_id)
    except ValueError:
        await callback.answer(
            "Invalid user ID",
            show_alert=True,
        )
        return

    users = await user_service.get_by_ids([user_id])

    if not users:
        await callback.answer(
            "User not found",
            show_alert=True,
        )
        return

    user = users[0]

    if await admin_service.is_owner(
        user.telegram_user_id
    ):
        await callback.answer(
            "⛔ Owner account cannot be deleted.",
            show_alert=True,
        )
        return

    target_telegram_id = user.telegram_user_id
    target_username = user.username

    deleted = await user_service.delete_user(
        user_id=user_id,
        owner_telegram_user_id=callback.from_user.id,
    )

    if not deleted:
        await callback.answer(
            "Could not delete user.",
            show_alert=True,
        )
        return

    await audit_log_service.record(
        actor_telegram_user_id=callback.from_user.id,
        action="user_deleted",
        target_type="user",
        target_id=str(target_telegram_id),
        details=(
            f"Deleted user @{target_username}."
            if target_username
            else "User permanently deleted."
        ),
    )

    await callback.answer("User deleted ✅")

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "🗑 <b>USER DELETED</b>\n\n"
            f"Telegram ID: <code>{target_telegram_id}</code>",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="⬅️ MANAGE USERS",
                            callback_data="owner:manage_users",
                        )
                    ]
                ]
            ),
        )


@router.callback_query(
    F.data.startswith("admin:user_delete_confirm:")
)
async def handle_admin_user_delete_confirm(
    callback: CallbackQuery,
    admin_service: AdminService,
    user_service: UserService,
) -> None:
    if callback.data is None:
        return

    raw_id = callback.data.removeprefix(
        "admin:user_delete_confirm:"
    )

    try:
        user_id = int(raw_id)
    except ValueError:
        await callback.answer(
            "Invalid user ID",
            show_alert=True,
        )
        return

    users = await user_service.get_by_ids([user_id])

    if not users:
        await callback.answer(
            "User not found",
            show_alert=True,
        )
        return

    user = users[0]

    if await admin_service.is_owner(
        user.telegram_user_id
    ):
        await callback.answer(
            "⛔ Owner account cannot be deleted.",
            show_alert=True,
        )
        return

    username = (
        f"@{user.username}"
        if user.username
        else "No username"
    )

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "⚠️ <b>DELETE USER?</b>\n\n"
            f"User: {escape(username)}\n"
            f"Telegram ID: <code>{user.telegram_user_id}</code>\n\n"
            "This will permanently delete this user.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🗑 YES, DELETE",
                            callback_data=f"admin:user_delete:{user.id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="❌ CANCEL",
                            callback_data=f"admin:user:{user.id}",
                        )
                    ],
                ]
            ),
        )

    await callback.answer()


@router.callback_query(
    F.data.startswith("admin:user_delete:")
)
async def handle_admin_user_delete(
    callback: CallbackQuery,
    admin_service: AdminService,
    user_service: UserService,
    audit_log_service: AuditLogService,
) -> None:
    if callback.data is None:
        return

    raw_id = callback.data.removeprefix(
        "admin:user_delete:"
    )

    try:
        user_id = int(raw_id)
    except ValueError:
        await callback.answer(
            "Invalid user ID",
            show_alert=True,
        )
        return

    users = await user_service.get_by_ids([user_id])

    if not users:
        await callback.answer(
            "User not found",
            show_alert=True,
        )
        return

    user = users[0]

    if await admin_service.is_owner(
        user.telegram_user_id
    ):
        await callback.answer(
            "⛔ Owner account cannot be deleted.",
            show_alert=True,
        )
        return

    target_telegram_id = user.telegram_user_id
    target_username = user.username

    deleted = await user_service.delete_user(
        user_id=user_id,
        owner_telegram_user_id=callback.from_user.id,
    )

    if not deleted:
        await callback.answer(
            "Could not delete user.",
            show_alert=True,
        )
        return

    await audit_log_service.record(
        actor_telegram_user_id=callback.from_user.id,
        action="user_deleted",
        target_type="user",
        target_id=str(target_telegram_id),
        details=(
            f"Deleted user @{target_username} by admin."
            if target_username
            else "User permanently deleted by admin."
        ),
    )

    await callback.answer("User deleted ✅")

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "🗑 <b>USER DELETED</b>\n\n"
            f"Telegram ID: <code>{target_telegram_id}</code>",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="⬅️ MANAGE USERS",
                            callback_data="admin:manage_users",
                        )
                    ]
                ]
            ),
        )

@router.callback_query(F.data == "owner:transfer_ownership")
async def handle_owner_transfer_ownership(
    callback: CallbackQuery,
    admin_service: AdminService,
    user_service: UserService,
) -> None:
    if callback.from_user is None:
        return

    if not await admin_service.is_owner(callback.from_user.id):
        await callback.answer(
            "Owner access required",
            show_alert=True,
        )
        return

    admins = await admin_service.list_admins()

    eligible_admins = [
        admin
        for admin in admins
        if (
            admin.role == "admin"
            and admin.is_active
            and admin.telegram_user_id != callback.from_user.id
        )
    ]

    if not eligible_admins:
        await callback.answer(
            "No active admin available for ownership transfer.",
            show_alert=True,
        )
        return

    lines = [
        "👑 <b>TRANSFER OWNERSHIP</b>",
        "",
        "Select the admin who should become the new owner:",
        "",
    ]

    buttons = []

    for admin in eligible_admins:
        user = await user_service.get_by_telegram_id(
            admin.telegram_user_id
        )

        username = (
            f"@{user.username}"
            if user is not None and user.username
            else "No username"
        )

        lines.append(
            f"🛡 {escape(username)} "
            f"• <code>{admin.telegram_user_id}</code>"
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"👑 {username}",
                    callback_data=(
                        "owner:transfer_select:"
                        f"{admin.telegram_user_id}"
                    ),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="⬅️ BACK",
                callback_data="owner:back",
            )
        ]
    )

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=buttons
            ),
        )

    await callback.answer()

@router.callback_query(F.data.startswith("owner:transfer_select:"))
async def handle_owner_transfer_select(
    callback: CallbackQuery,
    admin_service: AdminService,
    user_service: UserService,
) -> None:
    if callback.from_user is None:
        return

    if not await admin_service.is_owner(callback.from_user.id):
        await callback.answer(
            "Owner access required",
            show_alert=True,
        )
        return

    try:
        new_owner_telegram_id = int(
            callback.data.rsplit(":", 1)[1]
        )
    except (ValueError, AttributeError):
        await callback.answer(
            "Invalid admin",
            show_alert=True,
        )
        return

    admin = await admin_service.get_admin(
        new_owner_telegram_id
    )

    if (
        admin is None
        or admin.role != "admin"
        or not admin.is_active
    ):
        await callback.answer(
            "This admin is not eligible for ownership transfer.",
            show_alert=True,
        )
        return

    user = await user_service.get_by_telegram_id(
        new_owner_telegram_id
    )

    username = (
        f"@{user.username}"
        if user is not None and user.username
        else "No username"
    )

    text = (
        "⚠️ <b>CONFIRM OWNERSHIP TRANSFER</b>\n\n"
        f"New Owner: {escape(username)}\n"
        f"Telegram ID: <code>{new_owner_telegram_id}</code>\n\n"
        "After confirmation:\n"
        "• This admin becomes OWNER\n"
        "• You become a normal ADMIN\n"
        "• New owner gets full /owner access\n\n"
        "This is a sensitive action."
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ CONFIRM TRANSFER",
                    callback_data=(
                        "owner:transfer_confirm:"
                        f"{new_owner_telegram_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ CANCEL",
                    callback_data="owner:transfer_ownership",
                )
            ],
        ]
    )

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
        )

    await callback.answer()

@router.callback_query(F.data.startswith("owner:transfer_confirm:"))
async def handle_owner_transfer_confirm(
    callback: CallbackQuery,
    admin_service: AdminService,
    audit_log_service: AuditLogService,
    user_service: UserService,
) -> None:
    if callback.from_user is None:
        return

    current_owner_id = callback.from_user.id

    if not await admin_service.is_owner(current_owner_id):
        await callback.answer(
            "Owner access required",
            show_alert=True,
        )
        return

    try:
        new_owner_telegram_id = int(
            callback.data.rsplit(":", 1)[1]
        )
    except (ValueError, AttributeError):
        await callback.answer(
            "Invalid admin",
            show_alert=True,
        )
        return

    new_owner_admin = await admin_service.get_admin(
        new_owner_telegram_id
    )

    if (
        new_owner_admin is None
        or new_owner_admin.role != "admin"
        or not new_owner_admin.is_active
    ):
        await callback.answer(
            "This admin is no longer eligible.",
            show_alert=True,
        )
        return

    transferred = await admin_service.transfer_ownership(
        current_owner_telegram_user_id=current_owner_id,
        new_owner_telegram_user_id=new_owner_telegram_id,
    )

    if not transferred:
        await callback.answer(
            "Ownership transfer failed.",
            show_alert=True,
        )
        return

    new_owner_user = await user_service.get_by_telegram_id(
        new_owner_telegram_id
    )

    username = (
        f"@{new_owner_user.username}"
        if new_owner_user is not None
        and new_owner_user.username
        else "No username"
    )

    await audit_log_service.record(
        actor_telegram_user_id=current_owner_id,
        action="ownership_transferred",
        target_type="admin",
        target_id=str(new_owner_telegram_id),
        details=(
            f"previous_owner_telegram_id={current_owner_id}; "
            f"new_owner_telegram_id={new_owner_telegram_id}; "
            f"new_owner_username="
            f"{new_owner_user.username if new_owner_user is not None else 'None'}"
        ),
    )

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "✅ <b>OWNERSHIP TRANSFERRED</b>\n\n"
            f"New Owner: {escape(username)}\n"
            f"Telegram ID: <code>{new_owner_telegram_id}</code>\n\n"
            "You are now a normal admin.\n"
            "The new owner can now use /owner.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="⚙️ OPEN ADMIN PANEL",
                            callback_data="owner:admin_panel",
                        )
                    ]
                ]
            ),
        )

    await callback.answer(
        "Ownership transferred successfully ✅"
    )

@router.callback_query(F.data == "owner:timezone")
async def handle_owner_timezone(
    callback: CallbackQuery,
    admin_service: AdminService,
) -> None:
    if callback.from_user is None:
        return

    if not await admin_service.is_owner(callback.from_user.id):
        await callback.answer(
            "Owner access required",
            show_alert=True,
        )
        return

    admin = await admin_service.get_admin(
        callback.from_user.id
    )

    current_timezone = (
        admin.timezone
        if admin is not None and admin.timezone
        else "Not set"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌏 ASIA",
                    callback_data="owner:timezone_region:Asia",
                ),
                InlineKeyboardButton(
                    text="🌍 EUROPE",
                    callback_data="owner:timezone_region:Europe",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🌎 AMERICA",
                    callback_data="owner:timezone_region:America",
                ),
                InlineKeyboardButton(
                    text="🌍 AFRICA",
                    callback_data="owner:timezone_region:Africa",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🇦🇺 AUSTRALIA",
                    callback_data="owner:timezone_region:Australia",
                ),
                InlineKeyboardButton(
                    text="🌊 PACIFIC",
                    callback_data="owner:timezone_region:Pacific",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ BACK",
                    callback_data="owner:back",
                )
            ],
        ]
    )

    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(
                "🌍 <b>OWNER TIMEZONE</b>\n\n"
                f"Current: <code>{escape(current_timezone)}</code>\n\n"
                "Select your region:",
                reply_markup=keyboard,
            )
        except TelegramBadRequest as exc:
            if "message is not modified" not in str(exc):
                raise

    await callback.answer()


@router.callback_query(F.data.startswith("owner:set_timezone:"))
async def handle_owner_set_timezone(
    callback: CallbackQuery,
    admin_service: AdminService,
    audit_log_service: AuditLogService,
) -> None:
    if callback.from_user is None:
        return

    if not await admin_service.is_owner(callback.from_user.id):
        await callback.answer(
            "Owner access required",
            show_alert=True,
        )
        return

    timezone_name = callback.data.split(
        "owner:set_timezone:",
        1,
    )[1]

    from zoneinfo import available_timezones

    if timezone_name not in available_timezones():
        await callback.answer(
            "Invalid timezone",
            show_alert=True,
        )
        return

    admin = await admin_service.set_timezone(
        telegram_user_id=callback.from_user.id,
        timezone=timezone_name,
    )

    if admin is None:
        await callback.answer(
            "Failed to save timezone",
            show_alert=True,
        )
        return

    await audit_log_service.record(
        actor_telegram_user_id=callback.from_user.id,
        action="owner_timezone_updated",
        target_type="admin",
        target_id=str(callback.from_user.id),
        details=f"timezone={timezone_name}",
    )

    if callback.message is not None:
        await callback.message.edit_text(
            "✅ <b>TIMEZONE UPDATED</b>\n\n"
            f"Selected: <code>{escape(timezone_name)}</code>\n\n"
            "Audit Log will now use this timezone.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📋 OPEN AUDIT LOG",
                            callback_data="owner:audit_log",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🌍 CHANGE TIMEZONE",
                            callback_data="owner:timezone",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="⬅️ OWNER PANEL",
                            callback_data="owner:back",
                        )
                    ],
                ]
            ),
        )

    await callback.answer(
        "Timezone updated ✅",
        show_alert=True,
    )

@router.callback_query(F.data.startswith("owner:timezone_region:"))
async def handle_owner_timezone_region(
    callback: CallbackQuery,
    admin_service: AdminService,
) -> None:
    if callback.from_user is None:
        return

    if not await admin_service.is_owner(callback.from_user.id):
        await callback.answer(
            "Owner access required",
            show_alert=True,
        )
        return

    payload = callback.data.split(
        "owner:timezone_region:",
        1,
    )[1]

    parts = payload.rsplit(":", 1)

    if len(parts) == 2 and parts[1].isdigit():
        region = parts[0]
        page = int(parts[1])
    else:
        region = payload
        page = 0

    allowed_regions = {
        "Asia",
        "Europe",
        "America",
        "Africa",
        "Australia",
        "Pacific",
    }

    if region not in allowed_regions:
        await callback.answer(
            "Invalid region",
            show_alert=True,
        )
        return

    from zoneinfo import available_timezones

    timezones = sorted(
        tz
        for tz in available_timezones()
        if tz.startswith(f"{region}/")
    )

    if not timezones:
        await callback.answer(
            "No timezones found for this region.",
            show_alert=True,
        )
        return

    page_size = 20
    total_pages = (len(timezones) + page_size - 1) // page_size

    if page < 0:
        page = 0

    if page >= total_pages:
        page = total_pages - 1

    start_index = page * page_size
    end_index = start_index + page_size

    page_timezones = timezones[start_index:end_index]

    buttons = []

    for timezone_name in page_timezones:
        label = timezone_name.split("/", 1)[1].replace(
            "_",
            " ",
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=(
                        "owner:set_timezone:"
                        f"{timezone_name}"
                    ),
                )
            ]
        )

    nav_row = []

    if page > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ PREV",
                callback_data=(
                    f"owner:timezone_region:{region}:{page - 1}"
                ),
            )
        )

    nav_row.append(
        InlineKeyboardButton(
            text=f"{page + 1}/{total_pages}",
            callback_data="owner:timezone_noop",
        )
    )

    if page < total_pages - 1:
        nav_row.append(
            InlineKeyboardButton(
                text="NEXT ➡️",
                callback_data=(
                    f"owner:timezone_region:{region}:{page + 1}"
                ),
            )
        )

    buttons.append(nav_row)

    buttons.append(
        [
            InlineKeyboardButton(
                text="⬅️ BACK TO REGIONS",
                callback_data="owner:timezone",
            )
        ]
    )

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            f"🌍 <b>{escape(region.upper())} TIMEZONES</b>\n\n"
            f"Page {page + 1} of {total_pages}\n"
            "Select your timezone:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=buttons
            ),
        )

    await callback.answer()


@router.callback_query(F.data == "owner:timezone_noop")
async def handle_owner_timezone_noop(
    callback: CallbackQuery,
) -> None:
    await callback.answer()


@router.callback_query(F.data == "admin:content_settings")
async def handle_content_settings(callback: CallbackQuery) -> None:
    if callback.message is None:
        return

    await callback.message.edit_text(
        "📝 CONTENT SETTINGS\n\n"
        "Select the screen you want to edit:",
        reply_markup=_content_settings_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:content:winning_tips")
async def handle_winning_tips_settings(
    callback: CallbackQuery,
    content_screen_settings_service: ContentScreenSettingsService,
) -> None:
    if callback.message is None:
        return

    settings = await content_screen_settings_service.get("winning_tips")

    if settings is None:
        await callback.answer(
            "Winning Tips settings not found.",
            show_alert=True,
        )
        return

    media_status = (
        f"{settings.media_type.upper()} configured"
        if settings.media_file_id and settings.media_type
        else "No media"
    )

    text = (
        "🎯 WINNING TIPS SETTINGS\n\n"
        f"Heading:\n{settings.heading or 'Not set'}\n\n"
        f"Info:\n{settings.body or 'Not set'}\n\n"
        f"Footer:\n{settings.footer or 'Not set'}\n\n"
        f"Registration Link:\n"
        f"{settings.registration_url or 'Not set'}\n\n"
        f"Promo Code:\n{settings.promo_code or 'Not set'}\n\n"
        f"Media: {media_status}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ CHANGE HEADING",
                    callback_data="admin:content_edit:winning_tips:heading",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 CHANGE INFO",
                    callback_data="admin:content_edit:winning_tips:body",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🧾 CHANGE FOOTER",
                    callback_data="admin:content_edit:winning_tips:footer",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🖼 CHANGE MEDIA",
                    callback_data="admin:content_media:winning_tips",
                ),
                InlineKeyboardButton(
                    text="🗑 REMOVE MEDIA",
                    callback_data="admin:content_media_remove:winning_tips",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔗 REGISTRATION LINK",
                    callback_data="admin:content_edit:winning_tips:registration_url",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎟 PROMO CODE",
                    callback_data="admin:content_edit:winning_tips:promo_code",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ BACK",
                    callback_data="admin:content_settings",
                )
            ],
        ]
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
    )
    await callback.answer()


_CONTENT_EDIT_LABELS = {
    "heading": "heading",
    "body": "info",
    "footer": "footer",
    "registration_url": "registration link",
    "promo_code": "promo code",
    "support_username": "support username",
}


@router.callback_query(F.data.startswith("admin:content_edit:"))
async def handle_content_text_edit_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if callback.data is None or callback.message is None:
        return

    parts = callback.data.split(":", 3)

    if len(parts) != 4:
        await callback.answer("Invalid edit request.", show_alert=True)
        return

    _, _, screen_key, field_name = parts

    if field_name not in _CONTENT_EDIT_LABELS:
        await callback.answer("Unsupported field.", show_alert=True)
        return

    await state.set_state(ContentSettingsStates.waiting_for_text)
    await state.update_data(
        content_screen_key=screen_key,
        content_field_name=field_name,
    )

    await callback.message.answer(
        f"Send the new {_CONTENT_EDIT_LABELS[field_name]}.\n\n"
        "Send /cancel to cancel."
    )
    await callback.answer()


@router.message(ContentSettingsStates.waiting_for_text)
async def handle_content_text_edit_save(
    message: Message,
    state: FSMContext,
    content_screen_settings_service: ContentScreenSettingsService,
) -> None:
    if message.text is None:
        await message.answer("Please send text.")
        return

    if message.text.strip().lower() == "/cancel":
        await state.clear()
        await message.answer("Edit cancelled.")
        return

    data = await state.get_data()

    screen_key = data.get("content_screen_key")
    field_name = data.get("content_field_name")

    if not isinstance(screen_key, str) or not isinstance(field_name, str):
        await state.clear()
        await message.answer("Edit session expired. Please try again.")
        return

    settings = await content_screen_settings_service.get(screen_key)

    if settings is None:
        await state.clear()
        await message.answer("Content settings not found.")
        return

    values = {
        "heading": settings.heading,
        "body": settings.body,
        "footer": settings.footer,
        "registration_url": settings.registration_url,
        "promo_code": settings.promo_code,
        "support_username": settings.support_username,
    }

    if field_name not in values:
        await state.clear()
        await message.answer("Unsupported field.")
        return

    values[field_name] = message.text.strip()

    updated = await content_screen_settings_service.update_content(
        screen_key=screen_key,
        heading=values["heading"],
        body=values["body"],
        footer=values["footer"],
        registration_url=values["registration_url"],
        promo_code=values["promo_code"],
        support_username=values["support_username"],
    )

    await state.clear()

    if not updated:
        await message.answer("Could not update content settings.")
        return

    await message.answer(
        f"✅ {_CONTENT_EDIT_LABELS[field_name].title()} updated."
    )


@router.callback_query(F.data.startswith("admin:content_media:"))
async def handle_content_media_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if callback.data is None or callback.message is None:
        return

    parts = callback.data.split(":", 2)

    if len(parts) != 3:
        await callback.answer("Invalid media request.", show_alert=True)
        return

    screen_key = parts[2]

    await state.set_state(ContentSettingsStates.waiting_for_media)
    await state.update_data(content_screen_key=screen_key)

    await callback.message.answer(
        "Send a photo or video for this screen.\n\n"
        "Send /cancel to cancel."
    )
    await callback.answer()


@router.message(ContentSettingsStates.waiting_for_media)
async def handle_content_media_save(
    message: Message,
    state: FSMContext,
    content_screen_settings_service: ContentScreenSettingsService,
) -> None:
    if message.text and message.text.strip().lower() == "/cancel":
        await state.clear()
        await message.answer("Media update cancelled.")
        return

    data = await state.get_data()
    screen_key = data.get("content_screen_key")

    if not isinstance(screen_key, str):
        await state.clear()
        await message.answer("Media session expired. Please try again.")
        return

    media_file_id: str | None = None
    media_type: str | None = None

    if message.photo:
        media_file_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.video:
        media_file_id = message.video.file_id
        media_type = "video"
    else:
        await message.answer(
            "Please send a photo or video.\n"
            "Send /cancel to cancel."
        )
        return

    updated = await content_screen_settings_service.update_media(
        screen_key=screen_key,
        media_file_id=media_file_id,
        media_type=media_type,
    )

    await state.clear()

    if not updated:
        await message.answer("Could not update media.")
        return

    await message.answer("✅ Media updated.")


@router.callback_query(F.data.startswith("admin:content_media_remove:"))
async def handle_content_media_remove(
    callback: CallbackQuery,
    content_screen_settings_service: ContentScreenSettingsService,
) -> None:
    if callback.data is None:
        return

    parts = callback.data.split(":", 2)

    if len(parts) != 3:
        await callback.answer("Invalid media request.", show_alert=True)
        return

    screen_key = parts[2]

    updated = await content_screen_settings_service.update_media(
        screen_key=screen_key,
        media_file_id=None,
        media_type=None,
    )

    if not updated:
        await callback.answer(
            "Could not remove media.",
            show_alert=True,
        )
        return

    await callback.answer("Media removed.", show_alert=True)


@router.callback_query(F.data == "admin:content:today_insights")
async def handle_today_insights_settings(
    callback: CallbackQuery,
    content_screen_settings_service: ContentScreenSettingsService,
) -> None:
    if callback.message is None:
        return

    settings = await content_screen_settings_service.get("today_insights")

    if settings is None:
        await callback.answer(
            "Today's Insights settings not found.",
            show_alert=True,
        )
        return

    media_status = (
        f"{settings.media_type.upper()} configured"
        if settings.media_file_id and settings.media_type
        else "No media"
    )

    text = (
        "🔥 TODAY'S INSIGHTS SETTINGS\n\n"
        f"Heading:\n{settings.heading or 'Not set'}\n\n"
        f"Info:\n{settings.body or 'Not set'}\n\n"
        f"Footer:\n{settings.footer or 'Not set'}\n\n"
        f"Registration Link:\n"
        f"{settings.registration_url or 'Not set'}\n\n"
        f"Promo Code:\n{settings.promo_code or 'Not set'}\n\n"
        f"Media: {media_status}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ CHANGE HEADING",
                    callback_data="admin:content_edit:today_insights:heading",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 CHANGE INFO",
                    callback_data="admin:content_edit:today_insights:body",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🧾 CHANGE FOOTER",
                    callback_data="admin:content_edit:today_insights:footer",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🖼 CHANGE MEDIA",
                    callback_data="admin:content_media:today_insights",
                ),
                InlineKeyboardButton(
                    text="🗑 REMOVE MEDIA",
                    callback_data="admin:content_media_remove:today_insights",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔗 REGISTRATION LINK",
                    callback_data="admin:content_edit:today_insights:registration_url",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎟 PROMO CODE",
                    callback_data="admin:content_edit:today_insights:promo_code",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ BACK",
                    callback_data="admin:content_settings",
                )
            ],
        ]
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "admin:content:live_stats")
async def handle_live_stats_settings(
    callback: CallbackQuery,
    content_screen_settings_service: ContentScreenSettingsService,
) -> None:
    if callback.message is None:
        return

    settings = await content_screen_settings_service.get("live_stats")

    if settings is None:
        await callback.answer(
            "Live Stats settings not found.",
            show_alert=True,
        )
        return

    media_status = (
        f"{settings.media_type.upper()} configured"
        if settings.media_file_id and settings.media_type
        else "No media"
    )

    text = (
        "🏆 LIVE STATS SETTINGS\n\n"
        f"Heading:\n{settings.heading or 'Not set'}\n\n"
        f"Info:\n{settings.body or 'Not set'}\n\n"
        f"Recent Winners / Footer:\n"
        f"{settings.footer or 'Not set'}\n\n"
        f"Registration Link:\n"
        f"{settings.registration_url or 'Not set'}\n\n"
        f"Media: {media_status}\n\n"
        "📊 Bot Members, Channel Joins and VIP Members "
        "are calculated automatically from the database."
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ CHANGE HEADING",
                    callback_data="admin:content_edit:live_stats:heading",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 CHANGE INFO",
                    callback_data="admin:content_edit:live_stats:body",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏆 CHANGE RECENT WINNERS",
                    callback_data="admin:content_edit:live_stats:footer",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🖼 CHANGE MEDIA",
                    callback_data="admin:content_media:live_stats",
                ),
                InlineKeyboardButton(
                    text="🗑 REMOVE MEDIA",
                    callback_data="admin:content_media_remove:live_stats",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔗 REGISTRATION LINK",
                    callback_data="admin:content_edit:live_stats:registration_url",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ BACK",
                    callback_data="admin:content_settings",
                )
            ],
        ]
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "admin:content:referral")
async def handle_referral_settings(
    callback: CallbackQuery,
    content_screen_settings_service: ContentScreenSettingsService,
    referral_service: ReferralService,
) -> None:
    if callback.message is None:
        return

    content = await content_screen_settings_service.get("referral")
    program = await referral_service.get_program_settings()

    if content is None:
        await callback.answer(
            "Referral content settings not found.",
            show_alert=True,
        )
        return

    media_status = (
        f"{content.media_type.upper()} configured"
        if content.media_file_id and content.media_type
        else "No media"
    )

    text = (
        "🎁 REFER & EARN SETTINGS\n\n"
        f"Heading:\n{content.heading or 'Not set'}\n\n"
        f"Info:\n{content.body or 'Not set'}\n\n"
        f"Commission: {program.commission_percent}%\n\n"
        f"VIP Link:\n{program.vip_link or 'Not set'}\n\n"
        f"Promo Code:\n{program.promo_code or 'Not set'}\n\n"
        f"Claim Username:\n"
        f"{program.claim_username or 'Not set'}\n\n"
        f"Media: {media_status}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ CHANGE HEADING",
                    callback_data="admin:content_edit:referral:heading",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 CHANGE INFO",
                    callback_data="admin:content_edit:referral:body",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💰 COMMISSION %",
                    callback_data="admin:referral_edit:commission",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔗 VIP LINK",
                    callback_data="admin:referral_edit:vip_link",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎟 PROMO CODE",
                    callback_data="admin:referral_edit:promo_code",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 CLAIM USERNAME",
                    callback_data="admin:referral_edit:claim_username",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🖼 CHANGE MEDIA",
                    callback_data="admin:content_media:referral",
                ),
                InlineKeyboardButton(
                    text="🗑 REMOVE MEDIA",
                    callback_data="admin:content_media_remove:referral",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ BACK",
                    callback_data="admin:content_settings",
                )
            ],
        ]
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
    )
    await callback.answer()


_REFERRAL_EDIT_LABELS = {
    "commission": "Commission %",
    "vip_link": "VIP Link",
    "promo_code": "Promo Code",
    "claim_username": "Claim Username",
}


@router.callback_query(F.data.startswith("admin:referral_edit:"))
async def handle_referral_edit_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if callback.message is None or callback.data is None:
        return

    field = callback.data.rsplit(":", 1)[-1]

    if field not in _REFERRAL_EDIT_LABELS:
        await callback.answer(
            "Unknown referral setting.",
            show_alert=True,
        )
        return

    await state.set_state(
        ReferralSettingsStates.waiting_for_value
    )
    await state.update_data(referral_field=field)

    await callback.message.answer(
        f"✏️ Send new <b>{_REFERRAL_EDIT_LABELS[field]}</b>.\n\n"
        "Send /cancel to cancel."
    )
    await callback.answer()


@router.message(ReferralSettingsStates.waiting_for_value)
async def handle_referral_edit_save(
    message: Message,
    state: FSMContext,
    referral_service: ReferralService,
) -> None:
    if not message.text:
        await message.answer("Please send a text value.")
        return

    value = message.text.strip()

    if value.lower() == "/cancel":
        await state.clear()
        await message.answer("❌ Referral settings edit cancelled.")
        return

    data = await state.get_data()
    field = data.get("referral_field")

    if field == "commission":
        try:
            commission = int(value)
        except ValueError:
            await message.answer(
                "Commission must be a number from 0 to 100."
            )
            return

        if not 0 <= commission <= 100:
            await message.answer(
                "Commission must be between 0 and 100."
            )
            return

        await referral_service.update_program_settings(
            commission_percent=commission,
        )

    elif field == "vip_link":
        await referral_service.update_program_settings(
            vip_link=value,
        )

    elif field == "promo_code":
        await referral_service.update_program_settings(
            promo_code=value,
        )

    elif field == "claim_username":
        await referral_service.update_program_settings(
            claim_username=value.lstrip("@"),
        )

    else:
        await state.clear()
        await message.answer("Unknown referral setting.")
        return

    await state.clear()

    await message.answer(
        f"✅ <b>{_REFERRAL_EDIT_LABELS[field]}</b> updated successfully.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ BACK TO REFER & EARN SETTINGS",
                        callback_data="admin:content:referral",
                    )
                ]
            ]
        ),
    )


@router.callback_query(F.data == "admin:content:how_it_works")
async def handle_how_it_works_settings(
    callback: CallbackQuery,
    content_screen_settings_service: ContentScreenSettingsService,
) -> None:
    if callback.message is None:
        return

    settings = await content_screen_settings_service.get(
        "how_it_works"
    )

    if settings is None:
        await callback.answer(
            "How It Works settings not found.",
            show_alert=True,
        )
        return

    text = (
        "📖 HOW IT WORKS SETTINGS\n\n"
        f"Heading:\n{settings.heading or 'Not set'}\n\n"
        f"Instructions:\n{settings.body or 'Not set'}\n\n"
        f"Registration Link:\n"
        f"{settings.registration_url or 'Not set'}\n\n"
        f"Promo Code:\n"
        f"{settings.promo_code or 'Not set'}\n\n"
        f"Support Username:\n"
        f"{settings.support_username or 'Not set'}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ CHANGE HEADING",
                    callback_data=(
                        "admin:content_edit:how_it_works:heading"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 CHANGE INSTRUCTIONS",
                    callback_data=(
                        "admin:content_edit:how_it_works:body"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔗 REGISTRATION LINK",
                    callback_data=(
                        "admin:content_edit:how_it_works:"
                        "registration_url"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎁 PROMO CODE",
                    callback_data=(
                        "admin:content_edit:how_it_works:"
                        "promo_code"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="💬 SUPPORT USERNAME",
                    callback_data=(
                        "admin:content_edit:how_it_works:"
                        "support_username"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ BACK",
                    callback_data="admin:content_settings",
                )
            ],
        ]
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "admin:content:notifications")
async def handle_notifications_settings(
    callback: CallbackQuery,
    content_screen_settings_service: ContentScreenSettingsService,
) -> None:
    if callback.message is None:
        return

    settings = await content_screen_settings_service.get(
        "notifications"
    )

    if settings is None:
        await callback.answer(
            "Notifications settings not found.",
            show_alert=True,
        )
        return

    text = (
        "🔔 NOTIFICATIONS SETTINGS\n\n"
        f"Heading:\n{settings.heading or 'Not set'}\n\n"
        f"Info:\n{settings.body or 'Not set'}\n\n"
        "ℹ️ User ON/OFF status is stored separately "
        "for every user in the database."
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ CHANGE HEADING",
                    callback_data=(
                        "admin:content_edit:notifications:heading"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 CHANGE INFO",
                    callback_data=(
                        "admin:content_edit:notifications:body"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ BACK",
                    callback_data="admin:content_settings",
                )
            ],
        ]
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "admin:content:support")
async def handle_support_settings(
    callback: CallbackQuery,
    content_screen_settings_service: ContentScreenSettingsService,
) -> None:
    if callback.message is None:
        return

    settings = await content_screen_settings_service.get("support")

    if settings is None:
        await callback.answer(
            "Support settings not found.",
            show_alert=True,
        )
        return

    text = (
        "💬 SUPPORT SETTINGS\n\n"
        f"Heading:\n{settings.heading or 'Not set'}\n\n"
        f"Info:\n{settings.body or 'Not set'}\n\n"
        f"Support Username:\n"
        f"{settings.support_username or 'Not set'}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ CHANGE HEADING",
                    callback_data="admin:content_edit:support:heading",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 CHANGE INFO",
                    callback_data="admin:content_edit:support:body",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💬 SUPPORT USERNAME",
                    callback_data=(
                        "admin:content_edit:support:support_username"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ BACK",
                    callback_data="admin:content_settings",
                )
            ],
        ]
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "admin:referral_stats")
async def handle_referral_stats(
    callback: CallbackQuery,
    referral_service: ReferralService,
) -> None:
    if not isinstance(callback.message, Message):
        return

    leaderboard = await referral_service.get_referral_leaderboard()

    if not leaderboard:
        await callback.message.edit_text(
            "📊 <b>REFERRAL STATS</b>\n\n"
            "No referrals have been recorded yet.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="⬅️ BACK",
                            callback_data="admin:content:referral",
                        )
                    ]
                ]
            ),
        )
        await callback.answer()
        return

    total_referrals = sum(
        count for _, count in leaderboard
    )

    lines = [
        "📊 <b>REFERRAL STATS</b>",
        "",
        f"👥 <b>Total Referrals:</b> {total_referrals}",
        f"🏆 <b>Total Referrers:</b> {len(leaderboard)}",
        "",
        "━━━━━━━━━━━━━━━━━━",
        "",
        "🏆 <b>TOP REFERRERS</b>",
    ]

    for index, (user, count) in enumerate(
        leaderboard,
        start=1,
    ):
        if user.username:
            display_name = f"@{user.username}"
        else:
            display_name = (
                user.first_name
                or user.last_name
                or f"User {user.telegram_user_id}"
            )

        lines.append(
            f"{index}. {escape(display_name)} — "
            f"<b>{count}</b> referrals"
        )

    lines.extend(
        [
            "",
            "━━━━━━━━━━━━━━━━━━",
        ]
    )

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ BACK TO REFERRAL SETTINGS",
                        callback_data="admin:content:referral",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🛡 ADMIN PANEL",
                        callback_data="admin:back",
                    )
                ],
            ]
        ),
    )

    await callback.answer()


@router.callback_query(F.data == "owner:channel_settings")
async def handle_owner_channel_settings(
    callback: CallbackQuery,
    admin_service: AdminService,
    channel_settings_service: ChannelSettingsService,
) -> None:
    if not await admin_service.is_owner(callback.from_user.id):
        await callback.answer("⛔ Owner only", show_alert=True)
        return

    channel = await channel_settings_service.get_required_channel()

    if channel is None:
        text = (
            "📢 <b>CHANNEL SETTINGS</b>\n\n"
            "No active required channel is configured."
        )
    else:
        username = (
            f"@{channel.username.lstrip('@')}"
            if channel.username
            else "Not set"
        )
        invite_url = channel.invite_url or "Not set"

        text = (
            "📢 <b>CHANNEL SETTINGS</b>\n\n"
            f"<b>Current Channel:</b> {escape(channel.title)}\n"
            f"<b>Username:</b> {escape(username)}\n"
            f"<b>Join URL:</b> {escape(invite_url)}\n\n"
            "Only the bot owner can change this channel."
        )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ CHANGE CHANNEL",
                    callback_data="owner:channel_change",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ BACK",
                    callback_data="owner:back",
                )
            ],
        ]
    )

    if callback.message is not None:
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
        )

    await callback.answer()


@router.callback_query(F.data == "owner:channel_change")
async def handle_owner_channel_change(
    callback: CallbackQuery,
    state: FSMContext,
    admin_service: AdminService,
) -> None:
    if not await admin_service.is_owner(callback.from_user.id):
        await callback.answer("⛔ Owner only", show_alert=True)
        return

    await state.clear()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌐 PUBLIC CHANNEL",
                    callback_data="owner:channel_public",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔒 PRIVATE CHANNEL",
                    callback_data="owner:channel_private",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ CANCEL",
                    callback_data="owner:channel_settings",
                )
            ],
        ]
    )

    if callback.message is not None:
        await callback.message.edit_text(
            "📢 <b>CHANGE REQUIRED CHANNEL</b>\n\n"
            "Choose the channel type.",
            reply_markup=keyboard,
        )

    await callback.answer()


@router.callback_query(F.data == "owner:channel_public")
async def handle_owner_public_channel(
    callback: CallbackQuery,
    state: FSMContext,
    admin_service: AdminService,
) -> None:
    if not await admin_service.is_owner(callback.from_user.id):
        await callback.answer("⛔ Owner only", show_alert=True)
        return

    await state.set_state(
        ChannelSettingsStates.waiting_for_channel_username
    )

    if callback.message is not None:
        await callback.message.edit_text(
            "🌐 <b>PUBLIC CHANNEL</b>\n\n"
            "Send the channel username.\n\n"
            "Example: <code>@sportswinnerchannel</code>\n\n"
            "⚠️ Add the bot as an administrator first."
        )

    await callback.answer()


@router.callback_query(F.data == "owner:channel_private")
async def handle_owner_private_channel(
    callback: CallbackQuery,
    state: FSMContext,
    admin_service: AdminService,
) -> None:
    if not await admin_service.is_owner(callback.from_user.id):
        await callback.answer("⛔ Owner only", show_alert=True)
        return

    await state.set_state(
        ChannelSettingsStates.waiting_for_private_channel
    )

    if callback.message is not None:
        await callback.message.edit_text(
            "🔒 <b>PRIVATE CHANNEL</b>\n\n"
            "Send these on ONE message:\n\n"
            "<code>-1001234567890 https://t.me/+INVITE_LINK</code>\n\n"
            "First = Channel ID\n"
            "Second = Private invite link\n\n"
            "⚠️ Add the bot as an administrator first."
        )

    await callback.answer()


@router.message(ChannelSettingsStates.waiting_for_channel_username)
async def save_owner_required_channel(
    message: Message,
    state: FSMContext,
    bot: Bot,
    admin_service: AdminService,
    channel_settings_service: ChannelSettingsService,
) -> None:
    if message.from_user is None:
        return

    if not await admin_service.is_owner(message.from_user.id):
        await state.clear()
        return

    raw_username = (message.text or "").strip()
    if not raw_username:
        await message.answer(
            "❌ Send a valid channel username, for example "
            "<code>@sportswinnerchannel</code>."
        )
        return

    username = raw_username.lstrip("@")
    if not username:
        await message.answer("❌ Invalid channel username.")
        return

    try:
        chat = await bot.get_chat(f"@{username}")
    except TelegramBadRequest:
        await message.answer(
            "❌ I couldn't find that channel.\n\n"
            "Check the username and make sure the bot has access."
        )
        return

    if str(chat.type) not in {"channel", "ChatType.CHANNEL"}:
        await message.answer("❌ That username is not a Telegram channel.")
        return

    try:
        bot_member = await bot.get_chat_member(
            chat_id=chat.id,
            user_id=bot.id,
        )
    except TelegramBadRequest:
        await message.answer(
            "❌ I can't verify my access to that channel.\n\n"
            "Add this bot as an administrator first."
        )
        return

    if str(bot_member.status) not in {
        "administrator",
        "creator",
        "ChatMemberStatus.ADMINISTRATOR",
        "ChatMemberStatus.CREATOR",
    }:
        await message.answer(
            "❌ This bot is not an administrator in that channel.\n\n"
            "Add it as admin, then send the username again."
        )
        return

    current = await channel_settings_service.get_required_channel()
    if current is None:
        await state.clear()
        await message.answer(
            "❌ No existing required channel record was found."
        )
        return

    canonical_username = chat.username or username
    invite_url = f"https://t.me/{canonical_username}"

    updated = await channel_settings_service.update_required_channel(
        channel_id=current.id,
        telegram_chat_id=chat.id,
        title=chat.title or canonical_username,
        username=canonical_username,
        invite_url=invite_url,
    )

    if updated is None:
        await state.clear()
        await message.answer("❌ Channel update failed.")
        return

    await state.clear()

    await message.answer(
        "✅ <b>REQUIRED CHANNEL UPDATED</b>\n\n"
        f"<b>Channel:</b> {escape(updated.title)}\n"
        f"<b>Username:</b> @{escape(updated.username or canonical_username)}\n"
        f"<b>Join URL:</b> {escape(updated.invite_url or invite_url)}\n\n"
        "The Join Channel button and membership verification "
        "will now use this channel."
    )


@router.message(ChannelSettingsStates.waiting_for_private_channel)
async def save_owner_private_channel(
    message: Message,
    state: FSMContext,
    bot: Bot,
    admin_service: AdminService,
    channel_settings_service: ChannelSettingsService,
) -> None:
    if message.from_user is None:
        return

    if not await admin_service.is_owner(message.from_user.id):
        await state.clear()
        return

    parts = (message.text or "").strip().split(maxsplit=1)

    if len(parts) != 2:
        await message.answer(
            "❌ Invalid format.\n\n"
            "Send:\n"
            "<code>-1001234567890 https://t.me/+INVITE_LINK</code>"
        )
        return

    raw_chat_id, invite_url = parts

    try:
        chat_id = int(raw_chat_id)
    except ValueError:
        await message.answer("❌ Invalid channel ID.")
        return

    if not str(chat_id).startswith("-100"):
        await message.answer(
            "❌ Telegram channel ID should normally start with "
            "<code>-100</code>."
        )
        return

    if not (
        invite_url.startswith("https://t.me/+")
        or invite_url.startswith("https://t.me/joinchat/")
    ):
        await message.answer("❌ Invalid private Telegram invite link.")
        return

    try:
        chat = await bot.get_chat(chat_id)
        bot_member = await bot.get_chat_member(
            chat_id=chat_id,
            user_id=bot.id,
        )
    except TelegramBadRequest:
        await message.answer(
            "❌ I can't access that channel.\n\n"
            "Check the Channel ID and add this bot as an administrator."
        )
        return

    if str(chat.type) not in {"channel", "ChatType.CHANNEL"}:
        await message.answer("❌ That ID does not belong to a channel.")
        return

    if str(bot_member.status) not in {
        "administrator",
        "creator",
        "ChatMemberStatus.ADMINISTRATOR",
        "ChatMemberStatus.CREATOR",
    }:
        await message.answer(
            "❌ This bot is not an administrator in that channel."
        )
        return

    current = await channel_settings_service.get_required_channel()

    if current is None:
        await state.clear()
        await message.answer(
            "❌ No existing required channel record was found."
        )
        return

    updated = await channel_settings_service.update_required_channel(
        channel_id=current.id,
        telegram_chat_id=chat.id,
        title=chat.title or "Private Channel",
        username=None,
        invite_url=invite_url,
    )

    if updated is None:
        await state.clear()
        await message.answer("❌ Channel update failed.")
        return

    await state.clear()

    await message.answer(
        "✅ <b>PRIVATE REQUIRED CHANNEL UPDATED</b>\n\n"
        f"<b>Channel:</b> {escape(updated.title)}\n"
        f"<b>Channel ID:</b> <code>{updated.telegram_chat_id}</code>\n"
        f"<b>Join URL:</b> {escape(updated.invite_url or invite_url)}\n\n"
        "The Join Channel button and membership verification "
        "will now use this private channel."
    )
