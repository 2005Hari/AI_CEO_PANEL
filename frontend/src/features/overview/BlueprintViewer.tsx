import React from 'react';

interface BlueprintViewerProps {
  blueprint: any;
}

export function BlueprintViewer({ blueprint }: BlueprintViewerProps) {
  
  const renderField = (label: string, value: any) => {
    if (!value) return null;
    
    if (typeof value === 'string') {
      return (
        <div className="mb-4">
          <h4 className="text-[10px] uppercase text-gray-500 font-semibold mb-1">{label}</h4>
          <p className="text-sm text-gray-300">{value}</p>
        </div>
      );
    }
    
    if (Array.isArray(value)) {
      if (value.length === 0) return null;
      return (
        <div className="mb-4">
          <h4 className="text-[10px] uppercase text-gray-500 font-semibold mb-1">{label}</h4>
          <ul className="list-disc list-inside text-sm text-gray-300 space-y-1">
            {value.map((item, idx) => (
              <li key={idx}>
                {typeof item === 'string' ? item : JSON.stringify(item)}
              </li>
            ))}
          </ul>
        </div>
      );
    }

    if (typeof value === 'object') {
      if (Object.keys(value).length === 0) return null;
      return (
        <div className="mb-4">
          <h4 className="text-[10px] uppercase text-gray-500 font-semibold mb-1">{label}</h4>
          <pre className="text-xs text-gray-300 bg-black/20 p-2 rounded-md overflow-x-auto">
            {JSON.stringify(value, null, 2)}
          </pre>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="glass rounded-xl border border-white/[0.04] overflow-hidden">
      <div className="bg-white/[0.02] border-b border-white/[0.04] px-5 py-3 flex items-center justify-between">
        <h2 className="font-semibold text-sm text-white">Company Blueprint</h2>
        <span className="text-xs text-gray-500">v{blueprint.version || 1}</span>
      </div>
      
      <div className="p-5 grid grid-cols-1 lg:grid-cols-2 gap-x-8 gap-y-2">
        <div>
          <h3 className="text-sm font-bold text-blue-400 mb-3 pb-1 border-b border-blue-400/20">Core Identity</h3>
          {renderField('Company Name', blueprint.company_name)}
          {renderField('Industry', blueprint.industry)}
          {renderField('Business Model', blueprint.business_model)}
          {renderField('Value Proposition', blueprint.value_proposition)}
          {renderField('Target Audience', blueprint.target_audience)}
        </div>
        
        <div>
          <h3 className="text-sm font-bold text-emerald-400 mb-3 pb-1 border-b border-emerald-400/20">Strategy & Operations</h3>
          {renderField('Growth Stage', blueprint.growth_stage)}
          {renderField('Team Size', blueprint.team_size)}
          {renderField('Tech Stack', blueprint.tech_stack)}
          {renderField('Current Goals', blueprint.current_goals)}
          {renderField('Current Problems', blueprint.current_problems)}
        </div>
      </div>
    </div>
  );
}
