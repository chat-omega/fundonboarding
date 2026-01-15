import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Fund Onboarding Chat - Intelligent Portfolio Analysis',
  description: 'Chat-based interface for intelligent fund portfolio analysis and onboarding',
};

export default function ChatLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-gray-50">
      {children}
    </div>
  );
}