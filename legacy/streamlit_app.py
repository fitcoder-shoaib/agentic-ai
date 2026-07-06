"""
Finguide - modern Streamlit finance dashboard.

Run from the project root:
    streamlit run legacy/streamlit_app.py
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

try:
    from groq import Groq
except ImportError:
    Groq = None


APP_NAME = "Finguide"
APP_SLOGAN = "Smarter money moves, beautifully guided."
CHAT_NAME = "ThinkDesk"

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

CHART_COLORS = ["#8b5cf6", "#06b6d4", "#f97316", "#ec4899", "#22c55e", "#2563eb", "#facc15", "#14b8a6", "#ef4444"]


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


def money_compact(value: float) -> str:
    value = float(value)
    absolute = abs(value)
    if absolute >= 10_000_000:
        return f"Rs. {value / 10_000_000:.1f}Cr"
    if absolute >= 100_000:
        return f"Rs. {value / 100_000:.1f}L"
    if absolute >= 1_000:
        return f"Rs. {value / 1_000:.0f}K"
    return f"Rs. {value:,.0f}"


def pct(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:.1f}%"


def parse_money_input(value: str, default: float = 10000) -> float:
    cleaned = (
        str(value)
        .replace(",", "")
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
        if any(keyword in text for keyword in keywords):
            return category
    return "Other"


def normalize_amounts(df: pd.DataFrame, amount_col: str, type_col: str | None) -> pd.Series:
    raw_amount = pd.to_numeric(
        df[amount_col]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("$", "", regex=False)
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


def load_expenses(uploaded_file) -> pd.DataFrame:
    df = pd.read_csv(uploaded_file)
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
    out["category"] = df[category_col].fillna("Other").astype(str).str.strip().replace("", "Other") if category_col else out["description"].apply(categorize)

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
    return max((dated["date"].max() - dated["date"].min()).days + 1, 1)


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


def compute_metrics(df: pd.DataFrame) -> FinanceMetrics:
    expenses = expense_rows(df)
    income = income_rows(df)
    total_spend = float(expenses["amount"].sum())
    total_income = float(income["amount"].sum())
    by_cat = expenses.groupby("category")["amount"].sum().sort_values(ascending=False)
    top_category = by_cat.index[0] if not by_cat.empty else "N/A"
    top_category_amount = float(by_cat.iloc[0]) if not by_cat.empty else 0.0
    days = date_span_days(df)
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
        recurring_monthly=estimate_recurring(expenses),
        projected_monthly_spend=total_spend / days * 30,
        savings_rate=((total_income - total_spend) / total_income * 100) if total_income else None,
        date_min=dated["date"].min() if not dated.empty else None,
        date_max=dated["date"].max() if not dated.empty else None,
    )


def build_recommendations(df: pd.DataFrame) -> list[dict[str, str]]:
    if df.empty:
        return []
    expenses = expense_rows(df)
    metrics = compute_metrics(df)
    by_cat = expenses.groupby("category")["amount"].sum().sort_values(ascending=False)
    recommendations: list[dict[str, str]] = []

    if metrics.savings_rate is not None and metrics.savings_rate < 10:
        recommendations.append(
            {
                "title": "Protect the savings rate first",
                "impact": "High",
                "detail": f"Your estimated savings rate is {pct(metrics.savings_rate)}. Aim for 15-20% by setting an automatic transfer before discretionary spending starts.",
            }
        )
    elif metrics.savings_rate is not None and metrics.savings_rate >= 20:
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
                    "detail": f"{metrics.top_category} is {top_share:.0f}% of spending. A 12% reduction could free about {money(trim)}.",
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
                "detail": f"Detected {len(subscriptions)} likely recurring charges totaling {money(float(subscriptions['amount'].sum()))}.",
            }
        )

    if metrics.projected_monthly_spend > metrics.total_income > 0:
        recommendations.append(
            {
                "title": "Projected spending is above income",
                "impact": "High",
                "detail": f"Projected monthly spend is {money(metrics.projected_monthly_spend)} against income of {money(metrics.total_income)}.",
            }
        )

    if not recommendations:
        recommendations.append(
            {
                "title": "Spending mix looks balanced",
                "impact": "Low",
                "detail": "No major imbalance jumped out. Keep uploading monthly statements so category drift becomes visible early.",
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
        return f"Latest monthly spend is {money(float(monthly.iloc[-1]))}. Average monthly spend is {money(float(monthly.mean()))}."
    return (
        f"Total spending is {money(metrics.total_spend)} with projected monthly spend of "
        f"{money(metrics.projected_monthly_spend)}. Top category is {metrics.top_category} "
        f"at {money(metrics.top_category_amount)}. Estimated savings rate: {pct(metrics.savings_rate)}."
    )


def ask_groq(question: str, context: str) -> str | None:
    api_key = os.environ.get("GROQ_API_KEY")
    if Groq is None or not api_key:
        return None
    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are ThinkDesk, a careful personal finance guide. Use only the provided transaction "
                        "summary. Give concrete, kind, non-judgmental advice. Do not provide tax, legal, "
                        "or investment guarantees.\n\n"
                        + context
                    ),
                },
                {"role": "user", "content": question},
            ],
        )
        return response.choices[0].message.content
    except Exception as exc:
        return f"Could not contact Groq: {exc}"


def apply_styles():
    st.markdown(
        """
        <style>
        :root {
            --bg: #0f1024;
            --panel: rgba(28, 26, 53, 0.86);
            --panel-soft: rgba(52, 42, 96, 0.72);
            --ink: #fbfaff;
            --muted: #b8add2;
            --accent: #a78bfa;
            --cyan: #22d3ee;
            --gold: #facc15;
            --orange: #fb923c;
        }
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(167, 139, 250, 0.30), transparent 32rem),
                radial-gradient(circle at 80% 6%, rgba(34, 211, 238, 0.20), transparent 26rem),
                linear-gradient(135deg, #0f1024 0%, #171333 54%, #111827 100%);
            color: var(--ink);
        }
        .block-container {
            max-width: 1240px;
            padding-top: 2.2rem;
        }
        .hero {
            padding: 2.4rem 2.5rem;
            border: 1px solid rgba(255, 255, 255, 0.10);
            background: linear-gradient(135deg, rgba(36, 22, 63, 0.98), rgba(36, 32, 84, 0.88));
            box-shadow: 0 30px 90px rgba(0, 0, 0, 0.30);
            border-radius: 22px;
            margin-bottom: 1.2rem;
        }
        .hero h1 {
            margin: 0;
            font-size: 4rem;
            line-height: 1;
            letter-spacing: 0;
        }
        .slogan {
            margin-top: .55rem;
            color: var(--gold);
            font-size: 1.35rem;
            font-weight: 800;
        }
        .subcopy {
            color: #ddd6fe;
            margin-top: .8rem;
            font-size: 1.02rem;
        }
        .metric-card {
            padding: 1.2rem 1.25rem;
            border-radius: 18px;
            background: var(--panel);
            border: 1px solid rgba(255, 255, 255, 0.10);
            min-height: 120px;
        }
        .metric-label {
            color: var(--muted);
            font-size: .78rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: .08em;
        }
        .metric-value {
            color: var(--ink);
            font-size: 1.75rem;
            font-weight: 900;
            margin-top: .45rem;
        }
        .pill {
            display: inline-block;
            padding: .35rem .65rem;
            border-radius: 999px;
            font-size: .76rem;
            font-weight: 800;
            background: rgba(167, 139, 250, .18);
            color: #ddd6fe;
        }
        .rec-card {
            padding: 1rem 1.15rem;
            background: var(--panel-soft);
            border: 1px solid rgba(255, 255, 255, .10);
            border-radius: 16px;
            margin-bottom: .75rem;
        }
        .rec-card h4 {
            margin: .35rem 0;
            font-size: 1.05rem;
        }
        .rec-card p {
            color: var(--muted);
            margin: 0;
        }
        div[data-testid="stTabs"] button {
            border-radius: 999px;
            padding: .85rem 1.2rem;
            font-weight: 800;
            color: #d8ceff;
        }
        div[data-testid="stTabs"] button:hover {
            background: linear-gradient(135deg, rgba(167,139,250,.28), rgba(34,211,238,.16));
            color: #ffffff;
        }
        div[data-testid="stTextArea"] textarea {
            min-height: 120px;
            border-radius: 18px;
            font-size: 1.02rem;
            padding: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def draw_category_chart(by_cat: pd.Series):
    fig, ax = plt.subplots(figsize=(10, 5.8), facecolor="#18172f")
    ax.set_facecolor("#18172f")
    top = by_cat.head(8).sort_values()
    ax.barh(top.index, top.values, color=CHART_COLORS[: len(top)])
    ax.set_title("Top spending categories", loc="left", color="#fbfaff", fontsize=16, fontweight="bold", pad=14)
    ax.tick_params(colors="#b8add2", labelsize=11)
    ax.xaxis.set_major_formatter(lambda value, _pos: money_compact(value))
    ax.grid(axis="x", color="#302a4d", linewidth=1)
    for spine in ax.spines.values():
        spine.set_visible(False)
    st.pyplot(fig, clear_figure=True)


def draw_trend_chart(expenses: pd.DataFrame):
    dated = expenses.dropna(subset=["date"])
    if dated.empty:
        st.info("No usable date column found for trend analysis.")
        return
    monthly = dated.set_index("date").resample("ME")["amount"].sum()
    fig, ax = plt.subplots(figsize=(10, 5.8), facecolor="#18172f")
    ax.set_facecolor("#18172f")
    ax.plot(monthly.index, monthly.values, color="#22d3ee", marker="o", linewidth=3)
    ax.fill_between(monthly.index, monthly.values, color="#22d3ee", alpha=.16)
    ax.set_title("Monthly spending trend", loc="left", color="#fbfaff", fontsize=16, fontweight="bold", pad=14)
    ax.tick_params(colors="#b8add2", labelsize=11)
    ax.yaxis.set_major_formatter(lambda value, _pos: money_compact(value))
    ax.grid(axis="y", color="#302a4d", linewidth=1)
    for spine in ax.spines.values():
        spine.set_visible(False)
    st.pyplot(fig, clear_figure=True)


def render_overview(df: pd.DataFrame):
    metrics = compute_metrics(df)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Total Spend", money(metrics.total_spend))
    with col2:
        metric_card("Net Cash Flow", money(metrics.net_cashflow))
    with col3:
        metric_card("Savings Rate", pct(metrics.savings_rate))
    with col4:
        metric_card("Projected Monthly", money(metrics.projected_monthly_spend))

    st.write("")
    left, right = st.columns([1.05, .95], gap="large")
    with left:
        st.subheader("Priority Insights")
        for rec in build_recommendations(df):
            st.markdown(
                f"""
                <div class="rec-card">
                    <span class="pill">{rec['impact']} impact</span>
                    <h4>{rec['title']}</h4>
                    <p>{rec['detail']}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
    with right:
        st.subheader("Financial Snapshot")
        st.code(build_summary_text(df), language="text")


def render_visuals(df: pd.DataFrame):
    expenses = expense_rows(df)
    by_cat = expenses.groupby("category")["amount"].sum().sort_values(ascending=False)
    view = st.radio("View", ["Categories", "Trend"], horizontal=True)
    if view == "Trend":
        draw_trend_chart(expenses)
    else:
        draw_category_chart(by_cat)


def render_transactions(df: pd.DataFrame):
    query = st.text_input("Search transactions", placeholder="Merchant, note, category...")
    categories = ["All"] + sorted(df["category"].dropna().unique().tolist())
    category = st.selectbox("Category", categories)
    filtered = df.copy()
    if query:
        filtered = filtered[filtered["description"].str.lower().str.contains(re.escape(query.lower()), na=False)]
    if category != "All":
        filtered = filtered[filtered["category"] == category]
    table = filtered[["date", "description", "category", "kind", "amount"]].copy()
    table["date"] = table["date"].dt.strftime("%Y-%m-%d").fillna("")
    table["amount"] = table["amount"].map(money)
    st.dataframe(table, use_container_width=True, height=520)


def render_strategy(df: pd.DataFrame):
    goal_text = st.text_input("Monthly savings target", value="10,000")
    goal = parse_money_input(goal_text)
    metrics = compute_metrics(df)
    expenses = expense_rows(df)
    by_cat = expenses.groupby("category")["amount"].sum().sort_values(ascending=False)
    available_cash = max(metrics.net_cashflow, 0.0)
    remaining = max(goal - available_cash, 0.0)
    st.markdown(f"### Target: {money(goal)}")
    if remaining <= 0:
        st.success("You are already on track for this goal based on the uploaded data. Automate the transfer and protect it from discretionary spending.")
        return
    st.warning(f"You need to create roughly {money(remaining)} more monthly room.")
    st.subheader("A practical split")
    top_three = by_cat.head(3)
    if top_three.empty:
        st.info("Upload expense data with categories to get a sharper plan.")
        return
    per_bucket = remaining / len(top_three)
    for category, amount in top_three.items():
        trim_pct = min(per_bucket / amount * 100, 30) if amount else 0
        st.markdown(f"- Trim **{category}** by about **{pct(trim_pct)}** to free **{money(min(per_bucket, amount * 0.3))}**")


def render_chat(df: pd.DataFrame):
    st.subheader(CHAT_NAME)
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": CHAT_NAME,
                "content": "Upload a CSV and ask me about savings, categories, monthly trends, or spending patterns.",
            }
        ]
    for message in st.session_state.messages:
        with st.chat_message("assistant" if message["role"] == CHAT_NAME else "user"):
            st.markdown(message["content"])

    with st.form("thinkdesk_form", clear_on_submit=True):
        question = st.text_area("Message ThinkDesk", height=130, placeholder="Ask a bigger question here...")
        submitted = st.form_submit_button("Send to ThinkDesk", use_container_width=True)
    if submitted and question.strip():
        user_question = question.strip()
        st.session_state.messages.append({"role": "You", "content": user_question})
        context = build_summary_text(df) if not df.empty else "No transaction data has been uploaded."
        answer = ask_groq(user_question, context) or build_local_advice(df, user_question)
        st.session_state.messages.append({"role": CHAT_NAME, "content": answer})
        st.rerun()


def main():
    st.set_page_config(page_title=APP_NAME, page_icon="F", layout="wide")
    apply_styles()
    st.markdown(
        f"""
        <section class="hero">
            <h1>{APP_NAME}</h1>
            <div class="slogan">{APP_SLOGAN}</div>
            <div class="subcopy">A modern finance dashboard with vivid insights, elegant charts, and {CHAT_NAME} built in.</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader("Upload your transaction CSV", type=["csv"])
    if uploaded is None:
        st.info("Upload a CSV to open the dashboard.")
        st.stop()

    try:
        df = load_expenses(uploaded)
    except Exception as exc:
        st.error(f"Could not load CSV: {exc}")
        st.stop()
    if df.empty:
        st.warning("The CSV loaded, but no valid transactions were found.")
        st.stop()

    tabs = st.tabs(["Overview", "Visuals", "Transactions", "Strategy", CHAT_NAME])
    with tabs[0]:
        render_overview(df)
    with tabs[1]:
        render_visuals(df)
    with tabs[2]:
        render_transactions(df)
    with tabs[3]:
        render_strategy(df)
    with tabs[4]:
        render_chat(df)


if __name__ == "__main__":
    main()
