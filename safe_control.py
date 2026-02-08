#!/usr/bin/env python3
"""Safe multi-device control via Telegram.

Hub mode runs the Telegram bot + HTTP server.
Agent mode connects to hub and executes *safe* commands only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import http.server
import json
import os
import queue
import socket
import sys
import threading
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import platform
    import shutil
    import subprocess
    import uuid
except Exception as exc:  # pragma: no cover - stdlib
    raise SystemExit(f"Missing stdlib dependency: {exc}")

try:
    import requests
except Exception:  # pragma: no cover
    requests = None


DEFAULT_PORT = 8000
DEFAULT_POLL_SECONDS = 3


@dataclass
class Command:
    id: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeviceState:
    device_id: str
    name: str
    last_seen: float
    queue: List[Command] = field(default_factory=list)


class HubState:
    def __init__(self, secret: str):
        self.secret = secret
        self.devices: Dict[str, DeviceState] = {}
        self.lock = threading.Lock()
        self.chat_queue: "queue.Queue[str]" = queue.Queue()

    def register(self, device_id: str, name: str) -> None:
        with self.lock:
            if device_id not in self.devices:
                self.devices[device_id] = DeviceState(
                    device_id=device_id, name=name, last_seen=time.time()
                )
            else:
                self.devices[device_id].name = name
                self.devices[device_id].last_seen = time.time()

    def enqueue(self, device_id: str, command: Command) -> None:
        with self.lock:
            if device_id not in self.devices:
                raise KeyError("Device not registered")
            self.devices[device_id].queue.append(command)

    def poll(self, device_id: str) -> List[Command]:
        with self.lock:
            if device_id not in self.devices:
                raise KeyError("Device not registered")
            device = self.devices[device_id]
            device.last_seen = time.time()
            commands = list(device.queue)
            device.queue.clear()
            return commands

    def list_devices(self) -> List[DeviceState]:
        with self.lock:
            return list(self.devices.values())


class HubRequestHandler(http.server.BaseHTTPRequestHandler):
    server_version = "SafeHub/1.0"

    def _send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def _is_authorized(self, payload: Dict[str, Any]) -> bool:
        secret = payload.get("secret")
        return bool(secret) and secret == self.server.state.secret

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._read_json()
            if not self._is_authorized(payload):
                self._send_json({"ok": False, "error": "unauthorized"}, status=403)
                return

            if self.path == "/register":
                device_id = str(payload.get("device_id"))
                name = str(payload.get("name"))
                self.server.state.register(device_id, name)
                self._send_json({"ok": True})
                return
            if self.path == "/poll":
                device_id = str(payload.get("device_id"))
                commands = self.server.state.poll(device_id)
                self._send_json(
                    {
                        "ok": True,
                        "commands": [
                            {"id": cmd.id, "action": cmd.action, "params": cmd.params}
                            for cmd in commands
                        ],
                    }
                )
                return
            if self.path == "/result":
                message = payload.get("message", "")
                if message:
                    self.server.state.chat_queue.put(str(message))
                self._send_json({"ok": True})
                return
            if self.path == "/chat":
                message = payload.get("message", "")
                if message:
                    self.server.state.chat_queue.put(str(message))
                self._send_json({"ok": True})
                return

            self._send_json({"ok": False, "error": "not_found"}, status=404)
        except Exception as exc:  # pragma: no cover - defensive
            self._send_json({"ok": False, "error": str(exc)}, status=500)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


class HubServer(http.server.ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], state: HubState):
        super().__init__(server_address, HubRequestHandler)
        self.state = state


class TelegramBot:
    def __init__(self, token: str, admin_ids: List[int]):
        if not requests:
            raise SystemExit("requests library required: pip install requests")
        self.token = token
        self.admin_ids = set(admin_ids)
        self.api_base = f"https://api.telegram.org/bot{token}"
        self.offset = 0
        self.selected_devices: Dict[int, set[str]] = {}

    def _get(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        response = requests.get(f"{self.api_base}/{method}", params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def _post(self, method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = requests.post(f"{self.api_base}/{method}", json=payload, timeout=30)
        response.raise_for_status()
        return response.json()

    def send_message(self, chat_id: int, text: str, reply_markup: Optional[Dict[str, Any]] = None) -> None:
        payload = {"chat_id": chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        self._post("sendMessage", payload)

    def answer_callback(self, callback_id: str, text: str) -> None:
        self._post("answerCallbackQuery", {"callback_query_id": callback_id, "text": text})

    def fetch_updates(self) -> List[Dict[str, Any]]:
        data = self._get("getUpdates", params={"timeout": 30, "offset": self.offset})
        results = data.get("result", [])
        if results:
            self.offset = results[-1]["update_id"] + 1
        return results


SAFE_ACTIONS = {
    "ping",
    "system_info",
    "uptime",
    "disk_usage",
    "list_dir",
    "write_note",
    "append_log",
    "create_folder",
    "open_folder",
    "show_message",
    "network_info",
    "time",
    "python_version",
    "check_path",
    "hash_file",
    "report",
    "beep",
    "list_env",
    "whoami",
    "chat",
    "stop_agent",
}


def safe_hash_file(path: str) -> str:
    import hashlib

    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def resolve_in_base(base_dir: str, target: str) -> str:
    candidate = os.path.abspath(os.path.join(base_dir, target))
    base_dir = os.path.abspath(base_dir)
    if os.path.commonpath([candidate, base_dir]) != base_dir:
        raise ValueError("Path outside base directory")
    return candidate


def collect_system_info() -> str:
    info = {
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "hostname": socket.gethostname(),
        "cpu_count": os.cpu_count(),
    }
    return "\n".join(f"{key}: {value}" for key, value in info.items())


def collect_uptime() -> str:
    if sys.platform.startswith("linux"):
        try:
            with open("/proc/uptime", "r", encoding="utf-8") as handle:
                seconds = float(handle.read().split()[0])
                return str(dt.timedelta(seconds=int(seconds)))
        except Exception:
            return "unknown"
    return "unknown"


def collect_disk_usage(path: str) -> str:
    usage = shutil.disk_usage(path)
    return f"total={usage.total} used={usage.used} free={usage.free}"


def collect_network_info() -> str:
    hostname = socket.gethostname()
    try:
        ip = socket.gethostbyname(hostname)
    except Exception:
        ip = "unknown"
    return f"hostname={hostname} ip={ip}"


def open_folder(path: str) -> str:
    if sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore[attr-defined]
        return "opened"
    if sys.platform.startswith("darwin"):
        subprocess.run(["open", path], check=False)
        return "opened"
    subprocess.run(["xdg-open", path], check=False)
    return "opened"


def render_keyboard(buttons: List[List[Dict[str, str]]]) -> Dict[str, Any]:
    return {"inline_keyboard": buttons}


def device_buttons(devices: List[DeviceState], selected: set[str]) -> List[List[Dict[str, str]]]:
    rows: List[List[Dict[str, str]]] = []
    for device in devices:
        mark = "✅" if device.device_id in selected else "⬜️"
        rows.append(
            [
                {
                    "text": f"{mark} {device.name} ({device.device_id})",
                    "callback_data": f"toggle:{device.device_id}",
                }
            ]
        )
    rows.append(
        [
            {"text": "Готово", "callback_data": "devices:done"},
            {"text": "Выбрать всех", "callback_data": "devices:all"},
        ]
    )
    return rows


def section_buttons() -> Dict[str, Any]:
    return render_keyboard(
        [
            [
                {"text": "Инфо", "callback_data": "section:info"},
                {"text": "Файлы", "callback_data": "section:files"},
            ],
            [
                {"text": "Сообщения", "callback_data": "section:messages"},
                {"text": "Утилиты", "callback_data": "section:utils"},
            ],
            [{"text": "Выбор устройств", "callback_data": "section:devices"}],
        ]
    )


def section_menu(section: str) -> Dict[str, Any]:
    menus: Dict[str, List[List[Dict[str, str]]]] = {
        "info": [
            [
                {"text": "Системная информация", "callback_data": "cmd:system_info"},
                {"text": "Время", "callback_data": "cmd:time"},
            ],
            [
                {"text": "Аптайм", "callback_data": "cmd:uptime"},
                {"text": "Сеть", "callback_data": "cmd:network_info"},
            ],
            [
                {"text": "Версия Python", "callback_data": "cmd:python_version"},
                {"text": "Кто я", "callback_data": "cmd:whoami"},
            ],
        ],
        "files": [
            [
                {"text": "Список папки", "callback_data": "cmd:list_dir"},
                {"text": "Создать папку", "callback_data": "cmd:create_folder"},
            ],
            [
                {"text": "Открыть папку", "callback_data": "cmd:open_folder"},
                {"text": "Хэш файла", "callback_data": "cmd:hash_file"},
            ],
            [
                {"text": "Проверить путь", "callback_data": "cmd:check_path"},
                {"text": "Отчет", "callback_data": "cmd:report"},
            ],
        ],
        "messages": [
            [
                {"text": "Показать сообщение", "callback_data": "cmd:show_message"},
                {"text": "Записка", "callback_data": "cmd:write_note"},
            ],
            [
                {"text": "Дополнить лог", "callback_data": "cmd:append_log"},
                {"text": "Чат", "callback_data": "cmd:chat"},
            ],
        ],
        "utils": [
            [
                {"text": "Пинг", "callback_data": "cmd:ping"},
                {"text": "Звук", "callback_data": "cmd:beep"},
            ],
            [
                {"text": "Использование диска", "callback_data": "cmd:disk_usage"},
                {"text": "Переменные среды", "callback_data": "cmd:list_env"},
            ],
            [
                {"text": "Остановить агент", "callback_data": "cmd:stop_agent"},
                {"text": "Назад", "callback_data": "section:main"},
            ],
        ],
    }
    return render_keyboard(menus.get(section, []))


def hub_loop(bot: TelegramBot, hub: HubState, host: str, port: int) -> None:
    server = HubServer((host, port), hub)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    bot.send_message(
        next(iter(bot.admin_ids)),
        f"Хаб запущен на {host}:{port}. Команда /menu для управления.",
    )

    while True:
        for update in bot.fetch_updates():
            if "message" in update:
                handle_message(bot, hub, update["message"])
            if "callback_query" in update:
                handle_callback(bot, hub, update["callback_query"])

        try:
            while True:
                msg = hub.chat_queue.get_nowait()
                for admin_id in bot.admin_ids:
                    bot.send_message(admin_id, msg)
        except queue.Empty:
            pass

        time.sleep(0.5)


def handle_message(bot: TelegramBot, hub: HubState, message: Dict[str, Any]) -> None:
    chat_id = message["chat"]["id"]
    if chat_id not in bot.admin_ids:
        return
    text = message.get("text", "")
    if text == "/start":
        bot.send_message(chat_id, "Безопасный бот управления запущен. /menu - меню.")
        return
    if text == "/menu":
        bot.send_message(chat_id, "Разделы:", reply_markup=section_buttons())
        return
    if text == "/devices":
        show_devices(bot, hub, chat_id)
        return
    if text.startswith("/send "):
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            bot.send_message(chat_id, "Формат: /send <команда> <текст/путь>")
            return
        action = parts[1]
        payload = parts[2]
        params: Dict[str, Any]
        if action in {"show_message", "write_note", "append_log"}:
            params = {"text": payload}
        elif action in {"list_dir", "create_folder", "open_folder", "check_path", "hash_file"}:
            params = {"path": payload}
        else:
            bot.send_message(chat_id, "Неизвестная команда для /send.")
            return
        send_command_to_selected(bot, hub, chat_id, action, params)
        return
    if text.startswith("/chat "):
        content = text.replace("/chat ", "", 1)
        send_command_to_selected(bot, hub, chat_id, "chat", {"text": content})
        return


def handle_callback(bot: TelegramBot, hub: HubState, callback: Dict[str, Any]) -> None:
    callback_id = callback["id"]
    data = callback.get("data", "")
    chat_id = callback["message"]["chat"]["id"]
    if chat_id not in bot.admin_ids:
        bot.answer_callback(callback_id, "Недостаточно прав")
        return

    if data == "section:main":
        bot.send_message(chat_id, "Разделы:", reply_markup=section_buttons())
        bot.answer_callback(callback_id, "Ок")
        return
    if data.startswith("section:"):
        section = data.split(":", 1)[1]
        if section == "devices":
            show_devices(bot, hub, chat_id)
            bot.answer_callback(callback_id, "Ок")
            return
        bot.send_message(chat_id, f"Раздел {section}", reply_markup=section_menu(section))
        bot.answer_callback(callback_id, "Ок")
        return
    if data.startswith("toggle:"):
        device_id = data.split(":", 1)[1]
        selected = bot.selected_devices.setdefault(chat_id, set())
        if device_id in selected:
            selected.remove(device_id)
            bot.answer_callback(callback_id, "Убрано")
        else:
            selected.add(device_id)
            bot.answer_callback(callback_id, "Добавлено")
        show_devices(bot, hub, chat_id)
        return
    if data == "devices:all":
        selected = bot.selected_devices.setdefault(chat_id, set())
        selected.clear()
        for device in hub.list_devices():
            selected.add(device.device_id)
        show_devices(bot, hub, chat_id)
        bot.answer_callback(callback_id, "Все выбраны")
        return
    if data == "devices:done":
        bot.answer_callback(callback_id, "Готово")
        return

    if data.startswith("cmd:"):
        action = data.split(":", 1)[1]
        prompt_for_action(bot, hub, chat_id, action)
        bot.answer_callback(callback_id, "Команда отправлена")


def show_devices(bot: TelegramBot, hub: HubState, chat_id: int) -> None:
    devices = hub.list_devices()
    selected = bot.selected_devices.setdefault(chat_id, set())
    if not devices:
        bot.send_message(chat_id, "Устройства не подключены.")
        return
    bot.send_message(
        chat_id,
        "Выберите устройства:",
        reply_markup=render_keyboard(device_buttons(devices, selected)),
    )


def prompt_for_action(bot: TelegramBot, hub: HubState, chat_id: int, action: str) -> None:
    if action not in SAFE_ACTIONS:
        bot.send_message(chat_id, "Недоступная команда.")
        return

    params: Dict[str, Any] = {}
    if action in {"show_message", "write_note", "append_log", "list_dir", "create_folder", "open_folder", "check_path", "hash_file"}:
        bot.send_message(chat_id, f"Введите /send {action} <текст/путь>.")
        return
    if action == "report":
        params = {"filename": "report.txt"}
    if action == "chat":
        bot.send_message(chat_id, "Для чата используйте /chat <текст>.")
        return
    send_command_to_selected(bot, hub, chat_id, action, params)


def send_command_to_selected(
    bot: TelegramBot, hub: HubState, chat_id: int, action: str, params: Dict[str, Any]
) -> None:
    selected = bot.selected_devices.get(chat_id, set())
    if not selected:
        bot.send_message(chat_id, "Сначала выберите устройства (/devices).")
        return
    for device_id in selected:
        try:
            hub.enqueue(
                device_id,
                Command(id=str(uuid.uuid4()), action=action, params=params),
            )
        except KeyError:
            bot.send_message(chat_id, f"Устройство {device_id} недоступно.")
    bot.send_message(chat_id, f"Команда {action} отправлена на {len(selected)} устройств.")


def agent_loop(hub_url: str, device_id: str, name: str, secret: str, base_dir: str) -> None:
    if not requests:
        raise SystemExit("requests library required: pip install requests")
    base_dir = os.path.abspath(base_dir)
    os.makedirs(base_dir, exist_ok=True)

    def post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = requests.post(f"{hub_url}{path}", json=payload, timeout=30)
        response.raise_for_status()
        return response.json()

    post("/register", {"device_id": device_id, "name": name, "secret": secret})
    print(f"Агент зарегистрирован: {device_id}")

    def stdin_loop() -> None:
        if not sys.stdin.isatty():
            return
        while True:
            try:
                line = sys.stdin.readline()
            except Exception:
                return
            if not line:
                return
            message = line.strip()
            if message:
                post(
                    "/chat",
                    {
                        "device_id": device_id,
                        "secret": secret,
                        "message": f"[{name}] {message}",
                    },
                )

    threading.Thread(target=stdin_loop, daemon=True).start()

    while True:
        data = post("/poll", {"device_id": device_id, "secret": secret})
        for cmd in data.get("commands", []):
            output = execute_command(cmd, base_dir)
            message = f"[{name}] {cmd['action']}: {output}"
            post("/result", {"device_id": device_id, "secret": secret, "message": message})
            if cmd["action"] == "stop_agent":
                return
        time.sleep(DEFAULT_POLL_SECONDS)


def execute_command(cmd: Dict[str, Any], base_dir: str) -> str:
    action = cmd.get("action")
    params = cmd.get("params", {})

    if action == "ping":
        return "pong"
    if action == "system_info":
        return collect_system_info()
    if action == "uptime":
        return collect_uptime()
    if action == "disk_usage":
        return collect_disk_usage(base_dir)
    if action == "list_dir":
        path = resolve_in_base(base_dir, params.get("path", "."))
        return ", ".join(os.listdir(path))
    if action == "write_note":
        content = params.get("text", "")
        path = resolve_in_base(base_dir, "note.txt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(str(content))
        return f"written {path}"
    if action == "append_log":
        content = params.get("text", "")
        path = resolve_in_base(base_dir, "log.txt")
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(str(content) + "\n")
        return f"appended {path}"
    if action == "create_folder":
        path = resolve_in_base(base_dir, params.get("path", "new_folder"))
        os.makedirs(path, exist_ok=True)
        return f"created {path}"
    if action == "open_folder":
        path = resolve_in_base(base_dir, params.get("path", "."))
        return open_folder(path)
    if action == "show_message":
        content = params.get("text", "")
        print(f"Сообщение: {content}")
        return "shown"
    if action == "network_info":
        return collect_network_info()
    if action == "time":
        return dt.datetime.now().isoformat()
    if action == "python_version":
        return sys.version
    if action == "check_path":
        path = resolve_in_base(base_dir, params.get("path", "."))
        return f"exists={os.path.exists(path)}"
    if action == "hash_file":
        path = resolve_in_base(base_dir, params.get("path", ""))
        return safe_hash_file(path)
    if action == "report":
        filename = params.get("filename", "report.txt")
        path = resolve_in_base(base_dir, filename)
        report = "\n".join(
            [
                collect_system_info(),
                f"time={dt.datetime.now().isoformat()}",
                f"disk={collect_disk_usage(base_dir)}",
            ]
        )
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(report)
        return f"report saved {path}"
    if action == "beep":
        print("\a", end="")
        return "beep"
    if action == "list_env":
        keys = sorted(os.environ.keys())
        return ", ".join(keys[:50])
    if action == "whoami":
        import getpass

        return getpass.getuser()
    if action == "chat":
        content = params.get("text", "")
        print(f"Сообщение от админа: {content}")
        return "received"
    if action == "stop_agent":
        return "stopping"

    return "unknown"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safe multi-device control")
    sub = parser.add_subparsers(dest="mode", required=True)

    hub = sub.add_parser("hub", help="run hub + telegram bot")
    hub.add_argument("--token", default=os.getenv("BOT_TOKEN"))
    hub.add_argument("--admins", default=os.getenv("ADMIN_IDS", ""))
    hub.add_argument("--secret", default=os.getenv("HUB_SECRET", "change-me"))
    hub.add_argument("--host", default="0.0.0.0")
    hub.add_argument("--port", type=int, default=DEFAULT_PORT)

    agent = sub.add_parser("agent", help="run agent")
    agent.add_argument("--hub", required=True, help="Hub URL, e.g. http://host:8000")
    agent.add_argument("--device-id", default=str(uuid.uuid4())[:8])
    agent.add_argument("--name", default=socket.gethostname())
    agent.add_argument("--secret", default=os.getenv("HUB_SECRET", "change-me"))
    agent.add_argument("--base-dir", default=os.path.expanduser("~/safe_agent"))

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.mode == "hub":
        if not args.token:
            raise SystemExit("Bot token required. Use --token or BOT_TOKEN env var.")
        admins = [int(item) for item in args.admins.split(",") if item.strip()]
        if not admins:
            raise SystemExit("Admin IDs required. Use --admins or ADMIN_IDS env var.")
        bot = TelegramBot(args.token, admins)
        hub = HubState(args.secret)
        hub_loop(bot, hub, args.host, args.port)
        return

    if args.mode == "agent":
        agent_loop(args.hub, args.device_id, args.name, args.secret, args.base_dir)
        return


if __name__ == "__main__":
    main()
