// A row of exclusive choices drawn as the Budget tab's Simple | Advanced toggle
// (.detail-seg): `options` is a list of [key, label] pairs and `value` the key
// currently shown.
export default function SegmentedControl({ label, options, value, onChange }) {
  return (
    <div className="detail-seg" role="group" aria-label={label}>
      {options.map(([key, text]) => (
        <button key={key} type="button" aria-pressed={value === key} onClick={() => onChange(key)}>
          {text}
        </button>
      ))}
    </div>
  );
}
