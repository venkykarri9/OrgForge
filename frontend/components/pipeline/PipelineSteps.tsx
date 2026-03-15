const STEPS = [
  "STORY_LOADED",
  "TDD_DRAFTED",
  "TDD_APPROVED",
  "IN_DEVELOPMENT",
  "PACKAGE_READY",
  "VALIDATING",
  "VALIDATED",
  "DEPLOYING",
  "DEPLOYED",
  "COMMITTED",
  "PR_OPEN",
  "MERGED",
];

export function PipelineSteps({ currentStatus }: { currentStatus: string }) {
  const currentIdx = STEPS.indexOf(currentStatus);

  return (
    <ol className="flex items-center gap-0 overflow-x-auto">
      {STEPS.map((step, i) => {
        const done = i < currentIdx;
        const active = i === currentIdx;
        return (
          <li key={step} className="flex items-center">
            <div
              className={`text-xs px-2 py-1 rounded whitespace-nowrap ${
                active
                  ? "bg-blue-600 text-white font-semibold"
                  : done
                  ? "bg-green-100 text-green-700"
                  : "bg-gray-100 text-gray-400"
              }`}
            >
              {step.replace(/_/g, " ")}
            </div>
            {i < STEPS.length - 1 && (
              <div className={`h-0.5 w-4 ${done ? "bg-green-400" : "bg-gray-200"}`} />
            )}
          </li>
        );
      })}
    </ol>
  );
}
