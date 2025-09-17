import React, { useState, useEffect } from 'react';
import { ChevronRight, Menu, Home, ArrowLeft, Search } from 'lucide-react';
import Overview from './Overview';
import { reportAPI, ConsultationSummary } from './api/backend';

interface ConsultationDetail {
  id: string;
  title: string;
  location: string;
  date: string;
  category: string;
  expectedAmount?: string;
  possibleAmount?: string;
  maturityDate?: string;
  nextAction: string;
  status: 'active' | 'completed';
  statusText: string;
}

interface ConsultingProps {
  onBack: () => void;
}

const Consulting: React.FC<ConsultingProps> = ({ onBack }) => {
  const [selectedConsultation, setSelectedConsultation] = useState<string | null>(null);
  const [consultationDetails, setConsultationDetails] = useState<ConsultationDetail[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  // 백엔드에서 상담 데이터 불러오기
  useEffect(() => {
    const fetchConsultations = async () => {
      try {
        setIsLoading(true);
        const response = await reportAPI.getCompletedConsultations(10);

        // 백엔드 데이터를 UI 형식으로 변환
        const formattedConsultations: ConsultationDetail[] = response.consultations.map((consultation, index) => ({
          id: consultation.consultation_id,
          title: `${consultation.product_type} 상담`,
          location: 'NH 디지털 상담',
          date: new Date(consultation.start_time).toLocaleDateString('ko-KR').replace(/\./g, '.').replace(/ /g, ''),
          category: '상담 완료',
          expectedAmount: consultation.status === 'completed' ? '상담 완료' : '진행 중',
          nextAction: consultation.status === 'completed' ? '' : '다음 할 일: 추가 서류 준비',
          status: consultation.status === 'completed' ? 'completed' : 'active',
          statusText: consultation.status === 'completed' ? '완료' : '액션필요'
        }));

        setConsultationDetails(formattedConsultations);
      } catch (error) {
        console.error('상담 목록 조회 실패:', error);
        setError('상담 목록을 불러올 수 없습니다.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchConsultations();
  }, []);

  // 자연어 검색 처리
  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      return;
    }

    try {
      setIsSearching(true);
      setError(null);
      
      // 백엔드 API 호출 (자연어 -> SQL 변환 후 검색)
      const response = await reportAPI.searchConsultationsWithNL(searchQuery);
      
      // 검색 결과를 UI 형식으로 변환
      const formattedResults: ConsultationDetail[] = response.consultations.map((consultation: any) => ({
        id: consultation.consultation_id,
        title: `${consultation.product_type} 상담`,
        location: 'NH 디지털 상담',
        date: new Date(consultation.start_time).toLocaleDateString('ko-KR').replace(/\./g, '.').replace(/ /g, ''),
        category: '상담 완료',
        expectedAmount: consultation.status === 'completed' ? '상담 완료' : '진행 중',
        nextAction: consultation.status === 'completed' ? '' : '다음 할 일: 추가 서류 준비',
        status: consultation.status === 'completed' ? 'completed' : 'active',
        statusText: consultation.status === 'completed' ? '완료' : '액션필요'
      }));

      setConsultationDetails(formattedResults);
      
      if (formattedResults.length === 0) {
        setError('검색 결과가 없습니다. 다른 검색어로 시도해보세요.');
      }
    } catch (error) {
      console.error('자연어 검색 실패:', error);
      setError('검색 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
    } finally {
      setIsSearching(false);
    }
  };

  if (selectedConsultation) {
    return (
      <Overview
        consultationId={selectedConsultation}
        onBack={() => setSelectedConsultation(null)}
      />
    );
  }

  if (isLoading) {
    return (
      <div className="max-w-sm mx-auto bg-gray-50 min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">상담 내역을 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-sm mx-auto bg-gray-50 min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={onBack}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg"
          >
            돌아가기
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-sm mx-auto bg-gray-50 min-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-4 bg-white">
        <ArrowLeft 
          className="w-6 h-6 text-gray-700 cursor-pointer" 
          onClick={onBack}
        />
        <h1 className="text-lg font-medium text-black">스마트상담센터</h1>
        <div className="flex items-center space-x-4">
          <Home className="w-6 h-6 text-gray-700" />
          <Menu className="w-6 h-6 text-gray-700" />
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="px-4 py-4 bg-white">
        <div className="bg-gray-200 rounded-full p-1 flex">
          <button className="flex-1 py-2 text-sm font-medium text-white bg-gray-500 rounded-full">
            상담예약
          </button>
          <button className="flex-1 py-2 text-sm font-medium text-gray-600">
            내역조회
          </button>
          <button className="flex-1 py-2 text-sm font-medium text-gray-600">
            카드조회
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="px-4 pb-4 overflow-y-auto scrollbar-hide" style={{ height: 'calc(100vh - 140px)' }}>
        <h2 className="text-lg font-medium text-black mb-4">상담 내역</h2>
        
        {/* Search Bar */}
        <div className="mb-4">
          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  handleSearch();
                }
              }}
              placeholder="예: 지난달 정기예금 상담 내역 보여줘"
              className="w-full pl-10 pr-4 py-3 bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <Search className="absolute left-3 top-3.5 w-5 h-5 text-gray-400" />
            <button
              onClick={handleSearch}
              disabled={isSearching}
              className="absolute right-2 top-2 px-3 py-1.5 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:bg-gray-400"
            >
              {isSearching ? '검색중...' : '검색'}
            </button>
          </div>
          <p className="mt-1 text-xs text-gray-500">
            자연어로 검색하세요. AI가 적절한 상담 내역을 찾아드립니다.
          </p>
        </div>

        {/* Consultation Items */}
        <div className="space-y-4">
          {consultationDetails.map((consultation, index) => (
            <div 
              key={consultation.id} 
              className="bg-white rounded-lg p-4 relative cursor-pointer hover:bg-gray-50"
              onClick={() => setSelectedConsultation(consultation.id)}
            >
              {index === 0 && (
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-red-500 rounded-l-lg"></div>
              )}
              
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-black rounded-full flex items-center justify-center">
                    <span className="text-white text-lg">🍎</span>
                  </div>
                  <div>
                    <h3 className="text-base font-medium text-black">{consultation.title}</h3>
                    <p className="text-xs text-gray-500">{consultation.location} • {consultation.date}</p>
                  </div>
                </div>
                <ChevronRight className="w-5 h-5 text-gray-400" />
              </div>

              {index === 0 && (
                <div className="mb-3">
                  <span className="inline-block bg-orange-500 text-white text-xs px-2 py-1 rounded">
                    중요 확인사항 2
                  </span>
                </div>
              )}

              <div className="mb-3">
                <p className="text-sm text-gray-600 mb-1">{consultation.category}</p>
                <p className="text-xl font-bold text-blue-600">
                  {consultation.expectedAmount || consultation.possibleAmount}
                </p>
              </div>

              {consultation.maturityDate && (
                <div className="mb-3">
                  <p className="text-sm text-gray-600">{consultation.maturityDate}</p>
                </div>
              )}

              <div className="flex items-center justify-between">
                <p className="text-sm text-gray-600">{consultation.nextAction}</p>
                <div className="flex items-center">
                  <div className={`w-2 h-2 rounded-full mr-2 ${
                    consultation.status === 'active' ? 'bg-red-500' : 'bg-green-500'
                  }`}></div>
                  <span className={`text-xs ${
                    consultation.status === 'active' ? 'text-red-500' : 'text-green-500'
                  }`}>
                    {consultation.statusText}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Consulting;