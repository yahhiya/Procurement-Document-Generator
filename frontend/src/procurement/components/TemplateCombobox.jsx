import { useEffect, useRef, useState } from "react";
import { CheckIcon } from "./icons";

// options: Array<{ id, label }>   value: selected id   onChange(id)
export default function TemplateCombobox({ options, value, onChange, id }) {
  const [isOpen, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const wrapperRef = useRef(null);
  const inputRef = useRef(null);
  const listRef = useRef(null);

  const selected = options.find((opt) => opt.id === value) || null;

  const filtered = options.filter((opt) =>
    opt.label.toLowerCase().includes(query.trim().toLowerCase())
  );

  useEffect(() => {
    function handleClickOutside(e) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setOpen(false);
        setQuery("");
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    setActiveIndex(0);
  }, [query, isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const activeEl = listRef.current?.querySelector('[data-active="true"]');
    activeEl?.scrollIntoView({ block: "nearest" });
  }, [activeIndex, isOpen]);

  const commit = (option) => {
    onChange(option.id);
    setQuery("");
    setOpen(false);
    inputRef.current?.blur();
  };

  const handleKeyDown = (e) => {
    if (!isOpen && (e.key === "ArrowDown" || e.key === "Enter")) {
      setOpen(true);
      return;
    }
    if (!isOpen) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (filtered[activeIndex]) commit(filtered[activeIndex]);
    } else if (e.key === "Escape") {
      setOpen(false);
      setQuery("");
      inputRef.current?.blur();
    }
  };

  const displayValue = selected ? selected.label : "";

  return (
    <div className="sg-combobox" ref={wrapperRef}>
      <input
        id={id}
        ref={inputRef}
        className="sg-input sg-combobox-input"
        role="combobox"
        aria-expanded={isOpen}
        aria-autocomplete="list"
        autoComplete="off"
        placeholder={displayValue}
        value={isOpen ? query : displayValue}
        onFocus={() => {
          setOpen(true);
          setQuery("");
        }}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
      />

      {isOpen && (
        <ul className="sg-combobox-list" ref={listRef} role="listbox">
          {filtered.length === 0 && (
            <li className="sg-combobox-empty">No templates match "{query}"</li>
          )}
          {filtered.map((opt, i) => (
            <li
              key={opt.id}
              role="option"
              aria-selected={opt.id === value}
              data-active={i === activeIndex}
              className={`sg-combobox-option ${i === activeIndex ? "is-active" : ""}`}
              onMouseDown={(e) => e.preventDefault()} // keep focus, avoid premature blur
              onClick={() => commit(opt)}
              onMouseEnter={() => setActiveIndex(i)}
            >
              <span>{opt.label}</span>
              {opt.id === value && <CheckIcon width={15} height={15} />}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
