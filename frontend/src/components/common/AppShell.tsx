import { NavLink } from "react-router-dom";
import { ReactNode } from "react";
import classes from "../../styles/layout.module.css";
import GradientButton from "./GradientButton";

const navItems = [
  { path: "/", label: "Dashboard" },
  { path: "/testcases", label: "Тест-кейсы" },
  { path: "/autotests", label: "Автотесты" },
  { path: "/standards", label: "Стандарты" },
  { path: "/optimization", label: "Оптимизация" },
  { path: "/settings", label: "Настройки" },
];

type Props = {
  children: ReactNode;
};

const AppShell = ({ children }: Props) => {
  return (
    <div className={classes.shell}>
      <aside className={classes.sidebar}>
        <div className={classes.brand}>TestOps Copilot</div>
        <nav className={classes.nav}>
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                [classes.navItem, isActive ? classes.active : ""].join(" ")
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className={classes.content}>
        <header className={classes.header}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ fontWeight: 800, color: "var(--text-primary)", fontSize: 16 }}>TestOps Copilot</div>
            <span className="badge-soft" style={{ borderColor: "rgba(255,255,255,0.12)" }}>Dark SaaS board</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <GradientButton variant="ghost">Live demo</GradientButton>
            <GradientButton>Generate tests</GradientButton>
          </div>
        </header>
        <div className={classes.page}>
          <div className={classes.pageInner}>{children}</div>
        </div>
      </main>
    </div>
  );
};

export default AppShell;

