import React from 'react'
import './Card.css'

interface CardProps {
  children: React.ReactNode
  className?: string
  onClick?: () => void
}

export const Card: React.FC<CardProps> = ({ children, className, onClick }) => {
  return (
    <div className={`card ${className || ''}`} onClick={onClick}>
      {children}
    </div>
  )
}

interface CardHeaderProps {
  children: React.ReactNode
}

export const CardHeader: React.FC<CardHeaderProps> = ({ children }) => (
  <div className="card-header">{children}</div>
)

interface CardBodyProps {
  children: React.ReactNode
}

export const CardBody: React.FC<CardBodyProps> = ({ children }) => (
  <div className="card-body">{children}</div>
)

interface CardFooterProps {
  children: React.ReactNode
}

export const CardFooter: React.FC<CardFooterProps> = ({ children }) => (
  <div className="card-footer">{children}</div>
)
