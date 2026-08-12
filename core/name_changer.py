import asyncio
import os
import threading

from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    PasswordHashInvalidError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
)
from telethon.tl.functions.account import UpdateProfileRequest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")


class TgClient:
    """Единственный клиент Telethon для всего приложения."""

    def __init__(self, api_id: int, api_hash: str, log, state):
        self.api_id = api_id
        self.api_hash = api_hash
        self.log = log
        self.state = state

        os.makedirs(SESSIONS_DIR, exist_ok=True)
        session_path = os.path.join(SESSIONS_DIR, "user")

        self._client = None
        self._error = None
        self._loop = asyncio.new_event_loop()
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run_loop, args=(session_path,), daemon=True)
        self._thread.start()
        self._ready.wait(timeout=15)

        if self._error is not None:
            raise self._error
        self.client = self._client

    def _run_loop(self, session_path):
        asyncio.set_event_loop(self._loop)
        try:
            self._client = TelegramClient(session_path, self.api_id, self.api_hash)
        except Exception as e:
            self._error = e
        finally:
            self._ready.set()
        if self._error is None:
            self._loop.run_forever()

    def _submit(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    # --- Авторизация ---
    def check_session(self):
        self._submit(self._check_session())

    def send_code(self, phone: str):
        self._submit(self._send_code(phone))

    def sign_in(self, phone: str, code: str):
        self._submit(self._sign_in(phone, code))

    def sign_in_2fa(self, password: str):
        self._submit(self._sign_in_2fa(password))

    # --- Смена имени ---
    def change_name(self, first_name: str, last_name: str = "", restore: bool = False):
        self._submit(self._change_name(first_name, last_name, restore))

    def shutdown(self):
        """Корректное завершение: сначала отключаем клиент, потом стопим цикл."""
        try:
            self._submit(self.client.disconnect()).result(timeout=5)
        except Exception:
            pass
        self._loop.call_soon_threadsafe(self._loop.stop)

    # --- Корутины ---
    async def _check_session(self):
        try:
            await self.client.connect()
            if await self.client.is_user_authorized():
                me = await self.client.get_me()
                self.log(f"Сессия активна: {me.first_name}")
                self.state(("authorized", me))
            else:
                self.log("Сессия истекла — нужна повторная авторизация")
                self.state(("session_expired", None))
        except Exception as e:
            self.log(f"Ошибка проверки сессии: {e}")
            self.state(("session_expired", None))

    async def _send_code(self, phone: str):
        try:
            await self.client.connect()
            await self.client.send_code_request(phone)
            self.log("Код отправлен — проверь Telegram")
            self.state(("code_sent", None))
        except FloodWaitError as e:
            self.log(f"FloodWait: подожди {e.seconds} сек")
            self.state(("error", None))
        except PhoneNumberInvalidError:
            self.log("Неверный формат номера. Пример: +79991234567")
            self.state(("error", None))
        except Exception as e:
            self.log(f"Ошибка отправки кода: {e}")
            self.state(("error", None))

    async def _sign_in(self, phone: str, code: str):
        try:
            me = await self.client.sign_in(phone=phone, code=code)
            self.log(f"Вход выполнен: {me.first_name}")
            self.state(("authorized", me))
        except SessionPasswordNeededError:
            self.log("Включён 2FA — введи пароль")
            self.state(("need_2fa", None))
        except (PhoneCodeInvalidError, PhoneCodeExpiredError):
            self.log("Код неверный или устарел — запроси новый")
            self.state(("error", None))
        except FloodWaitError as e:
            self.log(f"FloodWait: подожди {e.seconds} сек")
            self.state(("error", None))
        except Exception as e:
            self.log(f"Ошибка входа: {e}")
            self.state(("error", None))

    async def _sign_in_2fa(self, password: str):
        try:
            me = await self.client.sign_in(password=password)
            self.log(f"Вход выполнен: {me.first_name}")
            self.state(("authorized", me))
        except PasswordHashInvalidError:
            self.log("Неверный пароль 2FA")
            self.state(("need_2fa", None))
        except Exception as e:
            self.log(f"Ошибка 2FA: {e}")
            self.state(("error", None))

    async def _change_name(self, first_name: str, last_name: str, restore: bool = False):
        try:
            await self.client.connect()
            await self.client(UpdateProfileRequest(first_name=first_name, last_name=last_name))
            full = f"{first_name} {last_name}".strip()
            if restore:
                self.log(f"Оригинальное имя восстановлено: {full}")
            else:
                self.log(f"Имя изменено на: {full}")
            self.state(("name_changed", full))
        except FloodWaitError as e:
            self.log(f"FloodWait: подожди {e.seconds} сек")
            self.state(("flood_wait", e.seconds))
        except Exception as e:
            self.log(f"Ошибка смены имени: {e}")
            self.state(("error", str(e)))