import { useContext } from "react";

import NotificationContext from "./notificationContext.js";

export default function useNotifications() {
  const context = useContext(NotificationContext);
  if (!context) throw new Error("Notifications must be used inside NotificationProvider");
  return context;
}
