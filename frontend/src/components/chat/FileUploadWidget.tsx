"use client";

import { useState, useRef, useCallback, DragEvent } from 'react';
import { Upload, X, FileText, File, AlertCircle, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface FileUploadWidgetProps {
  onUpload: (file: File) => void;
  onCancel: () => void;
  acceptedTypes?: Record<string, string[]>;
  maxSize?: number;
  className?: string;
}

export function FileUploadWidget({
  onUpload,
  onCancel,
  acceptedTypes = {
    'text/csv': ['.csv'],
    'application/vnd.ms-excel': ['.xls'],
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    'application/pdf': ['.pdf']
  },
  maxSize = 50 * 1024 * 1024, // 50MB
  className
}: FileUploadWidgetProps) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Get accepted file extensions
  const acceptedExtensions = Object.values(acceptedTypes).flat();
  const acceptString = Object.keys(acceptedTypes).join(',');

  // Validate file
  const validateFile = useCallback((file: File): string | null => {
    // Check file size
    if (file.size > maxSize) {
      return `File size must be less than ${Math.round(maxSize / (1024 * 1024))}MB`;
    }

    // Check file type
    const extension = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!acceptedExtensions.includes(extension)) {
      return `File type not supported. Accepted types: ${acceptedExtensions.join(', ')}`;
    }

    return null;
  }, [maxSize, acceptedExtensions]);

  // Handle file selection
  const handleFileSelect = useCallback((file: File) => {
    setError(null);
    
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }

    setSelectedFile(file);
  }, [validateFile]);

  // Handle drag events
  const handleDrag = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  // Handle drop
  const handleDrop = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  }, [handleFileSelect]);

  // Handle file input change
  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  }, [handleFileSelect]);

  // Handle upload
  const handleUpload = useCallback(async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setError(null);

    try {
      await onUpload(selectedFile);
      // Success - parent component should handle closing
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      setIsUploading(false);
    }
  }, [selectedFile, onUpload]);

  // Get file type icon
  const getFileIcon = (fileName: string) => {
    const extension = fileName.split('.').pop()?.toLowerCase();
    switch (extension) {
      case 'pdf':
        return <FileText className="h-8 w-8 text-red-500" />;
      case 'csv':
      case 'xls':
      case 'xlsx':
        return <File className="h-8 w-8 text-green-500" />;
      default:
        return <File className="h-8 w-8 text-gray-500" />;
    }
  };

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className={cn("bg-white rounded-lg shadow-lg", className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">Upload File</h3>
        <button
          onClick={onCancel}
          className="p-1 hover:bg-gray-100 rounded-full"
        >
          <X className="h-5 w-5 text-gray-500" />
        </button>
      </div>

      <div className="p-6">
        {!selectedFile ? (
          /* Upload Area */
          <div
            className={cn(
              "border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer",
              dragActive 
                ? "border-blue-400 bg-blue-50" 
                : "border-gray-300 hover:border-gray-400 hover:bg-gray-50"
            )}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className={cn(
              "h-12 w-12 mx-auto mb-4",
              dragActive ? "text-blue-500" : "text-gray-400"
            )} />
            
            <div className="space-y-2">
              <p className="text-lg font-medium text-gray-900">
                {dragActive ? "Drop your file here" : "Choose a file or drag it here"}
              </p>
              <p className="text-sm text-gray-500">
                Supported formats: {acceptedExtensions.join(', ')}
              </p>
              <p className="text-xs text-gray-400">
                Maximum file size: {Math.round(maxSize / (1024 * 1024))}MB
              </p>
            </div>

            <button className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
              Browse Files
            </button>
          </div>
        ) : (
          /* File Preview */
          <div className="space-y-4">
            <div className="flex items-center space-x-4 p-4 border border-gray-200 rounded-lg">
              {getFileIcon(selectedFile.name)}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {selectedFile.name}
                </p>
                <p className="text-sm text-gray-500">
                  {formatFileSize(selectedFile.size)}
                </p>
              </div>
              <CheckCircle className="h-5 w-5 text-green-500" />
            </div>

            {/* File Type Specific Info */}
            <div className="bg-gray-50 p-3 rounded-lg text-sm">
              {selectedFile.name.endsWith('.csv') || selectedFile.name.endsWith('.xlsx') || selectedFile.name.endsWith('.xls') ? (
                <div>
                  <p className="font-medium text-gray-900 mb-1">📊 Portfolio File</p>
                  <p className="text-gray-600">
                    This appears to be a portfolio holdings file. I'll process the fund tickers and extract detailed information for each holding.
                  </p>
                </div>
              ) : selectedFile.name.endsWith('.pdf') ? (
                <div>
                  <p className="font-medium text-gray-900 mb-1">📄 Fund Prospectus</p>
                  <p className="text-gray-600">
                    This appears to be a fund prospectus. I'll extract key fund data including performance, fees, and allocations.
                  </p>
                </div>
              ) : null}
            </div>

            {/* Actions */}
            <div className="flex items-center justify-between">
              <button
                onClick={() => {
                  setSelectedFile(null);
                  setError(null);
                }}
                className="text-sm text-gray-600 hover:text-gray-800"
              >
                Choose different file
              </button>
              
              <div className="flex space-x-3">
                <button
                  onClick={onCancel}
                  className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
                  disabled={isUploading}
                >
                  Cancel
                </button>
                <button
                  onClick={handleUpload}
                  disabled={isUploading}
                  className={cn(
                    "px-4 py-2 rounded-lg transition-colors",
                    isUploading
                      ? "bg-gray-400 text-white cursor-not-allowed"
                      : "bg-blue-600 text-white hover:bg-blue-700"
                  )}
                >
                  {isUploading ? "Uploading..." : "Upload & Process"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-2">
            <AlertCircle className="h-5 w-5 text-red-500" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Help Text */}
        <div className="mt-4 text-xs text-gray-500 space-y-1">
          <p><strong>Portfolio Files (CSV/Excel):</strong> Should contain fund tickers, names, and allocation data</p>
          <p><strong>Fund PDFs:</strong> Prospectuses or fact sheets for individual fund analysis</p>
        </div>
      </div>

      {/* Hidden File Input */}
      <input
        ref={fileInputRef}
        type="file"
        accept={acceptString}
        onChange={handleFileInputChange}
        className="hidden"
      />
    </div>
  );
}