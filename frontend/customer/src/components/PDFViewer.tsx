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
    const [highlightActive, setHighlightActive] = useState(false);

    const viewerContainerRef = useRef<HTMLDivElement>(null);
    const highlightRef = useRef<any>(null);
    const scrollPositionRef = useRef<number>(0);
    
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
        '원금손실': "세 개의 지수 중 두 개가 아무리 올라도 소용없습니다. 가장 많이 떨어진 지수 하나가 고객님의 최종 손실률을 결정합니다."
    };
    
    const [currentKeyword, setCurrentKeyword] = useState<string>('');

    const searchPluginInstance = searchPlugin({
        renderHighlights: (renderProps) => {
            // 라인별로 키워드 수집
            const lineKeywords = new Map<number, Set<string>>();
            const lineAreas = new Map<number, number[]>();

            renderProps.highlightAreas.forEach((area, idx) => {
                const keyword = (area as any).keywordStr;
                const cssProps = renderProps.getCssProperties(area);
                if (cssProps.top && keyword?.trim()) {
                    const topValue = typeof cssProps.top === 'string' ? cssProps.top : String(cssProps.top);
                    const topNum = parseFloat(topValue);

                    if (!lineKeywords.has(topNum)) {
                        lineKeywords.set(topNum, new Set());
                        lineAreas.set(topNum, []);
                    }
                    lineKeywords.get(topNum)!.add(keyword);
                    lineAreas.get(topNum)!.push(idx);
                }
            });

            // 첫 번째 줄과 두 번째 줄을 각각 찾기
            type LineData = {top: number, areas: number[]};
            let firstLine: LineData | null = null;
            let secondLine: LineData | null = null;

            // 첫 번째 줄 찾기: 원금손실(손실률 = 만기평가가격이 최초기준가격 대비
            lineKeywords.forEach((keywords, topNum) => {
                const keywordArray = Array.from(keywords);

                const hasAll =
                    keywordArray.some(k => k.includes('원금손실')) &&
                    keywordArray.some(k => k.includes('(')) &&
                    keywordArray.some(k => k.includes('손실률')) &&
                    keywordArray.some(k => k.includes('=')) &&
                    keywordArray.some(k => k.includes('만기평가가격')) &&
                    keywordArray.some(k => k.includes('이')) &&
                    keywordArray.some(k => k.includes('최초기준가격')) &&
                    keywordArray.some(k => k.includes('대비'));

                if (hasAll) {
                    firstLine = { top: topNum, areas: lineAreas.get(topNum) || [] };
                }
            });

            // 두 번째 줄 찾기: 가장 낮은 기초자산의 하락률)
            lineKeywords.forEach((keywords, topNum) => {
                const keywordArray = Array.from(keywords);
                const hasAll =
                    keywordArray.some(k => k.includes('가장')) &&
                    keywordArray.some(k => k.includes('낮은')) &&
                    keywordArray.some(k => k.includes('기초자산')) &&
                    keywordArray.some(k => k.includes('의')) &&
                    keywordArray.some(k => k.includes('하락률')) &&
                    keywordArray.some(k => k.includes(')'));

                if (hasAll) {
                    secondLine = { top: topNum, areas: lineAreas.get(topNum) || [] };
                }
            });

            // 두 줄이 모두 있고, 서로 가까운 위치에 있는지 확인 (±50px 이내)
            const targetAreaIndices = new Set<number>();
            if (firstLine !== null && secondLine !== null) {
                const line1: LineData = firstLine;
                const line2: LineData = secondLine;
                if (Math.abs(line1.top - line2.top) < 50) {
                    line1.areas.forEach((idx: number) => targetAreaIndices.add(idx));
                    line2.areas.forEach((idx: number) => targetAreaIndices.add(idx));
                }
            }

            // 렌더링
            return (
                <>
                    {renderProps.highlightAreas.map((area, index) => {
                        if (!targetAreaIndices.has(index)) return null;

                        const keyword = (area as any).keywordStr;
                        if (!keyword?.trim()) return null;

                        const cssProps = renderProps.getCssProperties(area);
                        const isClickable = keyword.includes('원금손실');

                        return (
                            <div
                                key={`keyword-${index}`}
                                className="keyword-highlight"
                                style={{
                                    ...cssProps,
                                    cursor: isClickable ? 'pointer' : 'default',
                                    pointerEvents: isClickable ? 'auto' : 'none',
                                    zIndex: 100
                                }}
                                onClick={isClickable ? (e) => {
                                    e.preventDefault();
                                    e.stopPropagation();

                                    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
                                    setCurrentKeyword('원금손실');

                                    const newPosition = {
                                        top: rect.bottom + window.scrollY + 15,
                                        left: rect.left + window.scrollX
                                    };

                                    setPopupPosition(newPosition);
                                    setShowPopup(true);
                                } : undefined}
                                title={isClickable ? "클릭하여 쉬운 설명 보기" : undefined}
                            />
                        );
                    })}
                </>
            );
        },
    });

    const { highlight } = searchPluginInstance;

    // highlight 함수를 ref에 저장
    useEffect(() => {
        highlightRef.current = highlight;
    }, [highlight]);

    // Shift+0 키보드 이벤트로 하이라이트 토글
    useEffect(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            // Shift+0 키 감지
            if (event.shiftKey && event.key === ')') {  // Shift+0는 ')' 문자
                event.preventDefault();
                setHighlightActive(prev => {
                    // 토글 off 시 팝업도 닫기
                    if (prev) {
                        setShowPopup(false);
                    }
                    return !prev;
                });
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, []);

    // highlightActive 상태에 따라 하이라이트 실행/제거
    useEffect(() => {
        if (highlightRef.current && pdfLoaded) {
            if (highlightActive) {
                // 현재 스크롤 위치 저장
                const viewerContainer = viewerContainerRef.current?.querySelector('.rpv-core__viewer');
                if (viewerContainer) {
                    scrollPositionRef.current = viewerContainer.scrollTop;
                }

                setTimeout(() => {
                    // 첫 번째 줄과 두 번째 줄의 모든 키워드
                    const keywords = [
                        // 첫 번째 줄: 원금손실(손실률 = 만기평가가격이 최초기준가격 대비
                        '원금손실', '(', '손실률', '=', '>', '만기평가가격', '이', '최초기준가격', '대비',
                        // 두 번째 줄: 가장 낮은 기초자산의 하락률)
                        '가장', '낮은', '기초자산', '의', '하락률', ')'
                    ];
                    highlightRef.current(keywords);

                    // 하이라이트 후 스크롤 위치 복원
                    setTimeout(() => {
                        const viewerContainer = viewerContainerRef.current?.querySelector('.rpv-core__viewer');
                        if (viewerContainer && scrollPositionRef.current > 0) {
                            viewerContainer.scrollTop = scrollPositionRef.current;
                        }
                    }, 50);
                }, 100);
            } else {
                // 하이라이트 제거
                highlightRef.current([]);
            }
        }
    }, [highlightActive, pdfLoaded]);

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
                            width: '400px',  // 280px * 1.2 = 336px
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
                                        const explanationText = EXPLANATIONS[currentKeyword as keyof typeof EXPLANATIONS] || EXPLANATIONS['원금손실'];
                                        const exampleText = '예를 들어, KOSPI200 지수가 +20%, NIKKEI225 지수가 +15% 올랐어도, HSCEI 지수가 -30% 떨어지면 고객님의 손실은 -30%가 됩니다. 가장 안 좋은 하나의 결과가 전체 손실을 결정합니다.';

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
                                    {EXPLANATIONS[currentKeyword as keyof typeof EXPLANATIONS] || EXPLANATIONS['원금손실']}
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
                                    예를 들어, <strong>KOSPI200 지수가 +20%</strong>, <strong>NIKKEI225 지수가 +15%</strong> 올랐어도, <strong style={{color: '#d32f2f'}}>HSCEI 지수가 -30% 떨어지면</strong> 고객님의 손실은 <strong style={{color: '#d32f2f'}}>-30%</strong>가 됩니다. 가장 안 좋은 하나의 결과가 전체 손실을 결정합니다.
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