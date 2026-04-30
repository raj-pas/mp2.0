import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/button";
import { useLogout } from "../lib/auth";

interface UserChipProps {
  name: string;
  role: string;
}

export function UserChip({ name, role }: UserChipProps) {
  const { t } = useTranslation();
  const logout = useLogout();

  const roleLabel =
    role === "advisor"
      ? t("topbar.user_role_advisor")
      : role === "financial_analyst"
        ? t("topbar.user_role_analyst")
        : role;

  return (
    <div className="flex items-baseline gap-2 text-[11px]">
      <span className="font-semibold text-ink">{name}</span>
      <span className="font-mono text-[9px] uppercase tracking-wider text-muted">{roleLabel}</span>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => logout.mutate()}
        disabled={logout.isPending}
        aria-label={t("topbar.logout")}
      >
        {t("topbar.logout")}
      </Button>
    </div>
  );
}
