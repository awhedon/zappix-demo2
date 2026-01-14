'use client';

import { useRef, useEffect, useState } from 'react';
import SignatureCanvas from 'react-signature-canvas';
import { motion } from 'framer-motion';
import { Eraser, Check } from 'lucide-react';

interface SignaturePadProps {
  onSignature: (signature: string | null) => void;
  clearText: string;
}

export function SignaturePad({ onSignature, clearText }: SignaturePadProps) {
  const sigRef = useRef<SignatureCanvas>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [hasSignature, setHasSignature] = useState(false);
  const [dimensions, setDimensions] = useState({ width: 0, height: 200 });

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.offsetWidth,
          height: 200,
        });
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  const handleEnd = () => {
    if (sigRef.current && !sigRef.current.isEmpty()) {
      setHasSignature(true);
      const dataUrl = sigRef.current.toDataURL('image/png');
      onSignature(dataUrl);
    }
  };

  const handleClear = () => {
    if (sigRef.current) {
      sigRef.current.clear();
      setHasSignature(false);
      onSignature(null);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.6 }}
      className="space-y-4"
    >
      <div 
        ref={containerRef}
        className="signature-pad relative bg-white rounded-2xl overflow-hidden shadow-lg shadow-black/20"
        style={{ height: dimensions.height }}
      >
        {/* Grid lines for signature */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute bottom-12 left-4 right-4 border-b-2 border-dashed border-gray-300" />
          <div className="absolute bottom-4 left-4 text-xs text-gray-400 font-mono">✕</div>
        </div>
        
        <SignatureCanvas
          ref={sigRef}
          canvasProps={{
            width: dimensions.width,
            height: dimensions.height,
            className: 'signature-canvas',
            style: { touchAction: 'none' }
          }}
          backgroundColor="transparent"
          penColor="#0a1628"
          minWidth={1.5}
          maxWidth={3}
          onEnd={handleEnd}
        />

        {/* Signature indicator */}
        {hasSignature && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="absolute top-3 right-3 w-8 h-8 rounded-full bg-zappix-accent/20 flex items-center justify-center"
          >
            <Check className="w-4 h-4 text-zappix-accent" />
          </motion.div>
        )}
      </div>

      <button
        type="button"
        onClick={handleClear}
        className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white/60 hover:text-white bg-white/5 hover:bg-white/10 rounded-lg transition-all duration-300"
      >
        <Eraser className="w-4 h-4" />
        {clearText}
      </button>
    </motion.div>
  );
}

