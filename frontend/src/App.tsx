/**
 * v36 advisor console shell — Phase R2 chrome.
 *
 * BrowserRouter + auth gate + topbar + per-route ErrorBoundary
 * (locked decision #31a). Stage content is empty in R2; R3 fills
 * HouseholdRoute / AccountRoute / GoalRoute with the three-view stage.
 */
import { useEffect, useMemo, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import { ErrorBoundary } from "./components/ErrorBoundary";
import { ContextPanel, type ContextPanelKind } from "./ctx-panel/ContextPanel";
import { TopBar } from "./chrome/TopBar";
import { useRememberedClientId } from "./chrome/ClientPicker";
import { type GroupByMode } from "./chrome/ModeToggle";
import { useLocalStorage } from "./lib/local-storage";
import { isAdvisorRole, isAnalystRole, useSession, type SessionUser } from "./lib/auth";
import { AccountRoute } from "./routes/AccountRoute";
import { CmaRoute } from "./routes/CmaRoute";
import { GoalRoute } from "./routes/GoalRoute";
import { HouseholdRoute } from "./routes/HouseholdRoute";
import { LoginRoute } from "./routes/LoginRoute";
import { MethodologyRoute } from "./routes/MethodologyRoute";
import { ReviewRoute } from "./routes/ReviewRoute";
import { HouseholdWizard } from "./wizard/HouseholdWizard";

function App() {
  return (
    <BrowserRouter>
      <SessionGate />
    </BrowserRouter>
  );
}

function SessionGate() {
  const { t } = useTranslation();
  const session = useSession();

  if (session.isPending) {
    return <FullScreenStatus tone="muted" message={t("auth.checking")} role="status" />;
  }

  if (session.isError) {
    return <FullScreenStatus tone="danger" message={t("empty.backend_unavailable")} role="alert" />;
  }

  if (!session.data?.authenticated) {
    return <LoginRoute />;
  }

  const user = session.data.user;
  const role = user.role;

  if (isAdvisorRole(role) || isAnalystRole(role)) {
    return <AuthenticatedShell role={role as "advisor" | "financial_analyst"} user={user} />;
  }
  return <FullScreenStatus tone="danger" message={t("auth.role_unsupported")} role="alert" />;
}

function FullScreenStatus({
  tone,
  message,
  role,
}: {
  tone: "muted" | "danger";
  message: string;
  role: "status" | "alert";
}) {
  const className =
    tone === "danger"
      ? "font-mono text-[10px] uppercase tracking-widest text-danger"
      : "font-mono text-[10px] uppercase tracking-widest text-muted";
  return (
    <div className="flex min-h-screen items-center justify-center bg-paper">
      <p role={role} className={className}>
        {message}
      </p>
    </div>
  );
}

function AuthenticatedShell({
  role,
  user,
}: {
  role: "advisor" | "financial_analyst";
  user: SessionUser;
}) {
  const navigate = useNavigate();
  const location = useLocation();
  const [rememberedId, setRememberedId] = useRememberedClientId();
  const [groupBy, setGroupBy] = useLocalStorage<GroupByMode>("mp20_group_by", "by-account");

  // Analysts only see CMA — bounce root → /cma on first paint.
  useEffect(() => {
    if (role === "financial_analyst" && location.pathname === "/") {
      navigate("/cma", { replace: true });
    }
  }, [role, location.pathname, navigate]);

  const showClientControls = role === "advisor";

  return (
    <div className="flex min-h-screen flex-col bg-paper text-ink">
      <TopBar
        selectedClientId={rememberedId}
        onSelectClient={(id) => {
          setRememberedId(id);
          navigate("/");
        }}
        groupBy={groupBy}
        onChangeGroupBy={setGroupBy}
        user={{ name: user.name, role: user.role }}
        showClientControls={showClientControls}
      />
      <div className="flex flex-1 overflow-hidden">
        <RouteHost role={role} />
      </div>
    </div>
  );
}

function RouteHost({ role }: { role: "advisor" | "financial_analyst" }) {
  const isAdvisor = role === "advisor";
  return (
    <Routes>
      <Route
        path="/"
        element={
          isAdvisor ? (
            <StageWithContext kind="household">
              <HouseholdRoute />
            </StageWithContext>
          ) : (
            <Navigate to="/cma" replace />
          )
        }
      />
      <Route
        path="/account/:accountId"
        element={
          isAdvisor ? (
            <StageWithContext kind="account">
              <AccountRoute />
            </StageWithContext>
          ) : (
            <Navigate to="/cma" replace />
          )
        }
      />
      <Route
        path="/goal/:goalId"
        element={
          isAdvisor ? (
            <StageWithContext kind="goal">
              <GoalRoute />
            </StageWithContext>
          ) : (
            <Navigate to="/cma" replace />
          )
        }
      />
      <Route
        path="/wizard/new"
        element={
          isAdvisor ? (
            <RouteFrame scope="wizard">
              <HouseholdWizard />
            </RouteFrame>
          ) : (
            <Navigate to="/cma" replace />
          )
        }
      />
      <Route
        path="/review"
        element={
          isAdvisor ? (
            <RouteFrame scope="review">
              <ReviewRoute />
            </RouteFrame>
          ) : (
            <Navigate to="/cma" replace />
          )
        }
      />
      <Route
        path="/cma"
        element={
          <RouteFrame scope="cma">
            <CmaRoute />
          </RouteFrame>
        }
      />
      <Route
        path="/methodology"
        element={
          <RouteFrame scope="methodology">
            <MethodologyRoute />
          </RouteFrame>
        }
      />
      <Route path="*" element={<Navigate to={isAdvisor ? "/" : "/cma"} replace />} />
    </Routes>
  );
}

function StageWithContext({ kind, children }: { kind: ContextPanelKind; children: ReactNode }) {
  const breadcrumb = useMemo(() => buildBreadcrumb(kind), [kind]);
  return (
    <RouteFrame scope={kind}>
      <div className="flex flex-1 overflow-hidden">
        <div className="flex flex-1 flex-col overflow-hidden">{children}</div>
        <ContextPanel kind={kind} breadcrumb={breadcrumb} />
      </div>
    </RouteFrame>
  );
}

function RouteFrame({ scope, children }: { scope: string; children: ReactNode }) {
  return (
    <ErrorBoundary scope={scope}>
      <div className="flex flex-1 overflow-hidden">{children}</div>
    </ErrorBoundary>
  );
}

function buildBreadcrumb(kind: ContextPanelKind): string[] {
  if (kind === "household") return ["Household"];
  if (kind === "account") return ["Household", "Account"];
  return ["Household", "Account", "Goal"];
}

export default App;
