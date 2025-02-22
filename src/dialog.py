import json
import operator
from typing import Any

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Back, Button, Column, Next, Select
from aiogram_dialog.widgets.text import Const, Format

from src.constants import BLOCKCHAINS_TOKENS_MAP, Token
from src.database import make_session
from src.schemas import Subscription
from src.service import (
    get_user_subscriptions,
    subscribe_user_to_coin,
    unsubscribe_user_from_coin,
)
from src.utils import cast_away_optional


class SG(StatesGroup):
    HOME = State()
    SUBSCRIPTIONS = State()

    SUBSCRIPTION = State()
    UNSUBSCRIBED = State()

    BLOCKCHAINS = State()
    TOKENS = State()
    SET_ALERT_PRICE = State()
    ALERT_PRICE_IS_SET = State()


def create_blockchains_buttons():
    data = {blockchain: blockchain for blockchain in BLOCKCHAINS_TOKENS_MAP}

    async def clicked(callback: CallbackQuery, button: Button, manager: DialogManager):
        if button.widget_id is None:
            raise ValueError("Button widget id is none")
        manager.dialog_data["blockchain"] = data[button.widget_id]

    return [
        Next(Const(blockchain.upper()), id=blockchain, on_click=clicked)
        for blockchain in BLOCKCHAINS_TOKENS_MAP
    ]


async def clicked_subscription(
    callback: CallbackQuery,
    widget: Any,
    manager: DialogManager,
    item_id: str,
):
    manager.dialog_data["subscription"] = manager.dialog_data["subscriptions"][int(item_id)]  # fmt: skip
    await manager.switch_to(SG.SUBSCRIPTION)


async def user_subscriptions_getter(**kwargs):
    tg_id = kwargs["event_from_user"].id
    manager: DialogManager = kwargs["dialog_manager"]

    with make_session() as session:
        subscriptions = get_user_subscriptions(tg_id, session)

    manager.dialog_data["subscriptions"] = subscriptions
    return {"subscriptions": enumerate(subscriptions)}


async def clicked_unsubscribe(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
):
    tg_id = callback.from_user.id
    subscription: Subscription = manager.dialog_data["subscription"]

    with make_session() as session:
        await unsubscribe_user_from_coin(
            tg_id,
            subscription.chain_id,
            subscription.token_address,
            session,
        )
    await manager.next()


async def clicked_token(
    callback: CallbackQuery,
    widget: Any,
    manager: DialogManager,
    item_id: str,
):
    manager.dialog_data["token"] = manager.dialog_data["tokens"][int(item_id)]
    await manager.next()


async def tokens_getter(**kwargs):
    manager: DialogManager = kwargs["dialog_manager"]
    blockchain = manager.dialog_data["blockchain"]
    tokens = BLOCKCHAINS_TOKENS_MAP[blockchain]
    manager.dialog_data["tokens"] = tokens
    return {"tokens": enumerate(tokens)}


async def switch_to_blockchains(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    await manager.switch_to(SG.BLOCKCHAINS)


async def switch_to_subscriptions(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    await manager.switch_to(SG.SUBSCRIPTIONS)


async def set_alert_price_error(
    message: Message,
    dialog_: Any,
    manager: DialogManager,
    error_: ValueError,
):
    await message.answer("Alert price must be dot separated number greater than 0.")


async def set_alert_price_success(
    message: Message,
    dialog_: Any,
    manager: DialogManager,
    data,
):
    alert_price = data
    blockchain = manager.dialog_data["blockchain"]
    token: Token = manager.dialog_data["token"]

    with make_session() as session:
        await subscribe_user_to_coin(
            cast_away_optional(message.from_user).id,
            blockchain,
            token.address,
            alert_price,
            session,
        )
    await manager.next()


def validate_alert_price(value: str):
    if float(value) <= 0:
        raise ValueError("Alert price must be greater than 0")
    return value


dialog = Dialog(
    Window(
        Format("Hello, {event.from_user.full_name}"),
        Next(
            text=Const("My Subscriptions"),
            id="subscriptions",
        ),
        state=SG.HOME,
    ),
    Window(
        Const("Your Subscriptions:"),
        Column(
            Select(
                Format("{item[1].token_name}"),
                id="s_subscriptions",
                item_id_getter=operator.itemgetter(0),
                items="subscriptions",
                on_click=clicked_subscription,
            )
        ),
        Button(
            text=Const("Subscribe"),
            id="blockchains",
            on_click=switch_to_blockchains,
        ),
        Back(text=Const("Back")),
        state=SG.SUBSCRIPTIONS,
        getter=user_subscriptions_getter,
    ),
    #
    Window(
        Format("{dialog_data[subscription]}"),
        Button(
            text=Const("Unsubscribe"),
            id="unsubscribe",
            on_click=clicked_unsubscribe,
        ),
        Back(text=Const("Back")),
        state=SG.SUBSCRIPTION,
    ),
    Window(
        Format(
            "You sucessfully unsubscribed from {dialog_data[subscription].token_name}."
        ),
        Button(
            text=Const("Back to subscriptions"),
            id="back_to_subscriptions_unsubscribed",
            on_click=switch_to_subscriptions,
        ),
        state=SG.UNSUBSCRIBED,
    ),
    #
    Window(
        Const("Available Blockchains:"),
        *create_blockchains_buttons(),
        Button(
            text=Const("Back"),
            id="back_to_subscriptions",
            on_click=switch_to_subscriptions,
        ),
        state=SG.BLOCKCHAINS,
    ),
    Window(
        Const("Available Tokens:"),
        Column(
            Select(
                Format("{item[1].name}"),
                id="s_tokens",
                item_id_getter=operator.itemgetter(0),
                items="tokens",
                on_click=clicked_token,
            )
        ),
        Back(text=Const("Back")),
        state=SG.TOKENS,
        getter=tokens_getter,
    ),
    Window(
        Const("Enter the USD alert price:"),
        TextInput(
            id="set_price",
            type_factory=validate_alert_price,
            on_success=set_alert_price_success,
            on_error=set_alert_price_error,
        ),
        Back(text=Const("Back")),
        state=SG.SET_ALERT_PRICE,
    ),
    Window(
        Format("You successfully subscribed to {dialog_data[token].name}."),
        Button(
            text=Const("Back to subscriptions"),
            id="back_to_subscriptions_subscribed",
            on_click=switch_to_subscriptions,
        ),
        state=SG.ALERT_PRICE_IS_SET,
    ),
)
