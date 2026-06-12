import React, { useState, useEffect, useRef } from 'react';
import { Project, startDiscovery, respondDiscovery, getDiscoveryStatus, finalizeDiscovery } from '@/lib/api';

interface DiscoveryChatProps {
  project: Project;
  onComplete?: () => void;
}

export function DiscoveryChat({ project, onComplete }: DiscoveryChatProps) {
  const [messages, setMessages] = useState<{ role: 'assistant' | 'user'; content: string }[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [status, setStatus] = useState<any>(null);
  
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function init() {
      try {
        setLoading(true);
        const st = await getDiscoveryStatus(project.id);
        setStatus(st);
        
        const res = await startDiscovery(project.id);
        setMessages([{ role: 'assistant', content: res.questions }]);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    init();
  }, [project.id]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isProcessing) return;

    const userMsg = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setIsProcessing(true);

    try {
      const res = await respondDiscovery(project.id, userMsg, messages);
      setMessages(prev => [...prev, { role: 'assistant', content: res.message + '\n\n' + res.next_questions }]);
      
      const st = await getDiscoveryStatus(project.id);
      setStatus(st);
      
      if (res.status === 'complete') {
        // Optionally finalize
        await finalizeDiscovery(project.id);
        if (onComplete) onComplete();
      }
    } catch (e) {
      console.error(e);
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error processing that.' }]);
    } finally {
      setIsProcessing(false);
    }
  };

  if (loading) {
    return <div className="p-6 text-gray-500">Initializing Discovery...</div>;
  }

  const confidence = status ? Math.round(status.confidence * 100) : 0;

  return (
    <div className="h-full flex flex-col bg-[#050510] max-w-4xl mx-auto border-x border-white/[0.04]">
      {/* Header */}
      <div className="bg-[#08081a]/80 backdrop-blur-md px-6 py-4 border-b border-white/[0.04] flex items-center justify-between shrink-0">
        <div>
          <h2 className="text-lg font-bold text-white">Business Discovery</h2>
          <p className="text-xs text-gray-500">Let's build your Company Blueprint</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className="text-xs font-bold text-blue-400">{confidence}% Complete</span>
          <div className="w-32 h-1.5 bg-gray-800 rounded-full overflow-hidden">
            <div className="h-full bg-blue-500 rounded-full transition-all duration-500" style={{ width: `${confidence}%` }} />
          </div>
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-2xl p-4 text-sm leading-relaxed ${
              m.role === 'user' 
                ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/20 rounded-tr-none' 
                : 'glass border border-white/[0.04] text-gray-200 rounded-tl-none'
            }`}>
              <div dangerouslySetInnerHTML={{ __html: m.content.replace(/\n/g, '<br/>') }} />
            </div>
          </div>
        ))}
        {isProcessing && (
          <div className="flex justify-start">
            <div className="glass border border-white/[0.04] rounded-2xl rounded-tl-none px-4 py-3 text-sm">
              <span className="flex gap-1 items-center">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" />
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '0.1s' }} />
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '0.2s' }} />
              </span>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input */}
      <div className="p-4 bg-[#08081a]/80 backdrop-blur-md border-t border-white/[0.04]">
        <form onSubmit={handleSubmit} className="relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isProcessing || confidence >= 90}
            placeholder={confidence >= 90 ? "Discovery complete!" : "Answer here..."}
            className="w-full bg-black/40 border border-white/10 rounded-xl py-3 pl-4 pr-12 text-sm text-white focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-all disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || isProcessing || confidence >= 90}
            className="absolute right-2 top-2 bottom-2 aspect-square rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-gray-800 disabled:text-gray-500 text-white flex items-center justify-center transition-colors"
          >
            ↑
          </button>
        </form>
      </div>
    </div>
  );
}
