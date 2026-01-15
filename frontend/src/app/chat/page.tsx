"use client";

import { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { Loader } from 'lucide-react';

function ChatPageContent() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get('session');

  return (
    <div className="h-screen overflow-hidden">
      <ChatInterface sessionId={sessionId || undefined} />
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense 
      fallback={
        <div className="h-screen flex items-center justify-center bg-gray-50">
          <div className="text-center">
            <Loader className="h-8 w-8 animate-spin mx-auto mb-4 text-blue-600" />
            <p className="text-gray-600">Loading chat interface...</p>
          </div>
        </div>
      }
    >
      <ChatPageContent />
    </Suspense>
  );
}