from aiogram.fsm.state import State, StatesGroup


class ChannelSettingsStates(StatesGroup):
    waiting_for_channel_username = State()
    waiting_for_private_channel = State()
