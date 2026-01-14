'use client';

import { useState } from 'react';
import Head from 'next/head';
import { motion } from 'framer-motion';
import { Phone, MessageSquare, FileCheck, Sparkles, ArrowRight, Globe } from 'lucide-react';
import { initiateOutboundCall } from '@/lib/api';

export default function Home() {
  const [firstName, setFirstName] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [language, setLanguage] = useState<'en' | 'es'>('en');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<{ success: boolean; message: string; sessionId?: string } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setResult(null);

    try {
      const response = await initiateOutboundCall({
        first_name: firstName,
        phone_number: phoneNumber,
        language,
      });
      setResult({
        success: response.success,
        message: response.message,
        sessionId: response.session_id,
      });
    } catch (error) {
      setResult({
        success: false,
        message: 'Failed to initiate call. Please try again.',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <Head>
        <title>Zappix + Aldea AI Demo | Health Assessment</title>
        <meta name="description" content="Conversational AI Health Assessment Demo" />
      </Head>

      <main className="min-h-screen animated-gradient relative overflow-hidden">
        {/* Background effects */}
        <div className="absolute inset-0 grid-pattern opacity-50" />
        <div className="floating-shape w-96 h-96 bg-zappix-accent -top-48 -left-48" />
        <div className="floating-shape w-80 h-80 bg-zappix-purple -bottom-40 -right-40" style={{ animationDelay: '2s' }} />
        <div className="floating-shape w-64 h-64 bg-zappix-gold top-1/2 left-1/2" style={{ animationDelay: '4s' }} />

        <div className="relative z-10 container mx-auto px-4 py-12 md:py-20">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-16"
          >
            <div className="flex items-center justify-center gap-3 mb-6">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-zappix-accent to-zappix-accent/70 flex items-center justify-center">
                <Sparkles className="w-6 h-6 text-zappix-navy" />
              </div>
              <span className="text-2xl font-display font-bold tracking-tight">
                <span className="text-white">Zappix</span>
                <span className="text-zappix-accent"> × </span>
                <span className="text-white">Aldea</span>
              </span>
            </div>
            <h1 className="text-4xl md:text-6xl font-display font-bold mb-4">
              <span className="gradient-text">Conversational AI</span>
              <br />
              <span className="text-white">Health Assessment</span>
            </h1>
            <p className="text-xl text-white/60 max-w-2xl mx-auto">
              Experience the seamless integration of voice AI and digital engagement
            </p>
          </motion.div>

          {/* Demo Flow */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="max-w-4xl mx-auto mb-16"
          >
            <div className="grid md:grid-cols-3 gap-6">
              {[
                {
                  icon: Phone,
                  title: 'AI Voice Call',
                  description: 'Aldea conducts the health assessment via natural conversation',
                  color: 'from-zappix-accent to-teal-400',
                },
                {
                  icon: MessageSquare,
                  title: 'SMS Link',
                  description: 'Receive a link to review and sign your responses',
                  color: 'from-zappix-purple to-violet-400',
                },
                {
                  icon: FileCheck,
                  title: 'Digital Signature',
                  description: 'Sign and submit your completed assessment form',
                  color: 'from-zappix-gold to-amber-400',
                },
              ].map((step, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 + i * 0.1 }}
                  className="glass-card p-6 text-center group hover:scale-105 transition-transform duration-300"
                >
                  <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${step.color} flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform`}>
                    <step.icon className="w-7 h-7 text-white" />
                  </div>
                  <h3 className="text-lg font-display font-semibold text-white mb-2">{step.title}</h3>
                  <p className="text-sm text-white/50">{step.description}</p>
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* Call Form */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="max-w-md mx-auto"
          >
            <div className="glass-card p-8 glow">
              <h2 className="text-2xl font-display font-bold text-white mb-6 text-center">
                Start Demo Call
              </h2>

              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label className="block text-sm font-medium text-zappix-accent mb-2">
                    First Name
                  </label>
                  <input
                    type="text"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    required
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/30 focus:outline-none focus:border-zappix-accent/50 focus:ring-2 focus:ring-zappix-accent/20 transition-all"
                    placeholder="Enter first name"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-zappix-accent mb-2">
                    Phone Number
                  </label>
                  <input
                    type="tel"
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value)}
                    required
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/30 focus:outline-none focus:border-zappix-accent/50 focus:ring-2 focus:ring-zappix-accent/20 transition-all"
                    placeholder="+1 (555) 123-4567"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-zappix-accent mb-2">
                    <Globe className="w-4 h-4 inline mr-1" />
                    Language
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    {[
                      { value: 'en', label: 'English' },
                      { value: 'es', label: 'Español' },
                    ].map((option) => (
                      <button
                        key={option.value}
                        type="button"
                        onClick={() => setLanguage(option.value as 'en' | 'es')}
                        className={`px-4 py-3 rounded-xl font-medium transition-all ${
                          language === option.value
                            ? 'bg-zappix-accent text-zappix-navy'
                            : 'bg-white/5 text-white/60 hover:bg-white/10 hover:text-white'
                        }`}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isLoading || !firstName || !phoneNumber}
                  className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? (
                    <div className="spinner" />
                  ) : (
                    <>
                      Initiate Call
                      <ArrowRight className="w-5 h-5 ml-2" />
                    </>
                  )}
                </button>
              </form>

              {result && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`mt-6 p-4 rounded-xl ${
                    result.success
                      ? 'bg-zappix-accent/20 border border-zappix-accent/30'
                      : 'bg-zappix-coral/20 border border-zappix-coral/30'
                  }`}
                >
                  <p className={`text-sm font-medium ${result.success ? 'text-zappix-accent' : 'text-zappix-coral'}`}>
                    {result.success ? '✓ Call initiated successfully!' : '✕ ' + result.message}
                  </p>
                  {result.sessionId && (
                    <p className="text-xs text-white/40 mt-2 font-mono">
                      Session: {result.sessionId.slice(0, 8)}...
                    </p>
                  )}
                </motion.div>
              )}
            </div>
          </motion.div>

          {/* Footer */}
          <motion.footer
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
            className="text-center mt-16 text-white/30 text-sm"
          >
            <p>Powered by LiveKit, Twilio, Deepgram, Cartesia & OpenAI</p>
            <p className="mt-2">© 2024 Zappix + Aldea AI Demo</p>
          </motion.footer>
        </div>
      </main>
    </>
  );
}

