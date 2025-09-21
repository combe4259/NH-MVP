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

  // 백엔드 데이터에서 UI용 상세 정보 추출 (하드코딩)
  const getConsultationDetails = (): ConsultationDetails | null => {
    // NH내가Green초록세상적금 실제 상품 정보 기반
    return {
      productInfo: {
        name: 'NH내가Green초록세상적금',
        investment: '자유적립식 (월 1만원~50만원)',
        totalAmount: '월 30만원 × 24개월'
      },
      importantItems: [
        {
          text: '계좌에 압류, 가압류, 질권설정 등이 등록될 경우 원금 및 이자 지급 제한',
          desc: '법원이나 채권자가 계좌를 막으면 돈을 찾을 수 없게 됩니다. 압류는 법원이 재산을 못 쓰게 막는 것, 가압류는 임시로 막는 것, 질권설정은 담보로 잡히는 것입니다.'
        }
      ],
      expectedReturn: {
        period: '24개월 만기 시 (기본 2.35% + 우대 1.0%)',
        amount: '7,602,180원',
        profit: '원금 7,200,000원 + 이자 402,180원 (세전)'
      },
      todoItems: [
        '온실가스 줄이기 실천 서약서 제출하기',
        '통장 미발급 선택하여 우대금리 0.3% 받기'
      ]
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
          <h2 className="text-xl font-bold text-black mb-2">NH내가Green초록세상적금 상담</h2>
          <p className="text-sm text-gray-500">NH농협은행 종로금융센터 • 2025. 9. 16.</p>
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
              <span className="text-sm text-green-600 font-bold">{details.productInfo.totalAmount}</span>
            </div>
          </div>
        </div>

        {/* Important Notice */}
        <div className="mb-6">
          <div className="flex items-center mb-3">
            <h3 className="text-base font-medium text-black">특별히 확인하신 내용</h3>
          </div>
          
          <div className="space-y-3">
            {details.importantItems.map((item, index) => (
              <div key={index} className="bg-green-50 border-l-4 border-green-600 p-3 rounded-r">
                <h4 className="text-sm font-medium text-black mb-1">{item.text}</h4>
                <p className="text-xs text-gray-600">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Expected Returns */}
        <div className="mb-6">
          <div className="flex items-center mb-3">
            <h3 className="text-base font-medium text-black">예상 수익 시뮬레이션</h3>
          </div>
          
          <div className="bg-green-50 rounded-lg p-4 text-center">
            <p className="text-sm text-gray-600 mb-2">{details.expectedReturn.period}</p>
            <p className="text-2xl font-bold text-green-600 mb-1">{details.expectedReturn.amount}</p>
            <p className="text-sm text-gray-600">{details.expectedReturn.profit}</p>
          </div>
        </div>

        {/* Todo List */}
        <div className="mb-6">
          <div className="flex items-center mb-3">
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
            <h3 className="text-base font-medium text-black">가족과 공유하기</h3>
          </div>
          
          <div className="bg-white rounded-lg p-4">
            <p className="text-sm text-gray-600 text-center mb-4">
              오늘 상담 내용을 가족에게 공유해보세요
            </p>
            <button className="w-full py-3 bg-green-600 text-white rounded-lg text-sm font-medium">
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