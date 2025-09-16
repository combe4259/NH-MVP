import React, { useState, useEffect } from 'react';
import { ArrowLeft } from 'lucide-react';
import { reportAPI, ConsultationReport } from './api/backend';

interface OverviewProps {
  consultationId: string;
  onBack: () => void;
}

interface ConsultationDetails {
  productInfo: {
    name: string;
    investment: string;
    totalAmount: string;
  };
  importantItems: Array<{
    text: string;
    desc: string;
  }>;
  expectedReturn: {
    period: string;
    amount: string;
    profit: string;
  };
  todoItems: string[];
}

const Overview: React.FC<OverviewProps> = ({ consultationId, onBack }) => {
  const [consultationReport, setConsultationReport] = useState<ConsultationReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchConsultationReport = async () => {
      try {
        setIsLoading(true);
        const report = await reportAPI.getConsultationReport(consultationId);
        setConsultationReport(report);
      } catch (error) {
        console.error('상담 리포트 조회 실패:', error);
        setError('상담 정보를 불러올 수 없습니다.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchConsultationReport();
  }, [consultationId]);

  // 백엔드 데이터에서 UI용 상세 정보 추출
  const getConsultationDetails = (): ConsultationDetails | null => {
    if (!consultationReport?.detailed_info) {
      return null;
    }

    const dbData = consultationReport.detailed_info;
    return {
      productInfo: {
        name: dbData.product_name || '',
        investment: dbData.investment_type || '',
        totalAmount: dbData.total_amount || ''
      },
      importantItems: dbData.important_items || [],
      expectedReturn: dbData.expected_return || { period: '', amount: '', profit: '' },
      todoItems: dbData.todo_items || []
    };
  };

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

  if (error || !consultationReport) {
    return (
      <div className="max-w-sm mx-auto bg-gray-50 min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 mb-4">{error || '상담 내역을 찾을 수 없습니다.'}</p>
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

  const details = getConsultationDetails();
  if (!details) {
    return (
      <div className="max-w-sm mx-auto bg-gray-50 min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 mb-4">상담 상세 정보를 찾을 수 없습니다.</p>
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
      <div className="flex items-center justify-center px-4 py-4 bg-white relative">
        <ArrowLeft 
          className="w-6 h-6 text-gray-700 cursor-pointer absolute left-4" 
          onClick={onBack}
        />
        <h1 className="text-lg font-medium text-black">상담 상세내역</h1>
      </div>

      {/* Content */}
      <div className="px-4 py-6 overflow-y-auto scrollbar-hide" style={{ height: 'calc(100vh - 90px)' }}>
        {/* Title Section */}
        <div className="text-center mb-8">
          <h2 className="text-xl font-bold text-black mb-2">{consultationReport.product_type} 상담</h2>
          <p className="text-sm text-gray-500">NH 디지털 상담 • {new Date(consultationReport.start_time).toLocaleDateString('ko-KR')}</p>
        </div>

        {/* Product Info */}
        <div className="bg-white rounded-lg p-4 mb-6">
          <h3 className="text-base font-medium text-black mb-4">상품 정보</h3>
          
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">상품명</span>
              <span className="text-sm text-black font-medium">{details.productInfo.name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">투자 방식</span>
              <span className="text-sm text-black font-medium">{details.productInfo.investment}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">총 투자금액</span>
              <span className="text-sm text-blue-600 font-bold">{details.productInfo.totalAmount}</span>
            </div>
          </div>
        </div>

        {/* Important Notice */}
        <div className="mb-6">
          <div className="flex items-center mb-3">
            <span className="text-orange-500 mr-2">⚠️</span>
            <h3 className="text-base font-medium text-black">특별히 확인하신 내용</h3>
          </div>
          
          <div className="space-y-3">
            {details.importantItems.map((item, index) => (
              <div key={index} className="bg-orange-50 border-l-4 border-orange-500 p-3 rounded-r">
                <h4 className="text-sm font-medium text-black mb-1">{item.text}</h4>
                <p className="text-xs text-gray-600">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Expected Returns */}
        <div className="mb-6">
          <div className="flex items-center mb-3">
            <span className="text-blue-500 mr-2">📊</span>
            <h3 className="text-base font-medium text-black">예상 수익 시뮬레이션</h3>
          </div>
          
          <div className="bg-blue-50 rounded-lg p-4 text-center">
            <p className="text-sm text-gray-600 mb-2">{details.expectedReturn.period}</p>
            <p className="text-2xl font-bold text-blue-600 mb-1">{details.expectedReturn.amount}</p>
            <p className="text-sm text-gray-600 mb-4">{details.expectedReturn.profit}</p>
            <button className="px-4 py-2 border border-blue-300 text-blue-600 rounded-full text-sm">
              상세 시뮬레이션 보기
            </button>
          </div>
        </div>

        {/* Todo List */}
        <div className="mb-6">
          <div className="flex items-center mb-3">
            <span className="text-orange-500 mr-2">📝</span>
            <h3 className="text-base font-medium text-black">다음에 해야 할 일</h3>
          </div>
          
          <div className="bg-white rounded-lg p-4">
            <div className="space-y-3">
              {details.todoItems.map((item, index) => (
                <div key={index} className="flex items-center">
                  <div className="w-4 h-4 border border-gray-300 rounded mr-3"></div>
                  <span className="text-sm text-gray-700">{item}</span>
                </div>
              ))}
            </div>
            
            <div className="flex space-x-3 mt-4">
              <button className="flex-1 py-3 border border-gray-300 text-gray-700 rounded-lg text-sm">
                일정 추가
              </button>
              <button className="flex-1 py-3 bg-green-600 text-white rounded-lg text-sm">
                재예약
              </button>
            </div>
          </div>
        </div>

        {/* Share */}
        <div className="mb-6">
          <div className="flex items-center mb-3">
            <span className="text-yellow-500 mr-2">📤</span>
            <h3 className="text-base font-medium text-black">가족과 공유하기</h3>
          </div>
          
          <div className="bg-white rounded-lg p-4">
            <p className="text-sm text-gray-600 text-center mb-4">
              오늘 상담 내용을 가족에게 공유해보세요
            </p>
            <button className="w-full py-3 bg-yellow-400 text-black rounded-lg text-sm font-medium">
              카카오톡으로 공유
            </button>
          </div>
        </div>

        {/* Bottom Button */}
        <button className="w-full py-4 bg-green-600 text-white rounded-lg text-base font-medium">
          추가 문의하기
        </button>
      </div>
    </div>
  );
};

export default Overview;