"use client";

import {
  useState,
  type DragEvent,
  type FocusEventHandler,
  type KeyboardEvent,
  type ReactNode,
} from "react";

import { Button } from "@/components/ui/button";
import { BaseCard } from "@/components/ui/card";
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
  collapsible?: boolean;
  defaultCollapsed?: boolean;
  collapsed?: boolean;
  onCollapsedChange?: (next: boolean) => void;
};

function sanitizeBaseCardClassName(className?: string) {
  return className
    ?.split(/\s+/)
    .filter((item) => {
      if (!item || item === "card") return false;
      if (item.startsWith("rounded")) return false;
      if (item === "border" || item.startsWith("border-")) return false;
      if (item.startsWith("bg-")) return false;
      if (item.startsWith("shadow")) return false;
      return true;
    })
    .join(" ");
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
  showCustomizer = true,
  customizerId,
  collapsible = true,
  defaultCollapsed = false,
  collapsed,
  onCollapsedChange,
}: SettingsBaseCardProps) {
  const sanitizedClassName = sanitizeBaseCardClassName(className);

  return (
    <BaseCard
      bodyClassName="settings-base-card__body"
      className={`settings-base-card ${sanitizedClassName || ""}`}
      collapsed={collapsed}
      collapsible={collapsible}
      defaultCollapsed={defaultCollapsed}
      description={description}
      footer={onSave ? (
        <div className="bc-body-save">
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
        </div>
      ) : null}
      header={header}
      icon={icon}
      onCollapsedChange={onCollapsedChange}
      padding="none"
      settingsId={customizerId}
      showSettings={showCustomizer}
      title={title}
    >
      {children}
    </BaseCard>
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
    <SettingsInnerCard>
      <div className={className || "ssec mt-0 border-none pt-0"}>
        {label ? (
          <div className="ssec-label">
            {icon ? icon : null}
            {label}
          </div>
        ) : null}
        {children}
      </div>
    </SettingsInnerCard>
  );
}

export function SettingsCardItem({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={sanitizeBaseCardClassName(className) || "settings-row webhook-family-item"}>
      {children}
    </div>
  );
}

export function SettingsInnerCard({
  children,
  collapsible = false,
  defaultCollapsed = false,
}: {
  children: ReactNode;
  collapsible?: boolean;
  defaultCollapsed?: boolean;
}) {
  return (
    <BaseCard
      as="div"
      className="settings-subsection webhook-family-card"
      collapsible={collapsible}
      defaultCollapsed={defaultCollapsed}
      tone="soft"
    >
      {children}
    </BaseCard>
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
  available = ["tz", "comments", "figma", "custom_context", "code"],
  onChange,
  required = [],
  value,
}: {
  value?: string[];
  onChange: (next: string[]) => void;
  available?: string[];
  required?: string[];
}) {
  const ordered = Array.isArray(value) ? Array.from(new Set(value)) : [];
  const availableItems = Array.from(new Set(available));
  const inactiveItems = availableItems.filter((item) => !ordered.includes(item));
  const requiredItems = new Set(required);
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

  function removeItem(item: string) {
    if (requiredItems.has(item)) return;
    onChange(ordered.filter((current) => current !== item));
  }

  function addItem(item: string) {
    if (ordered.includes(item)) return;
    onChange([...ordered, item]);
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
            <span className="order-pill-label">{item}</span>
            {!requiredItems.has(item) ? (
              <button
                aria-label={`${item} ni olib tashlash`}
                className="order-pill-remove"
                draggable={false}
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  removeItem(item);
                }}
                onDragStart={(event) => event.preventDefault()}
                onMouseDown={(event) => event.stopPropagation()}
                type="button"
              >
                x
              </button>
            ) : null}
          </div>
        ))}
      </div>
      {inactiveItems.length > 0 ? (
        <div className="order-add-wrap">
          <span className="order-add-label">Qo'shish:</span>
          {inactiveItems.map((item) => (
            <button
              className="order-add-pill"
              key={item}
              onClick={() => addItem(item)}
              type="button"
            >
              + {item}
            </button>
          ))}
        </div>
      ) : null}
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
