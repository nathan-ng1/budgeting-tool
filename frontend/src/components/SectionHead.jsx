// A section break on the Overview: a rule, a title and a one-line subheader,
// with an optional control (the Breakdown's section tabs) on the right.
export default function SectionHead({ title, note, children }) {
  return (
    <div className="section-head">
      <div>
        <h2>{title}</h2>
        {note && <p>{note}</p>}
      </div>
      {children}
    </div>
  );
}
