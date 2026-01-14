'use client';

import { motion } from 'framer-motion';

interface FormFieldProps {
  label: string;
  value: string | null;
  fallback?: string;
  delay?: number;
}

export function FormField({ label, value, fallback = 'Not provided', delay = 0 }: FormFieldProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="form-field group"
    >
      <div className="absolute inset-0 bg-gradient-to-r from-zappix-accent/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-xl" />
      <div className="relative">
        <div className="form-field-label">{label}</div>
        <div className="form-field-value">
          {value || <span className="text-white/40 italic">{fallback}</span>}
        </div>
      </div>
    </motion.div>
  );
}

