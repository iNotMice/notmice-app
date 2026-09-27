import React, { useState } from 'react';
import { X, Terminal as TerminalIcon, Play } from 'lucide-react';

interface TerminalModalProps {
  isOpen: boolean;
  onClose: () => void;
  accountAddress: string;
  phenoAge: number;
}

export const TerminalModal: React.FC<TerminalModalProps> = ({
  isOpen,
  onClose,
  accountAddress,
  phenoAge,
}) => {
  const [logs, setLogs] = useState<string[]>([
    `[SESSION] Public id ${accountAddress}.`,
    `[PHENOAGE] Research index (Levine 2018): ${phenoAge.toFixed(1)} years. Not a medical service.`,
    `[LOINC] Dictionary v1. PhenoAge uses 9 of 20 markers.`,
    `[FILES] Original PDFs are not stored. Confirmed values are saved after review.`,
  ]);
  const [inputCmd, setInputCmd] = useState('');

  if (!isOpen) return null;

  const handleCommand = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputCmd.trim()) return;

    const cmd = inputCmd.trim().toLowerCase();
    const newLogs = [...logs, `> ${inputCmd}`];

    if (cmd === 'help') {
      newLogs.push('Available commands: status, loinc, privacy, cite, clear');
    } else if (cmd === 'status') {
      newLogs.push(`Public id: ${accountAddress} | PhenoAge: ${phenoAge.toFixed(1)} years`);
    } else if (cmd === 'loinc') {
      newLogs.push('PhenoAge LOINC codes: 1751-7, 2160-0, 2345-7, 30522-7, 26474-7, 787-2, 788-0, 6768-6, 6690-2');
    } else if (cmd === 'privacy') {
      newLogs.push('Original lab files are not written to disk. Confirmed biomarker values are stored in Postgres. A profile appears in the public export only after opt-in.');
    } else if (cmd === 'cite') {
      newLogs.push('Levine ME et al. Aging (Albany NY) 2018; 10(4):573–591. DOI:10.18632/aging.101414');
    } else if (cmd === 'clear') {
      setLogs([]);
      setInputCmd('');
      return;
    } else {
      newLogs.push(`Command not recognized: "${inputCmd}". Type "help" for options.`);
    }

    setLogs(newLogs);
    setInputCmd('');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#0b1c30]/60 backdrop-blur-xs animate-in fade-in">
      <div className="bg-[#0b1c30] text-[#f8f9ff] rounded-xl border border-[#3f4850] shadow-2xl max-w-2xl w-full overflow-hidden flex flex-col font-['JetBrains_Mono']">
        {/* Terminal Header */}
        <div className="px-4 py-3 border-b border-[#213145] bg-[#131b2e] flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs">
            <span className="w-2.5 h-2.5 rounded-full bg-[#ef4444]"></span>
            <span className="w-2.5 h-2.5 rounded-full bg-[#f59e0b]"></span>
            <span className="w-2.5 h-2.5 rounded-full bg-[#10b981]"></span>
            <span className="text-[#bec6e0] ml-2 flex items-center gap-1.5 font-medium">
              <TerminalIcon className="w-3.5 h-3.5 text-[#4edea3]" />
              NotMice session log
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-[#bec6e0] hover:text-white hover:bg-[#213145] transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Terminal Output */}
        <div className="p-4 h-72 overflow-y-auto text-xs space-y-1 bg-[#0b1c30] text-[#eaf1ff]">
          {logs.map((log, index) => (
            <div
              key={index}
              className={`${
                log.startsWith('>')
                  ? 'text-[#4edea3] font-bold'
                  : log.includes('PHENOAGE') || log.includes('FILES')
                  ? 'text-[#93ccff]'
                  : 'text-[#bec6e0]'
              }`}
            >
              {log}
            </div>
          ))}
        </div>

        {/* Command Input Form */}
        <form
          onSubmit={handleCommand}
          className="border-t border-[#213145] p-2 bg-[#131b2e] flex items-center gap-2"
        >
          <span className="text-[#4edea3] text-sm pl-2">$</span>
          <input
            type="text"
            value={inputCmd}
            onChange={(e) => setInputCmd(e.target.value)}
            placeholder="Type 'help' or command..."
            className="flex-1 bg-transparent text-xs text-white focus:outline-none placeholder:text-[#565e74]"
          />
          <button
            type="submit"
            className="px-2.5 py-1 bg-[#006194] hover:bg-[#007bb9] text-white rounded text-xs flex items-center gap-1 cursor-pointer"
          >
            <Play className="w-3 h-3" />
            <span>Run</span>
          </button>
        </form>
      </div>
    </div>
  );
};
