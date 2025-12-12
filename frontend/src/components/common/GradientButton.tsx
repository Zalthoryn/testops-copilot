import { ButtonHTMLAttributes, ReactNode } from "react";
import clsx from "clsx";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  variant?: "primary" | "ghost";
};

const GradientButton = ({ children, variant = "primary", className, ...rest }: Props) => {
  return (
    <button
      className={clsx("btn", variant === "ghost" && "ghost", className)}
      {...rest}
    >
      {children}
    </button>
  );
};

export default GradientButton;

