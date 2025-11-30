import React, { useState } from 'react'
import { Button } from './Button'
import './Modal.css'

interface ModalProps {
  isOpen: boolean
  title: string
  children: React.ReactNode
  onClose: () => void
  footer?: React.ReactNode
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  title,
  children,
  onClose,
  footer,
}) => {
  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{title}</h2>
          <button className="modal-close" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>
  )
}

interface CreateConversationModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: (title: string) => void
  isLoading?: boolean
}

export const CreateConversationModal: React.FC<
  CreateConversationModalProps
> = ({ isOpen, onClose, onConfirm, isLoading = false }) => {
  const [title, setTitle] = useState('')
  const [error, setError] = useState('')

  const handleConfirm = () => {
    if (!title.trim()) {
      setError('Conversation title is required')
      return
    }
    onConfirm(title)
    setTitle('')
    setError('')
  }

  const handleClose = () => {
    setTitle('')
    setError('')
    onClose()
  }

  if (!isOpen) return null

  return (
    <Modal
      isOpen={isOpen}
      title="Create New Conversation"
      onClose={handleClose}
      footer={
        <div className="modal-actions">
          <Button variant="secondary" onClick={handleClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleConfirm}
            isLoading={isLoading}
            disabled={!title.trim() || isLoading}
          >
            Create
          </Button>
        </div>
      }
    >
      <div className="form-group">
        <label htmlFor="conversation-title" className="input-label">
          Conversation Title
        </label>
        <input
          id="conversation-title"
          type="text"
          value={title}
          onChange={(e) => {
            setTitle(e.target.value)
            if (error) setError('')
          }}
          placeholder="e.g., Project Analysis, Document Review"
          className={`input ${error ? 'input-error' : ''}`}
          disabled={isLoading}
          autoFocus
          onKeyDown={(e) => {
            if (e.key === 'Enter' && title.trim() && !isLoading) {
              handleConfirm()
            }
            if (e.key === 'Escape') {
              handleClose()
            }
          }}
        />
        {error && <span className="input-error-text">{error}</span>}
      </div>
    </Modal>
  )
}
