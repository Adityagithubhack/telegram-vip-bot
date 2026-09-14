from aiogram.fsm.state import State, StatesGroup


class ContentSettingsStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_media = State()


class ReferralSettingsStates(StatesGroup):
    waiting_for_value = State()
