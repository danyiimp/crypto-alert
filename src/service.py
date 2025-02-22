import asyncio

import aiohttp
from aiogram import Bot
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.constants import TOKEN_STATUS_ENDPOINT
from src.database import make_session
from src.models import Coin, User, UserCoin
from src.schemas import Subscription, TokenStatusResponse
from src.utils import custom_retry, get_aiohttp_trace_config


def add_user(tg_id: int, session: Session):
    session.add(User(tg_id=tg_id))
    session.commit()


def get_user(tg_id: int, session: Session):
    stmt = select(User).where(User.tg_id == tg_id)
    return session.execute(stmt).scalar_one()


async def add_coin(blockchain: str, token_address: str, db_session: Session):
    async with aiohttp.ClientSession(
        trace_configs=[get_aiohttp_trace_config()]
    ) as session:
        res = await parse_coin_info(blockchain, token_address, session)

    coin = Coin(
        chain_id=blockchain,
        token_address=token_address,
        token_name=res.base_token.symbol,
        price=res.price_usd,
    )
    db_session.add(coin)
    db_session.commit()
    return coin


async def get_coin(blockchain: str, token_address: str, session: Session):
    stmt = select(Coin).where(Coin.token_address == token_address)
    res = session.execute(stmt).scalar_one_or_none()

    if res is None:
        return await add_coin(blockchain, token_address, session)
    else:
        return res


def get_coins(session: Session):
    stmt = select(Coin)
    return session.execute(stmt).scalars().all()


def update_coin_price(token_address: str, price: float, session: Session):
    stmt = update(Coin).where(Coin.token_address == token_address).values(price=price)
    result = session.execute(stmt)

    if result.rowcount == 0:
        raise ValueError(f"Coin with token address {token_address} not found")

    session.commit()


async def update_prices_and_notify_subscribers(bot: Bot):
    with make_session() as db_session:
        coins = get_coins(db_session)
        for coin in coins:
            async with aiohttp.ClientSession(
                trace_configs=[get_aiohttp_trace_config()]
            ) as session:
                coin_info = await parse_coin_info(
                    coin.chain_id,
                    coin.token_address,
                    session,
                )
                update_coin_price(coin.token_address, coin_info.price_usd, db_session)
            for user in coin.users:
                stmt = select(UserCoin).where(
                    UserCoin.user_id == user.id, UserCoin.coin_id == coin.id
                )
                user_coin = db_session.execute(stmt).scalar_one()
                alert_price = user_coin.alert_price

                if coin_info.price_usd < alert_price:
                    await notify_subscriber(
                        user.tg_id, coin.token_name, alert_price, bot
                    )


async def notify_subscriber(tg_id: int, token_name: str, alert_price: float, bot: Bot):
    text = f"{token_name} now lower than {alert_price}!"
    await bot.send_message(tg_id, text, disable_web_page_preview=True)
    await asyncio.sleep(0.05)  # 20 messages per second (Limit: 30 messages per second)


async def subscribe_user_to_coin(
    tg_id: int,
    blockchain: str,
    token_address: str,
    alert_price: float,
    session: Session,
):
    user = get_user(tg_id, session)
    coin = await get_coin(blockchain, token_address, session)
    user.coins.append(coin)

    stmt = select(UserCoin).where(
        UserCoin.user_id == user.id, UserCoin.coin_id == coin.id
    )
    user_coin = session.execute(stmt).scalar_one()
    user_coin.alert_price = alert_price

    session.commit()


async def unsubscribe_user_from_coin(
    tg_id: int, blockchain: str, token_address: str, session: Session
):
    user = get_user(tg_id, session)
    coin = await get_coin(blockchain, token_address, session)
    if coin in user.coins:
        user.coins.remove(coin)
        session.commit()
    else:
        raise ValueError(
            f"User with id {tg_id} is not subscribed to coin with token_address {token_address}"
        )
    session.commit()


def get_user_subscriptions(tg_id: int, session: Session):
    stmt = select(User).where(User.tg_id == tg_id)
    user = session.execute(stmt).scalar_one()

    subscriptions: list[Subscription] = []
    for coin in user.coins:
        subscription = Subscription.model_validate(coin)
        stmt = select(UserCoin).where(
            UserCoin.user_id == user.id, UserCoin.coin_id == coin.id
        )
        user_coin = session.execute(stmt).scalar_one()
        subscription.alert_price = user_coin.alert_price
        subscriptions.append(subscription)

    return subscriptions


@custom_retry
async def parse_coin_info(
    blockchain: str,
    token_address: str,
    session: aiohttp.ClientSession,
):
    async with session.get(
        TOKEN_STATUS_ENDPOINT.format(chain_id=blockchain, pair_id=token_address)
    ) as response:
        match response.status:
            case 200:
                data = await response.json()
                return TokenStatusResponse(**data).pairs[0]
            case _:
                response.raise_for_status()
                raise ValueError(f"Unexpected status code: {response.status}")
