from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.audio import SoundLoader
from kivy.utils import platform
import random, time

# ---------------- CONFIG ----------------
BASE_TIME = {"easy": 60, "medium": 90, "hard": 120}
GRID_SIZE = {"easy": 3, "medium": 4, "hard": 5}

SHOP_HINT_PRICE = {"easy": 10, "medium": 20, "hard": 30}
SHOP_TIME_PRICE = {"easy": 5, "medium": 10, "hard": 20}

BUTTON_COLORS = {
    "easy": (0, 0.7, 0, 1),
    "medium": (0.9, 0.9, 0, 1),
    "hard": (0.8, 0, 0, 1),
}

# ---------------------------------------


class MainMenu(Screen):
    def on_enter(self):
        self.clear_widgets()
        app = App.get_running_app()

        layout = BoxLayout(orientation="vertical", padding=20, spacing=15)

        layout.add_widget(Label(text="🧠 The Brain in Numbers", font_size=26))
        layout.add_widget(Label(text=f"🪙 Coins: {app.coins}", font_size=18))

        daily = Button(
            text="🎁 Daily Reward (+30)",
            background_color=(0.6, 0.3, 0.9, 1),
            size_hint_y=None, height=50
        )
        daily.bind(on_release=self.daily_reward)
        layout.add_widget(daily)

        for mode in ["easy", "medium", "hard"]:
            btn = Button(
                text=mode.capitalize(),
                background_color=BUTTON_COLORS[mode],
                size_hint_y=None, height=70
            )
            btn.bind(on_release=lambda x, m=mode: self.start_game(m))
            layout.add_widget(btn)

        shop = Button(
            text="🛒 Shop",
            background_color=(0.2, 0.4, 1, 1),
            size_hint_y=None, height=60
        )
        shop.bind(on_release=lambda x: setattr(self.manager, "current", "shop"))
        layout.add_widget(shop)

        self.add_widget(layout)

    def daily_reward(self, *_):
        app = App.get_running_app()
        if time.time() - app.last_daily >= 86400:
            app.coins += 30
            app.last_daily = time.time()
            self.on_enter()
        else:
            Popup(
                title="Not Ready",
                content=Label(text="Come back later 😊"),
                size_hint=(0.6, 0.3)
            ).open()

    def start_game(self, mode):
        if mode == "hard":
            self.confirm_hard()
            return

        game = self.manager.get_screen("game")
        game.start(mode)
        self.manager.current = "game"

    def play_warning_sound(self):
        sound = SoundLoader.load("warning.wav")
        if sound:
            sound.play()

    def confirm_hard(self):
        box = BoxLayout(orientation="vertical", spacing=15, padding=15)
        box.add_widget(Label(text="⚠️ Are you sure?", font_size=20))

        btns = BoxLayout(spacing=10)
        yes = Button(text="Yes", background_color=(0.8, 0, 0, 1))
        no = Button(text="No", background_color=(0.5, 0.5, 0.5, 1))
        btns.add_widget(yes)
        btns.add_widget(no)
        box.add_widget(btns)

        popup = Popup(
            title="Hard Mode",
            content=box,
            size_hint=(0.7, 0.4),
            auto_dismiss=False
        )

        yes.bind(on_release=lambda x: (
            popup.dismiss(),
            self.start_hard_game()
        ))
        no.bind(on_release=lambda x: popup.dismiss())

        self.play_warning_sound()
        popup.open()

    def start_hard_game(self):
        game = self.manager.get_screen("game")
        game.start("hard")
        self.manager.current = "game"


class GameScreen(Screen):
    def start(self, mode):
        self.clear_widgets()
        self.mode = mode
        app = App.get_running_app()

        self.size_n = GRID_SIZE[mode]
        self.hints = app.hints[mode]
        self.time_left = BASE_TIME[mode] + app.extra_time[mode]

        root = BoxLayout(orientation="vertical", spacing=10)

        self.timer_lbl = Label(text=f"⏱ {self.time_left}", font_size=20)
        root.add_widget(self.timer_lbl)

        self.grid = GridLayout(cols=self.size_n, spacing=5)
        root.add_widget(self.grid)

        self.make_board()
        self.draw()

        bottom = BoxLayout(size_hint_y=None, height=60)
        hint_btn = Button(text=f"Hint ({self.hints})")
        hint_btn.bind(on_release=self.use_hint)
        bottom.add_widget(hint_btn)

        menu = Button(text="Main Menu")
        menu.bind(on_release=lambda x: setattr(self.manager, "current", "menu"))
        bottom.add_widget(menu)

        root.add_widget(bottom)
        self.add_widget(root)

        Clock.unschedule(self.tick)
        Clock.schedule_interval(self.tick, 1)

    def make_board(self):
        n = self.size_n ** 2
        self.tiles = list(range(1, n)) + [0]
        while True:
            random.shuffle(self.tiles)
            if self.is_solvable() and not self.is_solved():
                break

    def is_solvable(self):
        inv = 0
        nums = [x for x in self.tiles if x]
        for i in range(len(nums)):
            for j in range(i + 1, len(nums)):
                if nums[i] > nums[j]:
                    inv += 1
        return inv % 2 == 0

    def draw(self):
        self.grid.clear_widgets()
        for i, v in enumerate(self.tiles):
            if v == 0:
                self.grid.add_widget(Label())
            else:
                b = Button(text=str(v))
                b.bind(on_release=lambda x, i=i: self.move(i))
                self.grid.add_widget(b)

    def vibrate(self):
        if platform == "android":
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Context = autoclass('android.content.Context')
                activity = PythonActivity.mActivity
                vibrator = activity.getSystemService(Context.VIBRATOR_SERVICE)
                if vibrator:
                    vibrator.vibrate(100)
            except:
                pass

    def move(self, i):
        z = self.tiles.index(0)
        r1, c1 = divmod(i, self.size_n)
        r2, c2 = divmod(z, self.size_n)
        if abs(r1 - r2) + abs(c1 - c2) == 1:
            self.tiles[z], self.tiles[i] = self.tiles[i], self.tiles[z]
            self.draw()
            if self.is_solved():
                self.win()
        else:
            self.vibrate()

    def is_solved(self):
        return self.tiles == list(range(1, self.size_n ** 2)) + [0]

    def use_hint(self, *_):
        if self.hints <= 0:
            return
        self.hints -= 1
        z = self.tiles.index(0)
        self.move(z - 1 if z % self.size_n else z + 1)

    def tick(self, *_):
        self.time_left -= 1
        if self.time_left <= 10:
            self.timer_lbl.color = (1, 0, 0, 1)
        self.timer_lbl.text = f"⏱ {self.time_left}"
        if self.time_left <= 0:
            Clock.unschedule(self.tick)

    def win(self):
        Clock.unschedule(self.tick)
        app = App.get_running_app()
        app.coins += 50

        box = BoxLayout(orientation="vertical", spacing=10, padding=10)
        box.add_widget(Label(text="🎉 YOU WIN!", font_size=22))
        box.add_widget(Label(text="+50 Coins 🪙", font_size=18))

        btn = Button(text="Main Menu", size_hint_y=None, height=50)
        box.add_widget(btn)

        popup = Popup(
            title="Victory",
            content=box,
            size_hint=(0.7, 0.5),
            auto_dismiss=False
        )

        btn.bind(on_release=lambda x: (
            popup.dismiss(),
            setattr(self.manager, "current", "menu")
        ))
        popup.open()


class Shop(Screen):
    def on_enter(self):
        self.clear_widgets()
        app = App.get_running_app()

        box = BoxLayout(orientation="vertical", padding=20, spacing=15)
        box.add_widget(Label(text=f"🪙 Coins: {app.coins}", font_size=20))

        for m, p in SHOP_HINT_PRICE.items():
            b = Button(text=f"+1 Hint ({m}) – ₹{p}")
            b.bind(on_release=lambda x, m=m, p=p: self.buy_hint(m, p))
            box.add_widget(b)

        for m, p in SHOP_TIME_PRICE.items():
            b = Button(text=f"+10s ({m}) – ₹{p}")
            b.bind(on_release=lambda x, m=m, p=p: self.buy_time(m, p))
            box.add_widget(b)

        back = Button(text="Back")
        back.bind(on_release=lambda x: setattr(self.manager, "current", "menu"))
        box.add_widget(back)

        self.add_widget(box)

    def buy_hint(self, mode, price):
        app = App.get_running_app()
        if app.coins >= price:
            app.coins -= price
            app.hints[mode] += 1
            self.on_enter()

    def buy_time(self, mode, price):
        app = App.get_running_app()
        if app.coins >= price:
            app.coins -= price
            app.extra_time[mode] += 10
            self.on_enter()


class BrainGame(App):
    def build(self):
        self.coins = 100
        self.last_daily = 0
        self.hints = {"easy": 10, "medium": 5, "hard": 0}
        self.extra_time = {"easy": 0, "medium": 0, "hard": 0}

        sm = ScreenManager()
        sm.add_widget(MainMenu(name="menu"))
        sm.add_widget(GameScreen(name="game"))
        sm.add_widget(Shop(name="shop"))
        return sm


BrainGame().run()