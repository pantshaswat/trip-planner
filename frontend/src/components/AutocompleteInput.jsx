import { useEffect, useId, useRef, useState } from 'react';
import { searchPlaces } from '../api/photon';
import './AutocompleteInput.css';

const DEBOUNCE_MS = 300;

/**
 * A text input with Photon-powered place suggestions.
 * Controlled by the parent (value / onChange). Suggestions appear while typing;
 * selecting one fills the field with its label (which the backend later geocodes).
 */
export default function AutocompleteInput({ label, value, onChange, placeholder, disabled }) {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const [active, setActive] = useState(-1);
  const [loading, setLoading] = useState(false);
  const skipFetch = useRef(false); // set true right after a selection
  const listId = useId();

  // Debounced fetch whenever the value changes while the box is open.
  // All state updates happen inside the timer/async callback (not in the effect
  // body) to avoid synchronous cascading renders.
  useEffect(() => {
    if (skipFetch.current) {
      skipFetch.current = false;
      return;
    }
    if (!open) return;

    const controller = new AbortController();
    const timer = setTimeout(async () => {
      if (value.trim().length < 3) {
        setItems([]);
        return;
      }
      setLoading(true);
      const results = await searchPlaces(value, { signal: controller.signal });
      setItems(results);
      setActive(-1);
      setLoading(false);
    }, DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [value, open]);

  function choose(item) {
    skipFetch.current = true;
    onChange(item.label);
    setItems([]);
    setOpen(false);
    setActive(-1);
  }

  function onKeyDown(e) {
    if (!open || items.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActive((a) => (a + 1) % items.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((a) => (a - 1 + items.length) % items.length);
    } else if (e.key === 'Enter') {
      if (active >= 0) {
        e.preventDefault();
        choose(items[active]);
      }
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  }

  const showList = open && (items.length > 0 || loading);

  return (
    <label className="field ac-field">
      <span className="field-label">{label}</span>
      <div className="ac-wrap">
        <input
          className="field-input"
          type="text"
          value={value}
          placeholder={placeholder}
          autoComplete="off"
          role="combobox"
          aria-expanded={showList}
          aria-controls={listId}
          aria-autocomplete="list"
          disabled={disabled}
          required
          onChange={(e) => { onChange(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          onBlur={() => setOpen(false)}
          onKeyDown={onKeyDown}
        />
        {showList && (
          <ul className="ac-list" id={listId} role="listbox">
            {loading && items.length === 0 && (
              <li className="ac-item ac-empty">Searching…</li>
            )}
            {items.map((item, i) => (
              <li
                key={item.id}
                role="option"
                aria-selected={i === active}
                className={`ac-item ${i === active ? 'is-active' : ''}`}
                // onMouseDown (not onClick) so it fires before the input blur.
                onMouseDown={(e) => { e.preventDefault(); choose(item); }}
                onMouseEnter={() => setActive(i)}
              >
                {item.label}
              </li>
            ))}
          </ul>
        )}
      </div>
    </label>
  );
}
