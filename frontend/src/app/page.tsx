"use client";

import React, { useState, useCallback, useRef } from "react";
import { ArrowRight, MessageSquare } from "lucide-react";
import Link from "next/link";
import { UploadPanel } from "@/components/UploadPanel";
import { FundCompositionTable } from "@/components/FundCompositionTable";
import { FundData } from "@/lib/types";

type ExtractionStatus = "idle" | "uploading" | "uploaded" | "processing" | "completed" | "error";

interface ExtractEvent {
  type: string;
  data: any;
}


interface FileProcessingStatus {
  fileName: string;
  filePath: string;
  fileType: 'csv' | 'pdf' | 'xlsx' | 'xls';
  status: 'pending' | 'processing' | 'completed' | 'error';
  progress: number;
  message: string;
  extractedFunds: FundData[];
  sessionId?: string;
  error?: string;
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
  const [fundData, setFundData] = useState<FundData[]>([]);
  const [selectedFund, setSelectedFund] = useState<FundData | null>(null);
  const [isExtracting, setIsExtracting] = useState<boolean>(false);
  
  // New parallel processing state
  const [fileProcessingStatuses, setFileProcessingStatuses] = useState<Map<string, FileProcessingStatus>>(new Map());

  // Helper functions for file processing status
  const updateFileStatus = useCallback((filePath: string, updates: Partial<FileProcessingStatus>) => {
    setFileProcessingStatuses(prev => {
      const updated = new Map(prev);
      const current = updated.get(filePath);
      if (current) {
        updated.set(filePath, { ...current, ...updates });
      }
      return updated;
    });
  }, []);

  const initializeFileStatus = useCallback((filePath: string, fileName: string, fileType: 'csv' | 'pdf' | 'xlsx' | 'xls', sessionId?: string) => {
    const status: FileProcessingStatus = {
      fileName,
      filePath,
      fileType,
      status: 'pending',
      progress: 0,
      message: 'Ready to process',
      extractedFunds: [],
      sessionId
    };
    setFileProcessingStatuses(prev => {
      const updated = new Map(prev);
      updated.set(filePath, status);
      return updated;
    });
  }, []);

  // Individual file processors
  const processCSVFile = useCallback(async (filePath: string, sessionId: string): Promise<FundData[]> => {
    const fileName = filePath.split('/').pop() || 'Unknown';
    
    try {
      updateFileStatus(filePath, { status: 'processing', progress: 10, message: 'Starting CSV processing...' });

      // Start processing
      await fetch("/api/onboarding/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          action: "upload_file",
          data: { file_path: filePath, file_type: 'csv' }
        })
      });

      updateFileStatus(filePath, { progress: 30, message: 'Connecting to processing stream...' });

      // Connect to stream with abort controller for proper cleanup
      const controller = new AbortController();
      const streamResponse = await fetch(`/api/onboarding/enhanced-stream/${sessionId}`, {
        signal: controller.signal,
        headers: {
          'Accept': 'text/event-stream',
          'Cache-Control': 'no-cache',
        }
      });
      
      if (!streamResponse.ok) {
        throw new Error(`Stream connection failed: ${streamResponse.status}`);
      }

      updateFileStatus(filePath, { progress: 50, message: 'Processing CSV data...' });

      const extractedFunds: Fund[] = [];
      const reader = streamResponse.body?.getReader();
      
      if (reader) {
        let streamTimeout: ReturnType<typeof setTimeout>;
        let isConnected = true;
        
        const processStream = new Promise<void>((resolve, reject) => {
          // Set up timeout
          streamTimeout = setTimeout(() => {
            isConnected = false;
            controller.abort();
            reject(new Error('Stream timeout - no data received within 60 seconds'));
          }, 60000);
          
          // Process stream
          (async () => {
            try {
              let buffer = ''; // Handle split chunks
              let dataReceived = false; // Flag to exit loop gracefully
              
              while (isConnected && !dataReceived) {
                const { done, value } = await reader.read();
                if (done) {
                  console.log('Stream ended naturally');
                  break;
                }

                const chunk = new TextDecoder().decode(value);
                buffer += chunk;
                const lines = buffer.split('\n');
                
                // Keep the last incomplete line in buffer
                buffer = lines.pop() || '';

                for (const line of lines) {
                  if (line.trim() && line.startsWith('data: ')) {
                    try {
                      const eventDataStr = line.slice(6).trim();
                      if (eventDataStr) {
                        const eventData = JSON.parse(eventDataStr);
                        
                        if (eventData.type === 'data_processed') {
                          const portfolioItems = eventData.data?.portfolio_items || [];
                          const csvFunds = portfolioItems.map((item: any) => ({
                            ticker: item.ticker || 'Unknown',
                            fund_name: item.name || 'Unknown Fund',
                            expense_ratio: parseFloat(item.expense_ratio) || 0,
                            category: item.morningstar_category || 'Unknown Category',
                            asset_class: item.asset_class || 'Unknown'
                          }));
                          extractedFunds.push(...csvFunds);
                          
                          updateFileStatus(filePath, { 
                            progress: 90, 
                            message: `Extracted ${csvFunds.length} funds from CSV`,
                            extractedFunds: csvFunds
                          });
                          
                          // Set flag to exit loop gracefully instead of returning
                          dataReceived = true;
                          break;
                        }
                      }
                    } catch (parseError) {
                      console.warn("Failed to parse CSV event data:", parseError, "Line:", line);
                    }
                  }
                }
              }
              
              // Graceful cleanup
              isConnected = false;
              
              // Cancel any pending reads
              try {
                await reader.cancel();
                console.log('Reader cancelled successfully');
              } catch (cancelError) {
                console.warn('Failed to cancel reader:', cancelError);
              }
              
              // Release the reader
              try {
                reader.releaseLock();
                console.log('Reader lock released');
              } catch (releaseError) {
                console.warn("Failed to release stream reader:", releaseError);
              }
              
              // Abort the connection
              controller.abort();
              
              // Clear timeout and resolve
              clearTimeout(streamTimeout);
              resolve();
              
            } catch (streamError) {
              isConnected = false;
              clearTimeout(streamTimeout);
              
              // Handle specific error types
              if (streamError.name === 'AbortError') {
                console.log('Stream was aborted (expected behavior)');
                resolve(); // This is expected when we abort
              } else {
                console.error('Stream processing error:', streamError);
                reject(new Error(`Stream processing error: ${streamError.message || streamError}`));
              }
            }
          })();
        });

        // Wait for stream processing to complete
        await processStream;
      }

      updateFileStatus(filePath, { 
        status: 'completed', 
        progress: 100, 
        message: `Successfully processed ${extractedFunds.length} funds`,
        extractedFunds 
      });

      return extractedFunds;
    } catch (error) {
      console.error(`CSV processing error for ${fileName}:`, error);
      
      // Determine error type and provide helpful message
      let errorMessage = 'Unknown error occurred';
      let errorType = 'processing_error';
      
      if (error instanceof Error) {
        if (error.message.includes('timeout') || error.message.includes('Stream timeout')) {
          errorMessage = 'Processing timed out - file may be too large or server is busy';
          errorType = 'timeout_error';
        } else if (error.message.includes('Stream connection failed')) {
          errorMessage = 'Unable to connect to processing server - please try again';
          errorType = 'connection_error';
        } else if (error.message.includes('Stream processing error')) {
          errorMessage = 'Stream was interrupted - connection closed unexpectedly';
          errorType = 'stream_error';
        } else if (error.message.includes('Failed to fetch')) {
          errorMessage = 'Network error - please check your connection and try again';
          errorType = 'network_error';
        } else if (error.name === 'AbortError') {
          errorMessage = 'Processing was cancelled';
          errorType = 'abort_error';
        } else if (error.message.includes('signal is aborted')) {
          errorMessage = 'Connection was closed due to timeout or cancellation';
          errorType = 'abort_error';
        } else {
          errorMessage = error.message || 'Unexpected error during CSV processing';
        }
      } else {
        errorMessage = String(error) || 'Unknown error occurred';
      }
      
      updateFileStatus(filePath, { 
        status: 'error', 
        progress: 0, 
        message: `CSV processing failed: ${errorMessage}`,
        error: `[${errorType}] ${errorMessage}`
      });
      return [];
    }
  }, [updateFileStatus]);

  const processPDFFile = useCallback(async (filePath: string): Promise<FundData[]> => {
    const fileName = filePath.split('/').pop() || 'Unknown';
    
    try {
      updateFileStatus(filePath, { status: 'processing', progress: 10, message: 'Starting PDF extraction...' });

      const streamResponse = await fetch('/api/fund-extraction-agent', {
        method: 'POST',
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          file_path: filePath,
          message: "Extract fund data from this PDF",
          threadId: generateUUID(),
          messageId: generateUUID(),
        })
      });

      if (!streamResponse.ok) {
        throw new Error(`PDF extraction failed: ${streamResponse.status} ${streamResponse.statusText}`);
      }

      updateFileStatus(filePath, { progress: 20, message: 'Processing PDF stream...' });

      const extractedFunds: FundData[] = [];
      const reader = streamResponse.body?.getReader();
      
      if (reader) {
        try {
          let eventCount = 0;
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = new TextDecoder().decode(value);
            const lines = chunk.split('\n').filter(line => line.trim());

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                eventCount++;
                try {
                  const eventData = JSON.parse(line.slice(6));
                  
                  if (eventData.type === 'status') {
                    const progress = Math.min(90, 20 + (eventData.data?.progress || 0) * 0.7);
                    updateFileStatus(filePath, { 
                      progress, 
                      message: eventData.data?.message || 'Processing...' 
                    });
                  }
                  
                  if (eventData.type === 'fund_extracted') {
                    const fundInfo = eventData.data?.fund || eventData.data;
                    const newFund: FundData = {
                      fund_name: fundInfo.fund_name || fundInfo.name || 'Unknown Fund',
                      ticker: fundInfo.ticker || fundInfo.fund_ticker,
                      expense_ratio: parseFloat(fundInfo.expense_ratio) || undefined,
                      category: fundInfo.category || fundInfo.morningstar_category,
                      asset_class: fundInfo.asset_class || 'Unknown',
                      // Map all available FundData fields
                      target_equity_pct: fundInfo.target_equity_pct ? parseInt(fundInfo.target_equity_pct) : undefined,
                      report_date: fundInfo.report_date,
                      equity_pct: fundInfo.equity_pct ? parseFloat(fundInfo.equity_pct) : undefined,
                      fixed_income_pct: fundInfo.fixed_income_pct ? parseFloat(fundInfo.fixed_income_pct) : undefined,
                      money_market_pct: fundInfo.money_market_pct ? parseFloat(fundInfo.money_market_pct) : undefined,
                      other_pct: fundInfo.other_pct ? parseFloat(fundInfo.other_pct) : undefined,
                      nav: fundInfo.nav ? parseFloat(fundInfo.nav) : undefined,
                      net_assets_usd: fundInfo.net_assets_usd ? parseFloat(fundInfo.net_assets_usd) : undefined,
                      management_fee: fundInfo.management_fee ? parseFloat(fundInfo.management_fee) : undefined,
                      one_year_return: fundInfo.one_year_return ? parseFloat(fundInfo.one_year_return) : undefined,
                      portfolio_turnover: fundInfo.portfolio_turnover ? parseFloat(fundInfo.portfolio_turnover) : undefined
                    };
                    extractedFunds.push(newFund);
                  } 
                  
                  if (eventData.type === 'results') {
                    const funds = eventData.data?.funds || [];
                    const mappedFunds = funds.map((fund: any) => ({
                      fund_name: fund.fund_name || fund.name || 'Unknown Fund',
                      ticker: fund.ticker || fund.fund_ticker,
                      expense_ratio: parseFloat(fund.expense_ratio) || undefined,
                      category: fund.category || fund.morningstar_category,
                      asset_class: fund.asset_class || 'Unknown',
                      // Map all available FundData fields
                      target_equity_pct: fund.target_equity_pct ? parseInt(fund.target_equity_pct) : undefined,
                      report_date: fund.report_date,
                      equity_pct: fund.equity_pct ? parseFloat(fund.equity_pct) : undefined,
                      fixed_income_pct: fund.fixed_income_pct ? parseFloat(fund.fixed_income_pct) : undefined,
                      money_market_pct: fund.money_market_pct ? parseFloat(fund.money_market_pct) : undefined,
                      other_pct: fund.other_pct ? parseFloat(fund.other_pct) : undefined,
                      nav: fund.nav ? parseFloat(fund.nav) : undefined,
                      net_assets_usd: fund.net_assets_usd ? parseFloat(fund.net_assets_usd) : undefined,
                      management_fee: fund.management_fee ? parseFloat(fund.management_fee) : undefined,
                      one_year_return: fund.one_year_return ? parseFloat(fund.one_year_return) : undefined,
                      portfolio_turnover: fund.portfolio_turnover ? parseFloat(fund.portfolio_turnover) : undefined
                    } as FundData));
                    extractedFunds.push(...mappedFunds);
                  }
                  
                  if (eventData.type === 'error') {
                    throw new Error(eventData.data?.message || 'Unknown PDF extraction error');
                  }
                } catch (parseError) {
                  console.warn(`Failed to parse PDF event data for ${fileName}:`, parseError);
                }
              }
            }
          }
        } finally {
          reader.releaseLock();
        }
      }

      updateFileStatus(filePath, { 
        status: 'completed', 
        progress: 100, 
        message: `Successfully extracted ${extractedFunds.length} funds`,
        extractedFunds
      });

      return extractedFunds;
    } catch (error) {
      console.error(`PDF processing error for ${fileName}:`, error);
      
      // Determine error type and provide helpful message
      let errorMessage = 'Unknown error occurred';
      let errorType = 'processing_error';
      
      if (error instanceof Error) {
        if (error.message.includes('PDF extraction failed')) {
          errorMessage = 'PDF extraction service is unavailable';
          errorType = 'service_error';
        } else if (error.message.includes('Failed to fetch')) {
          errorMessage = 'Network error - please check your connection';
          errorType = 'network_error';
        } else if (error.message.includes('Unknown PDF extraction error')) {
          errorMessage = 'PDF processing service encountered an error';
          errorType = 'extraction_error';
        } else {
          errorMessage = error.message;
        }
      } else {
        errorMessage = String(error);
      }
      
      updateFileStatus(filePath, { 
        status: 'error', 
        progress: 0, 
        message: `PDF processing failed: ${errorMessage}`,
        error: `[${errorType}] ${errorMessage}`
      });
      return [];
    }
  }, [updateFileStatus]);

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
      
      // Automatically start extraction for all uploaded files
      setTimeout(async () => {
        setIsExtracting(true);
        setExtractionStatus("processing");
        setExtractionProgress(0);
        setExtractionLogs(prev => [...prev, `🚀 Starting processing of ${uploadedPaths.length} file(s)...`]);
        
        await processAllFilesParallel(uploadedPaths, newCsvSessionIds);
      }, 500);

    } catch (error) {
      console.error("Upload error:", error);
      setExtractionStatus("error");
      setExtractionLogs(prev => [...prev, `❌ Upload failed: ${error}`]);
    }
  }, []);

  // Handle extraction start
  const handleStartExtraction = useCallback(async (pathOverride?: string, sessionIdOverride?: string) => {
    // Use provided parameters or fall back to state
    const pathToProcess = pathOverride || filePath || filePaths[0];
    const sessionIdToUse = sessionIdOverride || (pathOverride ? csvSessionIds[pathOverride] : (filePath ? csvSessionId : csvSessionIds[pathToProcess]));
    
    if (!pathToProcess) {
      console.log("No file path available for extraction");
      return;
    }

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
        
        if (!sessionIdToUse) {
          throw new Error("No onboarding session found for this CSV file. Please re-upload the file.");
        }
        
        body = JSON.stringify({
          session_id: sessionIdToUse,
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

      // For CSV files, start processing first, then connect to stream
      if (isCSV) {
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
      }

      // Handle streaming response for both CSV and PDF
      let streamEndpoint: string;
      let streamMethod: string;
      let streamBody: string | undefined;
      
      if (isCSV) {
        streamEndpoint = `/api/onboarding/enhanced-stream/${sessionIdToUse}`;
        streamMethod = 'GET';
        streamBody = undefined;
      } else {
        // For PDFs, use the fund-extraction-agent streaming endpoint directly
        streamEndpoint = `/api/fund-extraction-agent`;
        streamMethod = 'POST';
        streamBody = body;
      }

      const streamResponse = await fetch(streamEndpoint, {
        method: streamMethod,
        headers: streamMethod === 'POST' ? {
          "Content-Type": "application/json",
        } : {},
        body: streamBody,
      });
      
      if (!streamResponse.ok) {
        throw new Error(`Failed to connect to stream: ${streamResponse.statusText}`);
      }

      const reader = streamResponse.body?.getReader();
      if (!reader) throw new Error("No reader available");

      try {
        const extractedFunds: FundData[] = [];
        
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = new TextDecoder().decode(value);
          const lines = chunk.split('\n').filter(line => line.trim());

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const eventData = JSON.parse(line.slice(6));
                
                // Handle CSV data processing
                if (eventData.type === 'data_processed') {
                  const portfolioItems = eventData.data?.portfolio_items || [];
                  setFundData(portfolioItems.map((item: any) => ({
                    ticker: item.ticker,
                    fund_name: item.name,
                    expense_ratio: item.expense_ratio,
                    category: item.morningstar_category,
                    asset_class: item.asset_class
                  })));
                }
                
                // Handle PDF extraction events
                else if (eventData.type === 'fund_extracted') {
                  const fundInfo = eventData.data?.fund || eventData.data;
                  const newFund: FundData = {
                    fund_name: fundInfo.fund_name || fundInfo.name || 'Unknown Fund',
                    ticker: fundInfo.ticker || fundInfo.fund_ticker,
                    expense_ratio: parseFloat(fundInfo.expense_ratio) || undefined,
                    category: fundInfo.category || fundInfo.morningstar_category,
                    asset_class: fundInfo.asset_class || 'Unknown'
                  };
                  extractedFunds.push(newFund);
                  setFundData([...extractedFunds]);
                }
                
                // Handle final results from PDF extraction
                else if (eventData.type === 'results') {
                  const funds = eventData.data?.funds || [];
                  const mappedFunds = funds.map((fund: any) => ({
                    fund_name: fund.fund_name || fund.name || 'Unknown Fund',
                    ticker: fund.ticker || fund.fund_ticker,
                    expense_ratio: parseFloat(fund.expense_ratio) || undefined,
                    category: fund.category || fund.morningstar_category,
                    asset_class: fund.asset_class || 'Unknown'
                  }));
                  setFundData(mappedFunds);
                }
                
                // Handle status updates for both CSV and PDF
                else if (eventData.type === 'status') {
                  const statusData = eventData.data;
                  if (statusData.stage) {
                    setExtractionStage(statusData.stage);
                  }
                  if (statusData.progress !== undefined) {
                    setExtractionProgress(statusData.progress);
                  }
                  if (statusData.message) {
                    setExtractionLogs(prev => [...prev, statusData.message]);
                  }
                }
                
                // Handle extraction completion
                else if (eventData.type === 'extraction_complete' || eventData.type === 'results') {
                  setExtractionStatus("completed");
                  setExtractionProgress(100);
                }
                
                // Handle errors
                else if (eventData.type === 'error') {
                  throw new Error(eventData.data?.message || 'Extraction failed');
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

  // Process all uploaded files sequentially
  // Parallel file processing
  const processAllFilesParallel = useCallback(async (filePaths: string[], sessionIds: Record<string, string>) => {
    try {
      setIsExtracting(true);
      setExtractionStatus("processing");
      setExtractionLogs(prev => [...prev, `🚀 Starting parallel processing of ${filePaths.length} files...`]);

      // Initialize all file statuses
      filePaths.forEach(filePath => {
        const fileName = filePath.split('/').pop() || 'Unknown';
        const fileExtension = filePath.split('.').pop()?.toLowerCase();
        const isCSV = ['csv', 'xlsx', 'xls'].includes(fileExtension || '');
        const fileType = isCSV ? fileExtension as 'csv' | 'xlsx' | 'xls' : 'pdf';
        const sessionId = sessionIds[filePath];
        
        initializeFileStatus(filePath, fileName, fileType, sessionId);
      });

      // Create processing promises for all files
      const processingPromises = filePaths.map(async (filePath) => {
        const fileName = filePath.split('/').pop() || 'Unknown';
        const fileExtension = filePath.split('.').pop()?.toLowerCase();
        const isCSV = ['csv', 'xlsx', 'xls'].includes(fileExtension || '');
        
        if (isCSV) {
          const sessionId = sessionIds[filePath];
          if (sessionId) {
            return await processCSVFile(filePath, sessionId);
          } else {
            updateFileStatus(filePath, { 
              status: 'error', 
              message: 'No session ID found for CSV file',
              error: 'Missing session ID'
            });
            return [];
          }
        } else {
          return await processPDFFile(filePath);
        }
      });

      // Wait for all files to complete
      const results = await Promise.allSettled(processingPromises);
      
      // Collect all extracted funds
      const allExtractedFunds: FundData[] = [];
      let completedCount = 0;
      let errorCount = 0;
      
      results.forEach((result, index) => {
        if (result.status === 'fulfilled') {
          allExtractedFunds.push(...result.value);
          completedCount++;
        } else {
          errorCount++;
          const filePath = filePaths[index];
          updateFileStatus(filePath, { 
            status: 'error', 
            message: `Processing failed: ${result.reason}`,
            error: String(result.reason)
          });
        }
      });

      // Update overall state
      setFundData(allExtractedFunds);
      
      if (errorCount === 0) {
        setExtractionStatus("completed");
        setExtractionLogs(prev => [...prev, `🎉 Successfully processed all ${filePaths.length} files! Total funds extracted: ${allExtractedFunds.length}`]);
      } else if (completedCount > 0) {
        setExtractionStatus("completed");
        setExtractionLogs(prev => [...prev, `⚠️ Processed ${completedCount}/${filePaths.length} files successfully. ${errorCount} files had errors. Total funds extracted: ${allExtractedFunds.length}`]);
      } else {
        setExtractionStatus("error");
        setExtractionLogs(prev => [...prev, `❌ All ${filePaths.length} files failed to process.`]);
      }

      // Calculate overall progress
      const overallProgress = Math.round((completedCount / filePaths.length) * 100);
      setExtractionProgress(overallProgress);
      
    } catch (error) {
      console.error("Parallel processing error:", error);
      setExtractionStatus("error");
      setExtractionLogs(prev => [...prev, `❌ Parallel processing failed: ${error}`]);
    } finally {
      setIsExtracting(false);
    }
  }, [initializeFileStatus, updateFileStatus, processCSVFile, processPDFFile]);

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
        {/* Compact Left Panel - Upload & Processing */}
        <div className="w-80 min-w-80 p-4 border-r border-gray-800 bg-gray-900/20">
          <div className="h-full flex flex-col space-y-4">
            {/* Upload Section */}
            <div className="flex-shrink-0">
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

            {/* File Processing Status */}
            {fileProcessingStatuses.size > 0 && (
              <div className="flex-1 flex flex-col overflow-hidden">
                <h3 className="text-sm font-semibold mb-3 text-blue-400">Processing Status</h3>
                <div className="flex-1 overflow-y-auto space-y-3 pr-1">
                  {Array.from(fileProcessingStatuses.values()).map((fileStatus) => (
                    <div key={fileStatus.filePath} className="bg-gray-800/30 rounded-lg p-3 border border-gray-700">
                      {/* Compact file header */}
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center space-x-1 min-w-0 flex-1">
                          <span className="text-xs font-medium text-white truncate">
                            {fileStatus.fileName}
                          </span>
                          <span className="text-xs px-1 py-0.5 rounded bg-gray-700 text-gray-300 flex-shrink-0">
                            {fileStatus.fileType.toUpperCase()}
                          </span>
                        </div>
                      </div>
                      
                      {/* Status badge */}
                      <div className={`text-xs px-2 py-1 rounded-full font-medium mb-2 inline-block ${
                        fileStatus.status === 'completed' ? 'bg-green-900 text-green-300' :
                        fileStatus.status === 'error' ? 'bg-red-900 text-red-300' :
                        fileStatus.status === 'processing' ? 'bg-blue-900 text-blue-300' :
                        'bg-gray-700 text-gray-300'
                      }`}>
                        {fileStatus.status === 'completed' ? '✓ Complete' :
                         fileStatus.status === 'error' ? '✗ Error' :
                         fileStatus.status === 'processing' ? '⏳ Processing' :
                         '⏸ Pending'}
                      </div>
                      
                      {/* Compact progress bar */}
                      <div className="mb-2">
                        <div className="flex justify-between text-xs text-gray-400 mb-1">
                          <span>Progress</span>
                          <span>{fileStatus.progress}%</span>
                        </div>
                        <div className="w-full bg-gray-700 rounded-full h-1.5">
                          <div 
                            className={`h-1.5 rounded-full transition-all duration-300 ${
                              fileStatus.status === 'error' ? 'bg-red-500' :
                              fileStatus.status === 'completed' ? 'bg-green-500' :
                              'bg-blue-500'
                            }`}
                            style={{ width: `${Math.max(0, Math.min(100, fileStatus.progress))}%` }}
                          />
                        </div>
                      </div>
                      
                      {/* Compact status message */}
                      <div className="text-xs text-gray-400 mb-1 truncate" title={fileStatus.message}>
                        {fileStatus.message}
                      </div>
                      
                      {/* Results summary */}
                      {fileStatus.extractedFunds.length > 0 && (
                        <div className="text-xs text-green-400">
                          📊 {fileStatus.extractedFunds.length} funds
                        </div>
                      )}
                      
                      {/* Error details */}
                      {fileStatus.error && (
                        <div className="text-xs text-red-400 mt-1 p-1.5 bg-red-900/20 rounded border border-red-800 truncate" title={fileStatus.error}>
                          {fileStatus.error}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Expanded Dashboard Area */}
        <div className="flex-1 flex flex-col min-w-0">
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
                <FundCompositionTable funds={fundData} />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}