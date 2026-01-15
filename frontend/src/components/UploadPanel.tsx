"use client";

import { useState, useRef, useCallback } from "react";
import { Upload, File, Play, CheckCircle, AlertCircle, Loader } from "lucide-react";
import { ExtractionStatus } from "@/lib/types";

interface UploadPanelProps {
  onFileUpload: (files: File | File[]) => void;
  onStartExtraction: () => void;
  uploadedFile: File | null;
  uploadedFiles?: File[];
  extractionStatus: ExtractionStatus;
  isExtracting: boolean;
  canExtract: boolean;
}

export function UploadPanel({
  onFileUpload,
  onStartExtraction,
  uploadedFile,
  uploadedFiles = [],
  extractionStatus,
  isExtracting,
  canExtract
}: UploadPanelProps) {
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const files = Array.from(e.dataTransfer.files);
      const validTypes = [
        "application/pdf",
        "text/csv", 
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      ];
      
      const validFiles = files.filter(file => 
        validTypes.includes(file.type) || file.name.endsWith('.csv')
      );
      
      if (validFiles.length === 0) {
        alert("Please upload PDF, CSV, or Excel files only");
        return;
      }
      
      if (validFiles.length === 1) {
        onFileUpload(validFiles[0]);
      } else {
        onFileUpload(validFiles);
      }
    }
  }, [onFileUpload]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const files = Array.from(e.target.files);
      const validTypes = [
        "application/pdf",
        "text/csv", 
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      ];
      
      const validFiles = files.filter(file => 
        validTypes.includes(file.type) || file.name.endsWith('.csv')
      );
      
      if (validFiles.length === 0) {
        alert("Please upload PDF, CSV, or Excel files only");
        return;
      }
      
      if (validFiles.length === 1) {
        onFileUpload(validFiles[0]);
      } else {
        onFileUpload(validFiles);
      }
    }
  }, [onFileUpload]);

  const getStatusIcon = (status: ExtractionStatus) => {
    switch (status) {
      case "uploading":
        return <Loader className="h-4 w-4 animate-spin text-blue-400" />;
      case "uploaded":
        return <CheckCircle className="h-4 w-4 text-green-400" />;
      case "processing":
        return <Loader className="h-4 w-4 animate-spin text-blue-400" />;
      case "completed":
        return <CheckCircle className="h-4 w-4 text-green-400" />;
      case "error":
        return <AlertCircle className="h-4 w-4 text-red-400" />;
      default:
        return null;
    }
  };

  const getStatusText = (status: ExtractionStatus) => {
    switch (status) {
      case "uploading":
        return "Uploading...";
      case "uploaded":
        return "Ready to extract";
      case "processing":
        return "Extracting data...";
      case "completed":
        return "Extraction completed";
      case "error":
        return "Error occurred";
      default:
        return "Ready";
    }
  };

  return (
    <div className="space-y-3">
      <div>
        <h2 className="text-lg font-bold text-white mb-3">📄 Upload Files</h2>
        
        {/* Upload Area */}
        <div
          className={`
            relative border-2 border-dashed rounded-lg p-6 text-center transition-all duration-200
            ${dragActive 
              ? "border-blue-500 bg-blue-500/10" 
              : uploadedFile 
                ? "border-green-500 bg-green-500/5" 
                : "border-gray-600 hover:border-gray-500"
            }
            ${isExtracting ? "opacity-50 pointer-events-none" : ""}
          `}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => !isExtracting && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.csv,.xlsx,.xls"
            multiple
            className="hidden"
            onChange={handleFileSelect}
            disabled={isExtracting}
          />

          <div className="flex flex-col items-center space-y-3">
            {uploadedFile || uploadedFiles.length > 0 ? (
              <>
                <File className="h-12 w-12 text-green-400" />
                <div className="text-center">
                  {uploadedFiles.length > 1 ? (
                    <>
                      <p className="text-green-400 font-medium">{uploadedFiles.length} files selected</p>
                      <div className="text-gray-400 text-xs mt-1 max-h-20 overflow-y-auto">
                        {uploadedFiles.map((file, idx) => (
                          <div key={idx}>
                            {file.name} ({(file.size / 1024 / 1024).toFixed(1)} MB)
                          </div>
                        ))}
                      </div>
                    </>
                  ) : uploadedFile ? (
                    <>
                      <p className="text-green-400 font-medium">{uploadedFile.name}</p>
                      <p className="text-gray-400 text-sm">
                        {(uploadedFile.size / 1024 / 1024).toFixed(1)} MB
                      </p>
                    </>
                  ) : (
                    <>
                      <p className="text-green-400 font-medium">{uploadedFiles[0]?.name}</p>
                      <p className="text-gray-400 text-sm">
                        {uploadedFiles[0] ? (uploadedFiles[0].size / 1024 / 1024).toFixed(1) : 0} MB
                      </p>
                    </>
                  )}
                </div>
              </>
            ) : (
              <>
                <Upload className="h-12 w-12 text-gray-400" />
                <div>
                  <p className="text-white font-medium">Drop your files here</p>
                  <p className="text-gray-400 text-sm">
                    PDF, CSV, or Excel files supported
                  </p>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Status Section */}
      <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {getStatusIcon(extractionStatus)}
            <span className="text-sm text-gray-300">
              {getStatusText(extractionStatus)}
            </span>
          </div>
        </div>
      </div>

      {/* Action Button */}
      <button
        onClick={onStartExtraction}
        disabled={!canExtract}
        className={`
          w-full flex items-center justify-center space-x-2 py-2.5 px-3 rounded-lg font-medium transition-all duration-200 text-sm
          ${canExtract
            ? "bg-blue-600 hover:bg-blue-700 text-white"
            : "bg-gray-700 text-gray-400 cursor-not-allowed"
          }
        `}
      >
        {isExtracting ? (
          <>
            <Loader className="h-4 w-4 animate-spin" />
            <span>Extracting...</span>
          </>
        ) : (
          <>
            <Play className="h-4 w-4" />
            <span>Start Extraction</span>
          </>
        )}
      </button>


    </div>
  );
}