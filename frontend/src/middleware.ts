import { NextRequest, NextResponse } from 'next/server';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  // Only handle API routes
  if (pathname.startsWith('/api/')) {
    // Skip streaming endpoints - they have dedicated API route handlers
    if (pathname === '/api/fund-extraction-agent' || pathname === '/api/fund-extraction-agent-mock') {
      console.log('🔍 Skipping middleware for streaming endpoint:', pathname);
      return NextResponse.next();
    }
    
    // Get the backend URL from environment variable (runtime)
    const backendUrl = process.env.BACKEND_URL || 'http://35.174.147.10:8002';
    
    // Create the target URL
    let targetPath = pathname;
    const searchParams = request.nextUrl.searchParams.toString();
    if (searchParams) {
      targetPath += `?${searchParams}`;
    }
    
    // For onboarding API routes, map to the backend onboarding endpoints
    if (pathname.startsWith('/api/onboarding/')) {
      const backendTargetUrl = `${backendUrl}${targetPath}`;
      return NextResponse.rewrite(new URL(backendTargetUrl));
    }
    
    // For other API routes, map directly to backend
    if (pathname.startsWith('/api/')) {
      const backendTargetUrl = `${backendUrl}${targetPath.replace('/api', '')}`;
      return NextResponse.rewrite(new URL(backendTargetUrl));
    }
  }
  
  return NextResponse.next();
}

export const config = {
  matcher: [
    '/api/:path*',
  ],
};