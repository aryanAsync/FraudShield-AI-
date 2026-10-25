import React, { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Eye, EyeOff, ShieldCheck, CheckCircle2, AlertCircle } from 'lucide-react'
import { useAuth } from '../../auth/AuthContext'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { ApiClientError } from '../../api/client'
import './LoginPage.css'

export const LoginPage: React.FC = () => {
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Redirect if already authenticated
  React.useEffect(() => {
    if (isAuthenticated) {
      const from = (location.state as any)?.from?.pathname || '/overview'
      navigate(from, { replace: true })
    }
  }, [isAuthenticated, navigate, location])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMessage(null)

    const cleanEmail = email.trim()
    if (!cleanEmail) {
      setErrorMessage('Please enter your account email address.')
      return
    }

    if (!password) {
      setErrorMessage('Please enter your account password.')
      return
    }

    setIsLoading(true)
    try {
      await login({ email: cleanEmail, password })
      const from = (location.state as any)?.from?.pathname || '/overview'
      navigate(from, { replace: true })
    } catch (err) {
      if (err instanceof ApiClientError) {
        if (err.status === 401) {
          setErrorMessage('Invalid email or password.')
        } else if (err.status === 403) {
          setErrorMessage(err.message || 'Your account is deactivated. Contact an administrator.')
        } else {
          setErrorMessage(err.message || 'Sign in failed. Please try again.')
        }
      } else {
        setErrorMessage('Unable to connect to service. Please check your network.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="login-page-root">
      <div className="login-container">
        {/* Left Column: Brand & Context */}
        <div className="login-brand-panel">
          <div className="login-brand-header">
            <div className="brand-logo-icon large">
              <ShieldCheck size={26} />
            </div>
            <div className="login-brand-title">
              <span className="brand-name-fraud">Fraud</span>
              <span className="brand-name-shield">Shield</span>
              <span className="brand-tag">AI</span>
            </div>
          </div>

          <p className="login-brand-desc">
            Production-grade financial risk operations, automated inference scoring, and
            case-adjudication platform.
          </p>

          <div className="login-feature-list">
            <div className="login-feature-item">
              <CheckCircle2 size={16} className="feature-icon" />
              <span>Calibrated Random Forest probability scoring</span>
            </div>
            <div className="login-feature-item">
              <CheckCircle2 size={16} className="feature-icon" />
              <span>SHAP feature attribution explanations</span>
            </div>
            <div className="login-feature-item">
              <CheckCircle2 size={16} className="feature-icon" />
              <span>Strict state-machine investigation workflows</span>
            </div>
            <div className="login-feature-item">
              <CheckCircle2 size={16} className="feature-icon" />
              <span>Immutable security and compliance audit trail</span>
            </div>
          </div>

          <div className="login-footer-note caption">
            FraudShield AI &bull; Production v1.0.0
          </div>
        </div>

        {/* Right Column: Authentication Form */}
        <div className="login-form-panel">
          <div className="login-form-header">
            <h1 className="login-heading">Sign In</h1>
            <p className="caption">Enter your credentials to access your risk operations account.</p>
          </div>

          {errorMessage && (
            <div className="login-error-alert" role="alert">
              <AlertCircle size={16} className="alert-icon" />
              <span>{errorMessage}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="login-form" noValidate>
            <Input
              id="login-email"
              label="Work Email"
              type="email"
              autoComplete="username"
              placeholder="analyst@fraudshield.ai"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading}
              required
            />

            <Input
              id="login-password"
              label="Password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
              required
              rightAddon={
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              }
            />

            <Button
              type="submit"
              variant="primary"
              size="lg"
              isLoading={isLoading}
              className="login-submit-btn"
            >
              Sign In to Console
            </Button>
          </form>

          <div className="login-security-notice caption">
            Protected under Role-Based Access Control. All authentications and triage activities are
            logged to the immutable audit ledger.
          </div>
        </div>
      </div>
    </div>
  )
}
