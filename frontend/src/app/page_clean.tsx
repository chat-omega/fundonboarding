"use client";

import React, { useState, useCallback, useRef } from "react";
import { ArrowRight, MessageSquare } from "lucide-react";
import Link from "next/link";
import { UploadPanel } from "@/components/UploadPanel";
import { Charts } from "@/components/Charts";

type ExtractionStatus = "idle" | "uploading" | "uploaded" | "processing" | "completed" | "error";

interface ExtractEvent {
  type: string;
  data: any;
}

interface Fund {
  ticker: string;
  name: string;
  expense_ratio: number;
  category: string;
  asset_class: string;
}

function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

export default function FundExtractionPage() {
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [filePath, setFilePath] = useState<string | null>(null);
  const [filePaths, setFilePaths] = useState<string[]>([]);
  const [csvSessionId, setCsvSessionId] = useState<string | null>(null);
  const [csvSessionIds, setCsvSessionIds] = useState<Record<string, string>>({});
  const [extractionStatus, setExtractionStatus] = useState<ExtractionStatus>("idle");
  const [extractionProgress, setExtractionProgress] = useState<number>(0);
  const [extractionStage, setExtractionStage] = useState<string>("");
  const [extractionLogs, setExtractionLogs] = useState<string[]>([]);
  const [fundData, setFundData] = useState<Fund[]>([]);
  const [selectedFund, setSelectedFund] = useState<Fund | null>(null);
  const [isExtracting, setIsExtracting] = useState<boolean>(false);

  // Handle file upload
  const handleFileUpload = useCallback(async (files: File | File[]) => {
    const fileArray = Array.isArray(files) ? files : [files];
    
    setUploadedFile(fileArray[0]);
    setUploadedFiles(fileArray);
    setExtractionStatus("uploading");
    setExtractionLogs(["📤 Starting file upload..."]);

    try {
      const uploadedPaths: string[] = [];
      const newCsvSessionIds: Record<string, string> = {};

      for (const file of fileArray) {
        const fileExtension = file.name.split('.').pop()?.toLowerCase();
        const isCSV = ['csv', 'xlsx', 'xls'].includes(fileExtension || '');
        
        setExtractionLogs(prev => [...prev, `📄 Processing ${file.name}...`]);

        if (isCSV) {
          // Create onboarding session for CSV files
          const sessionResponse = await fetch("/api/onboarding/session/create", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({}),
          });
          
          if (!sessionResponse.ok) {
            throw new Error(`Failed to create session for ${file.name}`);
          }
          
          const sessionData = await sessionResponse.json();
          
          // Upload file to onboarding system
          const formData = new FormData();
          formData.append("file", file);
          
          const uploadResponse = await fetch(`/api/onboarding/upload?session_id=${sessionData.session_id}`, {
            method: "POST",
            body: formData,
          });
          
          if (!uploadResponse.ok) {
            let errorMessage = `Upload failed for ${file.name}: ${uploadResponse.statusText}`;
            try {
              const errorData = await uploadResponse.json();
              if (errorData.detail) {
                errorMessage += ` - ${errorData.detail}`;
              }
            } catch {
              // Use statusText only if JSON parsing fails
            }
            throw new Error(errorMessage);
          }
          
          const uploadResult = await uploadResponse.json();
          uploadedPaths.push(uploadResult.file_path);
          newCsvSessionIds[uploadResult.file_path] = sessionData.session_id;
          
        } else {
          // Use regular upload for PDFs
          const formData = new FormData();
          formData.append("file", file);

          const response = await fetch("/api/upload", {
            method: "POST",
            body: formData,
          });

          if (!response.ok) {
            let errorMessage = `Upload failed: ${response.statusText}`;
            const responseClone = response.clone();
            try {
              const errorData = await response.json();
              if (errorData.detail) {
                errorMessage += ` - ${errorData.detail}`;
              }
            } catch {
              try {
                const errorText = await responseClone.text();
                if (errorText) {
                  errorMessage += ` - ${errorText}`;
                }
              } catch {
                // If both JSON and text parsing fail, use statusText only
              }
            }
            throw new Error(errorMessage);
          }

          const result = await response.json();
          uploadedPaths.push(result.file_path);
        }
        
        setExtractionLogs(prev => [...prev, `✅ ${file.name} uploaded successfully`]);
      }
      
      // Update session IDs state
      if (Object.keys(newCsvSessionIds).length > 0) {
        if (uploadedPaths.length === 1) {
          setCsvSessionId(Object.values(newCsvSessionIds)[0]);
        }
        setCsvSessionIds(prev => ({ ...prev, ...newCsvSessionIds }));
      }
      
      if (uploadedPaths.length === 1) {
        setFilePath(uploadedPaths[0]);
        setFilePaths([]);
      } else {
        setFilePath(null);
        setFilePaths(uploadedPaths);
      }
      
      setExtractionStatus("uploaded");
      setExtractionLogs(prev => [...prev, `✅ All files uploaded successfully`]);
      
      // Automatically start extraction after successful upload
      setTimeout(() => {
        handleStartExtraction();
      }, 500);

    } catch (error) {
      console.error("Upload error:", error);
      setExtractionStatus("error");
      setExtractionLogs(prev => [...prev, `❌ Upload failed: ${error}`]);
    }
  }, []);

  // Handle extraction start
  const handleStartExtraction = useCallback(async () => {
    if (!filePath && filePaths.length === 0) return;
    
    const pathToProcess = filePath || filePaths[0];

    setIsExtracting(true);
    setExtractionStatus("processing");
    setExtractionProgress(0);
    setExtractionLogs([]);
    setFundData([]);
    setSelectedFund(null);

    try {
      const fileExtension = pathToProcess.split('.').pop()?.toLowerCase();
      const isCSV = ['csv', 'xlsx', 'xls'].includes(fileExtension || '');
      
      let endpoint, body;
      
      if (isCSV) {
        endpoint = "/api/onboarding/process";
        const sessionId = filePath ? csvSessionId : csvSessionIds[pathToProcess];
        
        if (!sessionId) {
          throw new Error("No onboarding session found for this CSV file. Please re-upload the file.");
        }
        
        body = JSON.stringify({
          session_id: sessionId,
          action: "upload_file",
          data: {
            file_path: pathToProcess,
            file_type: fileExtension
          }
        });
      } else {
        endpoint = "/api/fund-extraction-agent";
        body = JSON.stringify({
          file_path: pathToProcess,
          message: "Extract fund data from this PDF",
          threadId: generateUUID(),
          messageId: generateUUID(),
        });
      }

      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: body,
      });

      if (!response.ok) {
        throw new Error(`Extraction failed: ${response.statusText}`);
      }

      if (isCSV) {
        const sessionId = filePath ? csvSessionId : csvSessionIds[pathToProcess];
        const streamResponse = await fetch(`/api/onboarding/enhanced-stream/${sessionId}`);
        
        if (!streamResponse.ok) {
          throw new Error(`Failed to connect to stream: ${streamResponse.statusText}`);
        }

        const reader = streamResponse.body?.getReader();
        if (!reader) throw new Error("No reader available");

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = new TextDecoder().decode(value);
            const lines = chunk.split('\n').filter(line => line.trim());

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const eventData = JSON.parse(line.slice(6));
                  
                  if (eventData.type === 'data_processed') {
                    const portfolioItems = eventData.data?.portfolio_items || [];
                    setFundData(portfolioItems.map((item: any) => ({
                      ticker: item.ticker,
                      name: item.name,
                      expense_ratio: item.expense_ratio,
                      category: item.morningstar_category,
                      asset_class: item.asset_class
                    })));
                  }
                } catch (parseError) {
                  console.warn("Failed to parse event data:", parseError);
                }
              }
            }
          }
        } finally {
          reader.releaseLock();
        }
      }

      setExtractionStatus("completed");
      setExtractionProgress(100);
      
    } catch (error) {
      console.error("Extraction error:", error);
      setExtractionStatus("error");
      setExtractionLogs(prev => [...prev, `❌ Extraction failed: ${error}`]);
    } finally {
      setIsExtracting(false);
    }
  }, [filePath, filePaths, csvSessionId, csvSessionIds]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black text-white">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-20">
            <div className="flex items-center space-x-4">
              <div className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                Fund Analyzer
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2 text-sm text-gray-400">
                <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse"></div>
                <span>Ready for analysis</span>
              </div>
              
              <Link 
                href="/chat"
                className="flex items-center space-x-2 text-black bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 px-4 py-2 rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl"
              >
                <MessageSquare className="h-4 w-4" />
                <span className="text-sm font-medium">Try Chat Mode</span>
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex h-[calc(100vh-80px)]">
        {/* Left Panel - Upload & Config */}
        <div className="w-1/4 min-w-[300px] p-6 border-r border-gray-800">
          <UploadPanel
            onFileUpload={handleFileUpload}
            onStartExtraction={handleStartExtraction}
            uploadedFile={uploadedFile}
            uploadedFiles={uploadedFiles}
            extractionStatus={extractionStatus}
            isExtracting={isExtracting}
            canExtract={(!!filePath || filePaths.length > 0) && !isExtracting}
          />
        </div>

        {/* Right Panel - Results */}
        <div className="flex-1 flex flex-col">
          {/* Results Panel */}
          <div className="flex-1 p-6">
            {fundData.length === 0 ? (
              <div className="h-full flex items-center justify-center">
                <div className="text-center text-gray-400">
                  <div className="text-6xl mb-4">📊</div>
                  <h3 className="text-xl font-semibold mb-2">Upload files to get started</h3>
                  <p>Support for PDF prospectuses and CSV/Excel portfolio files</p>
                </div>
              </div>
            ) : (
              <div className="h-full overflow-y-auto">
                <Charts funds={fundData} />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}