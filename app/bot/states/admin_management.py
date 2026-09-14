from aiogram.fsm.state import State, StatesGroup


class AdminManagementStates(StatesGroup):
    waiting_for_admin_telegram_id = State()
