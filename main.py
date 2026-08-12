import queue
import random
import threading
import time

import customtkinter as ctk
import pystray
from PIL import Image, ImageDraw

from core.config import load_config, save_config
from core.logger import setup_logger
from core.name_changer import TgClient

MIN_INTERVAL_HOURS = 4


def create_tray_image():
    img = Image.new("RGB", (64, 64), color=(45, 45, 48))
    d = ImageDraw.Draw(img)
    d.rectangle([10, 10, 54, 54], fill=(33, 150, 243))
    d.text((22, 22), "TG", fill=(255, 255, 255))
    return img


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TG Name Changer")
        self.geometry("450x790")
        self.resizable(False, False)

        self.config = load_config()
        self.tg = None
        self.log_queue = queue.Queue()
        self.state_queue = queue.Queue()
        self.logger = setup_logger(self.log_queue.put)

        self.tray_icon = None
        self.is_running = False
        self.scheduler_thread = None

        self._build_ui()
        self.after(100, self._poll)
        self.protocol("WM_DELETE_WINDOW", self._hide_to_tray)

        if self.config["api_id"] and self.config["api_hash"]:
            self._start_tg()

        threading.Thread(target=self._setup_tray, daemon=True).start()

    # ================= UI =================
    def _build_ui(self):
        self.status_label = ctk.CTkLabel(self, text="Статус: не авторизован")
        self.status_label.pack(pady=(15, 5))

        # Контейнер для авторизации
        self.input_container = ctk.CTkFrame(self, fg_color="transparent")
        self.input_container.pack(fill="x", padx=20, pady=5)

        self.frame_creds = ctk.CTkFrame(self.input_container)
        self.frame_creds.pack(fill="x")

        ctk.CTkLabel(self.frame_creds, text="api_id").pack(anchor="w", padx=10, pady=(10, 0))
        self.entry_api_id = ctk.CTkEntry(self.frame_creds)
        self.entry_api_id.pack(fill="x", padx=10)
        if self.config["api_id"]:
            self.entry_api_id.insert(0, str(self.config["api_id"]))

        ctk.CTkLabel(self.frame_creds, text="api_hash").pack(anchor="w", padx=10, pady=(8, 0))
        self.entry_api_hash = ctk.CTkEntry(self.frame_creds, show="*")
        self.entry_api_hash.pack(fill="x", padx=10)
        self.entry_api_hash.insert(0, self.config["api_hash"])

        ctk.CTkLabel(self.frame_creds, text="Телефон (+79991234567)").pack(anchor="w", padx=10, pady=(8, 0))
        self.entry_phone = ctk.CTkEntry(self.frame_creds)
        self.entry_phone.pack(fill="x", padx=10, pady=(0, 10))
        self.entry_phone.insert(0, self.config["phone"])

        self.btn_send_code = ctk.CTkButton(self.input_container, text="Отправить код", command=self._on_send_code)
        self.btn_send_code.pack(pady=8)

        self.frame_code = ctk.CTkFrame(self.input_container)
        self.entry_code = ctk.CTkEntry(self.frame_code, placeholder_text="Код из Telegram")
        self.entry_code.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(self.frame_code, text="Войти", command=self._on_sign_in).pack(pady=(0, 10))

        self.frame_2fa = ctk.CTkFrame(self.input_container)
        self.entry_2fa = ctk.CTkEntry(self.frame_2fa, show="*", placeholder_text="Пароль 2FA")
        self.entry_2fa.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(self.frame_2fa, text="Подтвердить", command=self._on_2fa).pack(pady=(0, 10))

        # Панель управления (скрыта до авторизации)
        self.control_frame = ctk.CTkFrame(self)

        ctk.CTkLabel(self.control_frame, text="Интервал (от 4 часов до 3 дней)").pack(anchor="w", padx=10, pady=(10, 0))
        self.interval_slider = ctk.CTkSlider(self.control_frame, from_=MIN_INTERVAL_HOURS, to=72, number_of_steps=68)
        self.interval_slider.set(max(MIN_INTERVAL_HOURS, self.config.get("interval_hours", 6)))
        self.interval_slider.pack(fill="x", padx=10)
        self.interval_label = ctk.CTkLabel(self.control_frame, text=self._format_interval(self.interval_slider.get()))
        self.interval_label.pack()
        self.interval_slider.configure(command=self._on_interval_change)

        ctk.CTkLabel(self.control_frame, text="Разброс времени (± минут)").pack(anchor="w", padx=10, pady=(10, 0))
        self.jitter_slider = ctk.CTkSlider(self.control_frame, from_=0, to=120, number_of_steps=24)
        self.jitter_slider.set(self.config.get("jitter_minutes", 30))
        self.jitter_slider.pack(fill="x", padx=10)
        self.jitter_label = ctk.CTkLabel(self.control_frame, text=f"±{int(self.jitter_slider.get())} мин")
        self.jitter_label.pack()
        self.jitter_slider.configure(command=self._on_jitter_change)

        ctk.CTkLabel(self.control_frame, text="Оригинальное имя (для восстановления)").pack(anchor="w", padx=10, pady=(10, 0))
        self.entry_original = ctk.CTkEntry(self.control_frame)
        self.entry_original.pack(fill="x", padx=10)
        orig = f"{self.config.get('original_first_name', '')} {self.config.get('original_last_name', '')}".strip()
        self.entry_original.insert(0, orig)

        ctk.CTkLabel(self.control_frame, text="Имена (по одному на строку)").pack(anchor="w", padx=10, pady=(10, 0))
        self.names_box = ctk.CTkTextbox(self.control_frame, height=100)
        self.names_box.pack(fill="x", padx=10, pady=(0, 10))
        self.names_box.insert("1.0", "\n".join(self.config.get("names", [])))

        btn_row = ctk.CTkFrame(self.control_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkButton(btn_row, text="Сменить сейчас", command=self._on_change_now).pack(side="left", expand=True, padx=5)
        self.btn_toggle = ctk.CTkButton(btn_row, text="Старт", command=self._on_toggle)
        self.btn_toggle.pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_row, text="Вернуть", command=self._on_restore).pack(side="left", expand=True, padx=5)

        # Лог
        self.log_box = ctk.CTkTextbox(self, height=160, state="disabled")
        self.log_box.pack(fill="both", expand=True, padx=20, pady=(10, 20))

    # ================= Действия =================
    @staticmethod
    def _format_interval(hours):
        hours = int(hours)
        if hours >= 24:
            days = hours // 24
            rest = hours % 24
            return f"{hours} ч ({days} д {rest} ч)" if rest else f"{hours} ч ({days} д)"
        return f"{hours} ч"

    def _on_interval_change(self, value):
        self.interval_label.configure(text=self._format_interval(value))

    def _on_jitter_change(self, value):
        self.jitter_label.configure(text=f"±{int(value)} мин")
    def _on_change_now(self):
        if not self.tg:
            self.logger.warning("Сначала авторизуйся")
            return
        names = self._get_names(exclude_current=True)
        if not names:
            self.logger.warning("Добавь хотя бы одно имя")
            return
        first, last = random.choice(names)
        self.tg.change_name(first, last)

    def _on_restore(self):
        if not self.tg:
            self.logger.warning("Сначала авторизуйся")
            return
        orig = self.entry_original.get().strip()
        if not orig:
            self.logger.warning("Укажи оригинальное имя")
            return
        parts = orig.split(maxsplit=1)
        first = parts[0]
        last = parts[1] if len(parts) > 1 else ""
        self.config["original_first_name"] = first
        self.config["original_last_name"] = last
        self._save_settings()
        self.tg.change_name(first, last, restore=True)

    def _on_toggle(self):
        if self.is_running:
            self.is_running = False
            self.btn_toggle.configure(text="Старт")
            self.logger.info("Планировщик остановлен")
        else:
            if not self.tg:
                self.logger.warning("Сначала авторизуйся")
                return
            names = self._get_names(exclude_current=True)
            if not names:
                self.logger.warning("Добавь хотя бы одно имя")
                return
            self._save_settings()
            self.is_running = True
            self.btn_toggle.configure(text="Пауза")
            self.logger.info("Планировщик запущен")
            # Сразу меняем имя при старте
            first, last = random.choice(names)
            self.tg.change_name(first, last)
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self.scheduler_thread.start()

    def _scheduler_loop(self):
        while self.is_running:
            interval_h = max(MIN_INTERVAL_HOURS, int(self.interval_slider.get()))
            jitter_m = int(self.jitter_slider.get())
            jitter_s = random.randint(-jitter_m * 60, jitter_m * 60)
            sleep_s = max(60, interval_h * 3600 + jitter_s)
            self.logger.info(f"Следующая смена через {sleep_s // 60} мин")
            for _ in range(int(sleep_s)):
                if not self.is_running:
                    return
                time.sleep(1)
            if not self.is_running:
                return
            names = self._get_names(exclude_current=True)
            if names:
                first, last = random.choice(names)
                self.tg.change_name(first, last)

    def _get_names(self, exclude_current=False):
        raw = self.names_box.get("1.0", "end").strip()
        names = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            first = parts[0]
            last = parts[1] if len(parts) > 1 else ""
            names.append((first, last))
        if exclude_current and len(names) > 1:
            current = self.status_label.cget("text").replace("Текущее имя: ", "").strip()
            names = [n for n in names if f"{n[0]} {n[1]}".strip() != current]
        return names

    def _on_send_code(self):
        api_id_raw = self.entry_api_id.get().strip()
        api_hash = self.entry_api_hash.get().strip()
        phone = self.entry_phone.get().strip()

        if not api_id_raw.isdigit() or len(api_hash) < 10 or not phone.startswith("+"):
            self.logger.warning("Проверь поля: api_id — цифры, api_hash, телефон с +")
            return

        self.config.update({"api_id": int(api_id_raw), "api_hash": api_hash, "phone": phone})
        save_config(self.config)

        self._start_tg()
        self.tg.send_code(phone)

    def _on_sign_in(self):
        code = self.entry_code.get().strip()
        if code and self.tg:
            self.tg.sign_in(self.config["phone"], code)

    def _on_2fa(self):
        password = self.entry_2fa.get().strip()
        if password and self.tg:
            self.tg.sign_in_2fa(password)

    # ================= Трей =================
    def _setup_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem("Показать окно", self._show_window, default=True),
            pystray.MenuItem("Пауза", self._toggle_pause, checked=lambda item: not self.is_running),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Выход", self._quit_app),
        )
        self.tray_icon = pystray.Icon("tg_name_changer", create_tray_image(), "TG Name Changer", menu)
        self.tray_icon.run()

    def _hide_to_tray(self):
        self.withdraw()
        if self.tray_icon:
            self.tray_icon.notify("Приложение свёрнуто в трей", "TG Name Changer")

    def _show_window(self, icon=None, item=None):
        self.after(0, self._restore_window)

    def _restore_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def _toggle_pause(self, icon=None, item=None):
        self._on_toggle()

    def _quit_app(self, icon=None, item=None):
        self.is_running = False
        self._save_settings()
        if self.tg:
            self.tg.shutdown()
        if self.tray_icon:
            self.tray_icon.stop()
        self.after(0, self.destroy)

    # ================= Служебное =================
    def _start_tg(self):
        if self.tg:
            self.tg.shutdown()
            self.tg = None
        if self.config["api_id"] and self.config["api_hash"]:
            try:
                self.tg = TgClient(
                    self.config["api_id"],
                    self.config["api_hash"],
                    self.log_queue.put,
                    self.state_queue.put,
                )
                self.tg.check_session()
            except Exception as e:
                self.logger.error(f"Не удалось создать клиент: {e}")

    def _save_settings(self):
        names = self._get_names()
        # Не перезаписываем список пустым, если поле ещё не заполнено
        if names:
            self.config["names"] = [f"{f} {l}".strip() for f, l in names]
        self.config["interval_hours"] = max(MIN_INTERVAL_HOURS, int(self.interval_slider.get()))
        self.config["jitter_minutes"] = int(self.jitter_slider.get())
        save_config(self.config)
        
    def _poll(self):
        while True:
            try:
                self._append_log(self.log_queue.get_nowait())
            except queue.Empty:
                break
        while True:
            try:
                self._handle_state(*self.state_queue.get_nowait())
            except queue.Empty:
                break
        self.after(100, self._poll)

    def _append_log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _handle_state(self, name, payload):
        if name == "code_sent":
            self.frame_code.pack(fill="x")
        elif name == "need_2fa":
            self.frame_2fa.pack(fill="x")
        elif name == "authorized":
            self.status_label.configure(text=f"Авторизован: {payload.first_name}")
            self.input_container.pack_forget()
            self.control_frame.pack(fill="x", padx=20, pady=5)
            # Сохраняем оригинальное имя при первом входе
            if not self.config.get("original_first_name"):
                self.config["original_first_name"] = payload.first_name or ""
                self.config["original_last_name"] = payload.last_name or ""
                save_config(self.config)
                self.logger.info("Оригинальное имя сохранено")
            if not self.entry_original.get().strip():
                orig = f"{payload.first_name or ''} {payload.last_name or ''}".strip()
                self.entry_original.insert(0, orig)
            if self.tray_icon:
                self.tray_icon.notify(f"Вход выполнен: {payload.first_name}", "TG Name Changer")
        elif name == "name_changed":
            self.status_label.configure(text=f"Текущее имя: {payload}")
            if self.tray_icon:
                self.tray_icon.notify(f"Имя изменено на: {payload}", "TG Name Changer")
        elif name == "flood_wait":
            self.logger.warning(f"Telegram просит подождать {payload} сек")
        elif name == "session_expired":
            self.status_label.configure(text="Сессия истекла — авторизуйся заново")
            self.input_container.pack(fill="x", padx=20, pady=5)
            self.control_frame.pack_forget()
        elif name == "error":
            self.status_label.configure(text="Ошибка — смотри лог")


if __name__ == "__main__":
    app = App()
    app.mainloop()