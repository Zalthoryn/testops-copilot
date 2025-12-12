import clsx from "clsx";
import { ReactNode } from "react";

type GlassCardProps = {
  children: ReactNode;
  glow?: boolean;
  padding?: number | string;
  style?: React.CSSProperties;
  className?: string;
};

const GlassCard = ({
  children,
  glow = true,
  padding = 18,
  style,
  className,
}: GlassCardProps) => {
  return (
    <div
      className={clsx("card", className)}
      style={{
        padding,
        borderRadius: "22px",
        background:
          "linear-gradient(145deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02)) rgba(8,12,22,0.78)",
        backdropFilter: "blur(20px) saturate(1.15)",
        border: "1px solid rgba(255,255,255,0.06)",
        boxShadow: glow
          ? "0 26px 90px rgba(0,0,0,0.65), 0 0 0 1px rgba(124,58,237,0.14), inset 0 1px 0 rgba(255,255,255,0.04)"
          : "0 18px 48px rgba(0,0,0,0.38), inset 0 1px 0 rgba(255,255,255,0.02)",
        ...style,
      }}
    >
      {children}
    </div>
  );
};

export default GlassCard;

