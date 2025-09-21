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

        // NH 영업점 이름 목록
        const nhBranches = ['NH농협은행 종로금융센터', 'NH농협은행 동대문지점', 'NH농협은행 평화지점'];
        
        // 각각 다른 날짜 생성 (최근 30일 내)
        const generateDate = (index: number) => {
          const date = new Date();
          date.setDate(date.getDate() - (index * 3 + Math.floor(Math.random() * 3))); // 3-5일 간격
          return date.toLocaleDateString('ko-KR').replace(/\./g, '.').replace(/ /g, '');
        };
        
        // 상품 타입에 따른 구체적 상품명
        const getProductName = (productType: string) => {
          console.log('Product type received:', productType);
          
          // 한글/영문 모두 처리
          const type = productType.toLowerCase().trim();
          
          if (type.includes('예금') || type.includes('deposit')) {
            return '채움적금';
          } else if (type.includes('적금') || type.includes('savings')) {
            return 'NH내가Green초록세상예금';
          } else if (type.includes('펀드') || type.includes('fund') || type.includes('대출') || type.includes('loan')) {
            return '주택담보노후연금대출';
          } else {
            return productType;
          }
        };
        
        // 백엔드 데이터를 UI 형식으로 변환
        const formattedConsultations: ConsultationDetail[] = response.consultations.map((consultation, index) => {
          const productName = getProductName(consultation.product_type);
          
          // 상품명에 따른 카테고리 설정
          let category = '가입 완료';
          if (productName === 'NH내가Green초록세상예금') {
            category = '상담 완료';
          } else if (productName === '채움적금') {
            category = '신규 가입';
          } else if (productName === '주택담보노후연금대출') {
            category = '서류 보완 필요';
          }
          
          return {
            id: consultation.consultation_id,
            title: productName,
            location: nhBranches[index % nhBranches.length],
            date: generateDate(index),
            category: category,
            expectedAmount: '',
            nextAction: consultation.status === 'completed' ? '' : '',
            status: consultation.status === 'completed' ? 'completed' : 'active',
            statusText: consultation.status === 'completed' ? '완료' : '액션필요'
          };
        });

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
      
      // NH 영업점 이름 목록
      const nhBranches = ['NH농협은행 종로금융센터', 'NH농협은행 동대문지점', 'NH농협은행 평화지점'];
      
      // 각각 다른 날짜 생성
      const generateDate = (index: number) => {
        const date = new Date();
        date.setDate(date.getDate() - (index * 3 + Math.floor(Math.random() * 3)));
        return date.toLocaleDateString('ko-KR').replace(/\./g, '.').replace(/ /g, '');
      };
      
      // 상품 타입에 따른 구체적 상품명
      const getProductName = (productType: string) => {
        // 한글/영문 모두 처리
        const type = productType.toLowerCase().trim();
        
        if (type.includes('예금') || type.includes('deposit')) {
          return '채움적금';
        } else if (type.includes('적금') || type.includes('savings')) {
          return 'NH내가Green초록세상예금';
        } else if (type.includes('펀드') || type.includes('fund') || type.includes('대출') || type.includes('loan')) {
          return '주택담보노후연금대출';
        } else {
          return productType;
        }
      };
      
      // 검색 결과를 UI 형식으로 변환
      const formattedResults: ConsultationDetail[] = response.consultations.map((consultation: any, index: number) => {
        const productName = getProductName(consultation.product_type);
        
        // 상품명에 따른 카테고리 설정
        let category = '가입 완료';
        if (productName === 'NH내가Green초록세상예금') {
          category = '상담 완료';
        } else if (productName === '채움적금') {
          category = '신규 가입';
        } else if (productName === '주택담보노후연금대출') {
          category = '서류 보완 필요';
        }
        
        return {
          id: consultation.consultation_id,
          title: productName,
          location: nhBranches[index % nhBranches.length],
          date: generateDate(index),
          category: category,
          expectedAmount: '',
          nextAction: consultation.status === 'completed' ? '' : '다음 할 일: 추가 서류 준비',
          status: consultation.status === 'completed' ? 'completed' : 'active',
          statusText: consultation.status === 'completed' ? '완료' : '액션필요'
        };
      });

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
          <button className="flex-1 py-2 text-sm font-medium text-gray-600">
            상담예약
          </button>
          <button className="flex-1 py-2 text-sm font-medium text-white bg-gray-500 rounded-full">
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
                      <span className="inline-block px-2 py-0.5 bg-gray-100 text-xs text-gray-700 rounded">
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