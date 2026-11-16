import queue
import sqlite3
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from config import DATABASE_PATH, EXPORT_DIR
from tracker.calculations import calculate_portfolio
from tracker.database import connect
from tracker.exceptions import TrackerError
from tracker.exporter import export_history
from tracker.market.service import get_price
from tracker.portfolio import PortfolioManager
from tracker.repositories import (
    AssetRepository,
    HoldingRepository,
    PriceRepository,
    SnapshotRepository,
)
from ui.charts import (
    allocation_percentages,
    CHART_PERIODS,
    cost_basis_series,
    filter_series_by_period,
    format_gain_loss,
    sort_positions,
    value_series,
)
from ui.settings import load_settings, save_settings

BACKGROUND = "#111827"
SURFACE = "#1f2937"
SURFACE_ALT = "#273449"
TEXT = "#f3f4f6"
MUTED = "#9ca3af"
ACCENT = "#4ea1ff"
POSITIVE = "#42d392"
NEGATIVE = "#f87171"
WARNING = "#fbbf24"


def create_worker_repositories(database_path: Path):
    connection = connect(database_path)
    return (
        connection,
        HoldingRepository(connection),
        PriceRepository(connection),
    )


def allocation_legend_columns(holding_count: int) -> int:
    return 2 if holding_count >= 6 else 1


class PortfolioWidget(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.settings = load_settings()
        ctk.set_appearance_mode(self.settings["theme"])
        self.title("Portfolio Tracker")
        self.configure(fg_color=BACKGROUND)
        self.attributes("-topmost", self.settings["always_on_top"])
        self.connection = connect(DATABASE_PATH)
        self.holdings = HoldingRepository(self.connection)
        self.assets = AssetRepository(self.connection)
        self.prices = PriceRepository(self.connection)
        self.snapshots = SnapshotRepository(self.connection)
        self.manager = PortfolioManager(self.assets, self.holdings)
        self.positions = []
        self.totals = None
        self.price_errors = {}
        self.chart_mode = self.settings["default_chart"]
        self.chart_period = "Last 30 days"
        self.sort_by = "value"
        self._refresh_queue = queue.Queue()
        self._refresh_poll_id = None
        self.apply_settings()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.refresh()

    def _build_ui(self) -> None:
        for child in self.winfo_children():
            child.destroy()
        self._build_dashboard_ui()

    def _build_dashboard_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=28, pady=(22, 8), sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Portfolio Tracker", text_color=TEXT, font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        self.updated_label = ctk.CTkLabel(header, text="Not updated", text_color=MUTED, font=ctk.CTkFont(size=12))
        self.updated_label.grid(row=1, column=0, sticky="w")
        self.refresh_button = ctk.CTkButton(header, text="Refresh", width=100, fg_color=ACCENT, hover_color="#3182ce", command=self.refresh)
        self.refresh_button.grid(row=0, column=1, rowspan=2, padx=(8, 0))

        self.summary = ctk.CTkFrame(self, fg_color="transparent")
        self.summary.grid(row=1, column=0, padx=28, pady=8, sticky="ew")
        for column in range(3):
            self.summary.grid_columnconfigure(column, weight=1)
        self.total_label = self._summary_card(self.summary, 0, "TOTAL VALUE", "$0.00", 28)
        self.cost_label = self._summary_card(self.summary, 1, "COST", "$0.00", 20)
        self.gain_label = self._summary_card(self.summary, 2, "GAIN / LOSS", "$0.00  (0.00%)", 20)
        chart_frame = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=14)
        chart_frame.grid(row=2, column=0, padx=28, pady=8, sticky="ew")
        chart_frame.grid_columnconfigure(0, weight=3)
        chart_frame.grid_columnconfigure(1, weight=2)
        ctk.CTkLabel(chart_frame, text="PORTFOLIO VALUE", text_color=MUTED, font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, padx=16, pady=(14, 0), sticky="w")
        self.period_selector = ctk.CTkSegmentedButton(
            chart_frame,
            values=list(CHART_PERIODS),
            command=self._set_period,
            width=290,
        )
        self.period_selector.set(self.chart_period)
        self.period_selector.grid(row=1, column=0, padx=16, pady=(6, 0), sticky="w")
        ctk.CTkLabel(chart_frame, text="ALLOCATION", text_color=MUTED, font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=1, padx=16, pady=(14, 0), sticky="w")
        self.figure = Figure(figsize=(9, 2.6), dpi=90, facecolor=SURFACE)
        grid = self.figure.add_gridspec(1, 3, width_ratios=(3, 1.25, 2.4), wspace=0.2)
        self.value_axis = self.figure.add_subplot(grid[0, 0])
        self.allocation_axis = self.figure.add_subplot(grid[0, 1])
        self.allocation_legend_axis = self.figure.add_subplot(grid[0, 2])
        self.canvas = FigureCanvasTkAgg(self.figure, master=chart_frame)
        self.canvas.get_tk_widget().grid(row=2, column=0, columnspan=2, padx=8, pady=(0, 8), sticky="ew")
        self.chart_frame = chart_frame
        self._build_common_lower_ui(28, 5)

    def _build_common_lower_ui(self, padding: int, footer_columns: int) -> None:
        self.list_frame = ctk.CTkScrollableFrame(self, label_text="Holdings")
        self.list_frame.grid(row=3, column=0, padx=padding, pady=4, sticky="nsew")
        self.list_frame.grid_columnconfigure(0, weight=1)
        self.status_label = ctk.CTkLabel(self, text="", text_color=WARNING, wraplength=900, font=ctk.CTkFont(size=11))
        self.status_label.grid(row=4, column=0, padx=padding, pady=2, sticky="w")
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=5, column=0, padx=padding, pady=(2, 6), sticky="ew")
        for column in range(5):
            footer.grid_columnconfigure(column, weight=1)
        buttons = (
            (0, "Add", self._add_holding),
            (1, "Remove", self._remove_holding),
            (2, "Snapshot", self._save_snapshot),
            (3, "Export", self._export),
            (4, "Settings", self._open_settings),
        )
        for column, text, command in buttons:
            ctk.CTkButton(footer, text=text, height=30, fg_color=ACCENT, hover_color="#3182ce", command=command).grid(row=0, column=column, padx=2, sticky="ew")

    def apply_settings(self) -> None:
        self._build_ui()
        self.geometry("1200x720")
        self.minsize(1000, 640)

    def _summary_card(self, parent, column: int, title: str, value: str, size: int):
        card = ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=14)
        card.grid(row=0, column=column, padx=5, sticky="ew")
        ctk.CTkLabel(card, text=title, text_color=MUTED, font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=18, pady=(14, 1))
        label = ctk.CTkLabel(card, text=value, text_color=TEXT, font=ctk.CTkFont(size=size, weight="bold"))
        label.pack(anchor="w", padx=18, pady=(0, 14))
        return label

    def refresh(self) -> None:
        self.refresh_button.configure(state="disabled", text="Loading...")
        if self._refresh_poll_id is None:
            self._poll_refresh_queue()
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        connection = None
        try:
            connection, holdings_repository, prices_repository = create_worker_repositories(
                DATABASE_PATH
            )
            holdings = holdings_repository.list()
            prices = {}
            errors = {}
            for holding in holdings:
                try:
                    price = get_price(holding.asset.ticker, holding.asset.asset_type)
                    prices[holding.asset.ticker] = price.value
                    prices_repository.save(holding.asset.id, price)
                except TrackerError as exc:
                    errors[holding.asset.ticker] = str(exc)
            positions, totals = calculate_portfolio(
                [holding for holding in holdings if holding.asset.ticker in prices], prices
            )
            self._refresh_queue.put(("success", (holdings, positions, totals, errors)))
        except (TrackerError, sqlite3.Error, OSError, ValueError, KeyError, TypeError) as exc:
            self._refresh_queue.put(("error", exc))
        finally:
            if connection is not None:
                connection.close()

    def _poll_refresh_queue(self) -> None:
        try:
            result, payload = self._refresh_queue.get_nowait()
        except queue.Empty:
            self._refresh_poll_id = self.after(50, self._poll_refresh_queue)
            return
        self._refresh_poll_id = None
        if result == "error":
            self._show_refresh_error(payload)
        else:
            self._show_refresh(*payload)

    def _show_refresh_error(self, error: Exception) -> None:
        self.status_label.configure(text=f"Refresh failed: {error}")
        self.refresh_button.configure(state="normal", text="Refresh")

    def _show_refresh(self, holdings, positions, totals, errors) -> None:
        self.positions = positions
        self.totals = totals
        self.price_errors = errors
        self.total_label.configure(text=f"${totals.total_value:,.2f}")
        self.cost_label.configure(text=f"${totals.total_cost:,.2f}")
        self.gain_label.configure(
            text=f"{format_gain_loss(totals.profit_loss)}  ({totals.percent_return:+.2f}%)",
            text_color=POSITIVE if totals.profit_loss >= 0 else NEGATIVE,
        )
        self.updated_label.configure(text=f"Updated {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M')}")
        self.status_label.configure(text="; ".join(errors.values()))
        self._render_holdings()
        self._render_charts()
        if self.settings["save_snapshot_on_refresh"] and self.positions:
            self._snapshot_current("refresh")
        self.refresh_button.configure(state="normal", text="Refresh")
        if self.settings["auto_refresh"]:
            self.after(self.settings["refresh_interval_seconds"] * 1000, self.refresh)

    def _render_holdings(self) -> None:
        for child in self.list_frame.winfo_children():
            child.destroy()
        if not self.positions and not self.price_errors:
            ctk.CTkLabel(self.list_frame, text="No holdings yet. Add one to get started.", text_color=MUTED).pack(pady=18)
            return
        columns = (("Ticker", 0, 100), ("Qty", 1, 150), ("Price", 2, 170), ("Value", 3, 190), ("Gain/Loss", 4, 190))
        header = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        header.pack(fill="x", padx=8, pady=(0, 5))
        sort_keys = {"Ticker": "name", "Value": "value", "Gain/Loss": "gain_loss"}
        for title, column, width in columns:
            if title in sort_keys:
                ctk.CTkButton(header, text=title, text_color=MUTED, fg_color="transparent", hover_color=SURFACE_ALT, width=width, anchor="w", command=lambda key=sort_keys[title]: self._sort_holdings(key)).grid(row=0, column=column, sticky="w")
            else:
                ctk.CTkLabel(header, text=title, text_color=MUTED, width=width, anchor="w", font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=column, sticky="w")
        for position in sort_positions(self.positions, self.sort_by):
            color = POSITIVE if position.profit_loss >= 0 else NEGATIVE
            row = ctk.CTkFrame(self.list_frame, fg_color=SURFACE, corner_radius=8)
            row.pack(fill="x", padx=4, pady=3)
            values = (position.ticker, f"{position.quantity:g}", f"${position.price:,.2f}", f"${position.market_value:,.2f}", format_gain_loss(position.profit_loss))
            for value, (_, column, width) in zip(values, columns):
                ctk.CTkLabel(row, text=value, text_color=color if column == 4 else TEXT, width=width, anchor="w", font=ctk.CTkFont(weight="bold" if column == 0 else "normal")).grid(row=0, column=column, padx=(10 if column == 0 else 0), pady=9, sticky="w")
            row.bind("<Button-1>", lambda _event, item=position, target=row: self._toggle_position_details(item, target))
        for ticker, error in self.price_errors.items():
            ctk.CTkLabel(self.list_frame, text=f"{ticker}  price unavailable — {error}", text_color=WARNING, anchor="w").pack(fill="x", padx=12, pady=3)

    def _sort_holdings(self, sort_by: str) -> None:
        self.sort_by = sort_by
        self._render_holdings()

    def _toggle_position_details(self, position, row) -> None:
        detail = getattr(row, "_detail_label", None)
        if detail is not None:
            detail.destroy()
            row._detail_label = None
            return
        row._detail_label = ctk.CTkLabel(
            row,
            text=f"Purchase price ${position.cost_basis / position.quantity:,.2f}   Cost basis ${position.cost_basis:,.2f}   {position.percent_return:+.2f}% return",
            text_color=MUTED,
            anchor="w",
        )
        row._detail_label.grid(row=1, column=0, columnspan=len(row.grid_slaves(row=0)), padx=10, pady=(0, 8), sticky="w")

    def _render_charts(self) -> None:
        for axis in (self.value_axis, self.allocation_axis):
            axis.clear()
            axis.set_facecolor(SURFACE)
            axis.tick_params(colors=MUTED, labelsize=9)
            for spine in axis.spines.values():
                spine.set_visible(False)
            axis.grid(False)
        self.allocation_legend_axis.clear()
        self.allocation_legend_axis.set_facecolor(SURFACE)
        self.allocation_legend_axis.axis("off")
        history = filter_series_by_period(
            reversed(self.snapshots.history()),
            self.chart_period,
            datetime.now(timezone.utc),
        )
        if len(history) < 2:
            self.value_axis.text(0.5, 0.5, "Save snapshots to see history for this period.", color=MUTED, ha="center", va="center", wrap=True)
        else:
            _, values = zip(*value_series(history))
            _, costs = zip(*cost_basis_series(history))
            self.value_axis.plot(range(len(values)), values, color=ACCENT, linewidth=2)
            self.value_axis.plot(range(len(costs)), costs, color=MUTED, linestyle="--", linewidth=1)
            self.value_axis.set_xticks([])
            self.value_axis.set_ylabel("USD", color=MUTED, fontsize=9)
        allocations = allocation_percentages(self.positions)
        if allocations:
            wedges, _ = self.allocation_axis.pie(
                [value for _, value in allocations],
                colors=[ACCENT, "#8b5cf6", "#f59e0b", "#14b8a6", "#ec4899"],
                radius=1.25,
                wedgeprops={"width": 0.42, "edgecolor": SURFACE},
            )
            labels = [f"{ticker}  {value:.1f}%" for ticker, value in allocations]
            if allocation_legend_columns(len(allocations)) == 2:
                split = (len(labels) + 1) // 2
                legend_options = {
                    "loc": "center left",
                    "frameon": False,
                    "labelcolor": TEXT,
                    "fontsize": 8,
                    "mode": "expand",
                    "borderaxespad": 0,
                }
                first_legend = self.allocation_legend_axis.legend(
                    wedges[:split],
                    labels[:split],
                    bbox_to_anchor=(0, 0, 0.36, 1),
                    **legend_options,
                )
                self.allocation_legend_axis.add_artist(first_legend)
                self.allocation_legend_axis.legend(
                    wedges[split:],
                    labels[split:],
                    bbox_to_anchor=(0.34, 0, 0.66, 1),
                    **legend_options,
                )
            else:
                self.allocation_legend_axis.legend(
                    wedges,
                    labels,
                    bbox_to_anchor=(0, 0, 1, 1),
                    **{
                        "loc": "center left",
                        "frameon": False,
                        "labelcolor": TEXT,
                        "fontsize": 8,
                        "mode": "expand",
                        "borderaxespad": 0,
                    },
                )
        else:
            self.allocation_axis.text(0.5, 0.5, "Add holdings to see allocation", color=MUTED, ha="center", va="center")
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _set_period(self, period: str) -> None:
        self.chart_period = period
        self._render_charts()

    def _add_holding(self) -> None:
        ticker = simpledialog.askstring("Add holding", "Ticker:")
        if not ticker:
            return
        asset_type = simpledialog.askstring("Add holding", "Type (stock/etf/crypto):", initialvalue="stock")
        quantity = simpledialog.askstring("Add holding", "Quantity:")
        purchase_price = simpledialog.askstring("Add holding", "Purchase price per unit:")
        if not asset_type or not quantity or not purchase_price:
            return
        try:
            self.manager.add_or_update(ticker, asset_type.lower(), quantity, purchase_price)
            self.refresh()
        except TrackerError as exc:
            messagebox.showerror("Could not save holding", str(exc))

    def _remove_holding(self) -> None:
        ticker = simpledialog.askstring("Remove holding", "Ticker:")
        if ticker:
            try:
                self.manager.remove(ticker)
                self.refresh()
            except TrackerError as exc:
                messagebox.showerror("Could not remove holding", str(exc))

    def _save_snapshot(self) -> None:
        if not self.positions or self.totals is None:
            messagebox.showinfo("Snapshot", "Refresh prices before saving a snapshot.")
            return
        self._snapshot_current("manual")
        self._render_charts()

    def _snapshot_current(self, trigger: str) -> None:
        asset_ids = {
            holding.asset.ticker: holding.asset.id
            for holding in self.holdings.list()
            if any(position.ticker == holding.asset.ticker for position in self.positions)
        }
        self.snapshots.save(1, self.totals, self.positions, asset_ids, trigger)

    def _export(self) -> None:
        path = export_history(self.snapshots.history(), Path(EXPORT_DIR) / "portfolio_history.csv")
        self.status_label.configure(text=f"Exported to {path}")

    def _open_settings(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Settings")
        dialog.transient(self)
        dialog.resizable(True, True)
        action_row = ctk.CTkFrame(dialog, fg_color="transparent")
        action_row.pack(side="bottom", fill="x", padx=20, pady=14)
        auto_refresh = tk.BooleanVar(value=self.settings["auto_refresh"])
        save_snapshot = tk.BooleanVar(value=self.settings["save_snapshot_on_refresh"])
        always_on_top = tk.BooleanVar(value=self.settings["always_on_top"])
        theme = tk.StringVar(value=self.settings["theme"])
        default_chart = tk.StringVar(value=self.settings["default_chart"])
        fields = ctk.CTkScrollableFrame(dialog, label_text="Preferences")
        fields.pack(side="top", fill="both", expand=True, padx=10, pady=(10, 0))
        ctk.CTkCheckBox(fields, text="Auto-refresh", variable=auto_refresh).pack(anchor="w", padx=10, pady=(12, 8))
        ctk.CTkCheckBox(fields, text="Save snapshot on refresh", variable=save_snapshot).pack(anchor="w", padx=10, pady=8)
        ctk.CTkCheckBox(fields, text="Always on top", variable=always_on_top).pack(anchor="w", padx=10, pady=8)
        ctk.CTkLabel(fields, text="Theme").pack(anchor="w", padx=10, pady=(8, 2))
        ctk.CTkOptionMenu(fields, variable=theme, values=["dark", "light"]).pack(fill="x", padx=10)
        ctk.CTkLabel(fields, text="Default chart").pack(anchor="w", padx=10, pady=(8, 2))
        ctk.CTkOptionMenu(fields, variable=default_chart, values=["value", "allocation"]).pack(fill="x", padx=10)
        ctk.CTkLabel(fields, text="Refresh interval (seconds, minimum 60)").pack(anchor="w", padx=10, pady=(12, 2))
        interval = ctk.CTkEntry(fields)
        interval.insert(0, str(self.settings["refresh_interval_seconds"]))
        interval.pack(fill="x", padx=10)
        error_label = ctk.CTkLabel(fields, text="", text_color=NEGATIVE, wraplength=280)
        error_label.pack(padx=10, pady=(8, 0))

        def save_and_apply() -> None:
            save_button.configure(state="disabled")
            error_label.configure(text="")
            try:
                interval_value = int(interval.get())
                self.settings = save_settings(
                    {
                        **self.settings,
                        "auto_refresh": auto_refresh.get(),
                        "save_snapshot_on_refresh": save_snapshot.get(),
                        "always_on_top": always_on_top.get(),
                        "refresh_interval_seconds": interval_value,
                        "theme": theme.get(),
                        "default_chart": default_chart.get(),
                    }
                )
                self.chart_mode = self.settings["default_chart"]
                ctk.set_appearance_mode(self.settings["theme"])
                self.attributes("-topmost", self.settings["always_on_top"])
                self.apply_settings()
                dialog.destroy()
            except Exception as exc:
                traceback.print_exc()
                error_label.configure(text=f"Could not save and apply settings: {exc}")
                save_button.configure(state="normal")

        save_button = ctk.CTkButton(
            action_row,
            text="Save settings and apply",
            command=save_and_apply,
        )
        save_button.pack(fill="x")
        dialog.update_idletasks()
        requested_height = max(480, dialog.winfo_reqheight())
        dialog.geometry(f"340x{requested_height}")
        dialog.minsize(320, 480)
        def report_button_visibility() -> None:
            dialog.update_idletasks()
            print(
                "Settings button:",
                f"winfo_ismapped={save_button.winfo_ismapped()}",
                f"winfo_y={save_button.winfo_y()}",
                f"winfo_height={save_button.winfo_height()}",
                f"dialog_height={dialog.winfo_height()}",
                f"winfo_viewable={save_button.winfo_viewable()}",
            )

        dialog.after(100, report_button_visibility)

    def _close(self) -> None:
        save_settings(self.settings)
        self.connection.close()
        self.destroy()


def launch() -> None:
    PortfolioWidget().mainloop()
