// PROTOTYPE ONLY — seed data for the Category management UI exploration.
// Mirrors the real (currently hardcoded) list in src/transaction_log/categories.py
// so the variants feel like this app, not a toy dataset.

export const TYPE_ORDER = ["Income", "Expense", "Debt", "Transfer"];

export function seedCategories() {
  return [
    { id: 1, type: "Income", name: "Salary", emoji: "💼", locked: false },
    { id: 2, type: "Income", name: "Rental", emoji: "🏠", locked: false },
    { id: 3, type: "Expense", name: "Groceries", emoji: "🛒", locked: false },
    { id: 4, type: "Expense", name: "Dining & Takeaway", emoji: "🍔", locked: false },
    { id: 5, type: "Expense", name: "Transport", emoji: "🚗", locked: false },
    { id: 6, type: "Expense", name: "Shopping & Retail", emoji: "🛍️", locked: false },
    { id: 7, type: "Expense", name: "Holidays & Travel", emoji: "✈️", locked: false },
    { id: 8, type: "Expense", name: "Entertainment & Leisure", emoji: "🎬", locked: false },
    { id: 9, type: "Expense", name: "Health & Medical", emoji: "🏥", locked: false },
    { id: 10, type: "Expense", name: "Donations & Giving", emoji: "", locked: false },
    { id: 11, type: "Expense", name: "Subscriptions", emoji: "📺", locked: false },
    { id: 12, type: "Expense", name: "Insurance & Bills", emoji: "", locked: false },
    { id: 13, type: "Expense", name: "Rental Expense", emoji: "🏠", locked: false },
    { id: 14, type: "Expense", name: "Beem Adjustment", emoji: "🔄", locked: true },
    { id: 15, type: "Debt", name: "Mortgage Repayment", emoji: "🏦", locked: false },
  ];
}

// A curated quick-pick set for the emoji picker — free text still works
// alongside it, this is just a shortcut for common choices.
export const EMOJI_PICKS = [
  "🛒", "🍔", "🚗", "🛍️", "✈️", "🎬", "🏥", "❤️", "📺", "🧾", "🏠", "💰",
  "🏦", "💳", "📈", "🎁", "⚡", "📱", "🐾", "☕", "🔄", "🎓", "🧘", "🐶",
];
