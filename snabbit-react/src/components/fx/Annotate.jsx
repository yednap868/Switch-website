/* Hand-drawn mark behind a word: an underline sweep, a scribbled circle or an
   arrow. The CSS animates clip-path from `inset(0 100% 0 0)`, offset by
   --annotation-delay. */

export default function Annotate({ as: Tag = 'span', kind = 'underline', delay = 0, children }) {
  return (
    <Tag
      className={`annotated annotated-${kind}`}
      style={{ '--annotation-delay': `${delay}s` }}
      data-annotate={kind}
    >
      {children}
    </Tag>
  )
}
