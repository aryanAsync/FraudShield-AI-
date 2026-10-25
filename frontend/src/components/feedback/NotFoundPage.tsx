import React from 'react'
import { Link } from 'react-router-dom'
import { ShieldAlert } from 'lucide-react'
import { Button } from '../ui/Button'

export const NotFoundPage: React.FC = () => (
  <div style={{ textAlign: 'center', padding: '60px 20px', maxWidth: '480px', margin: '0 auto' }}>
    <div style={{ color: 'var(--text-tertiary)', marginBottom: '16px' }}>
      <ShieldAlert size={48} />
    </div>
    <h2 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '8px' }}>Page Not Found</h2>
    <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
      The requested route or resource does not exist in the FraudShield console.
    </p>
    <Link to="/overview">
      <Button variant="primary" size="md">
        Return to Overview
      </Button>
    </Link>
  </div>
)
