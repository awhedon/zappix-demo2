'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import { motion } from 'framer-motion';
import { Shield, Heart, Activity, Send, Loader2 } from 'lucide-react';

import { FormField } from '@/components/FormField';
import { SignaturePad } from '@/components/SignaturePad';
import { SuccessAnimation } from '@/components/SuccessAnimation';
import { getFormData, submitForm, FormData } from '@/lib/api';
import { translations, Language } from '@/lib/utils';

export default function FormPage() {
  const router = useRouter();
  const { sessionId } = router.query;
  
  const [formData, setFormData] = useState<FormData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [signature, setSignature] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const lang = (formData?.language as Language) || 'en';
  const t = translations[lang];

  useEffect(() => {
    if (!sessionId || typeof sessionId !== 'string') return;

    const fetchData = async () => {
      try {
        const data = await getFormData(sessionId);
        setFormData(data);
      } catch (err) {
        setError('Unable to load form data. Please try again later.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [sessionId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!signature || !sessionId || typeof sessionId !== 'string') return;

    setIsSubmitting(true);
    try {
      await submitForm(sessionId, signature);
      setIsSubmitted(true);
    } catch (err) {
      setError('Failed to submit form. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen animated-gradient flex items-center justify-center">
        <div className="text-center">
          <div className="spinner mx-auto mb-4" />
          <p className="text-white/60">Loading your form...</p>
        </div>
      </div>
    );
  }

  if (error || !formData) {
    return (
      <div className="min-h-screen animated-gradient flex items-center justify-center">
        <div className="glass-card p-8 max-w-md text-center">
          <div className="w-16 h-16 rounded-full bg-zappix-coral/20 flex items-center justify-center mx-auto mb-4">
            <span className="text-3xl">⚠️</span>
          </div>
          <h2 className="text-2xl font-display font-bold text-white mb-2">{t.error}</h2>
          <p className="text-white/60">{error || 'Form not found'}</p>
        </div>
      </div>
    );
  }

  if (isSubmitted) {
    return (
      <>
        <Head>
          <title>{t.success} | Zappix + Aldea AI</title>
        </Head>
        <div className="min-h-screen animated-gradient relative overflow-hidden">
          <div className="absolute inset-0 grid-pattern opacity-50" />
          <div className="relative z-10 container mx-auto px-4 py-12">
            <div className="max-w-2xl mx-auto glass-card p-8 glow-accent">
              <SuccessAnimation title={t.success} message={t.successMessage} />
            </div>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <Head>
        <title>{t.title} | Zappix + Aldea AI</title>
        <meta name="description" content="Review and sign your health assessment form" />
      </Head>

      <main className="min-h-screen animated-gradient relative overflow-hidden">
        {/* Background effects */}
        <div className="absolute inset-0 grid-pattern opacity-50" />
        <div className="floating-shape w-96 h-96 bg-zappix-accent -top-48 -right-48" />
        <div className="floating-shape w-80 h-80 bg-zappix-purple -bottom-40 -left-40" style={{ animationDelay: '3s' }} />

        <div className="relative z-10 container mx-auto px-4 py-8 md:py-12">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-8"
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 mb-6">
              <Shield className="w-4 h-4 text-zappix-accent" />
              <span className="text-sm text-white/60">Secure Form</span>
            </div>
            <h1 className="text-3xl md:text-5xl font-display font-bold text-white mb-3">
              {t.title}
            </h1>
            <p className="text-lg text-white/50">{t.subtitle}</p>
          </motion.div>

          <div className="max-w-2xl mx-auto">
            <form onSubmit={handleSubmit}>
              {/* Introduction */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="glass-card p-6 mb-6"
              >
                <p className="text-white/70">{t.description}</p>
              </motion.div>

              {/* Personal Information */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="glass-card p-6 mb-6"
              >
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-zappix-accent to-teal-400 flex items-center justify-center">
                    <Shield className="w-5 h-5 text-white" />
                  </div>
                  <h2 className="text-xl font-display font-semibold text-white">
                    {t.personalInfo}
                  </h2>
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <FormField
                    label={t.name}
                    value={formData.first_name}
                    fallback={t.notProvided}
                    delay={0.1}
                  />
                  <FormField
                    label={t.dateOfBirth}
                    value={formData.date_of_birth}
                    fallback={t.notProvided}
                    delay={0.15}
                  />
                  <FormField
                    label={t.zipCode}
                    value={formData.zip_code}
                    fallback={t.notProvided}
                    delay={0.2}
                  />
                </div>
              </motion.div>

              {/* Health Responses */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="glass-card p-6 mb-6"
              >
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-zappix-purple to-violet-400 flex items-center justify-center">
                    <Heart className="w-5 h-5 text-white" />
                  </div>
                  <h2 className="text-xl font-display font-semibold text-white">
                    {t.healthResponses}
                  </h2>
                </div>

                <div className="space-y-4">
                  <FormField
                    label={t.generalHealth}
                    value={formData.general_health_display}
                    fallback={t.notProvided}
                    delay={0.3}
                  />
                  <FormField
                    label={t.moderateActivities}
                    value={formData.moderate_activities_display}
                    fallback={t.notProvided}
                    delay={0.35}
                  />
                  <FormField
                    label={t.climbingStairs}
                    value={formData.climbing_stairs_display}
                    fallback={t.notProvided}
                    delay={0.4}
                  />
                </div>
              </motion.div>

              {/* Signature */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="glass-card p-6 mb-8"
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-zappix-gold to-amber-400 flex items-center justify-center">
                    <Activity className="w-5 h-5 text-white" />
                  </div>
                  <h2 className="text-xl font-display font-semibold text-white">
                    {t.signature}
                  </h2>
                </div>
                <p className="text-white/50 text-sm mb-4">{t.signatureInstructions}</p>
                
                <SignaturePad
                  onSignature={setSignature}
                  clearText={t.clear}
                />
              </motion.div>

              {/* Submit Button */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
              >
                <button
                  type="submit"
                  disabled={!signature || isSubmitting}
                  className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                      {t.submitting}
                    </>
                  ) : (
                    <>
                      <Send className="w-5 h-5 mr-2" />
                      {t.submit}
                    </>
                  )}
                </button>
              </motion.div>
            </form>

            {/* Footer */}
            <motion.footer
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.7 }}
              className="text-center mt-12 pb-8"
            >
              <p className="text-white/30 text-sm">
                {t.poweredBy} <span className="text-zappix-accent">Zappix</span> + <span className="text-zappix-accent">Aldea AI</span>
              </p>
            </motion.footer>
          </div>
        </div>
      </main>
    </>
  );
}

