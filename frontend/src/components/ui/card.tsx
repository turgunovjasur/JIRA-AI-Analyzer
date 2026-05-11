import type { ComponentPropsWithoutRef, ElementType, ReactNode } from "react";

import { cn } from "@/lib/cn";

type CardTone = "default" | "soft" | "accent";
type CardPadding = "md" | "lg" | "none";

type BaseCardProps = {
  children: ReactNode;
  className?: string;
  padding?: CardPadding;
  tone?: CardTone;
};

type CardProps<T extends ElementType> = BaseCardProps &
  Omit<ComponentPropsWithoutRef<T>, keyof BaseCardProps | "as"> & {
    as?: T;
  };

export function Card<T extends ElementType = "section">({
  as,
  children,
  className,
  padding = "md",
  tone = "default",
  ...props
}: CardProps<T>) {
  const Component = as || "section";

  return (
    <Component
      className={cn(
        "rounded-[20px] border border-border bg-card text-card-foreground shadow-sm",
        tone === "soft" && "bg-[color:var(--bg-layer)]",
        tone === "accent" &&
          "bg-gradient-to-br from-[color:var(--surface-strong)] via-[color:var(--surface-strong)] to-[color:var(--accent-soft)]/60",
        padding === "md" && "p-6",
        padding === "lg" && "p-8",
        padding === "none" && "p-0",
        className,
      )}
      {...props}
    >
      {children}
    </Component>
  );
}
