import { staticData } from '../store/dataCache';

// 添加清理按钮组件
export function ClearCacheButton() {
  return (
    <button
      onClick={() => {
        staticData.clearAll();
        window.location.reload();
      }}
      className="fixed bottom-4 right-4 bg-red-500 text-white px-4 py-2 rounded-md"
    >
      Clear Cache
    </button>
  );
} 