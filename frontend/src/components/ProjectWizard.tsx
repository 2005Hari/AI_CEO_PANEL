// frontend/src/components/ProjectWizard.tsx
"use client";

import React, { useState } from 'react';
import { createProject, Project } from '@/lib/api';

interface ProjectWizardProps {
  onSuccess: (project: Project) => void;
}

export const ProjectWizard: React.FC<ProjectWizardProps> = ({ onSuccess }) => {
  const [step, setStep] = useState(1);
  const [name, setName] = useState('');
  const [valueProp, setValueProp] = useState('');
  const [targetAudience, setTargetAudience] = useState('');
  const [techStack, setTechStack] = useState('');
  const [businessModel, setBusinessModel] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const nextStep = () => setStep(prev => Math.min(prev + 1, 4));
  const prevStep = () => setStep(prev => Math.max(prev - 1, 1));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Company name is required.');
      setStep(1);
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      const coreContext = {
        company_name: name,
        value_proposition: valueProp,
        target_audience: targetAudience,
        tech_stack: techStack,
        business_model: businessModel
      };

      const project = await createProject(name, coreContext);
      onSuccess(project);
    } catch (err: any) {
      setError(err.message || 'Failed to create project. Please try again.');
      setIsSubmitting(false);
    }
  };

  const stepsTotal = 4;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
      <div className="w-full max-w-xl bg-gray-950 border border-gray-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Progress Bar */}
        <div className="w-full bg-gray-900 h-1.5 flex">
          {Array.from({ length: stepsTotal }).map((_, idx) => (
            <div
              key={idx}
              className={`flex-1 h-full transition-all duration-300 ${
                idx + 1 <= step ? 'bg-gradient-to-r from-blue-500 to-emerald-500' : 'bg-transparent'
              }`}
            />
          ))}
        </div>

        <div className="p-8 flex-1 flex flex-col gap-6">
          {/* Header */}
          <div className="text-center">
            <span className="text-xs font-semibold uppercase tracking-wider text-blue-500">
              Step {step} of {stepsTotal}
            </span>
            <h2 className="text-2xl font-bold mt-1 text-white">Configure Your Startup Boardroom</h2>
            <p className="text-sm text-gray-400 mt-2">
              Tell your AI executive panel about your business to get tailored advice.
            </p>
          </div>

          {error && (
            <div className="bg-red-900/30 border border-red-500/50 rounded-lg p-3 text-sm text-red-300">
              {error}
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="flex-1 flex flex-col gap-6">
            {step === 1 && (
              <div className="space-y-4 animate-fadeIn">
                <label className="block text-sm font-medium text-gray-300">
                  What is your Company or Project Name? *
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="e.g. Acme Corp, SaaSify"
                  className="w-full bg-gray-900 border border-gray-800 rounded-lg px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                />
              </div>
            )}

            {step === 2 && (
              <div className="space-y-4 animate-fadeIn">
                <label className="block text-sm font-medium text-gray-300">
                  What is your Value Proposition? (Product Description)
                </label>
                <textarea
                  value={valueProp}
                  onChange={e => setValueProp(e.target.value)}
                  placeholder="e.g. We build a developer-first analytics platform that tracks SQL query performance in real-time, solving high latency issues automatically."
                  rows={4}
                  className="w-full bg-gray-900 border border-gray-800 rounded-lg px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none"
                />
              </div>
            )}

            {step === 3 && (
              <div className="space-y-4 animate-fadeIn">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Who is your Target Audience / Customer Persona?
                  </label>
                  <input
                    type="text"
                    value={targetAudience}
                    onChange={e => setTargetAudience(e.target.value)}
                    placeholder="e.g. CTOs, VP of Engineering, Database Administrators at mid-market tech startups"
                    className="w-full bg-gray-900 border border-gray-800 rounded-lg px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    What is your Technology Stack?
                  </label>
                  <input
                    type="text"
                    value={techStack}
                    onChange={e => setTechStack(e.target.value)}
                    placeholder="e.g. Next.js, FastAPI, PostgreSQL, AWS RDS, Datadog"
                    className="w-full bg-gray-900 border border-gray-800 rounded-lg px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                  />
                </div>
              </div>
            )}

            {step === 4 && (
              <div className="space-y-4 animate-fadeIn">
                <label className="block text-sm font-medium text-gray-300">
                  What is your Business / Monetization Model?
                </label>
                <textarea
                  value={businessModel}
                  onChange={e => setBusinessModel(e.target.value)}
                  placeholder="e.g. SaaS subscription with tiered pricing. Developer plan starts at $29/mo; Enterprise plan starts at $499/mo with dedicated support and unlimited query history."
                  rows={4}
                  className="w-full bg-gray-900 border border-gray-800 rounded-lg px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none"
                />
              </div>
            )}

            {/* Navigation Buttons */}
            <div className="mt-8 flex justify-between gap-4">
              {step > 1 ? (
                <button
                  type="button"
                  onClick={prevStep}
                  className="px-6 py-2.5 bg-gray-900 hover:bg-gray-800 text-gray-300 font-medium rounded-lg transition-colors border border-gray-800"
                >
                  Back
                </button>
              ) : (
                <div />
              )}

              {step < stepsTotal ? (
                <button
                  type="button"
                  disabled={step === 1 && !name.trim()}
                  onClick={nextStep}
                  className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-all hover:shadow-[0_0_15px_rgba(37,99,235,0.4)] disabled:opacity-50 disabled:hover:shadow-none"
                >
                  Next
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={isSubmitting || !name.trim()}
                  className="px-8 py-2.5 bg-gradient-to-r from-blue-600 to-emerald-600 hover:from-blue-500 hover:to-emerald-500 text-white font-medium rounded-lg transition-all hover:shadow-[0_0_20px_rgba(16,185,129,0.3)] disabled:opacity-50"
                >
                  {isSubmitting ? 'Creating Room...' : 'Assemble Panel'}
                </button>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
