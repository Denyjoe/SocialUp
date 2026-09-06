export const PANEL_API_ENDPOINT = `${window.location.origin.replace("5173", "8000")}/api/v2/`;

/** The action names are part of the wire protocol, so they stay literal.
 * Everything a human reads is a translation key. */
export const PANEL_API_ACTIONS: { action: string; paramsKey: string; descriptionKey: string }[] = [
  { action: "services", paramsKey: "apiAction.services.params", descriptionKey: "apiAction.services.description" },
  { action: "add", paramsKey: "apiAction.add.params", descriptionKey: "apiAction.add.description" },
  { action: "status", paramsKey: "apiAction.status.params", descriptionKey: "apiAction.status.description" },
  { action: "balance", paramsKey: "apiAction.balance.params", descriptionKey: "apiAction.balance.description" },
];
