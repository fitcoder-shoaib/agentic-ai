"""
Basic Expense Tracker (Tkinter + Pandas + Matplotlib + Groq)

A simple beginner-friendly project.

How to use:
1. Make a CSV file with these columns: Date, Category, Description, Amount
   (see sample_expenses_basic.csv for an example)
2. Run this file: python basic_expense_tracker.py
3. Click "Load CSV" and pick your file.
4. Use the buttons to see charts, a summary, or chat with Groq.

Before using the chat feature, set your Groq API key:
    export GROQ_API_KEY=your_key_here
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox

import pandas as pd
import matplotlib.pyplot as plt

from groq import Groq


# ------------------------------------------------------------------
# Global variables (simple approach - no classes needed)
# ------------------------------------------------------------------

expenses_df = None  # will hold our data after loading the CSV


# ------------------------------------------------------------------
# Step 1: Load the CSV file
# ------------------------------------------------------------------

def load_csv():
    global expenses_df

    file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if not file_path:
        return

    try:
        df = pd.read_csv(file_path)

        # Clean up column names: remove extra spaces and fix capitalization
        # e.g. "category" or " Amount " both become "Category" / "Amount"
        df.columns = [col.strip().capitalize() for col in df.columns]

        required_columns = ["Date", "Category", "Description", "Amount"]
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            messagebox.showerror(
                "Missing columns",
                f"Your CSV is missing these columns: {', '.join(missing)}\n\n"
                f"Found columns: {', '.join(df.columns)}\n\n"
                f"Please make sure your CSV has: {', '.join(required_columns)}"
            )
            return

        df["Amount"] = pd.to_numeric(df["Amount"])
        expenses_df = df
        status_label.config(text=f"Loaded {len(df)} expenses from {os.path.basename(file_path)}")
    except Exception as e:
        messagebox.showerror("Error", f"Could not read file:\n{e}")


# ------------------------------------------------------------------
# Step 2: Show a pie chart of spending by category
# ------------------------------------------------------------------

def show_pie_chart():
    if expenses_df is None:
        messagebox.showwarning("No data", "Please load a CSV file first.")
        return

    totals_by_category = expenses_df.groupby("Category")["Amount"].sum()

    plt.figure()
    plt.pie(totals_by_category, labels=totals_by_category.index, autopct="%1.1f%%")
    plt.title("Spending by Category")
    plt.show()


# ------------------------------------------------------------------
# Step 3: Show a bar chart of spending by category
# ------------------------------------------------------------------

def show_bar_chart():
    if expenses_df is None:
        messagebox.showwarning("No data", "Please load a CSV file first.")
        return

    totals_by_category = expenses_df.groupby("Category")["Amount"].sum()

    plt.figure()
    plt.bar(totals_by_category.index, totals_by_category.values)
    plt.title("Spending by Category")
    plt.ylabel("Amount Spent")
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.show()


# ------------------------------------------------------------------
# Step 4: Print a simple summary
# ------------------------------------------------------------------

def show_summary():
    if expenses_df is None:
        messagebox.showwarning("No data", "Please load a CSV file first.")
        return

    total = expenses_df["Amount"].sum()
    totals_by_category = expenses_df.groupby("Category")["Amount"].sum().sort_values(ascending=False)
    top_category = totals_by_category.index[0]
    top_amount = totals_by_category.iloc[0]

    summary_lines = []
    summary_lines.append(f"Total Spent: {total:.2f}")
    summary_lines.append(f"Number of Expenses: {len(expenses_df)}")
    summary_lines.append(f"Top Category: {top_category} ({top_amount:.2f})")
    summary_lines.append("")
    summary_lines.append("Spending by Category:")
    for category, amount in totals_by_category.items():
        percent = (amount / total) * 100
        summary_lines.append(f"  {category}: {amount:.2f} ({percent:.1f}%)")

    # Very basic savings tip: warn if one category is more than 40% of spending
    summary_lines.append("")
    if top_amount / total > 0.4:
        summary_lines.append(f"Tip: {top_category} is over 40% of your spending. Try to cut back here!")
    else:
        summary_lines.append("Tip: Your spending looks fairly balanced across categories.")

    summary_text.delete("1.0", tk.END)
    summary_text.insert(tk.END, "\n".join(summary_lines))


# ------------------------------------------------------------------
# Step 5: Chat with Groq about the expenses
# ------------------------------------------------------------------

def ask_groq():
    if expenses_df is None:
        messagebox.showwarning("No data", "Please load a CSV file first.")
        return

    question = chat_entry.get()
    if question.strip() == "":
        return

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        chat_output.insert(tk.END, "\nBot: GROQ_API_KEY is not set. Please set it and restart the app.\n")
        return

    # Build a short text summary of the expenses to give Groq some context
    total = expenses_df["Amount"].sum()
    totals_by_category = expenses_df.groupby("Category")["Amount"].sum()
    context = f"Total spending: {total:.2f}\nSpending by category:\n{totals_by_category.to_string()}"

    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that answers questions about a user's expenses. Use the data below.\n\n" + context},
            {"role": "user", "content": question},
        ],
    )

    answer = response.choices[0].message.content

    chat_output.insert(tk.END, f"\nYou: {question}\n")
    chat_output.insert(tk.END, f"Bot: {answer}\n")
    chat_entry.delete(0, tk.END)


# ------------------------------------------------------------------
# Step 6: Build the Tkinter window
# ------------------------------------------------------------------

window = tk.Tk()
window.title("Basic Expense Tracker")
window.geometry("600x600")

# Top section - load CSV
top_frame = tk.Frame(window)
top_frame.pack(pady=10)

load_button = tk.Button(top_frame, text="Load CSV", command=load_csv)
load_button.pack(side=tk.LEFT, padx=5)

status_label = tk.Label(top_frame, text="No file loaded")
status_label.pack(side=tk.LEFT, padx=5)

# Middle section - chart and summary buttons
button_frame = tk.Frame(window)
button_frame.pack(pady=5)

pie_button = tk.Button(button_frame, text="Pie Chart", command=show_pie_chart)
pie_button.pack(side=tk.LEFT, padx=5)

bar_button = tk.Button(button_frame, text="Bar Chart", command=show_bar_chart)
bar_button.pack(side=tk.LEFT, padx=5)

summary_button = tk.Button(button_frame, text="Show Summary", command=show_summary)
summary_button.pack(side=tk.LEFT, padx=5)

# Summary text box
summary_text = tk.Text(window, height=12, width=65)
summary_text.pack(pady=10)

# Chat section
chat_label = tk.Label(window, text="Chat with Groq about your expenses:")
chat_label.pack()

chat_output = tk.Text(window, height=10, width=65)
chat_output.pack(pady=5)

chat_frame = tk.Frame(window)
chat_frame.pack(pady=5)

chat_entry = tk.Entry(chat_frame, width=50)
chat_entry.pack(side=tk.LEFT, padx=5)

ask_button = tk.Button(chat_frame, text="Ask", command=ask_groq)
ask_button.pack(side=tk.LEFT)

window.mainloop()
