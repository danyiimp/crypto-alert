from attr import dataclass


@dataclass
class Token:
    name: str
    address: str


BASE_API_URL = "https://api.dexscreener.com"
TOKEN_STATUS_ENDPOINT = f"{BASE_API_URL}/latest/dex/pairs/{{chain_id}}/{{pair_id}}"


DATABASE_URI = "sqlite:///data/database.db"

BLOCKCHAINS_TOKENS_MAP = {
    "ton": [Token("FPIBANK", "EQAyrrAjgSuyHrgGO1HimNbGV9tVLndZ3uocLaOyTw_FgegD")]
}
