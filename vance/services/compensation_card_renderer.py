"""
Renderer that uses the actual React component from vance-comp-card to generate images.
Uses Playwright to render the component and take a screenshot.
"""

import os
import json
import asyncio
from typing import List
from pathlib import Path

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️ [COMP_CARD] Playwright not installed. Install with: pip install playwright && playwright install chromium")


class CompensationCardRenderer:
    """Renders compensation card using the actual React component."""
    
    def __init__(self):
        self.comp_card_dir = Path("/Users/alt/vance-comp-card")
        self.port = 3001  # Port for the dev server
        
    async def render_card_png(
        self,
        compensation_band: str,
        helping_signals: List[str],
        holding_back: List[str],
        fixes: List[str] = None,
    ) -> bytes:
        """
        Render the compensation card using the actual React component.
        
        Returns PNG bytes of the rendered card.
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is not installed. Cannot render React component.")
        
        # Combine holding_back and fixes
        combined_holding_back = holding_back.copy()
        if fixes:
            combined_holding_back.extend(fixes)
        
        # Create HTML file with the component data
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Compensation Card</title>
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        :root {{
            --background: 0 0% 0%;
            --foreground: 0 0% 100%;
            --card: 0 0% 6%;
            --card-foreground: 0 0% 100%;
            --primary: 142 71% 45%;
            --primary-foreground: 0 0% 0%;
            --secondary: 0 0% 12%;
            --secondary-foreground: 0 0% 100%;
            --muted: 0 0% 15%;
            --muted-foreground: 0 0% 60%;
            --accent: 142 71% 45%;
            --accent-foreground: 0 0% 0%;
            --info: 217 91% 60%;
            --info-foreground: 0 0% 100%;
            --warning: 38 92% 50%;
            --warning-foreground: 0 0% 0%;
            --border: 0 0% 18%;
            --input: 0 0% 18%;
            --ring: 142 71% 45%;
            --radius: 0.75rem;
        }}
        body {{
            background: hsl(var(--background));
            color: hsl(var(--foreground));
            margin: 0;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }}
    </style>
</head>
<body>
    <div id="root"></div>
    <script type="text/babel">
        const {{ useState }} = React;
        
        // Lucide icons as SVG components
        const Sparkles = ({{ size = 24, className = "" }}) => (
            <svg width="{{size}}" height="{{size}}" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={{className}}>
                <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>
                <path d="M5 3v4"/>
                <path d="M19 17v4"/>
                <path d="M3 5h4"/>
                <path d="M17 19h4"/>
            </svg>
        );
        
        const CheckCircle = ({{ size = 24, className = "" }}) => (
            <svg width="{{size}}" height="{{size}}" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={{className}}>
                <circle cx="12" cy="12" r="10"/>
                <path d="m9 12 2 2 4-4"/>
            </svg>
        );
        
        const AlertCircle = ({{ size = 24, className = "" }}) => (
            <svg width="{{size}}" height="{{size}}" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={{className}}>
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
        );
        
        const CompensationCard = ({{ compensationBand, helpingSignals, holdingBack }}) => {{
            return (
                <div style={{{{ width: '100%', maxWidth: '512px', margin: '0 auto' }}}}>
                    <div style={{{{ 
                        position: 'relative',
                        overflow: 'hidden',
                        borderRadius: '1rem',
                        backgroundColor: 'hsl(var(--card))',
                        border: '1px solid hsl(var(--border) / 0.5)',
                        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
                    }}}}>
                        {/* Gradient overlay */}
                        <div style={{{{ 
                            position: 'absolute',
                            inset: 0,
                            background: 'linear-gradient(to bottom right, hsl(var(--primary) / 0.05), transparent, hsl(var(--info) / 0.05))',
                            pointerEvents: 'none'
                        }}}} />
                        
                        {/* Header */}
                        <div style={{{{ 
                            position: 'relative',
                            padding: '24px 24px 16px',
                            borderBottom: '1px solid hsl(var(--border) / 0.3)'
                        }}}}>
                            <div style={{{{ display: 'flex', alignItems: 'center', gap: '8px' }}}}>
                                <Sparkles size={20} className="text-primary" style={{{{ color: 'hsl(var(--primary))' }}}} />
                                <span style={{{{ 
                                    fontSize: '14px',
                                    fontWeight: 600,
                                    letterSpacing: '0.05em',
                                    color: 'hsl(var(--primary))',
                                    textTransform: 'uppercase'
                                }}}}>
                                    Vance
                                </span>
                            </div>
                            <h2 style={{{{ 
                                marginTop: '12px',
                                fontSize: '20px',
                                fontWeight: 600,
                                color: 'hsl(var(--foreground))'
                            }}}}>
                                Compensation Analysis
                            </h2>
                        </div>
                        
                        {/* Compensation Band Pill */}
                        <div style={{{{ position: 'relative', padding: '20px 24px' }}}}>
                            <div style={{{{ 
                                display: 'inline-flex',
                                alignItems: 'center',
                                padding: '10px 16px',
                                borderRadius: '9999px',
                                backgroundColor: 'hsl(var(--info) / 0.15)',
                                border: '1px solid hsl(var(--info) / 0.3)'
                            }}}}>
                                <span style={{{{ 
                                    fontSize: '18px',
                                    fontWeight: 600,
                                    color: 'hsl(var(--info))'
                                }}}}>
                                    {compensationBand}
                                </span>
                            </div>
                        </div>
                        
                        {/* Helping Signals Section */}
                        <div style={{{{ position: 'relative', padding: '0 24px 20px' }}}}>
                            <div style={{{{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}}}>
                                <CheckCircle size={16} style={{{{ color: 'hsl(var(--primary))' }}}} />
                                <h3 style={{{{ 
                                    fontSize: '14px',
                                    fontWeight: 600,
                                    color: 'hsl(var(--primary))',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.05em'
                                }}}}>
                                    Helping Signals
                                </h3>
                            </div>
                            <ul style={{{{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '10px' }}}}>
                                {helpingSignals.map((signal, index) => (
                                    <li key={index} style={{{{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}}}>
                                        <span style={{{{ 
                                            marginTop: '6px',
                                            width: '6px',
                                            height: '6px',
                                            borderRadius: '50%',
                                            backgroundColor: 'hsl(var(--primary))',
                                            flexShrink: 0
                                        }}}} />
                                        <span style={{{{ 
                                            fontSize: '14px',
                                            color: 'hsl(var(--foreground) / 0.9)',
                                            lineHeight: '1.6'
                                        }}}}>
                                            {signal}
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                        
                        {/* Divider */}
                        <div style={{{{ margin: '0 24px', height: '1px', backgroundColor: 'hsl(var(--border) / 0.5)' }}}} />
                        
                        {/* Holding Back Section */}
                        <div style={{{{ position: 'relative', padding: '20px 24px' }}}}>
                            <div style={{{{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}}}>
                                <AlertCircle size={16} style={{{{ color: 'hsl(var(--warning))' }}}} />
                                <h3 style={{{{ 
                                    fontSize: '14px',
                                    fontWeight: 600,
                                    color: 'hsl(var(--warning))',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.05em'
                                }}}}>
                                    Holding Back & Fixes
                                </h3>
                            </div>
                            <ul style={{{{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '10px' }}}}>
                                {holdingBack.map((item, index) => (
                                    <li key={index} style={{{{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}}}>
                                        <span style={{{{ 
                                            marginTop: '6px',
                                            width: '6px',
                                            height: '6px',
                                            borderRadius: '50%',
                                            backgroundColor: 'hsl(var(--warning))',
                                            flexShrink: 0
                                        }}}} />
                                        <span style={{{{ 
                                            fontSize: '14px',
                                            color: 'hsl(var(--foreground) / 0.9)',
                                            lineHeight: '1.6'
                                        }}}}>
                                            {item}
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                        
                        {/* Footer */}
                        <div style={{{{ 
                            position: 'relative',
                            padding: '16px 24px',
                            backgroundColor: 'hsl(var(--secondary) / 0.3)',
                            borderTop: '1px solid hsl(var(--border) / 0.3)'
                        }}}}>
                            <div style={{{{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}}}>
                                <Sparkles size={14} style={{{{ color: 'hsl(var(--muted-foreground))' }}}} />
                                <span style={{{{ 
                                    fontSize: '12px',
                                    color: 'hsl(var(--muted-foreground))',
                                    fontWeight: 500
                                }}}}>
                                    Generated by Vance from your call
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            );
        }};
        
        const helpingSignals = {json.dumps(helping_signals)};
        const holdingBack = {json.dumps(combined_holding_back)};
        const compensationBand = {json.dumps(compensation_band)};
        
        ReactDOM.render(
            <CompensationCard 
                compensationBand={compensationBand}
                helpingSignals={helpingSignals}
                holdingBack={holdingBack}
            />,
            document.getElementById('root')
        );
    </script>
</body>
</html>
"""
        
        # Use Playwright to render and screenshot
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 600, "height": 1000})
            
            # Set the HTML content
            await page.set_content(html_content, wait_until="networkidle")
            
            # Wait a bit for React to render
            await page.wait_for_timeout(500)
            
            # Take screenshot of the card element
            card_element = await page.query_selector("#root > div > div")
            if card_element:
                screenshot_bytes = await card_element.screenshot(type="png")
            else:
                # Fallback: screenshot the whole page
                screenshot_bytes = await page.screenshot(type="png", full_page=True)
            
            await browser.close()
            
            return screenshot_bytes


# For backward compatibility, create a sync wrapper
def render_card_png_sync(
    compensation_band: str,
    helping_signals: List[str],
    holding_back: List[str],
    fixes: List[str] = None,
) -> bytes:
    """Synchronous wrapper for render_card_png."""
    return asyncio.run(
        CompensationCardRenderer().render_card_png(
            compensation_band, helping_signals, holding_back, fixes
        )
    )


