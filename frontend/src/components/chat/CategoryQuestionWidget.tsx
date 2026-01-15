import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { HelpCircle, TrendingUp, Lightbulb, Fund } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { CategoryQuestion, CategoryResponse } from '@/lib/chat-types';

interface CategoryQuestionWidgetProps {
  question: CategoryQuestion;
  onResponse: (response: CategoryResponse) => void;
  disabled?: boolean;
  className?: string;
}

export function CategoryQuestionWidget({
  question,
  onResponse,
  disabled = false,
  className = ''
}: CategoryQuestionWidgetProps) {
  const [selectedValue, setSelectedValue] = useState<string>('');
  const [customValue, setCustomValue] = useState<string>('');
  const [notes, setNotes] = useState<string>('');
  const [showCustomInput, setShowCustomInput] = useState(false);

  const handleOptionSelect = (value: string) => {
    setSelectedValue(value);
    if (value === 'custom') {
      setShowCustomInput(true);
    } else {
      setShowCustomInput(false);
      setCustomValue('');
    }
  };

  const handleSubmit = () => {
    if (!selectedValue) return;

    const response: CategoryResponse = {
      question_id: question.id,
      selected_value: selectedValue === 'custom' ? customValue : selectedValue,
      custom_value: selectedValue === 'custom' ? customValue : undefined,
      notes: notes.trim() || undefined,
      responded_at: new Date().toISOString()
    };

    onResponse(response);
  };

  const canSubmit = selectedValue && (selectedValue !== 'custom' || customValue.trim());

  const getQuestionIcon = () => {
    switch (question.question_type) {
      case 'asset_class':
        return <TrendingUp className="h-5 w-5 text-blue-600" />;
      case 'equity_subcategory':
        return <Fund className="h-5 w-5 text-green-600" />;
      case 'fixed_income_subcategory':
        return <Fund className="h-5 w-5 text-purple-600" />;
      case 'alternatives_type':
        return <Fund className="h-5 w-5 text-orange-600" />;
      default:
        return <HelpCircle className="h-5 w-5 text-gray-600" />;
    }
  };

  const getQuestionTypeLabel = () => {
    switch (question.question_type) {
      case 'asset_class':
        return 'Asset Class';
      case 'equity_subcategory':
        return 'Equity Details';
      case 'fixed_income_subcategory':
        return 'Fixed Income Details';
      case 'alternatives_type':
        return 'Alternative Type';
      default:
        return 'Category Question';
    }
  };

  return (
    <Card className={`w-full max-w-2xl ${className}`}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            {getQuestionIcon()}
            <span>{getQuestionTypeLabel()}</span>
          </CardTitle>
          <Badge variant="outline" className="text-xs">
            {question.required ? 'Required' : 'Optional'}
          </Badge>
        </div>

        {question.context.fund_ticker && (
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Fund className="h-4 w-4" />
            <span className="font-mono font-medium">{question.context.fund_ticker}</span>
            {question.context.fund_name && (
              <span className="text-gray-500">- {question.context.fund_name}</span>
            )}
          </div>
        )}
      </CardHeader>

      <CardContent className="space-y-6">
        <div>
          <h3 className="text-lg font-medium text-gray-900 mb-3">
            {question.question_text}
          </h3>
          
          {question.context.research_summary && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <div className="flex items-start gap-2">
                <Lightbulb className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-medium text-blue-900 mb-2">Research Summary</h4>
                  <p className="text-sm text-blue-800">{question.context.research_summary}</p>
                </div>
              </div>
            </div>
          )}
        </div>

        <div>
          <RadioGroup
            value={selectedValue}
            onValueChange={handleOptionSelect}
            className="space-y-3"
            disabled={disabled}
          >
            {question.options.map((option) => (
              <div key={option.value} className="flex items-start space-x-3">
                <RadioGroupItem 
                  value={option.value} 
                  id={option.value}
                  className="mt-1"
                />
                <div className="flex-1">
                  <Label 
                    htmlFor={option.value}
                    className="text-base font-medium cursor-pointer"
                  >
                    <div className="flex items-center gap-2">
                      {option.label}
                      {option.recommended && (
                        <Badge variant="secondary" className="text-xs bg-green-100 text-green-700">
                          Recommended
                        </Badge>
                      )}
                      {option.confidence && (
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Badge 
                                variant="outline" 
                                className="text-xs"
                              >
                                {Math.round(option.confidence * 100)}%
                              </Badge>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>Classification confidence</p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      )}
                    </div>
                  </Label>
                  {option.description && (
                    <p className="text-sm text-gray-600 mt-1">{option.description}</p>
                  )}
                </div>
              </div>
            ))}

            {question.allow_custom && (
              <div className="flex items-start space-x-3">
                <RadioGroupItem 
                  value="custom" 
                  id="custom"
                  className="mt-1"
                />
                <div className="flex-1">
                  <Label 
                    htmlFor="custom"
                    className="text-base font-medium cursor-pointer"
                  >
                    Other (specify)
                  </Label>
                </div>
              </div>
            )}
          </RadioGroup>

          {showCustomInput && (
            <div className="mt-4 pl-6">
              <Label htmlFor="custom-value" className="text-sm font-medium">
                Please specify:
              </Label>
              <Input
                id="custom-value"
                value={customValue}
                onChange={(e) => setCustomValue(e.target.value)}
                placeholder="Enter custom category..."
                className="mt-1"
                disabled={disabled}
              />
            </div>
          )}
        </div>

        <div>
          <Label htmlFor="notes" className="text-sm font-medium">
            Additional Notes (Optional)
          </Label>
          <Textarea
            id="notes"
            placeholder="Add any additional context or reasoning..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="mt-1 min-h-[80px]"
            disabled={disabled}
          />
        </div>

        <div className="flex justify-end pt-4 border-t">
          <Button 
            onClick={handleSubmit}
            disabled={!canSubmit || disabled}
            className="min-w-[120px]"
          >
            Submit Answer
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}