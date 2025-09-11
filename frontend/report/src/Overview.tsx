import React from 'react';
import { ArrowLeft } from 'lucide-react';

interface OverviewProps {
  consultationId: string;
  onBack: () => void;
}

interface ConsultationDetails {
  title: string;
  location: string;
  date: string;
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
  const getConsultationDetails = (id: string): ConsultationDetails | null => {
    const detailsMap: Record<string, ConsultationDetails> = {
      '1': {
        title: '은퇴설계 연금펀드 상담',
        location: '미사강변지점',
        date: '2025.09.08',
        productInfo: {
          name: 'NH 퇴직연금펀드',
          investment: '월 50만원 적립',
          totalAmount: '6,000만원 (10년)'
        },
        importantItems: [
          {
            text: '중도해지 시 불이익',
            desc: '5년 이내 해지 시 수익률 3% 감소'
          },
          {
            text: '세제 혜택',
            desc: '연간 700만원까지 세액공제 가능'
          }
        ],
        expectedReturn: {
          period: '10년 만기 예상',
          amount: '8,570만원',
          profit: '수익률 42.8% (+2,570만원)'
        },
        todoItems: [
          '가족 관계 증명서 준비',
          '소득 증빙 서류 제출',
          '계좌 개설 신청서 작성'
        ]
      },
      '2': {
        title: '주택청약 적금 상담',
        location: '미사강변지점',
        date: '2025.09.08',
        productInfo: {
          name: 'NH 주택청약종합저축',
          investment: '월 30만원 적립',
          totalAmount: '1,080만원 (3년)'
        },
        importantItems: [
          {
            text: '청약 1순위 조건',
            desc: '2년 이상 납입, 지역별 예치금 충족 필요'
          },
          {
            text: '해지 제한',
            desc: '청약 사용 전 임의 해지 시 재가입 제한'
          }
        ],
        expectedReturn: {
          period: '3년 만기 예상',
          amount: '1,150만원',
          profit: '수익률 6.5% (+70만원)'
        },
        todoItems: [
          '주민등록등본 제출',
          '청약통장 개설 신청',
          '자동이체 계좌 연결'
        ]
      },
      '3': {
        title: '정기예금 상담',
        location: '미사강변지점',
        date: '2025.09.08',
        productInfo: {
          name: 'NH 정기예금',
          investment: '1,000만원 일시납',
          totalAmount: '1,000만원 (1년)'
        },
        importantItems: [
          {
            text: '금리 우대 조건',
            desc: 'NH카드 사용실적 월 30만원 이상 시 0.2%p 추가'
          },
          {
            text: '만기 후 처리',
            desc: '만기일 후 자동연장 또는 보통예금 전환'
          }
        ],
        expectedReturn: {
          period: '1년 만기',
          amount: '1,038만원',
          profit: '수익률 3.8% (+38만원)'
        },
        todoItems: [
          '신분증 지참 방문',
          '예금 가입 신청서 작성',
          '인감 또는 서명 등록'
        ]
      }
    };

    return detailsMap[id] || null;
  };

  const details = getConsultationDetails(consultationId);
  if (!details) return null;

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
          <h2 className="text-xl font-bold text-black mb-2">{details.title}</h2>
          <p className="text-sm text-gray-500">{details.location} • {details.date}</p>
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