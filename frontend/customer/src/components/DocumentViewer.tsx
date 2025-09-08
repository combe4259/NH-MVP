import React, { useEffect, useRef, useState } from 'react';
import './DocumentViewer.css';

interface DocumentViewerProps {
  onSectionChange: (section: string) => void;
  isTracking: boolean;
}

const DocumentViewer: React.FC<DocumentViewerProps> = ({ onSectionChange, isTracking }) => {
  const [highlightedSections, setHighlightedSections] = useState<string[]>([]);
  const documentRef = useRef<HTMLDivElement>(null);

  // 샘플 약관 내용
  const documentContent = {
    title: "NH농협 정기예금 상품약관",
    sections: [
      {
        id: "section1",
        title: "1. 상품 개요",
        content: `본 상품은 일정 기간 동안 고정금리로 운용되는 정기예금 상품입니다.
        
        • 가입대상: 개인 및 법인
        • 예금한도: 1인당 5천만원까지 예금자보호
        • 가입기간: 6개월, 12개월, 24개월, 36개월
        • 이자지급: 만기일시지급식, 월이자지급식 선택 가능`
      },
      {
        id: "section2",
        title: "2. 이자율 및 우대조건",
        content: `기본이자율은 연 3.5%이며, 다음 조건 충족 시 우대이자율이 적용됩니다.
        
        • 급여이체 고객: +0.2%p
        • 신용카드 이용고객: +0.1%p
        • 공과금 자동이체 3건 이상: +0.1%p
        • 최대 우대이자율: 연 4.0%`
      },
      {
        id: "section3",
        title: "3. 중도해지 시 불이익",
        content: `만기 전 중도해지 시 다음과 같은 중도해지이율이 적용됩니다.
        
        • 1개월 미만: 연 0.1%
        • 1개월 이상 ~ 3개월 미만: 연 0.5%
        • 3개월 이상 ~ 6개월 미만: 연 1.0%
        • 6개월 이상: 약정이율의 50%
        
        ⚠️ 중도해지 시 약정한 우대이율은 적용되지 않습니다.`
      },
      {
        id: "section4",
        title: "4. 예금자보호",
        content: `이 예금은 예금자보호법에 따라 예금보험공사가 보호합니다.
        
        • 보호한도: 본 은행에 있는 모든 예금보호 대상 금융상품의 원금과 소정의 이자를 합하여 1인당 5천만원
        • 5천만원을 초과하는 나머지 금액은 보호하지 않습니다.
        • 법인의 경우 예금보험 대상에서 제외될 수 있습니다.`
      },
      {
        id: "section5",
        title: "5. 유의사항",
        content: `• 만기 후 재예치를 원하지 않는 경우 사전에 해지 신청을 하셔야 합니다.
        • 만기 자동연장 시 재예치 시점의 금리가 적용됩니다.
        • 비과세종합저축은 가입자격 제한이 있으며, 한도가 정해져 있습니다.
        • 인터넷뱅킹 가입 고객은 온라인으로도 해지가 가능합니다.`
      }
    ]
  };

  useEffect(() => {
    if (isTracking && documentRef.current) {
      const handleScroll = () => {
        const sections = documentRef.current?.querySelectorAll('.document-section');
        sections?.forEach((section) => {
          const rect = section.getBoundingClientRect();
          const isInView = rect.top >= 0 && rect.bottom <= window.innerHeight;
          if (isInView) {
            onSectionChange(section.id);
          }
        });
      };

      documentRef.current.addEventListener('scroll', handleScroll);
      return () => {
        documentRef.current?.removeEventListener('scroll', handleScroll);
      };
    }
  }, [isTracking, onSectionChange]);

  return (
    <div className="document-viewer" ref={documentRef}>
      <div className="document-header">
        <h2>{documentContent.title}</h2>
        <div className="document-meta">
          <span className="doc-date">작성일: 2024.01.01</span>
          <span className="doc-version">버전: 1.0</span>
        </div>
      </div>
      
      <div className="document-body">
        {documentContent.sections.map((section) => (
          <div 
            key={section.id} 
            id={section.id}
            className={`document-section ${highlightedSections.includes(section.id) ? 'highlighted' : ''}`}
          >
            <h3>{section.title}</h3>
            <div className="section-content">
              {section.content.split('\n').map((line, idx) => (
                <p key={idx}>{line}</p>
              ))}
            </div>
          </div>
        ))}
      </div>
      
      <div className="document-footer">
        <p className="disclaimer">
          본 약관은 금융소비자의 이해를 돕기 위한 요약본입니다. 
          자세한 내용은 상품설명서 및 약관을 참고하시기 바랍니다.
        </p>
      </div>
    </div>
  );
};

export default DocumentViewer;