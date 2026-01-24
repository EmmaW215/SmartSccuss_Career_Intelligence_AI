/**
 * FileUploader Component (Phase 2)
 * Drag & drop file upload for Customize Interview
 */

import React, { useCallback, useState } from 'react';

interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  file: File;
}

interface FileUploaderProps {
  onFilesChange: (files: UploadedFile[]) => void;
  acceptedFormats?: string[];
  maxFiles?: number;
  maxSizeMB?: number;
}

export const FileUploader: React.FC<FileUploaderProps> = ({
  onFilesChange,
  acceptedFormats = ['.pdf', '.txt', '.md', '.docx'],
  maxFiles = 5,
  maxSizeMB = 10
}) => {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragActive, setIsDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateId = () => Math.random().toString(36).substring(7);

  const validateFile = (file: File): string | null => {
    // Check size
    if (file.size > maxSizeMB * 1024 * 1024) {
      return `File "${file.name}" exceeds ${maxSizeMB}MB limit`;
    }

    // Check format
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!acceptedFormats.includes(ext)) {
      return `File type "${ext}" not allowed. Use: ${acceptedFormats.join(', ')}`;
    }

    return null;
  };

  const processFiles = useCallback((newFiles: FileList | File[]) => {
    setError(null);
    const fileArray = Array.from(newFiles);

    // Check max files
    if (files.length + fileArray.length > maxFiles) {
      setError(`Maximum ${maxFiles} files allowed`);
      return;
    }

    const validFiles: UploadedFile[] = [];

    for (const file of fileArray) {
      const validationError = validateFile(file);
      if (validationError) {
        setError(validationError);
        return;
      }

      validFiles.push({
        id: generateId(),
        name: file.name,
        size: file.size,
        type: file.type || 'application/octet-stream',
        file
      });
    }

    const updatedFiles = [...files, ...validFiles];
    setFiles(updatedFiles);
    onFilesChange(updatedFiles);
  }, [files, maxFiles, acceptedFormats, maxSizeMB, onFilesChange]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(false);

    if (e.dataTransfer.files?.length) {
      processFiles(e.dataTransfer.files);
    }
  }, [processFiles]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(false);
  }, []);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) {
      processFiles(e.target.files);
    }
    // Reset input
    e.target.value = '';
  }, [processFiles]);

  const removeFile = useCallback((id: string) => {
    const updatedFiles = files.filter(f => f.id !== id);
    setFiles(updatedFiles);
    onFilesChange(updatedFiles);
  }, [files, onFilesChange]);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileIcon = (filename: string): string => {
    const ext = filename.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'pdf': return '📄';
      case 'txt': return '📝';
      case 'md': return '📋';
      case 'docx': return '📃';
      default: return '📁';
    }
  };

  return (
    <div className="file-uploader">
      {/* Drop Zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
          transition-colors duration-200
          ${isDragActive 
            ? 'border-blue-500 bg-blue-50' 
            : 'border-gray-300 hover:border-gray-400'
          }
        `}
      >
        <input
          type="file"
          multiple
          accept={acceptedFormats.join(',')}
          onChange={handleFileInput}
          className="hidden"
          id="file-input"
        />
        <label htmlFor="file-input" className="cursor-pointer">
          <div className="flex flex-col items-center gap-3">
            <span className="text-4xl">📁</span>
            {isDragActive ? (
              <p className="text-blue-600 font-medium">Drop files here...</p>
            ) : (
              <>
                <p className="text-gray-600">
                  <span className="font-medium text-blue-600">Click to upload</span>
                  {' '}or drag and drop
                </p>
                <p className="text-sm text-gray-400">
                  {acceptedFormats.join(', ')} • Max {maxSizeMB}MB each • Up to {maxFiles} files
                </p>
              </>
            )}
          </div>
        </label>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded text-red-600 text-sm flex justify-between items-center">
          <span>⚠️ {error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600">✕</button>
        </div>
      )}

      {/* Uploaded Files List */}
      {files.length > 0 && (
        <div className="mt-4 space-y-2">
          <h4 className="font-medium text-gray-700">Uploaded Files ({files.length}/{maxFiles})</h4>
          {files.map(file => (
            <div
              key={file.id}
              className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border"
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">{getFileIcon(file.name)}</span>
                <div>
                  <p className="font-medium text-gray-800">{file.name}</p>
                  <p className="text-sm text-gray-500">{formatFileSize(file.size)}</p>
                </div>
              </div>
              <button
                onClick={() => removeFile(file.id)}
                className="text-gray-400 hover:text-red-500 transition-colors"
                title="Remove file"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Suggestions */}
      <div className="mt-6 p-4 bg-blue-50 rounded-lg">
        <h4 className="font-medium text-blue-800 mb-2">📌 Recommended Uploads</h4>
        <ul className="text-sm text-blue-700 space-y-1">
          <li>📄 Your latest resume (PDF or DOCX)</li>
          <li>📋 Job description you're applying for</li>
          <li>📝 Cover letter or personal statement</li>
          <li>🏆 Project descriptions or portfolio summary</li>
        </ul>
      </div>
    </div>
  );
};

export default FileUploader;
