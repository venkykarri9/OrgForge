const COLORS: Record<string, string> = {
  BACKLOG: "bg-gray-100 text-gray-600",
  STORY_LOADED: "bg-blue-100 text-blue-700",
  TDD_DRAFTED: "bg-yellow-100 text-yellow-700",
  TDD_APPROVED: "bg-green-100 text-green-700",
  IN_DEVELOPMENT: "bg-purple-100 text-purple-700",
  PACKAGE_READY: "bg-orange-100 text-orange-700",
  VALIDATING: "bg-yellow-100 text-yellow-700",
  VALIDATED: "bg-teal-100 text-teal-700",
  DEPLOYING: "bg-orange-100 text-orange-700",
  DEPLOYED: "bg-green-100 text-green-700",
  COMMITTED: "bg-indigo-100 text-indigo-700",
  PR_OPEN: "bg-blue-100 text-blue-700",
  MERGED: "bg-green-200 text-green-800",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded font-medium ${COLORS[status] ?? "bg-gray-100 text-gray-600"}`}>
      {status}
    </span>
  );
}
