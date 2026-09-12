from aiogram.fsm.state import State, StatesGroup


class DailyPickStates(StatesGroup):
    sport = State()
    event_title = State()
    selection = State()
    confidence = State()
    odds = State()
    analysis = State()
    preview = State()
