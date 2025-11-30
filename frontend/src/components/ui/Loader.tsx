import React from 'react'
import './Loader.css'

interface LoaderProps {
  size?: 'small' | 'medium' | 'large'
  variant?: 'spinner' | 'pulse'
}

export const Loader: React.FC<LoaderProps> = ({
  size = 'medium',
  variant = 'spinner',
}) => {
  return (
    <div className={`loader loader-${size} loader-${variant}`}>
      {variant === 'spinner' ? (
        <div className="spinner"></div>
      ) : (
        <div className="pulse"></div>
      )}
    </div>
  )
}

export const PageLoader: React.FC = () => {
  return (
    <div className="page-loader">
      <Loader size="large" variant="spinner" />
      <p>Loading...</p>
    </div>
  )
}
