import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Info, AlertCircle, CheckCircle, Edit } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

interface CategorySelectorProps {
  fundName: string;
  ticker: string;
  currentCategory: {
    asset_class: 'Equity' | 'Fixed Income' | 'Cash' | 'Alternatives';
    equity_region?: 'US' | 'International' | 'Emerging' | 'Global';
    equity_style?: 'Value' | 'Growth' | 'Blend';
    equity_size?: 'Large' | 'Mid' | 'Small' | 'Micro';
    fixed_income_type?: 'Government' | 'Corporate' | 'Municipal' | 'High Yield';
    fixed_income_duration?: 'Short' | 'Intermediate' | 'Long';
    alternatives_type?: string;
  };
  confidence: number;
  alternatives?: Array<{
    asset_class: string;
    confidence: number;
    reasoning: string;
  }>;
  onCategoryChange: (newCategory: any, reason: string) => void;
  onCancel?: () => void;
  disabled?: boolean;
}

const assetClassOptions = ['Equity', 'Fixed Income', 'Cash', 'Alternatives'];
const equityRegionOptions = ['US', 'International', 'Emerging', 'Global'];
const equityStyleOptions = ['Value', 'Growth', 'Blend'];
const equitySizeOptions = ['Large', 'Mid', 'Small', 'Micro'];
const fixedIncomeTypeOptions = ['Government', 'Corporate', 'Municipal', 'High Yield'];
const fixedIncomeDurationOptions = ['Short', 'Intermediate', 'Long'];

export function CategorySelector({
  fundName,
  ticker,
  currentCategory,
  confidence,
  alternatives = [],
  onCategoryChange,
  onCancel,
  disabled = false
}: CategorySelectorProps) {
  const [selectedCategory, setSelectedCategory] = useState(currentCategory);
  const [reason, setReason] = useState('');
  const [isModified, setIsModified] = useState(false);
  const [showAlternatives, setShowAlternatives] = useState(false);

  useEffect(() => {
    const hasChanged = JSON.stringify(selectedCategory) !== JSON.stringify(currentCategory);
    setIsModified(hasChanged);
  }, [selectedCategory, currentCategory]);

  const handleAssetClassChange = (assetClass: string) => {
    const newCategory = {
      asset_class: assetClass as any,
      equity_region: assetClass === 'Equity' ? selectedCategory.equity_region : undefined,
      equity_style: assetClass === 'Equity' ? selectedCategory.equity_style : undefined,
      equity_size: assetClass === 'Equity' ? selectedCategory.equity_size : undefined,
      fixed_income_type: assetClass === 'Fixed Income' ? selectedCategory.fixed_income_type : undefined,
      fixed_income_duration: assetClass === 'Fixed Income' ? selectedCategory.fixed_income_duration : undefined,
      alternatives_type: assetClass === 'Alternatives' ? selectedCategory.alternatives_type : undefined,
    };
    setSelectedCategory(newCategory);
  };

  const handleSubCategoryChange = (field: string, value: string) => {
    setSelectedCategory(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleAlternativeSelect = (alternative: any) => {
    const newCategory = {
      asset_class: alternative.asset_class,
      equity_region: alternative.asset_class === 'Equity' ? alternative.equity_region : undefined,
      equity_style: alternative.asset_class === 'Equity' ? alternative.equity_style : undefined,
      equity_size: alternative.asset_class === 'Equity' ? alternative.equity_size : undefined,
      fixed_income_type: alternative.asset_class === 'Fixed Income' ? alternative.fixed_income_type : undefined,
      fixed_income_duration: alternative.asset_class === 'Fixed Income' ? alternative.fixed_income_duration : undefined,
      alternatives_type: alternative.asset_class === 'Alternatives' ? alternative.alternatives_type : undefined,
    };
    setSelectedCategory(newCategory);
    setReason(alternative.reasoning);
    setShowAlternatives(false);
  };

  const handleSubmit = () => {
    if (!reason.trim()) {
      alert('Please provide a reason for the categorization change.');
      return;
    }
    onCategoryChange(selectedCategory, reason);
  };

  const getConfidenceColor = (conf: number) => {
    if (conf >= 0.8) return 'text-green-600 bg-green-50';
    if (conf >= 0.6) return 'text-yellow-600 bg-yellow-50';
    return 'text-red-600 bg-red-50';
  };

  const getConfidenceIcon = (conf: number) => {
    if (conf >= 0.8) return <CheckCircle className="h-4 w-4" />;
    if (conf >= 0.6) return <AlertCircle className="h-4 w-4" />;
    return <AlertCircle className="h-4 w-4" />;
  };

  return (
    <Card className="w-full max-w-2xl">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Edit className="h-5 w-5" />
            Edit Category: {fundName}
          </CardTitle>
          <Badge variant="outline" className="font-mono text-sm">
            {ticker}
          </Badge>
        </div>
        
        <div className="flex items-center gap-2">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className={`flex items-center gap-1 px-2 py-1 rounded-full ${getConfidenceColor(confidence)}`}>
                  {getConfidenceIcon(confidence)}
                  <span className="text-sm font-medium">
                    {Math.round(confidence * 100)}% confidence
                  </span>
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p>Current classification confidence score</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
          
          {alternatives.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowAlternatives(!showAlternatives)}
            >
              <Info className="h-4 w-4 mr-1" />
              View Alternatives ({alternatives.length})
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {showAlternatives && alternatives.length > 0 && (
          <div className="border rounded-lg p-4 bg-gray-50">
            <h4 className="font-medium mb-3">Alternative Classifications:</h4>
            <div className="space-y-2">
              {alternatives.map((alt, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 bg-white rounded border cursor-pointer hover:bg-blue-50"
                  onClick={() => handleAlternativeSelect(alt)}
                >
                  <div>
                    <Badge variant="secondary" className="mb-1">
                      {alt.asset_class}
                    </Badge>
                    <p className="text-sm text-gray-600">{alt.reasoning}</p>
                  </div>
                  <div className={`px-2 py-1 rounded text-sm ${getConfidenceColor(alt.confidence)}`}>
                    {Math.round(alt.confidence * 100)}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-4">
          <div>
            <Label htmlFor="asset-class">Asset Class *</Label>
            <Select
              value={selectedCategory.asset_class}
              onValueChange={handleAssetClassChange}
              disabled={disabled}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select asset class" />
              </SelectTrigger>
              <SelectContent>
                {assetClassOptions.map(option => (
                  <SelectItem key={option} value={option}>
                    {option}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {selectedCategory.asset_class === 'Equity' && (
            <div className="space-y-3 pl-4 border-l-2 border-blue-200">
              <div>
                <Label htmlFor="equity-region">Region</Label>
                <Select
                  value={selectedCategory.equity_region || ''}
                  onValueChange={(value) => handleSubCategoryChange('equity_region', value)}
                  disabled={disabled}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select region" />
                  </SelectTrigger>
                  <SelectContent>
                    {equityRegionOptions.map(option => (
                      <SelectItem key={option} value={option}>
                        {option}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="equity-style">Style</Label>
                <Select
                  value={selectedCategory.equity_style || ''}
                  onValueChange={(value) => handleSubCategoryChange('equity_style', value)}
                  disabled={disabled}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select style" />
                  </SelectTrigger>
                  <SelectContent>
                    {equityStyleOptions.map(option => (
                      <SelectItem key={option} value={option}>
                        {option}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="equity-size">Size</Label>
                <Select
                  value={selectedCategory.equity_size || ''}
                  onValueChange={(value) => handleSubCategoryChange('equity_size', value)}
                  disabled={disabled}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select size" />
                  </SelectTrigger>
                  <SelectContent>
                    {equitySizeOptions.map(option => (
                      <SelectItem key={option} value={option}>
                        {option}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          {selectedCategory.asset_class === 'Fixed Income' && (
            <div className="space-y-3 pl-4 border-l-2 border-green-200">
              <div>
                <Label htmlFor="fixed-income-type">Type</Label>
                <Select
                  value={selectedCategory.fixed_income_type || ''}
                  onValueChange={(value) => handleSubCategoryChange('fixed_income_type', value)}
                  disabled={disabled}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    {fixedIncomeTypeOptions.map(option => (
                      <SelectItem key={option} value={option}>
                        {option}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="fixed-income-duration">Duration</Label>
                <Select
                  value={selectedCategory.fixed_income_duration || ''}
                  onValueChange={(value) => handleSubCategoryChange('fixed_income_duration', value)}
                  disabled={disabled}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select duration" />
                  </SelectTrigger>
                  <SelectContent>
                    {fixedIncomeDurationOptions.map(option => (
                      <SelectItem key={option} value={option}>
                        {option}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          {selectedCategory.asset_class === 'Alternatives' && (
            <div className="pl-4 border-l-2 border-purple-200">
              <Label htmlFor="alternatives-type">Alternative Type</Label>
              <Select
                value={selectedCategory.alternatives_type || ''}
                onValueChange={(value) => handleSubCategoryChange('alternatives_type', value)}
                disabled={disabled}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select alternative type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="REIT">REIT</SelectItem>
                  <SelectItem value="Commodity">Commodity</SelectItem>
                  <SelectItem value="Hedge Fund">Hedge Fund</SelectItem>
                  <SelectItem value="Private Equity">Private Equity</SelectItem>
                  <SelectItem value="Infrastructure">Infrastructure</SelectItem>
                  <SelectItem value="Other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}

          <div>
            <Label htmlFor="reason">Reason for Classification {isModified && '*'}</Label>
            <Textarea
              id="reason"
              placeholder={isModified ? "Please provide a reason for this categorization change..." : "Add additional notes (optional)"}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              disabled={disabled}
              className="min-h-[80px]"
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t">
          {onCancel && (
            <Button variant="outline" onClick={onCancel} disabled={disabled}>
              Cancel
            </Button>
          )}
          <Button 
            onClick={handleSubmit} 
            disabled={disabled || (isModified && !reason.trim())}
            className="min-w-[120px]"
          >
            {isModified ? 'Apply Changes' : 'Confirm Category'}
          </Button>
        </div>

        {isModified && !reason.trim() && (
          <p className="text-sm text-red-600 text-center">
            Please provide a reason when making changes to the categorization.
          </p>
        )}
      </CardContent>
    </Card>
  );
}