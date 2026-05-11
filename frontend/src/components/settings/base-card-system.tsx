"use client";

import {
  useEffect,
  useId,
  useState,
  type DragEvent,
  type FocusEventHandler,
  type KeyboardEvent,
  type ReactNode,
} from "react";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Notice } from "@/components/ui/notice";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

type CardStatusStackProps = {
  dirty: boolean;
  dirtyText?: string;
  error: string | null;
  success: string | null;
};

export function BaseStatusStack({
  dirty,
  dirtyText = "Saqlanmagan o'zgarishlar bor",
  error,
  success,
}: CardStatusStackProps) {
  return (
    <div>
      {dirty ? <Notice className="mt-2" tone="warning">{dirtyText}</Notice> : null}
      {error ? <Notice className="mt-2" tone="error">{error}</Notice> : null}
      {success ? <Notice className="mt-2" tone="success">{success}</Notice> : null}
    </div>
  );
}

type BaseActionRowProps = {
  dirty?: boolean;
  dirtyText?: string;
  error?: string | null;
  success?: string | null;
  onSave: () => void;
  saveDisabled?: boolean;
  saveLabel?: string;
  saving?: boolean;
};

export function BaseActionRow({
  dirty,
  dirtyText,
  error,
  success,
  onSave,
  saveDisabled,
  saveLabel,
  saving,
}: BaseActionRowProps) {
  return (
    <div className="save-footer">
      <BaseStatusStack dirty={Boolean(dirty)} dirtyText={dirtyText} error={error || null} success={success || null} />
      <Button disabled={Boolean(saveDisabled)} onClick={onSave} type="button">
        {saving ? "Saqlanmoqda..." : (saveLabel || "Saqlash")}
      </Button>
    </div>
  );
}

export type SettingsBaseCardProps = {
  className?: string;
  title?: string;
  description?: string;
  icon?: ReactNode;
  header?: ReactNode;
  children: ReactNode;
  dirty?: boolean;
  dirtyText?: string;
  error?: string | null;
  success?: string | null;
  onSave?: () => void;
  saveDisabled?: boolean;
  saveLabel?: string;
  saving?: boolean;
  selectClassName?: string;
  showCustomizer?: boolean;
  customizerId?: string;
};

type CardTone = "neutral" | "blue" | "amber" | "rose";
type CardLayout = "vertical" | "horizontal";

function isCardTone(value: unknown): value is CardTone {
  return value === "neutral" || value === "blue" || value === "amber" || value === "rose";
}

function isCardLayout(value: unknown): value is CardLayout {
  return value === "vertical" || value === "horizontal";
}

export function SettingsBaseCard({
  className,
  description,
  title,
  icon,
  header,
  children,
  dirty,
  dirtyText,
  error,
  success,
  onSave,
  saveDisabled,
  saveLabel,
  saving,
  selectClassName = "settings-form-select",
  showCustomizer = true,
  customizerId,
}: SettingsBaseCardProps) {
  const autoCustomizerId = useId().replace(/:/g, "");
  const resolvedCustomizerId = customizerId || autoCustomizerId;
  const storageKey = `settings-card-customizer:${resolvedCustomizerId}`;
  const [customizeOpen, setCustomizeOpen] = useState(false);
  const [tone, setTone] = useState<CardTone>("neutral");
  const [layout, setLayout] = useState<CardLayout>("vertical");

  useEffect(() => {
    if (!showCustomizer) return;
    try {
      const raw = window.localStorage.getItem(storageKey);
      if (!raw) return;
      const parsed = JSON.parse(raw) as { layout?: unknown; tone?: unknown } | null;
      if (parsed && isCardTone(parsed.tone)) {
        setTone(parsed.tone);
      }
      if (parsed && isCardLayout(parsed.layout)) {
        setLayout(parsed.layout);
      }
    } catch {
      // ignore broken localStorage payload
    }
  }, [showCustomizer, storageKey]);

  useEffect(() => {
    if (!showCustomizer) return;
    try {
      window.localStorage.setItem(storageKey, JSON.stringify({ tone, layout }));
    } catch {
      // localStorage may be unavailable in some environments
    }
  }, [layout, showCustomizer, storageKey, tone]);

  const toneClass =
    tone === "blue"
      ? "settings-base-card--blue"
      : tone === "amber"
        ? "settings-base-card--amber"
        : tone === "rose"
          ? "settings-base-card--rose"
          : "settings-base-card--neutral";
  const layoutClass = layout === "horizontal" ? "settings-base-card--horizontal" : "settings-base-card--vertical";

  return (
    <div className={`${className || "card"} settings-base-card ${toneClass} ${layoutClass}`}>
      <div className="settings-base-card__top">
        <div className="settings-base-card__header">
          {header ? (
            header
          ) : (
            <div className="scard-hd">
              {icon ? icon : null}
              <div>
                {title ? <div className="scard-title">{title}</div> : null}
                {description ? <div className="scard-desc">{description}</div> : null}
              </div>
            </div>
          )}
        </div>
        {showCustomizer ? (
          <div className="settings-base-card__custom">
            <button
              aria-label="Karta sozlamalari"
              className="settings-card-gear"
              onClick={() => setCustomizeOpen((current) => !current)}
              type="button"
            >
              <svg fill="none" height="16" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" viewBox="0 0 24 24" width="16">
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.01a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h.01a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.01a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
            </button>
            {customizeOpen ? (
              <div className="settings-card-popover">
                <div className="settings-card-popover__title">Karta sozlamalari</div>
                <div className="settings-card-popover__row">
                  <span>Rang</span>
                  <select
                    className={`select ${selectClassName}`}
                    onChange={(event) => setTone(event.target.value as "neutral" | "blue" | "amber" | "rose")}
                    value={tone}
                  >
                    <option value="neutral">Neytral</option>
                    <option value="blue">Ko'k</option>
                    <option value="amber">Sariq</option>
                    <option value="rose">Qizil</option>
                  </select>
                </div>
                <div className="settings-card-popover__row">
                  <span>Layout</span>
                  <select
                    className={`select ${selectClassName}`}
                    onChange={(event) => setLayout(event.target.value as "vertical" | "horizontal")}
                    value={layout}
                  >
                    <option value="vertical">Vertical</option>
                    <option value="horizontal">Horizontal</option>
                  </select>
                </div>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
      <div className="settings-base-card__body">
        {children}
      </div>
      {onSave ? (
        <BaseActionRow
          dirty={dirty}
          dirtyText={dirtyText}
          error={error}
          onSave={onSave}
          saveDisabled={saveDisabled}
          saveLabel={saveLabel}
          saving={saving}
          success={success}
        />
      ) : null}
    </div>
  );
}

export function SettingsCardSection({
  label,
  icon,
  children,
  className,
}: {
  label?: ReactNode;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={className || "ssec mt-0 border-none pt-0"}>
      {label ? (
        <div className="ssec-label">
          {icon ? icon : null}
          {label}
        </div>
      ) : null}
      {children}
    </div>
  );
}

export function SettingsCardItem({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={className || "rounded-lg border border-border/50 bg-layer/20 p-3 webhook-family-item"}>{children}</div>;
}

export function SettingsInnerCard({ children }: { children: ReactNode }) {
  return (
    <SettingsBaseCard className="card webhook-family-card" showCustomizer={false}>
      {children}
    </SettingsBaseCard>
  );
}

export function ToggleRow({
  desc,
  label,
  onChange,
  value,
}: {
  label: string;
  desc?: string;
  value: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <div className={`tog-wrap${value ? " tog-on" : ""}`} onClick={() => onChange(!value)}>
      <div className="tog-info">
        <span className="tog-label">{label}</span>
        {desc ? <span className="tog-desc">{desc}</span> : null}
      </div>
      <button
        aria-pressed={value}
        className={`tog-switch${value ? " on" : ""}`}
        onClick={(event) => {
          event.stopPropagation();
          onChange(!value);
        }}
        type="button"
      />
    </div>
  );
}

export function NumberField({
  hint,
  label,
  max,
  min,
  onChange,
  required,
  value,
  inputClassName = "settings-form-input",
}: {
  label: string;
  hint?: string;
  value: string;
  onChange: (next: string) => void;
  min?: number;
  max?: number;
  required?: boolean;
  inputClassName?: string;
}) {
  const numberValue = Number(value);
  const error =
    required && value === ""
      ? "Majburiy maydon"
      : min !== undefined && numberValue < min
        ? `Minimum: ${min}`
        : max !== undefined && numberValue > max
          ? `Maksimum: ${max}`
          : null;

  return (
    <div className="field">
      <label className="field-label">{label}</label>
      <div className="num-field">
        <input
          className={`input ${inputClassName}${error ? " input-err" : ""}`}
          max={max}
          min={min}
          onChange={(event) => onChange(event.target.value)}
          type="number"
          value={value}
        />
      </div>
      {hint && !error ? <span className="field-hint">{hint}</span> : null}
      {error ? (
        <span className="err-text">
          <svg fill="none" height="12" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" width="12">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" x2="12" y1="8" y2="12" />
            <line x1="12" x2="12.01" y1="16" y2="16" />
          </svg>
          {error}
        </span>
      ) : null}
    </div>
  );
}

export function BaseInputField({
  label,
  hint,
  value,
  placeholder,
  onChange,
  type = "text",
  className = "settings-form-input",
  onBlur,
  onFocus,
  rightSlot,
}: {
  label: string;
  hint?: string;
  value: string;
  placeholder?: string;
  type?: string;
  onChange: (next: string) => void;
  className?: string;
  onBlur?: FocusEventHandler<HTMLInputElement>;
  onFocus?: FocusEventHandler<HTMLInputElement>;
  rightSlot?: ReactNode;
}) {
  return (
    <Field hint={hint} label={label}>
      {rightSlot ? (
        <div className="input-eye">
          <Input
            className={`${className} pr-10`}
            onBlur={onBlur}
            onChange={(event) => onChange(event.target.value)}
            onFocus={onFocus}
            placeholder={placeholder}
            type={type}
            value={value}
          />
          {rightSlot}
        </div>
      ) : (
        <Input
          className={className}
          onBlur={onBlur}
          onChange={(event) => onChange(event.target.value)}
          onFocus={onFocus}
          placeholder={placeholder}
          type={type}
          value={value}
        />
      )}
    </Field>
  );
}

export function BaseTextAreaField({
  className,
  hint,
  label,
  onChange,
  placeholder,
  rows = 4,
  value,
}: {
  className?: string;
  hint?: string;
  label: string;
  onChange: (next: string) => void;
  placeholder?: string;
  rows?: number;
  value: string;
}) {
  return (
    <Field hint={hint} label={label}>
      <Textarea
        className={className}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        rows={rows}
        value={value}
      />
    </Field>
  );
}

export function BaseFieldShell({
  children,
  className,
  hint,
  label,
}: {
  children: ReactNode;
  className?: string;
  hint?: ReactNode;
  label: ReactNode;
}) {
  return (
    <Field className={className} hint={hint} label={label}>
      {children}
    </Field>
  );
}

export function BaseSelectField({
  children,
  className = "settings-form-select",
  hint,
  label,
  onChange,
  value,
}: {
  children: ReactNode;
  className?: string;
  hint?: string;
  label: string;
  onChange: (next: string) => void;
  value: string;
}) {
  return (
    <Field hint={hint} label={label}>
      <Select
        className={className}
        onChange={(event) => onChange(event.target.value)}
        value={value}
      >
        {children}
      </Select>
    </Field>
  );
}

export function BaseInlineActionField({
  action,
  className = "settings-form-input",
  hint,
  label,
  min,
  onChange,
  placeholder,
  type = "text",
  value,
}: {
  action: ReactNode;
  className?: string;
  hint?: ReactNode;
  label: ReactNode;
  min?: number;
  onChange: (next: string) => void;
  placeholder?: string;
  type?: string;
  value: string | number;
}) {
  return (
    <Field hint={hint} label={label}>
      <div className="base-inline-action-field">
        <Input
          className={className}
          min={min}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          type={type}
          value={value}
        />
        {action}
      </div>
    </Field>
  );
}

export type BaseCheckOption = {
  key: string;
  label: string;
  badge?: string;
};

export function BaseCheckGroup({
  onChange,
  options,
  value,
}: {
  options: BaseCheckOption[];
  value?: string[];
  onChange: (next: string[]) => void;
}) {
  const selected = Array.isArray(value) ? value : [];
  return (
    <div className="chk-group">
      {options.map((option) => {
        const checked = selected.includes(option.key);
        return (
          <label className={`chk-item${checked ? " chk-checked" : ""}`} key={option.key}>
            <div className="chk-box">
              {checked ? (
                <svg fill="none" height="11" stroke="white" strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" viewBox="0 0 24 24" width="11">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              ) : null}
            </div>
            <input
              checked={checked}
              onChange={(event) => {
                onChange(event.target.checked ? [...selected, option.key] : selected.filter((item) => item !== option.key));
              }}
              style={{ display: "none" }}
              type="checkbox"
            />
            <span className="chk-item-label">{option.label}</span>
            {option.badge ? <span className="chk-item-badge">{option.badge}</span> : null}
          </label>
        );
      })}
    </div>
  );
}

export function BaseOrderPills({
  onChange,
  value,
}: {
  value?: string[];
  onChange: (next: string[]) => void;
}) {
  const ordered = Array.isArray(value) ? value : [];
  const [draggingIndex, setDraggingIndex] = useState<number | null>(null);
  const [overIndex, setOverIndex] = useState<number | null>(null);

  function handleDragStart(event: DragEvent<HTMLDivElement>, index: number) {
    setDraggingIndex(index);
    event.dataTransfer.effectAllowed = "move";
  }

  function handleDrop(event: DragEvent<HTMLDivElement>, index: number) {
    event.preventDefault();
    if (draggingIndex === null || draggingIndex === index) return;
    const next = [...ordered];
    const [item] = next.splice(draggingIndex, 1);
    next.splice(index, 0, item);
    onChange(next);
    setDraggingIndex(null);
    setOverIndex(null);
  }

  return (
    <div>
      <div className="order-wrap">
        {ordered.map((item, index) => (
          <div
            className="order-pill"
            draggable
            key={item}
            onDragOver={(event) => {
              event.preventDefault();
              setOverIndex(index);
            }}
            onDragStart={(event) => handleDragStart(event, index)}
            onDrop={(event) => handleDrop(event, index)}
            style={{
              opacity: overIndex === index && draggingIndex !== index ? 0.5 : 1,
              outline: overIndex === index ? "2px dashed var(--brand-border)" : "none",
            }}
          >
            <span className="order-pill-num">{index + 1}</span>
            {item}
          </div>
        ))}
      </div>
      <p className="order-hint">
        <svg fill="none" height="12" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" width="12">
          <circle cx="9" cy="5" r="1" />
          <circle cx="9" cy="12" r="1" />
          <circle cx="9" cy="19" r="1" />
          <circle cx="15" cy="5" r="1" />
          <circle cx="15" cy="12" r="1" />
          <circle cx="15" cy="19" r="1" />
        </svg>
        Tartibni o'zgartirish uchun sudrang
      </p>
    </div>
  );
}

export function BaseTagInput({
  onChange,
  placeholder = "Status qo'shing...",
  value,
}: {
  value: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
}) {
  const [inputValue, setInputValue] = useState("");

  function addTag() {
    const normalized = inputValue.trim().toUpperCase();
    if (normalized && !value.includes(normalized)) {
      onChange([...value, normalized]);
    }
    setInputValue("");
  }

  function removeTag(tag: string) {
    onChange(value.filter((item) => item !== tag));
  }

  function onInputKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      addTag();
      return;
    }
    if (event.key === "Backspace" && !inputValue && value.length) {
      removeTag(value[value.length - 1]);
    }
  }

  return (
    <div>
      <div
        className="tag-input-wrap"
        onClick={(event) => {
          const input = event.currentTarget.querySelector("input") as HTMLInputElement | null;
          input?.focus();
        }}
      >
        {value.map((tag) => (
          <span className="tag-chip" key={tag}>
            {tag}
            <button className="tag-chip-remove" onClick={() => removeTag(tag)} type="button">
              <svg fill="none" height="11" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24" width="11">
                <line x1="18" x2="6" y1="6" y2="18" />
                <line x1="6" x2="18" y1="6" y2="18" />
              </svg>
            </button>
          </span>
        ))}
        <input
          className="tag-real-input"
          onChange={(event) => setInputValue(event.target.value)}
          onKeyDown={onInputKeyDown}
          placeholder={value.length ? "" : placeholder}
          value={inputValue}
        />
      </div>
      <p className="tag-hint">Enter yoki vergul bilan qo'shing. Masalan: READY TO TEST, IN REVIEW</p>
    </div>
  );
}

export const BaseSection = SettingsCardSection;
export const BaseGroupCard = SettingsInnerCard;
export const BaseToggleRow = ToggleRow;
export const BaseNumberField = NumberField;
