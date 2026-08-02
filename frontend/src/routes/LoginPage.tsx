import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { useLanguage } from "../i18n";
import { translateApiError } from "../i18n/translateApiError";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const { t } = useLanguage();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? translateApiError(err, t) : t("login.loginFailed"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <LanguageSwitcher />
      <form className="auth-form" onSubmit={handleSubmit}>
        <h1>Flydaro</h1>
        <p className="subtitle">{t("login.subtitle")}</p>
        {error && <p className="form-error">{error}</p>}
        <label>
          {t("auth.emailLabel")}
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />
        </label>
        <label>
          {t("auth.passwordLabel")}
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </label>
        <button type="submit" disabled={submitting}>
          {submitting ? t("login.loggingIn") : t("login.logIn")}
        </button>
        <p className="auth-switch">
          {t("login.noAccountYetPre")}
          <Link to="/signup">{t("login.signUpLink")}</Link>
        </p>
      </form>
    </div>
  );
}
