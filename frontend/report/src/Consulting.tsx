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
  const [originalConsultations, setOriginalConsultations] = useState<ConsultationDetail[]>([]); // 원본 목록 저장
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [isSearchResult, setIsSearchResult] = useState(false); // 검색 결과 여부 상태

  const fetchInitialConsultations = async () => {
    try {
      setIsLoading(true);
      const response = await reportAPI.getCompletedConsultations(10);
      const nhBranches = ['NH금융PLUS 영업부금융센터', '잠실금융센터', 'Premier Blue 삼성동센터', 'NH금융PLUS 광화문금융센터'];

      const formatted = response.consultations.map((consultation: ConsultationSummary, index): ConsultationDetail => {
        const productName = consultation.product_details?.name || consultation.product_type;
        let category = '상담 완료';
        if (consultation.status !== 'completed') {
          category = '진행중';
        } else if (productName === 'N2 ELS 제44회 파생결합증권') {
          category = '가입 완료';
        } else if (productName.includes('적금')) {
          category = '만기';
        }

        return {
          id: consultation.consultation_id,
          title: productName,
          location: nhBranches[index % nhBranches.length],
          date: new Date(consultation.start_time).toLocaleDateString('ko-KR').replace(/\./g, '.').replace(/ /g, ''),
          category: category,
          nextAction: '',
          status: consultation.status,
          statusText: consultation.status === 'completed' ? '완료' : '진행중'
        };
      });

      setConsultationDetails(formatted);
      setOriginalConsultations(formatted); // 원본 데이터 저장
      setIsSearchResult(false); // 초기 로드는 검색 결과가 아님
    } catch (err) {
      console.error('상담 목록 조회 실패:', err);
      setError('상담 목록을 불러올 수 없습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchInitialConsultations();
  }, []);

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setConsultationDetails(originalConsultations); // 검색어가 없으면 원본 목록으로 복원
      setIsSearchResult(false);
      return;
    }

    try {
      setIsSearching(true);
      setError(null);
      const response = await reportAPI.searchConsultationsWithNL(searchQuery);
      const nhBranches = ['NH금융PLUS 영업부금융센터', '잠실금융센터', 'Premier Blue 삼성동센터', 'NH금융PLUS 광화문금융센터'];

      const formattedResults = response.consultations.map((consultation: ConsultationSummary, index: number): ConsultationDetail => {
        const productName = consultation.product_details?.name || consultation.product_type;
        let category = '가입 완료';
        if (productName === 'N2 ELS 제44회 파생결합증권') {
          category = '가입 완료';
        } else {
          category = '상담 완료';
        }

        return {
          id: consultation.consultation_id,
          title: productName,
          location: nhBranches[index % nhBranches.length],
          date: new Date(consultation.start_time).toLocaleDateString('ko-KR').replace(/\./g, '.').replace(/ /g, ''),
          category: category,
          nextAction: '',
          status: consultation.status,
          statusText: consultation.status === 'completed' ? '완료' : '진행중'
        };
      });

      setConsultationDetails(formattedResults);
      setIsSearchResult(true); // 검색 결과임을 표시

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
    return <Overview consultationId={selectedConsultation} onBack={() => setSelectedConsultation(null)} />;
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

  return (
    <div className="max-w-sm mx-auto bg-gray-50 min-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-4 bg-white">
        <ArrowLeft className="w-6 h-6 text-gray-700 cursor-pointer" onClick={onBack} />
        <h1 className="text-lg font-medium text-black">스마트상담센터</h1>
        <div className="flex items-center space-x-4">
          <Home className="w-6 h-6 text-gray-700" />
          <Menu className="w-6 h-6 text-gray-700" />
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="px-4 py-4 bg-white">
        <div className="bg-gray-200 rounded-full p-1 flex">
          <button className="flex-1 py-2 text-sm font-medium text-gray-600">상담예약</button>
          <button className="flex-1 py-2 text-sm font-medium text-white bg-gray-500 rounded-full">내역조회</button>
          <button className="flex-1 py-2 text-sm font-medium text-gray-600">카드조회</button>
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
              onKeyPress={(e) => { if (e.key === 'Enter') { handleSearch(); } }}
              placeholder="예: 최근에 가입한 ELS 상품 보여줘"
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
          <p className="mt-1 text-xs text-gray-500">자연어로 검색하세요. AI가 적절한 상담 내역을 찾아드립니다.</p>
        </div>

        {error && <p className="text-center text-red-500 text-sm mb-4">{error}</p>}

        {/* Consultation Items */}
        <div className="space-y-4">
          {consultationDetails.map((consultation) => (
            <div 
              key={consultation.id} 
              className="bg-white rounded-lg p-4 relative cursor-pointer hover:bg-gray-50"
              onClick={() => setSelectedConsultation(consultation.id)}
            >
              {isSearchResult && (
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-green-600 rounded-l-lg"></div>
              )}
              
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-green-600 rounded-full flex items-center justify-center">
                    <span className="text-white text-sm font-bold">NH</span>
                  </div>
                  <div>
                    <h3 className="text-base font-medium text-black">{consultation.title}</h3>
                    <div className="flex items-center text-xs text-gray-500">
                      <span>{consultation.location} • {consultation.date}</span>
                    </div>
                    <div className="mt-1">
                      <span className={`inline-block px-2 py-0.5 text-xs rounded ${
                        consultation.category === '가입 완료'
                          ? 'bg-green-100 text-green-800 font-semibold'
                          : 'bg-gray-100 text-gray-700'
                      }`}>
                        {consultation.category}
                      </span>
                    </div>
                  </div>
                </div>
                <ChevronRight className="w-5 h-5 text-gray-400" />
              </div>

              <div className="mb-3">
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
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Consulting;