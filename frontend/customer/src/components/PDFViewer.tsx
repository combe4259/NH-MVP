import React, { useState, useRef, useEffect } from 'react';
import { Worker, Viewer, SpecialZoomLevel } from '@react-pdf-viewer/core';
import { defaultLayoutPlugin } from '@react-pdf-viewer/default-layout';
import { searchPlugin } from '@react-pdf-viewer/search';
import type { RenderHighlightsProps, HighlightArea } from '@react-pdf-viewer/search';

import '@react-pdf-viewer/core/lib/styles/index.css';
import '@react-pdf-viewer/default-layout/lib/styles/index.css';
import '@react-pdf-viewer/search/lib/styles/index.css';
import './PDFViewer.css';

interface ExtendedHighlightArea extends HighlightArea {
    highlightContent: string;
}

interface HighlightedText {
    text: string;
    explanation: string;
}

interface PDFViewerProps {
    fileUrl: string;
    highlightedTexts?: HighlightedText[];
    onTextSelect?: (text: string) => void;
}

const PDFViewer: React.FC<PDFViewerProps> = ({ fileUrl, highlightedTexts = [], onTextSelect }) => {
    const [showPopup, setShowPopup] = useState(false);
    const [popupPosition, setPopupPosition] = useState({ top: 0, left: 0 });
    const [currentExplanation, setCurrentExplanation] = useState('');
    const [pdfLoaded, setPdfLoaded] = useState(false);
    const viewerContainerRef = useRef<HTMLDivElement>(null);

    const highlightedTextsRef = useRef(highlightedTexts);
    useEffect(() => { highlightedTextsRef.current = highlightedTexts; }, [highlightedTexts]);

    const defaultLayoutPluginInstance = defaultLayoutPlugin();

    const searchPluginInstance = searchPlugin({
        renderHighlights: (renderProps: RenderHighlightsProps) => (
            <>
                {renderProps.highlightAreas.map((area, index) => {
                    const extendedArea = area as ExtendedHighlightArea;
                    if (!extendedArea.highlightContent) return null;

                    const keyword = extendedArea.highlightContent.trim();
                    if (!keyword) return null;

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

    useEffect(() => {
        if (highlight && pdfLoaded && highlightedTexts.length > 0) {
            const keywords = highlightedTexts.map(ht => ht.text);
            highlight(keywords);
        }
    }, [highlight, pdfLoaded, highlightedTexts]);

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
        <div className="pdf-viewer-container" ref={viewerContainerRef} onMouseUp={handleTextSelection}>
            <Worker workerUrl="https://unpkg.com/pdfjs-dist@3.4.120/build/pdf.worker.min.js">
                <div className="pdf-viewer-wrapper">
                    <Viewer
                        fileUrl={fileUrl}
                        plugins={[defaultLayoutPluginInstance, searchPluginInstance]}
                        defaultScale={SpecialZoomLevel.PageFit}
                        onDocumentLoad={() => setPdfLoaded(true)}
                    />
                    {showPopup && (
                        <div
                            className="pdf-popup"
                            style={{
                                position: 'absolute',
                                left: `${popupPosition.left}px`,
                                top: `${popupPosition.top}px`,
                                transform: 'translate(-50%, -110%)',
                                zIndex: 1000,
                            }}
                        >
                            <div className="popup-content">
                                <div className="popup-header">
                                    <h4>추가 설명</h4>
                                    <button className="close-btn" onClick={() => setShowPopup(false)}>×</button>
                                </div>
                                <div className="popup-body">
                                    <p>{currentExplanation}</p>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </Worker>
        </div>
    );
};

export default PDFViewer;