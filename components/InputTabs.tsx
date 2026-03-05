interface Tab {
  id: string;
  label: string;
}

interface InputTabsProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
  disabled?: boolean;
}

export function InputTabs({ tabs, activeTab, onTabChange, disabled }: InputTabsProps) {
  return (
    <div className="flex gap-1 rounded-lg bg-surface p-1">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          disabled={disabled}
          className={`flex-1 rounded-md py-2 text-sm font-medium transition-all ${
            activeTab === tab.id
              ? 'bg-primary text-white shadow-sm'
              : 'text-text-secondary hover:text-text-primary'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
