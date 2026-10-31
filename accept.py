"""Screen-color auto accept prototype. Run with: python accept.py."""

import queue
import threading
import tkinter as tk
from tkinter import ttk

# Values from the original prototype. Adjust to your own screen.
TARGET_COLOR = (19, 60, 8)
SEARCH_AREA = (0, 0, 1280, 1024)  # left, top, width, height
SCAN_STEP = 5
CHECK_INTERVAL = 1.0


def find_color(image, target_color, step=SCAN_STEP):
    """Return the first matching local pixel, or None (x-first scan order)."""
    if step < 1:
        raise ValueError("Scan step must be positive")
    width, height = image.size
    for x in range(0, width, step):
        for y in range(0, height, step):
            if image.getpixel((x, y))[:3] == target_color:
                return x, y
    return None


def screen_position(local_position, area):
    """Convert a point in the screenshot into a screen coordinate."""
    return area[0] + local_position[0], area[1] + local_position[1]


def validate_area(area, screen_size):
    left, top, width, height = area
    if left < 0 or top < 0 or width <= 0 or height <= 0:
        raise ValueError("Область поиска должна иметь положительный размер и координаты >= 0.")
    if left + width > screen_size[0] or top + height > screen_size[1]:
        raise ValueError("Область SEARCH_AREA выходит за пределы основного экрана.")


class AutoAcceptApp:
    def __init__(self, root, automation):
        self.root = root
        self.automation = automation
        self.stop_event = threading.Event()
        self.worker = None
        self.events = queue.Queue()
        root.title("CS2 Auto Accept — prototype")
        root.geometry("500x340")
        self.button = ttk.Button(root, text="Auto Accept Off", command=self.toggle)
        self.button.pack(padx=12, pady=12, fill="x")
        ttk.Label(root, text="Остановка: кнопка Off или курсор в угол основного экрана.",
                  wraplength=470).pack(padx=12)
        self.output = tk.Text(root, height=10, state="disabled", wrap="word")
        self.output.pack(padx=12, pady=12, fill="both", expand=True)
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(100, self.poll_events)

    def log(self, message):
        self.output.config(state="normal")
        self.output.insert(tk.END, message + "\n")
        self.output.see(tk.END)
        self.output.config(state="disabled")

    def toggle(self):
        if self.worker is not None and self.worker.is_alive():
            self.stop_event.set()
            self.button.config(text="Остановка…", state="disabled")
            return
        try:
            validate_area(SEARCH_AREA, self.automation.size())
        except ValueError as error:
            self.log(str(error))
            return
        self.stop_event.clear()
        self.button.config(text="Auto Accept On")
        self.log("Поиск включён.")
        self.worker = threading.Thread(target=self.search_loop, daemon=True)
        self.worker.start()

    def search_loop(self):
        # All Tk operations stay in the main thread; this thread only queues text.
        try:
            while not self.stop_event.is_set():
                image = self.automation.screenshot(region=SEARCH_AREA)
                position = find_color(image, TARGET_COLOR)
                if position is not None and not self.stop_event.is_set():
                    x, y = screen_position(position, SEARCH_AREA)
                    self.automation.click(x, y)
                    self.events.put(f"Цвет найден: ({x}, {y}). Клик выполнен; поиск остановлен.")
                    # A single click per activation prevents repeated clicks.
                    break
                if self.stop_event.wait(CHECK_INTERVAL):
                    break
        except self.automation.FailSafeException:
            self.events.put("Аварийная остановка: курсор в углу экрана.")
        except Exception as error:
            self.events.put(f"Ошибка захвата экрана или клика: {error}")
        finally:
            self.stop_event.set()

    def poll_events(self):
        while True:
            try:
                self.log(self.events.get_nowait())
            except queue.Empty:
                break
        if self.worker is not None and not self.worker.is_alive():
            self.worker = None
            self.button.config(text="Auto Accept Off", state="normal")
        self.root.after(100, self.poll_events)

    def close(self):
        self.stop_event.set()
        self.button.config(state="disabled")
        self.finish_close()

    def finish_close(self):
        if self.worker is not None and self.worker.is_alive():
            self.root.after(50, self.finish_close)
        else:
            self.root.destroy()


def main():
    import pyautogui

    pyautogui.FAILSAFE = True
    root = tk.Tk()
    AutoAcceptApp(root, pyautogui)
    root.mainloop()


if __name__ == "__main__":
    main()
