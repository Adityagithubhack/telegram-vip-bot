from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.bot.states.daily_pick import DailyPickStates
from app.config.settings import get_settings
from app.services.admin_vip import AdminVipService
from app.services.daily_pick import DailyPickService
from app.services.onboarding import OnboardingService
from app.services.user import UserService

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
