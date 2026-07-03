"""
Finguide - polished Tkinter desktop app.

Upload a CSV of bank or card transactions, normalize the data, visualize
spending patterns, and get practical savings strategies. Optional Groq chat
can answer questions from the generated financial snapshot.

Setup:
    pip install -r requirements.txt
    export GROQ_API_KEY=your_key_here   # optional
    python expense_tracker.py
"""

from __future__ import annotations

import math
import os
import re
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, messagebox, ttk

os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.getcwd(), ".matplotlib-cache"))

import matplotlib

matplotlib.use("TkAgg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from dotenv import load_dotenv
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

load_dotenv()

try:
    from groq import Groq
except ImportError:
    Groq = None


APP_NAME = "Finguide"
APP_SLOGAN = "Smarter money moves, beautifully guided."
CHAT_NAME = "ThinkDesk"

APP_BG = "#f7f3ff"
PANEL_BG = "#ffffff"
INK = "#182033"
MUTED = "#647089"
ACCENT = "#7c3aed"
ACCENT_2 = "#06b6d4"
WARN = "#f97316"
GOOD = "#10b981"
LINE = "#d9d4ef"

THEMES = {
    "light": {
        "app_bg": "#f8f5ff",
        "panel_bg": "#ffffff",
        "panel_2": "#f0eaff",
        "ink": "#171528",
        "muted": "#665f7a",
        "accent": "#7c3aed",
        "accent_2": "#06b6d4",
        "warn": "#f97316",
        "good": "#10b981",
        "line": "#ded6f5",
        "tab": "#ebe3ff",
        "tab_hover": "#d9ccff",
        "tab_selected": "#ffffff",
        "tab_selected_hover": "#fff7d6",
        "tab_hover_text": "#4c1d95",
        "grid": "#ece7f8",
        "entry": "#ffffff",
        "header": "#f2edff",
        "button_active": "#6d28d9",
        "hero_bg": "#24163f",
        "hero_panel": "#34205f",
        "hero_accent": "#fbbf24",
        "chart_colors": ["#7c3aed", "#06b6d4", "#f97316", "#ec4899", "#22c55e", "#2563eb", "#facc15", "#14b8a6", "#ef4444"],
    },
    "dark": {
        "app_bg": "#0f1024",
        "panel_bg": "#18172f",
        "panel_2": "#242044",
        "ink": "#fbfaff",
        "muted": "#b7accf",
        "accent": "#a78bfa",
        "accent_2": "#22d3ee",
        "warn": "#fb923c",
        "good": "#34d399",
        "line": "#342e58",
        "tab": "#242044",
        "tab_hover": "#3d2d74",
        "tab_selected": "#18172f",
        "tab_selected_hover": "#32245f",
        "tab_hover_text": "#ffffff",
        "grid": "#302a4d",
        "entry": "#111226",
        "header": "#272147",
        "button_active": "#8b5cf6",
        "hero_bg": "#1b1235",
        "hero_panel": "#2b1d56",
        "hero_accent": "#facc15",
        "chart_colors": ["#a78bfa", "#22d3ee", "#fb923c", "#f472b6", "#34d399", "#60a5fa", "#fde047", "#2dd4bf", "#fb7185"],
    },
}

CATEGORY_COLORS = [
    "#7c3aed",
    "#06b6d4",
    "#f97316",
    "#ec4899",
    "#22c55e",
    "#2563eb",
    "#facc15",
    "#14b8a6",
    "#ef4444",
]

CATEGORY_KEYWORDS = {
    "Housing": ["rent", "mortgage", "landlord", "apartment", "hoa", "lease"],
    "Groceries": ["grocery", "supermarket", "market", "whole foods", "trader joe", "costco"],
    "Food & Dining": [
        "restaurant",
        "cafe",
        "coffee",
        "starbucks",
        "mcdonald",
        "pizza",
        "diner",
        "bakery",
        "bar",
        "kfc",
        "burger",
        "doordash",
        "ubereats",
        "swiggy",
        "zomato",
    ],
    "Transport": ["uber", "lyft", "taxi", "fuel", "gas station", "parking", "metro", "transit", "train", "flight", "airline"],
    "Shopping": ["amazon", "walmart", "target", "mall", "store", "shop", "clothing", "electronics", "flipkart"],
    "Utilities": ["electric", "water bill", "gas bill", "internet", "phone", "utility", "cable", "broadband"],
    "Entertainment": ["netflix", "spotify", "movie", "cinema", "game", "concert", "subscription", "hulu", "disney"],
    "Health": ["pharmacy", "doctor", "hospital", "clinic", "dental", "medical", "insurance"],
    "Education": ["course", "tuition", "book", "udemy", "coursera", "school", "college"],
    "Income": ["salary", "payroll", "deposit", "refund", "interest", "dividend"],
    "Other": [],
}


@dataclass
class FinanceMetrics:
    total_spend: float
    total_income: float
    net_cashflow: float
    transaction_count: int
    avg_daily_spend: float
    avg_transaction: float
    top_category: str
    top_category_amount: float
    recurring_monthly: float
    projected_monthly_spend: float
    savings_rate: float | None
    date_min: pd.Timestamp | None
    date_max: pd.Timestamp | None


def money(value: float) -> str:
    return f"Rs. {value:,.2f}"


def chart_money(value: float, _position=None) -> str:
    return f"Rs. {value:,.0f}"


def chart_money_compact(value: float, _position=None) -> str:
    value = float(value)
    absolute = abs(value)
    if absolute >= 10_000_000:
        return f"Rs. {value / 10_000_000:.1f}Cr"
    if absolute >= 100_000:
        return f"Rs. {value / 100_000:.1f}L"
    if absolute >= 1_000:
        return f"Rs. {value / 1_000:.0f}K"
    return f"Rs. {value:,.0f}"


def parse_money_input(value: str, default: float = 10000) -> float:
    cleaned = (
        str(value)
        .replace(",", "")
        .replace("₹", "")
        .replace("INR", "")
        .replace("inr", "")
        .replace("Rs.", "")
        .replace("rs.", "")
        .replace("Rs", "")
        .replace("rs", "")
        .strip()
    )
    try:
        amount = float(cleaned)
    except ValueError:
        return default
    return max(amount, 0)


def short_label(value: str, limit: int = 20) -> str:
    text = str(value)
    return text if len(text) <= limit else text[: limit - 1] + "..."


def pct(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:.1f}%"


def find_column(columns, candidates):
    lowered = {str(c).strip().lower(): c for c in columns}
    for candidate in candidates:
        for col_lower, col_original in lowered.items():
            if candidate in col_lower:
                return col_original
    return None


def categorize(description: str) -> str:
    text = str(description).lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if category == "Other":
            continue
        for keyword in keywords:
            if keyword in text:
                return category
    return "Other"


def normalize_amounts(df: pd.DataFrame, amount_col: str, type_col: str | None) -> pd.Series:
    raw_amount = pd.to_numeric(
        df[amount_col]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.replace("₹", "", regex=False)
        .str.replace("INR", "", case=False, regex=False)
        .str.replace("Rs.", "", case=False, regex=False)
        .str.replace("Rs", "", case=False, regex=False),
        errors="coerce",
    )
    if type_col is None:
        return raw_amount

    transaction_type = df[type_col].astype(str).str.lower()
    is_credit = transaction_type.str.contains("credit|income|deposit|salary|refund|cr", regex=True, na=False)
    is_debit = transaction_type.str.contains("debit|expense|withdraw|payment|purchase|dr", regex=True, na=False)

    signed = raw_amount.abs()
    signed = signed.where(~is_debit, -signed)
    signed = signed.where(~is_credit, signed.abs())
    return signed


def load_expenses(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [str(col).strip() for col in df.columns]

    date_col = find_column(df.columns, ["date", "posted", "transaction"])
    desc_col = find_column(df.columns, ["description", "merchant", "detail", "memo", "narration", "name"])
    amount_col = find_column(df.columns, ["amount", "debit", "value", "cost", "price"])
    category_col = find_column(df.columns, ["category", "spending category", "group"])
    type_col = find_column(df.columns, ["transaction type", "type", "kind", "direction", "credit/debit"])

    if amount_col is None:
        raise ValueError("Could not find an amount column. Include a column like Amount, Debit, Value, Cost, or Price.")

    out = pd.DataFrame()
    out["date"] = pd.to_datetime(df[date_col], errors="coerce") if date_col else pd.NaT
    out["description"] = df[desc_col].fillna("").astype(str) if desc_col else "Transaction"
    out["signed_amount"] = normalize_amounts(df, amount_col, type_col)

    if category_col:
        out["category"] = df[category_col].fillna("Other").astype(str).str.strip().replace("", "Other")
    else:
        out["category"] = out["description"].apply(categorize)

    if type_col is None and (out["signed_amount"] > 0).all():
        out["kind"] = "expense"
        out["amount"] = out["signed_amount"].abs()
    else:
        out["kind"] = out["signed_amount"].apply(lambda value: "income" if value > 0 else "expense")
        out["amount"] = out["signed_amount"].abs()

    out.loc[out["category"].str.lower().eq("income"), "kind"] = "income"
    out = out.dropna(subset=["amount"])
    out = out[out["amount"] > 0].copy()
    out["month"] = out["date"].dt.to_period("M").astype(str).where(out["date"].notna(), "No date")
    return out.reset_index(drop=True)


def expense_rows(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["kind"] == "expense"].copy()


def income_rows(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["kind"] == "income"].copy()


def date_span_days(df: pd.DataFrame) -> int:
    dated = df.dropna(subset=["date"])
    if dated.empty:
        return 30
    span = (dated["date"].max() - dated["date"].min()).days + 1
    return max(span, 1)


def compute_metrics(df: pd.DataFrame) -> FinanceMetrics:
    expenses = expense_rows(df)
    income = income_rows(df)
    total_spend = float(expenses["amount"].sum())
    total_income = float(income["amount"].sum())
    by_cat = expenses.groupby("category")["amount"].sum().sort_values(ascending=False)
    top_category = by_cat.index[0] if not by_cat.empty else "N/A"
    top_category_amount = float(by_cat.iloc[0]) if not by_cat.empty else 0.0
    days = date_span_days(df)
    projected_monthly_spend = total_spend / days * 30
    recurring_monthly = estimate_recurring(expenses)
    savings_rate = ((total_income - total_spend) / total_income * 100) if total_income else None

    dated = df.dropna(subset=["date"])
    return FinanceMetrics(
        total_spend=total_spend,
        total_income=total_income,
        net_cashflow=total_income - total_spend,
        transaction_count=len(df),
        avg_daily_spend=total_spend / days,
        avg_transaction=float(expenses["amount"].mean()) if not expenses.empty else 0.0,
        top_category=top_category,
        top_category_amount=top_category_amount,
        recurring_monthly=recurring_monthly,
        projected_monthly_spend=projected_monthly_spend,
        savings_rate=savings_rate,
        date_min=dated["date"].min() if not dated.empty else None,
        date_max=dated["date"].max() if not dated.empty else None,
    )


def estimate_recurring(expenses: pd.DataFrame) -> float:
    if expenses.empty:
        return 0.0
    recurring = expenses[
        expenses["description"].str.lower().str.contains(
            "subscription|netflix|spotify|hulu|prime|adobe|icloud|membership|monthly|annual",
            regex=True,
            na=False,
        )
    ]
    return float(recurring["amount"].sum())


def build_recommendations(df: pd.DataFrame) -> list[dict[str, str]]:
    if df.empty:
        return []

    expenses = expense_rows(df)
    metrics = compute_metrics(df)
    by_cat = expenses.groupby("category")["amount"].sum().sort_values(ascending=False)
    recommendations: list[dict[str, str]] = []

    if metrics.savings_rate is not None:
        if metrics.savings_rate < 10:
            recommendations.append(
                {
                    "title": "Protect the savings rate first",
                    "impact": "High",
                    "detail": f"Your estimated savings rate is {pct(metrics.savings_rate)}. Aim for 15-20% by setting an automatic transfer before discretionary spending starts.",
                }
            )
        elif metrics.savings_rate >= 20:
            recommendations.append(
                {
                    "title": "You have room to accelerate goals",
                    "impact": "Medium",
                    "detail": f"Your estimated savings rate is {pct(metrics.savings_rate)}. Consider directing surplus cash to debt payoff, emergency funds, or long-term investing.",
                }
            )

    if metrics.total_spend and not by_cat.empty:
        top_share = metrics.top_category_amount / metrics.total_spend * 100
        if top_share >= 30:
            trim = metrics.top_category_amount * 0.12
            recommendations.append(
                {
                    "title": f"Run a 12% trim test on {metrics.top_category}",
                    "impact": "High",
                    "detail": f"{metrics.top_category} is {top_share:.0f}% of spending. A modest 12% reduction could free up about {money(trim)} in this file's period.",
                }
            )

    dining = by_cat.get("Food & Dining", 0.0)
    groceries = by_cat.get("Groceries", 0.0)
    if metrics.total_spend and dining / metrics.total_spend > 0.18:
        recommendations.append(
            {
                "title": "Convert a few restaurant purchases into planned meals",
                "impact": "Medium",
                "detail": f"Dining is {pct(dining / metrics.total_spend * 100)} of spending. Replacing two meals per week with groceries can cut the category without feeling restrictive.",
            }
        )
    elif groceries and dining:
        recommendations.append(
            {
                "title": "Keep grocery and dining roles distinct",
                "impact": "Low",
                "detail": "Groceries and dining both appear in the data. Use groceries for planned meals and dining for intentional social or convenience moments.",
            }
        )

    subscriptions = expenses[
        expenses["description"].str.lower().str.contains(
            "subscription|netflix|spotify|hulu|prime|adobe|icloud|membership",
            regex=True,
            na=False,
        )
    ]
    if len(subscriptions) >= 2:
        recommendations.append(
            {
                "title": "Audit recurring charges",
                "impact": "Medium",
                "detail": f"Detected {len(subscriptions)} likely recurring charges totaling {money(float(subscriptions['amount'].sum()))}. Cancel, rotate, or annualize the ones you truly use.",
            }
        )

    if metrics.projected_monthly_spend > metrics.total_income > 0:
        recommendations.append(
            {
                "title": "Projected spending is above income",
                "impact": "High",
                "detail": f"Projected monthly spend is {money(metrics.projected_monthly_spend)} against income of {money(metrics.total_income)} in the file. Freeze non-essential purchases until the gap closes.",
            }
        )

    if not recommendations:
        recommendations.append(
            {
                "title": "Spending mix looks balanced",
                "impact": "Low",
                "detail": "No major imbalance jumped out. Keep uploading monthly statements so trends, subscriptions, and category drift become visible earlier.",
            }
        )

    return recommendations[:6]


def build_summary_text(df: pd.DataFrame) -> str:
    if df.empty:
        return "Upload a CSV to generate a financial snapshot."

    metrics = compute_metrics(df)
    expenses = expense_rows(df)
    by_cat = expenses.groupby("category")["amount"].sum().sort_values(ascending=False)
    period = "Unknown period"
    if metrics.date_min is not None and metrics.date_max is not None:
        period = f"{metrics.date_min.strftime('%b %d, %Y')} to {metrics.date_max.strftime('%b %d, %Y')}"

    lines = [
        "Financial Snapshot",
        f"Period: {period}",
        f"Transactions: {metrics.transaction_count}",
        f"Total spending: {money(metrics.total_spend)}",
        f"Total income detected: {money(metrics.total_income)}",
        f"Net cash flow: {money(metrics.net_cashflow)}",
        f"Projected monthly spend: {money(metrics.projected_monthly_spend)}",
        f"Estimated savings rate: {pct(metrics.savings_rate)}",
        "",
        "Category Breakdown",
    ]
    for category, amount in by_cat.items():
        share = amount / metrics.total_spend * 100 if metrics.total_spend else 0
        lines.append(f"- {category}: {money(float(amount))} ({share:.1f}%)")

    lines.append("")
    lines.append("Savings Strategies")
    for rec in build_recommendations(df):
        lines.append(f"- [{rec['impact']}] {rec['title']}: {rec['detail']}")
    return "\n".join(lines)


def build_local_advice(df: pd.DataFrame, question: str) -> str:
    if df.empty:
        return "Upload a CSV first, then I can answer using your actual spending data."

    metrics = compute_metrics(df)
    expenses = expense_rows(df)
    by_cat = expenses.groupby("category")["amount"].sum().sort_values(ascending=False)
    question_l = question.lower()

    if any(word in question_l for word in ["category", "highest", "most", "top"]):
        lines = ["Your top spending categories are:"]
        for category, amount in by_cat.head(5).items():
            share = amount / metrics.total_spend * 100 if metrics.total_spend else 0
            lines.append(f"- {category}: {money(float(amount))} ({share:.1f}%)")
        return "\n".join(lines)

    if any(word in question_l for word in ["save", "saving", "cut", "reduce", "strategy"]):
        lines = ["Here are the strongest savings moves from this file:"]
        for rec in build_recommendations(df)[:4]:
            lines.append(f"- {rec['title']}: {rec['detail']}")
        return "\n".join(lines)

    if any(word in question_l for word in ["month", "monthly", "trend"]):
        dated = expenses.dropna(subset=["date"])
        if dated.empty:
            return "I cannot calculate a monthly trend because this CSV does not have usable dates."
        monthly = dated.set_index("date").resample("ME")["amount"].sum().sort_index()
        latest = monthly.iloc[-1]
        average = monthly.mean()
        return f"Latest monthly spend is {money(float(latest))}. Average monthly spend across the file is {money(float(average))}."

    return (
        f"Total spending is {money(metrics.total_spend)} with projected monthly spend of "
        f"{money(metrics.projected_monthly_spend)}. Top category is {metrics.top_category} "
        f"at {money(metrics.top_category_amount)}. Estimated savings rate: {pct(metrics.savings_rate)}."
    )


class GroqChat:
    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        self.client = Groq(api_key=api_key) if Groq is not None and api_key else None
        self.model = "llama-3.3-70b-versatile"

    def available(self) -> bool:
        return self.client is not None

    def ask(self, question: str, context: str) -> str:
        if not self.available():
            return "Groq is not configured. Add GROQ_API_KEY to your environment or .env file, then restart the app."
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are ThinkDesk, a careful personal finance guide. Use only the provided transaction "
                            "summary. Give concrete, kind, non-judgmental advice. Do not provide tax, legal, "
                            "or investment guarantees. Your chat name is ThinkDesk.\n\n"
                            + context
                        ),
                    },
                    {"role": "user", "content": question},
                ],
            )
            return response.choices[0].message.content
        except Exception as exc:
            return f"Could not contact Groq: {exc}"


class PersonalFinanceAdvisor:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1280x860")
        self.root.minsize(1080, 720)

        self.df = pd.DataFrame()
        self.filtered_df = pd.DataFrame()
        self.summary = "Upload a CSV to generate a financial snapshot."
        self.groq_chat = GroqChat()
        self.chart_canvas = None
        self.chart_view = tk.StringVar(value="Categories")
        self.theme_name = "dark"
        self.colors = THEMES[self.theme_name]
        self.themed_text_widgets: list[tk.Text] = []
        self.root.configure(bg=self.colors["app_bg"])

        self._configure_style()
        self._build_shell()
        self._set_empty_state()

    def _configure_style(self):
        colors = self.colors
        style = ttk.Style()
        style.theme_use("clam")
        base_font = ("Helvetica", 12)
        style.configure(".", background=colors["app_bg"], foreground=colors["ink"], font=base_font)
        style.configure("TFrame", background=colors["app_bg"])
        style.configure("Panel.TFrame", background=colors["panel_bg"], relief="flat")
        style.configure("Surface.TFrame", background=colors["panel_2"], relief="flat")
        style.configure("Hero.TFrame", background=colors["hero_bg"], relief="flat")
        style.configure("HeroPanel.TFrame", background=colors["hero_panel"], relief="flat")
        style.configure("TLabel", background=colors["app_bg"], foreground=colors["ink"])
        style.configure("Muted.TLabel", background=colors["app_bg"], foreground=colors["muted"])
        style.configure("Panel.TLabel", background=colors["panel_bg"], foreground=colors["ink"])
        style.configure("Surface.TLabel", background=colors["panel_2"], foreground=colors["ink"])
        style.configure("Hero.TLabel", background=colors["hero_bg"], foreground="#ffffff")
        style.configure("HeroMuted.TLabel", background=colors["hero_bg"], foreground="#d8ceff")
        style.configure("HeroAccent.TLabel", background=colors["hero_bg"], foreground=colors["hero_accent"])
        style.configure("HeroPanel.TLabel", background=colors["hero_panel"], foreground="#ffffff")
        style.configure("Metric.TLabel", background=colors["panel_bg"], foreground=colors["ink"], font=("Helvetica", 26, "bold"))
        style.configure("MetricTitle.TLabel", background=colors["panel_bg"], foreground=colors["muted"], font=("Helvetica", 10, "bold"))
        style.configure("Accent.TButton", background=colors["accent"], foreground="#ffffff", borderwidth=0, padding=(18, 11), font=("Helvetica", 12, "bold"))
        style.map("Accent.TButton", background=[("active", colors["button_active"])])
        style.configure("Ghost.TButton", background=colors["panel_2"], foreground=colors["ink"], borderwidth=0, padding=(14, 10), font=("Helvetica", 12, "bold"))
        style.map("Ghost.TButton", background=[("active", colors["line"])])
        style.configure("TButton", padding=(14, 10), borderwidth=0, font=base_font)
        style.configure("TNotebook", background=colors["app_bg"], borderwidth=0, tabmargins=(0, 4, 0, 0))
        style.configure(
            "TNotebook.Tab",
            padding=(22, 12),
            background=colors["tab"],
            foreground=colors["muted"],
            borderwidth=0,
            focuscolor=colors["accent"],
            font=("Helvetica", 12, "bold"),
        )
        style.map(
            "TNotebook.Tab",
            background=[
                ("selected", "active", colors["tab_selected_hover"]),
                ("active", colors["tab_hover"]),
                ("selected", colors["tab_selected"]),
            ],
            foreground=[
                ("selected", "active", colors["ink"]),
                ("active", colors["tab_hover_text"]),
                ("selected", colors["ink"]),
            ],
            expand=[
                ("selected", (2, 2, 2, 0)),
                ("active", (1, 1, 1, 0)),
            ],
        )
        style.configure("Treeview", rowheight=34, background=colors["panel_bg"], fieldbackground=colors["panel_bg"], foreground=colors["ink"], bordercolor=colors["line"], font=("Helvetica", 12))
        style.map("Treeview", background=[("selected", colors["panel_2"])], foreground=[("selected", colors["ink"])])
        style.configure("Treeview.Heading", background=colors["header"], foreground=colors["ink"], font=("Helvetica", 11, "bold"))
        style.configure("TEntry", fieldbackground=colors["entry"], foreground=colors["ink"], insertcolor=colors["ink"], bordercolor=colors["line"])
        style.configure("TCombobox", fieldbackground=colors["entry"], foreground=colors["ink"], arrowcolor=colors["muted"], bordercolor=colors["line"])
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", colors["panel_2"]), ("focus", colors["panel_2"])],
            selectbackground=[("readonly", colors["line"]), ("focus", colors["line"])],
            selectforeground=[("readonly", colors["ink"]), ("focus", colors["ink"])],
            foreground=[("readonly", colors["ink"])],
        )

    def toggle_theme(self):
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self.colors = THEMES[self.theme_name]
        self._apply_theme()

    def _apply_theme(self):
        self.root.configure(bg=self.colors["app_bg"])
        self._configure_style()
        self.theme_button.configure(text="Dark Mode" if self.theme_name == "light" else "Light Mode")

        for widget in self.themed_text_widgets:
            widget.configure(
                bg=self.colors["panel_bg"],
                fg=self.colors["ink"],
                insertbackground=self.colors["ink"],
                selectbackground=self.colors["accent"],
            )
            widget.tag_configure("sender", foreground=self.colors["accent"])
            widget.tag_configure("message", foreground=self.colors["ink"])

        if self.df.empty:
            self._set_empty_state()
        else:
            self._refresh_all()

    def _build_shell(self):
        header = ttk.Frame(self.root, style="Hero.TFrame", padding=(28, 24, 28, 20))
        header.pack(fill="x", padx=22, pady=(20, 10))

        title_area = ttk.Frame(header, style="Hero.TFrame")
        title_area.pack(side="left", fill="x", expand=True)
        ttk.Label(title_area, text=APP_NAME, style="Hero.TLabel", font=("Helvetica", 34, "bold")).pack(anchor="w")
        ttk.Label(title_area, text=APP_SLOGAN, style="HeroAccent.TLabel", font=("Helvetica", 17, "bold")).pack(anchor="w", pady=(4, 0))
        ttk.Label(
            title_area,
            text="Colorful CSV insights, elegant spending visuals, and sharper savings decisions in one calm workspace.",
            style="HeroMuted.TLabel",
            font=("Helvetica", 13),
        ).pack(anchor="w", pady=(7, 0))

        self.theme_button = ttk.Button(header, text="Light Mode", style="Ghost.TButton", command=self.toggle_theme)
        self.theme_button.pack(side="right", padx=(10, 0))
        ttk.Button(header, text="Upload CSV", style="Accent.TButton", command=self.upload_csv).pack(side="right")

        self.status_var = tk.StringVar(value="No file loaded")
        ttk.Label(self.root, textvariable=self.status_var, style="Muted.TLabel", padding=(28, 0, 28, 10), font=("Helvetica", 12, "bold")).pack(fill="x")

        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill="both", expand=True, padx=22, pady=(0, 20))
        self.tabs.bind("<Motion>", self._on_tab_motion)
        self.tabs.bind("<Leave>", self._on_tab_leave)

        self.overview_tab = ttk.Frame(self.tabs)
        self.charts_tab = ttk.Frame(self.tabs)
        self.transactions_tab = ttk.Frame(self.tabs)
        self.strategy_tab = ttk.Frame(self.tabs)
        self.chat_tab = ttk.Frame(self.tabs)

        self.tabs.add(self.overview_tab, text="Overview")
        self.tabs.add(self.charts_tab, text="Visuals")
        self.tabs.add(self.transactions_tab, text="Transactions")
        self.tabs.add(self.strategy_tab, text="Strategy")
        self.tabs.add(self.chat_tab, text=CHAT_NAME)

        self._build_overview_tab()
        self._build_charts_tab()
        self._build_transactions_tab()
        self._build_strategy_tab()
        self._build_chat_tab()

    def _on_tab_motion(self, event):
        element = self.tabs.identify(event.x, event.y)
        self.tabs.configure(cursor="hand2" if element else "")

    def _on_tab_leave(self, _event):
        self.tabs.configure(cursor="")

    def _panel(self, parent, padding=16):
        frame = ttk.Frame(parent, style="Panel.TFrame", padding=padding)
        return frame

    def _build_overview_tab(self):
        self.metric_frame = ttk.Frame(self.overview_tab)
        self.metric_frame.pack(fill="x", pady=(16, 10))

        self.metric_vars = {}
        metrics = [
            ("total_spend", "Total Spend"),
            ("net_cashflow", "Net Cash Flow"),
            ("savings_rate", "Savings Rate"),
            ("projected", "Projected Monthly"),
        ]
        for key, label in metrics:
            panel = self._panel(self.metric_frame, 14)
            panel.pack(side="left", fill="x", expand=True, padx=(0, 10))
            ttk.Label(panel, text=label.upper(), style="MetricTitle.TLabel").pack(anchor="w")
            var = tk.StringVar(value="-")
            self.metric_vars[key] = var
            ttk.Label(panel, textvariable=var, style="Metric.TLabel").pack(anchor="w", pady=(8, 0))

        lower = ttk.Frame(self.overview_tab)
        lower.pack(fill="both", expand=True, pady=(4, 0))

        left = self._panel(lower)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        ttk.Label(left, text="Priority Insights", style="Panel.TLabel", font=("Helvetica", 18, "bold")).pack(anchor="w")
        self.insights_frame = ttk.Frame(left, style="Panel.TFrame")
        self.insights_frame.pack(fill="both", expand=True, pady=(12, 0))

        right = self._panel(lower)
        right.pack(side="left", fill="both", expand=True)
        ttk.Label(right, text="Financial Snapshot", style="Panel.TLabel", font=("Helvetica", 18, "bold")).pack(anchor="w")
        self.snapshot_text = tk.Text(
            right,
            height=16,
            wrap="word",
            bg=self.colors["panel_bg"],
            fg=self.colors["ink"],
            insertbackground=self.colors["ink"],
            selectbackground=self.colors["accent"],
            relief="flat",
            padx=0,
            pady=12,
            font=("Menlo", 12),
        )
        self.themed_text_widgets.append(self.snapshot_text)
        self.snapshot_text.pack(fill="both", expand=True)

    def _build_charts_tab(self):
        self.charts_container = self._panel(self.charts_tab)
        self.charts_container.pack(fill="both", expand=True, pady=16)

    def _build_transactions_tab(self):
        controls = ttk.Frame(self.transactions_tab)
        controls.pack(fill="x", pady=(16, 10))

        ttk.Label(controls, text="Search").pack(side="left")
        self.search_var = tk.StringVar()
        search = ttk.Entry(controls, textvariable=self.search_var, width=34)
        search.pack(side="left", padx=(8, 18))
        search.bind("<KeyRelease>", lambda _event: self._refresh_transactions())

        ttk.Label(controls, text="Category").pack(side="left")
        self.category_filter = tk.StringVar(value="All")
        self.category_menu = ttk.Combobox(controls, textvariable=self.category_filter, values=["All"], state="readonly", width=22)
        self.category_menu.pack(side="left", padx=(8, 18))
        self.category_menu.bind("<<ComboboxSelected>>", lambda _event: self._refresh_transactions())

        self.transaction_count_var = tk.StringVar(value="")
        ttk.Label(controls, textvariable=self.transaction_count_var, style="Muted.TLabel").pack(side="right")

        columns = ("date", "description", "category", "kind", "amount")
        self.tree = ttk.Treeview(self.transactions_tab, columns=columns, show="headings")
        widths = {"date": 130, "description": 420, "category": 190, "kind": 100, "amount": 120}
        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=widths[col], anchor="e" if col == "amount" else "w")
        self.tree.pack(fill="both", expand=True)

    def _build_strategy_tab(self):
        top = ttk.Frame(self.strategy_tab)
        top.pack(fill="x", pady=(16, 10))

        ttk.Label(top, text="Monthly savings target", font=("Helvetica", 12, "bold")).pack(side="left")
        self.goal_var = tk.StringVar(value="10000")
        self.goal_entry = ttk.Entry(top, textvariable=self.goal_var, width=16)
        self.goal_entry.pack(side="left", padx=(10, 8))
        self.goal_entry.bind("<Return>", lambda _event: self._refresh_strategy())
        ttk.Button(top, text="Update Plan", style="Accent.TButton", command=self._refresh_strategy).pack(side="left", padx=(0, 12))

        for amount in (5000, 10000, 25000, 50000):
            ttk.Button(top, text=chart_money_compact(amount), style="Ghost.TButton", command=lambda value=amount: self._set_goal(value)).pack(side="left", padx=(0, 6))

        self.goal_label = ttk.Label(top, text=f"Target: {money(10000)}", style="Muted.TLabel", font=("Helvetica", 12, "bold"))
        self.goal_label.pack(side="right")

        body = ttk.Frame(self.strategy_tab)
        body.pack(fill="both", expand=True)

        plan = self._panel(body)
        plan.pack(side="left", fill="both", expand=True, padx=(0, 10))
        ttk.Label(plan, text="Savings Plan", style="Panel.TLabel", font=("Helvetica", 18, "bold")).pack(anchor="w")
        self.plan_text = tk.Text(
            plan,
            wrap="word",
            bg=self.colors["panel_bg"],
            fg=self.colors["ink"],
            insertbackground=self.colors["ink"],
            selectbackground=self.colors["accent"],
            relief="flat",
            font=("Helvetica", 13),
            padx=0,
            pady=12,
        )
        self.themed_text_widgets.append(self.plan_text)
        self.plan_text.pack(fill="both", expand=True)

        recs = self._panel(body)
        recs.pack(side="left", fill="both", expand=True)
        ttk.Label(recs, text="Recommended Actions", style="Panel.TLabel", font=("Helvetica", 18, "bold")).pack(anchor="w")
        self.actions_frame = ttk.Frame(recs, style="Panel.TFrame")
        self.actions_frame.pack(fill="both", expand=True, pady=(12, 0))

    def _build_chat_tab(self):
        prompt_bar = ttk.Frame(self.chat_tab)
        prompt_bar.pack(fill="x", pady=(16, 8))
        ttk.Label(prompt_bar, text=f"Ask {CHAT_NAME} about", font=("Helvetica", 12, "bold")).pack(side="left")
        prompts = [
            "Where can I save money?",
            "What are my top categories?",
            "How is my monthly trend?",
        ]
        for prompt in prompts:
            ttk.Button(prompt_bar, text=prompt, style="Ghost.TButton", command=lambda text=prompt: self._ask_prompt(text)).pack(side="left", padx=(8, 0))

        self.chat_history = tk.Text(
            self.chat_tab,
            wrap="word",
            state="disabled",
            bg=self.colors["panel_bg"],
            fg=self.colors["ink"],
            insertbackground=self.colors["ink"],
            selectbackground=self.colors["accent"],
            relief="flat",
            padx=16,
            pady=16,
            font=("Helvetica", 13),
        )
        self.themed_text_widgets.append(self.chat_history)
        self.chat_history.tag_configure("sender", foreground=self.colors["accent"], font=("Helvetica", 12, "bold"))
        self.chat_history.tag_configure("message", foreground=self.colors["ink"], spacing3=10)
        self.chat_history.pack(fill="both", expand=True, pady=(0, 10))

        entry_frame = ttk.Frame(self.chat_tab)
        entry_frame.pack(fill="x", pady=(0, 16))
        self.chat_entry = tk.Text(
            entry_frame,
            height=4,
            wrap="word",
            bg=self.colors["panel_bg"],
            fg=self.colors["ink"],
            insertbackground=self.colors["ink"],
            selectbackground=self.colors["accent"],
            relief="flat",
            padx=16,
            pady=12,
            font=("Helvetica", 13),
        )
        self.themed_text_widgets.append(self.chat_entry)
        self.chat_entry.pack(side="left", fill="x", expand=True)
        self.chat_entry.bind("<Return>", self._send_chat_from_keyboard)
        self.chat_entry.bind("<Shift-Return>", lambda _event: None)
        ttk.Button(entry_frame, text="Send", style="Accent.TButton", command=self.send_chat).pack(side="left", fill="y", padx=(10, 0))

        if not self.groq_chat.available():
            self._append_chat(CHAT_NAME, "Groq is offline, so I will answer locally from your uploaded CSV. Add GROQ_API_KEY later for deeper conversational analysis.")

    def _set_empty_state(self):
        self.metric_vars["total_spend"].set("-")
        self.metric_vars["net_cashflow"].set("-")
        self.metric_vars["savings_rate"].set("-")
        self.metric_vars["projected"].set("-")
        self._write_text(self.snapshot_text, "Upload a CSV to see a complete financial snapshot.")
        self._empty_frame(self.insights_frame, "No insights yet. Upload a CSV to begin.")
        self._refresh_charts()
        self._write_text(self.plan_text, "Set a goal after uploading transactions to see a savings path.")
        self._empty_frame(self.actions_frame, "Recommendations will appear here.")

    def upload_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not path:
            return
        try:
            self.df = load_expenses(path)
        except Exception as exc:
            messagebox.showerror("Error loading CSV", str(exc))
            return

        if self.df.empty:
            messagebox.showwarning("No usable rows", "The CSV loaded, but no valid transactions were found.")
            return

        self.status_var.set(f"Loaded {len(self.df)} transactions from {os.path.basename(path)}")
        self.summary = build_summary_text(self.df)
        self._refresh_all()

    def _refresh_all(self):
        self._refresh_overview()
        self._refresh_charts()
        self._refresh_filters()
        self._refresh_transactions()
        self._refresh_strategy()

    def _refresh_overview(self):
        metrics = compute_metrics(self.df)
        self.metric_vars["total_spend"].set(money(metrics.total_spend))
        self.metric_vars["net_cashflow"].set(money(metrics.net_cashflow))
        self.metric_vars["savings_rate"].set(pct(metrics.savings_rate))
        self.metric_vars["projected"].set(money(metrics.projected_monthly_spend))
        self._write_text(self.snapshot_text, self.summary)

        for widget in self.insights_frame.winfo_children():
            widget.destroy()
        for rec in build_recommendations(self.df):
            self._insight_card(self.insights_frame, rec["title"], rec["detail"], rec["impact"])

    def _insight_card(self, parent, title: str, detail: str, impact: str):
        colors = self.colors
        impact_color = {"High": colors["warn"], "Medium": colors["accent"], "Low": colors["good"]}.get(impact, colors["muted"])
        card = ttk.Frame(parent, style="Panel.TFrame", padding=(0, 4, 0, 12))
        card.pack(fill="x", pady=(0, 10))
        ttk.Label(card, text=f"{impact.upper()} IMPACT", foreground=impact_color, background=colors["panel_bg"], font=("Helvetica", 10, "bold")).pack(anchor="w")
        ttk.Label(card, text=title, style="Panel.TLabel", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(3, 2))
        ttk.Label(card, text=detail, style="Panel.TLabel", wraplength=520, foreground=colors["muted"], font=("Helvetica", 12)).pack(anchor="w")
        ttk.Separator(parent).pack(fill="x", pady=(0, 10))

    def _refresh_charts(self):
        for widget in self.charts_container.winfo_children():
            widget.destroy()
        if self.chart_canvas is not None:
            plt.close(self.chart_canvas.figure)
            self.chart_canvas = None

        header = ttk.Frame(self.charts_container, style="Panel.TFrame")
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text="Spending Visuals", style="Panel.TLabel", font=("Helvetica", 19, "bold")).pack(anchor="w")
        ttk.Label(
            header,
            text="Choose one focused view at a time for cleaner reading.",
            style="Panel.TLabel",
            foreground=self.colors["muted"],
            font=("Helvetica", 12),
        ).pack(anchor="w", pady=(3, 0))

        controls = ttk.Frame(self.charts_container, style="Panel.TFrame")
        controls.pack(fill="x", pady=(0, 12))
        for view in ("Categories", "Trend", "Share", "Transactions"):
            style = "Accent.TButton" if self.chart_view.get() == view else "Ghost.TButton"
            ttk.Button(controls, text=view, style=style, command=lambda value=view: self._set_chart_view(value)).pack(side="left", padx=(0, 8))

        plot_frame = ttk.Frame(self.charts_container, style="Panel.TFrame")
        plot_frame.pack(fill="both", expand=True)

        if self.df.empty:
            ttk.Label(plot_frame, text="Upload a CSV to see spending visuals.", style="Panel.TLabel", font=("Helvetica", 15, "bold")).pack(pady=60)
            return

        expenses = expense_rows(self.df)
        by_cat = expenses.groupby("category")["amount"].sum().sort_values(ascending=False)
        fig, ax = plt.subplots(figsize=(12.6, 6.2), dpi=100, facecolor=self.colors["panel_bg"], constrained_layout=True)
        fig.set_constrained_layout_pads(w_pad=0.08, h_pad=0.08)

        view = self.chart_view.get()
        if view == "Trend":
            self._draw_monthly_trend(ax, expenses)
        elif view == "Share":
            self._draw_share_bars(ax, by_cat)
        elif view == "Transactions":
            self._draw_spend_distribution(ax, expenses)
        else:
            self._draw_category_bar(ax, by_cat)

        self.chart_canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        self.chart_canvas.draw()
        self.chart_canvas.get_tk_widget().pack(fill="both", expand=True)

    def _set_chart_view(self, view: str):
        self.chart_view.set(view)
        self._refresh_charts()

    def _style_axis(self, ax, title: str):
        colors = self.colors
        ax.set_facecolor(colors["panel_bg"])
        ax.set_title(title, loc="left", fontsize=15, fontweight="bold", color=colors["ink"], pad=12)
        ax.tick_params(colors=colors["muted"], labelsize=11)
        ax.xaxis.label.set_color(colors["muted"])
        ax.yaxis.label.set_color(colors["muted"])
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        for spine in ax.spines.values():
            spine.set_color(colors["line"])
        ax.grid(axis="y", color=colors["grid"], linewidth=1)
        ax.set_axisbelow(True)

    def _draw_category_bar(self, ax, by_cat: pd.Series):
        self._style_axis(ax, "Top Categories")
        if by_cat.empty:
            self._chart_empty(ax, "No expenses to chart")
            return
        top = by_cat.head(7).copy()
        if len(by_cat) > 7:
            top.loc["Other categories"] = by_cat.iloc[7:].sum()
        top = top.sort_values()
        labels = [short_label(label, 22) for label in top.index]
        ax.barh(labels, top.values, color=self.colors["chart_colors"][: len(top)], height=0.58)
        ax.set_xlabel("Spend")
        ax.xaxis.set_major_formatter(chart_money_compact)
        ax.margins(x=0.08)

    def _draw_monthly_trend(self, ax, expenses: pd.DataFrame):
        self._style_axis(ax, "Monthly Trend")
        dated = expenses.dropna(subset=["date"])
        if dated.empty:
            self._chart_empty(ax, "No date column found")
            return
        monthly = dated.set_index("date").resample("ME")["amount"].sum()
        ax.plot(monthly.index, monthly.values, color=self.colors["accent"], marker="o", linewidth=2.5)
        ax.fill_between(monthly.index, monthly.values, color=self.colors["accent"], alpha=0.16)
        ax.yaxis.set_major_formatter(chart_money_compact)
        locator = mdates.AutoDateLocator(minticks=3, maxticks=6)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        ax.tick_params(axis="x", rotation=0)
        for label in ax.get_xticklabels():
            label.set_horizontalalignment("center")

    def _draw_share_bars(self, ax, by_cat: pd.Series):
        colors = self.colors
        self._style_axis(ax, "Spending Share")
        if by_cat.empty:
            self._chart_empty(ax, "No expenses to chart")
            return

        total = by_cat.sum()
        top = by_cat.head(6).copy()
        if len(by_cat) > 6:
            top.loc["Other"] = by_cat.iloc[6:].sum()
        shares = (top / total * 100).sort_values()
        amounts = top.reindex(shares.index)
        labels = [short_label(label, 24) for label in shares.index]
        bars = ax.barh(labels, shares.values, color=colors["chart_colors"][: len(shares)], height=0.52)
        ax.set_xlim(0, max(100, shares.max() * 1.18))
        ax.set_xlabel("Share of spending")
        ax.xaxis.set_major_formatter(lambda value, _pos: f"{value:.0f}%")
        ax.grid(axis="x", color=colors["grid"], linewidth=1)
        ax.grid(axis="y", visible=False)
        ax.margins(y=0.16)

        for bar, share, amount in zip(bars, shares.values, amounts.values):
            ax.text(
                min(bar.get_width() + 1.2, 96),
                bar.get_y() + bar.get_height() / 2,
                f"{share:.1f}%  {chart_money_compact(amount)}",
                va="center",
                ha="left",
                color=colors["muted"],
                fontsize=11,
            )

    def _draw_spend_distribution(self, ax, expenses: pd.DataFrame):
        self._style_axis(ax, "Transaction Size")
        if expenses.empty:
            self._chart_empty(ax, "No expenses to chart")
            return
        bins = min(14, max(5, int(math.sqrt(len(expenses)))))
        ax.hist(expenses["amount"], bins=bins, color=self.colors["accent_2"], alpha=0.82, edgecolor=self.colors["panel_bg"])
        ax.set_xlabel("Transaction amount")
        ax.set_ylabel("Count")
        ax.xaxis.set_major_formatter(chart_money_compact)
        ax.margins(x=0.04)

    def _chart_empty(self, ax, message: str):
        ax.text(0.5, 0.5, message, ha="center", va="center", color=self.colors["muted"], transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)

    def _refresh_filters(self):
        categories = ["All"] + sorted(self.df["category"].dropna().unique().tolist())
        self.category_menu.configure(values=categories)
        if self.category_filter.get() not in categories:
            self.category_filter.set("All")

    def _refresh_transactions(self):
        self.tree.delete(*self.tree.get_children())
        if self.df.empty:
            self.transaction_count_var.set("")
            return

        df = self.df.copy()
        query = self.search_var.get().strip().lower()
        category = self.category_filter.get()
        if query:
            df = df[df["description"].str.lower().str.contains(re.escape(query), na=False)]
        if category and category != "All":
            df = df[df["category"] == category]

        df = df.sort_values(["date", "description"], ascending=[False, True], na_position="last")
        self.filtered_df = df
        for _, row in df.iterrows():
            date_value = row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else ""
            self.tree.insert(
                "",
                "end",
                values=(date_value, row["description"], row["category"], row["kind"].title(), money(float(row["amount"]))),
            )
        self.transaction_count_var.set(f"{len(df)} shown")

    def _set_goal(self, amount: float):
        self.goal_var.set(f"{amount:,.0f}")
        self._refresh_strategy()

    def _refresh_strategy(self):
        goal = parse_money_input(self.goal_var.get())
        self.goal_var.set(f"{goal:,.0f}")
        self.goal_label.configure(text=f"Target: {money(goal)}")
        if self.df.empty:
            return

        metrics = compute_metrics(self.df)
        expenses = expense_rows(self.df)
        by_cat = expenses.groupby("category")["amount"].sum().sort_values(ascending=False)
        top_three = by_cat.head(3)
        available_cash = max(metrics.net_cashflow, 0.0)
        remaining = max(goal - available_cash, 0.0)

        lines = [
            f"Goal: save {money(goal)} per month",
            f"Current net cash flow in uploaded data: {money(metrics.net_cashflow)}",
            f"Projected monthly spend: {money(metrics.projected_monthly_spend)}",
            "",
        ]
        if remaining <= 0:
            lines.append("You are already on track for this goal based on the uploaded data. Automate the transfer and protect it from discretionary spending.")
        else:
            lines.append(f"You need to create roughly {money(remaining)} more monthly room.")
            lines.append("A practical split:")
            if not top_three.empty:
                per_bucket = remaining / len(top_three)
                for category, amount in top_three.items():
                    trim_pct = min(per_bucket / amount * 100, 30) if amount else 0
                    lines.append(f"- Trim {category} by about {pct(trim_pct)} to free {money(min(per_bucket, amount * 0.3))}")
            lines.append("- Put any one-time refunds or bonuses directly toward the goal before spending them.")

        self._write_text(self.plan_text, "\n".join(lines))

        for widget in self.actions_frame.winfo_children():
            widget.destroy()
        for rec in build_recommendations(self.df):
            self._insight_card(self.actions_frame, rec["title"], rec["detail"], rec["impact"])

    def _append_chat(self, sender: str, message: str):
        self.chat_history.configure(state="normal")
        self.chat_history.insert("end", f"{sender}\n", ("sender",))
        self.chat_history.insert("end", f"{message}\n\n", ("message",))
        self.chat_history.configure(state="disabled")
        self.chat_history.see("end")

    def _ask_prompt(self, question: str):
        self.chat_entry.delete("1.0", "end")
        self.chat_entry.insert("1.0", question)
        self.send_chat()

    def _send_chat_from_keyboard(self, _event):
        self.send_chat()
        return "break"

    def send_chat(self):
        question = self.chat_entry.get("1.0", "end").strip()
        if not question:
            return
        self.chat_entry.delete("1.0", "end")
        self._append_chat("You", question)
        if self.groq_chat.available():
            context = self.summary if not self.df.empty else "No transaction data has been uploaded."
            answer = self.groq_chat.ask(question, context)
        else:
            answer = build_local_advice(self.df, question)
        self._append_chat(CHAT_NAME, answer)

    def _write_text(self, widget: tk.Text, text: str):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _empty_frame(self, frame, message: str):
        for widget in frame.winfo_children():
            widget.destroy()
        ttk.Label(frame, text=message, style="Panel.TLabel", foreground=self.colors["muted"]).pack(anchor="w", pady=12)


def main():
    root = tk.Tk()
    PersonalFinanceAdvisor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
