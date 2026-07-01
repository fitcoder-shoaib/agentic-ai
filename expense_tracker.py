"""
Expense Tracker - Tkinter desktop app.

Upload a CSV of expenses, auto-categorize them, view charts, get a
financial summary + savings suggestions, and chat with Groq about your
spending.

Setup:
    pip install -r requirements.txt
    export GROQ_API_KEY=your_key_here   (or put it in a .env file)
    python expense_tracker.py
"""
import os
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

import pandas as pd
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from dotenv import load_dotenv

load_dotenv()

try:
    from groq import Groq
except ImportError:
    Groq = None


# ---------------------------------------------------------------------------
# Categorization
# ---------------------------------------------------------------------------

CATEGORY_KEYWORDS = {
    "Food & Dining": ["restaurant", "cafe", "coffee", "starbucks", "mcdonald",
                       "pizza", "grocery", "supermarket", "food", "diner",
                       "bakery", "bar", "kfc", "burger"],
    "Transport": ["uber", "lyft", "taxi", "fuel", "gas station", "parking",
                  "metro", "transit", "train", "flight", "airline"],
    "Shopping": ["amazon", "walmart", "target", "mall", "store", "shop",
                 "clothing", "electronics"],
    "Utilities": ["electric", "water bill", "gas bill", "internet", "phone",
                  "utility", "cable"],
    "Entertainment": ["netflix", "spotify", "movie", "cinema", "game",
                      "concert", "subscription"],
    "Health": ["pharmacy", "doctor", "hospital", "clinic", "dental",
               "medical", "insurance"],
    "Housing": ["rent", "mortgage", "landlord", "apartment"],
    "Other": [],
}


def categorize(description: str) -> str:
    text = str(description).lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return category
    return "Other"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def find_column(columns, candidates):
    lowered = {c.lower(): c for c in columns}
    for cand in candidates:
        for col_lower, col_orig in lowered.items():
            if cand in col_lower:
                return col_orig
    return None


def load_expenses(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    date_col = find_column(df.columns, ["date"])
    desc_col = find_column(df.columns, ["description", "merchant", "detail", "memo", "narration"])
    amount_col = find_column(df.columns, ["amount", "debit", "value", "cost", "price"])
    category_col = find_column(df.columns, ["category", "type"])

    if amount_col is None:
        raise ValueError("Could not find an amount column in the CSV.")

    out = pd.DataFrame()
    out["date"] = pd.to_datetime(df[date_col], errors="coerce") if date_col else pd.NaT
    out["description"] = df[desc_col] if desc_col else ""
    out["amount"] = pd.to_numeric(df[amount_col], errors="coerce").abs()

    if category_col:
        out["category"] = df[category_col].fillna("Other")
    else:
        out["category"] = out["description"].apply(categorize)

    out = out.dropna(subset=["amount"])
    return out


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def build_summary(df: pd.DataFrame) -> str:
    total = df["amount"].sum()
    by_cat = df.groupby("category")["amount"].sum().sort_values(ascending=False)
    top_cat = by_cat.index[0] if not by_cat.empty else "N/A"
    top_cat_amt = by_cat.iloc[0] if not by_cat.empty else 0

    n_days = 1
    if df["date"].notna().any():
        span = (df["date"].max() - df["date"].min()).days
        n_days = max(span, 1)
    avg_daily = total / n_days

    lines = [
        f"Total spent: ${total:,.2f}",
        f"Number of transactions: {len(df)}",
        f"Average daily spend: ${avg_daily:,.2f}",
        f"Top spending category: {top_cat} (${top_cat_amt:,.2f}, "
        f"{top_cat_amt / total * 100:.1f}% of total)" if total else "",
        "",
        "Spending by category:",
    ]
    for cat, amt in by_cat.items():
        pct = amt / total * 100 if total else 0
        lines.append(f"  - {cat}: ${amt:,.2f} ({pct:.1f}%)")

    lines.append("")
    lines.append("Savings suggestions:")
    suggestions = suggest_savings(df, by_cat, total)
    for s in suggestions:
        lines.append(f"  - {s}")

    return "\n".join(l for l in lines if l is not None)


def suggest_savings(df: pd.DataFrame, by_cat: pd.Series, total: float) -> list:
    suggestions = []
    if total == 0 or by_cat.empty:
        return ["Not enough data to suggest savings yet."]

    for cat, amt in by_cat.items():
        pct = amt / total * 100
        if pct >= 30:
            suggestions.append(
                f"{cat} takes up {pct:.0f}% of spending - look for ways to trim it."
            )

    if "Entertainment" in by_cat.index:
        subs = df[df["category"] == "Entertainment"]
        if len(subs) >= 3:
            suggestions.append(
                "Multiple entertainment/subscription charges detected - "
                "review for unused subscriptions."
            )

    if "Food & Dining" in by_cat.index:
        dining = by_cat.get("Food & Dining", 0)
        if dining / total > 0.2:
            suggestions.append(
                "Dining out is a large share of spending - cooking at home "
                "more often could cut this significantly."
            )

    if not suggestions:
        suggestions.append("Spending looks fairly balanced across categories - "
                            "keep tracking to catch trends early.")

    return suggestions


# ---------------------------------------------------------------------------
# Groq chat
# ---------------------------------------------------------------------------

class GroqChat:
    def __init__(self):
        self.client = None
        api_key = os.environ.get("GROQ_API_KEY")
        if Groq is not None and api_key:
            self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"

    def available(self) -> bool:
        return self.client is not None

    def ask(self, question: str, context: str) -> str:
        if not self.available():
            return ("Groq API key not configured. Set the GROQ_API_KEY "
                    "environment variable (or a .env file) and restart the app.")
        system_prompt = (
            "You are a helpful personal finance assistant. Answer questions "
            "about the user's expenses using ONLY the summary data provided "
            "below. Be concise and practical.\n\n" + context
        )
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question},
                ],
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"Error contacting Groq: {e}"


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

class ExpenseTrackerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Expense Tracker")
        self.root.geometry("1000x700")

        self.df = pd.DataFrame()
        self.groq_chat = GroqChat()

        self._build_toolbar()
        self._build_tabs()

    # -- layout -------------------------------------------------------

    def _build_toolbar(self):
        bar = ttk.Frame(self.root)
        bar.pack(fill="x", padx=8, pady=8)
        ttk.Button(bar, text="Upload CSV", command=self.upload_csv).pack(side="left")
        self.status_label = ttk.Label(bar, text="No file loaded")
        self.status_label.pack(side="left", padx=10)

    def _build_tabs(self):
        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill="both", expand=True, padx=8, pady=8)

        self.tab_data = ttk.Frame(self.tabs)
        self.tab_charts = ttk.Frame(self.tabs)
        self.tab_summary = ttk.Frame(self.tabs)
        self.tab_chat = ttk.Frame(self.tabs)

        self.tabs.add(self.tab_data, text="Expenses")
        self.tabs.add(self.tab_charts, text="Charts")
        self.tabs.add(self.tab_summary, text="Summary")
        self.tabs.add(self.tab_chat, text="Chat (Groq)")

        self._build_data_tab()
        self._build_charts_tab()
        self._build_summary_tab()
        self._build_chat_tab()

    def _build_data_tab(self):
        columns = ("date", "description", "category", "amount")
        self.tree = ttk.Treeview(self.tab_data, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col.capitalize())
            self.tree.column(col, width=150)
        self.tree.pack(fill="both", expand=True)

    def _build_charts_tab(self):
        self.charts_frame = ttk.Frame(self.tab_charts)
        self.charts_frame.pack(fill="both", expand=True)
        self.charts_placeholder = ttk.Label(
            self.charts_frame, text="Upload a CSV to see charts."
        )
        self.charts_placeholder.pack(pady=20)

    def _build_summary_tab(self):
        self.summary_text = tk.Text(self.tab_summary, wrap="word")
        self.summary_text.pack(fill="both", expand=True)
        self.summary_text.insert("1.0", "Upload a CSV to see your summary.")
        self.summary_text.configure(state="disabled")

    def _build_chat_tab(self):
        self.chat_history = tk.Text(self.tab_chat, wrap="word", state="disabled")
        self.chat_history.pack(fill="both", expand=True, padx=4, pady=4)

        entry_frame = ttk.Frame(self.tab_chat)
        entry_frame.pack(fill="x", padx=4, pady=4)

        self.chat_entry = ttk.Entry(entry_frame)
        self.chat_entry.pack(side="left", fill="x", expand=True)
        self.chat_entry.bind("<Return>", lambda e: self.send_chat())

        ttk.Button(entry_frame, text="Send", command=self.send_chat).pack(side="left", padx=4)

        if not self.groq_chat.available():
            self._append_chat("System", "GROQ_API_KEY not set - chat replies "
                                          "will show a setup reminder until it's configured.")

    # -- actions --------------------------------------------------------

    def upload_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        try:
            self.df = load_expenses(path)
        except Exception as e:
            messagebox.showerror("Error loading CSV", str(e))
            return

        self.status_label.config(text=f"Loaded {len(self.df)} transactions from {os.path.basename(path)}")
        self._refresh_data_tab()
        self._refresh_charts()
        self._refresh_summary()

    def _refresh_data_tab(self):
        self.tree.delete(*self.tree.get_children())
        for _, row in self.df.iterrows():
            date_str = row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else ""
            self.tree.insert("", "end", values=(date_str, row["description"],
                                                 row["category"], f"{row['amount']:.2f}"))

    def _refresh_charts(self):
        for widget in self.charts_frame.winfo_children():
            widget.destroy()

        if self.df.empty:
            return

        fig, axes = plt.subplots(1, 2, figsize=(9, 4))

        by_cat = self.df.groupby("category")["amount"].sum().sort_values(ascending=False)
        axes[0].pie(by_cat.values, labels=by_cat.index, autopct="%1.0f%%")
        axes[0].set_title("Spending by Category")

        if self.df["date"].notna().any():
            monthly = (
                self.df.dropna(subset=["date"])
                .set_index("date")
                .resample("ME")["amount"]
                .sum()
            )
            axes[1].bar(monthly.index.strftime("%Y-%m"), monthly.values)
            axes[1].set_title("Monthly Spending")
            axes[1].tick_params(axis="x", rotation=45)
        else:
            axes[1].text(0.5, 0.5, "No date column found", ha="center")

        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.charts_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def _refresh_summary(self):
        self.summary = build_summary(self.df) if not self.df.empty else "No data."
        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", "end")
        self.summary_text.insert("1.0", self.summary)
        self.summary_text.configure(state="disabled")

    def _append_chat(self, sender: str, message: str):
        self.chat_history.configure(state="normal")
        self.chat_history.insert("end", f"{sender}: {message}\n\n")
        self.chat_history.configure(state="disabled")
        self.chat_history.see("end")

    def send_chat(self):
        question = self.chat_entry.get().strip()
        if not question:
            return
        self.chat_entry.delete(0, "end")
        self._append_chat("You", question)

        context = self.summary if not self.df.empty else "No expense data has been uploaded yet."
        answer = self.groq_chat.ask(question, context)
        self._append_chat("Groq", answer)


def main():
    root = tk.Tk()
    ExpenseTrackerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
