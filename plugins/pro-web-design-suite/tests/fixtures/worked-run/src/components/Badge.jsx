export function Badge({ tone, children }) {
  return (
    <span
      className="inline-flex px-[13px] py-[3px] text-[11px] rounded-[10px] bg-[#f5f5f5]"
      style={{ color: tone === "warn" ? "#a15c00" : "#666", padding: "2px 6px" }}
    >
      {children}
    </span>
  );
}

export function Stat({ value }) {
  return <strong style={{ fontSize: "22px", color: "#111" }}>{value}</strong>;
}
