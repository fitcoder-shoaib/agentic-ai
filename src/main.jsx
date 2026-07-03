import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import Papa from "papaparse";
import { motion, AnimatePresence } from "framer-motion";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  ArrowUpRight,
  Bot,
  Brain,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  Filter,
  LineChart,
  MessageSquareText,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Target,
  Upload,
  WalletCards,
} from "lucide-react";
import "./styles.css";

const APP_NAME = "Finguide";
const CHAT_NAME = "ThinkDesk";
const SLOGAN = "Smarter money moves, beautifully guided.";
const CHART_COLORS = ["#8b5cf6", "#06b6d4", "#f97316", "#ec4899", "#22c55e", "#2563eb", "#facc15", "#14b8a6", "#ef4444"];

const CATEGORY_KEYWORDS = {
  Housing: ["rent", "mortgage", "landlord", "apartment", "hoa", "lease"],
  Groceries: ["grocery", "supermarket", "market", "whole foods", "trader joe", "costco"],
  "Food & Dining": ["restaurant", "cafe", "coffee", "starbucks", "mcdonald", "pizza", "diner", "bakery", "bar", "kfc", "burger", "doordash", "ubereats", "swiggy", "zomato"],
  Transport: ["uber", "lyft", "taxi", "fuel", "gas station", "parking", "metro", "transit", "train", "flight", "airline"],
  Shopping: ["amazon", "walmart", "target", "mall", "store", "shop", "clothing", "electronics", "flipkart"],
  Utilities: ["electric", "water bill", "gas bill", "internet", "phone", "utility", "cable", "broadband"],
  Entertainment: ["netflix", "spotify", "movie", "cinema", "game", "concert", "subscription", "hulu", "disney"],
  Health: ["pharmacy", "doctor", "hospital", "clinic", "dental", "medical", "insurance"],
  Education: ["course", "tuition", "book", "udemy", "coursera", "school", "college"],
  Income: ["salary", "payroll", "deposit", "refund", "interest", "dividend"],
};

const sampleRows = [
  { Date: "2026-01-03", Description: "Salary Deposit", Amount: "95000", Category: "Income", Type: "credit" },
  { Date: "2026-01-04", Description: "Apartment Rent", Amount: "28000", Category: "Housing", Type: "debit" },
  { Date: "2026-01-06", Description: "Big Basket Groceries", Amount: "6200", Category: "Groceries", Type: "debit" },
  { Date: "2026-01-08", Description: "Zomato Dinner", Amount: "1850", Category: "Food & Dining", Type: "debit" },
  { Date: "2026-01-10", Description: "Uber rides", Amount: "1250", Category: "Transport", Type: "debit" },
  { Date: "2026-01-13", Description: "Netflix Subscription", Amount: "649", Category: "Entertainment", Type: "debit" },
  { Date: "2026-01-17", Description: "Amazon Shopping", Amount: "7200", Category: "Shopping", Type: "debit" },
  { Date: "2026-02-03", Description: "Salary Deposit", Amount: "95000", Category: "Income", Type: "credit" },
  { Date: "2026-02-04", Description: "Apartment Rent", Amount: "28000", Category: "Housing", Type: "debit" },
  { Date: "2026-02-08", Description: "Cafe and dining", Amount: "4400", Category: "Food & Dining", Type: "debit" },
  { Date: "2026-02-13", Description: "Phone and internet bill", Amount: "2400", Category: "Utilities", Type: "debit" },
  { Date: "2026-02-19", Description: "Medical pharmacy", Amount: "1900", Category: "Health", Type: "debit" },
];

function App() {
  const [rows, setRows] = useState([]);
  const [fileName, setFileName] = useState("");
  const [activeTab, setActiveTab] = useState("overview");
  const [query, setQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("All");
  const [goal, setGoal] = useState("10000");
  const [messages, setMessages] = useState([
    {
      role: CHAT_NAME,
      content: "Upload a CSV, then ask me about savings, categories, recurring spend, or your monthly trend.",
    },
  ]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [error, setError] = useState("");

  const expenses = useMemo(() => rows.filter((row) => row.kind === "expense"), [rows]);
  const metrics = useMemo(() => computeMetrics(rows), [rows]);
  const categories = useMemo(() => ["All", ...Array.from(new Set(rows.map((row) => row.category))).sort()], [rows]);
  const byCategory = useMemo(() => groupByCategory(expenses), [expenses]);
  const monthly = useMemo(() => monthlyTrend(expenses), [expenses]);
  const recommendations = useMemo(() => buildRecommendations(rows), [rows]);
  const filteredRows = useMemo(() => {
    const cleaned = query.trim().toLowerCase();
    return rows
      .filter((row) => (categoryFilter === "All" ? true : row.category === categoryFilter))
      .filter((row) => (cleaned ? `${row.description} ${row.category} ${row.kind}`.toLowerCase().includes(cleaned) : true))
      .sort((a, b) => (b.date?.getTime?.() || 0) - (a.date?.getTime?.() || 0));
  }, [rows, query, categoryFilter]);
  const summary = useMemo(() => buildSummary(rows, metrics, byCategory), [rows, metrics, byCategory]);

  function handleUpload(file) {
    if (!file) return;
    setError("");
    setFileName(file.name);
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (result) => {
        try {
          const normalized = normalizeRows(result.data);
          if (!normalized.length) {
            setError("The CSV loaded, but no usable transaction rows were found.");
          }
          setRows(normalized);
          setActiveTab("overview");
        } catch (parseError) {
          setError(parseError.message || "Could not parse the CSV.");
        }
      },
      error: (parseError) => setError(parseError.message || "Could not parse the CSV."),
    });
  }

  function loadSampleData() {
    setFileName("sample-finguide-data.csv");
    setRows(normalizeRows(sampleRows));
    setActiveTab("overview");
    setError("");
  }

  async function sendMessage(event) {
    event?.preventDefault();
    const question = chatInput.trim();
    if (!question || chatLoading) return;
    setChatInput("");
    setMessages((current) => [...current, { role: "You", content: question }]);
    setChatLoading(true);

    let answer;
    try {
      const response = await fetch("/api/thinkdesk", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, summary }),
      });
      if (response.ok) {
        const data = await response.json();
        answer = data.answer;
      }
    } catch {
      answer = "";
    }

    if (!answer) {
      answer = localAdvice(rows, question);
    }

    setMessages((current) => [...current, { role: CHAT_NAME, content: answer }]);
    setChatLoading(false);
  }

  return (
    <main className="app-shell">
      <Hero onUpload={handleUpload} onSample={loadSampleData} fileName={fileName} />
      {error ? <div className="notice error">{error}</div> : null}

      {!rows.length ? (
        <EmptyState onSample={loadSampleData} />
      ) : (
        <>
          <MetricStrip metrics={metrics} />
          <nav className="tabs" aria-label="Finguide sections">
            {[
              ["overview", "Overview", WalletCards],
              ["visuals", "Visuals", LineChart],
              ["transactions", "Transactions", Filter],
              ["strategy", "Strategy", Target],
              ["thinkdesk", CHAT_NAME, Brain],
            ].map(([id, label, Icon]) => (
              <button key={id} className={activeTab === id ? "tab active" : "tab"} onClick={() => setActiveTab(id)}>
                <Icon size={18} />
                {label}
              </button>
            ))}
          </nav>

          <AnimatePresence mode="wait">
            <motion.section
              key={activeTab}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.22 }}
              className="tab-panel"
            >
              {activeTab === "overview" && <Overview recommendations={recommendations} summary={summary} byCategory={byCategory} monthly={monthly} />}
              {activeTab === "visuals" && <Visuals byCategory={byCategory} monthly={monthly} expenses={expenses} />}
              {activeTab === "transactions" && (
                <Transactions rows={filteredRows} categories={categories} query={query} setQuery={setQuery} categoryFilter={categoryFilter} setCategoryFilter={setCategoryFilter} />
              )}
              {activeTab === "strategy" && <Strategy metrics={metrics} byCategory={byCategory} goal={goal} setGoal={setGoal} />}
              {activeTab === "thinkdesk" && (
                <ThinkDesk messages={messages} input={chatInput} setInput={setChatInput} onSend={sendMessage} loading={chatLoading} hasRows={Boolean(rows.length)} />
              )}
            </motion.section>
          </AnimatePresence>
        </>
      )}
    </main>
  );
}

function Hero({ onUpload, onSample, fileName }) {
  return (
    <section className="hero">
      <div className="hero-copy">
        <div className="eyebrow">
          <Sparkles size={16} />
          Secure finance intelligence
        </div>
        <h1>{APP_NAME}</h1>
        <p className="slogan">{SLOGAN}</p>
        <p className="hero-text">A premium CSV finance dashboard with vivid analytics, secure ThinkDesk AI, and browser-first privacy.</p>
        <div className="hero-actions">
          <label className="primary-upload">
            <Upload size={18} />
            Upload CSV
            <input type="file" accept=".csv,text/csv" onChange={(event) => onUpload(event.target.files?.[0])} />
          </label>
          <button className="secondary-button" onClick={onSample}>
            <FileSpreadsheet size={18} />
            Try sample data
          </button>
        </div>
        {fileName ? <p className="file-chip">Loaded: {fileName}</p> : null}
      </div>
      <div className="hero-card">
        <div className="hero-card-top">
          <ShieldCheck size={22} />
          <span>Secure by design</span>
        </div>
        <p>Your CSV analysis happens in the browser. ThinkDesk uses a protected assistant connection when live guidance is enabled, so private keys stay out of the app.</p>
        <div className="mini-grid">
          <span>Browser CSV</span>
          <span>Protected assistant</span>
          <span>Live guidance</span>
          <span>Local fallback</span>
        </div>
      </div>
    </section>
  );
}

function EmptyState({ onSample }) {
  return (
    <section className="empty-state">
      <div>
        <h2>Drop in your transactions and let Finguide do the first pass.</h2>
        <p>Upload a bank or card CSV with flexible columns like Date, Description, Amount, Category, and Type.</p>
      </div>
      <button className="primary-button" onClick={onSample}>
        <Sparkles size={18} />
        Open sample dashboard
      </button>
    </section>
  );
}

function MetricStrip({ metrics }) {
  const items = [
    ["Total Spend", money(metrics.totalSpend), "total"],
    ["Net Cash Flow", money(metrics.netCashflow), metrics.netCashflow >= 0 ? "good" : "warn"],
    ["Savings Rate", pct(metrics.savingsRate), metrics.savingsRate >= 15 ? "good" : "warn"],
    ["Projected Monthly", money(metrics.projectedMonthlySpend), "total"],
  ];
  return (
    <section className="metric-strip">
      {items.map(([label, value, tone]) => (
        <div className={`metric-card ${tone}`} key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </section>
  );
}

function Overview({ recommendations, summary, byCategory, monthly }) {
  return (
    <div className="overview-grid">
      <section className="panel">
        <PanelTitle icon={Sparkles} title="Priority Insights" />
        <div className="insight-list">
          {recommendations.map((rec) => (
            <article className="insight-card" key={rec.title}>
              <span className={`impact ${rec.impact.toLowerCase()}`}>{rec.impact} impact</span>
              <h3>{rec.title}</h3>
              <p>{rec.detail}</p>
            </article>
          ))}
        </div>
      </section>
      <section className="panel snapshot-panel">
        <PanelTitle icon={WalletCards} title="Financial Snapshot" />
        <pre>{summary}</pre>
      </section>
      <section className="panel wide-panel">
        <PanelTitle icon={LineChart} title="Spending Pulse" />
        <div className="two-chart-grid">
          <CategoryBar data={byCategory.slice(0, 7)} />
          <TrendArea data={monthly} />
        </div>
      </section>
    </div>
  );
}

function Visuals({ byCategory, monthly, expenses }) {
  const distribution = transactionDistribution(expenses);
  return (
    <div className="visual-grid">
      <section className="panel wide-panel">
        <PanelTitle icon={LineChart} title="Top Categories" />
        <CategoryBar data={byCategory.slice(0, 9)} />
      </section>
      <section className="panel">
        <PanelTitle icon={WalletCards} title="Spending Share" />
        <SharePie data={byCategory.slice(0, 7)} />
      </section>
      <section className="panel">
        <PanelTitle icon={ArrowUpRight} title="Monthly Trend" />
        <TrendArea data={monthly} />
      </section>
      <section className="panel wide-panel">
        <PanelTitle icon={FileSpreadsheet} title="Transaction Size Distribution" />
        <DistributionBar data={distribution} />
      </section>
    </div>
  );
}

function Transactions({ rows, categories, query, setQuery, categoryFilter, setCategoryFilter }) {
  return (
    <section className="panel">
      <PanelTitle icon={Filter} title="Transactions" />
      <div className="toolbar">
        <label className="search-box">
          <Search size={17} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search merchant, category, type..." />
        </label>
        <select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
          {categories.map((category) => (
            <option key={category} value={category}>
              {category}
            </option>
          ))}
        </select>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Description</th>
              <th>Category</th>
              <th>Kind</th>
              <th>Amount</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>{formatDate(row.date)}</td>
                <td>{row.description}</td>
                <td>
                  <span className="category-pill">{row.category}</span>
                </td>
                <td>{titleCase(row.kind)}</td>
                <td className="amount-cell">{money(row.amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Strategy({ metrics, byCategory, goal, setGoal }) {
  const target = parseMoney(goal);
  const availableCash = Math.max(metrics.netCashflow, 0);
  const remaining = Math.max(target - availableCash, 0);
  const topThree = byCategory.slice(0, 3);
  return (
    <div className="strategy-grid">
      <section className="panel">
        <PanelTitle icon={Target} title="Savings Target" />
        <label className="goal-input">
          Monthly goal
          <input value={goal} onChange={(event) => setGoal(event.target.value)} />
        </label>
        <div className="goal-summary">
          <span>Target</span>
          <strong>{money(target)}</strong>
        </div>
        <div className="goal-summary">
          <span>Current room</span>
          <strong>{money(availableCash)}</strong>
        </div>
      </section>
      <section className="panel wide-panel">
        <PanelTitle icon={CheckCircle2} title="Savings Plan" />
        {remaining <= 0 ? (
          <div className="success-box">You are already on track for this goal. Automate the transfer and protect it from discretionary spending.</div>
        ) : (
          <>
            <div className="warning-box">You need to create roughly {money(remaining)} more monthly room.</div>
            <div className="strategy-list">
              {topThree.map((item) => {
                const perBucket = remaining / Math.max(topThree.length, 1);
                const trimPct = item.amount ? Math.min((perBucket / item.amount) * 100, 30) : 0;
                return (
                  <article key={item.category}>
                    <span>{item.category}</span>
                    <strong>Trim about {pct(trimPct)}</strong>
                    <p>Potential room: {money(Math.min(perBucket, item.amount * 0.3))}</p>
                  </article>
                );
              })}
            </div>
          </>
        )}
      </section>
    </div>
  );
}

function ThinkDesk({ messages, input, setInput, onSend, loading, hasRows }) {
  return (
    <section className="panel chat-panel">
      <PanelTitle icon={Bot} title={CHAT_NAME} />
      <div className="chat-shell">
        <div className="messages">
          {messages.map((message, index) => (
            <div className={message.role === "You" ? "message user" : "message assistant"} key={`${message.role}-${index}`}>
              <span>{message.role}</span>
              <p>{message.content}</p>
            </div>
          ))}
          {loading ? (
            <div className="message assistant">
              <span>{CHAT_NAME}</span>
              <p>Thinking through your numbers...</p>
            </div>
          ) : null}
        </div>
        <form className="composer" onSubmit={onSend}>
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder={hasRows ? "Ask ThinkDesk where to save, what changed, or which categories need attention..." : "Upload a CSV first..."}
          />
          <button className="primary-button" disabled={loading || !input.trim()}>
            <Send size={18} />
            Send
          </button>
        </form>
      </div>
    </section>
  );
}

function PanelTitle({ icon: Icon, title }) {
  return (
    <div className="panel-title">
      <Icon size={20} />
      <h2>{title}</h2>
    </div>
  );
}

function CategoryBar({ data }) {
  return (
    <div className="chart-box">
      <ResponsiveContainer width="100%" height={330}>
        <BarChart data={data} layout="vertical" margin={{ top: 10, right: 22, left: 18, bottom: 10 }}>
          <CartesianGrid stroke="#302a4d" strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" tickFormatter={moneyCompact} stroke="#b8add2" />
          <YAxis type="category" dataKey="category" width={118} stroke="#b8add2" tick={{ fontSize: 12 }} />
          <Tooltip formatter={(value) => money(value)} contentStyle={tooltipStyle} />
          <Bar dataKey="amount" radius={[0, 12, 12, 0]}>
            {data.map((_, index) => (
              <Cell fill={CHART_COLORS[index % CHART_COLORS.length]} key={index} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function TrendArea({ data }) {
  return (
    <div className="chart-box">
      <ResponsiveContainer width="100%" height={330}>
        <AreaChart data={data} margin={{ top: 10, right: 22, left: 4, bottom: 10 }}>
          <defs>
            <linearGradient id="trendFill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.52} />
              <stop offset="100%" stopColor="#22d3ee" stopOpacity={0.03} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#302a4d" strokeDasharray="3 3" />
          <XAxis dataKey="month" stroke="#b8add2" />
          <YAxis tickFormatter={moneyCompact} stroke="#b8add2" />
          <Tooltip formatter={(value) => money(value)} contentStyle={tooltipStyle} />
          <Area type="monotone" dataKey="amount" stroke="#22d3ee" strokeWidth={3} fill="url(#trendFill)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function SharePie({ data }) {
  const total = data.reduce((sum, item) => sum + item.amount, 0);
  return (
    <div className="chart-box">
      <ResponsiveContainer width="100%" height={330}>
        <PieChart>
          <Pie data={data} dataKey="amount" nameKey="category" innerRadius={76} outerRadius={118} paddingAngle={3}>
            {data.map((_, index) => (
              <Cell fill={CHART_COLORS[index % CHART_COLORS.length]} key={index} />
            ))}
          </Pie>
          <Tooltip formatter={(value, name) => [`${money(value)} (${total ? ((value / total) * 100).toFixed(1) : "0.0"}%)`, name]} contentStyle={tooltipStyle} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

function DistributionBar({ data }) {
  return (
    <div className="chart-box">
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} margin={{ top: 10, right: 22, left: 4, bottom: 10 }}>
          <CartesianGrid stroke="#302a4d" strokeDasharray="3 3" />
          <XAxis dataKey="bucket" stroke="#b8add2" />
          <YAxis stroke="#b8add2" />
          <Tooltip contentStyle={tooltipStyle} />
          <Bar dataKey="count" fill="#a78bfa" radius={[12, 12, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

const tooltipStyle = {
  background: "#18172f",
  border: "1px solid rgba(255,255,255,.12)",
  borderRadius: "14px",
  color: "#fbfaff",
};

function normalizeRows(rawRows) {
  if (!rawRows.length) return [];
  const columns = Object.keys(rawRows[0] || {});
  const dateCol = findColumn(columns, ["date", "posted", "transaction"]);
  const descCol = findColumn(columns, ["description", "merchant", "detail", "memo", "narration", "name"]);
  const amountCol = findColumn(columns, ["amount", "debit", "value", "cost", "price"]);
  const categoryCol = findColumn(columns, ["category", "spending category", "group"]);
  const typeCol = findColumn(columns, ["transaction type", "type", "kind", "direction", "credit/debit"]);

  if (!amountCol) {
    throw new Error("Could not find an amount column. Include a column like Amount, Debit, Value, Cost, or Price.");
  }

  const mapped = rawRows
    .map((row, index) => {
      const amountRaw = Number.parseFloat(String(row[amountCol] ?? "").replace(/[$,]/g, "").replace(/INR|Rs\.?|rs\.?/g, "").trim());
      if (!Number.isFinite(amountRaw) || amountRaw === 0) return null;
      const type = String(row[typeCol] ?? "").toLowerCase();
      const category = cleanText(row[categoryCol]) || categorize(cleanText(row[descCol]));
      const description = cleanText(row[descCol]) || "Transaction";
      const isCredit = /credit|income|deposit|salary|refund|cr/.test(type) || category.toLowerCase() === "income";
      const isDebit = /debit|expense|withdraw|payment|purchase|dr/.test(type);
      let kind;
      if (!typeCol && amountRaw > 0 && category.toLowerCase() !== "income") {
        kind = "expense";
      } else if (isCredit) {
        kind = "income";
      } else if (isDebit) {
        kind = "expense";
      } else {
        kind = amountRaw > 0 ? "income" : "expense";
      }
      return {
        id: `${index}-${description}-${amountRaw}`,
        date: parseDate(row[dateCol]),
        description,
        category,
        kind,
        amount: Math.abs(amountRaw),
      };
    })
    .filter(Boolean);

  if (!typeCol && mapped.every((row) => row.kind === "income")) {
    return mapped.map((row) => (row.category.toLowerCase() === "income" ? row : { ...row, kind: "expense" }));
  }
  return mapped;
}

function findColumn(columns, candidates) {
  const lowered = columns.map((column) => [String(column).trim().toLowerCase(), column]);
  for (const candidate of candidates) {
    const match = lowered.find(([column]) => column.includes(candidate));
    if (match) return match[1];
  }
  return "";
}

function cleanText(value) {
  return String(value ?? "").trim();
}

function categorize(description) {
  const lower = description.toLowerCase();
  for (const [category, keywords] of Object.entries(CATEGORY_KEYWORDS)) {
    if (keywords.some((keyword) => lower.includes(keyword))) return category;
  }
  return "Other";
}

function parseDate(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function computeMetrics(rows) {
  if (!rows.length) {
    return {
      totalSpend: 0,
      totalIncome: 0,
      netCashflow: 0,
      transactionCount: 0,
      avgDailySpend: 0,
      avgTransaction: 0,
      topCategory: "N/A",
      topCategoryAmount: 0,
      projectedMonthlySpend: 0,
      savingsRate: null,
    };
  }
  const expenses = rows.filter((row) => row.kind === "expense");
  const income = rows.filter((row) => row.kind === "income");
  const totalSpend = sum(expenses.map((row) => row.amount));
  const totalIncome = sum(income.map((row) => row.amount));
  const byCategory = groupByCategory(expenses);
  const dated = rows.filter((row) => row.date);
  const spanDays = dated.length ? Math.max((Math.max(...dated.map((row) => row.date.getTime())) - Math.min(...dated.map((row) => row.date.getTime()))) / 86400000 + 1, 1) : 30;
  return {
    totalSpend,
    totalIncome,
    netCashflow: totalIncome - totalSpend,
    transactionCount: rows.length,
    avgDailySpend: totalSpend / spanDays,
    avgTransaction: expenses.length ? totalSpend / expenses.length : 0,
    topCategory: byCategory[0]?.category || "N/A",
    topCategoryAmount: byCategory[0]?.amount || 0,
    projectedMonthlySpend: (totalSpend / spanDays) * 30,
    savingsRate: totalIncome ? ((totalIncome - totalSpend) / totalIncome) * 100 : null,
  };
}

function groupByCategory(expenses) {
  const groups = new Map();
  for (const row of expenses) {
    groups.set(row.category, (groups.get(row.category) || 0) + row.amount);
  }
  return Array.from(groups, ([category, amount]) => ({ category, amount })).sort((a, b) => b.amount - a.amount);
}

function monthlyTrend(expenses) {
  const groups = new Map();
  for (const row of expenses) {
    if (!row.date) continue;
    const month = `${row.date.getFullYear()}-${String(row.date.getMonth() + 1).padStart(2, "0")}`;
    groups.set(month, (groups.get(month) || 0) + row.amount);
  }
  return Array.from(groups, ([month, amount]) => ({ month, amount })).sort((a, b) => a.month.localeCompare(b.month));
}

function transactionDistribution(expenses) {
  if (!expenses.length) return [];
  const max = Math.max(...expenses.map((row) => row.amount));
  const bucketCount = Math.min(8, Math.max(4, Math.ceil(Math.sqrt(expenses.length))));
  const bucketSize = Math.max(max / bucketCount, 1);
  const buckets = Array.from({ length: bucketCount }, (_, index) => ({
    bucket: `${moneyCompact(index * bucketSize)}-${moneyCompact((index + 1) * bucketSize)}`,
    count: 0,
  }));
  for (const row of expenses) {
    const index = Math.min(Math.floor(row.amount / bucketSize), bucketCount - 1);
    buckets[index].count += 1;
  }
  return buckets;
}

function buildRecommendations(rows) {
  if (!rows.length) return [];
  const expenses = rows.filter((row) => row.kind === "expense");
  const metrics = computeMetrics(rows);
  const byCategory = groupByCategory(expenses);
  const recs = [];

  if (metrics.savingsRate !== null && metrics.savingsRate < 10) {
    recs.push({
      impact: "High",
      title: "Protect the savings rate first",
      detail: `Your estimated savings rate is ${pct(metrics.savingsRate)}. Aim for 15-20% by setting an automatic transfer before discretionary spending starts.`,
    });
  } else if (metrics.savingsRate !== null && metrics.savingsRate >= 20) {
    recs.push({
      impact: "Medium",
      title: "You have room to accelerate goals",
      detail: `Your estimated savings rate is ${pct(metrics.savingsRate)}. Consider directing surplus cash to debt payoff, emergency funds, or long-term investing.`,
    });
  }

  if (metrics.totalSpend && byCategory[0]) {
    const share = (byCategory[0].amount / metrics.totalSpend) * 100;
    if (share >= 30) {
      recs.push({
        impact: "High",
        title: `Run a 12% trim test on ${byCategory[0].category}`,
        detail: `${byCategory[0].category} is ${share.toFixed(0)}% of spending. A 12% reduction could free about ${money(byCategory[0].amount * 0.12)}.`,
      });
    }
  }

  const subscriptions = expenses.filter((row) => /subscription|netflix|spotify|hulu|prime|adobe|icloud|membership/i.test(row.description));
  if (subscriptions.length >= 2) {
    recs.push({
      impact: "Medium",
      title: "Audit recurring charges",
      detail: `Detected ${subscriptions.length} likely recurring charges totaling ${money(sum(subscriptions.map((row) => row.amount)))}.`,
    });
  }

  if (metrics.projectedMonthlySpend > metrics.totalIncome && metrics.totalIncome > 0) {
    recs.push({
      impact: "High",
      title: "Projected spending is above income",
      detail: `Projected monthly spend is ${money(metrics.projectedMonthlySpend)} against detected income of ${money(metrics.totalIncome)}.`,
    });
  }

  if (!recs.length) {
    recs.push({
      impact: "Low",
      title: "Spending mix looks balanced",
      detail: "No major imbalance jumped out. Keep uploading monthly statements so trends and category drift become visible earlier.",
    });
  }
  return recs.slice(0, 6);
}

function buildSummary(rows, metrics, byCategory) {
  if (!rows.length) return "No transaction data has been uploaded.";
  const dated = rows.filter((row) => row.date);
  const period =
    dated.length > 0
      ? `${formatDate(new Date(Math.min(...dated.map((row) => row.date.getTime()))))} to ${formatDate(new Date(Math.max(...dated.map((row) => row.date.getTime()))))}`
      : "Unknown period";
  const lines = [
    "Financial Snapshot",
    `Period: ${period}`,
    `Transactions: ${metrics.transactionCount}`,
    `Total spending: ${money(metrics.totalSpend)}`,
    `Total income detected: ${money(metrics.totalIncome)}`,
    `Net cash flow: ${money(metrics.netCashflow)}`,
    `Projected monthly spend: ${money(metrics.projectedMonthlySpend)}`,
    `Estimated savings rate: ${pct(metrics.savingsRate)}`,
    "",
    "Category Breakdown",
  ];
  for (const item of byCategory) {
    const share = metrics.totalSpend ? (item.amount / metrics.totalSpend) * 100 : 0;
    lines.push(`- ${item.category}: ${money(item.amount)} (${share.toFixed(1)}%)`);
  }
  return lines.join("\n");
}

function localAdvice(rows, question) {
  if (!rows.length) return "Upload a CSV first, then I can answer using your actual spending data.";
  const lower = question.toLowerCase();
  const expenses = rows.filter((row) => row.kind === "expense");
  const metrics = computeMetrics(rows);
  const byCategory = groupByCategory(expenses);
  if (["category", "highest", "most", "top"].some((word) => lower.includes(word))) {
    return ["Your top spending categories are:", ...byCategory.slice(0, 5).map((item) => `- ${item.category}: ${money(item.amount)}`)].join("\n");
  }
  if (["save", "saving", "cut", "reduce", "strategy"].some((word) => lower.includes(word))) {
    return ["Here are the strongest savings moves from this file:", ...buildRecommendations(rows).slice(0, 4).map((rec) => `- ${rec.title}: ${rec.detail}`)].join("\n");
  }
  return `Total spending is ${money(metrics.totalSpend)} with projected monthly spend of ${money(metrics.projectedMonthlySpend)}. Top category is ${metrics.topCategory} at ${money(metrics.topCategoryAmount)}. Estimated savings rate: ${pct(metrics.savingsRate)}.`;
}

function money(value) {
  return `Rs. ${Number(value || 0).toLocaleString("en-IN", { maximumFractionDigits: 2, minimumFractionDigits: 2 })}`;
}

function moneyCompact(value) {
  const number = Number(value || 0);
  const abs = Math.abs(number);
  if (abs >= 10000000) return `Rs. ${(number / 10000000).toFixed(1)}Cr`;
  if (abs >= 100000) return `Rs. ${(number / 100000).toFixed(1)}L`;
  if (abs >= 1000) return `Rs. ${(number / 1000).toFixed(0)}K`;
  return `Rs. ${number.toFixed(0)}`;
}

function pct(value) {
  return value === null || Number.isNaN(value) ? "N/A" : `${Number(value).toFixed(1)}%`;
}

function parseMoney(value) {
  const parsed = Number.parseFloat(String(value).replace(/,/g, "").replace(/INR|Rs\.?|rs\.?/g, "").trim());
  return Number.isFinite(parsed) ? Math.max(parsed, 0) : 10000;
}

function formatDate(date) {
  if (!date) return "";
  return date.toISOString().slice(0, 10);
}

function titleCase(value) {
  return String(value).charAt(0).toUpperCase() + String(value).slice(1);
}

function sum(values) {
  return values.reduce((total, value) => total + Number(value || 0), 0);
}

createRoot(document.getElementById("root")).render(<App />);
