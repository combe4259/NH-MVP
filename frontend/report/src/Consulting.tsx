import React, { useState } from 'react';
import { ChevronRight, Menu, Home, ArrowLeft } from 'lucide-react';
import Overview from './Overview';

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
  const [consultationDetails] = useState<ConsultationDetail[]>([
    {
      id: '1',
      title: '은퇴설계 연금펀드 상담',
      location: '미사강변지점',
      date: '2025.09.08',
      category: '예상 수익',
      expectedAmount: '557만원 (5년)',
      nextAction: '다음 할 일: 가족 관계 증명서 준비하기',
      status: 'active',
      statusText: '액션필요'
    },
    {
      id: '2',
      title: '주택청약 적금 상담',
      location: '미사강변지점',
      date: '2025.09.08',
      category: '가입 금액',
      possibleAmount: '월 30만원',
      nextAction: '다음 할 일: 가족 관계 증명서 준비하기',
      status: 'completed',
      statusText: '완료'
    },
    {
      id: '3',
      title: '정기예금 상담',
      location: '미사강변지점',
      date: '2025.09.08',
      category: '만기 예상액',
      possibleAmount: '1,080만원 (1년)',
      maturityDate: '만기일: 2026년 9월 1일',
      nextAction: '',
      status: 'completed',
      statusText: '완료'
    }
  ]);

  if (selectedConsultation) {
    return (
      <Overview 
        consultationId={selectedConsultation} 
        onBack={() => setSelectedConsultation(null)} 
      />
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