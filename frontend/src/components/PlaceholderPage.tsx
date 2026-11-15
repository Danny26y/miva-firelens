type Props = {
  title: string;
  body: string;
};

export function PlaceholderPage({ title, body }: Props) {
  return (
    <div className="placeholder-page">
      <h2>{title}</h2>
      <p>{body}</p>
      <p>
        The Figma prototype includes this screen. Calendar and Season cards are
        wired to the verified Kaduna handoff first.
      </p>
    </div>
  );
}
