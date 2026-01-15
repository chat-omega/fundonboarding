import { NextRequest } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    // Get the backend URL from environment
    const backendUrl = process.env.BACKEND_URL || 'http://35.174.147.10:8002';
    const targetUrl = `${backendUrl}/fund-extraction-agent-mock`;
    
    console.log('🔍 Proxying mock streaming request to:', targetUrl);
    
    // Get request body
    const body = await request.text();
    
    // Forward the request to backend with streaming support
    const backendResponse = await fetch(targetUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
        'Cache-Control': 'no-cache',
      },
      body: body,
    });
    
    if (!backendResponse.ok) {
      console.error('❌ Backend mock response error:', backendResponse.status, backendResponse.statusText);
      return new Response(`Backend error: ${backendResponse.status} ${backendResponse.statusText}`, {
        status: backendResponse.status,
      });
    }
    
    console.log('✅ Backend mock streaming response received, starting proxy...');
    
    // Create a streaming response that forwards the backend stream
    const stream = new ReadableStream({
      start(controller) {
        const reader = backendResponse.body?.getReader();
        
        if (!reader) {
          controller.close();
          return;
        }
        
        const pump = async () => {
          try {
            while (true) {
              const { done, value } = await reader.read();
              
              if (done) {
                console.log('✅ Mock streaming completed');
                controller.close();
                break;
              }
              
              // Forward the chunk as-is
              controller.enqueue(value);
            }
          } catch (error) {
            console.error('❌ Mock streaming error:', error);
            controller.error(error);
          }
        };
        
        pump();
      }
    });
    
    // Return streaming response with proper headers
    return new Response(stream, {
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': '*',
        'Transfer-Encoding': 'chunked'
      },
    });
    
  } catch (error) {
    console.error('❌ Mock API route error:', error);
    return new Response(`API route error: ${error}`, {
      status: 500,
    });
  }
}