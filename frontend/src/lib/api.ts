const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://zappix2-backend.aldea.ai';

export interface FormData {
  session_id: string;
  first_name: string;
  language: string;
  date_of_birth: string | null;
  zip_code: string | null;
  general_health: string | null;
  general_health_display: string | null;
  moderate_activities_limitation: string | null;
  moderate_activities_display: string | null;
  climbing_stairs_limitation: string | null;
  climbing_stairs_display: string | null;
  call_completed: boolean;
}

export interface OutboundCallRequest {
  first_name: string;
  phone_number: string;
  language?: 'en' | 'es';
}

export interface OutboundCallResponse {
  success: boolean;
  session_id: string;
  message: string;
}

export async function getFormData(sessionId: string): Promise<FormData> {
  const response = await fetch(`${API_URL}/api/forms/${sessionId}`);
  
  if (!response.ok) {
    throw new Error('Failed to fetch form data');
  }
  
  return response.json();
}

export async function submitForm(sessionId: string, signature: string): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_URL}/api/forms/${sessionId}/submit`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ signature }),
  });
  
  if (!response.ok) {
    throw new Error('Failed to submit form');
  }
  
  return response.json();
}

export async function initiateOutboundCall(request: OutboundCallRequest): Promise<OutboundCallResponse> {
  const response = await fetch(`${API_URL}/api/calls/outbound`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error('Failed to initiate call');
  }
  
  return response.json();
}

export async function getSessionStatus(sessionId: string): Promise<{
  session_id: string;
  call_completed: boolean;
  form_submitted: boolean;
  opted_in_for_sms: boolean;
}> {
  const response = await fetch(`${API_URL}/api/forms/${sessionId}/status`);
  
  if (!response.ok) {
    throw new Error('Failed to fetch session status');
  }
  
  return response.json();
}

