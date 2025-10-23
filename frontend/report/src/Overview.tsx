import React, { useState, useEffect } from 'react';
import { ArrowLeft, TrendingUp, AlertTriangle, CheckCircle } from 'lucide-react';
import { reportAPI, ConsultationReport } from './api/backend';

interface OverviewProps {
  consultationId: string;
  onBack: () => void;
}

interface AssetPriceInfo {
  name: string;
  initialPrice: string;
  redemptionPrice: string;
  knockInPrice: string;
  schedule: string;
}

interface KeyDates {
  initialPriceDate: string;
  firstRedemptionDate: string;
  maturityDate: string;
}

interface ImportantItem {
  text: string;
  simpleExample: string;
}

interface ConsultationDetails {
  productInfo: {
    name: string;
    branch: string;
    date: string;
    totalAmount: string;
    riskGrade: string;
  };
  assetInfo: AssetPriceInfo[];
  keyDates: KeyDates;
  importantItems: ImportantItem[];
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

  const getConsultationDetails = (): ConsultationDetails | null => {
    const redemptionSchedule = '90-90-85-85-80-75';
    return {
      productInfo: {
        name: 'N2 ELS 제44회 파생결합증권',
        branch: 'NH투자증권 Premier Blue 삼성동센터',
        date: '2025. 10. 19.',
        totalAmount: '10,000,000원',
        riskGrade: '2등급 (높은 위험)',
      },
      assetInfo: [
        {
          name: 'KOSPI200',
          initialPrice: '525.48pt',
          redemptionPrice: '472.93pt',
          knockInPrice: '262.74pt',
          schedule: redemptionSchedule
        },
        {
          name: 'NIKKEI225',
          initialPrice: '47,582.15pt',
          redemptionPrice: '42,823.94pt',
          knockInPrice: '23,791.08pt',
          schedule: redemptionSchedule
        },
        {
          name: 'HSCEI',
          initialPrice: '9,009.57pt',
          redemptionPrice: '8,108.61pt',
          knockInPrice: '4,504.79pt',
          schedule: redemptionSchedule
        }
      ],
      keyDates: {
        initialPriceDate: '2025년 10월 17일',
        firstRedemptionDate: '2026년 04월 15일',
        maturityDate: '2028년 10월 17일'
      },
      importantItems: [
        {
          text: '투자기간 중 종가 기준으로 최초기준가격의 50% 미만으로 하락한 기초자산이 있는 경우 => 원금손실(손실률 = 만기평가가격이 최초기준가격 대비 가장 낮은 기초자산의 하락률)',
          simpleExample: '예를 들어, KOSPI200 지수가 +20%, NIKKEI225 지수가 +15% 올랐어도, HSCEI 지수가 -30% 떨어지면 고객님의 손실은 -30%가 됩니다. 가장 안 좋은 하나의 결과가 전체 손실을 결정합니다.'
        }
      ],
      todoItems: [
        '기초자산(KOSPI200, NIKKEI225, HSCEI) 가격 변동성 주기적으로 확인하기',
        '다음 조기상환 평가일(2026년 04월 15일) 달력에 추가하기'
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
        
        {/* Product Core Summary (New Header) */}
        <div className="bg-white rounded-lg p-4 mb-6">
          <div className="text-center mb-4">
            <h2 className="text-xl font-bold text-black mb-1">{details.productInfo.name}</h2>
            <p className="text-sm text-gray-500">{details.productInfo.branch} • {details.productInfo.date}</p>
          </div>
          <div className="border-t border-gray-200 pt-4 space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">총 투자금액</span>
              <span className="text-sm text-blue-600 font-bold">{details.productInfo.totalAmount}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">상품 위험등급</span>
              <span className="text-sm text-red-600 font-bold">{details.productInfo.riskGrade}</span>
            </div>
          </div>
        </div>

        {/* Key Clauses Requiring Confirmation */}
        <div className="mb-6">
          <h3 className="text-base font-medium text-black mb-3">핵심 위험 사항</h3>
          <div className="space-y-3">
            {details.importantItems.map((item, index) => (
              <div key={index} className="bg-white border border-gray-200 rounded-lg">
                <div className="bg-red-100 border-l-4 border-red-500 p-4">
                  <p className="text-sm text-gray-800 font-medium">{item.text}</p>
                </div>
                <div className="p-4 space-y-3">
                  <div>
                    <p className="text-xs font-semibold text-blue-500 mb-1">쉬운 설명</p>
                    <p className="text-sm text-gray-700">{item.simpleExample}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Key Asset Prices */}
        <div className="mb-6">
          <h3 className="text-base font-medium text-black mb-3">기초자산 주요 가격</h3>
          <div className="space-y-2">
            {details.assetInfo.map((asset, index) => (
              <div key={index} className="bg-white rounded-lg p-4">
                <div className="text-center font-bold text-blue-600 mb-1">{asset.name}</div>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div>
                    <div className="text-xs text-gray-500">최초 기준가</div>
                    <div className="text-sm font-medium text-black">{asset.initialPrice}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500">조기상환가 (90%)</div>
                    <div className="text-sm font-medium text-green-600">{asset.redemptionPrice}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500">원금손실선 (50%)</div>
                    <div className="text-sm font-medium text-red-600">{asset.knockInPrice}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="bg-white rounded-lg p-3 mt-2 text-center">
            <p className="text-xs text-gray-500">상환 조건 (6개월 단위)</p>
            <p className="text-sm font-medium text-gray-800">{details.assetInfo[0].schedule}</p>
          </div>
        </div>

        {/* Key Dates */}
        <div className="mb-6">
          <h3 className="text-base font-medium text-black mb-3">주요 일정</h3>
          <div className="bg-white rounded-lg p-4 space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">최초기준가격 평가일</span>
              <span className="text-sm text-black font-medium">{details.keyDates.initialPriceDate}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">첫 조기상환 평가일</span>
              <span className="text-sm text-black font-medium">{details.keyDates.firstRedemptionDate}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">만기일</span>
              <span className="text-sm text-black font-medium">{details.keyDates.maturityDate}</span>
            </div>
          </div>
        </div>

        {/* Todo List */}
        <div className="mb-6">
          <h3 className="text-base font-medium text-black mb-3">다음에 해야 할 일</h3>
          <div className="bg-white rounded-lg p-4">
            <div className="space-y-3">
              {details.todoItems.map((item, index) => (
                <div key={index} className="flex items-center">
                  <CheckCircle className="w-4 h-4 text-green-500 mr-3" />
                  <span className="text-sm text-gray-700">{item}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Share */}
        <div className="mb-6">
          <h3 className="text-base font-medium text-black mb-3">가족과 공유하기</h3>
          <div className="bg-white rounded-lg p-4">
            <p className="text-sm text-gray-600 text-center mb-4">오늘 상담 내용을 가족에게 공유해보세요</p>
            <button className="w-full py-3 bg-green-600 text-white rounded-lg text-sm font-medium">카카오톡으로 공유</button>
          </div>
        </div>

        {/* Bottom Button */}
        <button className="w-full py-4 bg-blue-600 text-white rounded-lg text-base font-medium">추가 문의하기</button>
      </div>
    </div>
  );
};

export default Overview;