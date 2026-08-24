import { useState } from "react";

import { EMOJI_PICKS } from "../lib/categories.js";

// A Category's optional emoji (Issue #91) - a curated quick-pick grid plus a
// free-text field, since the curated set can never cover every emoji a user
// might want.
export default function EmojiPicker({ value, onChange }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="emoji-picker">
      <button
        type="button"
        className="emoji-picker__trigger"
        aria-label="Choose emoji"
        onClick={() => setOpen((current) => !current)}
      >
        {value || "+"}
      </button>
      {open && (
        <div className="emoji-picker__panel">
          <div className="emoji-picker__grid">
            {EMOJI_PICKS.map((emoji) => (
              <button
                key={emoji}
                type="button"
                className="emoji-picker__option"
                aria-label={`Use ${emoji}`}
                onClick={() => {
                  onChange(emoji);
                  setOpen(false);
                }}
              >
                {emoji}
              </button>
            ))}
          </div>
          <input
            type="text"
            className="emoji-picker__custom"
            aria-label="Custom emoji"
            placeholder="or paste any emoji"
            value={value}
            maxLength={4}
            onChange={(event) => onChange(event.target.value)}
          />
        </div>
      )}
    </div>
  );
}
