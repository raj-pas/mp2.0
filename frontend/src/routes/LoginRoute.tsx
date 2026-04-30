import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/button";
import { useLogin } from "../lib/auth";
import { normalizeApiError } from "../lib/api-error";
import { cn } from "../lib/cn";

export function LoginRoute() {
  const { t } = useTranslation();
  const login = useLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    login.mutate({ email, password });
  }

  const errorMessage =
    login.error !== null && login.error !== undefined
      ? normalizeApiError(login.error, t("auth.generic_error")).message
      : null;

  return (
    <div className="flex min-h-screen items-center justify-center bg-paper px-4">
      <form
        onSubmit={handleSubmit}
        className={cn(
          "w-full max-w-sm border border-hairline-2 bg-paper-2 p-8 shadow-sm",
          "flex flex-col gap-4",
        )}
        aria-labelledby="login-title"
      >
        <h1 id="login-title" className="font-serif text-2xl font-medium tracking-tight text-ink">
          {t("auth.login_title")}
        </h1>
        <label className="flex flex-col gap-1">
          <span className="font-mono text-[10px] uppercase tracking-widest text-muted">
            {t("auth.email_label")}
          </span>
          <input
            type="email"
            required
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="border border-hairline-2 bg-paper px-3 py-2 font-sans text-sm text-ink focus:border-accent focus:outline-none"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="font-mono text-[10px] uppercase tracking-widest text-muted">
            {t("auth.password_label")}
          </span>
          <input
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="border border-hairline-2 bg-paper px-3 py-2 font-sans text-sm text-ink focus:border-accent focus:outline-none"
          />
        </label>
        {errorMessage !== null && (
          <p role="alert" className="font-mono text-[10px] uppercase tracking-widest text-danger">
            {errorMessage}
          </p>
        )}
        <Button type="submit" disabled={login.isPending} size="lg">
          {login.isPending ? t("auth.checking") : t("auth.submit")}
        </Button>
      </form>
    </div>
  );
}
