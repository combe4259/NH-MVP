import React from 'react';
import { ChevronRight, Search, Settings, Home, X } from 'lucide-react';

interface MenuProps {
  onClose: () => void;
  onNavigateToConsulting: () => void;
}

const Menu: React.FC<MenuProps> = ({ onClose, onNavigateToConsulting }) => {
  const menuItems = [
    { category: '최근', items: [
      { name: '스마트상담센터', hasArrow: true },
      { name: '국민비서', hasArrow: true },
      { name: '문화/공연', hasArrow: true },
      { name: '가입자교육', hasArrow: true },
      { name: '더+모임', hasArrow: true },
      { name: 'NH올원모임', hasArrow: true }
    ]},
    { category: '조회', items: [
      { name: '전체계좌조회', hasArrow: false },
      { name: '송금내역', hasArrow: false }
    ]}
  ];

  const sideMenuItems = [
    '조회', '이체/출금', '가입상품관리', '상품가입', '외환', '퇴직연금', '공과금/세금', '내 자산', '금융편의', '포인트쌓기'
  ];

  return (
    <div className="max-w-sm mx-auto bg-white min-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-white border-b border-gray-100">
        <div className="flex items-center space-x-2">
          <h1 className="text-lg font-normal text-black">김민수님</h1>
          <ChevronRight className="w-4 h-4 text-gray-500" />
          <div className="bg-gray-100 px-3 py-1 rounded-full">
            <span className="text-xs text-gray-600">로그아웃</span>
          </div>
        </div>
        <div className="flex items-center space-x-4">
          <Settings className="w-5 h-5 text-gray-700" />
          <Home className="w-5 h-5 text-gray-700" />
          <X className="w-5 h-5 text-gray-700 cursor-pointer" onClick={onClose} />
        </div>
      </div>

      {/* Search Bar */}
      <div className="px-4 py-4 bg-gray-50">
        <div className="flex items-center bg-white rounded-lg px-3 py-3 border border-gray-200">
          <Search className="w-4 h-4 text-gray-400 mr-2" />
          <span className="text-sm text-gray-400">검색으로 더 많은 정보를 찾아보세요.</span>
        </div>
      </div>

      {/* Quick Menu Icons */}
      <div className="px-4 py-4 bg-white">
        <div className="grid grid-cols-4 gap-6">
          <div className="flex flex-col items-center space-y-2">
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
              <span className="text-green-600 text-lg">💳</span>
            </div>
            <span className="text-xs text-gray-700">NH지갑</span>
          </div>
          <div className="flex flex-col items-center space-y-2">
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
              <span className="text-purple-600 text-lg">✓</span>
            </div>
            <span className="text-xs text-gray-700">인증/보안</span>
          </div>
          <div className="flex flex-col items-center space-y-2">
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
              <span className="text-blue-600 text-lg">🎧</span>
            </div>
            <span className="text-xs text-gray-700">고객센터</span>
          </div>
          <div className="flex flex-col items-center space-y-2">
            <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center">
              <span className="text-yellow-600 text-lg">🎁</span>
            </div>
            <span className="text-xs text-gray-700">이벤트</span>
          </div>
        </div>
      </div>

      {/* Menu Content */}
      <div className="flex flex-1">
        {/* Left Side Menu */}
        <div className="w-32 bg-gray-50 min-h-full">
          {sideMenuItems.map((item, index) => (
            <div 
              key={item} 
              className={`px-4 py-4 text-sm border-b border-gray-200 ${
                index === 0 ? 'bg-green-600 text-white' : 'text-gray-700'
              }`}
            >
              {item}
            </div>
          ))}
        </div>

        {/* Right Content Area */}
        <div className="flex-1 bg-white">
          {/* Recent Usage Menu Header */}
          <div className="px-4 py-3 bg-green-50 border-l-4 border-green-600">
            <span className="text-sm font-medium text-green-800">최근 이용메뉴</span>
          </div>

          {/* Menu Items */}
          <div className="divide-y divide-gray-100">
            {menuItems[0].items.map((item, index) => (
              <div 
                key={index} 
                className="px-4 py-4 flex items-center justify-between hover:bg-gray-50 cursor-pointer"
                onClick={() => {
                  if (item.name === '스마트상담센터') {
                    onNavigateToConsulting();
                  }
                }}
              >
                <span className="text-sm text-gray-700">{item.name}</span>
                {item.hasArrow && <ChevronRight className="w-4 h-4 text-gray-400" />}
              </div>
            ))}
          </div>

          {/* Inquiry Section */}
          <div className="mt-6">
            <div className="px-4 py-3 bg-green-50 border-l-4 border-green-600">
              <span className="text-sm font-medium text-green-800">조회</span>
            </div>
            <div className="divide-y divide-gray-100">
              {menuItems[1].items.map((item, index) => (
                <div key={index} className="px-4 py-4 flex items-center justify-between hover:bg-gray-50">
                  <span className="text-sm text-gray-700">{item.name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Menu;