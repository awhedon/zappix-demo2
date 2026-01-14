import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPhoneNumber(phone: string): string {
  const cleaned = phone.replace(/\D/g, '');
  const match = cleaned.match(/^(\d{1})?(\d{3})(\d{3})(\d{4})$/);
  if (match) {
    const intlCode = match[1] ? `+${match[1]} ` : '';
    return [intlCode, '(', match[2], ') ', match[3], '-', match[4]].join('');
  }
  return phone;
}

export const translations = {
  en: {
    title: 'Health Assessment Form',
    subtitle: 'Review and Sign',
    description: 'Please review your responses below and sign to complete your annual health assessment.',
    personalInfo: 'Personal Information',
    healthResponses: 'Health Assessment Responses',
    name: 'Name',
    dateOfBirth: 'Date of Birth',
    zipCode: 'Zip Code',
    generalHealth: 'General Health Status',
    moderateActivities: 'Moderate Activities Limitation',
    climbingStairs: 'Climbing Stairs Limitation',
    signature: 'Signature',
    signatureInstructions: 'Please sign in the box below to confirm your responses',
    clear: 'Clear',
    submit: 'Submit Form',
    submitting: 'Submitting...',
    success: 'Form Submitted Successfully!',
    successMessage: 'Thank you for completing your health assessment. A confirmation email has been sent.',
    error: 'Error',
    notProvided: 'Not provided',
    poweredBy: 'Powered by',
  },
  es: {
    title: 'Formulario de Evaluación de Salud',
    subtitle: 'Revisar y Firmar',
    description: 'Por favor revise sus respuestas a continuación y firme para completar su evaluación de salud anual.',
    personalInfo: 'Información Personal',
    healthResponses: 'Respuestas de Evaluación de Salud',
    name: 'Nombre',
    dateOfBirth: 'Fecha de Nacimiento',
    zipCode: 'Código Postal',
    generalHealth: 'Estado de Salud General',
    moderateActivities: 'Limitación en Actividades Moderadas',
    climbingStairs: 'Limitación al Subir Escaleras',
    signature: 'Firma',
    signatureInstructions: 'Por favor firme en el cuadro de abajo para confirmar sus respuestas',
    clear: 'Borrar',
    submit: 'Enviar Formulario',
    submitting: 'Enviando...',
    success: '¡Formulario Enviado Exitosamente!',
    successMessage: 'Gracias por completar su evaluación de salud. Se ha enviado un correo de confirmación.',
    error: 'Error',
    notProvided: 'No proporcionado',
    poweredBy: 'Desarrollado por',
  },
};

export type Language = keyof typeof translations;

