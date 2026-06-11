import type { ComponentPropsWithoutRef, ElementType, ReactNode } from "react";

import { cn } from "@/lib/cn";
import { BaseCardClient, type BaseCardColor } from "@/components/ui/base-card-client";

type CardTone = "default" | "soft" | "accent" | "success" | "danger" | "warning";
type CardPadding = "md" | "lg" | "none";

type BaseCardProps = {
  actions?: ReactNode;
  bodyClassName?: string;
  children: ReactNode;
  className?: string;
  collapsed?: boolean;
  collapsible?: boolean;
  controlsClassName?: string;
  defaultCollapsed?: boolean;
  defaultColor?: BaseCardColor;
  description?: ReactNode;
  footer?: ReactNode;
  header?: ReactNode;
  headerClassName?: string;
  icon?: ReactNode;
  interactive?: boolean;
  onCollapsedChange?: (next: boolean) => void;
  padding?: CardPadding;
  settingsId?: string;
  showSettings?: boolean;
  title?: ReactNode;
  tone?: CardTone;
};

type BaseCardComponentProps<T extends ElementType> = BaseCardProps &
  Omit<ComponentPropsWithoutRef<T>, keyof BaseCardProps | "as"> & {
    as?: T;
  };

export function BaseCard<T extends ElementType = "section">({
  actions,
  as,
  bodyClassName,
  children,
  className,
  collapsed,
  collapsible,
  controlsClassName,
  defaultCollapsed,
  defaultColor,
  description,
  footer,
  header,
  headerClassName,
  icon,
  interactive,
  onCollapsedChange,
  padding = "md",
  settingsId,
  showSettings,
  title,
  tone = "default",
  ...props
}: BaseCardComponentProps<T>) {
  const Component = as || "section";
  const hasStructuredShell = Boolean(
    header || title || description || icon || actions || footer || bodyClassName || headerClassName || controlsClassName || showSettings,
  );
  const hasLeftContent = Boolean(header || title || description || icon);
  const rootClassName = cn(
    "base-card text-card-foreground",
    tone === "soft" && "base-card--soft",
    tone === "accent" && "base-card--accent",
    tone === "success" && "base-card--success",
    tone === "danger" && "base-card--danger",
    tone === "warning" && "base-card--warning",
    interactive && "base-card--interactive",
    (collapsible || hasStructuredShell) ? "p-0" : padding === "md" && "card-pad",
    !collapsible && !hasStructuredShell && padding === "lg" && "card-pad-lg",
    !collapsible && !hasStructuredShell && padding === "none" && "p-0",
    className,
  );

  if (collapsible || showSettings) {
    return (
      <BaseCardClient
        actions={actions}
        as={as}
        bodyClassName={bodyClassName}
        className={rootClassName}
        collapsed={collapsed}
        collapsible={collapsible}
        controlsClassName={controlsClassName}
        defaultCollapsed={defaultCollapsed}
        defaultColor={defaultColor}
        description={description}
        footer={footer}
        header={header}
        headerClassName={headerClassName}
        icon={icon}
        onCollapsedChange={onCollapsedChange}
        settingsId={settingsId}
        showSettings={showSettings}
        title={title}
        {...props}
      >
        {children}
      </BaseCardClient>
    );
  }

  if (hasStructuredShell) {
    return (
      <Component className={rootClassName} {...props}>
        {hasLeftContent || actions ? (
          <div className={cn("bc-hd", !hasLeftContent && "bc-hd-ctrlonly", headerClassName)}>
            <div className="bc-hd-left">
              {header ? (
                header
              ) : hasLeftContent ? (
                <>
                  {icon ? icon : null}
                  <div className="bc-hd-text">
                    {title ? <div className="bc-hd-title">{title}</div> : null}
                    {description ? <div className="bc-hd-desc">{description}</div> : null}
                  </div>
                </>
              ) : null}
            </div>
            {actions ? <div className={cn("bc-ctrls", controlsClassName)}>{actions}</div> : null}
          </div>
        ) : null}
        <div className={cn("bc-body", bodyClassName)}>{children}</div>
        {footer}
      </Component>
    );
  }

  return (
    <Component
      className={rootClassName}
      {...props}
    >
      {children}
    </Component>
  );
}

export function Card<T extends ElementType = "section">(props: BaseCardComponentProps<T>) {
  return <BaseCard {...props} />;
}
