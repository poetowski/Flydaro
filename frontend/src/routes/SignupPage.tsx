import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { useLanguage } from "../i18n";
import { translateApiError } from "../i18n/translateApiError";

export function SignupPage() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const { t } = useLanguage();
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await signup(email, password, displayName);
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? translateApiError(err, t) : t("signup.signupFailed"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <LanguageSwitcher />
      <form className="auth-form" onSubmit={handleSubmit}>
        <h1>✈️ Flydaro</h1>
        <p className="subtitle">{t("signup.subtitle")}</p>
        {error && <p className="form-error">{error}</p>}
        <label>
          {t("signup.displayNameLabel")}
          <input
            required
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            autoComplete="nickname"
          />
        </label>
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
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
          />
        </label>
        <button type="submit" disabled={submitting}>
          {submitting ? t("signup.creatingAccount") : t("signup.signUp")}
        </button>
        <p className="auth-switch">
          {t("signup.alreadyHaveAccountPre")}
          <Link to="/login">{t("signup.logInLink")}</Link>
        </p>
      </form>
    </div>
  );
}
