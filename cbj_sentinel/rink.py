"""Interactive NHL regulation ice rink & shot chart visualizer.

Parses play-by-play shot coordinates (x, y) from the official NHL API,
normalizes them into an offensive half-rink perspective, and renders
an interactive vector rink on a Tkinter Canvas with interactive tooltips
and period/team filters.
"""
from __future__ import annotations

import math
import tkinter as tk
from typing import Any, Callable, Dict, List, Optional

from . import config as C


class ShotChart(tk.Frame):
    """Interactive offensive-zone ice rink with plotted shots and goals."""

    def __init__(self, master, bg: str = C.CARD, **kw):
        super().__init__(master, bg=bg, **kw)
        self.bg = bg
        self.shots: List[Dict[str, Any]] = []
        self.team_id = C.NHL_TEAM_ID
        self.team_abbrev = C.TEAM
        self.filter_team = "cbj"     # "cbj", "all", "opp", "goals"
        self.filter_period = 0       # 0 = all, 1, 2, 3, 4 (OT)
        self.hovered_shot: Optional[Dict[str, Any]] = None
        self._marker_items: Dict[int, Dict[str, Any]] = {}

        self._build_ui()

    def _build_ui(self) -> None:
        # Header / filter controls
        hdr = tk.Frame(self, bg=self.bg)
        hdr.pack(fill="x", padx=8, pady=(8, 4))

        tk.Label(hdr, text="\U0001F3D2 SHOT CHART", font=(C.FONT, 9, "bold"),
                 fg=C.ACCENT, bg=self.bg).pack(side="left")

        self.l_counts = tk.Label(hdr, text="", font=(C.FONT, 8),
                                 fg=C.SILVER, bg=self.bg)
        self.l_counts.pack(side="left", padx=(10, 0))

        # Filter buttons container
        btn_box = tk.Frame(hdr, bg=self.bg)
        btn_box.pack(side="right")

        self.team_btns: Dict[str, tk.Button] = {}
        for key, label in (("cbj", f"{self.team_abbrev} Only"),
                           ("goals", "\u2605 Goals"),
                           ("all", "Both Teams")):
            b = tk.Button(btn_box, text=label, font=(C.FONT, 7, "bold"),
                          command=lambda k=key: self._set_team_filter(k),
                          bd=0, padx=6, pady=2, cursor="hand2")
            b.pack(side="left", padx=2)
            self.team_btns[key] = b

        self.period_btns: Dict[int, tk.Button] = {}
        for p, label in ((0, "All"), (1, "P1"), (2, "P2"), (3, "P3")):
            b = tk.Button(btn_box, text=label, font=(C.FONT, 7),
                          command=lambda pr=p: self._set_period_filter(pr),
                          bd=0, padx=4, pady=2, cursor="hand2")
            b.pack(side="left", padx=1)
            self.period_btns[p] = b

        # Rink Canvas
        self.canvas_w = 540
        self.canvas_h = 240
        self.canvas = tk.Canvas(self, width=self.canvas_w, height=self.canvas_h,
                                bg="#081422", highlightthickness=1,
                                highlightbackground="#1b2f4a", bd=0)
        self.canvas.pack(fill="x", expand=True, padx=8, pady=4)
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.canvas.bind("<Leave>", self._on_mouse_leave)
        self.canvas.bind("<Configure>", self._on_resize)

        # Bottom HUD / Info bar
        self.hud = tk.Label(self, text="Hover over any shot marker on the ice to inspect shooter details.",
                            font=(C.FONT, 8), fg=C.MUTED, bg=self.bg, anchor="w")
        self.hud.pack(fill="x", padx=10, pady=(2, 6))

        self._sync_filter_styles()
        self._draw_rink()

    def _sync_filter_styles(self) -> None:
        for k, b in self.team_btns.items():
            on = self.filter_team == k
            b.configure(bg=C.RED if on else "#132338", fg=C.TEXT if on else C.MUTED)
        for p, b in self.period_btns.items():
            on = self.filter_period == p
            b.configure(bg=C.HILITE if on else "#132338", fg=C.TEXT if on else C.MUTED)

    def _set_team_filter(self, key: str) -> None:
        if self.filter_team != key:
            self.filter_team = key
            self._sync_filter_styles()
            self._render_shots()

    def _set_period_filter(self, p: int) -> None:
        if self.filter_period != p:
            self.filter_period = p
            self._sync_filter_styles()
            self._render_shots()

    def _on_resize(self, event) -> None:
        if event.width > 50 and event.height > 50:
            if abs(event.width - self.canvas_w) > 5 or abs(event.height - self.canvas_h) > 5:
                self.canvas_w = event.width
                self.canvas_h = event.height
                self._draw_rink()
                self._render_shots()

    def load_shots(self, shots_data: Dict[str, Any]) -> None:
        """Load parsed shot chart data and redraw the rink."""
        self.shots = shots_data.get("shots", [])
        counts = shots_data.get("counts", {})
        cbj_sog = counts.get("target_sog", 0)
        cbj_g = counts.get("target_goals", 0)
        opp_sog = counts.get("opp_sog", 0)
        opp_g = counts.get("opp_goals", 0)
        opp_name = shots_data.get("opponent", "OPP")
        self.l_counts.configure(text=f"{self.team_abbrev}: {cbj_sog} SOG ({cbj_g} G)  \u00b7  {opp_name}: {opp_sog} SOG ({opp_g} G)")
        self._render_shots()

    # ------------------------------------------------------------ rink vector graphics
    def _draw_rink(self) -> None:
        c = self.canvas
        c.delete("rink_line")
        w, h = self.canvas_w, self.canvas_h

        pad_x, pad_y = 16, 12
        rw = w - pad_x * 2
        rh = h - pad_y * 2

        # Coordinate mapper: norm_x (0..100) -> px_x, norm_y (-42.5..42.5) -> px_y
        def pt(nx: float, ny: float) -> tuple[float, float]:
            px = pad_x + (nx / 100.0) * rw
            py = pad_y + ((ny + 42.5) / 85.0) * rh
            return px, py

        # Ice surface background
        c.create_rectangle(pad_x, pad_y, pad_x + rw, pad_y + rh,
                           fill="#0a1829", outline="", tags="rink_line")

        # Outer boards with rounded right corners (behind the net)
        rad = rh * 0.28
        # Boards outline
        c.create_line(pad_x, pad_y, pad_x + rw - rad, pad_y, fill="#2c476b", width=2, tags="rink_line")
        c.create_line(pad_x, pad_y + rh, pad_x + rw - rad, pad_y + rh, fill="#2c476b", width=2, tags="rink_line")
        c.create_line(pad_x, pad_y, pad_x, pad_y + rh, fill="#c62828", width=3, tags="rink_line") # Center red line

        # Rounded corner arcs
        c.create_arc(pad_x + rw - rad * 2, pad_y, pad_x + rw, pad_y + rad * 2,
                     start=0, extent=90, style="arc", outline="#2c476b", width=2, tags="rink_line")
        c.create_arc(pad_x + rw - rad * 2, pad_y + rh - rad * 2, pad_x + rw, pad_y + rh,
                     start=270, extent=90, style="arc", outline="#2c476b", width=2, tags="rink_line")
        c.create_line(pad_x + rw, pad_y + rad, pad_x + rw, pad_y + rh - rad,
                      fill="#2c476b", width=2, tags="rink_line")

        # Blue line (x = 25 ft)
        bx, _ = pt(25, 0)
        c.create_line(bx, pad_y, bx, pad_y + rh, fill="#1565c0", width=3, tags="rink_line")

        # Faceoff dots in neutral zone (x = 20 ft)
        for y_dot in (-22.0, 22.0):
            dx, dy = pt(20, y_dot)
            c.create_oval(dx - 3, dy - 3, dx + 3, dy + 3, fill="#c62828", outline="", tags="rink_line")

        # Offensive zone faceoff circles (x = 69 ft, y = ±22 ft, r = 15 ft)
        r_circ_x = (15.0 / 100.0) * rw
        r_circ_y = (15.0 / 85.0) * rh
        for y_dot in (-22.0, 22.0):
            fx, fy = pt(69, y_dot)
            c.create_oval(fx - r_circ_x, fy - r_circ_y, fx + r_circ_x, fy + r_circ_y,
                          outline="#c62828", width=1, tags="rink_line")
            c.create_oval(fx - 3, fy - 3, fx + 3, fy + 3, fill="#c62828", outline="", tags="rink_line")
            # Hash marks
            c.create_line(fx - r_circ_x - 3, fy - 4, fx - r_circ_x + 3, fy - 4, fill="#c62828", width=1, tags="rink_line")
            c.create_line(fx + r_circ_x - 3, fy - 4, fx + r_circ_x + 3, fy - 4, fill="#c62828", width=1, tags="rink_line")
            c.create_line(fx - r_circ_x - 3, fy + 4, fx - r_circ_x + 3, fy + 4, fill="#c62828", width=1, tags="rink_line")
            c.create_line(fx + r_circ_x - 3, fy + 4, fx + r_circ_x + 3, fy + 4, fill="#c62828", width=1, tags="rink_line")

        # Goal line (x = 89 ft)
        gx, _ = pt(89, 0)
        c.create_line(gx, pad_y + 4, gx, pad_y + rh - 4, fill="#c62828", width=2, tags="rink_line")

        # Trapezoid lines behind the net (x=89 to 100)
        t1x, t1y = pt(89, -11)
        t2x, t2y = pt(100, -14)
        c.create_line(t1x, t1y, t2x, t2y, fill="#c62828", width=1, tags="rink_line")
        t3x, t3y = pt(89, 11)
        t4x, t4y = pt(100, 14)
        c.create_line(t3x, t3y, t4x, t4y, fill="#c62828", width=1, tags="rink_line")

        # Goal crease (semi-circle on goal line facing center ice)
        cr_w = (6.0 / 100.0) * rw
        cr_h = (4.0 / 85.0) * rh
        c.create_arc(gx - cr_w, pt(89, 0)[1] - cr_h, gx + cr_w, pt(89, 0)[1] + cr_h,
                     start=90, extent=180, fill="#1976d2", outline="#c62828", width=1, tags="rink_line")

        # Net outline (x = 89 to 92.5, y = -3 to 3)
        n1x, n1y = pt(89, -3)
        n2x, n2y = pt(92.5, 3)
        c.create_rectangle(n1x, n1y, n2x, n2y, fill="#b71c1c", outline="#ffffff", width=1, tags="rink_line")

    # ------------------------------------------------------------ shot plotting
    def _render_shots(self) -> None:
        c = self.canvas
        c.delete("shot_item")
        self._marker_items.clear()
        self.hovered_shot = None

        if not self.shots:
            c.create_text(self.canvas_w / 2, self.canvas_h / 2,
                          text="No shot coordinate data available for this game.",
                          font=(C.FONT, 9), fill=C.MUTED, tags="shot_item")
            return

        pad_x, pad_y = 16, 12
        rw = self.canvas_w - pad_x * 2
        rh = self.canvas_h - pad_y * 2

        def pt(nx: float, ny: float) -> tuple[float, float]:
            px = pad_x + (nx / 100.0) * rw
            py = pad_y + ((ny + 42.5) / 85.0) * rh
            return px, py

        for shot in self.shots:
            # Filters
            is_target = shot.get("is_cbj", False)
            stype = shot.get("type", "")

            if self.filter_team == "cbj" and not is_target:
                continue
            if self.filter_team == "opp" and is_target:
                continue
            if self.filter_team == "goals" and stype != "goal":
                continue
            if self.filter_period != 0 and shot.get("period") != self.filter_period:
                continue

            sx, sy = pt(shot.get("x", 50), shot.get("y", 0))

            if stype == "goal":
                # Glowing halo + bold gold star
                halo = c.create_oval(sx - 9, sy - 9, sx + 9, sy + 9,
                                     fill="#ff3d00", outline="#ffe082", width=1, tags="shot_item")
                star = c.create_text(sx, sy, text="\u2605", font=(C.FONT, 12, "bold"),
                                     fill="#ffd700", tags="shot_item")
                # Player name badge above
                p_name = shot.get("player", "").split()[-1]
                lbl = c.create_text(sx, sy - 12, text=p_name, font=(C.FONT, 7, "bold"),
                                    fill="#ffffff", tags="shot_item")
                for item in (halo, star, lbl):
                    self._marker_items[item] = shot
            elif stype == "shot-on-goal":
                color = "#00e5ff" if is_target else "#eceff1"
                outline = "#002654" if is_target else "#37474f"
                dot = c.create_oval(sx - 4.5, sy - 4.5, sx + 4.5, sy + 4.5,
                                    fill=color, outline=outline, width=1, tags="shot_item")
                self._marker_items[dot] = shot
            else: # missed / blocked
                color = "#78909c"
                dot = c.create_oval(sx - 3, sy - 3, sx + 3, sy + 3,
                                    fill="", outline=color, width=1, tags="shot_item")
                self._marker_items[dot] = shot

    # ------------------------------------------------------------ mouse inspection
    def _on_mouse_move(self, event) -> None:
        c = self.canvas
        items = c.find_overlapping(event.x - 7, event.y - 7, event.x + 7, event.y + 7)
        matched_shot = None
        for item in reversed(items):
            if item in self._marker_items:
                matched_shot = self._marker_items[item]
                break

        if matched_shot != self.hovered_shot:
            self.hovered_shot = matched_shot
            c.delete("highlight_ring")
            if matched_shot:
                pad_x, pad_y = 16, 12
                rw = self.canvas_w - pad_x * 2
                rh = self.canvas_h - pad_y * 2
                px = pad_x + (matched_shot.get("x", 50) / 100.0) * rw
                py = pad_y + ((matched_shot.get("y", 0) + 42.5) / 85.0) * rh

                c.create_oval(px - 10, py - 10, px + 10, py + 10,
                              outline="#ffeb3b", width=2, tags="highlight_ring")

                p_str = f"P{matched_shot.get('period', 1)} {matched_shot.get('time', '')}"
                dist = f"{matched_shot.get('dist', 0)} ft"
                st = matched_shot.get("shotType", "shot").capitalize()
                player = matched_shot.get("player", "Unknown")
                res = matched_shot.get("type", "").replace("-", " ").upper()
                team = self.team_abbrev if matched_shot.get("is_cbj") else "Opponent"

                danger = " \u00b7 High Danger Slot" if matched_shot.get("dist", 99) <= 22 and abs(matched_shot.get("y", 99)) <= 12 else ""
                self.hud.configure(text=f"[{res}] {player} ({team}) \u00b7 {st} from {dist} \u00b7 {p_str}{danger}",
                                   fg="#ffeb3b" if "GOAL" in res else C.TEXT)
            else:
                self.hud.configure(text="Hover over any shot marker on the ice to inspect shooter details.",
                                   fg=C.MUTED)

    def _on_mouse_leave(self, _event) -> None:
        self.canvas.delete("highlight_ring")
        self.hovered_shot = None
        self.hud.configure(text="Hover over any shot marker on the ice to inspect shooter details.",
                           fg=C.MUTED)
