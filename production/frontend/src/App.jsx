import { useState, useEffect, useCallback, useRef } from "react";
import { usePlaidLink } from "react-plaid-link";

const BACKEND = "http://localhost:5000";

export default function App() {
  const [linkToken, setLinkToken] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | loading | success | error
  const [message, setMessage] = useState("");
  const [fetched, setFetched] = useState(false);
  const fileInputRef = useRef(null);

  const refreshStatus = () => {
    fetch(`${BACKEND}/api/status`)
      .then((r) => r.json())
      .then((d) => setAccounts(d.accounts || []));
  };

  const refreshLinkToken = () => {
    fetch(`${BACKEND}/api/create_link_token`, { method: "POST" })
      .then((r) => r.json())
      .then((d) => setLinkToken(d.link_token));
  };

  useEffect(() => {
    refreshStatus();
    refreshLinkToken();
  }, []);

  const onPlaidSuccess = useCallback(async (public_token, metadata) => {
    const institution_name = metadata?.institution?.name || "Unknown Bank";
    const res = await fetch(`${BACKEND}/api/exchange_token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ public_token, institution_name }),
    });
    const data = await res.json();
    if (data.success) {
      refreshStatus();
      // Refresh link token so user can connect another bank
      refreshLinkToken();
    } else {
      setStatus("error");
      setMessage(data.error || "Failed to connect bank.");
    }
  }, []);

  const removeAccount = async (index) => {
    await fetch(`${BACKEND}/api/remove_account`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ index }),
    });
    refreshStatus();
  };

  const { open, ready } = usePlaidLink({ token: linkToken, onSuccess: onPlaidSuccess });

  const fetchTransactions = async () => {
    if (accounts.length === 0) return;
    setStatus("loading");
    setMessage(`Fetching 24 months of transactions from ${accounts.length} account${accounts.length > 1 ? "s" : ""}...`);
    setFetched(false);

    const formData = new FormData();
    if (uploadedFile) formData.append("file", uploadedFile);

    const res = await fetch(`${BACKEND}/api/fetch_transactions`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (data.success) {
      setStatus("success");
      setFetched(true);
      setMessage(`Done! ${data.transactions_count} transactions across ${data.accounts_count} accounts — duplicates removed.`);
    } else {
      setStatus("error");
      setMessage(data.error || "Something went wrong.");
    }
  };

  return (
    <div style={s.page}>
      <div style={s.card}>

        {/* Header */}
        <div style={s.header}>
          <div style={s.logo}>⬡</div>
          <h1 style={s.title}>Plaid Sync</h1>
          <p style={s.subtitle}>Connect your banks and export all transactions to Excel</p>
        </div>

        {/* Step 1 — Upload existing file (optional) */}
        <Section number="1" label="Upload previous file (optional)">
          <div style={s.uploadArea} onClick={() => fileInputRef.current.click()}>
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx"
              style={{ display: "none" }}
              onChange={(e) => setUploadedFile(e.target.files[0] || null)}
            />
            {uploadedFile ? (
              <div style={s.uploadedFile}>
                <span style={s.uploadedIcon}>📄</span>
                <span style={s.uploadedName}>{uploadedFile.name}</span>
                <button style={s.clearFile} onClick={(e) => { e.stopPropagation(); setUploadedFile(null); }}>✕</button>
              </div>
            ) : (
              <div style={s.uploadPlaceholder}>
                <span style={s.uploadIcon}>↑</span>
                <span>Click to upload transactions.xlsx</span>
                <span style={s.uploadHint}>New transactions will be merged & deduplicated</span>
              </div>
            )}
          </div>
          {!uploadedFile && (
            <p style={s.skipNote}>Skipping this will fetch all available history and overwrite any existing file.</p>
          )}
        </Section>

        <Divider />

        {/* Step 2 — Connect banks */}
        <Section number="2" label="Connect bank accounts">
          {accounts.length > 0 && (
            <div style={s.accountList}>
              {accounts.map((name, i) => (
                <div key={i} style={s.accountChip}>
                  <span style={s.bankIcon}>🏦</span>
                  <span style={s.accountName}>{name}</span>
                  <button style={s.removeBtn} onClick={() => removeAccount(i)}>✕</button>
                </div>
              ))}
            </div>
          )}
          <button
            style={{ ...s.btn, ...s.btnSecondary, ...(!ready ? s.btnDisabled : {}) }}
            onClick={() => { if (ready) open(); }}
          >
            + Connect{accounts.length > 0 ? " Another" : ""} Bank
          </button>
        </Section>

        <Divider />

        {/* Step 3 — Fetch */}
        <Section number="3" label="Fetch & export">
          <button
            style={{
              ...s.btn,
              ...s.btnPrimary,
              ...(accounts.length === 0 || status === "loading" ? s.btnDisabled : {}),
            }}
            onClick={() => { if (accounts.length > 0 && status !== "loading") fetchTransactions(); }}
          >
            {status === "loading" ? "Working..." : `Fetch All Transactions`}
          </button>
        </Section>

        {/* Status message */}
        {message && (
          <div style={{ ...s.message, ...(status === "error" ? s.messageError : s.messageSuccess) }}>
            {message}
          </div>
        )}

        {/* Download */}
        {fetched && (
          <a href={`${BACKEND}/api/download`} download="transactions.xlsx" style={s.downloadBtn}>
            ↓ Download transactions.xlsx
          </a>
        )}

      </div>
    </div>
  );
}

function Section({ number, label, children }) {
  return (
    <div style={s.section}>
      <div style={s.sectionHeader}>
        <div style={s.stepNum}>{number}</div>
        <div style={s.sectionLabel}>{label}</div>
      </div>
      <div style={s.sectionBody}>{children}</div>
    </div>
  );
}

function Divider() {
  return <div style={s.divider} />;
}

const s = {
  page: {
    minHeight: "100vh",
    background: "linear-gradient(135deg, #f0f4ff 0%, #fafbff 100%)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontFamily: "'DM Mono', 'Courier New', monospace",
    padding: "24px",
  },
  card: {
    background: "#ffffff",
    border: "1px solid #e8edf5",
    borderRadius: "20px",
    padding: "48px",
    width: "100%",
    maxWidth: "480px",
    boxShadow: "0 8px 40px rgba(99,120,220,0.10)",
  },
  header: {
    textAlign: "center",
    marginBottom: "40px",
  },
  logo: {
    fontSize: "32px",
    marginBottom: "12px",
  },
  title: {
    margin: 0,
    fontSize: "26px",
    fontWeight: "700",
    color: "#1a1f36",
    letterSpacing: "-0.5px",
  },
  subtitle: {
    margin: "8px 0 0",
    fontSize: "13px",
    color: "#8892aa",
    lineHeight: "1.5",
  },
  section: {
    marginBottom: "4px",
  },
  sectionHeader: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    marginBottom: "12px",
  },
  stepNum: {
    width: "28px",
    height: "28px",
    borderRadius: "50%",
    background: "#4f6ef7",
    color: "#fff",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "12px",
    fontWeight: "700",
    flexShrink: 0,
  },
  sectionLabel: {
    fontSize: "12px",
    fontWeight: "600",
    color: "#8892aa",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
  },
  sectionBody: {
    paddingLeft: "40px",
  },
  divider: {
    height: "1px",
    background: "#f0f2f8",
    margin: "20px 0",
  },
  uploadArea: {
    border: "2px dashed #d0d9ff",
    borderRadius: "10px",
    padding: "20px",
    cursor: "pointer",
    textAlign: "center",
    background: "#fafbff",
    transition: "border-color 0.15s",
  },
  uploadPlaceholder: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "4px",
    color: "#8892aa",
    fontSize: "13px",
  },
  uploadIcon: {
    fontSize: "20px",
    marginBottom: "4px",
  },
  uploadHint: {
    fontSize: "11px",
    color: "#b0b8cc",
    marginTop: "2px",
  },
  uploadedFile: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    justifyContent: "center",
  },
  uploadedIcon: { fontSize: "18px" },
  uploadedName: {
    fontSize: "13px",
    color: "#1a1f36",
    fontWeight: "600",
  },
  clearFile: {
    background: "none",
    border: "none",
    color: "#b0b8cc",
    cursor: "pointer",
    fontSize: "14px",
    padding: "0 4px",
    fontFamily: "inherit",
  },
  skipNote: {
    fontSize: "11px",
    color: "#b0b8cc",
    marginTop: "8px",
    lineHeight: "1.5",
  },
  accountList: {
    display: "flex",
    flexDirection: "column",
    gap: "6px",
    marginBottom: "10px",
  },
  accountChip: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    background: "#f0f4ff",
    border: "1px solid #d0d9ff",
    borderRadius: "8px",
    padding: "8px 12px",
  },
  bankIcon: { fontSize: "14px" },
  accountName: {
    flex: 1,
    fontSize: "13px",
    color: "#1a1f36",
    fontWeight: "500",
  },
  removeBtn: {
    background: "none",
    border: "none",
    color: "#b0b8cc",
    cursor: "pointer",
    fontSize: "13px",
    padding: "0",
    fontFamily: "inherit",
  },
  btn: {
    width: "100%",
    padding: "11px 20px",
    borderRadius: "10px",
    border: "none",
    fontSize: "14px",
    fontWeight: "600",
    cursor: "pointer",
    fontFamily: "inherit",
    letterSpacing: "0.01em",
    transition: "opacity 0.15s",
  },
  btnPrimary: {
    background: "#4f6ef7",
    color: "#fff",
  },
  btnSecondary: {
    background: "#f0f4ff",
    color: "#4f6ef7",
    border: "1px solid #d0d9ff",
  },
  btnDisabled: {
    opacity: 0.4,
    cursor: "not-allowed",
  },
  message: {
    marginTop: "20px",
    padding: "12px 16px",
    borderRadius: "10px",
    fontSize: "13px",
    lineHeight: "1.5",
  },
  messageSuccess: {
    background: "#f0fdf4",
    color: "#16a34a",
    border: "1px solid #bbf7d0",
  },
  messageError: {
    background: "#fff1f2",
    color: "#e11d48",
    border: "1px solid #fecdd3",
  },
  downloadBtn: {
    display: "block",
    marginTop: "12px",
    padding: "12px 20px",
    borderRadius: "10px",
    background: "#f0f4ff",
    color: "#4f6ef7",
    fontFamily: "'DM Mono', 'Courier New', monospace",
    fontSize: "14px",
    fontWeight: "600",
    textAlign: "center",
    textDecoration: "none",
    border: "1px solid #d0d9ff",
    cursor: "pointer",
  },
};