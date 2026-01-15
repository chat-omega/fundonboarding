import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { FundCategorization } from '@/lib/chat-types';
import { 
  TrendingUp, 
  DollarSign, 
  AlertTriangle, 
  CheckCircle,
  PieChart
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface CategorizationSummaryProps {
  categorizations: FundCategorization[];
  className?: string;
}

export function CategorizationSummary({ 
  categorizations, 
  className = '' 
}: CategorizationSummaryProps) {
  const totalFunds = categorizations.length;
  const approvedFunds = categorizations.filter(c => c.approved).length;
  const lowConfidenceFunds = categorizations.filter(c => c.confidence_score < 0.6).length;
  const highConfidenceFunds = categorizations.filter(c => c.confidence_score >= 0.8).length;

  const assetClassBreakdown = categorizations.reduce((acc, cat) => {
    acc[cat.asset_class] = (acc[cat.asset_class] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const averageConfidence = categorizations.reduce((sum, cat) => sum + cat.confidence_score, 0) / totalFunds;

  const getAssetClassColor = (assetClass: string) => {
    switch (assetClass) {
      case 'Equity':
        return 'bg-blue-500';
      case 'Fixed Income':
        return 'bg-green-500';
      case 'Cash':
        return 'bg-gray-500';
      case 'Alternatives':
        return 'bg-purple-500';
      default:
        return 'bg-gray-400';
    }
  };

  return (
    <Card className={`w-full ${className}`}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <PieChart className="h-5 w-5 text-blue-600" />
          <span>Categorization Summary</span>
        </CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* Overall Statistics */}
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{totalFunds}</div>
            <div className="text-sm text-gray-600">Total Funds</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{approvedFunds}</div>
            <div className="text-sm text-gray-600">Approved</div>
          </div>
        </div>

        {/* Confidence Overview */}
        <div>
          <div className="flex justify-between text-sm mb-2">
            <span>Average Confidence</span>
            <span className="font-medium">{Math.round(averageConfidence * 100)}%</span>
          </div>
          <Progress 
            value={averageConfidence * 100} 
            className="h-2 mb-3"
          />
          
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="text-center">
              <div className="flex items-center justify-center gap-1 text-red-600">
                <AlertTriangle className="h-3 w-3" />
                <span>{lowConfidenceFunds}</span>
              </div>
              <div className="text-gray-600">Low (&lt;60%)</div>
            </div>
            <div className="text-center">
              <div className="flex items-center justify-center gap-1 text-yellow-600">
                <DollarSign className="h-3 w-3" />
                <span>{totalFunds - lowConfidenceFunds - highConfidenceFunds}</span>
              </div>
              <div className="text-gray-600">Medium</div>
            </div>
            <div className="text-center">
              <div className="flex items-center justify-center gap-1 text-green-600">
                <CheckCircle className="h-3 w-3" />
                <span>{highConfidenceFunds}</span>
              </div>
              <div className="text-gray-600">High (≥80%)</div>
            </div>
          </div>
        </div>

        {/* Asset Class Breakdown */}
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-3">Asset Class Distribution</h4>
          <div className="space-y-2">
            {Object.entries(assetClassBreakdown)
              .sort(([, a], [, b]) => b - a)
              .map(([assetClass, count]) => {
                const percentage = (count / totalFunds) * 100;
                return (
                  <div key={assetClass} className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span>{assetClass}</span>
                      <span className="text-gray-600">{count} ({Math.round(percentage)}%)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-gray-200 rounded-full h-1.5">
                        <div 
                          className={cn("h-1.5 rounded-full", getAssetClassColor(assetClass))}
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
          </div>
        </div>

        {/* Sub-category Breakdown for Equity */}
        {assetClassBreakdown['Equity'] && (
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-3">Equity Breakdown</h4>
            <div className="space-y-2">
              {/* Region */}
              {(() => {
                const equityFunds = categorizations.filter(c => c.asset_class === 'Equity');
                const regionBreakdown = equityFunds.reduce((acc, cat) => {
                  if (cat.equity_region) {
                    acc[cat.equity_region] = (acc[cat.equity_region] || 0) + 1;
                  }
                  return acc;
                }, {} as Record<string, number>);

                return Object.entries(regionBreakdown).length > 0 ? (
                  <div>
                    <div className="text-xs font-medium text-gray-700 mb-1">By Region:</div>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(regionBreakdown).map(([region, count]) => (
                        <Badge key={region} variant="outline" className="text-xs">
                          {region}: {count}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ) : null;
              })()}

              {/* Style */}
              {(() => {
                const equityFunds = categorizations.filter(c => c.asset_class === 'Equity');
                const styleBreakdown = equityFunds.reduce((acc, cat) => {
                  if (cat.equity_style) {
                    acc[cat.equity_style] = (acc[cat.equity_style] || 0) + 1;
                  }
                  return acc;
                }, {} as Record<string, number>);

                return Object.entries(styleBreakdown).length > 0 ? (
                  <div>
                    <div className="text-xs font-medium text-gray-700 mb-1">By Style:</div>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(styleBreakdown).map(([style, count]) => (
                        <Badge key={style} variant="outline" className="text-xs">
                          {style}: {count}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ) : null;
              })()}
            </div>
          </div>
        )}

        {/* Sub-category Breakdown for Fixed Income */}
        {assetClassBreakdown['Fixed Income'] && (
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-3">Fixed Income Breakdown</h4>
            <div className="space-y-2">
              {/* Type */}
              {(() => {
                const fixedIncomeFunds = categorizations.filter(c => c.asset_class === 'Fixed Income');
                const typeBreakdown = fixedIncomeFunds.reduce((acc, cat) => {
                  if (cat.fixed_income_type) {
                    acc[cat.fixed_income_type] = (acc[cat.fixed_income_type] || 0) + 1;
                  }
                  return acc;
                }, {} as Record<string, number>);

                return Object.entries(typeBreakdown).length > 0 ? (
                  <div>
                    <div className="text-xs font-medium text-gray-700 mb-1">By Type:</div>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(typeBreakdown).map(([type, count]) => (
                        <Badge key={type} variant="outline" className="text-xs">
                          {type}: {count}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ) : null;
              })()}

              {/* Duration */}
              {(() => {
                const fixedIncomeFunds = categorizations.filter(c => c.asset_class === 'Fixed Income');
                const durationBreakdown = fixedIncomeFunds.reduce((acc, cat) => {
                  if (cat.fixed_income_duration) {
                    acc[cat.fixed_income_duration] = (acc[cat.fixed_income_duration] || 0) + 1;
                  }
                  return acc;
                }, {} as Record<string, number>);

                return Object.entries(durationBreakdown).length > 0 ? (
                  <div>
                    <div className="text-xs font-medium text-gray-700 mb-1">By Duration:</div>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(durationBreakdown).map(([duration, count]) => (
                        <Badge key={duration} variant="outline" className="text-xs">
                          {duration}: {count}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ) : null;
              })()}
            </div>
          </div>
        )}

        {/* Actions Needed */}
        {(lowConfidenceFunds > 0 || approvedFunds < totalFunds) && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 text-yellow-600 mt-0.5" />
              <div className="text-sm">
                <div className="font-medium text-yellow-800">Actions Required</div>
                {lowConfidenceFunds > 0 && (
                  <div className="text-yellow-700">
                    {lowConfidenceFunds} fund{lowConfidenceFunds === 1 ? '' : 's'} need{lowConfidenceFunds === 1 ? 's' : ''} review (low confidence)
                  </div>
                )}
                {approvedFunds < totalFunds && (
                  <div className="text-yellow-700">
                    {totalFunds - approvedFunds} fund{totalFunds - approvedFunds === 1 ? '' : 's'} pending approval
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}