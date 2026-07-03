Finguide

Smarter money moves, beautifully guided.

Finguide is now a Netlify-ready React/Vite finance dashboard. It turns CSV
transactions into spending insights, visual summaries, savings strategy, and
ThinkDesk chat.

Run the upgraded web app locally:
    npm install
    npm run dev

Build for production:
    npm run build

Deploy on Netlify:
    1. Push this folder to GitHub.
    2. Create a new Netlify site from the repo.
    3. Use these build settings:
        Build command: npm run build
        Publish directory: dist
    4. Add this environment variable in Netlify:
        GROQ_API_KEY=your_groq_api_key_here

ThinkDesk API key safety:
    Do not put GROQ_API_KEY in React frontend code.
    The React app calls /api/thinkdesk.
    Netlify redirects that to netlify/functions/thinkdesk.js.
    The function reads GROQ_API_KEY from Netlify environment variables, so the
    key stays server-side.

CSV support:
    Finguide looks for flexible column names, so most bank/card exports work.
    Recommended columns:
        Date
        Description or Merchant
        Amount
        Category
        Type, Transaction Type, or Direction

    All calculations and displays are in Indian rupees.
    Positive-only files are treated as expenses unless the Category is Income.
    Files with Type/Direction columns can distinguish income from expenses.

Main files:
    src/main.jsx                  React app, CSV logic, charts, ThinkDesk UI
    src/styles.css                Modern interface styling
    netlify/functions/thinkdesk.js Secure Groq serverless function
    netlify.toml                  Netlify build + API redirect config
    package.json                  React/Vite dependencies and scripts

Legacy Python versions:
    expense_tracker.py is the Tkinter desktop interface.
    streamlit_app.py is the Streamlit prototype.
    basic_expense_tracker.py is the beginner learning example.
