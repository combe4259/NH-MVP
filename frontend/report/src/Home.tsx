import React, { useState, useEffect } from 'react';
import { ChevronRight, Bell, Menu as MenuIcon, MoreVertical } from 'lucide-react';
import Menu from './Menu';
import Consulting from './Consulting';
import Overview from './Overview';
import { reportAPI, ConsultationSummary } from './api/backend';

interface ConsultationRecord {
  id: string;
  type: string;
  title: string;
  date: string;
  location?: string;
  nextAction?: string;
}

const Home: React.FC = () => {
  const [scrollPosition, setScrollPosition] = useState(0);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [showConsultationCenter, setShowConsultationCenter] = useState(false);
  const [selectedConsultationId, setSelectedConsultationId] = useState<string | null>(null);

  const [consultations, setConsultations] = useState<ConsultationRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [backendConnected, setBackendConnected] = useState(false);

  // 백엔드에서 상담 데이터 불러오기
  useEffect(() => {
    const fetchConsultations = async () => {
      try {
        setIsLoading(true);

        // 백엔드 연결 확인
        await reportAPI.healthCheck();
        setBackendConnected(true);

        // 완료된 상담 목록 가져오기
        const response = await reportAPI.getCompletedConsultations(10);

        // 백엔드 데이터를 UI 형식으로 변환
        const formattedConsultations: ConsultationRecord[] = response.consultations.map((consultation, index) => ({
          id: consultation.consultation_id,
          type: getProductIcon(consultation.product_type),
          title: `${consultation.product_type} 상담`,
          date: new Date(consultation.start_time).toLocaleDateString('ko-KR').replace(/\./g, '.').replace(/ /g, ''),
          location: 'NH 디지털 상담',
          nextAction: consultation.status === 'completed' ? '상담 완료' : '진행 중'
        }));

        setConsultations(formattedConsultations);

      } catch (error) {
        console.error('백엔드 연결 실패:', error);
        setBackendConnected(false);

        // 백엔드 연결 실패시 더미 데이터 사용
        setConsultations([
          {
            id: 'demo-1',
            type: '🏦',
            title: '정기예금 상담 (데모)',
            date: '2024.09.14',
            location: 'NH 디지털 상담',
            nextAction: '백엔드 연결 중...'
          }
        ]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchConsultations();
  }, []);

  // 상품 타입에 따른 아이콘 반환
  const getProductIcon = (productType: string): string => {
    switch (productType.toLowerCase()) {
      case '정기예금':
      case 'deposit':
        return '🏦';
      case '펀드':
      case 'fund':
        return '📈';
      case '대출':
      case 'loan':
        return '💼';
      default:
        return '📄';
    }
  };

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    setScrollPosition(e.currentTarget.scrollTop);
  };

  if (selectedConsultationId) {
    return (
      <Overview 
        consultationId={selectedConsultationId}
        onBack={() => setSelectedConsultationId(null)}
      />
    );
  }

  if (showConsultationCenter) {
    return <Consulting onBack={() => setShowConsultationCenter(false)} />;
  }

  if (isMenuOpen) {
    return (
      <Menu 
        onClose={() => setIsMenuOpen(false)} 
        onNavigateToConsulting={() => {
          setIsMenuOpen(false);
          setShowConsultationCenter(true);
        }}
      />
    );
  }

  return (
    <div className="max-w-sm mx-auto bg-gray-50 min-h-screen relative">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-50">
        <div className="flex items-center space-x-1">
          <h1 className="text-lg font-normal text-black">김수연님</h1>
          <ChevronRight className="w-4 h-4 text-gray-500" />
        </div>
        <div className="flex items-center space-x-4">
          <div className="w-8 h-8 bg-white rounded-full flex items-center justify-center">
            <span className="text-sm">🔔</span>
          </div>
          <Bell className="w-5 h-5 text-gray-700" />
          <MenuIcon 
            className="w-5 h-5 text-gray-700 cursor-pointer" 
            onClick={() => setIsMenuOpen(true)}
          />
        </div>
      </div>

      {/* Scrollable Content */}
      <div className="overflow-y-auto pb-20 scrollbar-hide" style={{ height: 'calc(100vh - 80px)' }} onScroll={handleScroll}>
        
        {/* My Account Section */}
        <div className="px-4 mb-4">
          <div className="bg-white rounded-lg">
            <div className="px-4 py-3 border-b border-gray-100">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-medium text-black">내 계좌</h2>
                <div className="flex items-center space-x-2 text-xs text-gray-500">
                  <span>계좌통틀관리</span>
                  <span>|</span>
                  <span>전체계좌조회</span>
                </div>
              </div>
            </div>
            
            <div className="px-4 py-4">
              <div className="bg-gray-100 rounded px-2 py-1 inline-block mb-3">
                <span className="text-xs text-gray-600">한도제한계좌</span>
              </div>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center">
                    <span className="text-white text-sm font-bold">NH</span>
                  </div>
                  <div>
                    <div className="text-sm text-black">NH1934우대통장(비대면실명...</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xl font-semibold text-black">0 원</div>
                </div>
              </div>
              <div className="flex justify-center space-x-3">
                <button className="px-4 py-2 text-sm border border-gray-300 rounded-full text-gray-700 bg-white">
                  한도제한해제
                </button>
                <button className="px-4 py-2 text-sm border border-gray-300 rounded-full text-gray-700 bg-white">
                  보내기
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Consultation Section */}
        <div className="px-4 mb-4">
          <div className="bg-white rounded-lg">
            <div className="px-4 py-3 border-b border-gray-100">
              <h2 className="text-base font-medium text-black">최근 상담 내역</h2>
            </div>
            
            <div className="divide-y divide-gray-100">
              {consultations.map((consultation) => (
                <div 
                  key={consultation.id} 
                  className="px-4 py-4 cursor-pointer hover:bg-gray-50"
                  onClick={() => setSelectedConsultationId(consultation.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-3 flex-1">
                      <div className="w-10 h-10 bg-black rounded-full flex items-center justify-center flex-shrink-0">
                        <span className="text-white text-lg">{consultation.type}</span>
                      </div>
                      <div className="flex-1">
                        <div className="text-sm text-black font-medium mb-1">
                          {consultation.title}
                        </div>
                        <div className="text-xs text-red-500 mb-1">
                          📍 {consultation.location}
                        </div>
                        <div className="flex items-center text-xs text-gray-500 mb-2">
                          <span>📅</span>
                          <span className="ml-1">{consultation.date}</span>
                        </div>
                        {consultation.nextAction && (
                          <div className="text-xs text-black flex items-center">
                            <span className="mr-2">📄</span>
                            {consultation.nextAction}
                            <ChevronRight className="w-3 h-3 text-gray-400 ml-auto" />
                          </div>
                        )}
                      </div>
                    </div>
                    <MoreVertical className="w-4 h-4 text-gray-400 mt-1" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* My Groups Section */}
        <div className="px-4 mb-4">
          <div className="bg-white rounded-lg">
            <div className="px-4 py-3 border-b border-gray-100">
              <h2 className="text-base font-medium text-black">내 모임</h2>
            </div>
            
            <div className="px-4 py-6">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-black mb-1">
                    함께하는 순간이 더 쉽고 즐거워지는
                  </div>
                  <div className="text-lg font-bold text-black">
                    NH올원모임서비스
                  </div>
                </div>
                <div className="flex -space-x-2">
                  <div className="w-8 h-8 rounded-full bg-blue-100 border-2 border-white flex items-center justify-center">
                    <span className="text-xs">👤</span>
                  </div>
                  <div className="w-8 h-8 rounded-full bg-green-100 border-2 border-white flex items-center justify-center">
                    <span className="text-xs">👤</span>
                  </div>
                  <div className="w-8 h-8 rounded-full bg-purple-100 border-2 border-white flex items-center justify-center">
                    <span className="text-xs">👤</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Expenses Section */}
        <div className="px-4 mb-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-base font-medium text-black">지출</h2>
            <div className="text-xs text-gray-500">자산정보 기준일: 2025.09.07</div>
          </div>
          
          <div className="space-y-4">
            <div className="bg-white rounded-lg px-4 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-red-100 rounded-lg flex items-center justify-center">
                    <span className="text-red-500">💳</span>
                  </div>
                  <span className="text-base font-medium text-black">소비</span>
                </div>
                <div className="text-right">
                  <div className="text-xs text-gray-500">이번 달</div>
                  <div className="text-lg font-semibold text-black">355,932 원</div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg px-4 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                    <span className="text-blue-500">💳</span>
                  </div>
                  <span className="text-base font-medium text-black">카드</span>
                </div>
                <div className="text-right">
                  <div className="text-xs text-gray-500">결제 예정 금액</div>
                  <div className="text-lg font-semibold text-black">0 원</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Financial Assets Section */}
        <div className="px-4 mb-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-base font-medium text-black">금융자산</h2>
            <div className="text-xs text-gray-500">자산정보 기준일: 2025.09.07</div>
          </div>
          
          <div className="space-y-4">
            <div className="bg-white rounded-lg px-4 py-6">
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-8 h-8 bg-red-100 rounded-lg flex items-center justify-center">
                  <span className="text-red-500">📊</span>
                </div>
                <span className="text-base font-medium text-black">대출</span>
              </div>
              <div className="text-center">
                <div className="text-lg font-medium text-black mb-2">내 대출 한번에 관리해볼까?</div>
                <div className="flex items-center justify-center text-blue-600 text-sm">
                  <span>모든 금융기관 대출보기</span>
                  <ChevronRight className="w-4 h-4 ml-1" />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg px-4 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                    <span className="text-blue-500">📈</span>
                  </div>
                  <span className="text-base font-medium text-black">투자</span>
                </div>
                <div className="text-right">
                  <div className="text-xs text-gray-500">평가금액</div>
                  <div className="text-lg font-semibold text-black">0 원</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Insurance Section */}
        <div className="px-4 mb-4">
          <div className="bg-white rounded-lg px-4 py-6">
            <div className="flex items-center space-x-3 mb-4">
              <div className="w-8 h-8 bg-yellow-100 rounded-lg flex items-center justify-center">
                <span className="text-yellow-600">☂️</span>
              </div>
              <span className="text-base font-medium text-black">보험</span>
            </div>
            <div className="text-center">
              <div className="text-lg font-medium text-black mb-2">내 보험 괜찮은지 점검해볼까?</div>
              <div className="flex items-center justify-center text-blue-600 text-sm">
                <span>보장 분석하기</span>
                <ChevronRight className="w-4 h-4 ml-1" />
              </div>
            </div>
          </div>
        </div>

        {/* Lifestyle Services Section */}
        <div className="px-4 mb-4">
          <h2 className="text-base font-medium text-black mb-3">생활자산</h2>
          
          <div className="space-y-4">
            <div className="bg-white rounded-lg px-4 py-4">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                  <span className="text-blue-500">🏠</span>
                </div>
                <div>
                  <div className="text-base font-medium text-black">부동산</div>
                  <div className="text-sm text-gray-600 mt-1">내 부동산 등록하고 최근 시세 확인하기</div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg px-4 py-4">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                  <span className="text-blue-500">🚗</span>
                </div>
                <div>
                  <div className="text-base font-medium text-black">모빌리티</div>
                  <div className="text-sm text-gray-600 mt-1">내게 딱 맞는 자동차 추천을 받아보세요</div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg px-4 py-4">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-red-100 rounded-lg flex items-center justify-center">
                  <span className="text-red-500">❤️</span>
                </div>
                <div>
                  <div className="text-base font-medium text-black">헬스케어</div>
                  <div className="text-sm text-gray-600 mt-1">최근에 건강검진을 받은 적이 있나요?</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Additional Services */}
        <div className="px-4 mb-8">
          <div className="bg-white rounded-lg px-4 py-6">
            <h3 className="text-lg font-medium text-black mb-4">이런 서비스도 있어요</h3>
          </div>
        </div>
      </div>

      {/* Bottom Navigation */}
      <div className="fixed bottom-0 left-1/2 transform -translate-x-1/2 max-w-sm w-full bg-white border-t border-gray-100">
        <div className="flex items-center justify-around py-2">
          <div className="flex flex-col items-center space-y-1 py-2">
            <div className="w-6 h-6 bg-black rounded flex items-center justify-center">
              <span className="text-white text-xs">🏠</span>
            </div>
            <span className="text-xs text-black font-medium">홈</span>
          </div>
          <div className="flex flex-col items-center space-y-1 py-2">
            <div className="w-6 h-6 bg-gray-100 rounded flex items-center justify-center">
              <span className="text-gray-600 text-xs">🛍️</span>
            </div>
            <span className="text-xs text-gray-500">상품몰</span>
          </div>
          <div className="flex flex-col items-center space-y-1 py-2">
            <div className="w-6 h-6 bg-gray-100 rounded flex items-center justify-center">
              <span className="text-gray-600 text-xs">📊</span>
            </div>
            <span className="text-xs text-gray-500">내 자산</span>
          </div>
          <div className="flex flex-col items-center space-y-1 py-2">
            <div className="w-6 h-6 bg-gray-100 rounded flex items-center justify-center">
              <span className="text-gray-600 text-xs">💰</span>
            </div>
            <span className="text-xs text-gray-500">포인트쌓기</span>
          </div>
          <div className="flex flex-col items-center space-y-1 py-2">
            <div className="w-6 h-6 bg-gray-100 rounded flex items-center justify-center">
              <span className="text-gray-600 text-xs">🎁</span>
            </div>
            <span className="text-xs text-gray-500">생활혜택</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Home;