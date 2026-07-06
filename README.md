# Finguide

Smarter money moves, beautifully guided.

## Summary

Finguide is a Netlify-ready React/Vite finance dashboard for CSV transaction files. It normalizes common bank and card exports, shows spending metrics and charts, lets users filter transactions, builds savings recommendations, and includes ThinkDesk, an AI finance chat assistant backed by a Netlify serverless function.

The primary application is the web app in `src/`. Older Python versions are kept in `legacy/` for reference and learning, while sample data lives in `examples/`.

## Project Structure

```text
.
├── README.md
├── index.html
├── package.json
├── package-lock.json
├── vite.config.js
├── netlify.toml
├── .env.example
├── examples/
│   └── sample_expenses_basic.csv
├── legacy/
│   ├── basic_expense_tracker.py
│   ├── expense_tracker.py
│   ├── requirements.txt
│   └── streamlit_app.py
├── netlify/
│   └── functions/
│       └── thinkdesk.js
└── src/
    ├── main.jsx
    └── styles.css
```

Generated folders such as `node_modules/`, `dist/`, Python virtual environments, bytecode caches, and local OS/cache files are intentionally excluded from the repository.

## Main Features

- Upload CSV files and analyze transactions in the browser.
- Detect dates, descriptions, amounts, categories, and transaction direction from flexible column names.
- Separate income and expenses when transaction type/direction data is available.
- Show overview metrics, category breakdowns, monthly trends, transaction search/filtering, and savings strategy.
- Use ThinkDesk through `/api/thinkdesk`, with Groq API calls kept server-side in Netlify Functions.
- Fall back to local guidance when `GROQ_API_KEY` is not configured.

## Requirements

### Web App

- Node.js 18 or newer
- npm
- Optional Groq API key for live ThinkDesk responses

### Legacy Python Apps

- Python 3.10 or newer
- `pip`
- Optional Groq API key for the chat features

Python dependencies are listed in `legacy/requirements.txt`.

## Web App Setup

Install dependencies:

```bash
npm install
```

Run the local development server:

```bash
npm run dev
```

Build for production:

```bash
npm run build
```

Preview the production build locally:

```bash
npm run preview
```

## ThinkDesk Setup

ThinkDesk calls the Netlify function at `/api/thinkdesk`. That route is mapped in `netlify.toml` to `netlify/functions/thinkdesk.js`.

For local or deployed AI responses, set:

```bash
GROQ_API_KEY=your_groq_api_key_here
```

Copy `.env.example` to `.env` for local development if needed. Never place `GROQ_API_KEY` directly in React frontend code. The browser app sends the finance summary and user question to the serverless function, and the function reads the key from environment variables.

If the key is missing, ThinkDesk returns a local guidance message and the React app can still provide rule-based advice.

## Netlify Deployment

1. Push this repository to GitHub.
2. Create a new Netlify site from the repository.
3. Use these build settings:
   - Build command: `npm run build`
   - Publish directory: `dist`
   - Functions directory: `netlify/functions`
4. Add `GROQ_API_KEY` in Netlify environment variables if live ThinkDesk responses are desired.

The existing `netlify.toml` already includes the build settings, the ThinkDesk API redirect, and the single-page app fallback route.

## CSV Format

Finguide accepts flexible CSV exports, but these columns work best:

- `Date`
- `Description` or `Merchant`
- `Amount`
- `Category`
- `Type`, `Transaction Type`, or `Direction`

If the file has a type or direction column, values such as credit, debit, income, expense, deposit, withdrawal, `cr`, or `dr` help Finguide classify rows. If every amount is positive and no type/direction column exists, rows are treated as expenses unless the category is `Income`.

Amounts are displayed in Indian rupees.

## Legacy Python Apps

The Python apps are optional and are not required for the React/Vite web app.

Set up the legacy environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r legacy/requirements.txt
```

Run the polished Tkinter version:

```bash
python legacy/expense_tracker.py
```

Run the Streamlit prototype:

```bash
streamlit run legacy/streamlit_app.py
```

Run the beginner Tkinter example:

```bash
python legacy/basic_expense_tracker.py
```

Use `examples/sample_expenses_basic.csv` when trying the beginner example.
