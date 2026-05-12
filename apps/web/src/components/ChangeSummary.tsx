type Props = {
  summary: string;
  projectStatus: string[];
};

export function ChangeSummary({ summary, projectStatus }: Props) {
  return (
    <section className="change-summary" aria-label="Change tracking summary">
      <span>{summary}</span>
      <details>
        <summary>Tracking status</summary>
        <ol>
          {projectStatus.map((status) => (
            <li key={status}>{status}</li>
          ))}
        </ol>
      </details>
    </section>
  );
}
