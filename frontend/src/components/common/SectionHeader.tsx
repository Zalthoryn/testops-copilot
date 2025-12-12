import { ReactNode } from "react";

type Props = {
  title: string;
  subtitle?: string;
  right?: ReactNode;
};

const SectionHeader = ({ title, subtitle, right }: Props) => (
  <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
    <div>
      <div className="section-title">{title}</div>
      {subtitle && <div className="muted" style={{ marginTop: 6 }}>{subtitle}</div>}
    </div>
    {right}
  </div>
);

export default SectionHeader;

