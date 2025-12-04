import React, { useState, useEffect } from 'react'
import { Button, Card, CardBody, Input, PageLoader } from '../components/ui'
import { CollectionConfigModal } from '../components/Documents'
import { apiClient } from '../services/api'
import { Collection, Document, DocumentContent, DocumentStatus, UpdateCollectionRequest } from '../types'
import './Documents.css'

interface UploadProgress {
  filename: string
  status: 'uploading' | 'processing' | 'done' | 'error'
  error?: string
  documentId?: string
}

export const Documents: React.FC = () => {
  const [collections, setCollections] = useState<Collection[]>([])
  const [selectedCollection, setSelectedCollection] = useState<string>('')
  const [documents, setDocuments] = useState<Document[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [uploadProgress, setUploadProgress] = useState<UploadProgress[]>([])
  const [newCollectionName, setNewCollectionName] = useState('')
  const [showNewCollection, setShowNewCollection] = useState(false)
  const [processingDoc, setProcessingDoc] = useState<string | null>(null)
  const [previewModal, setPreviewModal] = useState<DocumentContent | null>(null)
  const [loadingPreview, setLoadingPreview] = useState(false)
  const [deleteModal, setDeleteModal] = useState<Document | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [configModalOpen, setConfigModalOpen] = useState(false)
  const [deleteCollectionModal, setDeleteCollectionModal] = useState<Collection | null>(null)
  const [isDeletingCollection, setIsDeletingCollection] = useState(false)

  // Get the currently selected collection object
  const currentCollection = collections.find(c => c.id === selectedCollection)

  useEffect(() => {
    loadCollections()
  }, [])

  useEffect(() => {
    if (selectedCollection) {
      loadDocuments()
    }
  }, [selectedCollection])

  const loadCollections = async () => {
    try {
      setIsLoading(true)
      const data = await apiClient.listCollections()
      setCollections(data)
      if (data.length > 0) {
        setSelectedCollection(data[0].id)
      }
    } catch (error) {
      console.error('Failed to load collections:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const loadDocuments = async () => {
    try {
      const data = await apiClient.listDocuments(selectedCollection)
      setDocuments(data)
    } catch (error) {
      console.error('Failed to load documents:', error)
    }
  }

  const handleCreateCollection = async () => {
    if (!newCollectionName.trim()) return

    try {
      await apiClient.createCollection(newCollectionName, 'nomic-embed-text', 768)
      setNewCollectionName('')
      setShowNewCollection(false)
      loadCollections()
    } catch (error) {
      console.error('Failed to create collection:', error)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !selectedCollection) return

    const files = Array.from(e.target.files)

    // Initialize progress for all files
    setUploadProgress(files.map(f => ({ filename: f.name, status: 'uploading' })))

    // Upload and process files sequentially
    for (let i = 0; i < files.length; i++) {
      const file = files[i]

      try {
        // Update status to uploading
        setUploadProgress(prev =>
          prev.map((p, idx) =>
            idx === i ? { ...p, status: 'uploading' } : p
          )
        )

        // Upload the document
        const uploadedDoc = await apiClient.uploadDocument(selectedCollection, file)

        // Update status to processing
        setUploadProgress(prev =>
          prev.map((p, idx) =>
            idx === i ? { ...p, status: 'processing', documentId: uploadedDoc.id } : p
          )
        )

        // Automatically process the document
        try {
          await apiClient.processDocument(uploadedDoc.id)
          // Update status to done
          setUploadProgress(prev =>
            prev.map((p, idx) =>
              idx === i ? { ...p, status: 'done' } : p
            )
          )
        } catch (processError) {
          // Processing failed but upload succeeded
          const errorMessage = processError instanceof Error ? processError.message : 'Processing failed'
          setUploadProgress(prev =>
            prev.map((p, idx) =>
              idx === i ? { ...p, status: 'error', error: `Processing failed: ${errorMessage}` } : p
            )
          )
        }
      } catch (error) {
        // Upload failed
        const errorMessage = error instanceof Error ? error.message : 'Upload failed'
        setUploadProgress(prev =>
          prev.map((p, idx) =>
            idx === i ? { ...p, status: 'error', error: errorMessage } : p
          )
        )
      }
    }

    // Reload documents and clear progress after a delay
    loadDocuments()
    setTimeout(() => setUploadProgress([]), 5000)
    e.target.value = ''
  }

  const handleRetryProcessing = async (documentId: string) => {
    try {
      setProcessingDoc(documentId)
      await apiClient.processDocument(documentId)
      loadDocuments()
    } catch (error) {
      console.error('Failed to process document:', error)
      loadDocuments() // Reload to show updated error status
    } finally {
      setProcessingDoc(null)
    }
  }

  const handlePreviewDocument = async (documentId: string) => {
    try {
      setLoadingPreview(true)
      const content = await apiClient.getDocumentContent(documentId)
      setPreviewModal(content)
    } catch (error) {
      console.error('Failed to load document content:', error)
      alert('Failed to load document content.')
    } finally {
      setLoadingPreview(false)
    }
  }

  const handleDeleteClick = (doc: Document) => {
    setDeleteModal(doc)
  }

  const handleConfirmDelete = async () => {
    if (!deleteModal) return

    try {
      setIsDeleting(true)
      await apiClient.deleteDocument(deleteModal.id)
      setDeleteModal(null)
      loadDocuments()
    } catch (error) {
      console.error('Failed to delete document:', error)
    } finally {
      setIsDeleting(false)
    }
  }

  const handleSaveCollectionConfig = async (data: UpdateCollectionRequest) => {
    if (!selectedCollection) return

    await apiClient.updateCollection(selectedCollection, data)
    // Reload collections to reflect changes
    await loadCollections()
  }

  const handleDeleteCollectionClick = () => {
    if (currentCollection) {
      setDeleteCollectionModal(currentCollection)
    }
  }

  const handleConfirmDeleteCollection = async () => {
    if (!deleteCollectionModal) return

    try {
      setIsDeletingCollection(true)
      await apiClient.deleteCollection(deleteCollectionModal.id)
      setDeleteCollectionModal(null)
      setSelectedCollection('')
      await loadCollections()
    } catch (error) {
      console.error('Failed to delete collection:', error)
    } finally {
      setIsDeletingCollection(false)
    }
  }

  const getStatusBadge = (status: DocumentStatus) => {
    const badges: Record<DocumentStatus, { label: string; className: string }> = {
      pending: { label: 'Pending', className: 'status-badge pending' },
      processing: { label: 'Processing...', className: 'status-badge processing' },
      completed: { label: 'Ready', className: 'status-badge completed' },
      failed: { label: 'Failed', className: 'status-badge failed' },
    }
    return badges[status]
  }

  if (isLoading) {
    return <PageLoader />
  }

  return (
    <div className="documents-container">
      <div className="documents-header">
        <h2>Document Management</h2>
        <Button
          variant="primary"
          onClick={() => setShowNewCollection(!showNewCollection)}
        >
          + New Collection
        </Button>
      </div>

      {showNewCollection && (
        <Card className="new-collection-form">
          <CardBody>
            <div className="form-group">
              <Input
                label="Collection Name"
                value={newCollectionName}
                onChange={(e) => setNewCollectionName(e.target.value)}
                placeholder="e.g., Technical Documentation"
              />
            </div>
            <div className="form-actions">
              <Button
                variant="primary"
                onClick={handleCreateCollection}
                disabled={!newCollectionName.trim()}
              >
                Create
              </Button>
              <Button
                variant="secondary"
                onClick={() => {
                  setShowNewCollection(false)
                  setNewCollectionName('')
                }}
              >
                Cancel
              </Button>
            </div>
          </CardBody>
        </Card>
      )}

      {collections.length === 0 ? (
        <Card>
          <CardBody>
            <p>No collections yet. Create one to get started.</p>
          </CardBody>
        </Card>
      ) : (
        <>
          <div className="collection-selector">
            <label htmlFor="collection">Select Collection</label>
            <div className="collection-selector-row">
              <select
                id="collection"
                value={selectedCollection}
                onChange={(e) => setSelectedCollection(e.target.value)}
                className="select-input"
              >
                {collections.map((col) => (
                  <option key={col.id} value={col.id}>
                    {col.name} ({col.document_count} docs)
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="collection-settings-btn"
                onClick={() => setConfigModalOpen(true)}
                title="Collection Settings"
                aria-label="Collection Settings"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="3" />
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
                </svg>
              </button>
              <button
                type="button"
                className="collection-delete-btn"
                onClick={handleDeleteCollectionClick}
                title="Delete Collection"
                aria-label="Delete Collection"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="3 6 5 6 21 6" />
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                  <line x1="10" y1="11" x2="10" y2="17" />
                  <line x1="14" y1="11" x2="14" y2="17" />
                </svg>
              </button>
            </div>
          </div>

          <div className="upload-section">
            <Card>
              <CardBody>
                <h3>Upload Documents</h3>
                <p className="upload-description">
                  Supported formats: TXT, PDF, MD. Documents will be processed automatically after upload.
                </p>
                <label className="file-upload-label">
                  <input
                    type="file"
                    onChange={handleFileUpload}
                    disabled={uploadProgress.length > 0}
                    accept=".txt,.pdf,.md"
                    multiple
                    className="file-input"
                  />
                  <span className="upload-button">
                    {uploadProgress.length > 0 ? 'Uploading...' : 'Choose Files'}
                  </span>
                </label>

                {uploadProgress.length > 0 && (
                  <div className="upload-progress">
                    {uploadProgress.map((progress, idx) => (
                      <div key={idx} className={`progress-item ${progress.status}`}>
                        <span className="progress-filename">{progress.filename}</span>
                        <span className="progress-status">
                          {progress.status === 'uploading' && 'Uploading...'}
                          {progress.status === 'processing' && 'Processing...'}
                          {progress.status === 'done' && 'Done'}
                          {progress.status === 'error' && progress.error}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </CardBody>
            </Card>
          </div>

          <div className="documents-grid">
            <h3>Documents in Collection</h3>
            {documents.length === 0 ? (
              <p className="empty-text">No documents in this collection yet.</p>
            ) : (
              <div className="document-list">
                {documents.map((doc) => {
                  const badge = getStatusBadge(doc.status)
                  return (
                    <Card key={doc.id} className={`document-card ${doc.status === 'failed' ? 'has-error' : ''}`}>
                      <CardBody>
                        <div className="document-header">
                          <span className={badge.className}>{badge.label}</span>
                        </div>
                        <div
                          className="document-info clickable"
                          onClick={() => handlePreviewDocument(doc.id)}
                        >
                          <h4>{doc.filename}</h4>
                          <p className="document-meta">
                            {doc.chunk_count} chunks • Created{' '}
                            {new Date(doc.created_at).toLocaleDateString()}
                          </p>
                        </div>

                        {doc.status === 'failed' && doc.error && (
                          <div className="document-error">
                            <span className="error-icon">!</span>
                            <span className="error-text">{doc.error}</span>
                          </div>
                        )}

                        <div className="document-actions">
                          {(doc.status === 'failed' || doc.status === 'pending') && (
                            <Button
                              size="small"
                              variant="primary"
                              onClick={() => handleRetryProcessing(doc.id)}
                              disabled={processingDoc === doc.id}
                            >
                              {processingDoc === doc.id ? 'Processing...' : doc.status === 'failed' ? 'Retry' : 'Process'}
                            </Button>
                          )}
                          <Button
                            size="small"
                            variant="secondary"
                            onClick={() => handlePreviewDocument(doc.id)}
                            disabled={loadingPreview}
                          >
                            Preview
                          </Button>
                          <Button
                            size="small"
                            variant="danger"
                            onClick={() => handleDeleteClick(doc)}
                          >
                            Delete
                          </Button>
                        </div>
                      </CardBody>
                    </Card>
                  )
                })}
              </div>
            )}
          </div>
        </>
      )}

      {/* Preview Modal */}
      {previewModal && (
        <div className="modal-overlay" onClick={() => setPreviewModal(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{previewModal.filename}</h3>
              <button
                className="modal-close"
                onClick={() => setPreviewModal(null)}
                aria-label="Close"
              >
                &times;
              </button>
            </div>
            <div className="modal-body">
              <pre className="document-preview">{previewModal.content}</pre>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteModal && (
        <div className="modal-overlay" onClick={() => !isDeleting && setDeleteModal(null)}>
          <div className="modal-content modal-confirm" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Delete Document</h3>
              <button
                className="modal-close"
                onClick={() => setDeleteModal(null)}
                disabled={isDeleting}
                aria-label="Close"
              >
                &times;
              </button>
            </div>
            <div className="modal-body">
              <p className="confirm-message">
                Are you sure you want to delete <strong>{deleteModal.filename}</strong>?
              </p>
              <p className="confirm-warning">
                This action cannot be undone. All chunks and embeddings associated with this document will be permanently removed.
              </p>
            </div>
            <div className="modal-footer">
              <Button
                variant="secondary"
                onClick={() => setDeleteModal(null)}
                disabled={isDeleting}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                onClick={handleConfirmDelete}
                disabled={isDeleting}
              >
                {isDeleting ? 'Deleting...' : 'Delete'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Collection Config Modal */}
      {currentCollection && (
        <CollectionConfigModal
          collection={currentCollection}
          isOpen={configModalOpen}
          onClose={() => setConfigModalOpen(false)}
          onSave={handleSaveCollectionConfig}
        />
      )}

      {/* Delete Collection Confirmation Modal */}
      {deleteCollectionModal && (
        <div className="modal-overlay" onClick={() => !isDeletingCollection && setDeleteCollectionModal(null)}>
          <div className="modal-content modal-confirm" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Delete Collection</h3>
              <button
                className="modal-close"
                onClick={() => setDeleteCollectionModal(null)}
                disabled={isDeletingCollection}
                aria-label="Close"
              >
                &times;
              </button>
            </div>
            <div className="modal-body">
              <p className="confirm-message">
                Are you sure you want to delete the collection <strong>{deleteCollectionModal.name}</strong>?
              </p>
              <p className="confirm-warning">
                This action cannot be undone. All {deleteCollectionModal.document_count} documents, chunks, and embeddings in this collection will be permanently removed.
              </p>
            </div>
            <div className="modal-footer">
              <Button
                variant="secondary"
                onClick={() => setDeleteCollectionModal(null)}
                disabled={isDeletingCollection}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                onClick={handleConfirmDeleteCollection}
                disabled={isDeletingCollection}
              >
                {isDeletingCollection ? 'Deleting...' : 'Delete Collection'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
