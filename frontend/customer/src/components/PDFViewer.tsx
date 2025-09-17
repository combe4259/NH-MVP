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
    onPdfLoaded?: (textRegions: any[]) => void;
}

const PDFViewer: React.FC<PDFViewerProps> = ({ fileUrl, highlightedTexts = [], difficultSentences = [], onTextSelect, onSentenceClick, onPdfLoaded }) => {
    const [showPopup, setShowPopup] = useState(false);
    const [popupPosition, setPopupPosition] = useState({ top: 0, left: 0 });
    const [currentExplanation, setCurrentExplanation] = useState('');
    const [currentSentence, setCurrentSentence] = useState<DifficultSentence | null>(null);
    const [pdfLoaded, setPdfLoaded] = useState(false);

    const viewerContainerRef = useRef<HTMLDivElement>(null);
    
    // PDF 로드 시 텍스트 영역 추출
    useEffect(() => {
        if (pdfLoaded && viewerContainerRef.current && onPdfLoaded) {
            // PDF.js 텍스트 레이어에서 텍스트 영역 추출
            const extractTextRegions = () => {
                const textLayers = viewerContainerRef.current?.querySelectorAll('.rpv-core__text-layer');
                const textRegions: any[] = [];
                
                // PDF 뷰어 컨테이너의 위치 (스크린 좌표)
                const containerRect = viewerContainerRef.current?.getBoundingClientRect();
                if (!containerRect) return;
                
                textLayers?.forEach((layer, pageIndex) => {
                    const textSpans = layer.querySelectorAll('span');
                    textSpans.forEach(span => {
                        const rect = span.getBoundingClientRect();
                        const text = span.textContent?.trim();
                        
                        if (text && text.length > 0) {
                            // 스크린 좌표 그대로 저장
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
                    console.log(`PDF 텍스트 영역 추출 완료: ${textRegions.length}개`);
                    console.log('첫 번째 텍스트 영역:', textRegions[0]);
                    onPdfLoaded(textRegions);
                }
            };
            
            // PDF 렌더링 완료 후 텍스트 추출
            setTimeout(extractTextRegions, 500);
        }
    }, [pdfLoaded, onPdfLoaded]);

    const defaultLayoutPluginInstance = defaultLayoutPlugin();

    const searchPluginInstance = searchPlugin({
        renderHighlights: (renderProps: RenderHighlightsProps) => {
            return (
                <>
                    {renderProps.highlightAreas.map((area, index) => {
                        const keyword = (area as any).keywordStr;
                        if (!keyword?.trim()) return null;
                        const finalKeyword = keyword.trim();

                        // 주요 용어 확인
                        const termMatch = highlightedTexts.find(ht =>
                            typeof ht.text === 'string' &&
                            (ht.text.includes(finalKeyword) || finalKeyword.includes(ht.text))
                        );

                        if (termMatch) {
                            return (
                                <div
                                    key={`term-${index}`}
                                    className="custom-highlight-underline"
                                    style={renderProps.getCssProperties(area)}
                                    onClick={() => handleHighlightClick(area, termMatch.explanation)}
                                    title={termMatch.explanation}
                                />
                            );
                        }

                        // 어려운 문장 확인
                        const sentenceMatch = difficultSentences.find(s =>
                            s.sentence.includes(finalKeyword) || finalKeyword.includes(s.sentence)
                        );

                        if (sentenceMatch) {
                            return (
                                <div
                                    key={`sentence-${index}`}
                                    className="sentence-underline"
                                    style={{
                                        ...renderProps.getCssProperties(area),
                                        position: 'absolute',
                                        borderBottom: '3px solid #ffc107 !important',
                                        backgroundColor: 'transparent !important',
                                        cursor: 'pointer',
                                        zIndex: 10
                                    }}
                                    onClick={(e) => {
                                        e.preventDefault();
                                        e.stopPropagation();

                                        if (!viewerContainerRef.current) return;

                                        const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
                                        const containerRect = viewerContainerRef.current.getBoundingClientRect();

                                        console.log('밑줄 위치:', rect);
                                        console.log('컨테이너 위치:', containerRect);

                                        setCurrentSentence(sentenceMatch);
                                        setPopupPosition({
                                            top: rect.bottom - containerRect.top + 10,
                                            left: containerRect.width / 2 - 200 // 중앙 정렬을 위해 팝업 너비의 절반만큼 빼기
                                        });
                                        setShowPopup(true);

                                        if (onSentenceClick) {
                                            onSentenceClick(sentenceMatch);
                                        }
                                    }}
                                    title={`클릭하여 설명 보기: ${sentenceMatch.sentence.substring(0, 30)}...`}
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

    const keywordsRef = useRef<string>('');

    useEffect(() => {
        if (highlight && pdfLoaded) {
            const termKeywords = highlightedTexts.map(ht => ht.text);
            const sentenceKeywords = difficultSentences.map(s => s.sentence);
            const allKeywords = [...termKeywords, ...sentenceKeywords];
            const keywordsString = allKeywords.join('|||');

            console.log('PDFViewer useEffect 실행:');
            console.log('- pdfLoaded:', pdfLoaded);
            console.log('- highlightedTexts:', highlightedTexts);
            console.log('- difficultSentences:', difficultSentences);
            console.log('- allKeywords:', allKeywords);

            if (keywordsString !== keywordsRef.current && allKeywords.length > 0) {
                keywordsRef.current = keywordsString;
                highlight(allKeywords);
                console.log('✅ 검색 실행 - 키워드:', allKeywords);
            }
        }
    }, [pdfLoaded, highlightedTexts, difficultSentences, highlight]);

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

    const handleSentenceClick = useCallback((sentence: DifficultSentence, area: HighlightArea, event: React.MouseEvent) => {
        if (!viewerContainerRef.current) return;

        const containerRect = viewerContainerRef.current.getBoundingClientRect();
        const relativeLeft = (area.left / 100) * containerRect.width;
        const relativeTop = (area.top / 100) * containerRect.height + (area.height / 100) * containerRect.height + 10;

        setCurrentSentence(sentence);
        setPopupPosition({ top: relativeTop, left: relativeLeft });
        setShowPopup(true);

        if (onSentenceClick) {
            onSentenceClick(sentence);
        }
    }, [onSentenceClick]);

    const handleTextSelection = () => {
        const selection = window.getSelection();
        const text = selection?.toString().trim();
        if (text && text.length > 0 && onTextSelect) {
            onTextSelect(text);
        }
    };

    const handleDocumentLoad = useCallback(() => {
        setPdfLoaded(true);
    }, []);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            const target = event.target as HTMLElement;
            if (!target.closest('.pdf-popup') && !target.closest('.custom-highlight-underline') && !target.closest('.sentence-underline')) {
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
            <Worker workerUrl="https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js">
                <div className="pdf-viewer-wrapper">
                    <Viewer
                        fileUrl={fileUrl}
                        plugins={[defaultLayoutPluginInstance, searchPluginInstance]}
                        defaultScale={SpecialZoomLevel.PageFit}
                        onDocumentLoad={handleDocumentLoad}
                    />
                </div>

                {showPopup && currentSentence && (
                    <div
                        className="sentence-popup ai-style"
                        style={{
                            position: 'absolute',
                            left: '50%',
                            top: `${popupPosition.top}px`,
                            transform: 'translateX(-50%)',
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
                                <div className="original-content">
                                    <span className="label">원본 내용</span>
                                    <p className="original-text">{currentSentence.sentence}</p>
                                </div>

                                <div className="simple-explanation">
                                    <span className="label">쉽게 풀어서 설명</span>
                                    <div className="explanation-box">
                                        <p>{currentSentence.simplified_explanation}</p>
                                    </div>
                                </div>

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