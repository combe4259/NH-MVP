import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Worker, Viewer, SpecialZoomLevel } from '@react-pdf-viewer/core';
import { defaultLayoutPlugin } from '@react-pdf-viewer/default-layout';
import { searchPlugin } from '@react-pdf-viewer/search';
import type { RenderHighlightsProps, HighlightArea } from '@react-pdf-viewer/search';

import '@react-pdf-viewer/core/lib/styles/index.css';
import '@react-pdf-viewer/default-layout/lib/styles/index.css';
import '@react-pdf-viewer/search/lib/styles/index.css';
import './PDFViewer.css';
import './AIAssistant.css';

interface ExtendedHighlightArea extends HighlightArea {
    highlightContent: string;
}

interface HighlightedText {
    text: string;
    explanation: string;
}

interface DifficultSentence {
    sentence: string;
    sentence_id: string;
    difficulty_score: number;
    simplified_explanation: string;
    original_position: number;
    location?: {
        page_number: number;
        page_width: number;
        page_height: number;
        x: number;
        y: number;
        width: number;
        height: number;
    };
}

interface PDFViewerProps {
    fileUrl: string;
    highlightedTexts?: HighlightedText[];
    difficultSentences?: DifficultSentence[];
    onTextSelect?: (text: string) => void;
    onSentenceClick?: (sentence: DifficultSentence) => void;
}

// ★★★ 1. 밑줄 오버레이 컴포넌트 분리 ★★★
const UnderlineOverlay = React.memo(({
    sentences,
    dimensions,
    containerRef,
    onSentenceClick
}: {
    sentences: DifficultSentence[];
    dimensions: { width: number; height: number } | null;
    containerRef: React.RefObject<HTMLDivElement | null>;
    onSentenceClick: (sentence: DifficultSentence, event: React.MouseEvent) => void;
}) => {
    // 안정적인 좌표 계산 함수
    const calculateScaledPosition = useCallback((sentence: DifficultSentence) => {
        try {
            const location = sentence.location;

            if (!location || !dimensions || !containerRef.current) {
                return { display: 'none' };
            }

            if (location.page_width <= 0 || location.page_height <= 0 ||
                location.width <= 0 || location.height <= 0) {
                return { display: 'none' };
            }

            const containerRect = containerRef.current.getBoundingClientRect();
            const pdfPageRect = containerRef.current.querySelector('.rpv-core__page-layer')?.getBoundingClientRect();

            if (!pdfPageRect) {
                return { display: 'none' };
            }

            const scaleX = dimensions.width / location.page_width;
            const scaleY = dimensions.height / location.page_height;

            if (!isFinite(scaleX) || !isFinite(scaleY) || scaleX <= 0 || scaleY <= 0) {
                return { display: 'none' };
            }

            const topOffset = pdfPageRect.top - containerRect.top;
            const leftOffset = pdfPageRect.left - containerRect.left;

            const finalLeft = leftOffset + location.x * scaleX;
            const finalTop = topOffset + location.y * scaleY;
            const finalWidth = location.width * scaleX;
            const finalHeight = location.height * scaleY;

            if (!isFinite(finalLeft) || !isFinite(finalTop) || finalWidth <= 0 || finalHeight <= 0) {
                return { display: 'none' };
            }

            return {
                position: 'absolute' as const,
                left: `${finalLeft}px`,
                top: `${finalTop}px`,
                width: `${finalWidth}px`,
                height: `${finalHeight}px`,
                borderBottom: '3px solid #ffc107',
                backgroundColor: 'transparent',
                cursor: 'pointer',
                pointerEvents: 'all' as const,
                borderRadius: '2px'
            };
        } catch (error) {
            console.error('좌표 계산 중 오류 발생:', error);
            return { display: 'none' };
        }
    }, [dimensions, containerRef]);

    return (
        <div
            className="coordinate-based-overlay"
            style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                pointerEvents: 'none',
                zIndex: 5
            }}
        >
            {sentences.map((sentence) => (
                <div
                    key={sentence.sentence_id}
                    className="coordinate-sentence-marker"
                    style={calculateScaledPosition(sentence)}
                    onClick={(e) => onSentenceClick(sentence, e)}
                    title={`클릭하여 설명 보기: ${sentence.sentence.substring(0, 30)}...`}
                >
                    {!sentence.location && (
                        <span style={{ fontSize: '12px', color: '#666' }}>
                            {sentence.sentence.substring(0, 50)}...
                        </span>
                    )}
                </div>
            ))}
        </div>
    );
});

const PDFViewer: React.FC<PDFViewerProps> = ({ fileUrl, highlightedTexts = [], difficultSentences = [], onTextSelect, onSentenceClick }) => {
    const [showPopup, setShowPopup] = useState(false);
    const [popupPosition, setPopupPosition] = useState({ top: 0, left: 0 });
    const [currentExplanation, setCurrentExplanation] = useState('');
    const [currentSentence, setCurrentSentence] = useState<DifficultSentence | null>(null);
    const [pdfLoaded, setPdfLoaded] = useState(false);
    const [renderedPdfDimensions, setRenderedPdfDimensions] = useState<{width: number, height: number} | null>(null);
    const viewerContainerRef = useRef<HTMLDivElement>(null);

    const highlightedTextsRef = useRef(highlightedTexts);
    useEffect(() => { highlightedTextsRef.current = highlightedTexts; }, [highlightedTexts]);

    const defaultLayoutPluginInstance = defaultLayoutPlugin();

    // ★★★ 안정적인 클릭 핸들러 ★★★
    const handleSentenceClick = useCallback((sentence: DifficultSentence, event: React.MouseEvent) => {
        if (!viewerContainerRef.current) return;

        // 클릭된 요소의 현재 위치를 바로 계산 (리렌더링 영향 없음)
        const containerRect = viewerContainerRef.current.getBoundingClientRect();
        const underlineRect = (event.currentTarget as HTMLElement).getBoundingClientRect();

        // 상대 좌표 계산
        const relativeTop = underlineRect.bottom - containerRect.top + 5;
        const relativeLeft = underlineRect.left - containerRect.left;

        // 팝업 관련 state 한 번에 설정
        setCurrentSentence(sentence);
        setPopupPosition({ top: relativeTop, left: relativeLeft });
        setShowPopup(true);

        if (onSentenceClick) {
            onSentenceClick(sentence);
        }
    }, [onSentenceClick]);

    // PDF 크기 감지 함수 (여러 방법으로 시도)
    const detectPdfDimensions = (attempt: number = 0) => {
        const selectors = [
            '.rpv-core__inner-pages',
            '.rpv-core__page-layer',
            '.rpv-core__canvas-layer canvas',
            '.rpv-core__text-layer'
        ];

        for (const selector of selectors) {
            const element = document.querySelector(selector);
            if (element) {
                const rect = element.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    setRenderedPdfDimensions({
                        width: rect.width,
                        height: rect.height
                    });
                    console.log(`PDF 크기 감지 성공 (${selector}):`, { width: rect.width, height: rect.height });
                    return;
                }
            }
        }

        // 크기 감지 실패 시 재시도 (최대 5번)
        if (attempt < 5) {
            setTimeout(() => detectPdfDimensions(attempt + 1), 200 * (attempt + 1));
        } else {
            console.warn('PDF 크기 감지 실패 - 기본값 사용');
            setRenderedPdfDimensions({ width: 595, height: 842 }); // A4 기본 크기
        }
    };

    // PDF 렌더링 완료 시 크기 감지
    const handleDocumentLoad = () => {
        setPdfLoaded(true);
        setTimeout(() => detectPdfDimensions(), 300);
    };

    const searchPluginInstance = searchPlugin({
        renderHighlights: (renderProps: RenderHighlightsProps) => (
            <>
                {renderProps.highlightAreas.map((area, index) => {
                    const extendedArea = area as ExtendedHighlightArea;
                    if (!extendedArea.highlightContent) return null;

                    const keyword = extendedArea.highlightContent.trim();
                    if (!keyword) return null;

                    // 오직 주요 용어(highlightedTexts)만 처리
                    const match = highlightedTextsRef.current.find(ht =>
                        typeof ht.text === 'string' &&
                        (ht.text.includes(keyword) || keyword.includes(ht.text))
                    );

                    if (!match) return null;

                    return (
                        <div
                            key={index}
                            className="custom-highlight-underline"
                            style={Object.assign({}, renderProps.getCssProperties(area))}
                            onClick={() => handleHighlightClick(area, match.explanation)}
                            title={match.explanation}
                        />
                    );
                })}
            </>
        ),
    });

    const { highlight } = searchPluginInstance;

    const keywordsRef = useRef<string>('');

    useEffect(() => {
        if (highlight && pdfLoaded && highlightedTexts.length > 0) {
            // 오직 주요 용어(highlightedTexts)만 하이라이트
            const keywords = highlightedTexts.map(ht => ht.text);
            const keywordsString = keywords.join(',');

            // 키워드가 실제로 변경된 경우에만 하이라이트
            if (keywordsString !== keywordsRef.current) {
                keywordsRef.current = keywordsString;
                highlight(keywords);
            }
        }
    }, [pdfLoaded, highlightedTexts]);

    const handleHighlightClick = (area: HighlightArea, explanation: string) => {
        if (!viewerContainerRef.current) return;
        setCurrentExplanation(explanation);

        const containerRect = viewerContainerRef.current.getBoundingClientRect();
        setPopupPosition({
            left: area.left + area.width / 2,
            top: area.top
        });
        setShowPopup(true);
    };


    const handleTextSelection = () => {
        const selection = window.getSelection();
        const text = selection?.toString().trim();
        if (text && text.length > 0 && onTextSelect) {
            onTextSelect(text);
        }
    };

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            const target = event.target as HTMLElement;
            if (!target.closest('.pdf-popup') && !target.closest('.custom-highlight-underline')) {
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
            onMouseUp={handleTextSelection}
            style={{ position: 'relative' }}
        >
            <Worker workerUrl="https://unpkg.com/pdfjs-dist@3.4.120/build/pdf.worker.min.js">
                <div className="pdf-viewer-wrapper">
                    <Viewer
                        fileUrl={fileUrl}
                        plugins={[defaultLayoutPluginInstance, searchPluginInstance]}
                        defaultScale={SpecialZoomLevel.PageFit}
                        onDocumentLoad={handleDocumentLoad}
                    />
                </div>

                {/* ★★★ 분리된 밑줄 오버레이 컴포넌트 사용 ★★★ */}
                {pdfLoaded && difficultSentences.length > 0 && (
                    <UnderlineOverlay
                        sentences={difficultSentences}
                        dimensions={renderedPdfDimensions}
                        containerRef={viewerContainerRef}
                        onSentenceClick={handleSentenceClick}
                    />
                )}

                {showPopup && currentSentence && (
                    <div
                        className="sentence-popup ai-style"
                        style={{
                            position: 'absolute',
                            left: `${Math.min(popupPosition.left, window.innerWidth - 420)}px`,
                            top: `${Math.max(popupPosition.top + 10, 10)}px`,
                            transform: popupPosition.left > window.innerWidth - 420 ? 'translateX(-100%)' : 'none',
                            zIndex: 1000,
                            width: '400px'
                        }}
                    >
                        <div className="ai-panel">
                            <div className="panel-header">
                                <div className="ai-identity">
                                    <span className="ai-avatar-small">🤖</span>
                                    <span className="ai-name">NH AI 도우미</span>
                                </div>
                                <button className="close-btn" onClick={() => setShowPopup(false)}>✕</button>
                            </div>

                            <div className="panel-content">
                                {/* 원본 내용 */}
                                <div className="original-content">
                                    <span className="label">원본 내용</span>
                                    <p className="original-text">{currentSentence.sentence}</p>
                                </div>

                                {/* 쉬운 설명 */}
                                <div className="simple-explanation">
                                    <span className="label">쉽게 풀어서 설명</span>
                                    <div className="explanation-box">
                                        <p>{currentSentence.simplified_explanation}</p>
                                    </div>
                                </div>

                                {/* 실생활 예시 */}
                                <div className="example-section">
                                    <span className="label">실생활 예시</span>
                                    <div className="example-box">
                                        <span className="example-icon">💡</span>
                                        <p>
                                            {currentSentence.sentence.includes('압류') || currentSentence.sentence.includes('가압류') || currentSentence.sentence.includes('질권설정')
                                                ? '법원에서 계좌를 막거나, 빚 담보로 예금이 잡히면 돈을 찾을 수 없습니다.'
                                                : '이 조건에 해당하는 경우 예금 이용에 제한이 있을 수 있습니다.'
                                            }
                                        </p>
                                    </div>
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