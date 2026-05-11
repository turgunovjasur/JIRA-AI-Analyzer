import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

export type ButtonVariant = "primary" | "ghost" | "soft" | "danger";
export type ButtonSize = "md" | "sm";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-[12px] text-sm font-semibold transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:ring-offset-2 focus-visible:ring-offset-white disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      size: {
        md: "h-11 px-4 py-2",
        sm: "h-9 px-3 text-sm",
      },
      variant: {
        primary:
          "border border-transparent bg-primary text-primary-foreground shadow-sm hover:bg-[color:var(--brand-strong)]",
        ghost:
          "border border-border bg-background/80 text-foreground hover:border-primary/15 hover:bg-accent/60",
        soft:
          "border border-transparent bg-accent text-accent-foreground hover:bg-accent/80",
        danger:
          "border border-destructive/15 bg-destructive/10 text-destructive hover:bg-destructive/15",
      },
      width: {
        auto: "w-auto",
        full: "w-full",
      },
    },
    defaultVariants: {
      size: "md",
      variant: "primary",
      width: "auto",
    },
  },
);

type ButtonClassNameOptions = {
  className?: string;
  fullWidth?: boolean;
  size?: ButtonSize;
  variant?: ButtonVariant;
};

export function buttonClassName({
  className,
  fullWidth = false,
  size = "md",
  variant = "primary",
}: ButtonClassNameOptions = {}) {
  return cn(
    buttonVariants({
      size,
      variant,
      width: fullWidth ? "full" : "auto",
    }),
    className,
  );
}

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
    fullWidth?: boolean;
  };

export function Button({
  asChild = false,
  className,
  fullWidth = false,
  size = "md",
  type = "button",
  variant = "primary",
  ...props
}: ButtonProps) {
  const Component = asChild ? Slot : "button";

  return (
    <Component
      className={cn(
        buttonVariants({
          size,
          variant,
          width: fullWidth ? "full" : "auto",
        }),
        className,
      )}
      type={asChild ? undefined : type}
      {...props}
    />
  );
}
