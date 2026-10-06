"""Tkinter UI + system tray for CBJ Gameday Sentinel.

Threading model: background threads fetch data and *post* closures to
``self.ui_queue``; the Tk main loop drains that queue. Tray-menu callbacks
(which run on pystray's thread) also only post to the queue. No Tk call is
ever made off the main thread.

Rendering: every tab lives in the same grid cell and is switched with
``tkraise`` (no unmap/remap). Scrollable tabs are double-buffered: the new
content is built in a hidden canvas window, laid out, then swapped in, which
removes the white flash Windows shows when widgets are torn down.
"""
from __future__ import annotations

import collections
import ctypes
import logging
import os
import queue
import re
import sys
import threading
import time
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, Dict, List, Optional

import pystray
from PIL import ImageTk

from . import __version__, assets, config as C, data, net, rink, settings

log = logging.getLogger(__name__)

SCALE = 1.0  # set from the monitor DPI in main()


def px(n: float) -> int:
    return int(round(n * SCALE))


FACTS = [
    ("Expansion roots", "The Blue Jackets entered the NHL for the 2000\u201301 season and have played at Nationwide Arena since day one."),
    ("Why \u201cBlue Jackets\u201d?", "The name honors Ohio\u2019s contribution to the Union Army in the Civil War \u2014 hence the team\u2019s Union-blue look."),
    ("The Cannon", "A replica Civil War cannon fires inside Nationwide Arena when the team takes the ice, after every home goal, and after home wins."),
    ("Arena District", "Nationwide Arena anchors Columbus\u2019s Arena District, built on the former site of the Ohio Penitentiary."),
    ("2019 shocker", "In 2019 Columbus swept the 62-win, Presidents\u2019 Trophy-winning Tampa Bay Lightning \u2014 the franchise\u2019s first playoff series win."),
    ("Hardware in net", "Sergei Bobrovsky won the Vezina Trophy as the NHL\u2019s top goalie twice in Columbus (2012\u201313 and 2016\u201317)."),
    ("Franchise sniper", "Rick Nash is the franchise\u2019s all-time leading goal scorer and shared the 2003\u201304 Rocket Richard Trophy."),
]

_REPO_RE = re.compile(r"^[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}$")


# ---------------------------------------------------------------- widgets
def lbl(parent, text="", size=9, bold=False, fg=C.TEXT, bg=C.CARD, **kw) -> tk.Label:
    if "wraplength" in kw:
        kw["wraplength"] = px(kw["wraplength"])
    return tk.Label(parent, text=text, font=(C.FONT, size, "bold" if bold else "normal"),
                    fg=fg, bg=bg, **kw)


def btn(parent, text, cmd, bg=C.NAVY, fg=C.TEXT, size=9, bold=True) -> tk.Button:
    return tk.Button(parent, text=text, command=cmd, font=(C.FONT, size, "bold" if bold else "normal"),
                     fg=fg, bg=bg, activebackground=C.RED, activeforeground=C.TEXT,
                     relief="flat", bd=0, padx=px(10), pady=px(4), cursor="hand2")


def card(parent, bg=C.CARD, **pack) -> tk.Frame:
    f = tk.Frame(parent, bg=bg, padx=px(10), pady=px(8))
    f.pack(fill="x", pady=pack.pop("pady", px(4)), **pack)
    return f


def section(parent, text) -> None:
    lbl(parent, text, 9, True, C.SILVER, C.BG).pack(anchor="w", pady=(px(10), px(2)))


def table(parent, headers: List[str], rows: List[List[Any]], widths: List[int],
          accent_col: Optional[int] = None, highlight: Optional[int] = None,
          on_click: Optional[Callable[[int], None]] = None, divider_after: Optional[int] = None) -> None:
    grid = tk.Frame(parent, bg=C.CARD)
    grid.pack(fill="x")
    for c, (h, w) in enumerate(zip(headers, widths)):
        tk.Label(grid, text=h, width=w, anchor="w" if c == 1 else "center", bg=C.NAVY, fg=C.TEXT,
                 font=(C.FONT, 8, "bold")).grid(row=0, column=c, sticky="ew")
    out_row = 1
    for r, row in enumerate(rows):
        if divider_after is not None and r == divider_after:
            tk.Frame(grid, bg=C.RED, height=2).grid(row=out_row, column=0, columnspan=len(headers), sticky="ew")
            out_row += 1
        hl = highlight == r
        bg = C.HILITE if hl else (C.CARD if r % 2 == 0 else C.CARD_DEEP)
        for c, (val, w) in enumerate(zip(row, widths)):
            fg = C.ACCENT if c == accent_col else (C.GOLD if hl else C.TEXT)
            cell = tk.Label(grid, text=str(val), width=w, anchor="w" if c == 1 else "center", bg=bg, fg=fg,
                            font=(C.FONT, 8, "bold" if (c in (1, accent_col) or hl) else "normal"))
            cell.grid(row=out_row, column=c, sticky="ew")
            if on_click and c == 1:
                cell.configure(cursor="hand2", fg=C.GOLD if hl else "#9ed8ff")
                cell.bind("<Button-1>", lambda e, i=r: on_click(i))
        out_row += 1


def fmt(v: Any, digits: int = 0) -> str:
    if isinstance(v, bool) or v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.{digits}f}" if digits else f"{v:g}"
    return str(v)


class ScrollArea(tk.Frame):
    """Scrollable, double-buffered content area."""

    def __init__(self, master, registry: set, bg: str = C.BG):
        super().__init__(master, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=bar.set)
        self.canvas.pack(side="left", fill="both", expand=True, padx=(px(12), px(4)), pady=px(8))
        bar.pack(side="right", fill="y")
        self.bg = bg
        self.inner: Optional[tk.Frame] = None
        self.win: Optional[int] = None
        self.canvas.bind("<Configure>", self._on_resize)
        self.registry = registry
        registry.add(self.canvas)

    def _on_resize(self, event) -> None:
        if self.win is not None:
            self.canvas.itemconfigure(self.win, width=event.width)

    def _sync(self, _event=None) -> None:
        box = self.canvas.bbox(self.win) if self.win is not None else None
        self.canvas.configure(scrollregion=box or (0, 0, 0, 0))

    def render(self, builder: Callable[[tk.Frame], None]) -> None:
        pos = self.canvas.yview()[0] if self.win is not None else 0.0
        new = tk.Frame(self.canvas, bg=self.bg)
        builder(new)
        win = self.canvas.create_window(0, 0, window=new, anchor="nw",
                                        width=max(self.canvas.winfo_width(), 1), state="hidden")
        new.update_idletasks()
        old_win, old = self.win, self.inner
        self.canvas.itemconfigure(win, state="normal")
        if old_win is not None:
            self.canvas.delete(old_win)
        if old is not None:
            old.destroy()
        self.inner, self.win = new, win
        new.bind("<Configure>", self._sync)
        self._sync()
        self.canvas.yview_moveto(pos)

    def destroy(self) -> None:
        self.registry.discard(self.canvas)
        super().destroy()


# ---------------------------------------------------------------- mini overlay
class MiniOverlay:
    """Small borderless, always-on-top, draggable live scoreboard."""

    def __init__(self, app: "SentinelApp"):
        self.app = app
        self.win: Optional[tk.Toplevel] = None
        self.dismissed: Any = None
        self._drag = (0, 0)

    def _build(self) -> None:
        w = tk.Toplevel(self.app.root)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        try:
            w.attributes("-alpha", 0.94)
        except tk.TclError:
            pass
        w.configure(bg=C.RED)
        self.inner = tk.Frame(w, bg=C.NAVY, padx=px(10), pady=px(5))
        self.inner.pack(padx=2, pady=2)
        self.l_score = tk.Label(self.inner, font=(C.FONT, 13, "bold"), fg=C.TEXT, bg=C.NAVY)
        self.l_score.grid(row=0, column=0, sticky="w")
        close = tk.Label(self.inner, text="\u2715", font=(C.FONT, 8), fg=C.MUTED, bg=C.NAVY, cursor="hand2")
        close.grid(row=0, column=1, sticky="ne", padx=(px(8), 0))
        close.bind("<Button-1>", lambda e: self.dismiss())
        self.l_info = tk.Label(self.inner, font=(C.FONT, 8), fg=C.SILVER, bg=C.NAVY)
        self.l_info.grid(row=1, column=0, columnspan=2, sticky="w")
        for widget in (w, self.inner, self.l_score, self.l_info):
            widget.bind("<ButtonPress-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._on_drag)
            widget.bind("<ButtonRelease-1>", self._end_drag)
            widget.bind("<Double-Button-1>", lambda e: self.app.show())
        self.win = w
        w.update_idletasks()
        sw, sh = w.winfo_screenwidth(), w.winfo_screenheight()
        x, y = self.app.settings["overlay_x"], self.app.settings["overlay_y"]
        if not (0 <= x < sw - 40 and 0 <= y < sh - 30):
            x = sw - max(w.winfo_reqwidth(), px(230)) - px(24)
            y = sh - w.winfo_reqheight() - px(90)
        w.geometry(f"+{x}+{y}")

    def _start_drag(self, e) -> None:
        self._drag = (e.x_root - self.win.winfo_x(), e.y_root - self.win.winfo_y())

    def _on_drag(self, e) -> None:
        self.win.geometry(f"+{e.x_root - self._drag[0]}+{e.y_root - self._drag[1]}")

    def _end_drag(self, _e) -> None:
        self.app.settings["overlay_x"] = max(0, self.win.winfo_x())
        self.app.settings["overlay_y"] = max(0, self.win.winfo_y())
        settings.save(self.app.settings)

    def dismiss(self) -> None:
        self.dismissed = (self.app.game or {}).get("id")
        self.hide()

    def hide(self) -> None:
        if self.win is not None:
            self.win.destroy()
            self.win = None

    def show(self, score: str, info: str, flash: bool = False) -> None:
        if self.win is None:
            self._build()
        bg = C.RED if flash else C.NAVY
        for widget in (self.inner, self.l_score, self.l_info):
            widget.configure(bg=bg)
        self.l_score.configure(text=score)
        self.l_info.configure(text=info)


# ---------------------------------------------------------------- floating ticker bar
class TickerBar:
    """Ultra-slim, borderless, always-on-top floating ticker ribbon.

    Designed to float or dock on a second monitor while working or gaming.
    Displays live scores, clock/period, situation, shots on goal, and recent scorers,
    or next game countdown when idle.
    """

    def __init__(self, app: "SentinelApp"):
        self.app = app
        self.win: Optional[tk.Toplevel] = None
        self._drag = (0, 0)
        self._icon_img: Optional[ImageTk.PhotoImage] = None

    def _build(self) -> None:
        w = tk.Toplevel(self.app.root)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        try:
            w.attributes("-alpha", 0.95)
        except tk.TclError:
            pass
        w.configure(bg=C.RED)

        self.bar = tk.Frame(w, bg="#071322", padx=px(10), pady=px(4))
        self.bar.pack(fill="both", expand=True, padx=1, pady=1)

        self._icon_img = ImageTk.PhotoImage(assets.app_icon(px(22)))
        self.l_logo = tk.Label(self.bar, image=self._icon_img, bg="#071322")
        self.l_logo.pack(side="left", padx=(0, px(6)))

        self.l_badge = tk.Label(self.bar, text="", font=(C.FONT, 8, "bold"),
                                fg=C.TEXT, bg=C.RED, padx=px(5), pady=px(1))
        self.l_badge.pack(side="left", padx=(0, px(6)))

        self.l_score = tk.Label(self.bar, text="", font=(C.FONT, 10, "bold"),
                                fg=C.TEXT, bg="#071322")
        self.l_score.pack(side="left", padx=(0, px(8)))

        self.l_clock = tk.Label(self.bar, text="", font=(C.FONT, 9, "bold"),
                                fg=C.ACCENT, bg="#071322")
        self.l_clock.pack(side="left", padx=(0, px(8)))

        self.l_sit = tk.Label(self.bar, text="", font=(C.FONT, 8),
                              fg=C.GOLD, bg="#071322")
        self.l_sit.pack(side="left", padx=(0, px(8)))

        self.l_note = tk.Label(self.bar, text="", font=(C.FONT, 8),
                               fg=C.SILVER, bg="#071322")
        self.l_note.pack(side="left", fill="x", expand=True)

        ctrls = tk.Frame(self.bar, bg="#071322")
        ctrls.pack(side="right", padx=(px(6), 0))

        b_expand = tk.Button(ctrls, text="\u2922 Expand", font=(C.FONT, 8, "bold"),
                             command=self.expand, bg="#132338", fg=C.TEXT,
                             bd=0, padx=px(6), pady=px(1), cursor="hand2",
                             activebackground=C.RED, activeforeground=C.TEXT)
        b_expand.pack(side="left", padx=2)

        b_close = tk.Button(ctrls, text="\u2715", font=(C.FONT, 8),
                            command=self.hide, bg="#132338", fg=C.MUTED,
                            bd=0, padx=px(5), pady=px(1), cursor="hand2",
                            activebackground=C.RED, activeforeground=C.TEXT)
        b_close.pack(side="left", padx=1)

        for widget in (w, self.bar, self.l_logo, self.l_badge, self.l_score,
                       self.l_clock, self.l_sit, self.l_note, ctrls):
            widget.bind("<ButtonPress-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._on_drag)
            widget.bind("<ButtonRelease-1>", self._end_drag)
            widget.bind("<Double-Button-1>", lambda e: self.expand())

        self.win = w
        w.update_idletasks()
        sw, sh = w.winfo_screenwidth(), w.winfo_screenheight()
        x, y = self.app.settings.get("ticker_x", -1), self.app.settings.get("ticker_y", -1)
        if not (0 <= x < sw - 100 and 0 <= y < sh - 40):
            req_w = max(w.winfo_reqwidth(), px(640))
            x = (sw - req_w) // 2
            y = sh - w.winfo_reqheight() - px(48)
        w.geometry(f"+{x}+{y}")

    def _start_drag(self, e) -> None:
        if self.win:
            self._drag = (e.x_root - self.win.winfo_x(), e.y_root - self.win.winfo_y())

    def _on_drag(self, e) -> None:
        if self.win:
            self.win.geometry(f"+{e.x_root - self._drag[0]}+{e.y_root - self._drag[1]}")

    def _end_drag(self, _e) -> None:
        if self.win:
            self.app.settings["ticker_x"] = max(0, self.win.winfo_x())
            self.app.settings["ticker_y"] = max(0, self.win.winfo_y())
            settings.save(self.app.settings)

    def expand(self) -> None:
        self.app.show()

    def hide(self) -> None:
        if self.win is not None:
            self.win.destroy()
            self.win = None
        self.app.settings["ticker_bar"] = False
        settings.save(self.app.settings)
        if "ticker_bar" in self.app.setting_vars:
            self.app.setting_vars["ticker_bar"].set(False)
        try:
            self.app.icon.update_menu()
        except Exception:
            pass

    def show(self) -> None:
        if self.win is None:
            self._build()
        self.update_content()

    def update_content(self) -> None:
        if self.win is None:
            return
        g = self.app.display_game()
        if g:
            home = g.get("homeTeam") or {}
            away = g.get("awayTeam") or {}
            state = g.get("gameState")
            h_ab = away.get("abbrev", "")
            a_ab = home.get("abbrev", "")
            h_sc = away.get("score", 0)
            a_sc = home.get("score", 0)
            s_away = away.get("sog", 0)
            s_home = home.get("sog", 0)

            if state in data.LIVE_STATES:
                self.l_badge.configure(text=" \u25CF LIVE ", bg=C.RED, fg=C.TEXT)
                clock = g.get("clock") or {}
                p_lbl = data.period_label(g)
                c_lbl = f"{p_lbl} {clock.get('timeRemaining', '')}"
                self.l_score.configure(text=f"{h_ab} {h_sc} \u2013 {a_sc} {a_ab}")
                self.l_clock.configure(text=c_lbl, fg=C.ACCENT)
                self.l_sit.configure(text=f"SOG {h_ab} {s_away}-{s_home} {a_ab}")
                sit = data.situation(g, self.app.live_landing)
                if sit.get("pp"):
                    self.l_sit.configure(text=f"PP: {sit['pp']} ({sit['advantage']})")
                scorer = data.last_scorer(g.get("goals") or [], C.TEAM)
                self.l_note.configure(text=f"\u2605 {scorer}" if scorer else data.broadcasts(g, C.TEAM))
            elif state in data.FINAL_STATES:
                if self.app.spoiler_hidden(g):
                    self.l_badge.configure(text=" FINAL ", bg="#1a3152", fg=C.MUTED)
                    self.l_score.configure(text=f"{h_ab} @ {a_ab}")
                    self.l_clock.configure(text="Final (Hidden)", fg=C.MUTED)
                    self.l_sit.configure(text="")
                    self.l_note.configure(text="Spoiler mode active")
                else:
                    res, ours, theirs = data.result_of(g, C.TEAM)
                    bg = C.GREEN if res == "W" else C.RED
                    self.l_badge.configure(text=f" {res} ", bg=bg, fg=C.TEXT)
                    self.l_score.configure(text=f"{h_ab} {h_sc} \u2013 {a_sc} {a_ab}")
                    self.l_clock.configure(text="Final", fg=C.SILVER)
                    self.l_sit.configure(text=f"SOG {h_ab} {s_away}-{s_home} {a_ab}")
                    self.l_note.configure(text=data.venue_line(g))
            else:
                self.l_badge.configure(text=" GAMEDAY ", bg="#1a3152", fg=C.TEXT)
                self.l_score.configure(text=f"{h_ab} @ {a_ab}")
                self.l_clock.configure(text=data.local_start(g), fg=C.ACCENT)
                self.l_sit.configure(text="")
                self.l_note.configure(text=data.broadcasts(g, C.TEAM) or data.venue_line(g))
        else:
            nxt = self.app.next_game()
            if nxt:
                self.l_badge.configure(text=" NEXT ", bg="#1a3152", fg=C.SILVER)
                self.l_score.configure(text=data.matchup_line(nxt, C.TEAM))
                self.l_clock.configure(text=data.local_start(nxt), fg=C.ACCENT)
                self.l_sit.configure(text="")
                tv = data.broadcasts(nxt, C.TEAM)
                self.l_note.configure(text=f"\U0001F4FA {tv}" if tv else data.venue_line(nxt))
            else:
                self.l_badge.configure(text=" NHL ", bg="#1a3152", fg=C.MUTED)
                self.l_score.configure(text=C.APP_NAME)
                self.l_clock.configure(text="No upcoming games", fg=C.MUTED)
                self.l_sit.configure(text="")
                self.l_note.configure(text="")


# ---------------------------------------------------------------- app
class SentinelApp:
    TABS = (("live", "\U0001F3D2 Live"), ("games", "\U0001F4C5 Games"), ("shots", "\U0001F3AF Shots"),
            ("standings", "\U0001F3C6 Standings"), ("news", "\U0001F4F0 News"), ("roster", "\u2B50 Roster"),
            ("settings", "\u2699 Settings"))
    DEPS = {"games": ("schedule", "stats", "landing", "_ui"),
            "shots": ("schedule", "landing", "_ui"),
            "standings": ("standings", "schedule", "_ui"),
            "news": ("news", "schedule", "_ui"), "roster": ("roster", "stats", "boxscore"),
            "settings": ("_settings", "update_info")}

    def __init__(self, root: tk.Tk):
        self.root = root
        self.settings = settings.load()
        self.ui_queue: "queue.Queue[Callable[[], None]]" = queue.Queue()
        self.stop_event = threading.Event()
        self.wake_event = threading.Event()
        self.force_refresh = False

        # data state (main thread only)
        self.game: Optional[dict] = None
        self.boxscore: Optional[dict] = None
        self.live_landing: Optional[dict] = None
        self.schedule: List[dict] = []
        self.stats: Dict[str, Any] = {}
        self.roster: Dict[str, Any] = {}
        self.standings: Dict[str, Any] = {}
        self.news_by_source: Dict[str, List[dict]] = {}
        self.news: List[dict] = []
        self.landing: Dict[int, dict] = {}
        self.shot_data: Dict[int, dict] = {}
        self.update_info: Optional[dict] = None
        self.offline = False

        # UI state
        self.expanded: Optional[int] = None
        self.show_all_games = False
        self.news_filter = "all"
        self.selected_shot_game_id: Any = "combined"
        self._batch_fetching_shots = False
        self.revealed: set = set()
        self.goal_tracker = data.GoalTracker()
        self.opp_tracker = data.GoalTracker()
        self.popped_games: set = set()
        self.game_states: Dict[Any, str] = {}
        self.intermissions: Dict[Any, bool] = {}
        self.reminded: set = set()
        self.flash_until = 0.0
        self.delay_q: "collections.deque" = collections.deque(maxlen=200)
        self.versions: Dict[str, int] = {}
        self.rendered: Dict[str, tuple] = {}
        self.active_tab = "live"
        self.scroll_canvases: set = set()
        self.setting_vars: Dict[str, tk.Variable] = {}
        self.player_windows: Dict[int, tk.Toplevel] = {}
        self.icon_key: Any = "init"
        self.update_toasted = False
        self._save_job: Optional[str] = None
        self._reveal_shown = False
        self._vol_job: Optional[str] = None
        assets.set_volume(self.settings["volume"])

        self._icon_base = assets.app_icon(64)
        self.overlay = MiniOverlay(self)
        self.ticker = TickerBar(self)
        if self.settings.get("ticker_bar", False):
            self.ticker.show()
        self._build_window()
        self._build_tray()
        self.root.bind_all("<MouseWheel>", self._on_wheel)
        self.root.after(100, self._drain_queue)
        self.root.after(200, self._start_worker)
        threading.Thread(target=self._prepare_media, name="media", daemon=True).start()
        self._render_live()
        self._tick()

    def _prepare_media(self) -> None:
        """Background: synthesize sounds and download/refresh the team logo."""
        assets.prepare_sounds()
        assets.prepare_volume(self.settings["volume"])
        if assets.team_logo_stale():
            try:
                assets.save_team_logo(net.fetch_bytes(C.LOGO_URL, C.MAX_IMAGE_BYTES, timeout=20))
                self.post(self._reload_icons)
            except Exception as exc:
                log.info("Team logo unavailable, using fallback icon: %s", exc)

    def _reload_icons(self) -> None:
        self._icon_base = assets.app_icon(64)
        self._icon_img = ImageTk.PhotoImage(assets.app_icon(px(64)))
        self.root.iconphoto(True, self._icon_img)
        self._hdr_img = ImageTk.PhotoImage(assets.app_icon(px(38)))
        self.l_hdr_img.configure(image=self._hdr_img)
        self._live_img = ImageTk.PhotoImage(assets.app_icon(px(64)))
        self.l_logo.configure(image=self._live_img)
        self.icon_key = "reload"
        self._update_tray_icon()

    # ------------------------------------------------------------ plumbing
    def post(self, fn: Callable[[], None]) -> None:
        self.ui_queue.put(fn)

    def _drain_queue(self) -> None:
        try:
            while True:
                fn = self.ui_queue.get_nowait()
                try:
                    fn()
                except Exception:
                    log.exception("UI callback failed")
        except queue.Empty:
            pass
        if not self.stop_event.is_set():
            self.root.after(100, self._drain_queue)

    def _on_wheel(self, event) -> None:
        w = self.root.winfo_containing(event.x_root, event.y_root)
        while w is not None:
            if w in self.scroll_canvases:
                w.yview_scroll(int(-event.delta / 120), "units")
                return
            w = getattr(w, "master", None)

    def _set(self, key: str, value: Any) -> None:
        if getattr(self, key) != value:
            setattr(self, key, value)
            self._bump(key)

    def _bump(self, key: str) -> None:
        self.versions[key] = self.versions.get(key, 0) + 1

    def watch_label(self) -> str:
        return C.WATCH_OPTIONS[self.settings["watch"]][0].split(" \u00b7 ")[0]

    def open_watch(self) -> None:
        net.open_in_browser(C.WATCH_OPTIONS[self.settings["watch"]][1])

    def toast(self, title: str, message: str) -> None:
        if not self.settings["toasts"]:
            return
        try:
            self.icon.notify(message[:240], title[:63])
        except Exception:
            log.warning("Toast failed", exc_info=True)

    # ------------------------------------------------------------ window
    def _build_window(self) -> None:
        r = self.root
        r.title(C.APP_NAME)
        r.geometry(f"{px(660)}x{px(780)}")
        r.minsize(px(580), px(640))
        r.configure(bg=C.BG)
        r.protocol("WM_DELETE_WINDOW", self.hide)
        self._icon_img = ImageTk.PhotoImage(assets.app_icon(px(64)))
        r.iconphoto(True, self._icon_img)

        style = ttk.Style(r)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Vertical.TScrollbar", background=C.CARD, troughcolor=C.BG,
                        bordercolor=C.BG, arrowcolor=C.MUTED)

        header = tk.Frame(r, bg=C.NAVY, height=px(56))
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Frame(header, bg=C.RED, height=px(3)).pack(side="bottom", fill="x")
        self._hdr_img = ImageTk.PhotoImage(assets.app_icon(px(38)))
        self.l_hdr_img = tk.Label(header, image=self._hdr_img, bg=C.NAVY)
        self.l_hdr_img.pack(side="left", padx=(px(12), px(8)))
        lbl(header, C.APP_NAME.upper(), 12, True, bg=C.NAVY).pack(side="left")
        self.b_refresh = btn(header, "\U0001F504 Refresh", self.refresh, bg="#1a3152", size=8, bold=False)
        self.b_refresh.pack(side="right", padx=(px(6), px(12)))
        self.b_ticker = btn(header, "\U0001F5A5 Ticker", self._toggle_ticker, bg="#1a3152", size=8, bold=False)
        self.b_ticker.pack(side="right", padx=px(4))
        self.b_spoiler = btn(header, "", lambda: self._toggle("spoiler_mode", not self.settings["spoiler_mode"]),
                             size=8, bold=False)
        self.b_spoiler.pack(side="right", padx=px(4))
        self._sync_spoiler_button()
        self.b_update = btn(header, "\u2B06 Update available", self._open_update, bg=C.GOLD, fg=C.NAVY, size=8)

        nav = tk.Frame(r, bg=C.BAR)
        nav.pack(fill="x")
        self.tab_buttons: Dict[str, tk.Button] = {}
        for key, text in self.TABS:
            b = btn(nav, text, lambda k=key: self.switch_tab(k), bg=C.BAR, fg=C.MUTED, bold=False)
            b.configure(pady=px(7), padx=px(8))
            b.pack(side="left")
            self.tab_buttons[key] = b

        footer = tk.Frame(r, bg=C.BAR, height=px(40))
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        self.sound_var = tk.BooleanVar(value=self.settings["sound"])
        tk.Checkbutton(footer, text="Goal horn" if C.TEAM == "CBJ" else "Goal sound", variable=self.sound_var,
                       command=lambda: self._toggle("sound", self.sound_var.get()),
                       font=(C.FONT, 8), fg=C.SILVER, bg=C.BAR, selectcolor=C.NAVY,
                       activebackground=C.BAR, activeforeground=C.TEXT).pack(side="left", padx=px(8))
        btn(footer, "\U0001F50A Test horn", assets.play_horn, bg="#1a2d47", fg=C.GOLD, size=8).pack(side="left", pady=px(6))
        self.l_vol = lbl(footer, "", 8, fg=C.SILVER, bg=C.BAR, width=9, anchor="e")
        self.l_vol.pack(side="left", padx=(px(8), px(2)))
        self.vol_var = tk.IntVar(value=self.settings["volume"])
        self.scale_vol = tk.Scale(footer, from_=0, to=100, orient="horizontal", variable=self.vol_var, showvalue=False,
                                  command=self._on_volume, length=px(110), width=px(10), sliderlength=px(16), bd=0,
                                  bg=C.BAR, troughcolor=C.CARD, activebackground=C.RED, highlightthickness=0)
        self.scale_vol.pack(side="left")
        self.scale_vol.bind("<Button-1>", self._on_scale_press)
        self.scale_vol.bind("<B1-Motion>", self._on_scale_motion)
        self.scale_vol.bind("<ButtonRelease-1>", self._on_scale_release)
        self._scale_trough_dragging = False
        self._sync_volume_label()
        self.l_delay = lbl(footer, "", 8, fg=C.GOLD, bg=C.BAR)
        self.l_delay.pack(side="left", padx=px(10))
        btn(footer, "Hide to tray", self.hide, size=8, bold=False).pack(side="right", padx=px(10), pady=px(6))

        self.body = tk.Frame(r, bg=C.BG)
        self.body.pack(fill="both", expand=True)
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(0, weight=1)

        # Scrollable container for live tab (holds scoreboard + shot chart + scoring)
        live_frame = tk.Frame(self.body, bg=C.BG)
        live_canvas = tk.Canvas(live_frame, bg=C.BG, highlightthickness=0, bd=0)
        live_bar = ttk.Scrollbar(live_frame, orient="vertical", command=live_canvas.yview)
        live_canvas.configure(yscrollcommand=live_bar.set)
        live_canvas.pack(side="left", fill="both", expand=True, padx=(px(10), px(2)), pady=px(4))
        live_bar.pack(side="right", fill="y")
        live_inner = tk.Frame(live_canvas, bg=C.BG)
        live_win = live_canvas.create_window(0, 0, window=live_inner, anchor="nw")

        def _sync_live(_e=None):
            live_canvas.configure(scrollregion=live_canvas.bbox("all"))

        def _resize_live(event):
            live_canvas.itemconfigure(live_win, width=event.width)

        live_inner.bind("<Configure>", _sync_live)
        live_canvas.bind("<Configure>", _resize_live)
        self.scroll_canvases.add(live_canvas)
        self.live_canvas = live_canvas
        self.live_inner = live_inner

        self.frames: Dict[str, tk.Frame] = {"live": live_frame}
        for key in ("games", "shots", "standings", "news", "roster", "settings"):
            self.frames[key] = ScrollArea(self.body, self.scroll_canvases)
        for fr in self.frames.values():
            fr.grid(row=0, column=0, sticky="nsew")
        self._build_live()
        self.switch_tab("live")

    def _sync_spoiler_button(self) -> None:
        on = self.settings["spoiler_mode"]
        self.b_spoiler.configure(text="\U0001F648 Scores hidden" if on else "\U0001F441 Scores shown",
                                 bg=C.RED if on else C.HILITE, fg=C.TEXT)

    def _sync_volume_label(self) -> None:
        v = self.settings["volume"]
        self.l_vol.configure(text=("\U0001F507 " if v == 0 else "\U0001F509 ") + f"{v}%")

    def _on_volume(self, value: str) -> None:
        self.settings["volume"] = int(float(value))
        assets.set_volume(self.settings["volume"])
        self._sync_volume_label()
        if self._vol_job:
            self.root.after_cancel(self._vol_job)
        self._vol_job = self.root.after(500, self._commit_volume)

    def _commit_volume(self) -> None:
        self._vol_job = None
        settings.save(self.settings)
        threading.Thread(target=assets.prepare_volume, args=(self.settings["volume"],), daemon=True).start()

    def _scale_from_x(self, x: int) -> None:
        try:
            x0 = self.scale_vol.coords(0)[0]
            x1 = self.scale_vol.coords(100)[0]
        except Exception:
            x0 = px(8)
            x1 = px(110) - px(8)
        if x1 != x0:
            frac = (x - x0) / float(x1 - x0)
            val = int(round(max(0, min(100, frac * 100))))
            self.vol_var.set(val)
            self.scale_vol.set(val)
            self._on_volume(str(val))

    def _on_scale_press(self, event: tk.Event) -> Optional[str]:
        if self.scale_vol.identify(event.x, event.y) != "slider":
            self._scale_from_x(event.x)
            self._scale_trough_dragging = True
            return "break"
        self._scale_trough_dragging = False
        return None

    def _on_scale_motion(self, event: tk.Event) -> Optional[str]:
        if getattr(self, "_scale_trough_dragging", False):
            self._scale_from_x(event.x)
            return "break"
        return None

    def _on_scale_release(self, _event: tk.Event) -> None:
        self._scale_trough_dragging = False

    def _build_live(self) -> None:
        f = self.live_inner
        top = tk.Frame(f, bg=C.CARD, pady=px(10))
        top.pack(fill="x", pady=(0, px(6)))
        tk.Frame(top, bg=C.RED, height=px(3)).pack(fill="x", side="top")
        self._live_img = ImageTk.PhotoImage(assets.app_icon(px(56)))
        self.l_logo = tk.Label(top, image=self._live_img, bg=C.CARD)
        self.l_logo.pack(pady=(px(6), 0))
        self.l_title = lbl(top, "", 9, True, C.SILVER)
        self.l_title.pack(pady=(px(2), 0))
        self.l_matchup = lbl(top, "", 16, True)
        self.l_matchup.pack(pady=(px(2), 0))
        self.l_big = lbl(top, "-- : --", 26, True, C.ACCENT)
        self.l_big.pack()
        self.l_when = lbl(top, "Loading\u2026", 10)
        self.l_when.pack()
        self.l_sit = lbl(top, "", 10, True, C.GOLD)
        self.l_sit.pack()
        self.l_venue = lbl(top, "", 9, fg=C.MUTED)
        self.l_venue.pack(pady=(px(2), 0))
        self.l_tv = lbl(top, "", 9, fg=C.MUTED)
        self.l_tv.pack()

        bar = tk.Frame(f, bg=C.BG)
        bar.pack(fill="x", pady=(0, px(8)))
        self.b_watch = btn(bar, "", self.open_watch, bg="#00838f")
        self.b_watch.pack(side="left")
        self.b_gc = btn(bar, "GameCenter \u2197", self._open_current_gamecenter)
        self.b_gc.pack(side="left", padx=px(6))
        self.b_reveal = btn(bar, "\U0001F441 Reveal score", self._reveal_current, bg=C.RED)
        self._sync_watch_button()

        # Regulation Ice Rink & Interactive Shot Chart (dynamically shown during LIVE games)
        self.shot_chart = rink.ShotChart(f, bg=C.CARD)
        self.b_view_shots = btn(f, "\U0001F3AF View Completed Game Shot Charts & Season Heatmaps \u2192",
                                lambda: self.switch_tab("shots"), bg="#1a3152", size=8, bold=False)
        self.b_view_shots.pack(fill="x", pady=(0, px(8)))

        self.panes = tk.Frame(f, bg=C.BG)
        self.panes.pack(fill="both", expand=True)
        self.t_goals = self._text_pane(self.panes, "SCORING", 5)
        self.t_pens = self._text_pane(self.panes, "PENALTIES", 4)

    def _text_pane(self, parent, title: str, height: int) -> tk.Text:
        box = tk.Frame(parent, bg=C.CARD)
        box.pack(fill="both", expand=True, pady=(0, px(8)))
        lbl(box, title, 9, True, C.SILVER).pack(anchor="w", padx=px(12), pady=(px(6), px(2)))
        t = tk.Text(box, height=height, bg=C.CARD_DEEP, fg=C.TEXT, font=("Consolas", 9),
                    relief="flat", bd=0, padx=px(8), pady=px(6), state="disabled", wrap="word")
        t.pack(fill="both", expand=True, padx=px(10), pady=(0, px(10)))
        return t

    def _sync_watch_button(self) -> None:
        self.b_watch.configure(text=f"\U0001F4FA Watch on {self.watch_label()}")

    def switch_tab(self, key: str) -> None:
        self.active_tab = key
        for k, b in self.tab_buttons.items():
            on = k == key
            b.configure(bg=C.RED if on else C.BAR, fg=C.TEXT if on else C.MUTED,
                        font=(C.FONT, 9, "bold" if on else "normal"))
        self._render_active(force=False)   # build while hidden, then raise
        self.frames[key].tkraise()

    # ------------------------------------------------------------ tray
    def _build_tray(self) -> None:
        def go(tab):
            return lambda *_: self.post(lambda: (self.show(), self.switch_tab(tab)))

        def toggle(key):
            return lambda *_: self.post(lambda: self._toggle(key, not self.settings[key]))

        menu = pystray.Menu(
            pystray.MenuItem("Open", go("live"), default=True),
            pystray.MenuItem("Games && Stats", go("games")),   # "&&" = literal & in Windows menus
            pystray.MenuItem("Shot Charts && Heatmaps", go("shots")),
            pystray.MenuItem("Standings", go("standings")),
            pystray.MenuItem("News", go("news")),
            pystray.MenuItem("Roster", go("roster")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(lambda _: f"Watch on {self.watch_label()}", lambda *_: self.post(self.open_watch)),
            pystray.MenuItem("Mute goal horn", toggle("sound"), checked=lambda _: not self.settings["sound"]),
            pystray.MenuItem("Floating ticker bar", toggle("ticker_bar"), checked=lambda _: self.settings.get("ticker_bar", False)),
            pystray.MenuItem("Mini scoreboard", toggle("mini_overlay"), checked=lambda _: self.settings["mini_overlay"]),
            pystray.MenuItem("Spoiler mode", toggle("spoiler_mode"), checked=lambda _: self.settings["spoiler_mode"]),
            pystray.MenuItem("Refresh now", lambda *_: self.post(self.refresh)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", lambda *_: self.post(self.exit)),
        )
        self.icon = pystray.Icon(C.APP_ID, self._icon_base, C.APP_NAME, menu=menu)
        self.icon.run_detached()

    def _set_tooltip(self, text: str) -> None:
        try:
            self.icon.title = text[:63]
        except Exception:
            pass

    def _update_tray_icon(self) -> None:
        g = self.game
        key = None
        if self.settings.get("tray_live_score", False) and g and g.get("gameState") in data.LIVE_STATES:
            _, us, them = data.perspective(g, C.TEAM)
            key = (int(us.get("score") or 0), int(them.get("score") or 0))
        if key == self.icon_key:
            return
        self.icon_key = key
        try:
            self.icon.icon = assets.score_icon(*key) if key else self._icon_base
        except Exception:
            log.warning("Tray icon update failed", exc_info=True)

    def _toggle_ticker(self) -> None:
        self._toggle("ticker_bar", not self.settings.get("ticker_bar", False))

    def _toggle(self, key: str, value: bool) -> None:
        self.settings[key] = bool(value)
        if key == "sound":
            self.sound_var.set(value)
        if key == "start_with_windows" and not settings.set_autostart(value):
            self.settings[key] = False
            messagebox.showwarning(C.APP_NAME, "Could not update Windows start-up setting. See log for details.")
        if key in self.setting_vars:
            self.setting_vars[key].set(self.settings[key])
        settings.save(self.settings)
        try:
            self.icon.update_menu()
        except Exception:
            pass
        if key == "spoiler_mode":
            self._sync_spoiler_button()
            self._bump("_ui")
            self._render_live()
            self._render_active(force=False)
        elif key == "mini_overlay":
            if value:
                self.overlay.dismissed = None
            self._render_live()
        elif key == "ticker_bar":
            if value:
                self.ticker.show()
            else:
                self.ticker.hide()
        elif key == "tray_live_score":
            self.icon_key = "toggle"
            self._update_tray_icon()

    def show(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide(self) -> None:
        self.root.withdraw()

    def refresh(self) -> None:
        self.b_refresh.configure(text="\u23F3 Refreshing\u2026", state="disabled")
        self.force_refresh = True
        self.wake_event.set()

    def exit(self) -> None:
        self.stop_event.set()
        self.wake_event.set()
        try:
            self.icon.stop()
        except Exception:
            pass
        self.root.destroy()

    # ------------------------------------------------------------ worker
    def _start_worker(self) -> None:
        threading.Thread(target=self._worker, name="fetch", daemon=True).start()

    def _worker(self) -> None:
        last = {"slow": -1e9, "roster": -1e9, "news": -1e9, "update": -1e9}
        while not self.stop_event.is_set():
            snap: Dict[str, Any] = {}
            now = time.monotonic()
            force, self.force_refresh = self.force_refresh, False
            try:
                game = data.find_team_game(net.fetch_json(C.URL_SCORE_NOW), C.TEAM)
                snap["game"], snap["boxscore"], snap["live_landing"] = game, None, None
                state = (game or {}).get("gameState")
                if game and state in data.LIVE_STATES + data.FINAL_STATES:
                    gid = int(game["id"])
                    snap["boxscore"] = net.fetch_json(C.URL_BOXSCORE.format(game_id=gid))
                    try:
                        snap["live_landing"] = net.fetch_json(C.URL_LANDING.format(game_id=gid))
                    except Exception as exc:
                        log.warning("Live landing fetch failed: %s", exc)
                    try:
                        pbp = net.fetch_json(C.URL_PLAY_BY_PLAY.format(game_id=gid))
                        snap["shot_data"] = {gid: data.parse_shot_chart(pbp, C.NHL_TEAM_ID, C.TEAM)}
                    except Exception as exc:
                        log.warning("Live play-by-play fetch failed: %s", exc)
                snap["offline"] = False
            except Exception as exc:
                log.warning("Scoreboard fetch failed: %s", exc)
                snap.pop("game", None)
                snap["offline"] = True
            if force or now - last["slow"] > C.SLOW_REFRESH:
                for key, url in (("schedule", C.URL_SCHEDULE), ("stats", C.URL_CLUB_STATS),
                                 ("standings", C.URL_STANDINGS)):
                    try:
                        payload = net.fetch_json(url)
                        snap[key] = payload.get("games", []) if key == "schedule" else payload
                    except Exception as exc:
                        log.warning("%s fetch failed: %s", key, exc)
                last["slow"] = now
            if force or now - last["roster"] > 6 * 3600:
                try:
                    snap["roster"] = data.parse_roster(net.fetch_json(C.URL_ROSTER))
                    last["roster"] = now
                except Exception as exc:
                    log.warning("Roster fetch failed: %s", exc)
            if C.GITHUB_REPO and (force or now - last["update"] > C.UPDATE_CHECK):
                last["update"] = now
                info = self._check_update()
                if info:
                    snap["update_info"] = info
            self.post(lambda s=snap: self._apply(s))
            # News last and in parallel, so a slow feed never delays scores.
            if force or now - last["news"] > C.NEWS_REFRESH:
                last["news"] = now
                news = self._fetch_news()
                self.post(lambda n=news: self._apply({"news_by_source": n}))

            state = (snap.get("game") or {}).get("gameState")
            interval = C.POLL_LIVE if state in data.LIVE_STATES else (
                C.POLL_GAMEDAY if snap.get("game") and state not in data.FINAL_STATES else C.POLL_IDLE)
            self.wake_event.wait(interval)
            self.wake_event.clear()

    @staticmethod
    def _fetch_one_source(src: Dict[str, str]) -> List[dict]:
        if src["kind"] == "forge":
            return data.parse_forge(net.fetch_json(src["url"]), src["name"])
        if src["kind"] == "espn":
            return data.parse_espn(net.fetch_json(src["url"]), src["name"])
        items = data.parse_feed(net.fetch_bytes(src["url"], C.MAX_FEED_BYTES, timeout=20), src["name"])
        if src.get("filter"):
            keywords = [k.strip().lower() for k in src["filter"].split(",") if k.strip()]
            items = [i for i in items if any(k in i["title"].lower() or k in i["desc"].lower() for k in keywords)]
        return items

    @classmethod
    def _fetch_news(cls) -> Dict[str, List[dict]]:
        out: Dict[str, List[dict]] = {}
        with ThreadPoolExecutor(max_workers=len(C.NEWS_SOURCES)) as pool:
            futures = {src["id"]: pool.submit(cls._fetch_one_source, src) for src in C.NEWS_SOURCES}
            for sid, fut in futures.items():
                try:
                    out[sid] = fut.result()
                except Exception as exc:
                    log.warning("News source %s failed: %s", sid, exc)
        return out

    @staticmethod
    def _check_update() -> Optional[dict]:
        if not _REPO_RE.match(C.GITHUB_REPO):
            return None
        try:
            rel = net.fetch_json(C.URL_GITHUB_LATEST.format(repo=C.GITHUB_REPO))
        except Exception as exc:
            log.info("Update check failed: %s", exc)
            return None
        tag, url = str(rel.get("tag_name") or "")[:40], rel.get("html_url")
        if data.version_tuple(tag) > data.version_tuple(__version__) and net.is_safe_browser_url(url):
            return {"tag": data.clean_text(tag, 40), "url": url}
        return None

    def _fetch_landing(self, game_id: int) -> None:
        def run():
            try:
                landing = net.fetch_json(C.URL_LANDING.format(game_id=int(game_id)))
            except Exception as exc:
                log.warning("Landing fetch failed: %s", exc)
                landing = {"error": True}
            self.post(lambda: self._store_landing(game_id, landing))
        threading.Thread(target=run, daemon=True).start()

    def _store_landing(self, game_id: int, landing: dict) -> None:
        self.landing[game_id] = landing
        self._bump("landing")
        self._render_active(force=False)

    def _fetch_all_past_shot_charts(self) -> None:
        past = data.split_schedule(self.schedule)[0]
        missing = [int(g["id"]) for g in past if g.get("id") and int(g["id"]) not in self.shot_data]
        if not missing or getattr(self, "_batch_fetching_shots", False):
            return
        self._batch_fetching_shots = True

        def run():
            try:
                for gid in missing:
                    if self.stop_event.is_set():
                        break
                    try:
                        pbp = net.fetch_json(C.URL_PLAY_BY_PLAY.format(game_id=gid))
                        parsed = data.parse_shot_chart(pbp, C.NHL_TEAM_ID, C.TEAM)
                        self.post(lambda g=gid, s=parsed: self._store_shot_chart(g, s))
                    except Exception as exc:
                        log.warning("Batch shot chart fetch failed for %s: %s", gid, exc)
            finally:
                self._batch_fetching_shots = False

        threading.Thread(target=run, name="batch_shots", daemon=True).start()

    def _fetch_shot_chart(self, game_id: int) -> None:
        if game_id in self.shot_data:
            return
        def run():
            try:
                pbp = net.fetch_json(C.URL_PLAY_BY_PLAY.format(game_id=int(game_id)))
                shots = data.parse_shot_chart(pbp, C.NHL_TEAM_ID, C.TEAM)
            except Exception as exc:
                log.warning("Shot chart fetch failed for %s: %s", game_id, exc)
                shots = {"shots": [], "counts": {}, "opponent": "OPP"}
            self.post(lambda: self._store_shot_chart(game_id, shots))
        threading.Thread(target=run, daemon=True).start()

    def _store_shot_chart(self, game_id: int, shots: dict) -> None:
        self.shot_data[game_id] = shots
        if self.active_tab == "shots":
            self._bump("_ui")
            self._render_active(force=False)
        g = self.display_game()
        if g and int(g.get("id", 0)) == game_id and g.get("gameState") in data.LIVE_STATES:
            if not self.spoiler_hidden(g):
                self.shot_chart.load_shots(shots, banner="\U0001F534 LIVE IN-GAME SHOT CHART")

    # ------------------------------------------------------------ state
    def _apply(self, snap: Dict[str, Any]) -> None:
        for key in ("schedule", "stats", "standings", "roster", "offline", "update_info"):
            if key in snap:
                self._set(key, snap[key])
        if snap.get("shot_data"):
            self.shot_data.update(snap["shot_data"])
        if snap.get("news_by_source"):
            self.news_by_source = {**self.news_by_source, **snap["news_by_source"]}
            self._set("news", data.merge_news(*self.news_by_source.values()))
        if "game" in snap:
            self.delay_q.append((time.monotonic(), {k: snap.get(k) for k in ("game", "boxscore", "live_landing", "shot_data")}))
        self._release_delayed()
        if self.update_info and not self.update_toasted:
            self.update_toasted = True
            self.toast("Update available", f"{C.APP_NAME} {self.update_info['tag']} is out.")
        self._render_live()
        self._render_active(force=False)

    def _release_delayed(self) -> bool:
        """Apply buffered live snapshots once they are older than the delay."""
        delay = self.settings["delay_seconds"]
        now, changed = time.monotonic(), False
        while self.delay_q:
            ts, live = self.delay_q[0]
            state = (live.get("game") or {}).get("gameState")
            if delay and state in data.LIVE_STATES + data.FINAL_STATES and now - ts < delay:
                break
            self.delay_q.popleft()
            self._set("game", live.get("game"))
            self._set("boxscore", live.get("boxscore"))
            self._set("live_landing", live.get("live_landing"))
            if live.get("shot_data"):
                self.shot_data.update(live["shot_data"])
            self._check_game_events()
            changed = True
        return changed

    def sched_game(self, game_id: Any) -> Optional[dict]:
        return next((g for g in self.schedule if g.get("id") == game_id), None)

    def display_game(self) -> Optional[dict]:
        return data.enrich(self.game, self.sched_game(self.game.get("id"))) if self.game else None

    def next_game(self) -> Optional[dict]:
        now = datetime.now(timezone.utc)
        upcoming = [g for g in self.schedule if g.get("gameState") not in data.FINAL_STATES
                    and (data.parse_utc(g.get("startTimeUTC")) or now) >= now]
        return min(upcoming, key=lambda g: g.get("startTimeUTC", ""), default=None)

    def spoiler_hidden(self, g: Optional[dict]) -> bool:
        return bool(g and self.settings["spoiler_mode"] and g.get("gameState") in data.FINAL_STATES
                    and int(g.get("id") or 0) not in self.revealed)

    def _check_game_events(self) -> None:
        g = self.game
        if not g:
            return
        gid, state = g.get("id"), g.get("gameState")
        _, us, them = data.perspective(g, C.TEAM)
        us_s, them_s = int(us.get("score") or 0), int(them.get("score") or 0)
        them_ab = them.get("abbrev", "OPP")
        clock = g.get("clock") or {}
        score_txt = f"{C.TEAM} {us_s} \u2013 {them_s} {them_ab}"
        when = f"{data.period_label(g)} {clock.get('timeRemaining', '')}".strip()

        if self.goal_tracker.update(gid, us_s):
            self._goal_alert(score_txt, data.last_scorer(g.get("goals") or [], C.TEAM), when)
        if self.opp_tracker.update(gid, them_s):
            if self.settings["opponent_sound"]:
                assets.play_chime()
            self.toast(f"{them_ab} goal", f"{score_txt} \u00b7 {when}")

        prev = self.game_states.get(gid)
        self.game_states[gid] = state
        if prev is not None and prev != state:
            if state in data.LIVE_STATES and prev not in data.LIVE_STATES + data.FINAL_STATES:
                self.toast("Puck drop!", f"Blue Jackets {data.matchup_line(self.display_game(), C.TEAM)}")
            elif state in data.FINAL_STATES and prev not in data.FINAL_STATES:
                self._bump("_ui")
                if self.settings["spoiler_mode"]:
                    self.toast("Final", "The game is over. Open the app to reveal the score.")
                else:
                    res, ours, theirs = data.result_of(g, C.TEAM)
                    word = "win" if res == "W" else "fall"
                    self.toast("Final", f"Blue Jackets {word} {ours}\u2013{theirs} {data.matchup_line(g, C.TEAM)}")
        inter = bool(clock.get("inIntermission"))
        prev_i = self.intermissions.get(gid)
        self.intermissions[gid] = inter
        if state in data.LIVE_STATES and prev_i is False and inter:
            self.toast(f"End of {data.period_label(g)}", score_txt)
        if state in data.LIVE_STATES and gid not in self.popped_games:
            self.popped_games.add(gid)
            if self.settings["auto_popup"]:
                self.show()

    def _goal_alert(self, score_txt: str, scorer: str, when: str) -> None:
        if self.settings["sound"]:
            assets.play_horn()
        if self.settings["popup_on_goal"]:
            self.show()
        self.toast("\U0001F6A8 BLUE JACKETS GOAL!", " \u00b7 ".join(x for x in (scorer, score_txt, when) if x))
        self.flash_until = time.monotonic() + 5
        self.root.after(5100, self._render_live)

    # ------------------------------------------------------------ live tab
    def _render_live(self) -> None:
        g = self.display_game()
        if g:
            self._render_game(g)
        else:
            self._render_next()
        if self.offline:
            self.b_refresh.configure(text="\u26A0\uFE0F Offline \u00b7 Retry", bg=C.RED, state="normal")
        else:
            self.b_refresh.configure(text="\U0001F504 Refresh", bg="#1a3152", state="normal")
        if self.update_info and not self.b_update.winfo_manager():
            self.b_update.pack(side="right", padx=(0, px(4)))
        delay = self.settings["delay_seconds"]
        self.l_delay.configure(text=f"\u23F1 {delay}s delay" if delay else "")
        self._update_overlay()
        self._update_tray_icon()
        if self.settings.get("ticker_bar") and self.ticker.win is not None:
            self.ticker.update_content()
        self._tick(reschedule=False)

    def _show_reveal(self, show: bool) -> None:
        if show and not self._reveal_shown:
            self.b_reveal.pack(side="right")
        elif not show and self._reveal_shown:
            self.b_reveal.pack_forget()
        self._reveal_shown = show

    def _render_next(self) -> None:
        nxt = self.next_game()
        self._show_reveal(False)
        self.l_sit.configure(text="")
        self._set_text(self.t_goals, [], "Scoring plays appear here during games.")
        self._set_text(self.t_pens, [], "Penalties appear here during games.")
        self.b_gc.configure(text="Game preview \u2197")
        self.shot_chart.pack_forget()
        self.b_view_shots.pack(fill="x", pady=(0, px(8)), before=self.panes)
        if nxt:
            gtype = data.GAME_TYPES.get(nxt.get("gameType"), "")
            self.l_title.configure(text=f"NEXT GAME \u00b7 {gtype.upper()}")
            self.l_matchup.configure(text=data.matchup_line(nxt, C.TEAM))
            self.l_when.configure(text=data.local_start(nxt), fg=C.TEXT)
            self.l_venue.configure(text=f"\U0001F4CD {data.venue_line(nxt)}")
            tv = data.broadcasts(nxt, C.TEAM)
            self.l_tv.configure(text=f"\U0001F4FA {tv}" if tv else "")
            self._set_tooltip(f"Next: {data.matchup_line(nxt, C.TEAM)} {data.local_start(nxt)}")
        else:
            for w in (self.l_title, self.l_matchup, self.l_venue, self.l_tv):
                w.configure(text="")
            self.l_big.configure(text="NO GAMES", fg=C.MUTED)
            self.l_when.configure(text="Loading schedule\u2026" if not self.schedule else "No upcoming games on the schedule",
                                  fg=C.MUTED)

    def _render_game(self, g: dict) -> None:
        home, away = g.get("homeTeam") or {}, g.get("awayTeam") or {}
        state = g.get("gameState")
        gid = int(g.get("id") or 0)
        gtype = data.GAME_TYPES.get(g.get("gameType"), "").upper()
        score = f"{away.get('abbrev', '')}  {away.get('score', 0)}  \u2013  {home.get('score', 0)}  {home.get('abbrev', '')}"
        sog = f"Shots {away.get('abbrev', '')} {away.get('sog', 0)} \u00b7 {home.get('abbrev', '')} {home.get('sog', 0)}"
        tv = data.broadcasts(g, C.TEAM)
        self.l_matchup.configure(text=data.matchup_line(g, C.TEAM))
        self.l_tv.configure(text=f"\U0001F4FA {tv}" if tv else "")
        self.b_gc.configure(text="GameCenter \u2197" if state in data.LIVE_STATES + data.FINAL_STATES
                            else "Game preview \u2197")
        goals = data.goal_lines(g.get("goals") or [])
        pens = data.penalty_lines(self.live_landing) if self.live_landing else []
        delay = self.settings["delay_seconds"]
        hidden = self.spoiler_hidden(g)
        self._show_reveal(hidden)

        if state in data.LIVE_STATES:
            self.b_view_shots.pack_forget()
            self.shot_chart.pack(fill="x", pady=(0, px(8)), before=self.panes)
            if hidden:
                self.shot_chart.load_shots({"shots": [], "counts": {}, "opponent": ""}, banner="\U0001F534 LIVE IN-GAME SHOT CHART")
            elif gid in self.shot_data:
                self.shot_chart.load_shots(self.shot_data[gid], banner="\U0001F534 LIVE IN-GAME SHOT CHART")
            else:
                self._fetch_shot_chart(gid)
        else:
            self.shot_chart.pack_forget()
            self.b_view_shots.pack(fill="x", pady=(0, px(8)), before=self.panes)

        if state in data.LIVE_STATES:
            clock = g.get("clock") or {}
            period = data.period_label(g)
            when = (f"{period} Intermission \u00b7 {clock.get('timeRemaining', '')}" if clock.get("inIntermission")
                    else f"{period} period \u00b7 {clock.get('timeRemaining', '')} left")
            self.l_title.configure(text=f"\u25CF LIVE \u00b7 {gtype}" + (f" \u00b7 {delay}s DELAY" if delay else ""))
            self.l_big.configure(text=score, fg=C.TEXT)
            self.l_when.configure(text=when, fg=C.ACCENT)
            self.l_venue.configure(text=f"{sog} \u00b7 {data.venue_line(g)}")
            self.l_sit.configure(**self._situation_text(g))
            self._set_text(self.t_goals, goals, "No goals yet.")
            self._set_text(self.t_pens, pens, "No penalties yet.")
            self._set_tooltip(f"LIVE {away.get('abbrev')} {away.get('score', 0)}-{home.get('score', 0)} "
                              f"{home.get('abbrev')} \u00b7 {period} {clock.get('timeRemaining', '')}")
        elif state in data.FINAL_STATES:
            last = (g.get("gameOutcome") or {}).get("lastPeriodType", "REG")
            suffix = f" ({last})" if last in ("OT", "SO") else ""
            self.l_title.configure(text=f"FINAL{suffix} \u00b7 {gtype}")
            self.l_sit.configure(text="")
            if hidden:
                self.l_big.configure(text="SCORE HIDDEN", fg=C.MUTED)
                self.l_when.configure(text="Spoiler mode is on \u2014 press Reveal score when ready", fg=C.MUTED)
                self.l_venue.configure(text=f"\U0001F4CD {data.venue_line(g)}")
                self._set_text(self.t_goals, [], "Hidden (spoiler mode).")
                self._set_text(self.t_pens, [], "Hidden (spoiler mode).")
                self._set_tooltip(f"Final {data.matchup_line(g, C.TEAM)} (spoiler mode)")
                return
            res, ours, theirs = data.result_of(g, C.TEAM)
            word = {"W": "WIN", "L": "LOSS", "OTL": "LOSS"}[res]
            self.l_big.configure(text=score, fg=C.TEXT)
            self.l_when.configure(text=f"Blue Jackets {word} {ours}\u2013{theirs}{suffix}",
                                  fg=C.GREEN if res == "W" else C.SILVER)
            self.l_venue.configure(text=f"{sog} \u00b7 {data.venue_line(g)}")
            self._set_text(self.t_goals, goals, "No goals.")
            self._set_text(self.t_pens, pens, "No penalties.")
            self._set_tooltip(f"Final: {away.get('abbrev')} {away.get('score', 0)}-{home.get('score', 0)} "
                              f"{home.get('abbrev')}{suffix}")
        else:
            self.l_title.configure(text=f"GAMEDAY \u00b7 {gtype}")
            self.l_when.configure(text=f"Puck drop {data.local_start(g)}", fg=C.TEXT)
            self.l_venue.configure(text=f"\U0001F4CD {data.venue_line(g)}")
            self.l_sit.configure(text="")
            self._set_text(self.t_goals, [], "Scoring plays appear here once the puck drops.")
            self._set_text(self.t_pens, [], "Penalties appear here once the puck drops.")
            self._set_tooltip(f"Today {data.matchup_line(g, C.TEAM)} {data.local_start(g)}")

    def _situation_text(self, g: dict) -> Dict[str, Any]:
        sit = data.situation(self.live_landing, g)
        if not sit:
            return {"text": ""}
        parts, ours = [], False
        if sit.get("pp"):
            ours = sit["pp"] == C.TEAM
            who = "BLUE JACKETS" if ours else sit["pp"]
            clock = f" \u00b7 {sit['time']}" if sit.get("time") else ""
            parts.append(f"\u26A1 {who} POWER PLAY ({sit['advantage']}){clock}")
        for team in sit.get("empty_net") or []:
            parts.append(f"\U0001F945 {team} goalie pulled")
        return {"text": "   ".join(parts), "fg": C.GOLD if ours or not sit.get("pp") else "#ff8a80"}

    def _countdown_target(self) -> Optional[dict]:
        g = self.game
        if g and g.get("gameState") not in data.LIVE_STATES + data.FINAL_STATES:
            return self.display_game()
        return None if g else self.next_game()

    def _tick(self, reschedule: bool = True) -> None:
        if reschedule and self._release_delayed():
            self._render_live()
            self._render_active(force=False)
        if time.monotonic() < self.flash_until:
            self.l_big.configure(text="\U0001F6A8 GOAL! \U0001F6A8", fg="#ff1744")
        else:
            target = self._countdown_target()
            start = data.parse_utc(target.get("startTimeUTC")) if target else None
            if start:
                secs = (start - datetime.now(timezone.utc)).total_seconds()
                if secs > 0:
                    self.l_big.configure(text=data.format_countdown(secs), fg=C.ACCENT)
                else:
                    self.l_big.configure(text="PUCK DROP SOON", fg=C.GOLD)
                gid = target.get("id")
                if 0 < secs <= 1800 and gid not in self.reminded:
                    self.reminded.add(gid)
                    if self.settings["puck_drop_reminder"]:
                        self.toast(f"Puck drop in {max(1, int(secs // 60))} min",
                                   f"Blue Jackets {data.matchup_line(target, C.TEAM)} \u00b7 "
                                   f"{data.local_start(target)} \u00b7 {data.venue_line(target)}")
        if reschedule and not self.stop_event.is_set():
            self.root.after(1000, self._tick)

    def _update_overlay(self) -> None:
        g = self.game
        live = bool(g and g.get("gameState") in data.LIVE_STATES)
        if not (live and self.settings["mini_overlay"] and g.get("id") != self.overlay.dismissed):
            self.overlay.hide()
            return
        home, away = g.get("homeTeam") or {}, g.get("awayTeam") or {}
        clock = g.get("clock") or {}
        period = data.period_label(g)
        info = f"{period} INT \u00b7 {clock.get('timeRemaining', '')}" if clock.get("inIntermission") \
            else f"{period} \u00b7 {clock.get('timeRemaining', '')}"
        sit = data.situation(self.live_landing, g)
        if sit.get("pp"):
            info += f" \u00b7 {sit['pp']} PP"
        if sit.get("empty_net"):
            info += " \u00b7 EN"
        score = f"{away.get('abbrev', '')} {away.get('score', 0)} \u2013 {home.get('score', 0)} {home.get('abbrev', '')}"
        flashing = time.monotonic() < self.flash_until
        self.overlay.show("\U0001F6A8 GOAL! " + score if flashing else score, info, flash=flashing)

    @staticmethod
    def _set_text(widget: tk.Text, lines: List[str], empty: str) -> None:
        text = "\n".join(lines) if lines else empty
        if widget.get("1.0", "end-1c") == text:
            return
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", text)
        widget.configure(state="disabled")

    def _reveal_current(self) -> None:
        if self.game:
            self.revealed.add(int(self.game.get("id") or 0))
            self._bump("_ui")
            self._render_live()
            self._render_active(force=False)

    def _open_current_gamecenter(self) -> None:
        past = data.split_schedule(self.schedule)[0]
        target = self.display_game() or self.next_game() or (past[-1] if past else None)
        if not self._open_gamecenter(target):
            net.open_in_browser(f"{C.NHL_WEB}/bluejackets/schedule")

    @staticmethod
    def _open_gamecenter(game: Optional[dict]) -> bool:
        link = (game or {}).get("gameCenterLink") or ""
        if isinstance(link, str) and link.startswith("/") and not link.startswith("//"):
            return net.open_in_browser(C.NHL_WEB + link)
        return False

    def latest_final(self) -> Optional[dict]:
        finals = [g for g in self.schedule if g.get("gameState") in data.FINAL_STATES]
        if self.game and self.game.get("gameState") in data.FINAL_STATES:
            finals.append(self.game)
        return max(finals, key=lambda g: g.get("startTimeUTC", ""), default=None)

    def spoiler_gate(self) -> bool:
        """True when spoiler mode should cover tabs that reveal the latest result."""
        return self.spoiler_hidden(self.latest_final())

    def _spoiler_card(self, p: tk.Frame, what: str) -> None:
        c = card(p)
        lbl(c, "\U0001F648 Hidden by spoiler mode", 10, True, C.GOLD).pack(anchor="w")
        lbl(c, f"{what} could give away the result of the latest game "
               f"({data.matchup_line(self.latest_final(), C.TEAM)}).", 8, wraplength=520,
            justify="left").pack(anchor="w", pady=(px(2), px(6)))
        btn(c, "Reveal the latest result", self._reveal_latest, bg=C.RED, size=8).pack(anchor="w")

    def _reveal_latest(self) -> None:
        g = self.latest_final()
        if g:
            self._reveal(int(g.get("id") or 0))

    def _open_update(self) -> None:
        if self.update_info:
            net.open_in_browser(self.update_info["url"])

    # ------------------------------------------------------------ tab rendering
    def _render_active(self, force: bool) -> None:
        tab = self.active_tab
        if tab not in self.DEPS:
            return
        sig = tuple(self.versions.get(d, 0) for d in self.DEPS[tab])
        if not force and self.rendered.get(tab) == sig:
            return
        self.rendered[tab] = sig
        self.frames[tab].render(getattr(self, f"_render_{tab}"))

    def _bump_ui(self) -> None:
        self._bump("_ui")
        self._render_active(force=False)

    # ---- games
    def _render_games(self, p: tk.Frame) -> None:
        if self.spoiler_gate():
            self._spoiler_card(p, "Records")
        else:
            any_record = False
            for gt in (3, 2, 1):
                rec = data.team_record(self.schedule, C.TEAM, gt)
                if not rec["gp"]:
                    continue
                any_record = True
                c = card(p)
                lbl(c, f"{data.GAME_TYPES[gt].upper()} RECORD \u00b7 {rec['gp']} GP", 8, True, C.SILVER).pack(anchor="w")
                row = tk.Frame(c, bg=C.CARD)
                row.pack(fill="x")
                lbl(row, f"{rec['w']}-{rec['l']}-{rec['otl']}", 18, True, C.ACCENT).pack(side="left")
                lbl(row, "  W-L-OTL", 8, fg=C.MUTED).pack(side="left", anchor="s", pady=(0, px(5)))
                diff = rec["gf"] - rec["ga"]
                stats = tk.Frame(row, bg=C.CARD)
                stats.pack(side="right")
                for i, (name, val, color) in enumerate((("Goals for", rec["gf"], C.TEXT), ("Goals against", rec["ga"], C.TEXT),
                                                        ("Differential", f"{diff:+d}", C.GREEN if diff > 0 else (
                                                            "#ff8a80" if diff < 0 else C.TEXT)))):
                    lbl(stats, str(val), 12, True, color).grid(row=0, column=i, padx=px(10))
                    lbl(stats, name, 7, fg=C.MUTED).grid(row=1, column=i, padx=px(10))
            if any_record:
                lbl(p, "OTL = overtime or shootout loss (worth 1 point). Goals for = goals CBJ scored; goals against = "
                       "goals allowed. A shootout win counts as one goal, matching NHL.com standings.", 7, fg=C.MUTED,
                    bg=C.BG, wraplength=540, justify="left").pack(anchor="w", pady=(px(2), 0))
            else:
                lbl(p, "Loading schedule\u2026" if not self.schedule else "No completed games yet.",
                    fg=C.MUTED, bg=C.BG).pack(anchor="w")

        upcoming = data.upcoming_games(self.schedule, 10)
        if upcoming:
            section(p, "UPCOMING GAMES")
            for g in upcoming:
                c = card(p, pady=px(2))
                row = tk.Frame(c, bg=C.CARD)
                row.pack(fill="x")
                lbl(row, data.local_start(g), 8, True, C.ACCENT, width=18, anchor="w").pack(side="left")
                lbl(row, data.matchup_line(g, C.TEAM), 9, True).pack(side="left")
                tv = data.broadcasts(g, C.TEAM)
                if tv:
                    lbl(row, tv, 8, fg=C.MUTED).pack(side="right")
                lbl(c, data.venue_line(g) + ("  \u00b7  PRESEASON" if g.get("gameType") == 1 else ""),
                    8, fg=C.MUTED).pack(anchor="w", padx=(px(132), 0))

        past = list(reversed(data.split_schedule(self.schedule)[0]))
        if past:
            section(p, "RECENT RESULTS")
            for g in past if self.show_all_games else past[:10]:
                self._game_row(p, g)
            if len(past) > 10:
                btn(p, "Show fewer" if self.show_all_games else f"Show all {len(past)} games",
                    self._toggle_show_all, bg=C.CARD, bold=False).pack(anchor="w", pady=px(4))

        leaders = data.scoring_leaders(self.stats)
        if leaders:
            section(p, f"SCORING LEADERS \u00b7 {data.GAME_TYPES.get(self.stats.get('gameType'), '').upper()}"
                       "  (click a name for a player card)")
            rows = [[s.get("gamesPlayed", 0),
                     f"{data.name_of(s.get('firstName'))} {data.name_of(s.get('lastName'))}",
                     s.get("positionCode", ""), s.get("goals", 0), s.get("assists", 0), s.get("points", 0),
                     f"{s.get('plusMinus', 0):+d}"] for s in leaders]
            table(card(p), ["GP", "PLAYER", "POS", "G", "A", "PTS", "+/-"], rows, [4, 22, 5, 4, 4, 5, 5],
                  accent_col=5, on_click=lambda i: self.open_player(leaders[i].get("playerId")))

        section(p, "DID YOU KNOW?")
        for title, body in FACTS:
            c = card(p)
            lbl(c, title, 9, True, C.ACCENT).pack(anchor="w")
            lbl(c, body, 8, wraplength=520, justify="left").pack(anchor="w")

    def _game_row(self, p: tk.Frame, g: dict) -> None:
        gid = int(g.get("id") or 0)
        res, ours, theirs = data.result_of(g, C.TEAM)
        hidden = self.spoiler_hidden(g)
        c = card(p, pady=px(3))
        top = tk.Frame(c, bg=C.CARD)
        top.pack(fill="x")
        if hidden:
            lbl(top, "  ?  ", 8, True, C.NAVY, C.SILVER, padx=2).pack(side="left")
        else:
            lbl(top, f" {res} {ours}-{theirs} ", 8, True, C.TEXT, C.GREEN if res == "W" else C.RED,
                padx=2).pack(side="left")
        tag = "  \u00b7  PRE" if g.get("gameType") == 1 else ""
        lbl(top, f"  {data.matchup_line(g, C.TEAM)}  \u00b7  {g.get('gameDate', '')}{tag}", 9, True).pack(side="left")
        if hidden:
            btn(top, "Reveal", lambda: self._reveal(gid), size=8, bold=False).pack(side="right")
            return
        open_ = self.expanded == gid
        btn(top, "Close \u25B2" if open_ else "Details \u25BC", lambda: self._toggle_game(gid),
            size=8, bold=False).pack(side="right")
        if not open_:
            return
        box = tk.Frame(c, bg=C.CARD_DEEP, padx=px(8), pady=px(6))
        box.pack(fill="x", pady=(px(6), 0))
        landing = self.landing.get(gid)
        if landing is None:
            lbl(box, "Loading box score\u2026", 8, fg=C.MUTED, bg=C.CARD_DEEP).pack(anchor="w")
        elif landing.get("error"):
            lbl(box, "Couldn't load details. Try again later.", 8, fg=C.MUTED, bg=C.CARD_DEEP).pack(anchor="w")
        else:
            s = data.landing_summary(landing)
            if s["stars"]:
                lbl(box, "THREE STARS", 8, True, C.GOLD, C.CARD_DEEP).pack(anchor="w")
                for line in s["stars"]:
                    lbl(box, line, 8, bg=C.CARD_DEEP).pack(anchor="w", padx=px(6))
            lbl(box, "SCORING", 8, True, C.SILVER, C.CARD_DEEP).pack(anchor="w", pady=(px(6), 0))
            for line in s["goals"] or ["No goals"]:
                tk.Label(box, text=line, fg=C.TEXT, bg=C.CARD_DEEP, font=("Consolas", 8)).pack(anchor="w", padx=px(6))
            pens = data.penalty_lines(landing, limit=40)
            if pens:
                lbl(box, "PENALTIES", 8, True, C.SILVER, C.CARD_DEEP).pack(anchor="w", pady=(px(6), 0))
                for line in pens:
                    tk.Label(box, text=line, fg=C.MUTED, bg=C.CARD_DEEP, font=("Consolas", 8)).pack(anchor="w", padx=px(6))
        row_btns = tk.Frame(box, bg=C.CARD_DEEP)
        row_btns.pack(fill="x", pady=(px(6), 0))
        btn(row_btns, "\U0001F3AF View Shot Chart",
            lambda: (setattr(self, "selected_shot_game_id", gid), self.switch_tab("shots")),
            bg="#1a3152", size=8).pack(side="left")
        if g.get("gameCenterLink"):
            btn(row_btns, "Highlights & GameCenter \u2197", lambda: self._open_gamecenter(g), size=8).pack(side="right")

    def _reveal(self, gid: int) -> None:
        self.revealed.add(gid)
        self._bump_ui()

    # ---- shots & heatmaps
    def _render_shots(self, p: tk.Frame) -> None:
        past = list(reversed(data.split_schedule(self.schedule)[0]))
        if not past:
            c = card(p)
            lbl(c, "NO COMPLETED GAMES RECORDED YET", 10, True, C.SILVER).pack(anchor="w")
            lbl(c, "Shot charts and rink heatmaps will automatically populate once games are played.",
                8, fg=C.MUTED).pack(anchor="w", pady=(px(4), 0))
            return

        # Ensure all past shot charts are being fetched in background
        self._fetch_all_past_shot_charts()

        # Selector Card
        sel_card = card(p, pady=px(4))
        sel_hdr = tk.Frame(sel_card, bg=C.CARD)
        sel_hdr.pack(fill="x", pady=(0, px(4)))
        lbl(sel_hdr, "\U0001F3AF SHOT CLOCK & RINK VISUALIZER", 10, True, C.ACCENT).pack(side="left")

        # Build dropdown options
        options = ["\u2605 All Games Combined (Season Heatmap)"]
        game_map: Dict[str, Any] = {"\u2605 All Games Combined (Season Heatmap)": "combined"}
        id_to_opt: Dict[Any, str] = {"combined": "\u2605 All Games Combined (Season Heatmap)"}

        for g in past:
            gid = int(g.get("id") or 0)
            res, ours, theirs = data.result_of(g, C.TEAM)
            date_str = g.get("gameDate", "")
            away = (g.get("awayTeam") or {}).get("abbrev", "")
            home = (g.get("homeTeam") or {}).get("abbrev", "")
            label = f"{date_str} \u00b7 {away} @ {home} ({res} {ours}-{theirs})"
            options.append(label)
            game_map[label] = gid
            id_to_opt[gid] = label

        # Controls row
        ctrl_row = tk.Frame(sel_card, bg=C.CARD)
        ctrl_row.pack(fill="x", pady=(px(2), px(4)))

        lbl(ctrl_row, "Select Game:", 8, True, C.SILVER).pack(side="left", padx=(0, px(6)))

        current_opt = id_to_opt.get(self.selected_shot_game_id, options[0])
        var_choice = tk.StringVar(value=current_opt)

        def _on_select(val: str) -> None:
            chosen_gid = game_map.get(val, "combined")
            if chosen_gid != self.selected_shot_game_id:
                self.selected_shot_game_id = chosen_gid
                self._bump_ui()

        # Combobox
        cb = ttk.Combobox(ctrl_row, values=options, textvariable=var_choice, state="readonly", width=38)
        cb.pack(side="left", padx=(0, px(8)))
        cb.bind("<<ComboboxSelected>>", lambda e: _on_select(var_choice.get()))

        # Quick Navigation Buttons: [Combined] [◀ Newer] [Older ▶]
        def _step_game(delta: int) -> None:
            try:
                curr_idx = options.index(var_choice.get())
                new_idx = max(0, min(len(options) - 1, curr_idx + delta))
                var_choice.set(options[new_idx])
                _on_select(options[new_idx])
            except ValueError:
                pass

        btn(ctrl_row, "\u2605 Combined", lambda: _on_select(options[0]), bg=C.GOLD, fg=C.NAVY, size=7).pack(side="left", padx=px(2))
        btn(ctrl_row, "\u25C0 Newer", lambda: _step_game(-1), bg="#1a3152", size=7, bold=False).pack(side="left", padx=px(2))
        btn(ctrl_row, "Older \u25B6", lambda: _step_game(1), bg="#1a3152", size=7, bold=False).pack(side="left", padx=px(2))

        # Selected data resolution
        if self.selected_shot_game_id == "combined":
            charts = [self.shot_data.get(int(g.get("id", 0))) for g in past if int(g.get("id", 0)) in self.shot_data]
            chart_payload = data.combine_shot_charts(charts, target_abbrev=C.TEAM)
        else:
            try:
                gid = int(self.selected_shot_game_id)
            except (ValueError, TypeError):
                gid = int(past[0].get("id", 0))
            if gid in self.shot_data:
                chart_payload = self.shot_data[gid]
            else:
                self._fetch_shot_chart(gid)
                chart_payload = {"shots": [], "counts": {}, "opponent": "...", "game_id": gid}

        # Summary Metric Banner Card
        sum_card = card(p, pady=px(4))
        counts = chart_payload.get("counts", {})
        target_sog = counts.get("target_sog", 0)
        target_goals = counts.get("target_goals", 0)
        opp_sog = counts.get("opp_sog", 0)
        opp_goals = counts.get("opp_goals", 0)
        total_shots = counts.get("total_shots", 0)

        if self.selected_shot_game_id == "combined":
            cnt = chart_payload.get("games_count", 0)
            lbl(sum_card, f"SEASON TOTALS COMBINED \u00b7 {cnt} of {len(past)} Games Analyzed", 8, True, C.SILVER).pack(anchor="w")
            s_row = tk.Frame(sum_card, bg=C.CARD)
            s_row.pack(fill="x", pady=px(2))
            lbl(s_row, f"{target_goals} \u2013 {opp_goals}", 18, True, C.ACCENT).pack(side="left")
            lbl(s_row, f"  {C.TEAM} Goals \u2013 Opp Goals", 8, fg=C.MUTED).pack(side="left", anchor="s", pady=(0, px(4)))

            stats_grid = tk.Frame(s_row, bg=C.CARD)
            stats_grid.pack(side="right")
            lbl(stats_grid, str(target_sog), 12, True, C.TEXT).grid(row=0, column=0, padx=px(8))
            lbl(stats_grid, f"{C.TEAM} SOG", 7, fg=C.MUTED).grid(row=1, column=0, padx=px(8))

            t_pct = counts.get("target_sh_pct", 0.0)
            lbl(stats_grid, f"{t_pct}%", 12, True, C.GREEN if t_pct >= 10.0 else C.TEXT).grid(row=0, column=1, padx=px(8))
            lbl(stats_grid, "SH%", 7, fg=C.MUTED).grid(row=1, column=1, padx=px(8))

            lbl(stats_grid, str(opp_sog), 12, True, C.TEXT).grid(row=0, column=2, padx=px(8))
            lbl(stats_grid, "Opp SOG", 7, fg=C.MUTED).grid(row=1, column=2, padx=px(8))

            lbl(stats_grid, str(total_shots), 12, True, C.GOLD).grid(row=0, column=3, padx=px(8))
            lbl(stats_grid, "Total Tracked", 7, fg=C.MUTED).grid(row=1, column=3, padx=px(8))
        else:
            # Single game
            m_text = chart_payload.get("matchup") or "Game Details"
            d_text = chart_payload.get("game_date") or ""
            v_text = chart_payload.get("venue") or ""
            lbl(sum_card, f"{m_text.upper()} \u00b7 {d_text}", 8, True, C.SILVER).pack(anchor="w")
            s_row = tk.Frame(sum_card, bg=C.CARD)
            s_row.pack(fill="x", pady=px(2))

            t_sc = chart_payload.get("target_score", target_goals)
            o_sc = chart_payload.get("opp_score", opp_goals)
            res_str = "W" if t_sc > o_sc else ("L" if t_sc < o_sc else "T")
            color_res = C.GREEN if res_str == "W" else C.RED
            lbl(s_row, f"{C.TEAM} {t_sc} \u2013 {o_sc} {chart_payload.get('opponent', 'OPP')}", 18, True, C.ACCENT).pack(side="left")
            lbl(s_row, f"  Final ({res_str})", 8, fg=color_res).pack(side="left", anchor="s", pady=(0, px(4)))

            stats_grid = tk.Frame(s_row, bg=C.CARD)
            stats_grid.pack(side="right")
            lbl(stats_grid, str(target_sog), 12, True, C.TEXT).grid(row=0, column=0, padx=px(10))
            lbl(stats_grid, f"{C.TEAM} SOG", 7, fg=C.MUTED).grid(row=1, column=0, padx=px(10))
            lbl(stats_grid, str(opp_sog), 12, True, C.TEXT).grid(row=0, column=1, padx=px(10))
            lbl(stats_grid, "Opp SOG", 7, fg=C.MUTED).grid(row=1, column=1, padx=px(10))
            lbl(stats_grid, str(total_shots), 12, True, C.GOLD).grid(row=0, column=2, padx=px(10))
            lbl(stats_grid, "Total Shots", 7, fg=C.MUTED).grid(row=1, column=2, padx=px(10))

            if v_text:
                lbl(sum_card, f"\U0001F4CD {v_text}", 8, fg=C.MUTED).pack(anchor="w", pady=(px(2), 0))

        # Regulation Rink & Interactive Shot Chart
        rink_frame = tk.Frame(p, bg=C.CARD)
        rink_frame.pack(fill="x", pady=(0, px(8)))
        chart_widget = rink.ShotChart(rink_frame, bg=C.CARD)
        chart_widget.pack(fill="x", expand=True)
        chart_widget.load_shots(chart_payload)
        self._render_live()

    def _toggle_game(self, gid: int) -> None:
        self.expanded = None if self.expanded == gid else gid
        if self.expanded and gid not in self.landing:
            self._fetch_landing(gid)
        self._bump_ui()

    def _toggle_show_all(self) -> None:
        self.show_all_games = not self.show_all_games
        self._bump_ui()

    # ---- standings
    def _render_standings(self, p: tk.Frame) -> None:
        if self.spoiler_gate():
            self._spoiler_card(p, "The standings")
            return
        st = data.standings_tables(self.standings, C.TEAM_DIVISION, C.TEAM_CONFERENCE)
        if not st["division"]:
            lbl(p, "Loading standings\u2026" if not self.standings else "Standings are not available yet.",
                fg=C.MUTED, bg=C.BG).pack(anchor="w")
            return
        headers = ["#", "TEAM", "GP", "W", "L", "OT", "PTS", "P%", "DIFF", "L10", "STRK"]
        widths = [3, 6, 4, 4, 4, 4, 5, 6, 5, 7, 5]

        def rows_of(lst):
            rows = [[i + 1] + data.standings_row(r) for i, r in enumerate(lst)]
            hl = next((i for i, r in enumerate(lst) if data.name_of(r.get("teamAbbrev")) == C.TEAM), None)
            return rows, hl

        section(p, "METROPOLITAN DIVISION")
        rows, hl = rows_of(st["division"])
        table(card(p), headers, rows, widths, accent_col=6, highlight=hl, divider_after=3)
        section(p, "EASTERN CONFERENCE \u00b7 DIVISION LEADERS")
        rows, hl = rows_of(st["leaders"])
        table(card(p), headers, rows, widths, accent_col=6, highlight=hl, divider_after=3)
        section(p, "EASTERN CONFERENCE \u00b7 WILD CARD")
        rows, hl = rows_of(st["wildcard"])
        table(card(p), headers, rows, widths, accent_col=6, highlight=hl, divider_after=2)
        lbl(p, "Red line = playoff cut-off. Top 3 in each division plus two wild cards make the playoffs. "
               "Standings via NHL.com, refreshed every 5 minutes.", 8, fg=C.MUTED, bg=C.BG,
            wraplength=540, justify="left").pack(anchor="w", pady=(px(6), 0))

    # ---- news
    def _render_news(self, p: tk.Frame) -> None:
        top = tk.Frame(p, bg=C.BG)
        top.pack(fill="x")
        lbl(top, "LATEST BLUE JACKETS NEWS", 10, True, bg=C.BG).pack(side="left")
        btn(top, "Official team news \u2197", lambda: net.open_in_browser(C.OFFICIAL_NEWS_URL), size=8).pack(side="right")
        filters = tk.Frame(p, bg=C.BG)
        filters.pack(fill="x", pady=(px(6), px(4)))
        filter_specs = [
            ("all", "All"),
            ("nhl", "NHL.com"),
            ("espn", "ESPN"),
            ("cannon", "The Cannon"),
            ("1ob", "1st Ohio Battery"),
            ("reddit", "Reddit"),
            ("youtube", "\u25B6 YouTube"),
        ]
        for key, text in filter_specs:
            on = self.news_filter == key
            b = btn(filters, text, lambda k=key: self._set_news_filter(k),
                    bg=("#b71c1c" if key == "youtube" else C.RED) if on else C.CARD,
                    fg=C.TEXT if on else C.MUTED, size=8, bold=on)
            b.configure(padx=px(6), pady=px(2))
            b.pack(side="left", padx=(0, px(4)))

        def matches(item: dict) -> bool:
            if self.news_filter == "all":
                return True
            src = item.get("source", "").lower()
            if self.news_filter == "youtube":
                return "youtube" in src or "youtube.com" in item.get("link", "")
            if self.news_filter == "nhl":
                return "nhl.com" in src
            if self.news_filter == "espn":
                return "espn" in src
            if self.news_filter == "cannon":
                return "cannon" in src
            if self.news_filter == "1ob":
                return "1st ohio battery" in src or "1ob" in src
            if self.news_filter == "reddit":
                return "reddit" in src or "r/bluejackets" in src
            return self.news_filter.lower() in src

        items = [i for i in self.news if matches(i)]
        if self.spoiler_gate():
            self._spoiler_card(p, "Headlines")
            return
        if not self.news:
            lbl(p, "Loading headlines\u2026", fg=C.MUTED, bg=C.BG).pack(anchor="w")
            return
        if not items:
            lbl(p, "Nothing from this source right now.", fg=C.MUTED, bg=C.BG).pack(anchor="w")
        for item in items[:80]:
            c = card(p)
            meta = " \u00b7 ".join(x for x in (item["source"], data.ago(item["ts"])) if x)
            lbl(c, meta, 8, fg=C.ACCENT).pack(anchor="w")
            safe = net.is_safe_browser_url(item["link"])
            title = lbl(c, item["title"], 10, True, wraplength=520, justify="left", cursor="hand2" if safe else "")
            title.pack(anchor="w", pady=(px(1), px(3)))
            if item["desc"]:
                lbl(c, item["desc"], 8, fg=C.SILVER, wraplength=520, justify="left").pack(anchor="w")
            if safe:
                link = item["link"]
                title.bind("<Button-1>", lambda e, u=link: net.open_in_browser(u))
                is_video = "youtube.com" in link or "youtu.be" in link or "youtube" in item.get("source", "").lower()
                btn_text = "\u25B6 Watch on YouTube \u2197" if is_video else "Read \u2197"
                btn_bg = "#b71c1c" if is_video else C.HILITE
                btn(c, btn_text, lambda u=link: net.open_in_browser(u), size=8, bg=btn_bg).pack(anchor="e", pady=(px(4), 0))
        lbl(p, "Headlines link to their original publishers and open in your browser.", 8, fg=C.MUTED,
            bg=C.BG).pack(anchor="w", pady=(px(6), 0))

    def _set_news_filter(self, key: str) -> None:
        self.news_filter = key
        self._bump_ui()

    # ---- roster
    def _render_roster(self, p: tk.Frame) -> None:
        box = self.boxscore or {}
        is_home = data.perspective(self.game, C.TEAM)[0] if self.game else True
        live = (box.get("playerByGameStats") or {}).get("homeTeam" if is_home else "awayTeam") or {}
        if self.game and self.game.get("gameState") in data.LIVE_STATES + data.FINAL_STATES \
                and (live.get("forwards") or live.get("defense")) and not self.spoiler_hidden(self.game):
            lbl(p, "TONIGHT'S LINEUP \u00b7 IN-GAME STATS", 10, True, bg=C.BG).pack(anchor="w")
            for key, title in (("forwards", "FORWARDS"), ("defense", "DEFENSE")):
                players = live.get(key) or []
                rows = [[pl.get("sweaterNumber", ""), data.name_of(pl.get("name")), pl.get("position", ""),
                         pl.get("toi", ""), pl.get("shifts", 0), pl.get("goals", 0), pl.get("assists", 0),
                         pl.get("sog", 0), f"{pl.get('plusMinus', 0):+d}"] for pl in players]
                if rows:
                    section(p, title)
                    table(card(p), ["#", "PLAYER", "POS", "TOI", "SH", "G", "A", "SOG", "+/-"],
                          rows, [3, 18, 4, 6, 4, 3, 3, 4, 4], accent_col=3,
                          on_click=lambda i, pl=players: self.open_player(pl[i].get("playerId")))
            goalies = live.get("goalies") or []
            if goalies:
                section(p, "GOALIES")
                rows = []
                for gk in goalies:
                    pct = gk.get("savePctg")
                    rows.append([gk.get("sweaterNumber", ""), data.name_of(gk.get("name")), gk.get("toi", ""),
                                 f"{gk.get('saves', 0)}/{gk.get('shotsAgainst', 0)}",
                                 f"{pct:.3f}" if isinstance(pct, (int, float)) else "-"])
                table(card(p), ["#", "GOALIE", "TOI", "SAVES", "SV%"], rows, [3, 22, 7, 8, 7],
                      on_click=lambda i: self.open_player(goalies[i].get("playerId")))
            return

        lbl(p, "CURRENT ROSTER  (click a name for a player card)", 10, True, bg=C.BG).pack(anchor="w")
        if not self.roster:
            lbl(p, "Loading roster\u2026", fg=C.MUTED, bg=C.BG).pack(anchor="w")
            return
        season = {s.get("playerId"): s for s in (self.stats.get("skaters") or []) + (self.stats.get("goalies") or [])}
        for group, players in self.roster.items():
            if not players:
                continue
            section(p, group.upper())
            rows = []
            for pl in players:
                st = season.get(pl["id"]) or {}
                line = (f"{st.get('wins', 0)}-{st.get('losses', 0)}-{st.get('overtimeLosses', 0)}" if group == "Goalies"
                        else f"{st.get('goals', 0)}-{st.get('assists', 0)}-{st.get('points', 0)}") if st else "\u2013"
                rows.append([pl["num"], pl["name"], pl["pos"], pl["hand"], line, pl["from"][:22]])
            hdr = "W-L-OT" if group == "Goalies" else "G-A-P"
            table(card(p), ["#", "PLAYER", "POS", "S/C", hdr, "FROM"], rows, [3, 20, 4, 4, 8, 20],
                  on_click=lambda i, pls=players: self.open_player(pls[i]["id"]))

    # ---- player cards
    def open_player(self, player_id: Any) -> None:
        if type(player_id) is not int or not 0 < player_id < 100_000_000:
            return
        existing = self.player_windows.get(player_id)
        if existing is not None and existing.winfo_exists():
            existing.deiconify()
            existing.lift()
            return
        top = tk.Toplevel(self.root, bg=C.BG)
        top.title("Player card")
        top.geometry(f"{px(480)}x{px(640)}")
        area = ScrollArea(top, self.scroll_canvases)
        area.pack(fill="both", expand=True)
        area.render(lambda p: lbl(p, "Loading player\u2026", fg=C.MUTED, bg=C.BG).pack(anchor="w", pady=px(20)))
        top.area = area  # type: ignore[attr-defined]
        self.player_windows[player_id] = top
        threading.Thread(target=self._fetch_player, args=(player_id,), daemon=True).start()

    def _fetch_player(self, pid: int) -> None:
        try:
            info = data.player_card(net.fetch_json(C.URL_PLAYER.format(player_id=pid)))
        except Exception as exc:
            log.warning("Player fetch failed: %s", exc)
            self.post(lambda: self._show_player(pid, None, None))
            return
        img = None
        if isinstance(info.get("headshot"), str) and info["headshot"]:
            try:
                img = assets.load_safe_image(net.fetch_bytes(info["headshot"], C.MAX_IMAGE_BYTES), px(120))
            except Exception as exc:
                log.info("Headshot unavailable: %s", exc)
        self.post(lambda: self._show_player(pid, info, img))

    def _show_player(self, pid: int, info: Optional[dict], img) -> None:
        top = self.player_windows.get(pid)
        if top is None or not top.winfo_exists():
            return
        if info is None:
            top.area.render(lambda p: lbl(p, "Couldn't load this player. Try again later.", fg=C.MUTED,
                                          bg=C.BG).pack(anchor="w", pady=px(20)))
            return
        top.title(f"{info['name']} \u00b7 Player card")
        top.photo = ImageTk.PhotoImage(img) if img is not None else None  # keep a reference

        def build(p: tk.Frame) -> None:
            head = tk.Frame(p, bg=C.NAVY, padx=px(10), pady=px(10))
            head.pack(fill="x")
            if top.photo is not None:
                tk.Label(head, image=top.photo, bg=C.NAVY).pack(side="left", padx=(0, px(12)))
            txt = tk.Frame(head, bg=C.NAVY)
            txt.pack(side="left", fill="x")
            lbl(txt, info["name"], 15, True, bg=C.NAVY).pack(anchor="w")
            lbl(txt, " \u00b7 ".join(x for x in (f"#{info['num']}" if info["num"] else "", info["pos"],
                                               f"Shoots/Catches {info['hand']}" if info["hand"] else "") if x),
                9, fg=C.SILVER, bg=C.NAVY).pack(anchor="w")
            bio = card(p)
            for k, v in (("Age", info["age"]), ("Size", " \u00b7 ".join(x for x in (info["height"], info["weight"]) if x)),
                         ("Born", info["from"]), ("Draft", info["draft"])):
                if v:
                    row = tk.Frame(bio, bg=C.CARD)
                    row.pack(fill="x")
                    lbl(row, k, 8, True, C.MUTED, width=8, anchor="w").pack(side="left")
                    lbl(row, v, 9).pack(side="left")
            goalie = info["pos"] == "G"
            if goalie:
                hdr, keys = ["GP", "W", "L", "OTL", "GAA", "SV%"], ["gamesPlayed", "wins", "losses", "otLosses",
                                                                  "goalsAgainstAvg", "savePctg"]
            else:
                hdr, keys = ["GP", "G", "A", "PTS", "+/-", "PIM"], ["gamesPlayed", "goals", "assists", "points",
                                                                  "plusMinus", "pim"]

            def stat_row(src):
                return [fmt(src.get(k), 3 if k == "savePctg" else 2 if k == "goalsAgainstAvg" else 0) for k in keys]

            if info["season"]:
                section(p, f"THIS SEASON {info['season_label']}".strip())
                table(card(p), ["-"] + hdr, [["NHL"] + stat_row(info["season"])], [5] + [6] * len(hdr))
            if info["career"]:
                section(p, "CAREER (REGULAR SEASON)")
                table(card(p), ["-"] + hdr, [["NHL"] + stat_row(info["career"])], [5] + [6] * len(hdr))
            if info["last5"]:
                section(p, "LAST 5 GAMES")
                if goalie:
                    rows = [[g.get("gameDate", ""), g.get("opponentAbbrev", ""), g.get("decision", "-"),
                             g.get("shotsAgainst", "-"), g.get("goalsAgainst", "-"), fmt(g.get("savePctg"), 3)]
                            for g in info["last5"]]
                    table(card(p), ["DATE", "OPP", "DEC", "SA", "GA", "SV%"], rows, [11, 6, 5, 5, 5, 7])
                else:
                    rows = [[g.get("gameDate", ""), g.get("opponentAbbrev", ""), g.get("goals", 0), g.get("assists", 0),
                             g.get("points", 0), g.get("toi", "")] for g in info["last5"]]
                    table(card(p), ["DATE", "OPP", "G", "A", "PTS", "TOI"], rows, [11, 6, 4, 4, 5, 7])
            btn(p, "Full profile on NHL.com \u2197", lambda: net.open_in_browser(f"{C.NHL_WEB}/player/{pid}"),
                size=8).pack(anchor="e", pady=px(8))
            lbl(p, "Stats and headshot loaded live from NHL.com.", 8, fg=C.MUTED, bg=C.BG).pack(anchor="w")

        top.area.render(build)

    # ---- settings
    def _render_settings(self, p: tk.Frame) -> None:
        self.setting_vars = {}
        lbl(p, "SETTINGS", 10, True, bg=C.BG).pack(anchor="w")
        groups = (
            ("Alerts", (("sound", "Play the goal horn when the Blue Jackets score"),
                        ("opponent_sound", "Play a soft chime when the opponent scores"),
                        ("toasts", "Windows notifications (goals, period ends, final)"),
                        ("puck_drop_reminder", "Remind me 30 minutes before puck drop"))),
            ("Window", (("auto_popup", "Pop up the window when a game goes live"),
                        ("popup_on_goal", "Bring the window to front on a CBJ goal"),
                        ("ticker_bar", "Show compact floating ticker ribbon (dock on second monitor)"),
                        ("mini_overlay", "Show the mini always-on-top scoreboard during games"),
                        ("tray_live_score", "Show live score in tray icon during games (default: keep CBJ logo)"),
                        ("start_with_windows", "Start minimized to tray when Windows starts"))),
            ("Spoilers", (("spoiler_mode", "Spoiler mode: hide results until I reveal them (also in the header and tray)"),)),
        )
        for title, opts in groups:
            c = card(p)
            lbl(c, title, 9, True, C.ACCENT).pack(anchor="w")
            for key, text in opts:
                var = tk.BooleanVar(value=self.settings[key])
                self.setting_vars[key] = var
                tk.Checkbutton(c, text=text, variable=var, command=lambda k=key, v=var: self._toggle(k, v.get()),
                               font=(C.FONT, 9), fg=C.TEXT, bg=C.CARD, selectcolor=C.NAVY,
                               activebackground=C.CARD, activeforeground=C.TEXT, anchor="w").pack(fill="x")
            if title == "Spoilers":
                lbl(c, "For watching a replay later. Hides final scores, W/L results, records, standings, headlines, "
                       "the final-score notification and tray tooltip until you press Reveal. Live games are not "
                       "hidden \u2014 use Stream delay for that.", 8, fg=C.MUTED, wraplength=520,
                    justify="left").pack(anchor="w", pady=(px(2), 0))

        c = card(p)
        lbl(c, "Stream delay", 9, True, C.ACCENT).pack(anchor="w")
        lbl(c, "Watching on a stream that runs behind? Hold back scores, horn and alerts so nothing is spoiled "
               "before you see it.", 8, wraplength=520, justify="left").pack(anchor="w")
        dvar = tk.IntVar(value=self.settings["delay_seconds"])
        self.setting_vars["delay_seconds"] = dvar
        tk.Scale(c, from_=0, to=180, resolution=5, orient="horizontal", variable=dvar, command=self._on_delay,
                 length=px(320), bg=C.CARD, fg=C.TEXT, troughcolor=C.CARD_DEEP, highlightthickness=0,
                 activebackground=C.RED, label="seconds", font=(C.FONT, 8)).pack(anchor="w")

        c = card(p)
        lbl(c, "Where to watch", 9, True, C.ACCENT).pack(anchor="w")
        labels = {k: v[0] for k, v in C.WATCH_OPTIONS.items()}
        wvar = tk.StringVar(value=labels[self.settings["watch"]])
        self.setting_vars["watch"] = wvar
        om = tk.OptionMenu(c, wvar, *labels.values(), command=self._set_watch)
        om.configure(bg=C.NAVY, fg=C.TEXT, activebackground=C.RED, activeforeground=C.TEXT, relief="flat",
                     highlightthickness=0, font=(C.FONT, 9))
        om["menu"].configure(bg=C.CARD, fg=C.TEXT, activebackground=C.RED, font=(C.FONT, 9))
        om.pack(anchor="w", pady=(px(4), 0))
        lbl(c, "Prime Video carries the Blue Jackets Hockey Network for fans in the team's home region. "
               "Out-of-market fans usually watch on ESPN+.", 8, fg=C.MUTED, wraplength=520,
            justify="left").pack(anchor="w", pady=(px(4), 0))

        c = card(p)
        lbl(c, "Goal horn", 9, True, C.ACCENT).pack(anchor="w")
        current = "Your custom horn (custom_horn.wav)" if assets.has_custom_horn() else \
            "Built-in horn \u2014 an original synthesized horn-and-cannon tuned to sound like the arena"
        lbl(c, current, 8, wraplength=520, justify="left").pack(anchor="w")
        row = tk.Frame(c, bg=C.CARD)
        row.pack(anchor="w", pady=(px(4), 0))
        btn(row, "\U0001F50A Test horn", assets.play_horn, bg="#1a2d47", fg=C.GOLD, size=8).pack(side="left")
        btn(row, "Use my own horn\u2026", self._choose_horn, size=8).pack(side="left", padx=px(6))
        if assets.has_custom_horn():
            btn(row, "Reset to built-in", self._reset_horn, size=8, bold=False).pack(side="left")
        btn(row, "\U0001F514 Test chime", assets.play_chime, size=8, bold=False).pack(side="left", padx=px(6))
        lbl(c, f"Custom horns must be a PCM .wav up to {C.MAX_CUSTOM_WAV_SECONDS} seconds and "
               f"{C.MAX_CUSTOM_WAV_BYTES // (1024 * 1024)} MB. The file stays on your PC.",
            8, fg=C.MUTED, wraplength=520, justify="left").pack(anchor="w", pady=(px(4), 0))

        c = card(p)
        lbl(c, f"{C.APP_NAME} v{__version__}", 9, True).pack(anchor="w")
        if self.update_info:
            btn(c, f"\u2B06 Download {self.update_info['tag']}", self._open_update, bg=C.GOLD, fg=C.NAVY,
                size=8).pack(anchor="w", pady=px(4))
        row = tk.Frame(c, bg=C.CARD)
        row.pack(anchor="w", pady=(px(4), px(4)))
        btn(row, "Open app data folder", lambda: os.startfile(str(settings.data_dir())), size=8,
            bold=False).pack(side="left")
        if C.GITHUB_REPO:
            btn(row, "Project page \u2197", lambda: net.open_in_browser(C.REPO_URL), size=8,
                bold=False).pack(side="left", padx=px(6))
        lbl(c, "Unofficial fan project. Not affiliated with or endorsed by the Columbus Blue Jackets or the NHL. "
               "The Blue Jackets name and logo are trademarks of the club and are shown only to identify the team. "
               "Scores and stats from public NHL.com data; headlines from NHL.com, ESPN, The Cannon, "
               "1st Ohio Battery and r/BlueJackets.", 8, fg=C.MUTED, wraplength=520, justify="left").pack(anchor="w")

    def _on_delay(self, value: str) -> None:
        self.settings["delay_seconds"] = int(float(value))
        if self._save_job:
            self.root.after_cancel(self._save_job)
        self._save_job = self.root.after(600, self._save_delay)

    def _save_delay(self) -> None:
        self._save_job = None
        settings.save(self.settings)
        self._render_live()

    def _set_watch(self, label: str) -> None:
        key = next((k for k, v in C.WATCH_OPTIONS.items() if v[0] == label), None)
        if key:
            self.settings["watch"] = key
            settings.save(self.settings)
            self._sync_watch_button()
            try:
                self.icon.update_menu()
            except Exception:
                pass

    def _choose_horn(self) -> None:
        path = filedialog.askopenfilename(parent=self.root, title="Choose a goal horn (.wav)",
                                          filetypes=[("WAV audio", "*.wav")])
        if not path:
            return
        err = assets.install_custom_horn(path)
        if err:
            messagebox.showerror(C.APP_NAME, err, parent=self.root)
            return
        self._bump("_settings")
        self._render_active(force=False)
        if messagebox.askyesno(C.APP_NAME, "Custom horn installed. Play it now?", parent=self.root):
            assets.play_horn()

    def _reset_horn(self) -> None:
        if messagebox.askyesno(C.APP_NAME, "Remove your custom horn and go back to the built-in one?",
                               parent=self.root):
            assets.remove_custom_horn()
            self._bump("_settings")
            self._render_active(force=False)


# ---------------------------------------------------------------- entry point
_mutex = None


def _already_running() -> bool:
    global _mutex
    if sys.platform != "win32":
        return False
    _mutex = ctypes.windll.kernel32.CreateMutexW(None, False, f"Local\\{C.APP_ID}")
    return ctypes.windll.kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS


def _enable_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)   # system DPI aware: crisp text
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main(argv: Optional[List[str]] = None) -> None:
    global SCALE
    argv = sys.argv[1:] if argv is None else argv
    settings.setup_logging()
    minimized = "--minimized" in argv or "--tray" in argv
    if _already_running():
        if not minimized:
            r = tk.Tk()
            r.withdraw()
            messagebox.showinfo(C.APP_NAME, "CBJ Gameday Sentinel is already running \u2014 look for the icon in your system tray.")
            r.destroy()
        return
    _enable_dpi_awareness()
    try:
        root = tk.Tk()
        root.configure(bg=C.BG)
        if minimized:
            root.withdraw()
        SCALE = max(1.0, min(3.0, root.winfo_fpixels("1i") / 96.0))
        SentinelApp(root)
        root.mainloop()
    except Exception:
        log.exception("Fatal error")
        raise
