import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Worker, Viewer, SpecialZoomLevel } from '@react-pdf-viewer/core';
import { defaultLayoutPlugin } from '@react-pdf-viewer/default-layout';
import { searchPlugin } from '@react-pdf-viewer/search';

import '@react-pdf-viewer/core/lib/styles/index.css';
import '@react-pdf-viewer/default-layout/lib/styles/index.css';
import '@react-pdf-viewer/search/lib/styles/index.css';
import './PDFViewer.css';
import './AIAssistant.css';

interface PDFViewerProps {
    fileUrl: string;
    onPdfLoaded?: (textRegions: any[]) => void;
}

const PDFViewer: React.FC<PDFViewerProps> = ({ fileUrl, onPdfLoaded }) => {
    const [showPopup, setShowPopup] = useState(false);
    const [popupPosition, setPopupPosition] = useState({ top: 0, left: 0 });
    const [pdfLoaded, setPdfLoaded] = useState(false);
    
    const viewerContainerRef = useRef<HTMLDivElement>(null);
    
    // PDF 로드 시 텍스트 영역 추출
    useEffect(() => {
        if (pdfLoaded && viewerContainerRef.current && onPdfLoaded) {
            const extractTextRegions = () => {
                const textLayers = viewerContainerRef.current?.querySelectorAll('.rpv-core__text-layer');
                const textRegions: any[] = [];
                
                textLayers?.forEach((layer, pageIndex) => {
                    const textSpans = layer.querySelectorAll('span');
                    textSpans.forEach(span => {
                        const rect = span.getBoundingClientRect();
                        const text = span.textContent?.trim();
                        
                        if (text && text.length > 0) {
                            textRegions.push({
                                text: text,
                                page: pageIndex + 1,
                                bbox: [rect.left, rect.top, rect.right, rect.bottom],
                                x: rect.left,
                                y: rect.top,
                                width: rect.width,
                                height: rect.height
                            });
                        }
                    });
                });
                
                if (textRegions.length > 0) {
                    onPdfLoaded(textRegions);
                } else {
                    setTimeout(extractTextRegions, 1000);
                }
            };
            
            setTimeout(extractTextRegions, 500);
        }
    }, [pdfLoaded, onPdfLoaded]);

    const defaultLayoutPluginInstance = defaultLayoutPlugin();
    
    // 하드코딩된 설명
    const EXPLANATIONS = {
        '가압류': "통장에 법적인 문제가 생기면 돈을 못 찾아요. 빚 때문에 통장이 잠긴다고 생각하면 됩니다.",
        '질권설정': "통장에 법적인 문제가 생기면 돈을 못 찾아요. 빚 때문에 통장이 잠긴다고 생각하면 됩니다.",
        '권리구제': "나중에 문제가 생겼을 때 법적으로 도움받기 어려워진다는 뜻이에요. 이해하지 못했는데 서명하면 나중에 피해를 보상받기 힘들어집니다."
    };
    
    const [currentKeyword, setCurrentKeyword] = useState<string>('');

    const searchPluginInstance = searchPlugin({
        renderHighlights: (renderProps) => {
            // 특정 문장의 키워드들을 추적하기 위한 Set
            const targetSentenceAreas = new Set<number>();
            let targetLineTop: number | null = null;
            
            // 먼저 "가압류, 질권설정, 권리구제"이 포함된 라인들 찾기
            const targetLineTops: number[] = [];
            
            renderProps.highlightAreas.forEach((area, idx) => {
                const keyword = (area as any).keywordStr;
                if (keyword?.includes('가압류') || keyword?.includes('질권설정') || keyword?.includes('권리구제')) {
                    const cssProps = renderProps.getCssProperties(area);
                    if (cssProps.top) {
                        const topValue = typeof cssProps.top === 'string' ? cssProps.top : String(cssProps.top);
                        const topNum = parseFloat(topValue);
                        // 중복 제거 (오차 범위 2px)
                        if (!targetLineTops.some(t => Math.abs(t - topNum) < 2)) {
                            targetLineTops.push(topNum);
                        }
                    }
                }
            });
            
            // 타겟 라인들과 같은 높이에 있는 모든 키워드 찾기
            targetLineTops.forEach(lineTop => {
                renderProps.highlightAreas.forEach((area, idx) => {
                    const cssProps = renderProps.getCssProperties(area);
                    if (cssProps.top) {
                        const topValue = typeof cssProps.top === 'string' ? cssProps.top : String(cssProps.top);
                        const currentTop = parseFloat(topValue);
                        if (Math.abs(currentTop - lineTop) < 2) {
                            targetSentenceAreas.add(idx);
                        }
                    }
                });
            });
            
            return (
                <>
                    {renderProps.highlightAreas.map((area, index) => {
                        const keyword = (area as any).keywordStr;
                        if (!keyword?.trim()) return null;
                        
                        // 형광펜 하이라이트 키워드 (가압류, 질권설정, 권리구제)
                        const highlightKeywords = ['가압류', '질권설정', '권리구제'];
                        const isHighlightKeyword = highlightKeywords.some(k => keyword.includes(k));
                        
                        // 타겟 문장에 속하는지 확인
                        const isInTargetSentence = targetSentenceAreas.has(index);
                        
                        if (isHighlightKeyword) {
                            // 형광펜 하이라이트 (가압류, 질권설정, 권리구제)
                            const cssProps = renderProps.getCssProperties(area);
                            return (
                                <div
                                    key={`keyword-${index}`}
                                    className="keyword-highlight"
                                    style={{
                                        ...cssProps,
                                        cursor: 'pointer',
                                        pointerEvents: 'auto',
                                        zIndex: 100
                                    }}
                                    onClick={(e) => {
                                        e.preventDefault();
                                        e.stopPropagation();
                                        
                                        const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
                                        
                                        // 클릭된 키워드 확인
                                        const clickedKeyword = highlightKeywords.find(k => keyword.includes(k));
                                        if (clickedKeyword) {
                                            setCurrentKeyword(clickedKeyword);
                                        }
                                        
                                        // 화면 기준 절대 위치로 설정
                                        const newPosition = {
                                            top: rect.bottom + window.scrollY + 5,
                                            left: rect.left + window.scrollX
                                        };
                                        
                                        setPopupPosition(newPosition);
                                        setShowPopup(true);
                                    }}
                                    title="클릭하여 쉬운 설명 보기"
                                />
                            );
                        } else if (isInTargetSentence) {
                            // 타겟 문장에 속하는 다른 단어들은 밑줄
                            const cssProps = renderProps.getCssProperties(area);
                            return (
                                <div
                                    key={`underline-${index}`}
                                    className="line-underline"
                                    style={{
                                        ...cssProps,
                                        cursor: 'auto',
                                        pointerEvents: 'none'
                                    }}
                                />
                            );
                        }
                        
                        return null;
                    })}
                </>
            );
        },
    });

    const { highlight } = searchPluginInstance;

    // PDF 로드되면 자동으로 하이라이트
    useEffect(() => {
        if (highlight && pdfLoaded) {
            setTimeout(() => {
                // 모든 키워드 하이라이트 (형광펜 + 밑줄)
                const keywords = [
                    // 형광펜 키워드
                    '가압류', '질권설정', '권리구제',
                    // 첫 번째 문장 밑줄 키워드
                    '계좌에', '압류', '등이', '등록될', '경우', '원금', '및', '이자', '지급', '제한',
                    // 두 번째 문장 밑줄 키워드
                    '남기시는', '경우,', '추후', '해당', '내용과', '관련한', '가', '어려울', '수', '있습니다'
                ];
                highlight(keywords);
            }, 1500);
        }
    }, [pdfLoaded, highlight]);

    const handleDocumentLoad = useCallback(() => {
        setPdfLoaded(true);
    }, []);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            const target = event.target as HTMLElement;
            if (!target.closest('.sentence-popup') && !target.closest('.sentence-underline')) {
                setShowPopup(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    if (!fileUrl) {
        return (
            <div className="pdf-viewer-container">
                <p>표시할 PDF 문서가 없습니다.</p>
            </div>
        );
    }

    return (
        <div
            className="pdf-viewer-container"
            ref={viewerContainerRef}
            style={{ position: 'relative' }}
        >
            <Worker workerUrl="https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js">
                <div className="pdf-viewer-wrapper">
                    <Viewer
                        fileUrl={fileUrl}
                        plugins={[defaultLayoutPluginInstance, searchPluginInstance]}
                        defaultScale={SpecialZoomLevel.PageFit}
                        onDocumentLoad={handleDocumentLoad}
                    />
                </div>

                {showPopup && (
                    <div
                        className="sentence-popup"
                        style={{
                            position: 'fixed',
                            left: `${popupPosition.left}px`,
                            top: `${popupPosition.top}px`,
                            zIndex: 10000,
                            width: '336px',  // 280px * 1.2 = 336px
                            backgroundColor: '#ffffff',
                            border: '1px solid #e1e4e8',
                            borderRadius: '12px',
                            boxShadow: '0 8px 24px rgba(0, 166, 81, 0.15)',  // NH 그린 색상 그림자
                            overflow: 'hidden'
                        }}
                    >
                        {/* 헤더 */}
                        <div style={{
                            backgroundColor: '#00A651',  // NH 그린
                            padding: '12px 16px',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center'
                        }}>
                            <span style={{
                                color: 'white',
                                fontSize: '14px',
                                fontWeight: '600'
                            }}>
                                NH 문장 도우미
                            </span>
                            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                {/* TTS 재생 버튼 */}
                                <button 
                                    onClick={() => {
                                        const explanationText = EXPLANATIONS[currentKeyword as keyof typeof EXPLANATIONS] || EXPLANATIONS['가압류'];
                                        const exampleText = currentKeyword === '권리구제' 
                                            ? '예를 들어, 상품 설명을 제대로 듣지 못했는데 이해했다고 서명했다면, 나중에 손해를 봐도 은행에 책임을 물을 수 없게 됩니다.'
                                            : '통장에 100만원이 있어도 법원이 막으면 한 푼도 못 찾아요. 통장에 자물쇠가 걸린 것과 같습니다.';
                                        
                                        const fullText = `${explanationText} ${exampleText}`;
                                        
                                        // Web Speech API를 사용한 TTS
                                        if ('speechSynthesis' in window) {
                                            // 기존 재생 중지
                                            window.speechSynthesis.cancel();
                                            
                                            const utterance = new SpeechSynthesisUtterance(fullText);
                                            utterance.lang = 'ko-KR';
                                            utterance.rate = 0.9;  // 속도 약간 느리게
                                            utterance.pitch = 1.0;
                                            utterance.volume = 1.0;
                                            
                                            window.speechSynthesis.speak(utterance);
                                        } else {
                                            alert('이 브라우저는 음성 읽기를 지원하지 않습니다.');
                                        }
                                    }}
                                    style={{
                                        background: 'none',
                                        border: '1px solid white',
                                        borderRadius: '4px',
                                        color: 'white',
                                        fontSize: '12px',
                                        cursor: 'pointer',
                                        padding: '4px 8px',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '4px'
                                    }}
                                    title="음성으로 듣기"
                                >
                                    듣기
                                </button>
                                <button 
                                    onClick={() => {
                                        setShowPopup(false);
                                        // TTS 중지
                                        if ('speechSynthesis' in window) {
                                            window.speechSynthesis.cancel();
                                        }
                                    }}
                                    style={{
                                        background: 'none',
                                        border: 'none',
                                        color: 'white',
                                        fontSize: '18px',
                                        cursor: 'pointer',
                                        padding: 0,
                                        lineHeight: 1
                                    }}
                                >
                                    ×
                                </button>
                            </div>
                        </div>
                        
                        {/* 컨텐츠 */}
                        <div style={{ padding: '16px' }}>
                            {/* 쉬운 설명 */}
                            <div style={{ marginBottom: '16px' }}>
                                <div style={{ 
                                    fontSize: '12px', 
                                    color: '#00A651',  // NH 그린
                                    marginBottom: '8px',
                                    fontWeight: '600',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.5px'
                                }}>
                                    쉽게 풀어서 설명
                                </div>
                                <div style={{ 
                                    fontSize: '15px',
                                    lineHeight: '1.7',
                                    color: '#1a1a1a',
                                    padding: '16px',
                                    borderRadius: '8px',
                                    borderLeft: '4px solid #00A651',  // NH 그린 강조선
                                    fontWeight: '500'
                                }}>
                                    {EXPLANATIONS[currentKeyword as keyof typeof EXPLANATIONS] || EXPLANATIONS['가압류']}
                                </div>
                            </div>

                            {/* 실생활 예시 */}
                            <div>
                                <div style={{ 
                                    fontSize: '12px', 
                                    color: '#00A651',  // NH 그린
                                    marginBottom: '8px',
                                    fontWeight: '600',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.5px'
                                }}>
                                    실생활 예시
                                </div>
                                <div style={{ 
                                    fontSize: '14px',
                                    lineHeight: '1.6',
                                    color: '#1a1a1a',
                                    padding: '16px',
                                    borderRadius: '8px',
                                    boxShadow: '0 2px 8px rgba(0, 166, 81, 0.1)',  // 그린 톤 그림자
                                    fontWeight: '400'
                                }}>
                                    {currentKeyword === '권리구제' 
                                        ? '예를 들어, 상품 설명을 제대로 듣지 못했는데 "이해했다"고 서명했다면, 나중에 손해를 봐도 은행에 책임을 물을 수 없게 됩니다.'
                                        : '통장에 100만원이 있어도 법원이 막으면 한 푼도 못 찾아요. 통장에 자물쇠가 걸린 것과 같습니다.'
                                    }
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </Worker>
        </div>
    );
};

export default PDFViewer;