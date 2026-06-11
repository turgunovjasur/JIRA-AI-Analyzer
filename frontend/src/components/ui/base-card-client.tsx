"use client";

import {
  useEffect,
  useId,
  useRef,
  useState,
  type CSSProperties,
  type ElementType,
  type ReactNode,
} from "react";
import { ChevronDown, RotateCcw, Settings, X } from "lucide-react";

import { cn } from "@/lib/cn";

export type BaseCardColor = "neutral" | "blue" | "green" | "amber" | "rose" | "purple" | "teal";

type BaseCardColorPrefs = {
  color: BaseCardColor;
};

const BASE_CARD_DEFAULTS: BaseCardColorPrefs = {
  color: "neutral",
};

const BASE_CARD_COLORS: Array<{ bg: string; key: BaseCardColor; label: string; swatch: string }> = [
  { key: "neutral", label: "Neytral", bg: "var(--surface)", swatch: "#e4e4e7" },
  { key: "blue", label: "Ko'k", bg: "var(--accent-soft)", swatch: "rgba(79,70,229,0.55)" },
  { key: "green", label: "Yashil", bg: "var(--success-soft)", swatch: "rgba(5,150,105,0.55)" },
  { key: "amber", label: "Sariq", bg: "var(--warn-soft)", swatch: "rgba(245,158,11,0.65)" },
  { key: "rose", label: "Qizil", bg: "var(--error-soft)", swatch: "rgba(220,38,38,0.5)" },
  { key: "purple", label: "Binafsha", bg: "rgba(168,85,247,0.08)", swatch: "rgba(168,85,247,0.55)" },
  { key: "teal", label: "Moviy", bg: "rgba(20,184,166,0.08)", swatch: "rgba(20,184,166,0.55)" },
];

function isBaseCardColor(value: unknown): value is BaseCardColor {
  return value === "neutral" || value === "blue" || value === "green" || value === "amber" || value === "rose" || value === "purple" || value === "teal";
}

function coerceBaseCardPrefs(value: unknown): Partial<BaseCardColorPrefs> {
  if (!value || typeof value !== "object") return {};
  const source = value as Record<string, unknown>;
  const next: Partial<BaseCardColorPrefs> = {};
  if (isBaseCardColor(source.color)) next.color = source.color;
  if (!next.color && isBaseCardColor(source.tone)) next.color = source.tone;
  return next;
}

function BaseCardColorPanel({
  onChange,
  onClose,
  onReset,
  prefs,
}: {
  prefs: BaseCardColorPrefs;
  onChange: (next: Partial<BaseCardColorPrefs>) => void;
  onClose: () => void;
  onReset: () => void;
}) {
  return (
    <div className="bc-sp">
      <div className="bc-sp-head">
        <span className="bc-sp-title">Karta sozlamalari</span>
        <button aria-label="Yopish" className="bc-btn bc-sp-close" onClick={onClose} type="button">
          <X aria-hidden="true" size={12} />
        </button>
      </div>
      <div className="bc-sp-inner">
        <div className="bc-sp-row">
          <div className="bc-sp-label">Fon rangi</div>
          <div className="bc-swatches">
            {BASE_CARD_COLORS.map((color) => (
              <button
                aria-label={color.label}
                className={`bc-sw${prefs.color === color.key ? " bc-sw-sel" : ""}`}
                key={color.key}
                onClick={() => onChange({ color: color.key })}
                style={{ background: color.swatch }}
                title={color.label}
                type="button"
              />
            ))}
          </div>
        </div>
        <button className="bc-reset-btn" onClick={onReset} type="button">
          <RotateCcw aria-hidden="true" size={11} />
          Asl holatga qaytarish
        </button>
      </div>
    </div>
  );
}

type BaseCardClientOwnProps = {
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
  onCollapsedChange?: (next: boolean) => void;
  settingsId?: string;
  showSettings?: boolean;
  title?: ReactNode;
};

type BaseCardClientProps = BaseCardClientOwnProps & {
  as?: ElementType;
  style?: CSSProperties;
  [key: string]: unknown;
};

export function BaseCardClient({
  actions,
  as,
  bodyClassName,
  children,
  className,
  collapsed,
  collapsible = false,
  controlsClassName,
  defaultCollapsed = false,
  defaultColor = "neutral",
  description,
  footer,
  header,
  headerClassName,
  icon,
  onCollapsedChange,
  settingsId,
  showSettings = false,
  style,
  title,
  ...props
}: BaseCardClientProps) {
  const Component = as || "section";
  const fallbackId = useId().replace(/:/g, "");
  const resolvedSettingsId = settingsId || `auto-${fallbackId}`;
  const storageKey = `bc:${resolvedSettingsId}`;
  const legacyStorageKey = `settings-card-customizer:${resolvedSettingsId}`;
  const panelRef = useRef<HTMLDivElement | null>(null);
  const [internalCollapsed, setInternalCollapsed] = useState(defaultCollapsed);
  const [prefs, setPrefs] = useState<BaseCardColorPrefs>({ ...BASE_CARD_DEFAULTS, color: defaultColor });
  const [prefsReady, setPrefsReady] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const isCollapsed = collapsed ?? internalCollapsed;
  const hasLeftContent = Boolean(header || title || description || icon);
  const hasControls = Boolean(actions || collapsible || showSettings);
  const showHeader = hasLeftContent || hasControls;

  useEffect(() => {
    if (!showSettings) {
      setPrefsReady(false);
      return;
    }
    setPrefsReady(false);
    try {
      const raw = window.localStorage.getItem(storageKey) || window.localStorage.getItem(legacyStorageKey);
      if (raw) {
        setPrefs({ ...BASE_CARD_DEFAULTS, color: defaultColor, ...coerceBaseCardPrefs(JSON.parse(raw)) });
      } else {
        setPrefs({ ...BASE_CARD_DEFAULTS, color: defaultColor });
      }
    } catch {
      setPrefs({ ...BASE_CARD_DEFAULTS, color: defaultColor });
    } finally {
      setPrefsReady(true);
    }
  }, [defaultColor, legacyStorageKey, showSettings, storageKey]);

  useEffect(() => {
    if (!showSettings || !prefsReady) return;
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(prefs));
    } catch {
      // localStorage may be unavailable in some environments
    }
  }, [prefs, prefsReady, showSettings, storageKey]);

  useEffect(() => {
    if (!settingsOpen) return;
    function handleMouseDown(event: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        setSettingsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleMouseDown);
    return () => document.removeEventListener("mousedown", handleMouseDown);
  }, [settingsOpen]);

  function toggleCollapsed() {
    if (!collapsible) return;
    const next = !isCollapsed;
    setInternalCollapsed(next);
    onCollapsedChange?.(next);
    if (next) setSettingsOpen(false);
  }

  function updatePrefs(next: Partial<BaseCardColorPrefs>) {
    setPrefs((current) => ({ ...current, ...next }));
  }

  const colorDef = BASE_CARD_COLORS.find((color) => color.key === prefs.color) || BASE_CARD_COLORS[0];
  const cardStyle = showSettings
    ? ({ ...(style || {}), "--bc-bg": colorDef.bg } as CSSProperties)
    : style;

  return (
    <Component className={cn(className, isCollapsed && "bc-collapsed")} style={cardStyle} {...props}>
      {showHeader ? (
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
          {hasControls ? (
            <div className={cn("bc-ctrls", controlsClassName)} ref={panelRef}>
              {actions}
              {collapsible ? (
                <button
                  aria-expanded={!isCollapsed}
                  aria-label={isCollapsed ? "Karta ochish" : "Karta yopish"}
                  className="bc-btn"
                  onClick={toggleCollapsed}
                  title={isCollapsed ? "Ochish" : "Yig'ish"}
                  type="button"
                >
                  <span className={cn("bc-chev-wrap", !isCollapsed && "bc-open")}>
                    <ChevronDown aria-hidden="true" size={14} strokeWidth={2.2} />
                  </span>
                </button>
              ) : null}
              {showSettings ? (
                <button
                  aria-label="Karta sozlamalari"
                  className={`bc-btn${settingsOpen ? " bc-btn-on" : ""}`}
                  onClick={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    setSettingsOpen((current) => !current);
                  }}
                  title="Karta sozlamalari"
                  type="button"
                >
                  <Settings aria-hidden="true" size={13} />
                </button>
              ) : null}
              {showSettings && settingsOpen ? (
                <BaseCardColorPanel
                  onChange={updatePrefs}
                  onClose={() => setSettingsOpen(false)}
                  onReset={() => setPrefs({ ...BASE_CARD_DEFAULTS, color: defaultColor })}
                  prefs={prefs}
                />
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}
      {!isCollapsed ? <div className={cn("bc-body", bodyClassName)}>{children}</div> : null}
      {!isCollapsed ? footer : null}
    </Component>
  );
}
