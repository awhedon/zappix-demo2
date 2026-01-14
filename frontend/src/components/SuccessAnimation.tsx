'use client';

import { motion } from 'framer-motion';

interface SuccessAnimationProps {
  title: string;
  message: string;
}

export function SuccessAnimation({ title, message }: SuccessAnimationProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col items-center justify-center py-16 text-center"
    >
      {/* Animated checkmark */}
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', stiffness: 200, damping: 15, delay: 0.2 }}
        className="relative mb-8"
      >
        {/* Glow effect */}
        <div className="absolute inset-0 w-32 h-32 bg-zappix-accent/30 rounded-full blur-2xl animate-pulse" />
        
        {/* Circle background */}
        <div className="relative w-32 h-32 rounded-full bg-gradient-to-br from-zappix-accent to-zappix-accent/70 flex items-center justify-center shadow-xl shadow-zappix-accent/30">
          <svg
            className="w-16 h-16 text-zappix-navy"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <motion.path
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 0.5, delay: 0.5 }}
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={3}
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>

        {/* Particles */}
        {[...Array(8)].map((_, i) => (
          <motion.div
            key={i}
            initial={{ scale: 0, x: 0, y: 0 }}
            animate={{
              scale: [0, 1, 0],
              x: Math.cos((i * Math.PI) / 4) * 80,
              y: Math.sin((i * Math.PI) / 4) * 80,
            }}
            transition={{ duration: 0.8, delay: 0.3 + i * 0.05 }}
            className="absolute top-1/2 left-1/2 w-3 h-3 rounded-full bg-zappix-gold"
            style={{ transformOrigin: 'center' }}
          />
        ))}
      </motion.div>

      <motion.h2
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="text-3xl md:text-4xl font-display font-bold text-white mb-4"
      >
        {title}
      </motion.h2>

      <motion.p
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.7 }}
        className="text-lg text-white/70 max-w-md"
      >
        {message}
      </motion.p>
    </motion.div>
  );
}

