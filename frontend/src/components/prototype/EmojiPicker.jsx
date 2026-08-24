import { useState } from "react";

import { EMOJI_PICKS } from "./categoriesPrototypeData.js";

// PROTOTYPE ONLY — shared by Variants B and C.

export default function EmojiPicker({ value, onChange }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="menu">
      <button type="button" className="proto-emoji-trigger" onClick={() => setOpen((o) => !o)} aria-label="Choose emoji">
        {value || "＋"}
      </button>
      {open && (
        <div className="menu__list proto-emoji-grid">
          {EMOJI_PICKS.map((emoji) => (
            <button
              key={emoji}
              type="button"
              className="proto-emoji-option"
              onClick={() => {
                onChange(emoji);
                setOpen(false);
              }}
            >
              {emoji}
            </button>
          ))}
          <input
            type="text"
            className="proto-emoji-custom"
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
