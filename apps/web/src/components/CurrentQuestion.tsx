import type { Choice } from "../lib/mockState";

type Props = {
  text: string;
  whyThisMatters: string;
  choices: Choice[];
};

export function CurrentQuestion({ text, whyThisMatters, choices }: Props) {
  return (
    <section className="question-panel" aria-labelledby="current-question">
      <p className="eyebrow">Current question</p>
      <h2 id="current-question">{text}</h2>
      <p className="why">{whyThisMatters}</p>

      <div className="choice-grid" aria-label="Answer choices">
        {choices.map((choice) => (
          <button key={choice.id} type="button" className="choice-button">
            {choice.label}
          </button>
        ))}
      </div>

      <label className="amend-field">
        <span>Amend answer</span>
        <textarea placeholder="Add details or correct the answer here." rows={4} />
      </label>
    </section>
  );
}
