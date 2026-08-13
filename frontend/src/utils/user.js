export function getDisplayName(user) {
  const fullName = [user?.first_name, user?.last_name].filter(Boolean).join(" ");
  return fullName || user?.username || "ClassFlow user";
}
