"use client";

import { useEffect, useRef } from "react";
import { CheckCircle, Circle, AlertCircle, Activity } from "lucide-react";
import { FundData, ExtractionStatus, StageStatus } from "@/lib/types";

interface ExtractionCanvasProps {
  status: ExtractionStatus;
  progress: number;
  stage: string;
  logs: string[];
  fundData: FundData[];
  isExtracting: boolean;
}

export function ExtractionCanvas({
  status,
  progress,
  stage,
  logs,
  fundData,
  isExtracting
}: ExtractionCanvasProps) {
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const getStageStatus = (stageName: string): "pending" | "processing" | "completed" | "error" => {
    if (status === "error") return "error";
    if (stage === stageName) return "processing";
    
    const stageOrder = ["setup", "parsing", "splitting", "extracting", "analysis", "complete"];
    const currentIndex = stageOrder.indexOf(stage);
    const stageIndex = stageOrder.indexOf(stageName);
    
    if (currentIndex > stageIndex) return "completed";
    return "pending";
  };

  const StageIndicator = ({ name, stageName }: { name: string; stageName: string }) => {
    const stageStatus = getStageStatus(stageName);
    
    const getIcon = () => {
      switch (stageStatus) {
        case "completed":
          return <CheckCircle className="h-5 w-5 text-green-400" />;
        case "processing":
          return <Activity className="h-5 w-5 text-blue-400 animate-pulse" />;
        case "error":
          return <AlertCircle className="h-5 w-5 text-red-400" />;
        default:
          return <Circle className="h-5 w-5 text-gray-600" />;
      }
    };

    const getTextColor = () => {
      switch (stageStatus) {
        case "completed":
          return "text-green-400";
        case "processing":
          return "text-blue-400";
        case "error":
          return "text-red-400";
        default:
          return "text-gray-500";
      }
    };

    return (
      <div className="flex items-center space-x-3 p-3 rounded-lg bg-gray-800/30 border border-gray-700">
        {getIcon()}
        <span className={`font-medium ${getTextColor()}`}>{name}</span>
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col space-y-6">
      {/* Progress Section */}
      <div className="bg-gray-800/50 rounded-lg p-6 border border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">
            🔄 Extraction Progress
          </h3>
          <span className="text-sm text-gray-400">
            {progress}% Complete
          </span>
        </div>
        
        {/* Progress Bar */}
        <div className="w-full bg-gray-700 rounded-full h-3 mb-4">
          <div
            className="bg-gradient-to-r from-blue-600 to-blue-400 h-3 rounded-full transition-all duration-300 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
        
        {/* Current Stage */}
        {stage && (
          <div className="text-center">
            <p className="text-sm text-gray-400">Current Stage:</p>
            <p className="text-blue-400 font-medium capitalize">
              {stage.replace(/([A-Z])/g, " $1").trim()}
            </p>
          </div>
        )}
      </div>

      {/* Stages Overview */}
      <div className="bg-gray-800/50 rounded-lg p-6 border border-gray-700">
        <h3 className="text-lg font-semibold text-white mb-4">
          📋 Processing Stages
        </h3>
        
        <div className="grid grid-cols-2 gap-3">
          <StageIndicator name="Setup" stageName="setup" />
          <StageIndicator name="Parsing" stageName="parsing" />
          <StageIndicator name="Splitting" stageName="splitting" />
          <StageIndicator name="Extracting" stageName="extracting" />
          <StageIndicator name="Analysis" stageName="analysis" />
          <StageIndicator name="Complete" stageName="complete" />
        </div>
      </div>

      {/* Real-time Logs */}
      <div className="flex-1 bg-gray-800/50 rounded-lg border border-gray-700 flex flex-col">
        <div className="p-4 border-b border-gray-700">
          <h3 className="text-lg font-semibold text-white">
            📝 Processing Logs
          </h3>
        </div>
        
        <div className="flex-1 p-4 overflow-hidden">
          <div className="h-full overflow-y-auto space-y-1">
            {logs.length === 0 && !isExtracting ? (
              <div className="flex items-center justify-center h-full">
                <p className="text-gray-500 text-sm">
                  Upload a PDF to start seeing extraction logs...
                </p>
              </div>
            ) : (
              logs.map((log, idx) => (
                <div
                  key={idx}
                  className={`text-sm p-2 rounded font-mono ${
                    log.includes("❌") 
                      ? "text-red-400 bg-red-500/10" 
                      : log.includes("✅")
                        ? "text-green-400 bg-green-500/10"
                        : log.includes("🔍") || log.includes("📋")
                          ? "text-blue-400 bg-blue-500/10"
                          : "text-gray-300"
                  }`}
                >
                  {log}
                </div>
              ))
            )}
            <div ref={logsEndRef} />
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      {fundData.length > 0 && (
        <div className="bg-gray-800/50 rounded-lg p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">
            📊 Quick Stats
          </h3>
          
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-blue-400">{fundData.length}</p>
              <p className="text-xs text-gray-400">Funds Extracted</p>
            </div>
            
            <div className="text-center">
              <p className="text-2xl font-bold text-green-400">
                {fundData.filter(f => f.one_year_return).length}
              </p>
              <p className="text-xs text-gray-400">With Returns</p>
            </div>
            
            <div className="text-center">
              <p className="text-2xl font-bold text-purple-400">
                {fundData.filter(f => f.nav).length}
              </p>
              <p className="text-xs text-gray-400">With NAV</p>
            </div>
          </div>
          
          {fundData.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-700">
              <p className="text-xs text-gray-400 mb-2">Extracted Funds:</p>
              <div className="flex flex-wrap gap-1">
                {fundData.slice(0, 3).map((fund, idx) => (
                  <span
                    key={idx}
                    className="text-xs bg-blue-500/20 text-blue-300 px-2 py-1 rounded"
                  >
                    {fund.fund_name?.split(" ")[2] || `Fund ${idx + 1}`}
                  </span>
                ))}
                {fundData.length > 3 && (
                  <span className="text-xs bg-gray-500/20 text-gray-300 px-2 py-1 rounded">
                    +{fundData.length - 3} more
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}